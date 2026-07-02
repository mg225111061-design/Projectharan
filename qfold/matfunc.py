"""
§AY QLA-6 — matrix-function f(A)v via Chebyshev (PROVEN truncation interval; graded PROBABILISTIC, never EXACT).
================================================================================================================
For an analytic f on a spectral interval [a,b], f(A)v ≈ Σ_{k<K} c_k T_k(Ã)v (3-term Chebyshev recurrence). When f
is analytic in a Bernstein ellipse of parameter ρ>1 with max-modulus M, the Chebyshev coefficients decay |c_k|≤
2M/ρᵏ, so the truncation error is bounded by 2M/(ρ−1)·ρ^{−K}·‖v‖ — a DERIVED, guaranteed bound. The fold is a
B-axis speedup O(n³)→O(K·matvec). Graded PROBABILISTIC with the derived bound in the δ slot (a hard upper bound,
conservatively reported — never EXACT, since the evaluation is floating point).

★ Spectrum unknown (non-normal / complex spectrum) or f non-analytic on [a,b] (ρ→1) ⇒ DECLINE (no honest bound).
"""
from __future__ import annotations

import math
from typing import Optional

import kernel_verdict as KV


def chebyshev_truncation_bound(M_max: float, rho: float, K: int, vnorm: float = 1.0) -> Optional[float]:
    """Derived bound 2·M/(ρ−1)·ρ^{−K}·‖v‖ for analytic f (Bernstein-ellipse parameter ρ>1, max-modulus M). None if
    ρ≤1 (no analyticity margin ⇒ no honest bound)."""
    if rho <= 1.0 or M_max <= 0 or K < 1:
        return None
    return 2.0 * M_max / (rho - 1.0) * (rho ** (-K)) * vnorm


def matfunc_apply(M_max: float, rho: float, K: int, vnorm: float = 1.0, required_tol: float = 1e-6,
                  f_name: str = "analytic f") -> KV.Verdict:
    """Grade an f(A)v Chebyshev approximation: PROBABILISTIC with the DERIVED truncation bound if it meets the
    required tolerance; DECLINE if the spectrum/analyticity is unavailable (ρ≤1) or K too small to reach the bound."""
    bound = chebyshev_truncation_bound(M_max, rho, K, vnorm)
    if bound is None:
        return KV.decline(f"matfunc: ρ={rho}≤1 (no Bernstein-ellipse analyticity margin / unknown spectrum) ⇒ no "
                          f"honest truncation bound ⇒ DECLINE", "matfunc_chebyshev")
    if bound > required_tol:
        need = math.ceil(math.log(2.0 * M_max / ((rho - 1.0) * required_tol) * vnorm) / math.log(rho))
        return KV.decline(f"matfunc: K={K} gives truncation bound {bound:.2e} > required {required_tol:.2e} — would "
                          f"need K≥{need}; DECLINE rather than overclaim", "matfunc_chebyshev")
    cert = KV.Cert(KV.PROBABILISTIC, "chebyshev_truncation", passed=True, check_cost=f"K={K} matvecs (O(K·n))",
                   epsilon=bound, delta=bound,
                   detail=f"f(A)v via {K}-term Chebyshev; |c_k|≤2M/ρᵏ ⇒ truncation ≤2M/(ρ−1)·ρ^(−K)·‖v‖={bound:.2e} "
                          f"(derived from coefficient decay ρ={rho}). PROBABILISTIC — float eval, never EXACT.")
    return KV.probabilistic({"f": f_name, "K": K, "truncation_bound": bound}, "matfunc_chebyshev",
                            f"O(K·matvec) (K={K})", cert,
                            reason="Axis-B only; proven truncation interval from Chebyshev coefficient decay")


def adversarial_battery() -> dict:
    """★ PROBABILISTIC: an analytic f with a healthy ellipse (ρ=2) and enough terms gives a derived bound ≤ tol.
    ★★ DECLINE: ρ≤1 (no analyticity margin / unknown spectrum) and too-few-terms-for-tol both DECLINE; never EXACT."""
    ok = matfunc_apply(M_max=10.0, rho=2.0, K=60, vnorm=1.0, required_tol=1e-6, f_name="exp")
    prob_ok = ok.status == KV.PROBABILISTIC and ok.certificate.delta is not None and ok.certificate.delta <= 1e-6
    never_exact = ok.status != KV.EXACT
    nonanalytic = matfunc_apply(M_max=10.0, rho=1.0, K=60).status == KV.DECLINE          # ρ→1 ⇒ no bound
    tooshort = matfunc_apply(M_max=10.0, rho=2.0, K=3, required_tol=1e-9).status == KV.DECLINE
    cases = {"matfunc_probabilistic": prob_ok, "never_exact": never_exact,
             "nonanalytic_declines": nonanalytic, "too_few_terms_declines": tooshort}
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, x in cases.items() if not x]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
