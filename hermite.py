"""
HARAN #17 (Group A) — HERMITE / Horowitz–Ostrogradsky reduction for rational-function integration.
==================================================================================================
∫ A/B dx splits into a RATIONAL part plus a transcendental (logarithmic) part whose denominator is SQUAREFREE.
The Horowitz–Ostrogradsky method computes the split WITHOUT factoring B into irreducibles: with D = gcd(B, B′)
and B* = B/D, write A/B = (C/D)′ + A*/B* and solve for C (deg < deg D) and A* (deg < deg B*) by undetermined
coefficients — a linear system over ℚ. We DRIVE that reduction ourselves (sympy supplies the polynomial ring
arithmetic and the linear solve); the CERTIFICATE is independent and exact: differentiate the rational part and
verify (C/D)′ + A*/B* ≡ A/B as a rational-function identity. A mismatch ⇒ DECLINE (never a wrong antiderivative).
This is the rational part of integration that the Risch decision uses; here it stands alone with its own witness.
"""
from __future__ import annotations

import kernel_verdict as KV


def hermite_reduce(num: str, den: str, var: str = "x"):
    """Return (rational_part, reduced_integrand) with ∫(num/den) = rational_part + ∫ reduced_integrand and the
    reduced integrand having a SQUAREFREE denominator. sympy exprs in `var`. Raises on a non-rational input."""
    import sympy as sp
    x = sp.Symbol(var)
    A = sp.Poly(sp.expand(sp.sympify(num)), x, field=True)
    B = sp.Poly(sp.expand(sp.sympify(den)), x, field=True)
    if B.is_zero:
        raise ValueError("zero denominator")
    # polynomial part (deg A ≥ deg B): integrate directly, reduce to a proper fraction
    poly_q, A = A.div(B)
    rational = sp.integrate(poly_q.as_expr(), x)
    D = B.gcd(B.diff())                                       # ∏ Vᵢ^(i−1)
    Bstar = B.quo(D)                                          # ∏ Vᵢ (squarefree)
    m, k = D.degree(), Bstar.degree()
    if m == 0:                                                # B already squarefree ⇒ no rational part to extract
        return (rational, (A.as_expr(), B.as_expr()))
    H = (Bstar * D.diff()).quo(D)                             # Bstar·D′/D — a polynomial
    cs = sp.symbols(f"_c0:{m}")
    es = sp.symbols(f"_e0:{k}") if k > 0 else ()
    C = sp.Poly(sum(cs[i] * x ** i for i in range(m)), x)
    Astar = sp.Poly(sum(es[i] * x ** i for i in range(k)), x) if k > 0 else sp.Poly(0, x)
    # identity: A = C′·Bstar − C·H + A*·D  (multiply A/B = (C/D)′ + A*/B* through by B = D·Bstar)
    lhs = (C.diff() * Bstar - C * H + Astar * D - A)
    sol = sp.solve(lhs.all_coeffs(), [*cs, *es], dict=True)
    if not sol:
        raise ValueError("Horowitz system unsolvable (not a rational integrand in the expected form)")
    s = sol[0]
    Cv = C.as_expr().subs(s)
    Av = Astar.as_expr().subs(s)
    rational = rational + Cv / D.as_expr()
    return (sp.simplify(rational), (sp.expand(Av), Bstar.as_expr()))


def hermite_reduce_grade(num: str, den: str, var: str = "x") -> KV.Verdict:
    """Hermite/Horowitz reduction of ∫(num/den)d`var`, EXACT, CERTIFIED by differentiation: the returned
    rational_part′ + reduced_integrand must equal num/den as a rational-function identity (sympy-simplified to 0).
    The reduced integrand's denominator is SQUAREFREE. Non-rational / zero-denominator input ⇒ honest DECLINE."""
    import sympy as sp
    x = sp.Symbol(var)
    try:
        rational, (rn, rd) = hermite_reduce(num, den, var)
        integrand = sp.sympify(num) / sp.sympify(den)
        reduced = rn / rd
        # ★ certificate: d/dx(rational) + reduced ≡ integrand ★
        if sp.simplify(sp.diff(rational, x) + reduced - integrand) != 0:
            return KV.decline("hermite: (rational)′ + reduced ≢ integrand ⇒ DECLINE (bug guard)", "hermite")
        # the reduced denominator is squarefree (gcd with its derivative is a constant)
        rdp = sp.Poly(sp.expand(rd), x)
        squarefree = rdp.gcd(rdp.diff()).degree() == 0
    except (ValueError, ZeroDivisionError, TypeError, sp.SympifyError, sp.PolynomialError) as e:
        return KV.decline(f"hermite: {e} ⇒ DECLINE (not a rational integrand)", "hermite")
    cert = KV.Cert(KV.EXACT, "hermite_differentiation", passed=True, check_cost="symbolic diff + identity-to-0",
                   detail=f"∫({num})/({den}) = [{sp.sstr(rational)}] + ∫ ({sp.sstr(rn)})/({sp.sstr(rd)}); "
                          f"(rational)′ + reduced ≡ integrand (verified); reduced denom squarefree={squarefree}")
    return KV.exact({"rational_part": sp.sstr(rational), "reduced_num": sp.sstr(rn), "reduced_den": sp.sstr(rd),
                     "squarefree_reduced_denom": squarefree}, "hermite", "Horowitz–Ostrogradsky", cert)
