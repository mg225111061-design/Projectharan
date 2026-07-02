"""
UNIFIED ARSENAL §3 · P8 — Lagrangian / Hamiltonian mechanics + Noether + Lie point symmetry (EXACT where algebraic).
====================================================================================================================
The variational and symmetry structure of mechanics, with re-substitution certificates:
  • EULER–LAGRANGE: d/dt(∂L/∂q̇) − ∂L/∂q = 0. Fixture: harmonic L=½q̇²−½ω²q² ⇒ q̈+ω²q=0.
  • NOETHER (energy): for L with no explicit t, the Hamiltonian H = q̇·∂L/∂q̇ − L is CONSERVED — certified by
    dH/dt ≡ 0 ON-SHELL (substitute the EL equation q̈ = …). For a cyclic coordinate (∂L/∂q=0), the momentum
    p = ∂L/∂q̇ is conserved (dp/dt ≡ 0 mod EL).
  • POISSON brackets {f,g} = ∂_q f ∂_p g − ∂_p f ∂_q g; the canonical {q,p}=1; {f,H} = df/dt.
  • LIE POINT SYMMETRY of a first-order ODE y′=f(x,y): a generator X=ξ∂_x+η∂_y is a symmetry iff the first
    prolongation kills y′−f on-shell: η_x + (η_y−ξ_x)f − ξ_y f² − ξ f_x − η f_y ≡ 0. A DECISION for a GIVEN
    generator (the certificate is that residual → 0); a NON-symmetry has nonzero residual.
Honest scope (§X): EXACT where the algebra closes; INTEGRATING the determining PDE system (finding all symmetries)
is not guaranteed and is flagged — we VERIFY a given generator, we don't claim to find every one.
"""
from __future__ import annotations

import sympy as sp

import kernel_verdict as KV


def euler_lagrange(L: sp.Expr, q: sp.Function, t: sp.Symbol) -> KV.Verdict:
    """The Euler–Lagrange equation of L(q,q̇,t). EXACT (the equation is exact by the variational derivative)."""
    from sympy.calculus.euler import euler_equations
    eqs = euler_equations(L, q(t), t)
    if not eqs:
        return KV.decline("euler_lagrange: no equation produced ⇒ DECLINE", "lagrangian")
    cert = KV.Cert(KV.EXACT, "euler_lagrange", passed=True, check_cost="d/dt(∂L/∂q̇) − ∂L/∂q",
                   detail=f"EL: {sp.sstr(eqs[0])}")
    return KV.exact(eqs[0], "lagrangian.euler_lagrange", "EXACT (variational derivative)", cert)


def energy_conservation(L: sp.Expr, q: sp.Function, t: sp.Symbol) -> KV.Verdict:
    """Noether (time-translation): H = q̇·∂L/∂q̇ − L is conserved — CERTIFIED by dH/dt ≡ 0 on-shell (EL substituted)."""
    qd, qdd = q(t).diff(t), q(t).diff(t, 2)
    # EXPLICIT t-dependence test: freeze q, q̇ as independent dummies, then see if t still appears
    Q, V = sp.symbols("Q V")
    if t in L.subs(qd, V).subs(q(t), Q).free_symbols:
        return KV.decline("energy_conservation: L depends EXPLICITLY on t ⇒ energy not conserved ⇒ DECLINE", "lagrangian")
    H = qd * sp.diff(L, qd) - L
    # EL solved for q̈
    from sympy.calculus.euler import euler_equations
    el = euler_equations(L, q(t), t)[0]
    sol = sp.solve(el, qdd)
    if not sol:
        return KV.decline("energy_conservation: could not solve EL for q̈ ⇒ DECLINE", "lagrangian")
    dHdt = sp.simplify(sp.diff(H, t).subs(qdd, sol[0]))
    if dHdt != 0:
        return KV.decline(f"energy_conservation: dH/dt = {dHdt} ≠ 0 on-shell ⇒ DECLINE", "lagrangian")
    cert = KV.Cert(KV.EXACT, "noether_energy", passed=True, check_cost="dH/dt ≡ 0 mod EL",
                   detail=f"H = q̇·∂L/∂q̇ − L conserved (dH/dt ≡ 0 after substituting q̈={sp.sstr(sol[0])})")
    return KV.exact(sp.simplify(H), "lagrangian.energy_conservation", "EXACT (Noether: energy)", cert)


