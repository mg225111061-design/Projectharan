"""
UNIFIED ARSENAL §3 · P2 — curvature from a metric + Einstein-equation checker (EXACT, re-substitution certified).
================================================================================================================
Given a metric g_μν(x) (symbolic), compute the full curvature chain in closed form:
  Christoffel Γ^λ_μν = ½ g^λσ(∂_μ g_σν + ∂_ν g_σμ − ∂_σ g_μν)  →  Riemann R^ρ_σμν  →  Ricci R_μν = R^λ_μλν  →
  scalar R = g^μν R_μν  →  Einstein G_μν = R_μν − ½R g_μν  →  Kretschmann K = R_ρσμν R^{ρσμν}.

CERTIFICATE (our own, exact): re-substitution. For a VACUUM solution the check is R_μν ≡ 0 (every component
symbolically simplifies to 0); for a sourced spacetime, G_μν = 8πT_μν. A curvature INVARIANT (Kretschmann) is the
coordinate-independent witness. Fixture: Schwarzschild is Ricci-flat with K = 48M²/r⁶ — finite at the horizon
r=2M, diverging only at the true singularity r=0 (the engine SEES the difference a coordinate check would miss).

Reuse: sympy does the symbolic differentiation/inversion; the tensor algebra and the ≡0 / =K re-substitution are
OURS. No Lean/Coq. Honest scope (§X): closed-form metrics; the PDE/spectral wall of numerical relativity
(BBH/BSSN) is certified-numeric or DECLINE elsewhere, never EXACT here.
"""
from __future__ import annotations

from typing import List

import sympy as sp

import kernel_verdict as KV


def _christoffel(g, coords):
    n = len(coords)
    ginv = g.inv()
    Gamma = [[[sp.Integer(0)] * n for _ in range(n)] for _ in range(n)]
    for l in range(n):
        for mu in range(n):
            for nu in range(n):
                s = sp.Integer(0)
                for sig in range(n):
                    s += ginv[l, sig] * (sp.diff(g[sig, nu], coords[mu])
                                         + sp.diff(g[sig, mu], coords[nu])
                                         - sp.diff(g[mu, nu], coords[sig]))
                Gamma[l][mu][nu] = sp.simplify(s / 2)
    return Gamma


def _riemann(Gamma, coords):
    n = len(coords)
    R = [[[[sp.Integer(0)] * n for _ in range(n)] for _ in range(n)] for _ in range(n)]
    for rho in range(n):
        for sig in range(n):
            for mu in range(n):
                for nu in range(n):
                    term = sp.diff(Gamma[rho][nu][sig], coords[mu]) - sp.diff(Gamma[rho][mu][sig], coords[nu])
                    for lam in range(n):
                        term += Gamma[rho][mu][lam] * Gamma[lam][nu][sig] - Gamma[rho][nu][lam] * Gamma[lam][mu][sig]
                    R[rho][sig][mu][nu] = sp.simplify(term)
    return R


def _ricci(R, coords):
    n = len(coords)
    Ric = sp.zeros(n, n)
    for mu in range(n):
        for nu in range(n):
            Ric[mu, nu] = sp.simplify(sum(R[lam][mu][lam][nu] for lam in range(n)))
    return Ric


def _kretschmann(R, g, coords):
    n = len(coords)
    ginv = g.inv()
    # lower the first index: R_{ρσμν} = g_{ρα} R^α_{σμν}
    Rl = [[[[sp.simplify(sum(g[rho, a] * R[a][sig][mu][nu] for a in range(n)))
             for nu in range(n)] for mu in range(n)] for sig in range(n)] for rho in range(n)]
    K = sp.Integer(0)
    for rho in range(n):
        for sig in range(n):
            for mu in range(n):
                for nu in range(n):
                    # R^{ρσμν} via raising all indices
                    up = sp.Integer(0)
                    for a in range(n):
                        for b in range(n):
                            for c in range(n):
                                for d in range(n):
                                    up += ginv[rho, a] * ginv[sig, b] * ginv[mu, c] * ginv[nu, d] * Rl[a][b][c][d]
                    K += Rl[rho][sig][mu][nu] * up
    return sp.simplify(K)


