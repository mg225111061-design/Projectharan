"""
HARAN #25 (Group B) — exact CP (CANDECOMP/PARAFAC) tensor decomposition for the EXACT-DECIDABLE case.
=====================================================================================================
A CP decomposition writes a tensor as a sum of rank-1 terms. General CP rank is NP-hard, so the HONEST exact
scope is the rank-1 (and rank-0) case over ℚ, which IS exactly decidable and certifiable: a 3-way tensor T is
rank-1 iff T[i][j][k] = a_i·b_j·c_k for some vectors a,b,c — recovered from one nonzero "pivot" fibre and then
RE-COMPOSED and checked entry-by-entry exactly. Higher CP rank ⇒ honest DECLINE (we never fake an exact
decomposition where deciding the rank is NP-hard; that is certified-numeric territory, not EXACT). The certificate
is re-composition equality: Σ (rank-1 terms) ≡ T over ℚ.
"""
from __future__ import annotations

from fractions import Fraction as Fr
from typing import List

import kernel_verdict as KV


def _f3(T):
    return [[[x if isinstance(x, Fr) else Fr(x) for x in row] for row in mat] for mat in T]


def _outer(a, b, c):
    return [[[a[i] * b[j] * c[k] for k in range(len(c))] for j in range(len(b))] for i in range(len(a))]


def cp_rank1(T):
    """If the 3-way tensor T is rank-1 over ℚ, return (a,b,c) with T = a⊗b⊗c; else None. Recover from a nonzero
    pivot (i0,j0,k0): a_i=T[i,j0,k0], b_j=T[i0,j,k0], c_k=T[i0,j0,k]/p² (p=T[i0,j0,k0]); then VERIFY exactly."""
    T = _f3(T)
    I, J, K = len(T), len(T[0]), len(T[0][0])
    piv = None
    for i in range(I):
        for j in range(J):
            for k in range(K):
                if T[i][j][k] != 0:
                    piv = (i, j, k)
                    break
            if piv:
                break
        if piv:
            break
    if piv is None:
        return ([Fr(0)] * I, [Fr(0)] * J, [Fr(0)] * K)       # the zero tensor (rank 0)
    i0, j0, k0 = piv
    p = T[i0][j0][k0]
    a = [T[i][j0][k0] for i in range(I)]
    b = [T[i0][j][k0] for j in range(J)]
    c = [T[i0][j0][k] / (p * p) for k in range(K)]           # normalization so a⊗b⊗c reproduces T at the pivot
    return (a, b, c) if _outer(a, b, c) == T else None


def cp_decompose_grade(T) -> KV.Verdict:
    """Exact CP decomposition of a 3-way tensor over ℚ. EXACT iff T is rank ≤ 1 (recovered factors RE-COMPOSE to T
    exactly — a re-checkable certificate). Higher CP rank ⇒ honest DECLINE (exact CP rank is NP-hard; that case is
    certified-numeric, never a faked EXACT). Malformed (non-rectangular) input ⇒ DECLINE."""
    try:
        T = _f3(T)
        I, J, K = len(T), len(T[0]), len(T[0][0])
        if any(len(m) != J for m in T) or any(len(r) != K for m in T for r in m):
            return KV.decline("cp_decompose: non-rectangular tensor ⇒ DECLINE", "cp_decompose")
    except (TypeError, IndexError, ValueError):
        return KV.decline("cp_decompose: malformed 3-way tensor ⇒ DECLINE", "cp_decompose")
    fac = cp_rank1(T)
    if fac is None:
        return KV.decline("cp_decompose: tensor is not rank ≤ 1 ⇒ DECLINE (general CP rank is NP-hard — exact "
                          "decomposition beyond rank-1 is certified-numeric, not EXACT)", "cp_decompose")
    a, b, c = fac
    rank = 0 if all(x == 0 for x in a) else 1
    if _outer(a, b, c) != T:                                  # ★ re-composition certificate, re-checked ★
        return KV.decline("cp_decompose: re-composition ≠ T ⇒ DECLINE (bug guard)", "cp_decompose")
    cert = KV.Cert(KV.EXACT, "cp_recomposition", passed=True, check_cost="O(IJK) re-composition equality",
                   detail=f"rank-{rank} CP over ℚ: T = a⊗b⊗c with a={a}, b={b}, c={c} — Σ rank-1 terms ≡ T "
                          f"(verified entry-by-entry)")
    return KV.exact({"rank": rank, "factors": (a, b, c)}, "cp_decompose", "exact CP (rank ≤ 1)", cert)
