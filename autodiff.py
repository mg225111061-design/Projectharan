"""
HARAN #28 (Group B) — EXACT automatic differentiation via DUAL NUMBERS (forward mode).
======================================================================================
A dual number is a + b·ε with ε² = 0. Arithmetic on duals propagates (value, derivative) by the chain rule
exactly: (a+bε)(c+dε) = ac + (ad+bc)ε, so f(x₀ + 1·ε) = f(x₀) + f'(x₀)·ε. Evaluating a polynomial/rational
expression on duals therefore yields the EXACT derivative — no finite-difference error, no symbolic blow-up. We
own the forward pass (a `Dual` class over `Fraction`, walking the expression tree ourselves); sympy's symbolic
`diff` is used ONLY as an INDEPENDENT re-check (decision-procedure-correct, our certificate). Scope is exact over
ℚ: polynomial/rational functions with integer powers at a rational point — anything outside (non-integer power,
a transcendental whose value is not rational) is an honest DECLINE (the *value* would not be exact), never faked.
"""
from __future__ import annotations

from fractions import Fraction as Fr
from typing import Dict, List, Tuple

import kernel_verdict as KV


class Dual:
    """value v plus derivative-seed d; arithmetic carries the chain rule exactly over ℚ."""
    __slots__ = ("v", "d")

    def __init__(self, v, d=0):
        self.v = Fr(v)
        self.d = Fr(d)

    def __add__(s, o):
        o = _D(o)
        return Dual(s.v + o.v, s.d + o.d)

    __radd__ = __add__

    def __sub__(s, o):
        o = _D(o)
        return Dual(s.v - o.v, s.d - o.d)

    def __rsub__(s, o):
        o = _D(o)
        return Dual(o.v - s.v, o.d - s.d)

    def __neg__(s):
        return Dual(-s.v, -s.d)

    def __mul__(s, o):
        o = _D(o)
        return Dual(s.v * o.v, s.v * o.d + s.d * o.v)             # product rule

    __rmul__ = __mul__

    def __truediv__(s, o):
        o = _D(o)
        if o.v == 0:
            raise ZeroDivisionError("dual divide by a zero-value denominator")
        return Dual(s.v / o.v, (s.d * o.v - s.v * o.d) / (o.v * o.v))   # quotient rule

    def __rtruediv__(s, o):
        return _D(o).__truediv__(s)

    def __pow__(s, k: int):
        if not isinstance(k, int):
            raise ValueError("dual power must be an integer exponent (exact scope)")
        if k == 0:
            return Dual(1, 0)
        if s.v == 0 and k < 0:
            raise ZeroDivisionError("0 to a negative power")
        return Dual(s.v ** k, k * s.v ** (k - 1) * s.d)            # power rule


def _D(o):
    return o if isinstance(o, Dual) else Dual(o, 0)


def _to_fr(num) -> Fr:
    import sympy as sp
    r = sp.nsimplify(num) if not num.is_Rational else num
    if not r.is_Rational:
        raise ValueError(f"non-rational value {num} (outside the EXACT scope)")
    return Fr(int(r.p), int(r.q))


def _eval_dual(expr, seeds: Dict):
    """Walk a sympy expression with Dual arithmetic. `seeds` maps each Symbol → its Dual (value, seed)."""
    import sympy as sp
    if expr in seeds:
        return seeds[expr]
    if expr.is_Symbol:
        raise ValueError(f"unseeded symbol {expr}")
    if expr.is_Number:
        return Dual(_to_fr(expr), 0)
    if expr.is_Add:
        acc = Dual(0, 0)
        for a in expr.args:
            acc = acc + _eval_dual(a, seeds)
        return acc
    if expr.is_Mul:
        acc = Dual(1, 0)
        for a in expr.args:
            acc = acc * _eval_dual(a, seeds)
        return acc
    if expr.is_Pow:
        base, exp = expr.args
        if not exp.is_Integer:
            raise ValueError(f"non-integer power {exp} (outside the EXACT scope)")
        return _eval_dual(base, seeds) ** int(exp)
    raise ValueError(f"unsupported node {type(expr).__name__} (outside the EXACT polynomial/rational scope)")


def gradient(expr_str: str, point: Dict[str, object]) -> Tuple[Fr, Dict[str, Fr]]:
    """Forward-mode dual-number AD: return (value, {var: ∂f/∂var}) of `expr_str` at `point` (rational coords),
    EXACT over ℚ. One dual pass per variable (seed that variable's ε=1, the rest 0)."""
    import sympy as sp
    syms = {n: sp.Symbol(n) for n in point}
    expr = sp.sympify(expr_str, locals=syms)
    pf = {n: Fr(point[n]) if not isinstance(point[n], Fr) else point[n] for n in point}
    val = None
    grad: Dict[str, Fr] = {}
    for n in point:
        seeds = {syms[m]: Dual(pf[m], 1 if m == n else 0) for m in point}
        out = _eval_dual(expr, seeds)
        val = out.v
        grad[n] = out.d
    return (val if val is not None else _to_fr(expr), grad)


def autodiff_grade(expr_str: str, point: Dict[str, object]) -> KV.Verdict:
    """EXACT gradient of `expr_str` at `point` by forward-mode dual numbers, CROSS-CHECKED against sympy's
    independent symbolic ∂/∂x (an entirely different algorithm). EXACT iff both the value and every partial agree
    and are rational; an unsupported node / non-rational value ⇒ honest DECLINE (outside the exact scope)."""
    import sympy as sp
    try:
        syms = {n: sp.Symbol(n) for n in point}
        expr = sp.sympify(expr_str, locals=syms)
        pf = {n: (point[n] if isinstance(point[n], Fr) else Fr(point[n])) for n in point}
        val, grad = gradient(expr_str, point)
    except (ValueError, ZeroDivisionError, TypeError, sp.SympifyError) as e:
        return KV.decline(f"autodiff: {e} ⇒ DECLINE (outside the EXACT polynomial/rational scope)", "autodiff")
    # ── independent re-check: symbolic differentiation (a DIFFERENT algorithm) must agree, exactly ──
    subs = {syms[n]: sp.Rational(pf[n].numerator, pf[n].denominator) for n in point}
    try:
        v_sym = sp.Rational(sp.nsimplify(expr.subs(subs)))
        if Fr(int(v_sym.p), int(v_sym.q)) != val:
            return KV.decline("autodiff: dual value ≠ symbolic value ⇒ DECLINE (bug guard)", "autodiff")
        for n in point:
            ds = sp.diff(expr, syms[n]).subs(subs)
            ds = sp.Rational(sp.nsimplify(ds))
            if Fr(int(ds.p), int(ds.q)) != grad[n]:
                return KV.decline(f"autodiff: ∂/∂{n} dual ≠ symbolic ⇒ DECLINE (bug guard)", "autodiff")
    except (ValueError, TypeError) as e:
        return KV.decline(f"autodiff: value not rational at the point ({e}) ⇒ DECLINE", "autodiff")
    cert = KV.Cert(KV.EXACT, "autodiff_dual_vs_symbolic", passed=True, check_cost="O(nodes·vars) + symbolic recheck",
                   detail=f"∇({expr_str}) at {point} = {grad} (value {val}); forward-mode dual ≡ symbolic ∂/∂x "
                          f"(two independent algorithms agree, exact over ℚ)")
    return KV.exact({"value": val, "grad": grad}, "autodiff", "forward-mode dual numbers", cert)