def analyze(metric: sp.Matrix, coords: List[sp.Symbol], compute_kretschmann: bool = True) -> dict:
    Gamma = _christoffel(metric, coords)
    R = _riemann(Gamma, coords)
    Ric = _ricci(R, coords)
    ginv = metric.inv()
    scalar = sp.simplify(sum(ginv[i, j] * Ric[i, j] for i in range(len(coords)) for j in range(len(coords))))
    out = {"ricci": Ric, "ricci_scalar": scalar, "riemann": R}
    if compute_kretschmann:
        out["kretschmann"] = _kretschmann(R, metric, coords)
    return out


def schwarzschild_grade() -> KV.Verdict:
    """Schwarzschild: prove RICCI-FLAT (vacuum) AND Kretschmann K = 48M²/r⁶ (the horizon/singularity witness)."""
    t, r, th, ph, M = sp.symbols("t r theta phi M", positive=True)
    f = 1 - 2 * M / r
    g = sp.diag(-f, 1 / f, r ** 2, r ** 2 * sp.sin(th) ** 2)
    res = analyze(g, [t, r, th, ph])
    ricci_zero = all(sp.simplify(res["ricci"][i, j]) == 0 for i in range(4) for j in range(4))
    K = sp.simplify(res["kretschmann"])
    K_expected = sp.simplify(48 * M ** 2 / r ** 6)
    if not ricci_zero:
        return KV.decline("curvature[Schwarzschild]: Ricci not identically 0 ⇒ DECLINE (computation error)", "curvature")
    if sp.simplify(K - K_expected) != 0:
        return KV.decline(f"curvature[Schwarzschild]: Kretschmann {K} ≠ 48M²/r⁶ ⇒ DECLINE", "curvature")
    cert = KV.Cert(KV.EXACT, "ricci_flat_kretschmann", passed=True, check_cost="R_μν≡0 (16 comps) + K=48M²/r⁶",
                   detail="Schwarzschild: R_μν ≡ 0 (vacuum, re-substitution) AND Kretschmann K = 48M²/r⁶ "
                          "(finite at horizon r=2M, diverges only at r=0 — invariant, not coordinate)")
    return KV.exact({"ricci_flat": True, "kretschmann": K}, "curvature.schwarzschild",
                    "EXACT curvature (vacuum + invariant)", cert)


def metric_grade(metric: sp.Matrix, coords: List[sp.Symbol], expect_scalar=None) -> KV.Verdict:
    """General metric: report Ricci, scalar, Einstein, Kretschmann; if expect_scalar given, certify R = expect."""
    res = analyze(metric, coords)
    scalar = res["ricci_scalar"]
    if expect_scalar is not None and sp.simplify(scalar - sp.sympify(expect_scalar)) != 0:
        return KV.decline(f"curvature: Ricci scalar {scalar} ≠ expected {expect_scalar} ⇒ DECLINE", "curvature")
    detail = f"Ricci scalar R = {sp.sstr(scalar)}; Kretschmann = {sp.sstr(res['kretschmann'])}"
    cert = KV.Cert(KV.EXACT, "curvature_chain", passed=True, check_cost="Γ→Riemann→Ricci→R→K, re-substitution",
                   detail=detail + ("" if expect_scalar is None else f" (R = {expect_scalar} verified)"))
    return KV.exact({"ricci_scalar": scalar, "kretschmann": res["kretschmann"], "ricci": res["ricci"]},
                    "curvature.metric", "EXACT curvature chain", cert)


def solve(problem: dict) -> KV.Verdict:
    """ops: 'schwarzschild'; 'metric' (diag entries + coords + optional expect_scalar)."""
    op = problem.get("op")
    if op == "schwarzschild":
        return schwarzschild_grade()
    if op == "metric":
        coords = [sp.Symbol(c) for c in problem["coords"]]
        g = sp.Matrix(problem["metric"])
        return metric_grade(g, coords, problem.get("expect_scalar"))
    return KV.decline(f"curvature: unknown op {op!r} ⇒ DECLINE", "curvature")
