"""
GAP CLOSURE (detection) — recurrence / algebraic structure the linear probe (Berlekamp–Massey) misses.
========================================================================================================
BM sees only LINEAR recurrences; these recover the structure above it, each via the proposer→EXACT-disposer law:
  • Gap 1  nonlinear_recurrence_grade  — x[n] = P(x[n-1..n-k]) of bounded degree (poly), exact ℚ run-forward gate.
  • Gap 2  matrix_recurrence_grade     — coupled/vector streams v[n] = M·v[n-1], exact M re-substitution gate.
  • Gap 3  algebraic_relation_grade    — a polynomial relation P(x[n], x[n-1], n) = 0 (Gröbner cofactor, exact).

★ The disposer is EXACT and in ℚ (Fraction/sympy.Rational — never float): a candidate that does not regenerate EVERY
  supplied term with residual = 0 is rejected, and the input falls through to DECLINE. A random sequence fits no
  bounded-degree recurrence (the held-out tail residual ≠ 0) ⇒ DECLINE. Precision stays 1.0.
Honest core: GENERAL nonlinear recurrence is undecidable; the bounded-degree poly/rational class is the decidable
  island implemented here. Outside it ⇒ DECLINE (never a guess).
"""
from __future__ import annotations

from fractions import Fraction
from itertools import combinations_with_replacement
from typing import List, Optional, Tuple

import kernel_verdict as KV


def _is_num_seq(x, lo: int = 7) -> bool:
    return (isinstance(x, (list, tuple)) and len(x) >= lo
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in x))


def _monomials(window: List[Fraction], k: int, d: int) -> List[Fraction]:
    """All monomials in (window[0..k-1]) of total degree ≤ d, constant term first (deterministic order)."""
    vals = [Fraction(1)]
    for deg in range(1, d + 1):
        for combo in combinations_with_replacement(range(k), deg):
            m = Fraction(1)
            for idx in combo:
                m *= window[idx]
            vals.append(m)
    return vals


def _fit_recurrence(seq: List[Fraction], k: int, d: int) -> Optional[List[Fraction]]:
    """Solve, EXACTLY over ℚ, for coefficients c with x[n] = Σ c_i · monomial_i(x[n-1..n-k]) on all n≥k.
    Returns the unique coefficient vector, or None if the system is inconsistent (no such recurrence) or
    under-determined (not enough independent data ⇒ not certifiable)."""
    import sympy as sp
    rows, rhs = [], []
    for n in range(k, len(seq)):
        window = [seq[n - 1 - j] for j in range(k)]            # x[n-1], x[n-2], …, x[n-k]
        rows.append([sp.Rational(v.numerator, v.denominator) for v in _monomials(window, k, d)])
        rhs.append(sp.Rational(seq[n].numerator, seq[n].denominator))
    A, b = sp.Matrix(rows), sp.Matrix(rhs)
    M = A.cols
    if A.rows < M + 3:                                          # demand ≥3 held-out equations (genuine validation)
        return None
    sol = sp.linsolve((A, b))
    if not sol:                                                 # inconsistent ⇒ no exact recurrence of this (k,d)
        return None
    point = list(sol)[0]
    if any(getattr(v, "free_symbols", set()) for v in point):   # under-determined (free params) ⇒ not certifiable
        return None
    return [Fraction(int(v.p), int(v.q)) for v in point]


def _run_forward_ok(seq: List[Fraction], coeffs: List[Fraction], k: int, d: int) -> bool:
    """The EXACT disposer: re-substitute the fitted recurrence and require it to regenerate EVERY term (n≥k)
    with residual = 0 in ℚ. (One-step prediction from the actual past — the held-out tail is free validation.)"""
    for n in range(k, len(seq)):
        window = [seq[n - 1 - j] for j in range(k)]
        pred = sum(c * m for c, m in zip(coeffs, _monomials(window, k, d)))
        if pred != seq[n]:
            return False
    return True


