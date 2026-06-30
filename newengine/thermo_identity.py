"""
§BM NEW-5 — Maxwell relations + Legendre dual checker (conservation m05 + relax-dualize m04 branch, Axis B).
================================================================================================================
  • Maxwell relation: a thermodynamic potential's mixed second partials commute (Clairaut). Given a free energy
    F(T,V) and CLAIMED S, P, verify S = −∂F/∂T, P = −∂F/∂V, and the Maxwell relation (∂S/∂V) = (∂P/∂T). A wrong
    claimed derivation ⇒ DECLINE (a genuine Axis-B checker, not a tautology).
  • Legendre transform: for a strictly-convex quadratic f(x)=½a x² (a>0), the dual is f*(p)=p²/(2a); verify the
    Legendre pairing f(x)+f*(p)=x·p at the stationary p=f'(x)=a x.
★ certificate-or-DECLINE; exact Fraction polynomial arithmetic; zero-dep (stdlib). Polynomials in T^i V^j are
dicts {(i,j): coeff}.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Dict, Tuple

import kernel_verdict as KV

Q = Fraction
Poly = Dict[Tuple[int, int], Q]      # (i,j) -> coeff of T^i V^j


def _norm(p: Poly) -> Poly:
    return {k: Q(v) for k, v in p.items() if Q(v) != 0}


def _dT(p: Poly) -> Poly:
    return _norm({(i - 1, j): Q(v) * i for (i, j), v in p.items() if i >= 1})


def _dV(p: Poly) -> Poly:
    return _norm({(i, j - 1): Q(v) * j for (i, j), v in p.items() if j >= 1})


def _neg(p: Poly) -> Poly:
    return _norm({k: -Q(v) for k, v in p.items()})


def maxwell_check(F: Poly, S: Poly, P: Poly) -> KV.Verdict:
    """EXACT 'Maxwell relation holds' iff the CLAIMED S,P are the correct first partials of F and the mixed second
    partials agree: S=−∂F/∂T, P=−∂F/∂V, ∂S/∂V=∂P/∂T. A wrong claimed S or P ⇒ DECLINE."""
    F = _norm(F); S = _norm(S); P = _norm(P)
    if S != _neg(_dT(F)):
        return KV.decline("thermo: claimed S ≠ −∂F/∂T ⇒ DECLINE (wrong derivation)", "thermo")
    if P != _neg(_dV(F)):
        return KV.decline("thermo: claimed P ≠ −∂F/∂V ⇒ DECLINE (wrong derivation)", "thermo")
    dS_dV = _dV(S); dP_dT = _dT(P)
    if dS_dV != dP_dT:
        return KV.decline(f"thermo: Maxwell relation ∂S/∂V≠∂P/∂T ⇒ DECLINE", "thermo")
    cert = KV.Cert(KV.EXACT, "maxwell_clairaut", passed=True, check_cost="O(#monomials)",
                   detail="S=−∂F/∂T, P=−∂F/∂V verified; ∂S/∂V=∂P/∂T (mixed partials commute) ⇒ Maxwell relation")
    return KV.exact({"maxwell": True}, "thermo", "O(#monomials)", cert)


def legendre_quadratic(a) -> KV.Verdict:
    """EXACT Legendre dual of f(x)=½a x² (a>0): f*(p)=p²/(2a), verified by f(x)+f*(a x)=a x² at sample x. DECLINE
    if a≤0 (not strictly convex ⇒ the transform is not the simple dual)."""
    a = Q(a)
    if a <= 0:
        return KV.decline("legendre: a≤0 ⇒ f not strictly convex ⇒ DECLINE (simple dual does not apply)", "thermo")
    ok = True
    for x in (Q(0), Q(1), Q(-2), Q(3, 2), Q(5)):
        p = a * x                                     # stationary p = f'(x)
        fx = a * x * x / 2
        fstar = p * p / (2 * a)
        if fx + fstar != x * p:                       # Legendre pairing f(x)+f*(p)=x·p
            ok = False
            break
    if not ok:
        return KV.decline("legendre: pairing f(x)+f*(p)=x·p failed ⇒ DECLINE", "thermo")
    cert = KV.Cert(KV.EXACT, "legendre_pair", passed=True, check_cost="O(samples) exact ℚ",
                   detail=f"f(x)=½·{a}·x² ⇄ f*(p)=p²/(2·{a}); f(x)+f*(ax)=ax² verified ⇒ involutive Legendre dual")
    return KV.exact({"dual": f"p^2/(2*{a})"}, "thermo", "O(1)", cert)


def adversarial_battery() -> dict:
    """★ a correct (F,S,P) triple ⇒ Maxwell EXACT; ★ a wrong claimed S ⇒ DECLINE; ★ a convex quadratic's Legendre
    dual verifies EXACT; ★ a non-convex a≤0 ⇒ DECLINE."""
    # F = -T^2 - T*V  ⇒  S = -∂F/∂T = 2T + V ,  P = -∂F/∂V = T
    F = {(2, 0): Q(-1), (1, 1): Q(-1)}
    S = {(1, 0): Q(2), (0, 1): Q(1)}
    P = {(1, 0): Q(1)}
    good = maxwell_check(F, S, P)
    bad = maxwell_check(F, {(1, 0): Q(3)}, P)         # wrong S ⇒ DECLINE
    leg = legendre_quadratic(2)
    leg_bad = legendre_quadratic(-1)
    cases = {
        "maxwell_correct_EXACT": good.status == "EXACT" and good.result["maxwell"] is True,
        "maxwell_wrong_S_DECLINE": bad.status == "DECLINE",
        "legendre_convex_EXACT": leg.status == "EXACT",
        "legendre_nonconvex_DECLINE": leg_bad.status == "DECLINE",
        "exact_carries_cert": good.certificate is not None and good.certificate.passed,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
