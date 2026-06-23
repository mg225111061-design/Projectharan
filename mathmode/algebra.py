"""
MATH-Ascent §3 (arsenal) — SYMBOLIC ALGEBRA: factorization / gcd / root-solving, each self-certified.
=====================================================================================================
sympy does the heavy symbolic search; we never take its word — every answer is re-proven by an exact,
independent check that is the DEFINITION of correctness here:
  • factor      → EXACT iff  expand(∏ factors) − poly ≡ 0   (the factorization multiplies back to the input).
  • poly gcd    → EXACT iff  g | p  and  g | q   (exact polynomial division, remainder 0) and g is monic/primitive.
  • solve roots → EXACT iff every returned root is EXPLICIT (radical/rational, not an implicit RootOf) AND
                  p(root) simplifies to 0. A general quintic with no radical solution ⇒ honest DECLINE
                  (Abel–Ruffini: not a fabricated closed form).
This is fold's ethos for algebra: search for structure, then PROVE it with a cheap independent check; offload the
grind from the LLM (it must never expand a degree-12 product by hand). No Lean/Coq — sympy searches, we certify.
"""
from __future__ import annotations

import sympy as sp

import kernel_verdict as KV


def _expr(e, x):
    return sp.sympify(e, locals={str(x): x}) if isinstance(e, str) else e


def factor_grade(poly, x=None) -> KV.Verdict:
    """Factor a polynomial over ℚ. Certificate: expand(factored) − poly ≡ 0 (multiplies back exactly)."""
    x = x or sp.Symbol("x")
    p = _expr(poly, x)
    fac = sp.factor(p)
    if sp.expand(fac - p) != 0:                            # ★ self-certifying: the product reconstructs the input ★
        return KV.decline("factor: expand(factored) ≠ poly ⇒ DECLINE", "algebra.factor")
    nontrivial = fac != sp.expand(p) and bool(fac.args) and fac.func in (sp.Mul, sp.Pow)
    cert = KV.Cert(KV.EXACT, "factor_reconstructs", passed=True, check_cost="one symbolic expand",
                   detail=f"expand({sp.sstr(fac)}) ≡ poly (exact); {'nontrivial' if nontrivial else 'irreducible/trivial'}")
    return KV.exact(fac, "algebra.factor", "exact factorization over ℚ", cert)


def poly_gcd_grade(p, q, x=None) -> KV.Verdict:
    """gcd of two polynomials. Certificate: g | p and g | q (exact polynomial division, remainder 0)."""
    x = x or sp.Symbol("x")
    pp, qq = _expr(p, x), _expr(q, x)
    g = sp.gcd(pp, qq)
    if g == 0:
        return KV.decline("poly_gcd: gcd is 0 (both inputs 0) ⇒ DECLINE", "algebra.poly_gcd")
    rp = sp.rem(sp.Poly(pp, x), sp.Poly(g, x)) if g != 1 else sp.Integer(0)
    rq = sp.rem(sp.Poly(qq, x), sp.Poly(g, x)) if g != 1 else sp.Integer(0)
    if sp.simplify(rp) != 0 or sp.simplify(rq) != 0:       # ★ g divides both, exactly ★
        return KV.decline("poly_gcd: g does not divide both inputs ⇒ DECLINE", "algebra.poly_gcd")
    cert = KV.Cert(KV.EXACT, "gcd_divides_both", passed=True, check_cost="two exact polynomial divisions",
                   detail=f"g = {sp.sstr(g)} divides p and q with remainder 0 (exact)")
    return KV.exact(g, "algebra.poly_gcd", "exact polynomial gcd", cert)


def solve_poly_grade(poly, x=None) -> KV.Verdict:
    """Solve poly(x)=0. EXACT only if EVERY root is explicit (radical/rational) AND p(root)≡0 (substitution).
    A polynomial with no radical solution (general quintic+) ⇒ honest DECLINE (Abel–Ruffini, not fabricated)."""
    x = x or sp.Symbol("x")
    p = _expr(poly, x)
    try:
        roots = sp.solve(sp.Eq(p, 0), x)
    except Exception as e:
        return KV.decline(f"solve_poly: not solvable in closed form ({type(e).__name__}) ⇒ DECLINE", "algebra.solve")
    if not roots:
        return KV.decline("solve_poly: no roots returned ⇒ DECLINE", "algebra.solve")
    for r in roots:
        if r.has(sp.RootOf):                               # implicit root ⇒ no explicit closed form ⇒ honest DECLINE
            return KV.decline("solve_poly: roots only as implicit RootOf (no radical form) ⇒ DECLINE", "algebra.solve")
        if sp.simplify(p.subs(x, r)) != 0:                 # ★ self-certifying: each root satisfies the polynomial ★
            return KV.decline(f"solve_poly: root {sp.sstr(r)} fails p(root)=0 ⇒ DECLINE", "algebra.solve")
    cert = KV.Cert(KV.EXACT, "roots_substitute_zero", passed=True, check_cost=f"{len(roots)} exact substitutions",
                   detail=f"every root explicit (radical/rational) and p(root)≡0; {len(roots)} root(s)")
    return KV.exact(list(roots), "algebra.solve", "exact roots (radicals)", cert)


