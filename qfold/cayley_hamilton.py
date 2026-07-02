"""
§AY QLA-2 — Cayley–Hamilton matrix-power fold.
================================================================================================================
χ_A(A)=0 ⟹ Aⁿ = −Σ a_i Aⁱ, so a matrix-power LOOP (A^k built by k multiplications, O(k·n³)) collapses to a single
power-by-squaring (REUSE cfinite._matpow, O(n³·log k)), and every entry of A^k is C-finite (order-n recurrence with
coefficients from the characteristic polynomial). The char poly is computed by Faddeev–LeVerrier (exact over ℚ).

★ ∀-k = the Cayley–Hamilton THEOREM (§0-b). The exact certificate is the entrywise residual χ_A(A)=0 over ℚ (a
finite matrix identity, residual 0 — no z3 induction needed). Float A ⇒ DECLINE (no float-EXACT, §1-Q3).
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Sequence

import cfinite
import kernel_verdict as KV

from . import _la


def _trace(A) -> Fraction:
    return sum((A[i][i] for i in range(len(A))), Fraction(0))


def _scal(s, A):
    return [[s * A[i][j] for j in range(len(A))] for i in range(len(A))]


def _add(A, B):
    return [[A[i][j] + B[i][j] for j in range(len(A))] for i in range(len(A))]


def char_poly_faddeev(A) -> List[Fraction]:
    """Faddeev–LeVerrier: returns [c_{n-1}, …, c_0], the χ_A(λ)=λⁿ+c_{n-1}λ^{n-1}+…+c_0 coefficients (exact ℚ)."""
    n = len(A)
    I = _la.eye(n)
    Mk = _la.eye(n)
    coeffs = []
    for k in range(1, n + 1):
        AMk = _la.matmul(A, Mk)
        ck = -_trace(AMk) / k
        coeffs.append(ck)
        Mk = _add(AMk, _scal(ck, I))
    return coeffs                                              # [c_{n-1}, …, c_0]


def cayley_hamilton_fold(A: Sequence[Sequence]) -> KV.Verdict:
    """Recognize a matrix-power as C-finite via Cayley–Hamilton. EXACT (integer/rational A) — entrywise χ_A(A)=0
    residual 0; the power-loop folds to O(n³·log N). Float ⇒ DECLINE."""
    try:
        Af = _la.fmat(A)
    except _la.NonExact as e:
        return KV.decline(f"cayley_hamilton: {e} ⇒ DECLINE (no float-EXACT)", "cayley_hamilton")
    n = len(Af)
    if n == 0 or any(len(r) != n for r in Af):
        return KV.decline("cayley_hamilton: need a square matrix", "cayley_hamilton")
    coeffs = char_poly_faddeev(Af)                            # [c_{n-1}, …, c_0]
    # verify Cayley–Hamilton entrywise: Aⁿ + Σ c_i Aⁱ = 0 (exact residual)
    powers = [_la.eye(n)]
    for _ in range(n):
        powers.append(_la.matmul(Af, powers[-1]))
    resid = powers[n]                                         # Aⁿ
    for i in range(n):                                        # + c_{n-1}A^{n-1} + … + c_0 A⁰
        resid = _add(resid, _scal(coeffs[i], powers[n - 1 - i]))
    ch_zero = all(resid[i][j] == 0 for i in range(n) for j in range(n))
    if not ch_zero:                                           # cannot happen for exact A — defensive
        return KV.decline("cayley_hamilton: χ_A(A)≠0 residual (numerical inexactness) ⇒ DECLINE", "cayley_hamilton")
    # entry recurrence: Aᵏ = −Σ c_i A^{k-1-i}  ⇒ cfinite coeffs c_rec = [-c_{n-1}, …, -c_0]
    c_rec = [-coeffs[i] for i in range(n)]
    # held-out: A^N via _matpow == A^N via the recurrence reduction (sanity on an entry), several N
    for N in (n + 3, n + 7, 2 * n + 5):
        viapow = cfinite._matpow(Af, N)
        # reduce A^N through the recurrence on the (0,0) entry sequence e_k = (A^k)[0][0]
        ek = [powers[k][0][0] for k in range(n)]
        if cfinite.companion_nth(c_rec, ek, N) != viapow[0][0]:
            return KV.decline("cayley_hamilton: char-poly recurrence disagrees with matrix power ⇒ DECLINE",
                              "cayley_hamilton")
    cert = KV.Cert(KV.EXACT, "cayley_hamilton_charpoly", passed=True, check_cost="exact χ_A(A)=0 residual + held-out",
                   detail=f"χ_A via Faddeev–LeVerrier; Aⁿ+Σc_iAⁱ=0 entrywise (residual 0); every entry is C-finite "
                          f"order {n}; A^N via power-by-squaring O(n³·log N)")
    return KV.exact({"n": n, "char_poly_coeffs": [str(c) for c in coeffs], "entry_recurrence": [str(c) for c in c_rec]},
                    "cayley_hamilton", f"O(n³·log N) (n={n})", cert,
                    reason="Axis-A: matrix-power recognized as C-finite (Cayley–Hamilton); Axis-B O(k·n³)→O(n³·log k)")


def adversarial_battery() -> dict:
    """★ EXACT: integer matrices' powers fold via Cayley–Hamilton (χ_A(A)=0 residual 0, recurrence matches matpow).
    ★★ DECLINE: a float matrix ⇒ DECLINE (no float-EXACT)."""
    a2 = cayley_hamilton_fold([[2, 1], [1, 3]])
    a2_ok = a2.status == KV.EXACT and a2.result["n"] == 2
    a3 = cayley_hamilton_fold([[1, 2, 0], [0, 1, 3], [4, 0, 1]])
    a3_ok = a3.status == KV.EXACT and len(a3.result["char_poly_coeffs"]) == 3
    flt = cayley_hamilton_fold([[1.1, 0.0], [0.0, 2.2]])
    flt_declines = flt.status == KV.DECLINE
    cases = {"matrix2_exact": a2_ok, "matrix3_exact": a3_ok, "float_declines": flt_declines}
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, x in cases.items() if not x]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
