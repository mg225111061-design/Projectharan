"""
MATH-Ascent §3 (arsenal) — CERTIFIED NUMERICS: EXACT enclosures vs honest PROBABILISTIC approximation.
=====================================================================================================
This is where the grade discipline is sharpest. Two kinds of numeric answer, never confused:
  • EXACT ENCLOSURE — a PROVEN bound, not a sample:
      – real-root COUNT in [a,b] by Sturm's theorem (exact), cross-checked against isolated real roots;
      – root EXISTENCE by the intermediate-value theorem (a sign change of a continuous f over exact rational
        endpoints PROVES a root between them), refined by bisection to a narrow rational interval;
      – √n bracketed by exact rationals lo, hi with  lo² ≤ n ≤ hi²  (the inequalities ARE the certificate).
    These are EXACT (an exact interval uses ε = width / bound, never a probabilistic δ — kernel_verdict §0.2).
  • PROBABILISTIC(ε,δ) — Monte-Carlo estimation: an approximation with a REPORTED Hoeffding (ε,δ). NEVER EXACT,
    not even at tiny δ (a sample count is not a proof — Constitution §0.2). Honest by construction.
No win is claimed where there is none; an unprovable bound ⇒ DECLINE.
"""
from __future__ import annotations

import math
from fractions import Fraction
from typing import Optional

import sympy as sp

import kernel_verdict as KV


# ── EXACT: real-root count by Sturm (cross-checked) ──────────────────────────────────────────────────────
def real_root_count_grade(poly, a, b, x=None) -> KV.Verdict:
    """Count DISTINCT real roots of poly in [a,b] by Sturm's theorem (EXACT), cross-checked against the exactly
    isolated real roots. The two exact methods must agree."""
    x = x or sp.Symbol("x")
    p = sp.sympify(poly, locals={str(x): x}) if isinstance(poly, str) else poly
    P = sp.Poly(p, x)
    a, b = sp.nsimplify(a), sp.nsimplify(b)
    sturm = P.count_roots(a, b)                                   # Sturm-sequence count (exact)
    isolated = sum(1 for r in sp.real_roots(P) if a <= r <= b)    # independent exact isolation
    if sturm != isolated:
        return KV.decline(f"real_root_count: Sturm {sturm} ≠ isolated {isolated} ⇒ DECLINE", "numeric.sturm")
    cert = KV.Cert(KV.EXACT, "sturm_root_count", passed=True, check_cost="Sturm chain + real-root isolation",
                   detail=f"{sturm} distinct real root(s) in [{a},{b}] (Sturm ≡ isolation, exact)")
    return KV.exact(sturm, "numeric.sturm", "exact (Sturm)", cert)


# ── EXACT: root existence by IVT (sign change), refined by bisection ─────────────────────────────────────
def root_enclosure_grade(f, a, b, tol=Fraction(1, 10 ** 6), x=None) -> KV.Verdict:
    """A sign change of continuous f over exact rational [a,b] PROVES a root inside (IVT). Bisect to width ≤ tol.
    Returns an EXACT enclosure [lo,hi]; no sign change ⇒ DECLINE (cannot conclude — never a fabricated root)."""
    x = x or sp.Symbol("x")
    expr = sp.sympify(f, locals={str(x): x}) if isinstance(f, str) else f
    lo, hi = Fraction(a), Fraction(b)

    def val(t):
        return sp.nsimplify(expr.subs(x, sp.Rational(t.numerator, t.denominator)))

    flo, fhi = val(lo), val(hi)
    if flo == 0:
        return _exact_root_point(lo, "f(a)=0")
    if fhi == 0:
        return _exact_root_point(hi, "f(b)=0")
    if (flo > 0) == (fhi > 0):                                    # same sign ⇒ IVT gives nothing ⇒ honest DECLINE
        return KV.decline("root_enclosure: no sign change over [a,b] ⇒ cannot prove a root ⇒ DECLINE",
                          "numeric.ivt")
    while hi - lo > tol:                                          # bisection preserves the sign-change invariant
        mid = (lo + hi) / 2
        fm = val(mid)
        if fm == 0:
            return _exact_root_point(mid, "exact bisection hit")
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi, fhi = mid, fm
    cert = KV.Cert(KV.EXACT, "ivt_sign_change", passed=True, check_cost="O(1) two exact signs",
                   detail=f"f({lo})·f({hi}) < 0 (exact) ⇒ a root in [{float(lo):.9f},{float(hi):.9f}] by IVT",
                   epsilon=float(hi - lo))
    return KV.exact((lo, hi), "numeric.ivt", "exact enclosure (bisection)", cert)


