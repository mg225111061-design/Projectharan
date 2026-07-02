"""
MATH-Ascent §3 (arsenal) — SCIENCE / ENGINEERING: dimensional analysis & unit checking (EXACT, self-certifying).
================================================================================================================
Physical correctness has a cheap, EXACT certificate: DIMENSIONAL CONSISTENCY. Every quantity is a vector of
exponents over the 7 SI base dimensions [M, L, T, I, Θ, N, J]; a product adds the vectors, a power scales them,
and a SUM requires equal vectors. An equation is dimensionally valid iff both sides resolve to the SAME exponent
vector — an exact, decidable check over ℚ⁷. This catches a whole class of wrong physical formulas (E = m·v is
M·L·T⁻¹, not energy M·L²·T⁻²) before any number is computed. We use sympy only to PARSE the expression tree; the
dimension algebra and the verdict are ours. Consistent ⇒ EXACT (the equal vectors are the certificate);
inconsistent ⇒ honest DECLINE with the mismatch (never a fabricated "it's fine"). Derivation of a result's units
is likewise EXACT. Numeric physical prediction with measurement error would be PROBABILISTIC(ε,δ) — out of scope
here; this module is the exact dimensional layer.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Dict, List, Optional, Tuple

import sympy as sp

import kernel_verdict as KV

_BASE = ("M", "L", "T", "I", "Θ", "N", "J")          # mass, length, time, current, temperature, amount, luminous
_ZERO = (Fraction(0),) * 7


def _vec(**kw) -> Tuple[Fraction, ...]:
    return tuple(Fraction(kw.get(b, 0)) for b in _BASE)


# named physical quantities → their dimension vectors (the registry the bindings draw on)
DIM: Dict[str, Tuple[Fraction, ...]] = {
    "dimensionless": _ZERO, "mass": _vec(M=1), "length": _vec(L=1), "time": _vec(T=1),
    "current": _vec(I=1), "temperature": _vec(Θ=1), "amount": _vec(N=1),
    "area": _vec(L=2), "volume": _vec(L=3), "velocity": _vec(L=1, T=-1), "speed": _vec(L=1, T=-1),
    "acceleration": _vec(L=1, T=-2), "force": _vec(M=1, L=1, T=-2), "energy": _vec(M=1, L=2, T=-2),
    "work": _vec(M=1, L=2, T=-2), "power": _vec(M=1, L=2, T=-3), "pressure": _vec(M=1, L=-1, T=-2),
    "momentum": _vec(M=1, L=1, T=-1), "frequency": _vec(T=-1), "charge": _vec(I=1, T=1),
    "voltage": _vec(M=1, L=2, T=-3, I=-1), "density": _vec(M=1, L=-3),
}


def _add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def _scale(a, k):
    return tuple(x * k for x in a)


class _Inconsistent(Exception):
    pass


def _dim(expr: "sp.Expr", binding: Dict[str, Tuple[Fraction, ...]]) -> Tuple[Fraction, ...]:
    """The dimension vector of a sympy expression under a symbol→vector binding. A sum of unequal dimensions
    raises _Inconsistent (the honest failure)."""
    if expr.is_Number:
        return _ZERO                                          # pure numbers are dimensionless
    if expr.is_Symbol:
        name = str(expr)
        if name not in binding:
            raise _Inconsistent(f"unbound symbol {name}")
        return binding[name]
    if expr.is_Add:
        ds = [_dim(t, binding) for t in expr.args]
        if any(d != ds[0] for d in ds):
            raise _Inconsistent(f"sum of unequal dimensions: {ds}")
        return ds[0]
    if expr.is_Mul:
        out = _ZERO
        for t in expr.args:
            out = _add(out, _dim(t, binding))
        return out
    if expr.is_Pow:
        base, e = expr.args
        if not e.is_Number:
            raise _Inconsistent(f"non-numeric exponent {e}")
        return _scale(_dim(base, binding), Fraction(sp.Rational(e).p, sp.Rational(e).q))
    if expr.is_Function:                                      # sqrt etc. handled via Pow; other funcs ⇒ dimensionless arg
        raise _Inconsistent(f"unsupported function {expr.func}")
    raise _Inconsistent(f"unsupported node {expr}")


def _resolve(binding: Dict[str, str]) -> Dict[str, Tuple[Fraction, ...]]:
    out = {}
    for sym, qty in binding.items():
        if qty not in DIM:
            raise _Inconsistent(f"unknown quantity {qty!r}")
        out[sym] = DIM[qty]
    return out


def _fmt(v) -> str:
    parts = [f"{b}^{x}" if x != 1 else b for b, x in zip(_BASE, v) if x != 0]
    return "·".join(parts) if parts else "1 (dimensionless)"


def consistency_grade(equation: str, binding: Dict[str, str]) -> KV.Verdict:
    """Verify an equation 'lhs = rhs' is DIMENSIONALLY consistent under a symbol→quantity binding.
    EXACT (equal exponent vectors) or honest DECLINE (mismatch / inconsistent sum)."""
    if "=" not in equation:
        return KV.decline("dimensional: need an equation 'lhs = rhs' ⇒ DECLINE", "science.dimension")
    lhs_s, rhs_s = equation.split("=", 1)
    syms = {s: sp.Symbol(s) for s in binding}
    try:
        b = _resolve(binding)
        lhs = _dim(sp.sympify(lhs_s, locals=syms), b)
        rhs = _dim(sp.sympify(rhs_s, locals=syms), b)
    except (_Inconsistent, Exception) as e:                  # noqa: BLE001
        return KV.decline(f"dimensional: {e} ⇒ DECLINE", "science.dimension")
    if lhs != rhs:
        return KV.decline(f"dimensional: LHS [{_fmt(lhs)}] ≠ RHS [{_fmt(rhs)}] ⇒ inconsistent ⇒ DECLINE",
                          "science.dimension")
    cert = KV.Cert(KV.EXACT, "dimensional_consistency", passed=True, check_cost="O(nodes) exponent-vector algebra",
                   detail=f"both sides resolve to [{_fmt(lhs)}] over the 7 SI base dimensions (exact)")
    return KV.exact(lhs, "science.dimension", "exact dimensional check", cert)


def derive_dimension_grade(expr: str, binding: Dict[str, str]) -> KV.Verdict:
    """Derive the dimension (units) of a composed expression. EXACT, or DECLINE on an inconsistent sum/unknown."""
    syms = {s: sp.Symbol(s) for s in binding}
    try:
        v = _dim(sp.sympify(expr, locals=syms), _resolve(binding))
    except (_Inconsistent, Exception) as e:                  # noqa: BLE001
        return KV.decline(f"derive_dimension: {e} ⇒ DECLINE", "science.dimension")
    cert = KV.Cert(KV.EXACT, "dimension_derivation", passed=True, check_cost="O(nodes)",
                   detail=f"dimension = [{_fmt(v)}] (exact exponent-vector algebra)")
    return KV.exact(v, "science.dimension", "exact dimensional derivation", cert)


def solve(problem: dict) -> KV.Verdict:
    op = problem.get("op")
    if op == "dimension_check":
        return consistency_grade(problem["equation"], problem["binding"])
    if op == "derive_dimension":
        return derive_dimension_grade(problem["expr"], problem["binding"])
    return KV.decline(f"science_engineering: unknown op {op!r} ⇒ DECLINE", "science_engineering")
