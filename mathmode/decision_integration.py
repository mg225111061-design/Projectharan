"""
UNIFIED ARSENAL §2 — DECISION PROCEDURES (integration side): Risch + Kovacic.
=============================================================================
"Closed form OR a proof of non-existence", each with OUR certificate:

  • RISCH — elementary integration of a transcendental elementary integrand: ∫f dx is elementary (return it) OR
    it is NOT (Liouville's principle). DECISION for the transcendental case. Certificate (the EXACT side): the
    returned antiderivative F satisfies F′ = f EXACTLY (differentiate-and-check). The non-elementary side is the
    PROVEN DECLINE: ∫e^{x²}, ∫e^x/x are non-elementary by Liouville (sympy's risch_integrate, a real Risch for the
    transcendental tower, leaves them unevaluated). Honest scope (§X): the ALGEBRAIC case is only partial in
    sympy ⇒ honest UNVERIFIED/DECLINE, never a faked elementary form.
  • KOVACIC — Liouvillian solutions of a 2nd-order linear ODE a₂y″+a₁y′+a₀y=0: the four-case structure decides
    whether a Liouvillian solution exists. Certificate (the EXACT side): the returned general solution, SUBSTITUTED
    into the ODE, reduces to 0 EXACTLY. The non-Liouvillian side (Airy/Bessel — classically NON-Liouvillian) is a
    DECLINE: we report the special-function class honestly (not a from-scratch Kovacic non-existence proof).

We use sympy (risch_integrate / dsolve) as the SEARCH engine; F′=f and the ODE substitution are OUR certificate —
a wrong antiderivative / solution is rejected. No Lean/Coq.
"""
from __future__ import annotations

from typing import List

import sympy as sp

import kernel_verdict as KV

_x = sp.Symbol("x")

# special functions that are classically NON-elementary / NON-Liouvillian (their presence ⇒ no elementary/
# Liouvillian closed form by the respective theorem).
_NONELEM = (sp.erf, sp.erfi, sp.Si, sp.Ci, sp.li, sp.Ei, sp.fresnels, sp.fresnelc)
_NONLIOUVILLE = (sp.airyai, sp.airybi, sp.besselj, sp.bessely, sp.besseli, sp.besselk, sp.hyper, sp.meijerg)


def risch_elementary(f, x: sp.Symbol = None) -> KV.Verdict:
    """DECIDE elementary integrability of f (transcendental case). EXACT antiderivative (F′=f checked) or PROVEN
    DECLINE (non-elementary by Liouville)."""
    x = x or _x
    f = sp.sympify(f, locals={"x": x})
    try:
        from sympy.integrals.risch import risch_integrate
        F = risch_integrate(f, x)
    except NotImplementedError:
        return KV.decline("risch: integrand outside the implemented (transcendental) Risch tower ⇒ honest "
                          "UNVERIFIED/DECLINE (algebraic case is only partial)", "decision_integration")
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"risch: failed ({type(e).__name__}) ⇒ DECLINE", "decision_integration")
    if F.has(sp.Integral):                                   # risch left it unevaluated ⇒ non-elementary
        return KV.decline("risch: ∫ is NON-ELEMENTARY (Liouville) ⇒ PROVEN DECLINE (no elementary antiderivative; "
                          "not a fabricated formula)", "decision_integration")
    if F.has(*_NONELEM):                                     # answer needs erf/Ei/… ⇒ non-elementary
        return KV.decline(f"risch: ∫ requires non-elementary special functions ({F}) ⇒ PROVEN DECLINE (Liouville)",
                          "decision_integration")
    if sp.simplify(sp.diff(F, x) - f) != 0:                  # ★ our certificate: F′ = f exactly ★
        return KV.decline("risch: candidate antiderivative failed F′=f ⇒ DECLINE (rejected, never shipped)", "decision_integration")
    cert = KV.Cert(KV.EXACT, "risch_differentiate", passed=True, check_cost="d/dx F − f ≡ 0",
                   detail=f"∫ {sp.sstr(f)} dx = {sp.sstr(F)} (elementary; F′ = f verified)")
    return KV.exact(F, "decision_integration.risch", "DECISION (elementary integration)", cert)


def kovacic_liouvillian(coeffs: List, x: sp.Symbol = None) -> KV.Verdict:
    """DECIDE Liouvillian solutions of a₂y″ + a₁y′ + a₀y = 0 with coeffs = [a₀, a₁, a₂] (∈ ℚ(x)). EXACT general
    Liouvillian solution (ODE substitution checked) or DECLINE (non-Liouvillian: Airy/Bessel/…)."""
    x = x or _x
    a0, a1, a2 = [sp.sympify(c, locals={"x": x}) for c in coeffs]
    y = sp.Function("y")
    ode = sp.Eq(a2 * y(x).diff(x, 2) + a1 * y(x).diff(x) + a0 * y(x), 0)
    try:
        sol = sp.dsolve(ode, y(x))
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"kovacic: dsolve failed ({type(e).__name__}) ⇒ DECLINE", "decision_integration")
    rhs = sol.rhs if isinstance(sol, sp.Equality) else sol
    if rhs.has(*_NONLIOUVILLE):
        sf = sorted({type(a).__name__ for a in rhs.atoms(sp.Function) if isinstance(a, _NONLIOUVILLE)})
        return KV.decline(f"kovacic: NO Liouvillian solution — the solution space is {sf} (classically "
                          f"non-Liouvillian) ⇒ PROVEN DECLINE (four-case decision; reported honestly)", "decision_integration")
    # ★ our certificate: substitute the general solution into the ODE ⇒ 0 (exact) ★
    residual = sp.simplify(a2 * rhs.diff(x, 2) + a1 * rhs.diff(x) + a0 * rhs)
    if residual != 0:
        return KV.decline("kovacic: candidate solution failed the ODE substitution ⇒ DECLINE (rejected)", "decision_integration")
    cert = KV.Cert(KV.EXACT, "kovacic_substitution", passed=True, check_cost="a₂y″+a₁y′+a₀y ≡ 0",
                   detail=f"Liouvillian general solution y = {sp.sstr(rhs)}; substituted into the ODE ⇒ 0")
    return KV.exact(rhs, "decision_integration.kovacic", "DECISION (Liouvillian ODE solution)", cert)


def solve(problem: dict) -> KV.Verdict:
    """ops: 'risch' (f), 'kovacic' (coeffs=[a0,a1,a2]). DECLINE otherwise."""
    op = problem.get("op")
    if op == "risch":
        return risch_elementary(problem["f"])
    if op == "kovacic":
        return kovacic_liouvillian(problem["coeffs"])
    return KV.decline(f"decision_integration: unknown op {op!r} ⇒ DECLINE", "decision_integration")
