"""
§AY QLA-3 — Carleman linearization → C-finite (the EXACT bridge for *some* nonlinear maps).
================================================================================================================
A nonlinear iteration x_{n+1}=f(x_n) is EXACTLY foldable ONLY when its Carleman lift to a monomial basis CLOSES at
FINITE dimension (a finite invariant subspace). Then the lifted state evolves by a finite matrix M and every
coordinate is C-finite (reuse cfinite). Two honest faces:

  • RICCATI / linear-fractional  x' = (a·x+b)/(c·x+d)  → projective lift [p;q]'=[[a,b],[c,d]][p;q], x_n=p_n/q_n.
    The (p,q) sequence is C-finite (2×2 companion) ⇒ EXACT closed form (net-new: rational maps).
  • polynomial maps: the monomial set is CLOSED iteratively under f; FINITE ⇒ fold via M, INFINITE/degree-growth ⇒
    DECLINE. ★ The generic quadratic / logistic map's degree DOUBLES each step (deg f^k = (deg f)^k) ⇒ the lift is
    infinite ⇒ truncation error ⇒ **EXACT is FORBIDDEN, DECLINE** (§1.8 / QLA-3 DECLINE rule — no false-EXACT).

★ ∀-n = the projective-linear / companion THEOREM (§0-b) gated by exact held-out replay of the ACTUAL nonlinear
iteration. Float coefficients ⇒ DECLINE (no float-EXACT, §1-Q3).
"""
from __future__ import annotations

from fractions import Fraction
from typing import Dict, List, Optional, Sequence, Tuple

import cfinite
import kernel_verdict as KV

from . import _la

Mono = Tuple[int, ...]
Poly = Dict[Mono, Fraction]


# ── tiny exact multivariate polynomial arithmetic (dict{exponent-tuple: Fraction}) ──────────────────────────────
def _padd(p: Poly, q: Poly) -> Poly:
    r = dict(p)
    for m, c in q.items():
        r[m] = r.get(m, Fraction(0)) + c
        if r[m] == 0:
            del r[m]
    return r


def _pmul(p: Poly, q: Poly) -> Poly:
    r: Poly = {}
    for m1, c1 in p.items():
        for m2, c2 in q.items():
            m = tuple(a + b for a, b in zip(m1, m2))
            r[m] = r.get(m, Fraction(0)) + c1 * c2
            if r[m] == 0:
                del r[m]
    return r


def _ppow(p: Poly, k: int, nvars: int) -> Poly:
    r: Poly = {tuple([0] * nvars): Fraction(1)}
    for _ in range(k):
        r = _pmul(r, p)
    return r


def _deg(m: Mono) -> int:
    return sum(m)


def _eval(p: Poly, x: Sequence[Fraction]) -> Fraction:
    tot = Fraction(0)
    for m, c in p.items():
        term = c
        for i, e in enumerate(m):
            term *= x[i] ** e
        tot += term
    return tot


def carleman_closure(varmaps: List[Poly], nvars: int, target: int,
                     deg_cap: int = 8, size_cap: int = 60) -> Tuple[bool, List[Mono], Optional[List[List[Fraction]]]]:
    """Iteratively close the monomial basis under the map (forward-invariant). Returns (closed, basis, M) where
    y_{n+1}=M·y_n on the basis. FINITE closure ⇒ closed=True; degree-growth / size blow-up ⇒ closed=False (DECLINE)."""
    const = tuple([0] * nvars)
    unit_t = tuple(1 if i == target else 0 for i in range(nvars))
    basis: List[Mono] = [const, unit_t]
    seen = set(basis)
    images: Dict[Mono, Poly] = {}
    i = 0
    while i < len(basis):
        m = basis[i]
        img: Poly = {const: Fraction(1)}
        for var in range(nvars):
            if m[var]:
                img = _pmul(img, _ppow(varmaps[var], m[var], nvars))
        images[m] = img
        for mm in img:
            if _deg(mm) > deg_cap:
                return (False, basis, None)                     # ★ degree growth ⇒ infinite lift ⇒ DECLINE
            if mm not in seen:
                seen.add(mm)
                basis.append(mm)
                if len(basis) > size_cap:
                    return (False, basis, None)                 # blow-up ⇒ not finitely closed ⇒ DECLINE
        i += 1
    idx = {m: j for j, m in enumerate(basis)}
    n = len(basis)
    M = [[Fraction(0)] * n for _ in range(n)]                    # row j = image of basis[j] in the basis
    for j, m in enumerate(basis):
        for mm, c in images[m].items():
            M[j][idx[mm]] = c
    return (True, basis, M)