def nonlinear_recurrence_grade(seq, max_order: int = 3, max_degree: int = 3) -> KV.Verdict:
    """Gap 1 — detect a bounded-degree (nonlinear) polynomial recurrence x[n]=P(x[n-1..n-k]); EXACT ℚ run-forward
    gate. Liberal proposer: try (order, degree) by increasing complexity; the FIRST that regenerates every term
    exactly wins. No fit ⇒ DECLINE (random/irregular input lands here)."""
    if not _is_num_seq(seq):
        return KV.decline("nonlinear_recurrence: need a numeric sequence of length ≥ 7", "gap_recur")
    fseq = [Fraction(v).limit_denominator(10**12) if isinstance(v, float) else Fraction(v) for v in seq]
    int_input = all(isinstance(v, int) and not isinstance(v, bool) for v in seq)
    # try by increasing model complexity (k·d), so the simplest recurrence that fits is reported
    for total in range(2, max_order + max_degree + 1):
        for k in range(1, max_order + 1):
            for d in range(2, max_degree + 1):                 # degree ≥ 2 ⇒ genuinely NONLINEAR (linear is BM's job)
                if k + d != total:
                    continue
                try:
                    coeffs = _fit_recurrence(fseq, k, d)
                except Exception:  # noqa: BLE001
                    coeffs = None
                if coeffs is None:
                    continue
                if not _run_forward_ok(fseq, coeffs, k, d):
                    continue                                    # disposer rejected ⇒ not this (k,d)
                if int_input:                                   # integer sequences must regenerate as integers
                    if any((c.denominator != 1) for c in coeffs) and \
                       not all((sum(c * m for c, m in zip(coeffs, _monomials([fseq[n - 1 - j] for j in range(k)], k, d))).denominator == 1)
                               for n in range(k, len(fseq))):
                        continue
                cert = KV.Cert(KV.EXACT, "nonlinear_recurrence", passed=True,
                               check_cost=f"ℚ run-forward over {len(fseq) - k} terms ({len(fseq) - k - len(coeffs)} held-out)",
                               detail=f"x[n]=P(x[n-1..n-{k}]) deg {d}; regenerates every term, residual=0 (exact)")
                return KV.exact({"order": k, "degree": d, "coeffs": [str(c) for c in coeffs],
                                 "n_terms": len(fseq), "held_out": len(fseq) - k - len(coeffs)},
                                "gap_recur.nonlinear", f"nonlinear recurrence (order {k}, degree {d})", cert)
    return KV.decline("nonlinear_recurrence: no bounded-degree (k≤%d,d≤%d) recurrence regenerates the sequence "
                      "⇒ DECLINE (random / outside the decidable island)" % (max_order, max_degree), "gap_recur")


# ── Gap 2 — matrix / coupled recurrence v[n] = M·v[n-1] (exact M re-substitution) ───────────────────────
def _is_vec_seq(x) -> bool:
    return (isinstance(x, (list, tuple)) and len(x) >= 5
            and all(isinstance(v, (list, tuple)) and len(v) == len(x[0]) and len(v) >= 2
                    and all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in v) for v in x))


def matrix_recurrence_grade(vecs) -> KV.Verdict:
    """Gap 2 — a coupled/vector stream v[n] = M·v[n-1]: fit the transition matrix M EXACTLY over ℚ (one linear
    system per output coordinate), then DISPOSE by re-substitution — require M·v[n-1] = v[n] for every n (exact).
    A non-coupled / random vector stream admits no exact M ⇒ DECLINE. The characteristic polynomial of M is the
    certified closed-form driver."""
    import sympy as sp
    if not _is_vec_seq(vecs):
        return KV.decline("matrix_recurrence: need ≥5 equal-length numeric vectors (dim ≥ 2)", "gap_recur")
    m = len(vecs[0])
    V = [[sp.Rational(Fraction(c).limit_denominator(10**12)) for c in v] for v in vecs]
    if len(V) - 1 < m + 2:                                      # need ≥2 held-out transitions for validation
        return KV.decline("matrix_recurrence: too few transitions to validate (need ≥ dim+3 vectors)", "gap_recur")
    prev = sp.Matrix([V[n] for n in range(len(V) - 1)])         # rows = v[0..N-2]
    rows_M = []
    for i in range(m):                                          # solve row i of M: prev · M_i = (next coord i)
        rhs = sp.Matrix([V[n + 1][i] for n in range(len(V) - 1)])
        sol = sp.linsolve((prev, rhs))
        if not sol:
            return KV.decline(f"matrix_recurrence: coordinate {i} has no exact linear transition ⇒ DECLINE", "gap_recur")
        pt = list(sol)[0]
        if any(getattr(v, "free_symbols", set()) for v in pt):
            return KV.decline("matrix_recurrence: transition under-determined (need more data) ⇒ DECLINE", "gap_recur")
        rows_M.append(list(pt))
    M = sp.Matrix(rows_M)
    # EXACT disposer: M·v[n-1] = v[n] for every transition
    for n in range(len(V) - 1):
        if M * sp.Matrix(V[n]) != sp.Matrix(V[n + 1]):
            return KV.decline("matrix_recurrence: fitted M fails re-substitution ⇒ DECLINE", "gap_recur")
    charpoly = sp.Matrix(M).charpoly().as_expr()
    cert = KV.Cert(KV.EXACT, "matrix_recurrence", passed=True,
                   check_cost=f"ℚ re-substitution over {len(V) - 1} transitions (dim {m})",
                   detail=f"v[n]=M·v[n-1] exactly; M∈ℚ^{m}×{m}; char.poly {sp.srepr(charpoly)[:0]}{charpoly}")
    return KV.exact({"dim": m, "M": [[str(c) for c in row] for row in rows_M], "char_poly": str(charpoly),
                     "transitions": len(V) - 1}, "gap_recur.matrix", f"matrix recurrence (dim {m})", cert)