def _exact_root_point(r: Fraction, why: str) -> KV.Verdict:
    cert = KV.Cert(KV.EXACT, "exact_root", passed=True, check_cost="O(1)", detail=f"{why}: root = {r}")
    return KV.exact((r, r), "numeric.ivt", "exact root", cert)


# ── EXACT: √n bracketed by exact rationals (lo² ≤ n ≤ hi²) ────────────────────────────────────────────────
def sqrt_enclosure_grade(n, digits: int = 9) -> KV.Verdict:
    if n < 0:
        return KV.decline("sqrt_enclosure: n < 0 (no real root) ⇒ DECLINE", "numeric.sqrt")
    scale = 10 ** digits
    nr = Fraction(n)
    root_scaled = math.isqrt(int(nr.numerator * scale * scale) // int(nr.denominator))
    lo = Fraction(root_scaled, scale)
    hi = lo + Fraction(1, scale)
    if not (lo * lo <= nr <= hi * hi):                           # ★ the bracketing inequalities ARE the proof ★
        return KV.decline("sqrt_enclosure: bracket failed lo²≤n≤hi² ⇒ DECLINE", "numeric.sqrt")
    cert = KV.Cert(KV.EXACT, "sqrt_bracket", passed=True, check_cost="O(1) two exact squarings",
                   detail=f"lo²≤{n}≤hi² with lo={lo}, hi={hi} (exact rationals)", epsilon=float(hi - lo))
    return KV.exact((lo, hi), "numeric.sqrt", "exact enclosure", cert)


# ── PROBABILISTIC(ε,δ): Monte-Carlo — an approximation with a REPORTED Hoeffding bound, NEVER EXACT ──────
def monte_carlo_pi_grade(samples: int = 200000, delta: float = 1e-3, seed: int = 0) -> KV.Verdict:
    import random
    rng = random.Random(seed)
    inside = 0
    for _ in range(samples):
        u, v = rng.random(), rng.random()
        if u * u + v * v <= 1.0:
            inside += 1
    est = 4.0 * inside / samples
    # Hoeffding: P(|p̂−p| ≥ t) ≤ 2e^{−2 n t²}; for δ ⇒ t = sqrt(ln(2/δ)/(2n)); π-scale ε = 4·t
    t = math.sqrt(math.log(2.0 / delta) / (2.0 * samples))
    eps = 4.0 * t
    cert = KV.Cert(KV.PROBABILISTIC, "monte_carlo_hoeffding", passed=True, check_cost="O(samples)",
                   epsilon=eps, delta=delta,
                   detail=f"π≈{est:.5f} via {samples} samples; Hoeffding |π̂−π|≤{eps:.4f} w.p. ≥ 1−{delta}")
    return KV.probabilistic(est, "numeric.montecarlo", "O(n) sampling — approximation", cert)


def solve(problem: dict) -> KV.Verdict:
    op = problem.get("op")
    x = sp.Symbol(problem.get("var", "x"))
    if op == "root_count":
        return real_root_count_grade(problem["poly"], problem["a"], problem["b"], x)
    if op == "root_enclosure":
        return root_enclosure_grade(problem["f"], problem["a"], problem["b"],
                                    problem.get("tol", Fraction(1, 10 ** 6)), x)
    if op == "sqrt":
        return sqrt_enclosure_grade(problem["n"], problem.get("digits", 9))
    if op == "montecarlo_pi":
        return monte_carlo_pi_grade(problem.get("samples", 200000), problem.get("delta", 1e-3))
    return KV.decline(f"certified_numeric: unknown op {op!r} ⇒ DECLINE", "certified_numeric")