def detect_carleman_cfinite(varmaps: List[Poly], nvars: int, x0: Sequence, target: int = 0,
                            deg_cap: int = 8) -> KV.Verdict:
    """Polynomial-map fold: EXACT iff the Carleman lift closes finitely (verified by held-out replay of the actual
    nonlinear iteration); generic nonlinear (degree growth) ⇒ DECLINE (no truncation-EXACT)."""
    try:
        x0f = _la.fvec(x0)
        vm = [{m: _la.exact(c) for m, c in p.items()} for p in varmaps]
    except _la.NonExact as e:
        return KV.decline(f"carleman: {e} ⇒ DECLINE (no float-EXACT)", "carleman_cfinite")
    if len(x0f) != nvars:
        return KV.decline("carleman: x0 dimension mismatch", "carleman_cfinite")
    closed, basis, M = carleman_closure(vm, nvars, target, deg_cap=deg_cap)
    if not closed:
        return KV.decline("carleman: monomial lift does NOT close at finite degree (deg f^k grows) ⇒ infinite "
                          "invariant subspace ⇒ truncation ⇒ EXACT FORBIDDEN, DECLINE", "carleman_cfinite")
    unit_t = tuple(1 if i == target else 0 for i in range(nvars))
    tgt = basis.index(unit_t)
    y0 = [_eval({m: Fraction(1)}, x0f) for m in basis]          # evaluate each basis monomial at x0
    # ★ held-out replay: M^n y0 target-coord must equal the ACTUAL nonlinear iteration for several n beyond a window
    def actual(nstep: int) -> Optional[Fraction]:
        x = list(x0f)
        for _ in range(nstep):
            x = [_eval(vm[i], x) for i in range(nvars)]
        return x[target]
    for nstep in (3, 5, 8, 13):
        P = cfinite._matpow(M, nstep)
        yN = [sum((P[r][k] * y0[k] for k in range(len(basis))), Fraction(0)) for r in range(len(basis))]
        if yN[tgt] != actual(nstep):
            return KV.decline("carleman: lift fails held-out replay vs the actual iteration ⇒ DECLINE",
                              "carleman_cfinite")
    cert = KV.Cert(KV.EXACT, "carleman_finite_closure", passed=True,
                   check_cost=f"finite closure dim={len(basis)} + held-out replay",
                   detail=f"Carleman lift closes at finite dimension {len(basis)}; lifted state y_{{n+1}}=M·y_n is "
                          f"linear ⇒ C-finite; held-out replay vs actual nonlinear iteration ✓")
    return KV.exact({"lift_dim": len(basis), "target": target}, "carleman_cfinite",
                    f"O(dim³·log N) (dim={len(basis)})", cert,
                    reason="Axis-A: nonlinear map recognized via finite Carleman closure; Axis-B O(N)→O(log N)")


