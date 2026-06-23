"""
UNIFIED ARSENAL §1 · G3 — Creative telescoping, the meta-method (on G1/G2).
===========================================================================
One idea, four classical specializations:
  • GOSPER — indefinite hypergeometric summation (a DECISION procedure; re-homed from combinatorics).
  • ZEILBERGER — definite hypergeometric sums: a telescoper L (operator in n only) + a certificate G with
        L(F)(n,k) = G(n,k+1) − G(n,k)   ( = Δ_k G )
    so Σ_k L(F) telescopes ⇒ L annihilates S(n)=Σ_k F(n,k). The pair (L, G) is the WZ certificate.
  • ALMKVIST–ZEILBERGER — the continuous analog for hyperexponential integrals: L(F) = ∂_t G, so ∫ L(F) dt
    telescopes ⇒ L annihilates ∫ F dt.
  • CHYZAK — the general holonomic case (flagged future; needs the G1 Ore-module elimination at full generality).

WHAT IS CERTIFIED (our own machine-check, sympy only SEARCHES):
  • the WZ identity  Δ_k G − L(F) ≡ 0  (resp. ∂_t G − L(F) ≡ 0) as an EXACT rational/symbolic identity → 0;
  • the recurrence L holds on the brute-force sum/integral values over many n (an independent cross-check).
HONEST SCOPE (§X): we obtain the telescoper L from the (sympy-found) closed-form recurrence — this covers the
hypergeometric-summable class (binomial, central-binomial, …). A definite sum with NO closed form sympy can find
(e.g. Apéry numbers) gets an honest DECLINE *by this method* — NOT a claim that no telescoper exists; full
parametrized Gosper is future work. The certificate makes the result EXACT regardless of how L was discovered.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import sympy as sp
from sympy.concrete.gosper import gosper_sum

import kernel_verdict as KV
from mathmode import combinatorics as CB


# ── the rigorous WZ-pair verifier (the EXACT core) ──────────────────────────────────────────────────────────
def verify_wz_pair(F: sp.Expr, L_coeffs: Dict[int, sp.Expr], G: sp.Expr, n: sp.Symbol, k: sp.Symbol) -> bool:
    """Check the discrete WZ identity  Σ_j c_j(n) F(n+j,k)  =  G(n,k+1) − G(n,k)  as an exact identity → 0.
    This is the proof: summing both sides over k telescopes the RHS, so L = Σ c_j S_n^j annihilates Σ_k F."""
    LF = sum(sp.sympify(c) * F.subs(n, n + j) for j, c in L_coeffs.items())
    delta = G.subs(k, k + 1) - G
    return sp.simplify(sp.together(LF - delta)) == 0


def verify_az_pair(F: sp.Expr, L_coeffs: Dict[int, sp.Expr], G: sp.Expr, x: sp.Symbol, t: sp.Symbol) -> bool:
    """Continuous WZ identity  Σ_j c_j(x) ∂_x^j F  =  ∂_t G  → 0 (Almkvist–Zeilberger)."""
    LF = sum(sp.sympify(c) * sp.diff(F, x, j) for j, c in L_coeffs.items())
    return sp.simplify(sp.together(LF - sp.diff(G, t))) == 0


# ── telescoper from the closed-form recurrence (the discovery the certificate then proves) ──────────────────
def _first_order_telescoper(closed: sp.Expr, var: sp.Symbol) -> Optional[Dict[int, sp.Expr]]:
    """If the closed form C(var) is hypergeometric (C(var+1)/C(var) ∈ ℚ(var)), return the first-order telescoper
    den·S − num (den·C(var+1) = num·C(var)). Else None."""
    ratio = sp.simplify(closed.subs(var, var + 1) / closed)
    ratio = sp.cancel(sp.together(ratio))
    if ratio.free_symbols - {var}:
        return None                                  # not rational in var alone
    num, den = sp.fraction(ratio)
    if not (sp.Poly(num, var, domain="QQ") and sp.Poly(den, var, domain="QQ")):
        return None
    return {1: sp.expand(den), 0: sp.expand(-num)}


def _first_order_telescoper_diff(closed: sp.Expr, var: sp.Symbol) -> Optional[Dict[int, sp.Expr]]:
    """Continuous analog: if I(var) is hyperexponential (I′/I ∈ ℚ(var)), return the first-order differential
    telescoper den·D − num (den·I′ = num·I)."""
    ratio = sp.cancel(sp.together(sp.diff(closed, var) / closed))
    if ratio.free_symbols - {var}:
        return None
    num, den = sp.fraction(ratio)
    try:
        sp.Poly(num, var, domain="QQ"); sp.Poly(den, var, domain="QQ")
    except sp.PolynomialError:
        return None
    return {1: sp.expand(den), 0: sp.expand(-num)}


def _recover_ratio(points, dnum: int, dden: int, var: sp.Symbol):
    """Exact rational-function recovery: fit R(var)=num/den (degrees dnum/dden) to (var_i, R_i) points via a 1-dim
    nullspace over ℚ. Returns (num, den) cleared of denominators, or None (no consistent fit at these degrees)."""
    if len(points) < dnum + dden + 2:
        return None
    rows = [[ni ** j for j in range(dnum + 1)] + [-Ri * ni ** l for l in range(dden + 1)] for ni, Ri in points]
    M = sp.Matrix(rows)
    ns = M.nullspace()
    if len(ns) != 1:                                  # exactly 1-dim ⇒ the over-determined fit is consistent
        return None
    vec = ns[0]
    dens = [sp.denom(sp.together(e)) for e in vec]
    mult = sp.lcm(dens) if dens else 1
    vec = [sp.nsimplify(e * mult) for e in vec]
    num = sum(vec[j] * var ** j for j in range(dnum + 1))
    den = sum(vec[dnum + 1 + l] * var ** l for l in range(dden + 1))
    if den == 0 or num == 0:
        return None
    return sp.expand(num), sp.expand(den)


def _guess_first_order_telescoper(values, var: sp.Symbol) -> Optional[Dict[int, sp.Expr]]:
    """From exact sum/integral values S(0),S(1),… recover a first-order telescoper {1:den, 0:−num} with
    S(n+1)/S(n) = num/den ∈ ℚ(var). The WZ certificate then PROVES it — the recovery only needs to be a candidate."""
    pts = [(m, sp.nsimplify(values[m + 1] / values[m])) for m in range(len(values) - 1) if values[m] != 0]
    if len(pts) < 4:
        return None
    for total in range(0, 5):                         # increasing total degree of the rational ratio
        for dnum in range(total + 1):
            dden = total - dnum
            got = _recover_ratio(pts, dnum, dden, var)
            if got is None:
                continue
            num, den = got
            # held-out confirmation: the recovered ratio reproduces EVERY data point
            if all(sp.simplify(num.subs(var, ni) - Ri * den.subs(var, ni)) == 0 for ni, Ri in pts):
                return {1: sp.expand(den), 0: sp.expand(-num)}
    return None


# ── ZEILBERGER (definite hypergeometric) ────────────────────────────────────────────────────────────────────
def zeilberger(F: sp.Expr, n: sp.Symbol, k: sp.Symbol, lo=0, hi=None) -> KV.Verdict:
    """Definite sum S(n)=Σ_{k} F(n,k): find a WZ-certified telescoper L (recurrence for S). EXACT with the
    (L, G) certificate, or honest DECLINE (no closed form / no Gosper certificate found by this method)."""
    hi = n if hi is None else hi

    # discover a first-order telescoper from BRUTE-FORCE sum values (robust; sympy's symbolic summation of
    # binomials returns messy Piecewise/hyper forms). The WZ certificate then PROVES the candidate.
    def _S(m):
        top = m if hi is n else int(hi)
        return sum(sp.nsimplify(F.subs({n: m, k: j})) for j in range(int(lo), top + 1))
    try:
        values = [sp.nsimplify(_S(m)) for m in range(0, 12)]
    except Exception:  # noqa: BLE001
        values = []
    Lc = _guess_first_order_telescoper(values, n) if values else None
    if Lc is None:
        return KV.decline("zeilberger: no first-order telescoper recovered from the sum values ⇒ DECLINE (not a "
                          "non-existence claim; higher-order / parametrized Gosper is future work)", "telescoping")
    # T(n,k) = L(F) as a single hypergeometric term: F · Σ_j c_j(n)·(F(n+j,k)/F(n,k))
    rho = sum(Lc[j] * sp.cancel(sp.together(F.subs(n, n + j) / F)) for j in Lc)
    T = sp.simplify(F * rho)
    G = gosper_sum(T, k)
    if G is None:
        return KV.decline("zeilberger: L(F) not Gosper-summable in k ⇒ DECLINE (no WZ certificate found)", "telescoping")
    if not verify_wz_pair(F, Lc, G, n, k):
        return KV.decline("zeilberger: WZ identity Δ_kG ≠ L(F) ⇒ DECLINE (rejected, never shipped unproven)", "telescoping")
    # independent cross-check: the recurrence holds on brute-force sum values
    bad = 0
    for m in range(max(1, int(lo) + 1), 9):
        val = sum(sp.nsimplify(Lc[j].subs(n, m)) * _S(m + j) for j in Lc)
        if sp.simplify(val) != 0:
            bad += 1
    if bad:
        return KV.decline(f"zeilberger: recurrence fails on {bad} brute values (boundary terms?) ⇒ DECLINE", "telescoping")
    Ls = " + ".join(f"({sp.sstr(Lc[j])})·S^{j}" for j in sorted(Lc))
    cert = KV.Cert(KV.EXACT, "zeilberger_wz_pair", passed=True, check_cost="WZ identity →0 + brute recurrence",
                   detail=f"telescoper L = {Ls}; certificate R=G/F = {sp.sstr(sp.cancel(G / F))}; "
                          f"Δ_kG ≡ L(F) and the recurrence holds on the Σ values")
    return KV.exact({"telescoper": Lc, "certificate_G": G},
                    "telescoping.zeilberger", "creative telescoping (WZ pair)", cert)


# ── ALMKVIST–ZEILBERGER (hyperexponential integrals) ────────────────────────────────────────────────────────
def almkvist_zeilberger(F: sp.Expr, x: sp.Symbol, t: sp.Symbol, lo=-sp.oo, hi=sp.oo) -> KV.Verdict:
    """Definite integral I(x)=∫ F(x,t) dt: telescoper L (in x) + certificate G with L(F)=∂_t G. EXACT or DECLINE."""
    try:
        closed = sp.integrate(F, (t, lo, hi))
    except Exception:  # noqa: BLE001
        closed = None
    if closed is None or closed.has(sp.Integral) or closed in (sp.nan, sp.zoo):
        return KV.decline("almkvist_zeilberger: no closed-form integral by this method ⇒ DECLINE", "telescoping")
    Lc = _first_order_telescoper_diff(closed, x)
    if Lc is None:
        return KV.decline("almkvist_zeilberger: integral not first-order hyperexponential in x ⇒ DECLINE", "telescoping")
    LF = sum(Lc[j] * sp.diff(F, x, j) for j in Lc)
    G = sp.integrate(sp.simplify(LF), t)             # find G with ∂_t G = L(F)
    if G is None or G.has(sp.Integral):
        return KV.decline("almkvist_zeilberger: L(F) not elementarily integrable in t ⇒ DECLINE", "telescoping")
    if not verify_az_pair(F, Lc, G, x, t):
        return KV.decline("almkvist_zeilberger: ∂_tG ≠ L(F) ⇒ DECLINE", "telescoping")
    Ls = " + ".join(f"({sp.sstr(Lc[j])})·D^{j}" for j in sorted(Lc))
    cert = KV.Cert(KV.EXACT, "az_pair", passed=True, check_cost="∂_tG − L(F) →0",
                   detail=f"telescoper L = {Ls}; G = {sp.sstr(sp.simplify(G))}; ∂_tG ≡ L(F); ∫ = {sp.sstr(closed)}")
    return KV.exact({"telescoper": Lc, "certificate_G": sp.simplify(G), "closed_form": closed},
                    "telescoping.almkvist_zeilberger", "creative telescoping (continuous WZ)", cert)


# ── GOSPER (indefinite) — re-homed specialization (DECISION) ────────────────────────────────────────────────
def gosper_indefinite(term, k=None) -> KV.Verdict:
    """Indefinite hypergeometric summation: the G3 specialization that is a DECISION procedure (closed
    antidifference OR proof of non-existence). Delegates to the existing telescoping-certified Gosper."""
    return CB.gosper_indefinite(term, k)


def solve(problem: dict) -> KV.Verdict:
    """ops: 'zeilberger' (F, optional lo/hi), 'almkvist_zeilberger' (F in x,t), 'gosper' (term). DECLINE else."""
    op = problem.get("op")
    n, k = sp.symbols("n k", integer=True)
    if op == "zeilberger":
        F = sp.sympify(problem["F"], locals={"n": n, "k": k})
        return zeilberger(F, n, k, problem.get("lo", 0), problem.get("hi", n))
    if op == "almkvist_zeilberger":
        x, t = sp.symbols("x t")
        F = sp.sympify(problem["F"], locals={"x": x, "t": t})
        return almkvist_zeilberger(F, x, t, problem.get("lo", -sp.oo), problem.get("hi", sp.oo))
    if op == "gosper":
        return gosper_indefinite(problem["term"], k)
    return KV.decline(f"telescoping: unknown op {op!r} ⇒ DECLINE", "telescoping")