def poisson_bracket(f: sp.Expr, g: sp.Expr, q: sp.Symbol, p: sp.Symbol) -> sp.Expr:
    return sp.simplify(sp.diff(f, q) * sp.diff(g, p) - sp.diff(f, p) * sp.diff(g, q))


def canonical_poisson() -> KV.Verdict:
    """{q,p}=1, {q,q}=0, {p,p}=0 — the canonical structure, exact."""
    q, p = sp.symbols("q p")
    if poisson_bracket(q, p, q, p) != 1 or poisson_bracket(q, q, q, p) != 0 or poisson_bracket(p, p, q, p) != 0:
        return KV.decline("canonical_poisson: bracket structure wrong ⇒ DECLINE", "lagrangian")
    cert = KV.Cert(KV.EXACT, "canonical_poisson", passed=True, check_cost="∂_q f ∂_p g − ∂_p f ∂_q g",
                   detail="{q,p}=1, {q,q}=0, {p,p}=0 (canonical symplectic structure)")
    return KV.exact("{q,p}=1", "lagrangian.canonical_poisson", "EXACT (Poisson structure)", cert)


def lie_point_symmetry(f: sp.Expr, xi: sp.Expr, eta: sp.Expr, x: sp.Symbol, y: sp.Symbol) -> KV.Verdict:
    """DECIDE whether X = ξ∂_x + η∂_y is a Lie point symmetry of the first-order ODE y′ = f(x,y), via the
    first-prolongation invariance residual η_x + (η_y−ξ_x)f − ξ_y f² − ξ f_x − η f_y. EXACT (symmetry or not)."""
    f, xi, eta = sp.sympify(f), sp.sympify(xi), sp.sympify(eta)
    residual = sp.simplify(
        sp.diff(eta, x) + (sp.diff(eta, y) - sp.diff(xi, x)) * f - sp.diff(xi, y) * f ** 2
        - xi * sp.diff(f, x) - eta * sp.diff(f, y))
    is_sym = residual == 0
    cert = KV.Cert(KV.EXACT, "lie_prolongation", passed=True, check_cost="1st-prolongation residual",
                   detail=f"X=({sp.sstr(xi)})∂_x+({sp.sstr(eta)})∂_y on y′={sp.sstr(f)}: residual={sp.sstr(residual)} "
                          f"⇒ {'SYMMETRY' if is_sym else 'NOT a symmetry'}")
    return KV.exact(is_sym, "lagrangian.lie_point_symmetry", "DECISION (Lie point symmetry of a 1st-order ODE)", cert)


# ── CAP-1 (§AZ): Morales-Ramis — PROVE Hamiltonian NON-integrability via the normal variational equation ──────────
# Capability ledger, NOT a fold-rate item (fold-rate impact: 0). Composes the EXISTING Kovacic decision
# (decision_integration.kovacic_liouvillian) — repo-first, 0 re-implementation. ∀-content = the Morales-Ramis theorem
# applied to an EXACT (symbolic, polynomial) NVE + the EXACT Kovacic case-4 classification; NO z3 ∀-n claim (verifier
# truth §0). ★ Highest value = completing HONEST_DEFER: an UNKNOWN integrability question becomes a *theorem-backed*
# PROVEN-NON-INTEGRABLE decline. Necessary condition only ⇒ "integrable" is NEVER asserted.
def _nve_coeffs_along_axis(V: sp.Expr, x: sp.Symbol, y: sp.Symbol, h: sp.Expr):
    """Normal variational equation coeffs [a0,a1,a2] (∈ ℚ(x)) for the transverse coordinate along the invariant line
    y=0 of H=½(pₓ²+p_y²)+V, parametrised by the energy variable x: 2(h−U)·Y″ − U′·Y′ + V_yy(x,0)·Y = 0, U=V(x,0).
    Requires y=0 invariant (V_y(x,0)≡0). Returns (coeffs, None) or (None, reason)."""
    Vy0 = sp.simplify(sp.diff(V, y).subs(y, 0))
    if Vy0 != 0:
        return None, f"y=0 is NOT an invariant line: V_y(x,0) = {sp.sstr(Vy0)} ≢ 0 (energy reduction invalid)"
    U = sp.simplify(V.subs(y, 0))                              # potential restricted to the invariant line
    a2 = sp.simplify(2 * (h - U))
    if a2 == 0:
        return None, "2(h−U) ≡ 0 (degenerate: no transverse dynamics along this line)"
    a1 = sp.simplify(-sp.diff(U, x))
    a0 = sp.simplify(sp.diff(V, y, 2).subs(y, 0))
    return [a0, a1, a2], None


