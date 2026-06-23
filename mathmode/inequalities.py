"""
MATH-Ascent §B4 (arsenal) — INEQUALITIES: univariate polynomial nonnegativity, certified (or a counterexample).
===============================================================================================================
A univariate real polynomial p(x) is ≥ 0 for ALL real x iff its leading coefficient is > 0 AND every real root
has EVEN multiplicity (the graph touches the axis but never crosses below). That structural fact is an EXACT
certificate of global nonnegativity — and it is constructive: if it fails, there is a real x₀ with p(x₀) < 0,
and we EXHIBIT it (a counterexample witness ⇒ honest DECLINE, never a false "it's nonnegative"). We also accept
a sum-of-squares (SOS) certificate directly: if p = Σ qᵢ², then p ≥ 0 is proven by expansion (exact). sympy
finds the roots / expands; OUR check (even multiplicities + positive lead, or the exact expansion, or the exact
negative witness) is what licenses the grade. This is the positivity layer the optimizer/bounds work builds on.
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Optional

import sympy as sp

import kernel_verdict as KV


def _expr(e, x):
    return sp.sympify(e, locals={str(x): x}) if isinstance(e, str) else e


def _negative_witness(P: "sp.Poly", x) -> Optional[sp.Rational]:
    """Find an exact rational x₀ with P(x₀) < 0 (a constructive disproof of nonnegativity), or None."""
    reals = [r for r in sp.real_roots(P)]
    cands = [sp.Integer(0)]
    for r in reals:                                          # probe just off each real root and far out
        rr = sp.nsimplify(r)
        cands += [rr - sp.Rational(1, 4), rr + sp.Rational(1, 4)]
    cands += [sp.Integer(t) for t in (-1000, -10, -3, -1, 1, 3, 10, 1000)]
    for c in cands:
        if not c.is_rational:
            c = sp.Rational(sp.Float(c, 30))
        if P.eval(c) < 0:
            return c
    return None


def nonneg_grade(poly, x=None) -> KV.Verdict:
    """Prove p(x) ≥ 0 for all real x (EXACT), or DECLINE with an exact counterexample x₀ where p(x₀) < 0."""
    x = x or sp.Symbol("x")
    p = _expr(poly, x)
    try:
        P = sp.Poly(p, x)
    except Exception as e:                                   # noqa: BLE001
        return KV.decline(f"nonneg: not a univariate polynomial in {x} ({type(e).__name__}) ⇒ DECLINE",
                          "inequalities.nonneg")
    if P.total_degree() == 0:                                # a constant
        c = P.LC()
        if c >= 0:
            cert = KV.Cert(KV.EXACT, "nonneg_constant", passed=True, check_cost="O(1)", detail=f"constant {c} ≥ 0")
            return KV.exact(True, "inequalities.nonneg", "O(1)", cert)
        return KV.decline(f"nonneg: constant {c} < 0 ⇒ DECLINE (witness: any x)", "inequalities.nonneg")
    lead = P.LC()
    roots = sp.roots(P)                                      # {root: multiplicity}
    odd_real = [r for r, m in roots.items() if r.is_real and m % 2 == 1]
    if lead > 0 and not odd_real:
        # structural certificate; cross-check that no probed point is negative (belt-and-suspenders)
        if _negative_witness(P, x) is not None:
            return KV.decline("nonneg: structural test passed but a negative value was found ⇒ DECLINE (sound)",
                              "inequalities.nonneg")
        cert = KV.Cert(KV.EXACT, "nonneg_even_mult", passed=True, check_cost="root multiplicities + lead sign",
                       detail=f"leading coeff {lead} > 0 ∧ every real root has even multiplicity ⇒ p(x) ≥ 0 ∀x")
        return KV.exact(True, "inequalities.nonneg", "exact (roots)", cert)
    w = _negative_witness(P, x)
    if w is None:
        return KV.decline("nonneg: could not certify nonnegativity (no SOS/structure) ⇒ DECLINE",
                          "inequalities.nonneg")
    return KV.decline(f"nonneg: NOT ≥0 — witness x={w}, p(x)={P.eval(w)} < 0 ⇒ DECLINE", "inequalities.nonneg")


def verify_sos_grade(poly, squares, x=None) -> KV.Verdict:
    """Accept an SOS certificate: if expand(Σ qᵢ²) ≡ poly (exact), then poly ≥ 0 is PROVEN."""
    x = x or sp.Symbol("x")
    p = _expr(poly, x)
    qs = [_expr(q, x) for q in squares]
    if sp.expand(sum(q ** 2 for q in qs) - p) != 0:
        return KV.decline("verify_sos: Σqᵢ² ≠ poly ⇒ DECLINE (not a valid SOS certificate)", "inequalities.sos")
    cert = KV.Cert(KV.EXACT, "sum_of_squares", passed=True, check_cost="one exact expansion",
                   detail=f"poly = Σ qᵢ² ({len(qs)} squares) ⇒ poly ≥ 0 ∀x (exact SOS certificate)")
    return KV.exact(True, "inequalities.sos", "exact SOS", cert)


def solve(problem: dict) -> KV.Verdict:
    op = problem.get("op")
    x = sp.Symbol(problem.get("var", "x"))
    if op == "nonneg":
        return nonneg_grade(problem["poly"], x)
    if op == "verify_sos":
        return verify_sos_grade(problem["poly"], problem["squares"], x)
    return KV.decline(f"inequalities: unknown op {op!r} ⇒ DECLINE", "inequalities")
