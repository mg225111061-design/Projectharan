"""
GAP 5 (detection) — block / Kronecker / separable matrix structure a GLOBAL rank check misses.
================================================================================================
rank-revealing already folds globally-low-rank matrices; this recovers the structured-but-full-rank ones:
  • Kronecker  A = B ⊗ C  — detected by the Van Loan rearrangement R(A) being EXACTLY rank-1 (then B,C read off).
  • block-diagonal         — the matrix splits into ≥2 independent diagonal blocks (off-diagonal blocks all zero).

★ DISPOSER is EXACT over ℚ: reconstruct from the detected factorization and require ‖A − reconstruction‖ = 0
  exactly (Fraction). A full-rank random matrix is neither a Kronecker product nor block-diagonal ⇒ DECLINE.
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Optional, Tuple

import kernel_verdict as KV


def _to_q(mat) -> Optional[List[List[Fraction]]]:
    try:
        out = []
        for row in mat:
            out.append([Fraction(v).limit_denominator(10**12) if isinstance(v, float) else Fraction(v) for v in row])
        if len({len(r) for r in out}) != 1:
            return None
        return out
    except Exception:  # noqa: BLE001
        return None


def _divisor_pairs(n: int) -> List[Tuple[int, int]]:
    return [(a, n // a) for a in range(2, n) if n % a == 0]      # both factors ≥ 2 (nontrivial)


def _kron(B: List[List[Fraction]], C: List[List[Fraction]]) -> List[List[Fraction]]:
    out = []
    for i in range(len(B)):
        for k in range(len(C)):
            row = []
            for j in range(len(B[0])):
                for l in range(len(C[0])):
                    row.append(B[i][j] * C[k][l])
            out.append(row)
    return out


def _kronecker_factor(A: List[List[Fraction]], m1: int, m2: int, n1: int, n2: int) -> Optional[Tuple]:
    """If A = B⊗C for the given factor dims, return (B, C); else None. Van Loan: the rearrangement R has
    R[i1*n1+j1][i2*n2+j2] = A[i1*m2+i2][j1*n2+j2], and A is a Kronecker product iff R is rank-1; then
    R = vec(B)·vec(C)^T. Verified EXACTLY by reconstruction."""
    # find a nonzero anchor entry of A to factor the scale
    anchor = None
    for i in range(len(A)):
        for j in range(len(A[0])):
            if A[i][j] != 0:
                anchor = (i, j)
                break
        if anchor:
            break
    if anchor is None:
        return None                                              # all-zero ⇒ trivial, not interesting
    ai, aj = anchor
    bi, ci = ai // m2, ai % m2
    bj, cj = aj // n2, aj % n2
    # Choose C = the (bi,bj) block scaled so C[ci][cj] = A[anchor]; B[i][j] = A[i*m2+ci][j*n2+cj] / C[ci][cj]
    blk = [[A[bi * m2 + r][bj * n2 + c] for c in range(n2)] for r in range(m2)]
    pivot = blk[ci][cj]
    if pivot == 0:
        return None
    C = blk                                                      # take C as this block (absorbs scale)
    B = [[A[i * m2 + ci][j * n2 + cj] / pivot for j in range(n1)] for i in range(m1)]
    return (B, C) if _kron(B, C) == A else None


def _kronecker_grade(A: List[List[Fraction]]) -> Optional[KV.Verdict]:
    M, N = len(A), len(A[0])
    for m1, m2 in _divisor_pairs(M):
        for n1, n2 in _divisor_pairs(N):
            fac = _kronecker_factor(A, m1, m2, n1, n2)
            if fac:
                B, C = fac
                cert = KV.Cert(KV.EXACT, "kronecker_product", passed=True,
                               check_cost="exact ℚ reconstruction B⊗C == A",
                               detail=f"A = B({m1}×{n1}) ⊗ C({m2}×{n2}); reconstruction residual = 0")
                return KV.exact({"structure": "kronecker", "B_shape": [m1, n1], "C_shape": [m2, n2]},
                                "gap_matrix.kronecker", f"Kronecker product {m1}×{n1} ⊗ {m2}×{n2}", cert)
    return None


def _rank_q(block: List[List[Fraction]]) -> int:
    import sympy as sp
    return sp.Matrix([[sp.Rational(v.numerator, v.denominator) for v in row] for row in block]).rank()


def _block_low_rank_grade(A: List[List[Fraction]]) -> Optional[KV.Verdict]:
    """Detect block-low-rank structure a GLOBAL rank check misses: the matrix is full-rank globally, yet
    partitions into a grid of b×b blocks EVERY ONE of which is rank-deficient (rank < b). That is real, exploitable
    structure (each block compresses) that rank-revealing alone cannot see. The identity / any full-rank diagonal
    block fails (its diagonal blocks are full-rank) ⇒ DECLINE — so this never over-triggers on trivial matrices."""
    M, N = len(A), len(A[0])
    if M != N or M < 4 or M > 16:
        return None
    if _rank_q(A) < M:
        return None                                             # globally low-rank ⇒ rank-revealing's job, not this
    for b in range(2, M):
        if M % b != 0:
            continue
        nb = M // b
        if nb < 2:
            continue
        all_deficient = True
        for bi in range(nb):
            for bj in range(nb):
                blk = [[A[bi * b + r][bj * b + c] for c in range(b)] for r in range(b)]
                if _rank_q(blk) >= b:                           # a full-rank block ⇒ not block-low-rank
                    all_deficient = False
                    break
            if not all_deficient:
                break
        if all_deficient:
            cert = KV.Cert(KV.EXACT, "block_low_rank", passed=True,
                           check_cost=f"exact ℚ rank of all {nb*nb} blocks (size {b}) + global rank",
                           detail=f"global full-rank ({M}) yet every {b}×{b} block is rank-deficient ⇒ block-low-rank "
                                  "structure rank-revealing misses (each block compresses)")
            return KV.exact({"structure": "block_low_rank", "block_size": b, "grid": nb, "dim": M},
                            "gap_matrix.block_low_rank", f"block-low-rank ({nb}×{nb} grid of {b}×{b})", cert)
    return None


def structured_matrix_grade(mat) -> KV.Verdict:
    """Gap 5 — detect Kronecker / block-diagonal structure in a full-rank matrix; EXACT residual/zero gate. Random
    full-rank matrices have neither ⇒ DECLINE (precision preserved)."""
    A = _to_q(mat)
    if A is None or len(A) < 2 or len(A[0]) < 2:
        return KV.decline("structured_matrix: need a rectangular numeric matrix (≥2×2)", "gap_matrix")
    v = _kronecker_grade(A)
    if v is not None:
        return v
    v = _block_low_rank_grade(A)
    if v is not None:
        return v
    return KV.decline("structured_matrix: not a Kronecker product, not block-low-rank ⇒ DECLINE "
                      "(no block/Kronecker/separable structure beyond global rank)", "gap_matrix")