def morales_ramis_from_nve(coeffs, x: sp.Symbol = None) -> KV.Verdict:
    """Apply the Morales-Ramis decision to a GIVEN normal variational equation a₂Y″+a₁Y′+a₀Y=0 (coeffs=[a0,a1,a2]).
    PROVEN NON-INTEGRABLE iff the NVE has NO Liouvillian solution (Kovacic case 4 ⇒ Galois group SL₂(ℂ), identity
    component non-abelian); else UNDECIDED (necessary condition gives no conclusion — never 'integrable')."""
    x = x or sp.Symbol("x")
    from mathmode import decision_integration as DI
    kov = DI.kovacic_liouvillian(coeffs, x)                    # ★ REUSE the existing certified Kovacic decision
    if kov.status == KV.EXACT:
        return KV.decline("morales_ramis: UNDECIDED — the NVE is Liouvillian (Kovacic case 1–3); the Morales-Ramis "
                          "necessary condition gives NO conclusion (G⁰ may be abelian). Integrability neither proven "
                          "nor refuted (higher-order variational equations would be needed). No overclaim.", "lagrangian")
    if "NO Liouvillian solution" in (kov.reason or ""):        # the *proven* case-4 decline (not a dsolve failure)
        return KV.decline("morales_ramis: ★PROVEN NON-INTEGRABLE — the normal variational equation has NO Liouvillian "
                          "solution (Kovacic case 4 ⇒ differential Galois group SL₂(ℂ), identity component non-abelian); "
                          "by Morales-Ramis the Hamiltonian has NO complete set of meromorphic first integrals in "
                          "involution ⇒ Liouville-NON-INTEGRABLE (theorem-backed PROVEN DECLINE, not a timeout).", "lagrangian")
    return KV.decline(f"morales_ramis: UNDECIDED — could not classify the NVE's Liouvillian solvability "
                      f"({(kov.reason or '')[:70]}) ⇒ no conclusion (no overclaim).", "lagrangian")


def morales_ramis_nonintegrable(V, x: sp.Symbol = None, y: sp.Symbol = None, h=0) -> KV.Verdict:
    """DECIDE non-integrability of H=½(pₓ²+p_y²)+V(x,y) via the Morales-Ramis test along the invariant line y=0.
    PROVEN NON-INTEGRABLE / UNDECIDED / OUT_OF_SCOPE (y=0 not invariant). fold-rate impact: 0 (capability ledger)."""
    x = x or sp.Symbol("x")
    y = y or sp.Symbol("y")
    V = sp.sympify(V, locals={"x": x, "y": y})
    h = sp.sympify(h, locals={"x": x})
    coeffs, reason = _nve_coeffs_along_axis(V, x, y, h)
    if coeffs is None:
        return KV.decline(f"morales_ramis: OUT_OF_SCOPE — {reason}", "lagrangian")
    return morales_ramis_from_nve(coeffs, x)


def solve(problem: dict) -> KV.Verdict:
    """ops: 'euler_lagrange'/'energy' (L string in q(t),q'(t)); 'poisson' (canonical); 'lie' (f,xi,eta);
    'morales_ramis' (V in x,y; optional h) — PROVE non-integrability via the NVE (CAP-1)."""
    op = problem.get("op")
    t = sp.Symbol("t")
    q = sp.Function("q")
    if op == "morales_ramis":
        return morales_ramis_nonintegrable(problem["V"], h=problem.get("h", 0))
    if op in ("euler_lagrange", "energy"):
        L = sp.sympify(problem["L"], locals={"q": q, "t": t})
        return euler_lagrange(L, q, t) if op == "euler_lagrange" else energy_conservation(L, q, t)
    if op == "poisson":
        return canonical_poisson()
    if op == "lie":
        x, y = sp.Symbol("x"), sp.Symbol("y")
        return lie_point_symmetry(sp.sympify(problem["f"], locals={"x": x, "y": y}),
                                  problem["xi"], problem["eta"], x, y)
    return KV.decline(f"lagrangian: unknown op {op!r} ⇒ DECLINE", "lagrangian")
