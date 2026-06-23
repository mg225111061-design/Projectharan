"""
MATH-Ascent §B4 (arsenal) — CALCULUS: symbolic integration verified by DIFFERENTIATION (the self-check).
========================================================================================================
Integration is the hard direction; differentiation is the easy, algorithmic, EXACT direction. So an
antiderivative is its own certificate: ∫ f dx = F is EXACT iff  d/dx F − f ≡ 0  (verified symbolically, with an
independent finite-difference numeric cross-check). A definite integral uses the Fundamental Theorem,
∫ₐᵇ f = F(b) − F(a), on that VERIFIED antiderivative (plus a numeric quadrature sanity check). Where sympy returns
an UNEVALUATED Integral (no closed form it can find) ⇒ honest DECLINE — never a fabricated antiderivative. This is
the analysis companion to differential.py: the model proposes, differentiation proves.
"""
from __future__ import annotations

import sympy as sp

import kernel_verdict as KV


def _expr(e, x):
    return sp.sympify(e, locals={str(x): x}) if isinstance(e, str) else e


def _num_check_deriv(F, f, x, pts=(sp.Rational(1, 3), sp.Rational(6, 5), sp.Integer(2), sp.Rational(11, 4))) -> bool:
    """Independent finite-difference cross-check that F' ≈ f at several points (guards a bad symbolic simplify)."""
    h = sp.Rational(1, 10 ** 6)
    ok = 0
    tot = 0
    for p in pts:
        try:
            fd = (F.subs(x, p + h) - F.subs(x, p - h)) / (2 * h)
            target = f.subs(x, p)
            if not (fd.is_finite is False or target.is_finite is False):
                tot += 1
                if abs(complex(sp.N(fd - target))) < 1e-3:
                    ok += 1
        except Exception:                                    # noqa: BLE001
            continue
    return tot >= 2 and ok == tot


def integrate_grade(f, x=None) -> KV.Verdict:
    """∫ f dx (indefinite). EXACT iff the antiderivative F differentiates back to f (symbolic ∧ numeric). No
    closed form sympy can find (an unevaluated Integral) ⇒ honest DECLINE."""
    x = x or sp.Symbol("x")
    fe = _expr(f, x)
    try:
        F = sp.integrate(fe, x)
    except Exception as e:                                   # noqa: BLE001
        return KV.decline(f"integrate: failed ({type(e).__name__}) ⇒ DECLINE", "calculus.integrate")
    if F.has(sp.Integral):                                   # sympy could not find a closed form
        return KV.decline("integrate: no closed-form antiderivative found (unevaluated Integral) ⇒ DECLINE",
                          "calculus.integrate")
    if sp.simplify(sp.diff(F, x) - fe) != 0 or not _num_check_deriv(F, fe, x):   # ★ d/dx F = f, the certificate ★
        return KV.decline("integrate: antiderivative failed the differentiation check ⇒ DECLINE", "calculus.integrate")
    cert = KV.Cert(KV.EXACT, "integral_diff_check", passed=True, check_cost="symbolic d/dx + numeric finite-diff",
                   detail=f"∫ f dx = {sp.sstr(F)} (+C); d/dx of it ≡ f, verified")
    return KV.exact(F, "calculus.integrate", "antiderivative (verified)", cert)


def definite_integral_grade(f, x, a, b) -> KV.Verdict:
    """∫ₐᵇ f dx via the FTC on a VERIFIED antiderivative, cross-checked against numeric quadrature. No closed-form
    antiderivative ⇒ honest DECLINE."""
    x = x or sp.Symbol("x")
    fe = _expr(f, x)
    ind = integrate_grade(fe, x)
    if ind.status != KV.EXACT:
        return KV.decline("definite_integral: no verified antiderivative ⇒ DECLINE", "calculus.definite")
    F = ind.result
    val = sp.simplify(F.subs(x, b) - F.subs(x, a))
    try:                                                     # numeric quadrature sanity cross-check
        num = float(sp.N(sp.Integral(fe, (x, a, b))))
        if abs(float(sp.N(val)) - num) > 1e-4:
            return KV.decline("definite_integral: FTC value disagrees with quadrature ⇒ DECLINE", "calculus.definite")
    except Exception:                                        # noqa: BLE001
        pass
    cert = KV.Cert(KV.EXACT, "ftc_verified_antiderivative", passed=True, check_cost="verified F + FTC + quadrature",
                   detail=f"∫_{{{a}}}^{{{b}}} f = F(b)−F(a) = {sp.sstr(val)} (antiderivative diff-verified; FTC)")
    return KV.exact(val, "calculus.definite", "FTC on verified antiderivative", cert)


