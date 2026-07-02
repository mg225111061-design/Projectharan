"""
NATIVE ARSENAL — Gosper's algorithm for indefinite hypergeometric summation (creative-telescoping base), in-repo.
================================================================================================================
Given a hypergeometric term t(n) (t(n+1)/t(n) is rational), decide whether Σ t is itself hypergeometric (Gosper-
summable) and, if so, produce the antidifference S(n) with S(n+1) − S(n) = t(n). Mechanisms ⑤ ⑨ ⑬. The Gosper
LOGIC is driven here (GP normal form via the dispersion set, then the polynomial key equation); sympy supplies only
the underlying polynomial ring arithmetic (as in groebner.py).
★ CERTIFICATE (per-instance, §7): the returned S is re-checked by SIMPLIFYING S(n+1) − S(n) − t(n) to 0 — a wrong
  antidifference can never pass. Not Gosper-summable (no polynomial solution) ⇒ honest DECLINE.
"""
from __future__ import annotations

from typing import Optional

import kernel_verdict as KV


def gosper_antidifference(t, n):
    """Return S with S(n+1)−S(n)=t(n), or None if t is not Gosper-summable. `t` a sympy expr, `n` a sympy Symbol."""
    import sympy as sp
    t = sp.simplify(t)
    if t == 0:
        return sp.Integer(0)
    r = sp.simplify(t.subs(n, n + 1) / t)
    r = sp.together(r)
    num, den = sp.fraction(r)
    num, den = sp.Poly(num, n), sp.Poly(den, n)
    # Gosper–Petkovšek form: r(n) = (a/b)·(c(n+1)/c(n)), gcd(a(n), b(n+h)) = 1 for all integer h ≥ 0.
    a, b, c = num, den, sp.Poly(1, n)
    h = sp.Symbol("_h", integer=True, nonnegative=True)
    res = sp.resultant(a.as_expr(), b.as_expr().subs(n, n + h), n)
    roots = []
    try:
        for rt in sp.Poly(res, h).all_roots():
            if rt.is_integer and rt >= 0:
                roots.append(int(rt))
    except Exception:  # noqa: BLE001
        roots = [int(s) for s in sp.solve(res, h) if getattr(s, "is_integer", False) and s >= 0]
    for j in sorted(set(roots)):
        g = sp.Poly(sp.gcd(a.as_expr(), b.as_expr().subs(n, n + j)), n)
        if g.degree() > 0:
            a = sp.Poly(sp.quo(a.as_expr(), g.as_expr(), n), n)
            b = sp.Poly(sp.quo(b.as_expr(), g.as_expr().subs(n, n - j), n), n)
            c = sp.Poly((c.as_expr() * sp.prod([g.as_expr().subs(n, n - i) for i in range(j)])), n)
    # key equation: a(n)·x(n+1) − b(n−1)·x(n) = c(n), solve for a polynomial x of bounded degree
    deg = max(0, c.degree() - max(a.degree(), b.degree()) + 1) + 2
    coeffs = sp.symbols(f"_x0:{deg + 1}")
    x = sum(coeffs[i] * n ** i for i in range(deg + 1))
    eq = sp.expand(a.as_expr() * x.subs(n, n + 1) - b.as_expr().subs(n, n - 1) * x - c.as_expr())
    sol = sp.solve(sp.Poly(eq, n).all_coeffs(), coeffs, dict=True)
    if not sol:
        return None
    xsol = x.subs(sol[0])
    if any(co in xsol.free_symbols for co in coeffs):        # underdetermined free params → set to 0
        xsol = xsol.subs({co: 0 for co in coeffs})
    S = sp.simplify(b.as_expr().subs(n, n - 1) / c.as_expr() * xsol * t)
    return sp.simplify(S)


def telescope_grade(expr_str: str, var: str = "n") -> KV.Verdict:
    """Decide Gosper-summability of a hypergeometric term given as a string; EXACT with the antidifference S
    (re-verified S(n+1)−S(n)=t), else honest DECLINE."""
    import sympy as sp
    n = sp.Symbol(var)
    try:
        t = sp.sympify(expr_str, locals={var: n})
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"telescope: parse error {e}", "native_telescope")
    try:
        S = gosper_antidifference(t, n)
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"telescope: Gosper failed ({type(e).__name__}) ⇒ DECLINE", "native_telescope")
    if S is None:
        return KV.decline(f"telescope: {expr_str} is NOT Gosper-summable (no hypergeometric antidifference) ⇒ DECLINE",
                          "native_telescope")
    check = sp.simplify(S.subs(n, n + 1) - S - t)            # ★ certificate: S(n+1)−S(n) == t(n) ★
    if check != 0:
        return KV.decline(f"telescope: antidifference re-check S(n+1)−S(n)−t = {check} ≠ 0 ⇒ DECLINE (no overclaim)",
                          "native_telescope")
    cert = KV.Cert(KV.EXACT, "gosper_antidifference", passed=True, check_cost="simplify S(n+1)−S(n)−t(n) to 0",
                   detail=f"Σ {expr_str} = {sp.sstr(S)} + C; verified S(n+1)−S(n)=t(n)")
    return KV.exact({"antidifference": sp.sstr(S)}, "native_telescope", "Gosper's algorithm", cert)


def m_telescope_grade(x) -> KV.Verdict:
    """Route {"telescope": "t(n) expr", "var": "n"} → indefinite hypergeometric summation."""
    if isinstance(x, dict) and "telescope" in x:
        return telescope_grade(x["telescope"], x.get("var", "n"))
    return KV.decline("native_telescope: expected {telescope: expr}", "native_telescope")