def riccati_fold(a, b, c, d, x0) -> KV.Verdict:
    """Linear-fractional iteration x' = (a·x+b)/(c·x+d) → projective 2×2 lift → C-finite (p,q), x_n=p_n/q_n. EXACT
    (rational) gated by held-out replay of the direct iteration; a pole (q_n=0) or float ⇒ DECLINE."""
    try:
        af, bf, cf, df, x = _la.exact(a), _la.exact(b), _la.exact(c), _la.exact(d), _la.exact(x0)
    except _la.NonExact as e:
        return KV.decline(f"riccati: {e} ⇒ DECLINE (no float-EXACT)", "riccati_projective")
    if af * df - bf * cf == 0:
        return KV.decline("riccati: degenerate map (ad−bc=0) ⇒ collapses to a constant, not a projective lift",
                          "riccati_projective")
    M = [[af, bf], [cf, df]]
    # direct iteration (the ground truth) + companion lift; compare for held-out n
    def direct(nstep: int) -> Optional[Fraction]:
        v = x
        for _ in range(nstep):
            den = cf * v + df
            if den == 0:
                return None
            v = (af * v + bf) / den
        return v
    for nstep in (2, 3, 5, 8):
        P = cfinite._matpow(M, nstep)
        p_n = P[0][0] * x + P[0][1] * 1
        q_n = P[1][0] * x + P[1][1] * 1
        dv = direct(nstep)
        if dv is None:
            return KV.decline(f"riccati: a pole occurs (denominator 0) at n={nstep} ⇒ map undefined ⇒ DECLINE",
                              "riccati_projective")
        if q_n == 0 or p_n / q_n != dv:
            return KV.decline("riccati: projective lift fails held-out replay ⇒ DECLINE", "riccati_projective")
    cert = KV.Cert(KV.EXACT, "riccati_projective_lift", passed=True, check_cost="2×2 companion + held-out replay",
                   detail="x'=(ax+b)/(cx+d) lifts to [p;q]'=[[a,b],[c,d]][p;q]; x_n=p_n/q_n via 2×2 companion power; "
                          "held-out replay vs direct iteration ✓ (∀-n by the projective-linear theorem)")
    return KV.exact({"lift": "2x2 projective", "closed_form": "p_n/q_n = (M^n·[x0;1])[0]/[1]"},
                    "riccati_projective", "O(log N) (2×2 matpow)", cert,
                    reason="Axis-A: rational map recognized as projective-linear; Axis-B O(N)→O(log N)")


def adversarial_battery() -> dict:
    """★ EXACT: a Riccati map (x'=(x+1)/x → Fibonacci ratios) folds via the 2×2 projective lift; an affine map
    (x'=2x+3) folds via finite Carleman closure. ★★ DECLINE boundary (no false-EXACT): a quadratic map (x'=x²−1)
    and the logistic map (x'=3x−3x²) have DEGREE-DOUBLING lifts ⇒ DECLINE; float coefficients ⇒ DECLINE."""
    ric = riccati_fold(1, 1, 1, 0, 1)                                   # x'=(x+1)/x, x0=1 ⇒ 2, 3/2, 5/3, 8/5 …
    ric_ok = ric.status == KV.EXACT
    aff = detect_carleman_cfinite([{(1,): Fraction(2), (0,): Fraction(3)}], 1, [1], target=0)   # x'=2x+3
    aff_ok = aff.status == KV.EXACT
    quad = detect_carleman_cfinite([{(2,): Fraction(1), (0,): Fraction(-1)}], 1, [Fraction(1, 3)], target=0)  # x'=x²−1
    quad_declines = quad.status == KV.DECLINE                           # ★★ degree doubles ⇒ no false-EXACT
    logistic = detect_carleman_cfinite([{(1,): Fraction(3), (2,): Fraction(-3)}], 1, [Fraction(1, 5)], target=0)
    logistic_declines = logistic.status == KV.DECLINE                   # ★★ generic logistic ⇒ DECLINE
    flt = riccati_fold(1.5, 1.0, 1.0, 0.0, 1.0)
    flt_declines = flt.status == KV.DECLINE
    cases = {"riccati_exact": ric_ok, "affine_carleman_exact": aff_ok, "quadratic_declines": quad_declines,
             "logistic_declines": logistic_declines, "float_declines": flt_declines}
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, x in cases.items() if not x]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
