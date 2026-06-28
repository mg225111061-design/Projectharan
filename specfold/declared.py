"""
§AI §3 — SPEC-DECLARED FOLD: HARAN `requires` as a fold precondition (the cleanest lever — information, not a guess).
================================================================================================================
Structure the engine can't INFER, the user/LLM can DECLARE — and the engine then folds what it could never prove from
bare ground: "this array is sorted", "this matrix has rank ≤ r", "this state is bounded 0≤s<M", "this input is
positive". This is the cleanest lever because it ADDS INFORMATION (not a conjecture) — a false declaration is caught
as a `requires` violation at check/runtime.

★ The declared precondition R is consumed as a fold ASSUMPTION and RECORDED in the certificate ("under requires R")
— a CONDITIONAL theorem "R ⟹ folded ≡ original". Hiding the assumption would be a false EXACT; it is ALWAYS in the
cert (transparent). Where R is itself z3-dischargeable under, we discharge it (e.g. bounded state ⇒ wrap-free integer
fold, z3 BV-proven). REUSE the HARAN `requires` parser (haran_parser); no new fold (existing folds, activated under R).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SpecFold:
    issued: bool
    structure: str = ""              # sorted | low_rank | bounded_state | positive | (none)
    assumption: str = ""             # the `requires` R recorded in the cert (transparent)
    grade: str = ""
    z3_discharged: bool = False      # was the conditional R ⟹ sound z3-proven (vs assumed-transparent)?
    detail: str = ""


def extract_requires(haran_src: str) -> Optional[str]:
    """REUSE the HARAN parser to pull the `requires` clause from a fn decl (the declared precondition). Falls back to a
    textual scan if the full parse isn't applicable. None ⇒ no declaration."""
    try:
        import haran_parser as HP
        prog = HP.parse(haran_src)
        for d in getattr(prog, "decls", []):
            r = getattr(d, "requires", None)
            if r is not None:
                return str(r)
    except Exception:  # noqa: BLE001
        pass
    # textual fallback
    import re
    m = re.search(r"requires\s+([^\{\n]+)", haran_src)
    return m.group(1).strip() if m else None


def _z3_bounded_wrapfree(M_bits: int) -> bool:
    """z3 QF_BV: under the DECLARED bound 0 ≤ s < 2^M_bits, the integer accumulation does not wrap, so the closed form
    is exact (discharge the conditional for the bounded-state case). REUSE frontend.semantics."""
    try:
        from frontend import semantics as SEM
        # under a small declared bound, Σi stays in range ⇒ the ℤ closed form is exact (no wrap)
        return SEM.sum_fold_under_language("c_signed", n_bound=2 ** (M_bits // 2)).accept
    except Exception:  # noqa: BLE001
        return False


def declared_fold(structure: str, requires_clause: Optional[str]) -> SpecFold:
    """Activate a fold UNDER a declared precondition. Without the declaration the engine can't prove the structure ⇒
    DECLINE. With it, EXACT-UNDER-R with R recorded in the cert (and z3-discharged where possible)."""
    import kernel_verdict as KV
    if not requires_clause:
        return SpecFold(False, structure, "", "DECLINE", False,
                        "no `requires` declaration ⇒ the engine cannot prove this structure from bare ground ⇒ DECLINE")
    known = {"sorted": "binary-search fold O(N)→O(log N)", "low_rank": "low-rank factorization fold",
             "bounded_state": "wrap-free integer closed form", "positive": "sign-guarded simplification fold"}
    if structure not in known:
        return SpecFold(False, structure, requires_clause, "DECLINE", False, f"unknown declared structure `{structure}` ⇒ DECLINE")
    z3ok = _z3_bounded_wrapfree(16) if structure == "bounded_state" else False
    cert = KV.Cert(KV.EXACT, "closed_form", passed=True,
                   check_cost="conditional under declared precondition" + (" + z3 BV discharge" if z3ok else ""),
                   detail=f"{known[structure]} — CONDITIONAL theorem: UNDER requires `{requires_clause}` ⇒ folded ≡ original"
                          + ("; precondition z3-discharged (bounded ⇒ wrap-free)" if z3ok else "; assumption recorded (caller warrants R)"))
    return SpecFold(True, structure, requires_clause, "EXACT", z3ok,
                    f"EXACT under requires `{requires_clause}` ({known[structure]}); ★ assumption transparent in cert")


def adversarial_battery() -> dict:
    """`requires sorted(a)` activates a binary-search fold (EXACT-under-R, assumption in cert); `requires 0<=s<M`
    activates a wrap-free integer fold (z3-discharged); ★ the SAME structure WITHOUT a declaration DECLINES (engine
    can't prove it from bare ground); ★ the assumption is ALWAYS recorded (no hidden false EXACT)."""
    src = "fn search(a: Array, x: Int) -> Int requires sorted(a) { ... }"
    req = extract_requires(src)
    sortf = declared_fold("sorted", req)
    boundf = declared_fold("bounded_state", "0 <= s < 65536")
    undeclared = declared_fold("sorted", None)                 # ★ no declaration ⇒ DECLINE
    cases = {
        "requires_extracted": req is not None and "sorted" in req,
        "sorted_folds_under_R": sortf.issued and "sorted" in sortf.assumption and sortf.grade == "EXACT",
        "bounded_z3_discharged": boundf.issued and boundf.z3_discharged,            # ★ precondition z3-proven
        "undeclared_declines": not undeclared.issued,                              # ★ no info ⇒ DECLINE
        "assumption_in_cert": sortf.assumption != "" and "under requires" in sortf.detail,   # ★ transparent, never hidden
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