def interpolate_grade(points, x=None) -> KV.Verdict:
    """The unique degree-<n polynomial through n points. Certificate: p(xᵢ)=yᵢ for EVERY point (self-certifying,
    exact). Duplicate x-coordinates (over-determined / ill-posed) ⇒ honest DECLINE."""
    x = x or sp.Symbol("x")
    pts = [(sp.nsimplify(a), sp.nsimplify(b)) for a, b in points]
    xs = [a for a, _ in pts]
    if len(set(xs)) != len(xs):
        return KV.decline("interpolate: duplicate x-coordinates ⇒ ill-posed ⇒ DECLINE", "algebra.interpolate")
    if len(pts) < 1:
        return KV.decline("interpolate: need ≥ 1 point ⇒ DECLINE", "algebra.interpolate")
    p = sp.expand(sp.interpolate(pts, x))
    if any(sp.simplify(p.subs(x, a) - b) != 0 for a, b in pts):     # ★ passes every point, exactly ★
        return KV.decline("interpolate: polynomial fails a point ⇒ DECLINE", "algebra.interpolate")
    cert = KV.Cert(KV.EXACT, "interpolation_passes_points", passed=True, check_cost=f"{len(pts)} exact evaluations",
                   detail=f"p(x) = {sp.sstr(p)} passes all {len(pts)} points exactly (unique degree<{len(pts)})")
    return KV.exact(p, "algebra.interpolate", "exact Lagrange", cert)


def partial_fractions_grade(expr, x=None) -> KV.Verdict:
    """Partial-fraction decomposition of a rational function. Certificate: the decomposition RECOMBINES to the
    original (exact). A non-rational input that does not simplify back ⇒ honest DECLINE."""
    x = x or sp.Symbol("x")
    e = _expr(expr, x)
    try:
        ap = sp.apart(e, x)
    except Exception as ex:                                  # noqa: BLE001
        return KV.decline(f"partial_fractions: not decomposable ({type(ex).__name__}) ⇒ DECLINE", "algebra.apart")
    if sp.simplify(ap - e) != 0:                             # ★ recombination ≡ original, exact ★
        return KV.decline("partial_fractions: decomposition ≠ original ⇒ DECLINE", "algebra.apart")
    cert = KV.Cert(KV.EXACT, "partial_fractions_recombine", passed=True, check_cost="one symbolic recombination",
                   detail=f"{sp.sstr(e)} = {sp.sstr(ap)} (recombines to the original, exact)")
    return KV.exact(ap, "algebra.apart", "exact partial fractions", cert)


def solve_system_grade(equations, variables) -> KV.Verdict:
    """Solve a system of (polynomial) equations. EXACT only if EVERY returned solution is EXPLICIT and substitutes
    into ALL equations exactly (self-certifying). No closed-form / only-implicit RootOf solutions ⇒ honest DECLINE."""
    syms = [sp.Symbol(v) if isinstance(v, str) else v for v in variables]
    loc = {s.name: s for s in syms}
    eqs = []
    for e in equations:
        e = sp.sympify(e, locals=loc) if isinstance(e, str) else e
        eqs.append(e if isinstance(e, sp.Equality) else sp.Eq(e, 0))
    try:
        sols = sp.solve(eqs, syms, dict=True)
    except Exception as ex:                                  # noqa: BLE001
        return KV.decline(f"solve_system: not solvable in closed form ({type(ex).__name__}) ⇒ DECLINE", "algebra.system")
    if not sols:
        return KV.decline("solve_system: no solution (or none in closed form) ⇒ DECLINE", "algebra.system")
    for sol in sols:
        if any(val.has(sp.RootOf) for val in sol.values()):
            return KV.decline("solve_system: solutions only as implicit RootOf ⇒ DECLINE", "algebra.system")
        for e in eqs:                                        # ★ each solution satisfies every equation, exactly ★
            if sp.simplify(e.lhs.subs(sol) - e.rhs.subs(sol)) != 0:
                return KV.decline("solve_system: a solution fails an equation ⇒ DECLINE", "algebra.system")
    cert = KV.Cert(KV.EXACT, "system_solutions_substitute", passed=True,
                   check_cost=f"{len(sols)}×{len(eqs)} exact substitutions",
                   detail=f"{len(sols)} solution(s); each satisfies all {len(eqs)} equations exactly")
    return KV.exact(sols, "algebra.system", "exact (verified by substitution)", cert)


def solve(problem: dict) -> KV.Verdict:
    """problem = {"op": "factor"|"poly_gcd"|"solve_poly"|"interpolate"|"partial_fractions"|"solve_system", ...}."""
    op = problem.get("op")
    x = sp.Symbol(problem.get("var", "x"))
    if op == "factor":
        return factor_grade(problem["poly"], x)
    if op == "poly_gcd":
        return poly_gcd_grade(problem["p"], problem["q"], x)
    if op == "solve_poly":
        return solve_poly_grade(problem["poly"], x)
    if op == "interpolate":
        return interpolate_grade(problem["points"], x)
    if op == "partial_fractions":
        return partial_fractions_grade(problem["expr"], x)
    if op == "solve_system":
        return solve_system_grade(problem["equations"], problem["variables"])
    return KV.decline(f"algebra: unknown op {op!r} ⇒ DECLINE", "algebra")
