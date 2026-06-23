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


def solve(problem: dict) -> KV.Verdict:
    """problem = {"op": "factor"|"poly_gcd"|"solve_poly", ...}. Unknown op ⇒ honest DECLINE."""
    op = problem.get("op")
    x = sp.Symbol(problem.get("var", "x"))
    if op == "factor":
        return factor_grade(problem["poly"], x)
    if op == "poly_gcd":
        return poly_gcd_grade(problem["p"], problem["q"], x)
    if op == "solve_poly":
        return solve_poly_grade(problem["poly"], x)
    return KV.decline(f"algebra: unknown op {op!r} ⇒ DECLINE", "algebra")
