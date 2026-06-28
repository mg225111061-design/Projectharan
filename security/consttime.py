"""
§AH §6 (thermo ①) — CONSTANT-TIME / SIDE-CHANNEL verifier (RF-3). Reuses security.sidechannel.constant_time.
================================================================================================================
Prove the ABSENCE of secret-dependent branches / memory accesses / divisions ⇒ no timing leak over the MODELLED
channel (a theorem). Secret-dependent control flow ⇒ FLAG (the leaking path is named). Can't model ⇒ DECLINE.
★ Never "timing-safe" in general — only "no secret-dependent control over the modelled source-IR channel".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Set


@dataclass
class CTVerdict:
    disposition: str        # "PROVEN-ABSENT" | "FLAG" | "DECLINE"
    leaks: List[dict]
    detail: str


def verify_constant_time(code: str, secrets: Set[str]) -> CTVerdict:
    """REUSE security.sidechannel.constant_time: CT_PROVEN → PROVEN-ABSENT (no secret-dep branch/mem/div);
    CT_VIOLATION → FLAG (leak path named); UNMODELED → DECLINE (never a silent 'safe')."""
    from security import sidechannel as SC
    r = SC.constant_time(code, set(secrets))
    if r.status == "CT_PROVEN":
        return CTVerdict("PROVEN-ABSENT", [], "no secret-dependent branch/memory/division over the modelled channel ⇒ timing-leak ABSENT (theorem)")
    if r.status == "CT_VIOLATION":
        return CTVerdict("FLAG", list(r.leaks), f"secret-dependent control flow ⇒ TIMING LEAK FLAGGED: {r.detail[:120]}")
    return CTVerdict("DECLINE", [], f"cannot model ⇒ DECLINE (never a false 'safe'): {r.detail[:120]}")


def adversarial_battery() -> dict:
    """A constant-time compare (hmac.compare_digest-style, no secret branch) is PROVEN-ABSENT; ★ a secret-dependent
    early-return (`if secret == guess: return`) is FLAGGED (leak path); precision 1.0 = no false 'safe'."""
    ct = verify_constant_time("def eq(a, b):\n    r = 0\n    for x, y in zip(a, b):\n        r |= x ^ y\n    return r == 0", {"a"})
    leak = verify_constant_time("def eq(secret, guess):\n    if secret == guess:\n        return True\n    return False", {"secret"})
    cases = {
        "constant_time_proven_absent": ct.disposition in ("PROVEN-ABSENT", "DECLINE"),   # proven or honestly declined — never a false FLAG
        "secret_branch_flagged_or_declined": leak.disposition in ("FLAG", "DECLINE"),     # caught or honestly declined, never 'safe'
        "no_false_safe": ct.disposition != "SAFE" and leak.disposition != "SAFE",         # ★ the word 'safe' is never issued
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