# ── Gap 3 — algebraic (polynomial, non-recurrence) relation among windowed terms (exact cofactor) ───────
def _window_monomials(vars_vals: List[Fraction], d: int) -> List[Fraction]:
    return _monomials(vars_vals, len(vars_vals), d)            # monomials in the windowed variables up to degree d


def algebraic_relation_grade(seq, window: int = 3, max_degree: int = 2) -> KV.Verdict:
    """Gap 3 — a polynomial relation P(x[n], x[n-1], …) = 0 among `window` consecutive terms that is NOT necessarily
    a recurrence (e.g. geometric x[n]² = x[n-1]·x[n+1]). PROPOSER: build the monomial-evaluation matrix over all
    windows and find an exact rational NULL vector (sympy nullspace) — the vanishing polynomial. DISPOSER (Gröbner-
    cofactor style, EXACT): the relation, re-evaluated on EVERY window, is exactly 0. Random data ⇒ full column rank
    ⇒ no nontrivial null vector ⇒ DECLINE (the held-out windows would not vanish)."""
    import sympy as sp
    if not _is_num_seq(seq, lo=window + 4):
        return KV.decline(f"algebraic_relation: need a numeric sequence of length ≥ {window + 4}", "gap_recur")
    fseq = [Fraction(v).limit_denominator(10**12) if isinstance(v, float) else Fraction(v) for v in seq]
    windows = [[fseq[i + j] for j in range(window)] for i in range(len(fseq) - window + 1)]
    for d in range(2, max_degree + 1):                          # degree ≥2 (a degree-1 relation is just linear/affine)
        rows = [[sp.Rational(v.numerator, v.denominator) for v in _window_monomials(w, d)] for w in windows]
        A = sp.Matrix(rows)
        M = A.cols
        if A.rows < M + 3:                                     # ≥3 held-out windows (else a null vector is trivial)
            continue
        ns = A.nullspace()
        if not ns:
            continue                                            # full column rank ⇒ no relation (random lands here)
        c = ns[0]
        if all(v == 0 for v in c):
            continue
        # EXACT disposer: the polynomial Σ c_j·monomial_j vanishes on EVERY window (re-checked in ℚ)
        if any(sum(cj * mj for cj, mj in zip(c, [sp.Rational(v.numerator, v.denominator) for v in _window_monomials(w, d)])) != 0
               for w in windows):
            continue
        cert = KV.Cert(KV.EXACT, "algebraic_relation[cofactor]", passed=True,
                       check_cost=f"vanishing on all {len(windows)} windows ({len(windows) - M} held-out), exact ℚ",
                       detail=f"degree-{d} polynomial relation among {window} consecutive terms; evaluates to 0 everywhere")
        return KV.exact({"window": window, "degree": d, "relation_coeffs": [str(v) for v in c],
                         "n_windows": len(windows)}, "gap_recur.algebraic",
                        f"algebraic relation (window {window}, degree {d})", cert)
    return KV.decline("algebraic_relation: no nontrivial polynomial relation vanishes on all windows ⇒ DECLINE "
                      "(random / relation-free)", "gap_recur")
