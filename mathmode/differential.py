"""
MATH-Ascent §B4 (arsenal) — DIFFERENTIAL EQUATIONS: closed-form ODE solving, verified by back-substitution.
==========================================================================================================
sympy's `dsolve` searches for a closed-form solution; we do NOT take its word. The EXACT grade is licensed by
SUBSTITUTING the candidate solution back into the ODE and checking the residual is identically 0 — `checkodesol`
performs exactly that substitution-and-simplify, and we additionally spot-check it numerically at several (x,
constants) points (an independent cross-check). A solution that substitutes to 0 IS a proof it solves the ODE.
Where no closed form exists (a generic nonlinear ODE) `dsolve` raises / returns unevaluated ⇒ honest DECLINE —
never a fabricated solution. This is the analysis-side companion to the algebraic arsenal: the certificate is the
back-substitution, not the solver's say-so.
"""
from __future__ import annotations

import sympy as sp

import kernel_verdict as KV


def _numeric_crosscheck(ode_expr: "sp.Expr", sol: "sp.Eq", x: "sp.Symbol", y) -> bool:
    """Independent of checkodesol: plug the solution (with constants set to small values) into lhs−rhs and confirm
    it is ~0 at several x — catches a checkodesol that simplified incorrectly."""
    try:
        consts = sorted(sol.free_symbols - {x}, key=str)
        subs0 = {c: sp.Integer(i + 1) for i, c in enumerate(consts)}
        expr = ode_expr.subs(y(x), sol.rhs)
        # substitute derivatives explicitly (sympy resolves Derivative(sol.rhs) on doit)
        expr = expr.doit().subs(subs0)
        for xv in (sp.Rational(1, 3), sp.Rational(7, 5), sp.Integer(2)):
            val = complex(expr.subs(x, xv).evalf())
            if abs(val) > 1e-6:
                return False
        return True
    except Exception:                                        # noqa: BLE001
        return False


def solve_ode_grade(ode, y=None, x=None) -> KV.Verdict:
    """Solve an ODE in closed form, EXACT only if the solution back-substitutes to 0 (checkodesol ∧ numeric
    cross-check). No closed form ⇒ honest DECLINE."""
    x = x or sp.Symbol("x")
    y = y or sp.Function("y")
    if isinstance(ode, str):
        ode = sp.sympify(ode, locals={str(x): x, "y": y})
    if not isinstance(ode, sp.Equality):
        ode = sp.Eq(ode, 0)
    try:
        sol = sp.dsolve(ode, y(x))
    except (NotImplementedError, Exception) as e:            # noqa: BLE001
        return KV.decline(f"ode: no closed-form solution found ({type(e).__name__}) ⇒ DECLINE", "differential")
    sols = sol if isinstance(sol, (list, tuple)) else [sol]
    ode_expr = ode.lhs - ode.rhs
    for s in sols:
        ok = sp.checkodesol(ode, s)                          # ★ the substitution proof ★
        verified = (isinstance(ok, tuple) and ok[0] is True) or ok is True
        if not (verified and _numeric_crosscheck(ode_expr, s, x, y)):
            return KV.decline(f"ode: candidate did not back-substitute to 0 ⇒ DECLINE", "differential")
    cert = KV.Cert(KV.EXACT, "ode_backsubstitution", passed=True, check_cost="checkodesol + numeric spot-check",
                   detail=f"solution(s) substitute into the ODE with residual 0 (verified): "
                          f"{'; '.join(sp.sstr(s) for s in sols)}")
    return KV.exact(sols if len(sols) > 1 else sols[0], "differential.ode", "closed form (verified)", cert)


def solve(problem: dict) -> KV.Verdict:
    op = problem.get("op")
    x = sp.Symbol(problem.get("var", "x"))
    y = sp.Function(problem.get("func", "y"))
    if op == "ode":
        return solve_ode_grade(problem["ode"], y, x)
    return KV.decline(f"differential: unknown op {op!r} ⇒ DECLINE", "differential")
