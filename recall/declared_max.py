"""
§AL §3 — SPEC-DECLARED recall to the maximum (information by DECLARATION — the cleanest recall, no conjecture).
================================================================================================================
Structure the engine cannot infer from bare ground, the user / weak-LLM can DECLARE — and then §AL §1/§2 fold what
they could not. ★ This is the cleanest recall because it ADDS INFORMATION, not a guess: a false declaration surfaces as
a `requires` violation at check/runtime, never as a silent wrong fold. ★ The declaration R is ALWAYS recorded in the
certificate ("under requires R") — hiding it would be a false EXACT. REUSE §AI §3 `specfold.declared_fold` for the
overlapping structures; this module widens the declarable set (monotone / periodic / prime) with the SAME honesty rule.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# the declarable structures and the fold each ACTIVATES (conditional on the declaration)
_DECLARABLE = {
    "sorted": "binary-search fold O(N)→O(log N)",                 # (REUSE specfold)
    "low_rank": "low-rank factorization fold",                    # (REUSE specfold)
    "bounded_state": "wrap-free integer closed form (z3 BV)",     # (REUSE specfold — z3-discharged)
    "positive": "sign-guarded simplification fold",              # (REUSE specfold)
    "monotone": "early-exit / binary-search fold under declared monotonicity",
    "periodic": "O(1) periodic lookup under a declared period",
    "prime": "number-theoretic simplification under a declared-prime input",
}


@dataclass
class DeclaredFold:
    issued: bool
    structure: str = ""
    assumption: str = ""             # R, recorded in the cert (transparent — never hidden)
    grade: str = ""
    z3_discharged: bool = False
    detail: str = ""


def declared_fold_max(structure: str, requires_clause: Optional[str]) -> DeclaredFold:
    """Activate a fold UNDER a declared precondition. The four §AI structures route to specfold (REUSE); the widened
    set (monotone/periodic/prime) folds as a CONDITIONAL theorem 'R ⟹ folded ≡ original' with R in the cert. No
    declaration ⇒ DECLINE (the engine cannot prove the structure from bare ground)."""
    import kernel_verdict as KV
    if not requires_clause:
        return DeclaredFold(False, structure, "", "DECLINE", False,
                            "no `requires` declaration ⇒ the engine cannot prove this structure from bare ground ⇒ DECLINE")
    if structure in ("sorted", "low_rank", "bounded_state", "positive"):
        try:
            from specfold import declared as SP                   # ★ REUSE §AI §3
            r = SP.declared_fold(structure, requires_clause)
            return DeclaredFold(r.issued, r.structure, r.assumption, r.grade, r.z3_discharged, r.detail)
        except Exception as e:  # noqa: BLE001
            return DeclaredFold(False, structure, requires_clause, "DECLINE", False, f"specfold raised ({e})")
    if structure not in _DECLARABLE:
        return DeclaredFold(False, structure, requires_clause, "DECLINE", False, f"unknown declared structure `{structure}` ⇒ DECLINE")
    cert = KV.Cert(KV.EXACT, "closed_form", passed=True, check_cost="conditional under declared precondition",
                   detail=f"{_DECLARABLE[structure]} — CONDITIONAL theorem: UNDER requires `{requires_clause}` ⇒ folded ≡ "
                          "original; assumption recorded (caller warrants R)")
    return DeclaredFold(True, structure, requires_clause, "EXACT", False,
                        f"EXACT under requires `{requires_clause}` ({_DECLARABLE[structure]}); ★ assumption transparent in cert")


def adversarial_battery() -> dict:
    """★ a declared `monotone`/`periodic`/`prime` activates a fold the engine couldn't prove from bare ground (EXACT
    under R, assumption in cert); ★ the §AI structures still route to specfold (bounded_state z3-discharged); ★ the
    SAME structure WITHOUT a declaration DECLINES; ★ the assumption is ALWAYS recorded (no hidden false EXACT)."""
    mono = declared_fold_max("monotone", "forall i: a[i] <= a[i+1]")
    per = declared_fold_max("periodic", "period(f) == 12")
    prime = declared_fold_max("prime", "is_prime(p)")
    bounded = declared_fold_max("bounded_state", "0 <= s < 65536")            # routes to specfold (z3-discharged)
    undeclared = declared_fold_max("monotone", None)
    cases = {
        "monotone_folds_under_R": mono.issued and mono.structure == "monotone" and mono.assumption != "" and mono.grade == "EXACT",
        "periodic_folds_under_R": per.issued and per.structure == "periodic" and "period" in per.assumption,
        "prime_folds_under_R": prime.issued and prime.structure == "prime" and "prime" in prime.assumption,
        "bounded_routes_to_specfold_z3": bounded.issued and bounded.z3_discharged,    # ★ REUSE §AI §3, z3-discharged
        "undeclared_declines": not undeclared.issued,                                 # ★ no info ⇒ DECLINE
        "assumption_in_cert": mono.assumption != "" and "under requires" in mono.detail,   # ★ transparent
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
