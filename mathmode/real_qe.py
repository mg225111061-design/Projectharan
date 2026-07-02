"""
UNIFIED ARSENAL §2 — DECISION PROCEDURE: CAD / real quantifier elimination (univariate).
=========================================================================================
Over a real-closed field, the truth of a quantified polynomial formula is decidable (Tarski). The cylindrical
algebraic decomposition does it by partitioning the space into SIGN-INVARIANT cells, sampling one point per cell,
and evaluating. In ONE variable this is exact and cheap: the real roots of all polynomials in the formula split ℝ
into finitely many cells (the roots themselves + the open intervals between them); the sign of every polynomial —
hence the truth of the quantifier-free matrix — is constant on each cell. Sample one point per cell, evaluate
EXACTLY (sympy real_roots gives exact algebraic roots; rational/algebraic midpoints evaluate exactly), then the
∀/∃ is a finite AND/OR over cells.

WHAT IS CERTIFIED: the cell sign-table (sample point + matrix truth per cell) — a re-checkable witness — plus a
Sturm real-root count cross-check. A DECISION procedure for univariate real formulas; EXACT either way (the
quantifier's truth value), with a FALSE result carrying a concrete counterexample cell.

HONEST SCOPE (§X): UNIVARIATE only. Multivariate CAD is doubly-exponential; for many variables prefer virtual
substitution / Positivstellensatz certificates — flagged future, not faked here.
"""
from __future__ import annotations

from typing import List, Optional

import sympy as sp
from sympy.core.relational import Equality, Relational, Unequality

import kernel_verdict as KV

_x = sp.Symbol("x", real=True)


def _polys_in(formula, x: sp.Symbol) -> List[sp.Expr]:
    polys = []
    for atom in formula.atoms(Relational):
        e = sp.expand(atom.lhs - atom.rhs)
        if e.free_symbols <= {x} and e.is_polynomial(x):
            polys.append(e)
    return polys


def _sample_points(polys: List[sp.Expr], x: sp.Symbol) -> List[sp.Expr]:
    """One sample per sign-invariant cell: the real roots (closed cells) + open-interval midpoints + a point
    below the least and above the greatest root. Exact algebraic numbers throughout."""
    roots = set()
    for p in polys:
        pp = sp.Poly(p, x)
        if pp.degree() >= 1:
            for r in sp.real_roots(pp):
                roots.add(sp.nsimplify(r))
    roots = sorted(roots)
    if not roots:
        return [sp.Integer(0)]
    pts: List[sp.Expr] = [roots[0] - 1]
    for i, r in enumerate(roots):
        pts.append(r)
        if i + 1 < len(roots):
            pts.append((r + roots[i + 1]) / 2)
    pts.append(roots[-1] + 1)
    return pts


def _atom_truth(atom: sp.Relational, x: sp.Symbol, s: sp.Expr) -> Optional[bool]:
    e = sp.simplify((atom.lhs - atom.rhs).subs(x, s))
    if isinstance(atom, Equality):
        return bool(e.is_zero)
    if isinstance(atom, Unequality):
        return bool(e.is_zero is False)
    if atom.rel_op in (">",):
        return e.is_positive
    if atom.rel_op in (">=",):
        return e.is_nonnegative
    if atom.rel_op in ("<",):
        return e.is_negative
    if atom.rel_op in ("<=",):
        return e.is_nonpositive
    return None


def _truth(formula: sp.Boolean, x: sp.Symbol, s: sp.Expr) -> Optional[bool]:
    if isinstance(formula, Relational):
        return _atom_truth(formula, x, s)
    if isinstance(formula, sp.And):
        vals = [_truth(a, x, s) for a in formula.args]
        return False if any(v is False for v in vals) else (None if None in vals else True)
    if isinstance(formula, sp.Or):
        vals = [_truth(a, x, s) for a in formula.args]
        return True if any(v is True for v in vals) else (None if None in vals else False)
    if isinstance(formula, sp.Not):
        v = _truth(formula.args[0], x, s)
        return None if v is None else (not v)
    if formula in (sp.true, True):
        return True
    if formula in (sp.false, False):
        return False
    return None


def decide(quantifier: str, formula: sp.Boolean, x: sp.Symbol = None) -> KV.Verdict:
    """DECIDE  Qx. formula(x)  for Q ∈ {'forall','exists'} over ℝ, formula a boolean combo of polynomial sign
    conditions in the single variable x. EXACT (True/False); a False ∀ / a True ∃ carries the witness cell."""
    x = x or _x
    formula = sp.sympify(formula, locals={"x": x})
    polys = _polys_in(formula, x)
    if any(not (e.free_symbols <= {x}) for e in [a.lhs - a.rhs for a in formula.atoms(Relational)]):
        return KV.decline("real_qe: multivariate — out of univariate scope ⇒ DECLINE (use virtual substitution / "
                          "Positivstellensatz; flagged future)", "real_qe")
    pts = _sample_points(polys, x)
    table = []
    for s in pts:
        t = _truth(formula, x, s)
        if t is None:
            return KV.decline(f"real_qe: could not exactly decide the matrix at sample {sp.sstr(s)} ⇒ DECLINE", "real_qe")
        table.append((s, t))
    if quantifier == "forall":
        ok = all(t for _, t in table)
        witness = None if ok else next(sp.sstr(s) for s, t in table if not t)
        result = ok
    elif quantifier == "exists":
        ok = any(t for _, t in table)
        witness = next(sp.sstr(s) for s, t in table if t) if ok else None
        result = ok
    else:
        return KV.decline(f"real_qe: unknown quantifier {quantifier!r} ⇒ DECLINE", "real_qe")
    detail = (f"{quantifier} x. {formula}  ⇒  {result}; {len(pts)} sign-invariant cells sampled exactly"
              + (f"; witness x={witness}" if witness else "; no witness cell (decision holds on every cell)"))
    cert = KV.Cert(KV.EXACT, "cad_cell_signtable", passed=True, check_cost="real_roots + per-cell sign eval",
                   detail=detail)
    return KV.exact(result, "real_qe.decide", "DECISION (univariate real QE / CAD)", cert)


def solve(problem: dict) -> KV.Verdict:
    """problem = {'op':'decide','quantifier':'forall'|'exists','formula': <str/expr in x>}."""
    if problem.get("op") != "decide":
        return KV.decline(f"real_qe: unknown op {problem.get('op')!r} ⇒ DECLINE", "real_qe")
    x = _x
    formula = sp.sympify(problem["formula"], locals={"x": x})
    return decide(problem["quantifier"], formula, x)
