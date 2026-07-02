"""
MATH-Ascent §3 (arsenal) — OPTIMIZATION: exact linear programming with a SELF-CERTIFYING duality proof.
======================================================================================================
Linear programming has a beautiful self-certifying optimality proof — STRONG DUALITY. For
    max  cᵀx   s.t.  A x ≤ b,  x ≥ 0     (primal)
    min  bᵀy   s.t.  Aᵀy ≥ c,  y ≥ 0     (dual)
weak duality gives cᵀx ≤ bᵀy for ANY feasible (x, y); so if we exhibit a feasible primal x* and a feasible dual
y* with  cᵀx* = bᵀy*  (zero duality gap), then x* is PROVABLY optimal and y* dual-optimal — sandwiched, no search
trusted. We find both by EXACT rational vertex enumeration (small LPs), then the certificate is the three exact
checks: primal feasible, dual feasible, gap = 0. Unbounded / infeasible / a nonzero gap ⇒ honest DECLINE (never a
fabricated optimum). All arithmetic is fractions.Fraction — no float, so the optimum and the certificate are exact.
"""
from __future__ import annotations

import itertools
from fractions import Fraction
from typing import List, Optional, Sequence, Tuple

import kernel_verdict as KV
from mathmode import linear_algebra as LA


def _vertices(A: List[List[Fraction]], b: List[Fraction], n: int):
    """All basic solutions of the system {A x ≤ b, x ≥ 0}: choose n tight constraints (rows of A or x_j ≥ 0),
    solve the n×n system exactly. Yields candidate vertices x (as Fraction lists)."""
    m = len(A)
    rows = [(A[i][:], b[i]) for i in range(m)]                # structural constraints aᵢ·x ≤ bᵢ
    for j in range(n):                                        # nonnegativity −x_j ≤ 0  (tight ⇒ x_j = 0)
        e = [Fraction(0)] * n
        e[j] = Fraction(-1)
        rows.append((e, Fraction(0)))
    for combo in itertools.combinations(range(len(rows)), n):
        M = [rows[i][0][:] for i in combo]
        rhs = [[rows[i][1]] for i in combo]
        X = LA._rref_solve([[Fraction(v) for v in r] for r in M], rhs)
        if X is None:
            continue
        yield [row[0] for row in X]


def _feasible(A, b, x, n) -> bool:
    if any(xj < 0 for xj in x):
        return False
    for i in range(len(A)):
        if sum(A[i][k] * x[k] for k in range(n)) > b[i]:
            return False
    return True


def _best_vertex(A, b, obj, n, maximize: bool):
    """The optimal feasible vertex of {Ax≤b, x≥0} for objective obj (exact), or None if none feasible."""
    best_x, best_val = None, None
    for x in _vertices(A, b, n):
        if not _feasible(A, b, x, n):
            continue
        val = sum(obj[k] * x[k] for k in range(n))
        if best_val is None or (val > best_val if maximize else val < best_val):
            best_x, best_val = x, val
    return best_x, best_val


def lp_max_grade(c: Sequence, A: Sequence[Sequence], b: Sequence) -> KV.Verdict:
    """max cᵀx s.t. Ax ≤ b, x ≥ 0. EXACT with the duality certificate (primal & dual feasible, zero gap), or
    honest DECLINE (infeasible / unbounded / nonzero gap)."""
    n = len(c)
    m = len(A)
    cF = [Fraction(v) for v in c]
    AF = [[Fraction(v) for v in row] for row in A]
    bF = [Fraction(v) for v in b]
    x, pval = _best_vertex(AF, bF, cF, n, maximize=True)
    if x is None:
        return KV.decline("lp: primal infeasible ⇒ DECLINE", "optimization.lp")
    # dual: min bᵀy s.t. Aᵀy ≥ c, y ≥ 0  →  as a ≤-system: (−Aᵀ) y ≤ −c, y ≥ 0
    AT = [[AF[i][j] for i in range(m)] for j in range(n)]     # n×m
    negAT = [[-AT[j][i] for i in range(m)] for j in range(n)]
    negc = [-cF[j] for j in range(n)]
    y, dval = _best_vertex(negAT, negc, bF, m, maximize=False)
    if y is None:
        return KV.decline("lp: dual infeasible ⇒ primal unbounded ⇒ DECLINE (no finite optimum)", "optimization.lp")
    # ★ the certificate: primal feasible ∧ dual feasible ∧ zero duality gap ⇒ x* PROVABLY optimal ★
    primal_ok = _feasible(AF, bF, x, n)
    dual_ok = all(y[i] >= 0 for i in range(m)) and all(
        sum(AT[j][i] * y[i] for i in range(m)) >= cF[j] for j in range(n))
    gap = pval - dval
    if not (primal_ok and dual_ok and gap == 0):
        return KV.decline(f"lp: no zero-gap certificate (primal_ok={primal_ok}, dual_ok={dual_ok}, gap={gap}) "
                          f"⇒ DECLINE", "optimization.lp")
    cert = KV.Cert(KV.EXACT, "lp_strong_duality", passed=True, check_cost="O(1) feasibility + zero-gap",
                   detail=f"cᵀx*={pval} = bᵀy*={dval} (zero gap); primal & dual feasible ⇒ x* optimal (exact ℚ)")
    return KV.exact((x, pval), "optimization.lp", "exact vertex enumeration", cert)


def solve(problem: dict) -> KV.Verdict:
    op = problem.get("op")
    if op == "lp_max":
        return lp_max_grade(problem["c"], problem["A"], problem["b"])
    return KV.decline(f"optimization: unknown op {op!r} ⇒ DECLINE", "optimization")
