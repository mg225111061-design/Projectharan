"""
§AY QLA-5 — displacement-rank unified fold (Toeplitz / Hankel / Vandermonde / Cauchy). ★ net-new structures.
================================================================================================================
A matrix M is "structured" iff a displacement operator ∇(M)=Z·M−M·Z' has LOW rank r≪n. One recognizer unifies the
four classical classes (Toeplitz/Hankel rank ≤2 w.r.t. the shift; Vandermonde/Cauchy rank 1 w.r.t. diagonal
operators) and a structured solve runs in O(r·n²) instead of dense O(n³). REUSE gpu.hidden_structure.
exact_rank_factorization (RREF over ℚ) for the EXACT displacement rank + generator.

hidden_structure already covers Toeplitz/circulant/low-rank/Kronecker; ★ Hankel, Vandermonde and Cauchy are
genuinely NEW here. EXACT = the structure's DEFINING PROPERTY verified over ℚ (no z3 needed — pure rational linear
algebra, residual 0). Float ⇒ rank judgement unstable ⇒ DECLINE (no float-EXACT). Generic dense (∇ full rank) ⇒
DECLINE.
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Optional, Sequence

import kernel_verdict as KV

from . import _la


def _is_toeplitz(M) -> bool:
    n = len(M)
    return all(M[i][j] == M[i - 1][j - 1] for i in range(1, n) for j in range(1, n))


def _is_hankel(M) -> bool:
    n = len(M)
    return all(M[i][j] == M[i - 1][j + 1] for i in range(1, n) for j in range(n - 1))


def _is_vandermonde(M) -> bool:
    n = len(M)
    if any(M[i][0] != 1 for i in range(n)):
        return False
    return all(M[i][j] == M[i][j - 1] * M[i][1] for i in range(n) for j in range(2, n))


def _is_cauchy(M) -> Optional[tuple]:
    """Cauchy ⟺ 1/M[i][j] = x_i − y_j (additive-separable reciprocal). Returns (x, y) or None."""
    n = len(M)
    if any(M[i][j] == 0 for i in range(n) for j in range(n)):
        return None
    R = [[Fraction(1) / M[i][j] for j in range(n)] for i in range(n)]
    if any(R[i][j] - R[i][0] - R[0][j] + R[0][0] != 0 for i in range(n) for j in range(n)):
        return None
    x = [R[i][0] for i in range(n)]                          # x_i − y_0
    y = [R[0][0] - R[0][j] for j in range(n)]                # y_0 − y_j  ⇒  x_i − y_j = R[i][j] (verified above)
    return (x, y)


def _displacement_rank(M) -> int:
    """rank of the Toeplitz/Sylvester displacement ∇ = Z·M − M·Z (Z = lower shift), exact over ℚ."""
    n = len(M)
    Z = _la.shift_down(n)
    grad = _la.matsub(_la.matmul(Z, M), _la.matmul(M, Z))
    return _la.rank_exact(grad)


def displacement_grade(M: Sequence[Sequence]) -> KV.Verdict:
    """Recognize displacement structure. EXACT for a named class (Toeplitz/Hankel/Vandermonde/Cauchy) or a genuinely
    low displacement rank; DECLINE for generic dense (∇ full rank) or float input."""
    try:
        Mf = _la.fmat(M)
    except _la.NonExact as e:
        return KV.decline(f"displacement: {e} ⇒ rank judgement unstable ⇒ DECLINE (no float-EXACT)", "displacement")
    n = len(Mf)
    if n < 2 or any(len(r) != n for r in Mf):
        return KV.decline("displacement: need a square n≥2 matrix", "displacement")

    def _exact(struct: str, r: int, net_new: bool, detail: str):
        cert = KV.Cert(KV.EXACT, "displacement_rank", passed=True, check_cost="exact ℚ defining-property / RREF",
                       detail=detail)
        return KV.exact({"structure": struct, "displacement_rank": r, "net_new": net_new}, "displacement",
                        f"structured solve O(r·n²) (r={r}) vs dense O(n³)", cert,
                        reason=f"Axis-A: {struct} recognized (displacement rank {r}); Axis-B O(n³)→O(r·n²) at large n")

    if _is_toeplitz(Mf):
        return _exact("Toeplitz", 2, False, "constant diagonals M[i][j]=M[i−1][j−1] ∀i,j (∇-rank ≤2 w.r.t. the shift)")
    if _is_hankel(Mf):
        return _exact("Hankel", 2, True, "constant anti-diagonals M[i][j]=M[i−1][j+1] (∇-rank ≤2) ★ net-new")
    if _is_vandermonde(Mf):
        return _exact("Vandermonde", 1, True, "M[i][j]=αᵢ^j (geometric rows, nodes αᵢ=M[i][1]); ∇-rank 1 ★ net-new")
    cauchy = _is_cauchy(Mf)
    if cauchy is not None:
        return _exact("Cauchy", 1, True, "1/M[i][j]=xᵢ−yⱼ (additive-separable reciprocal); ∇-rank 1 ★ net-new")
    # not a named class — fall back to the measured Toeplitz-displacement rank (quasi-Toeplitz / Toeplitz+low-rank)
    r = _displacement_rank(Mf)
    if r < n and r <= max(2, n // 4):
        Z = _la.shift_down(n)
        grad = _la.matsub(_la.matmul(Z, Mf), _la.matmul(Mf, Z))
        from gpu import hidden_structure as HS
        fr = HS.exact_rank_factorization([[x for x in row] for row in grad])
        gen_ok = fr is not None and _la.matmul(fr[0], fr[1]) == grad        # generator reproduces ∇ exactly (residual 0)
        if gen_ok:
            cert = KV.Cert(KV.EXACT, "displacement_rank", passed=True, check_cost="exact ℚ RREF of ∇ + generator",
                           detail=f"low Toeplitz-displacement rank r={r}≪n={n}; generator (G,H) reproduces ∇=ZM−MZ "
                                  f"exactly (residual 0)")
            return KV.exact({"structure": "low-displacement-rank", "displacement_rank": r, "net_new": False},
                            "displacement", f"structured solve O(r·n²) (r={r})", cert,
                            reason=f"Axis-A: low displacement rank r={r}; Axis-B O(n³)→O(r·n²)")
    return KV.decline(f"displacement: no named structure and displacement rank r={r}≈n={n} (generic dense) ⇒ DECLINE",
                      "displacement")


def adversarial_battery() -> dict:
    """★ EXACT: Toeplitz, Hankel(★net-new), Vandermonde(★net-new), Cauchy(★net-new) all recognized exactly.
    ★★ DECLINE boundary: a generic (full-displacement-rank) integer matrix and a float matrix DECLINE — no
    false-EXACT (a generic dense matrix is never called structured)."""
    toe = [[3, 2, 1, 0], [4, 3, 2, 1], [5, 4, 3, 2], [6, 5, 4, 3]]              # constant diagonals
    han = [[1, 2, 3, 4], [2, 3, 4, 5], [3, 4, 5, 6], [4, 5, 6, 7]]              # constant anti-diagonals
    van = [[1, a, a * a, a * a * a] for a in (1, 2, 3, 5)]                       # M[i][j]=αᵢ^j
    cau = [[Fraction(1, (xi - yj)) for yj in (0, 3, 7)] for xi in (1, 2, 4)]    # 1/(xᵢ−yⱼ), nodes NOT co-arithmetic
    gen = [[1, 0, 2, 5], [3, 1, 0, 1], [0, 4, 1, 2], [2, 1, 3, 7]]              # generic (no displacement structure)
    flt = [[1.0, 2.0], [3.0, 4.0]]
    rT = displacement_grade(toe); rH = displacement_grade(han); rV = displacement_grade(van)
    rC = displacement_grade(cau); rG = displacement_grade(gen); rF = displacement_grade(flt)
    cases = {
        "toeplitz_exact": rT.status == KV.EXACT and rT.result["structure"] == "Toeplitz",
        "hankel_exact_netnew": rH.status == KV.EXACT and rH.result["structure"] == "Hankel" and rH.result["net_new"],
        "vandermonde_exact_netnew": rV.status == KV.EXACT and rV.result["structure"] == "Vandermonde" and rV.result["net_new"],
        "cauchy_exact_netnew": rC.status == KV.EXACT and rC.result["structure"] == "Cauchy" and rC.result["net_new"],
        "generic_declines": rG.status == KV.DECLINE,                            # ★★ no false-EXACT on dense
        "float_declines": rF.status == KV.DECLINE,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, x in cases.items() if not x]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
