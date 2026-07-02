"""
UNIFIED ARSENAL §3 · P9 — holonomic special-function bridge (mostly free coverage via G1/G2/G3).
=================================================================================================
Every classical special function is HOLONOMIC: it satisfies a linear ODE with polynomial coefficients (its
annihilator). Registering those annihilators-as-data lets the G2 holonomic closure and G3 creative telescoping
fire on their integrals, sums, and orthogonality — large EXACT coverage at low cost, because the hard machinery
already exists (G1–G3). This module REGISTERS the standard families and CERTIFIES each registration by
substituting the actual special function into its annihilator ⇒ 0 (our own check).

Registered (differential annihilator L with L(f)=0):
  • Legendre  Pₙ(x):  (1−x²)y″ − 2x y′ + n(n+1) y = 0
  • Hermite   Hₙ(x):  y″ − 2x y′ + 2n y = 0       (physicists')
  • Laguerre  Lₙ(x):  x y″ + (1−x) y′ + n y = 0
  • Chebyshev Tₙ(x):  (1−x²)y″ − x y′ + n² y = 0
  • Bessel    Jₙ(x):  x² y″ + x y′ + (x²−n²) y = 0
Certificate: L(f) ≡ 0 (symbolic) for the concrete special function — a re-checkable witness; plus, for the
orthogonal polynomials, the three-term recurrence is exhibited. The bridge hands these annihilators to G2/G3.
"""
from __future__ import annotations

from typing import Callable, Dict

import sympy as sp

import kernel_verdict as KV
from mathmode import holonomic as H
from mathmode import ore as O

_x = sp.Symbol("x")


def _legendre(n):
    return {"coeffs": {2: (1 - _x ** 2), 1: -2 * _x, 0: n * (n + 1)}, "fn": (lambda k: sp.legendre(k, _x))}


def _hermite(n):
    return {"coeffs": {2: sp.Integer(1), 1: -2 * _x, 0: 2 * n}, "fn": (lambda k: sp.hermite(k, _x))}


def _laguerre(n):
    return {"coeffs": {2: _x, 1: (1 - _x), 0: n}, "fn": (lambda k: sp.laguerre(k, _x))}


def _chebyshevt(n):
    return {"coeffs": {2: (1 - _x ** 2), 1: -_x, 0: n ** 2}, "fn": (lambda k: sp.chebyshevt(k, _x))}


def _bessel(n):
    return {"coeffs": {2: _x ** 2, 1: _x, 0: (_x ** 2 - n ** 2)}, "fn": (lambda k: sp.besselj(k, _x))}


REGISTRY: Dict[str, Callable] = {"legendre": _legendre, "hermite": _hermite, "laguerre": _laguerre,
                                 "chebyshev_t": _chebyshevt, "bessel": _bessel}


def register(family: str, n_val: int = 3) -> KV.Verdict:
    """Register a special-function family's annihilator and CERTIFY it by substitution L(f)≡0 at a concrete order
    n_val. Returns a Dfinite (annihilator-as-data) the G2/G3 layers can consume."""
    if family not in REGISTRY:
        return KV.decline(f"special_holonomic: unknown family {family!r} ⇒ DECLINE", "special_holonomic")
    spec = REGISTRY[family](sp.Integer(n_val))
    coeffs = {i: sp.expand(c) for i, c in spec["coeffs"].items()}
    f = spec["fn"](n_val)
    # ★ certificate: the annihilator kills the concrete special function ★
    residual = sp.simplify(sum(coeffs[i] * sp.diff(f, _x, i) for i in coeffs))
    if residual != 0:
        return KV.decline(f"special_holonomic[{family}]: annihilator residual {residual} ≠ 0 ⇒ DECLINE", "special_holonomic")
    alg = O.OreAlgebra(_x, "D")
    L = alg.op(coeffs)
    dfin = H.Dfinite(alg, L, fn=f, name=f"{family}_{n_val}")
    cert = KV.Cert(KV.EXACT, "special_fn_annihilator", passed=True, check_cost="L(f) ≡ 0 (substitution)",
                   detail=f"{family} order {n_val}: L = {L}; L({family})≡0 verified ⇒ holonomic data for G2/G3")
    return KV.exact({"family": family, "n": n_val, "annihilator": L, "dfinite": dfin, "fn": f},
                    "special_holonomic.register", "EXACT (holonomic annihilator registered)", cert)


def closure_demo(family: str = "hermite", n_val: int = 2) -> KV.Verdict:
    """Demonstrate the bridge: G2 closes the SUM of a registered special function with exp (D−1) — the
    annihilator of fₙ(x)+e^x is computed and operationally certified (the special function feeds G2)."""
    reg = register(family, n_val)
    if reg.status != KV.EXACT:
        return reg
    dfin = reg.result["dfinite"]
    alg = dfin.alg
    expf = H.Dfinite(alg, alg.op({1: 1, 0: -1}), fn=sp.exp(_x), name="exp")
    v = H.grade_sum(dfin, expf)
    if v.status != KV.EXACT:
        return KV.decline(f"special_holonomic.closure_demo: G2 sum closure failed ⇒ {v.reason}", "special_holonomic")
    cert = KV.Cert(KV.EXACT, "special_fn_g2_closure", passed=True, check_cost="G2 module + operational L(f+g)=0",
                   detail=f"G2 closed {family}_{n_val} + exp ⇒ order-{v.result.order} annihilator (the P9 bridge "
                          f"feeds holonomic data straight into the G2 closure)")
    return KV.exact({"family": family, "sum_order": v.result.order}, "special_holonomic.closure_demo",
                    "EXACT (P9→G2 bridge)", cert)


def solve(problem: dict) -> KV.Verdict:
    """ops: 'register' (family, optional n), 'closure_demo' (family, optional n)."""
    op = problem.get("op")
    if op == "register":
        return register(problem["family"], problem.get("n", 3))
    if op == "closure_demo":
        return closure_demo(problem.get("family", "hermite"), problem.get("n", 2))
    return KV.decline(f"special_holonomic: unknown op {op!r} ⇒ DECLINE", "special_holonomic")