def differentiate_grade(f, x=None) -> KV.Verdict:
    """d/dx f (EXACT — differentiation is algorithmic). Certificate: a finite-difference numeric cross-check at
    several points confirms the symbolic derivative (guards a wrong result)."""
    x = x or sp.Symbol("x")
    fe = _expr(f, x)
    d = sp.diff(fe, x)
    # cross-check: (f(p+h)−f(p−h))/2h ≈ d(p) at several points
    h = sp.Rational(1, 10 ** 6)
    pts = [sp.Rational(1, 3), sp.Rational(7, 5), sp.Integer(2), sp.Rational(11, 4)]
    ok = tot = 0
    for p in pts:
        try:
            fd = (fe.subs(x, p + h) - fe.subs(x, p - h)) / (2 * h)
            tgt = d.subs(x, p)
            if not (fd.is_finite is False or tgt.is_finite is False):
                tot += 1
                ok += int(abs(complex(sp.N(fd - tgt))) < 1e-3)
        except Exception:                                    # noqa: BLE001
            continue
    if tot < 2 or ok != tot:
        return KV.decline("differentiate: finite-difference cross-check failed ⇒ DECLINE", "calculus.diff")
    cert = KV.Cert(KV.EXACT, "derivative_fd_check", passed=True, check_cost="symbolic diff + finite-difference",
                   detail=f"d/dx f = {sp.sstr(d)} (finite-difference-confirmed)")
    return KV.exact(d, "calculus.diff", "exact derivative", cert)


def taylor_grade(f, a, n: int, x=None) -> KV.Verdict:
    """Order-n Taylor polynomial of f around x=a. Certificate: T⁽ᵏ⁾(a) = f⁽ᵏ⁾(a) for k=0..n (verified by
    differentiation — the polynomial matches f to order n). A singularity at a (a derivative blows up) ⇒ DECLINE."""
    x = x or sp.Symbol("x")
    fe = _expr(f, x)
    a = sp.nsimplify(a)
    try:
        T = sp.series(fe, x, a, n + 1).removeO()
    except Exception as e:                                   # noqa: BLE001
        return KV.decline(f"taylor: series failed ({type(e).__name__}) ⇒ DECLINE", "calculus.taylor")
    if T.has(sp.S.Infinity, sp.S.NegativeInfinity, sp.zoo, sp.nan):
        return KV.decline(f"taylor: singularity at x={a} ⇒ DECLINE", "calculus.taylor")
    fd = Td = fe, T
    for k in range(n + 1):                                    # ★ T⁽ᵏ⁾(a) = f⁽ᵏ⁾(a), k=0..n (matches to order n) ★
        try:
            if sp.simplify(sp.diff(fe, x, k).subs(x, a) - sp.diff(T, x, k).subs(x, a)) != 0:
                return KV.decline(f"taylor: order-{k} coefficient mismatch ⇒ DECLINE", "calculus.taylor")
        except Exception:                                    # noqa: BLE001
            return KV.decline(f"taylor: f is not {k}-times differentiable at {a} ⇒ DECLINE", "calculus.taylor")
    cert = KV.Cert(KV.EXACT, "taylor_derivative_match", passed=True, check_cost=f"{n+1} derivative matches at a",
                   detail=f"order-{n} Taylor of f at x={a}: {sp.sstr(T)}; T⁽ᵏ⁾({a})=f⁽ᵏ⁾({a}) ∀k≤{n}")
    return KV.exact(T, "calculus.taylor", "exact Taylor polynomial", cert)


def solve(problem: dict) -> KV.Verdict:
    op = problem.get("op")
    x = sp.Symbol(problem.get("var", "x"))
    if op == "integrate":
        return integrate_grade(problem["f"], x)
    if op == "definite_integral":
        return definite_integral_grade(problem["f"], x, problem["a"], problem["b"])
    if op == "differentiate":
        return differentiate_grade(problem["f"], x)
    if op == "taylor":
        return taylor_grade(problem["f"], problem.get("a", 0), problem.get("n", 5), x)
    return KV.decline(f"calculus: unknown op {op!r} ⇒ DECLINE", "calculus")
