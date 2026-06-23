"""
MATH-Ascent §3 (arsenal) — LINEAR ALGEBRA: exact rational solve / inverse / determinant, self-certified.
========================================================================================================
Exact arithmetic over ℚ (fractions.Fraction — never a float), so the answers are EXACT and carry a
SELF-CERTIFYING check: solving Ax=b is O(n³) but the residual  A·x − b = 0  is checkable in O(n²) and proves the
solution with no trust in the solver; the inverse is proven by  A·A⁻¹ = I  exactly. The determinant (fraction-
free Bareiss, O(n³)) is certified by a SECOND independent exact method — cofactor/Laplace expansion (our own)
for small n, sympy's exact det as the cross-check for larger n. Singular systems ⇒ honest DECLINE (no unique
solution / no inverse — never a fabricated answer). This is the §2 fold ethos: compute exactly, then prove the
result against a cheap independent check; offload the grind from the LLM (it must never invert a 6×6 by hand).
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Optional, Sequence

import kernel_verdict as KV

Mat = List[List[Fraction]]


# ── exact matrix helpers (Fraction, never float) ─────────────────────────────────────────────────────────
def _F(M: Sequence[Sequence]) -> Mat:
    return [[Fraction(x) for x in row] for row in M]


def _matmul(A: Mat, B: Mat) -> Mat:
    n, m, p = len(A), len(B), len(B[0])
    return [[sum((A[i][k] * B[k][j] for k in range(m)), Fraction(0)) for j in range(p)] for i in range(n)]


def _matvec(A: Mat, x: Sequence[Fraction]) -> List[Fraction]:
    return [sum((A[i][k] * x[k] for k in range(len(x))), Fraction(0)) for i in range(len(A))]


def _ident(n: int) -> Mat:
    return [[Fraction(1) if i == j else Fraction(0) for j in range(n)] for i in range(n)]


def _is_square(A) -> bool:
    return len(A) > 0 and all(len(r) == len(A) for r in A)


# ── exact Gaussian elimination on the augmented matrix (solve & inverse share it) ────────────────────────
def _rref_solve(A: Mat, rhs: Mat) -> Optional[Mat]:
    """Solve A·X = rhs exactly (rhs has one or more columns). Returns X, or None if A is singular."""
    n = len(A)
    aug = [A[i][:] + rhs[i][:] for i in range(n)]
    w = len(rhs[0])
    for col in range(n):
        piv = next((r for r in range(col, n) if aug[r][col] != 0), None)
        if piv is None:
            return None                                   # singular — no unique solution
        aug[col], aug[piv] = aug[piv], aug[col]
        pv = aug[col][col]
        aug[col] = [v / pv for v in aug[col]]
        for r in range(n):
            if r != col and aug[r][col] != 0:
                f = aug[r][col]
                aug[r] = [a - f * b for a, b in zip(aug[r], aug[col])]
    return [row[n:n + w] for row in aug]


def solve_grade(A, b) -> KV.Verdict:
    """Solve A·x = b exactly. Certificate: the residual A·x − b = 0 (exact). Singular A ⇒ DECLINE."""
    if not _is_square(A) or len(b) != len(A):
        return KV.decline("solve: A must be square and match b ⇒ DECLINE", "linear_algebra.solve")
    Af = _F(A)
    X = _rref_solve(Af, [[Fraction(v)] for v in b])
    if X is None:
        return KV.decline("solve: A is singular ⇒ no unique solution ⇒ DECLINE", "linear_algebra.solve")
    x = [row[0] for row in X]
    if _matvec(Af, x) != [Fraction(v) for v in b]:        # ★ self-certifying residual ★
        return KV.decline("solve: residual A·x ≠ b ⇒ DECLINE", "linear_algebra.solve")
    cert = KV.Cert(KV.EXACT, "exact_residual", passed=True, check_cost="O(n²) residual",
                   detail="A·x = b verified exactly over ℚ (residual = 0)")
    return KV.exact(x, "linear_algebra.solve", "O(n³) exact elimination", cert)


def inverse_grade(A) -> KV.Verdict:
    """Exact inverse A⁻¹. Certificate: A·A⁻¹ = I (exact). Singular A ⇒ DECLINE."""
    if not _is_square(A):
        return KV.decline("inverse: A must be square ⇒ DECLINE", "linear_algebra.inverse")
    n = len(A)
    Af = _F(A)
    inv = _rref_solve(Af, _ident(n))
    if inv is None:
        return KV.decline("inverse: A is singular ⇒ not invertible ⇒ DECLINE", "linear_algebra.inverse")
    if _matmul(Af, inv) != _ident(n):                     # ★ self-certifying A·A⁻¹ = I ★
        return KV.decline("inverse: A·A⁻¹ ≠ I ⇒ DECLINE", "linear_algebra.inverse")
    cert = KV.Cert(KV.EXACT, "inverse_identity", passed=True, check_cost="O(n³) one product",
                   detail="A·A⁻¹ = I verified exactly over ℚ")
    return KV.exact(inv, "linear_algebra.inverse", "O(n³) exact elimination", cert)


# ── determinant: fraction-free Bareiss, certified by a second independent exact method ───────────────────
def _bareiss_det(M: Mat) -> Fraction:
    """Fraction-free Bareiss determinant (exact). O(n³), no growing denominators on integer input."""
    n = len(M)
    A = [row[:] for row in M]
    sign = 1
    prev = Fraction(1)
    for k in range(n - 1):
        if A[k][k] == 0:
            sw = next((r for r in range(k + 1, n) if A[r][k] != 0), None)
            if sw is None:
                return Fraction(0)
            A[k], A[sw] = A[sw], A[k]
            sign = -sign
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                A[i][j] = (A[i][j] * A[k][k] - A[i][k] * A[k][j]) / prev
        prev = A[k][k]
    return sign * A[n - 1][n - 1]


def _cofactor_det(M: Mat) -> Fraction:
    """Independent Laplace/cofactor expansion (exact) — the cross-check for small n."""
    n = len(M)
    if n == 1:
        return M[0][0]
    if n == 2:
        return M[0][0] * M[1][1] - M[0][1] * M[1][0]
    total = Fraction(0)
    for j in range(n):
        if M[0][j] == 0:
            continue
        minor = [[M[i][c] for c in range(n) if c != j] for i in range(1, n)]
        total += ((-1) ** j) * M[0][j] * _cofactor_det(minor)
    return total


def det_grade(A) -> KV.Verdict:
    """Exact determinant via Bareiss, certified by an independent exact method (cofactor for small n, sympy
    exact det otherwise). The two exact computations must agree."""
    if not _is_square(A):
        return KV.decline("det: A must be square ⇒ DECLINE", "linear_algebra.det")
    Af = _F(A)
    d = _bareiss_det(Af)
    n = len(Af)
    if n <= 7:
        d2 = _cofactor_det(Af)
        method = "cofactor expansion (our own)"
    else:
        import sympy as sp
        d2 = Fraction(sp.Matrix(A).det())
        method = "sympy exact det"
    if d != d2:                                            # two independent EXACT methods must agree
        return KV.decline(f"det: Bareiss {d} ≠ {method} {d2} ⇒ DECLINE", "linear_algebra.det")
    cert = KV.Cert(KV.EXACT, "det_cross_method", passed=True, check_cost=f"second exact method ({method})",
                   detail=f"det = {d}; fraction-free Bareiss ≡ {method} (exact agreement)")
    return KV.exact(d, "linear_algebra.det", "O(n³) fraction-free", cert)


def solve(problem: dict) -> KV.Verdict:
    """problem = {"op": "solve"|"inverse"|"det", ...}. Unknown op ⇒ honest DECLINE."""
    op = problem.get("op")
    if op == "solve":
        return solve_grade(problem["A"], problem["b"])
    if op == "inverse":
        return inverse_grade(problem["A"])
    if op == "det":
        return det_grade(problem["A"])
    return KV.decline(f"linear_algebra: unknown op {op!r} ⇒ DECLINE", "linear_algebra")
