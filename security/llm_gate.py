"""
§R PHASE 1 — THE LLM SECURITY-SENSITIVITY GATE: the LLM judges the NEED, never the FACT.
================================================================================================================
The entry point. The LLM is asked a focused triage question — *does this code handle anything security-sensitive
(secrets, PII, auth, crypto, or untrusted input reaching a sensitive sink)?* — and answers SENSITIVE / NOT-SENSITIVE
with the category and locations. This is a WORLD-KNOWLEDGE judgment the LLM is good at ("a password hash deserves
scrutiny; a Fibonacci helper does not") — it is NOT asked whether the code IS secure (the verifier owns that).

★ The gate is binary and consequential: NOT-SENSITIVE → the verified security layer (Phases 3–4) stays entirely OFF,
the code is untouched, ZERO overhead. SENSITIVE → the layer turns on for the flagged parts. Uncertain → conservative
SENSITIVE (run the analysis) but NEVER auto-harden non-sensitive code (that is the overhead defect).

★ HONEST CLOCK: the LLM judgment is a Clock-A step. LLM egress is BLOCKED in this environment, so the gate falls back
to a conservative STATIC HEURISTIC (secret-like identifiers, crypto APIs, PII/auth names, untrusted-input→sink) and
labels its verdict "heuristic, not LLM-judged" — never presenting the heuristic as the LLM's world-knowledge judgment.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional

SENSITIVE = "SENSITIVE"
NOT_SENSITIVE = "NOT-SENSITIVE"

# secret-like identifiers (keys / passwords / tokens / credentials)
_SECRET_NAMES = re.compile(r"\b(secret|password|passwd|pwd|api[_-]?key|apikey|token|credential|private[_-]?key|"
                           r"salt|nonce|seed|signing[_-]?key|master[_-]?key|session[_-]?key)\b", re.I)
# PII identifiers
_PII_NAMES = re.compile(r"\b(ssn|social_security|credit[_-]?card|card[_-]?number|cvv|email|phone|address|dob|"
                        r"birth[_-]?date|passport|driver[_-]?license)\b", re.I)
# auth / authz identifiers
_AUTH_NAMES = re.compile(r"\b(authenticate|authorize|login|logout|session|permission|role|jwt|oauth|"
                         r"access[_-]?control|is[_-]?admin)\b", re.I)
# crypto API surface (callsites)
_CRYPTO_CALLS = re.compile(r"\b(hashlib|hmac|secrets|cryptography|Crypto|nacl|encrypt|decrypt|\.sign\b|\.verify\b|"
                           r"Cipher|AES|RSA|ECDSA|pbkdf2|bcrypt|scrypt|sha256|sha512|md5)\b")
# untrusted-input sources and sensitive sinks (injection surface)
_UNTRUSTED = re.compile(r"\b(request|input|argv|params?|query_string|user_input|form|payload|body|os\.environ)\b", re.I)
_SINKS = re.compile(r"\b(execute|executemany|executescript|eval|exec|system|popen|Popen|call|run|"
                    r"query|raw|open|loads)\b")
_SINK_FNS = {"execute", "executemany", "executescript", "eval", "exec", "system", "popen", "Popen",
             "call", "run", "query", "raw"}


def _dynamic_sink(code: str) -> Optional[str]:
    """A query/command sink fed by a CONCATENATED / f-string / .format()-built argument — the structure-altering
    injection signal (the same one Phase 2 flags), independent of how the variable is named. Returns the sink name or
    None. This widens the gate's recall: a SQL/command string assembled dynamically deserves scrutiny even when no
    identifier literally matches the 'untrusted source' name list (conservative — never miss a vuln)."""
    try:
        tree = ast.parse(code.strip())
    except SyntaxError:
        return None
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and n.args:
            fn = n.func.attr if isinstance(n.func, ast.Attribute) else (n.func.id if isinstance(n.func, ast.Name) else None)
            if fn in _SINK_FNS:
                a = n.args[0]
                if isinstance(a, (ast.BinOp, ast.JoinedStr)) or \
                        (isinstance(a, ast.Call) and isinstance(a.func, ast.Attribute) and a.func.attr == "format"):
                    return fn
    return None


@dataclass
class GateVerdict:
    verdict: str                       # SENSITIVE | NOT-SENSITIVE
    categories: List[str] = field(default_factory=list)        # secrets | pii | auth | crypto | injection
    locations: List[str] = field(default_factory=list)         # short evidence strings
    method: str = "heuristic"          # "llm" | "heuristic" (honestly labeled)
    reason: str = ""

    @property
    def security_on(self) -> bool:
        return self.verdict == SENSITIVE


def _heuristic_triage(code: str) -> GateVerdict:
    """Conservative static fallback when the LLM is unavailable (egress BLOCKED). Flags secret-like identifiers, crypto
    APIs, PII/auth names, and untrusted-input→sink flows. Any hit ⇒ SENSITIVE; clean ⇒ NOT-SENSITIVE. Labeled
    'heuristic' — never presented as the LLM's world-knowledge judgment."""
    cats: List[str] = []
    locs: List[str] = []

    def scan(rx, cat):
        m = rx.search(code)
        if m:
            cats.append(cat)
            locs.append(f"{cat}: matched {m.group(0)!r}")

    scan(_SECRET_NAMES, "secrets")
    scan(_PII_NAMES, "pii")
    scan(_AUTH_NAMES, "auth")
    if _CRYPTO_CALLS.search(code):
        cats.append("crypto")
        locs.append(f"crypto: matched {_CRYPTO_CALLS.search(code).group(0)!r}")
    # injection: (a) a named untrusted source AND a sensitive sink, OR (b) a sink fed by a dynamic/concatenated
    # string (structure-altering — Phase-2's signal), which deserves scrutiny regardless of source naming
    if _UNTRUSTED.search(code) and _SINKS.search(code):
        cats.append("injection")
        locs.append(f"injection: untrusted {_UNTRUSTED.search(code).group(0)!r} reaches sink "
                    f"{_SINKS.search(code).group(0)!r}")
    else:
        ds = _dynamic_sink(code)
        if ds:
            cats.append("injection")
            locs.append(f"injection: sink {ds}(...) built from a dynamic/concatenated string (structure-altering)")
    if cats:
        return GateVerdict(SENSITIVE, sorted(set(cats)), locs, method="heuristic",
                           reason="static heuristic flagged security-relevant identifiers/APIs/flows (LLM egress "
                                  "BLOCKED — this is NOT the LLM's world-knowledge judgment)")
    return GateVerdict(NOT_SENSITIVE, [], [], method="heuristic",
                       reason="static heuristic found no secret/PII/auth/crypto/injection surface — security layer "
                              "stays OFF (heuristic, not LLM-judged; a real LLM gate would apply world-knowledge)")


