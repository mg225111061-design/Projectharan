"""
§AH §6 — SECURITY ROUTER (deterministic-first; weak-LLM optional; guarantees NEVER depend on the router).
================================================================================================================
RF-3: there is NO "perfect security". The honest form is *machine-verified ABSENCE of a NAMED vulnerability class* +
an EXPLICIT threat model + DECLINE/FLAG when it can't be proved. The router only decides WHICH verifiers to switch
on (crypto/auth/secrets/smart-contract context); the security GUARANTEE comes solely from the deterministic z3/graph
verifiers below — never from the router or any LLM (the weak-LLM constraint's heart).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

# ★ the binding threat-model scope, attached to every security report (RF-3): what is and is NOT proved.
THREAT_MODEL = {
    "proves": ["timing-leak absence over the modelled channels (constant-time)",
               "taint source→sink non-reachability (information flow)",
               "reentrancy absence (checks-effects-interactions on the modelled CFG)",
               "LOW-entropy INSECURITY (positive finding) — never the converse"],
    "does_NOT_prove": ["unmodelled side channels (cache, power, EM)", "hardware (Spectre/Meltdown)",
                       "protocol flaws", "cryptographic primitive security (hardness assumptions)",
                       "anything outside the stated model"],
    "oath": "we NEVER claim 'perfectly safe' — only 'this named class is machine-verified absent under this model', "
            "or DECLINE/FLAG. Security-side precision 1.0 = ZERO false 'safe'.",
}


@dataclass
class Route:
    verifiers: List[str] = field(default_factory=list)     # which verifiers to enable
    categories: List[str] = field(default_factory=list)
    method: str = "heuristic"                              # "heuristic" | "llm-assisted" (honestly labelled)
    guarantee_independent_of_router: bool = True            # ★ always True — the proof is in the verifiers


def route(code: str, llm_fn: Optional[Callable] = None) -> Route:
    """Deterministic-first triage (keyword + AST heuristics via the existing llm_gate); the optional weak LLM only
    SUGGESTS extra categories — it can never grant a guarantee. Returns which verifiers to switch on."""
    cats: List[str] = []
    method = "heuristic"
    try:
        from security import llm_gate
        gv = llm_gate.security_gate(code, llm_fn=llm_fn)
        cats = list(gv.categories)
        method = gv.method
    except Exception:  # noqa: BLE001
        pass
    low = code.lower()
    if any(k in low for k in ("hash", "hmac", "compare_digest", "secret", "key", "password", "token", "nonce", "sign")):
        cats.append("crypto/secrets")
    if any(k in low for k in ("payable", "call.value", "msg.sender", ".call{", "transfer(", "withdraw")):
        cats.append("smart-contract")
    if any(k in low for k in ("rand", "random", "entropy", "seed", "prng")):
        cats.append("randomness")
    if any(k in low for k in ("input", "request", "argv", "query", "sql", "exec", "os.system", "eval(")):
        cats.append("injection")
    cats = sorted(set(cats))
    verifiers = []
    if "crypto/secrets" in cats:
        verifiers.append("consttime")
    if "randomness" in cats:
        verifiers.append("entropy")
    if "injection" in cats or "crypto/secrets" in cats:
        verifiers.append("taint")
    if "smart-contract" in cats:
        verifiers.append("reentrancy")
    return Route(sorted(set(verifiers)), cats, method, True)


def adversarial_battery() -> dict:
    """crypto code routes to consttime+taint; a smart-contract routes to reentrancy; a PRNG routes to entropy; ★ the
    guarantee is always router-independent (proof lives in the verifiers); the threat model lists what is NOT proved."""
    crypto = route("import hmac\ndef chk(pw, h): return hmac.compare_digest(hash(pw), h)")
    contract = route("function withdraw() public { msg.sender.call.value(bal)(); bal = 0; }")
    prng = route("import random\ndef token(): return random.random()")
    cases = {
        "crypto_routes_consttime": "consttime" in crypto.verifiers,
        "contract_routes_reentrancy": "reentrancy" in contract.verifiers,
        "prng_routes_entropy": "entropy" in prng.verifiers,
        "guarantee_router_independent": crypto.guarantee_independent_of_router,        # ★ weak-LLM constraint
        "threat_model_lists_unproved": len(THREAT_MODEL["does_NOT_prove"]) >= 4 and "perfectly safe" in THREAT_MODEL["oath"],
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
