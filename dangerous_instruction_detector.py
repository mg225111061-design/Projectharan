"""
v29 STAGE 28 — dangerous / contradictory / infeasible instruction detector.  ★safety; breaks GIGO★
====================================================================================================
Most systems faithfully implement a bad instruction. We don't: a dangerous, self-contradictory, or
infeasible instruction is FLAGGED with a safe alternative instead of being silently obeyed — the heart of
breaking garbage-in-garbage-out.

Two bases, clearly labeled:
  • danger lexicon (HEURISTIC) — a small CWE-mapped pattern catalog (TLS-verify-off, rm -rf /, plaintext
    passwords, eval/exec, pickle.loads, shell=True, AES-ECB, hardcoded secrets…). Each hit → FLAG + a safe
    alternative + the CWE. ★Never a heuristic-only HARD BLOCK — flag + alternative; the user decides.★
  • contradiction / infeasibility (SOUND) — numeric/ordering constraints are formalized and checked with
    Z3; UNSAT ⇒ a real contradiction (a proof, not a guess).

★ HONEST (§1.4, §1.5, §5.5) ★: "dangerous" is undecidable in general — we cover an ENUMERATED catalog
(measured coverage), everything else degrades gracefully (SAFE-by-default, not a false alarm). Only the
FORMALIZED contradiction is sound (Z3 UNSAT); lexicon flags are heuristic and never block.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import z3

# ── danger lexicon → (CWE, kind, safe alternative). Heuristic: FLAG + alternative, never hard-block. ──
_DANGER: List[Tuple[str, str, str, str]] = [
    (r"verify\s*=\s*false|insecure_?skip_?verify|ssl[_ ]?verify\s*=\s*false|disable[^\n]{0,15}(tls|ssl|cert)",
     "CWE-295", "TLS/certificate verification disabled",
     "keep certificate verification ON; pin a cert or use a trusted CA bundle"),
    (r"rm\s+-rf\s+/(?:\s|$)|shutil\.rmtree\(\s*['\"]?/",
     "destructive", "unbounded filesystem deletion",
     "scope deletion to a specific subdirectory; never the filesystem root"),
    (r"plain\s*text\s*password|store[^\n]{0,20}password[^\n]{0,20}(plain|clear)|password[^\n]{0,10}in\s+clear",
     "CWE-256/319", "passwords stored in plaintext",
     "hash passwords with a slow KDF (Argon2/bcrypt/scrypt), never store plaintext"),
    (r"(md5|sha1)[^\n]{0,20}password|password[^\n]{0,20}(md5|sha1)",
     "CWE-327/916", "fast/broken hash for passwords",
     "use Argon2/bcrypt for passwords (SHA-256+ is for integrity, not password storage)"),
    (r"\beval\s*\(|\bexec\s*\(",
     "CWE-95", "eval/exec of (possibly untrusted) input",
     "parse explicitly or use ast.literal_eval; never eval/exec untrusted input"),
    (r"pickle\.loads|yaml\.load\s*\((?![^)]*Loader)",
     "CWE-502", "deserializing untrusted data",
     "use json or yaml.safe_load; never unpickle/yaml.load untrusted bytes"),
    (r"shell\s*=\s*true",
     "CWE-78", "shell=True (command-injection risk)",
     "pass an argument list with shell=False; never interpolate user input into a shell string"),
    (r"\becb\b|ecb[_ ]?mode|mode\s*=\s*['\"]?ecb",
     "CWE-327", "AES-ECB (leaks plaintext structure)",
     "use an authenticated mode (AES-GCM); never ECB"),
    (r"(api[_-]?key|secret|password|token)\s*=\s*['\"][A-Za-z0-9_\-]{8,}['\"]",
     "CWE-798", "hardcoded secret/credential",
     "load secrets from env/secret-manager; never hardcode credentials in source"),
]
_DANGER_RE = [(re.compile(p, re.IGNORECASE), cwe, kind, alt) for (p, cwe, kind, alt) in _DANGER]

# known-infeasible combinations (HEURISTIC catalog → flag, not block)
_INFEASIBLE = [
    (("o(1)", "sort"), "O(1)-time sort of arbitrary data is impossible (Ω(n log n) comparison lower bound)",
     "target O(n log n); use O(n) counting/radix only when the key domain is bounded"),
    (("o(1)", "search") , "O(1) search of UNSORTED data is impossible (must inspect Ω(n))",
     "index/sort first (amortize), or accept O(n) for a single unsorted scan"),
]


@dataclass
class Flag:
    kind: str                   # danger | contradiction | infeasible
    basis: str                  # heuristic-lexicon | heuristic-catalog | sound-UNSAT
    evidence: str
    alternative: str
    cwe: str = ""


@dataclass
class DangerReport:
    status: str                 # SAFE | FLAGGED
    flags: List[Flag] = field(default_factory=list)

    @property
    def hard_block(self) -> bool:
        return False             # ★ this detector NEVER hard-blocks — it flags + proposes ★

    def __str__(self):
        if self.status == "SAFE":
            return "SAFE — no dangerous/contradictory/infeasible instruction detected (catalog-bounded)"
        return "FLAGGED:\n  " + "\n  ".join(f"[{f.basis}] {f.kind} ({f.cwe or '-'}): {f.evidence} → {f.alternative}"
                                            for f in self.flags)


# ── contradiction / infeasibility (SOUND, via Z3) ──────────────────────────────────────────────────
_OP = {"<": "<", ">": ">", "<=": "<=", ">=": ">=", "less than": "<", "greater than": ">",
       "at most": "<=", "at least": ">=", "under": "<", "over": ">", "below": "<", "above": ">",
       "no more than": "<=", "no less than": ">="}
_STOP = {"the", "a", "an", "must", "be", "should", "is", "of", "its", "it", "this", "value"}
_BOUND = re.compile(
    r"([a-zA-Z][a-zA-Z ]{0,24}?)\s*(?:must be|should be|be|is)?\s*"
    r"(<=|>=|<|>|less than|greater than|at most|at least|no more than|no less than|under|over|below|above)\s*(\d+)",
    re.IGNORECASE)


def _subject(phrase: str) -> str:
    words = [w for w in re.findall(r"[a-zA-Z]+", phrase.lower()) if w not in _STOP]
    return words[-1] if words else "_"


def extract_bounds(text: str) -> Dict[str, List[Tuple[str, int]]]:
    out: Dict[str, List[Tuple[str, int]]] = {}
    for m in _BOUND.finditer(text):
        subj = _subject(m.group(1))
        op = _OP[m.group(2).lower()]
        out.setdefault(subj, []).append((op, int(m.group(3))))
    return out


def _unsat(bounds: List[Tuple[str, int]]) -> bool:
    s = z3.Solver()
    x = z3.Int("x")
    for op, n in bounds:
        s.add({"<": x < n, ">": x > n, "<=": x <= n, ">=": x >= n}[op])
    return s.check() == z3.unsat


def check_contradiction(text: str) -> List[Flag]:
    """SOUND: per subject, formalize its numeric bounds and report a Z3-UNSAT conjunction as a contradiction."""
    flags: List[Flag] = []
    for subj, bounds in extract_bounds(text).items():
        if len(bounds) >= 2 and _unsat(bounds):
            flags.append(Flag("contradiction", "sound-UNSAT",
                              f"the constraints on '{subj}' are jointly unsatisfiable: {bounds}",
                              f"relax one bound on '{subj}' — there is no value satisfying all of them"))
    return flags


def _check_infeasible(text: str) -> List[Flag]:
    t = text.lower()
    flags: List[Flag] = []
    for keys, why, alt in _INFEASIBLE:
        if all(k in t for k in keys):
            flags.append(Flag("infeasible", "heuristic-catalog", why, alt))
    return flags


def scan_danger(text: str) -> List[Flag]:
    flags: List[Flag] = []
    for rx, cwe, kind, alt in _DANGER_RE:
        m = rx.search(text)
        if m:
            flags.append(Flag("danger", "heuristic-lexicon", f"matched: '{m.group(0).strip()}'", alt, cwe))
    return flags


def detect(prompt: str) -> DangerReport:
    """Flag dangerous (lexicon), contradictory (Z3 UNSAT — sound), or infeasible (catalog) instructions with
    a safe alternative. NEVER silently complies; NEVER heuristic-only hard-blocks."""
    flags = scan_danger(prompt) + check_contradiction(prompt) + _check_infeasible(prompt)
    return DangerReport("FLAGGED" if flags else "SAFE", flags)