_TRIAGE_PROMPT = (
    "SECURITY TRIAGE (judge the NEED, not the fact). Does this code handle anything security-sensitive — secrets "
    "(keys/passwords/tokens), personal data (PII), authentication/authorization, cryptographic operations, or "
    "untrusted input that reaches a sensitive sink (query/command/path/memory)? Answer SENSITIVE or NOT-SENSITIVE "
    "with the category and the specific parts. Do NOT judge whether the code is secure — only whether it deserves "
    "security scrutiny."
)


def security_gate(code: str, llm_fn: Optional[Callable[[str, str], dict]] = None) -> GateVerdict:
    """The gate. If `llm_fn` (a live LLM) is provided, ask it the NEED question (Clock A) and use its world-knowledge
    verdict; on any failure or absence, fall back to the conservative static heuristic (labeled). Uncertain ⇒
    conservative SENSITIVE. NOT-SENSITIVE turns the verified layer fully OFF."""
    if llm_fn is not None:
        try:
            r = llm_fn(_TRIAGE_PROMPT, code) or {}
            verdict = r.get("verdict")
            if verdict in (SENSITIVE, NOT_SENSITIVE):
                return GateVerdict(verdict, list(r.get("categories", [])), list(r.get("locations", [])),
                                   method="llm", reason=r.get("reason", "LLM world-knowledge security-need judgment"))
            # malformed / uncertain ⇒ conservative SENSITIVE (run the analysis; never miss a vuln)
            return GateVerdict(SENSITIVE, ["uncertain"], [], method="llm",
                               reason="LLM uncertain/malformed verdict ⇒ conservative SENSITIVE (analysis only; no "
                                      "auto-harden of non-sensitive code)")
        except Exception:  # noqa: BLE001 — LLM unavailable / egress blocked
            pass
    return _heuristic_triage(code)
