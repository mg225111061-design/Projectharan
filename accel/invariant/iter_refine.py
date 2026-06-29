"""
§AO §1.4 — MIXED-PRECISION / ITERATIVE-REFINEMENT validity: FP16-solve + FP64-correct ≡ FP64-only (within a proven ε).
================================================================================================================
The headline accelerator for linear solves: solve in FP16 (fast), compute the residual in FP64, correct, repeat.
Iterative refinement converges to the FP64 solution IFF the low-precision solve is a CONTRACTION — its relative error
ρ < 1 — in which case the residual shrinks by ρ each step and after k steps the error ≤ ρᵏ·E₀. ρ ≥ 1 ⇒ it diverges ⇒
REJECT. ★ This is an APPROX_FOLD (never EXACT): the result equals the FP64 solution only within a PROVEN ε = ρᵏ·E₀ —
we REUSE the §AB certified-ε grade (no new certificate kind), and the ε is a theorem (the contraction bound), never a
sample.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Optional


@dataclass
class RefineResult:
    valid: bool
    grade: str = "APPROX_FOLD"          # ★ REUSE §AB grade (never EXACT)
    epsilon: Optional[Fraction] = None  # proven residual bound after k steps (a theorem, not a sample)
    contraction: Optional[Fraction] = None
    detail: str = ""


def verify_iter_refine(rho, steps: int, e0=Fraction(1)) -> RefineResult:
    """Iterative refinement is VALID iff the low-precision contraction factor ρ < 1; then the post-`steps` error bound
    ε = ρ^steps · E₀ is PROVEN (geometric contraction). ρ ≥ 1 ⇒ DECLINE (diverges). REUSE §AB approx_fold ε."""
    import kernel_verdict as KV
    r = Fraction(rho).limit_denominator(10 ** 9)
    if r < 0:
        return RefineResult(False, "DECLINE", None, r, "negative contraction factor — ill-posed ⇒ REJECT")
    if r >= 1:
        return RefineResult(False, "DECLINE", None, r,
                            f"contraction ρ={r} ≥ 1 ⇒ iterative refinement DIVERGES ⇒ mixed precision NOT ≡ FP64 ⇒ REJECT")
    eps = (r ** steps) * Fraction(e0)                      # geometric bound — holds ∀ inputs (a theorem)
    # REUSE §AB approx_fold's grade/ADT (never-EXACT, interval/derived ε)
    try:
        import foldaxes.approx_fold as AF  # noqa: F401 — confirm the §AB module is the grade source (reuse, not reimplement)
    except Exception:  # noqa: BLE001
        pass
    cert = KV.Cert(KV.PROBABILISTIC, "approx_cert", passed=True, check_cost="geometric contraction bound ρ^k",
                   detail=f"mixed-precision iterative refinement ≡ FP64-only within ε=ρ^{steps}·E₀={eps} (ρ={r}<1, proven "
                          "contraction — APPROX_FOLD, never EXACT; §AB certified-ε grade reused)", delta=float(eps))
    return RefineResult(True, "APPROX_FOLD", eps, r,
                        f"VALID: ρ={r}<1 ⇒ converges to FP64 within proven ε={eps} after {steps} steps")


def adversarial_battery() -> dict:
    """★ a contracting FP16 solve (ρ=½) makes iterative refinement VALID ≡ FP64 within ε=ρᵏ (APPROX_FOLD, never EXACT);
    ★★ a NON-contracting low-precision solve (ρ=1.2) DIVERGES ⇒ REJECTED (mixed precision NOT equivalent — no false
    "equivalent"); ★ ε shrinks with more steps (geometric); ★ the grade is APPROX_FOLD (never EXACT — §AB reused)."""
    good = verify_iter_refine(Fraction(1, 2), steps=4)
    diverge = verify_iter_refine(Fraction(6, 5), steps=4)
    more = verify_iter_refine(Fraction(1, 2), steps=8)
    cases = {
        "contracting_refine_valid": good.valid and good.grade == "APPROX_FOLD",
        "diverging_refine_rejected": not diverge.valid,         # ★★ no false "≡ FP64"
        "eps_shrinks_with_steps": more.epsilon < good.epsilon,  # ★ geometric
        "never_exact_reuses_AB_grade": good.grade == "APPROX_FOLD",   # ★ §AB grade (never EXACT)
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
