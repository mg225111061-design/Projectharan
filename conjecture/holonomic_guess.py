"""
§AI §1.2 — HOLONOMIC (P-recursive) conjecturer. Defeats: disguised factorial / binomial / hypergeometric products.
================================================================================================================
Holonomic (P-recursive) sequences satisfy a recurrence with POLYNOMIAL coefficients (e.g. factorial a[n]=n·a[n-1];
binomials). When the output is NOT C-finite (BM fails — constant-coefficient), try a FIRST-ORDER P-recursive ansatz
a[n] = r(n)·a[n-1] with r(n) a low-degree polynomial in n, fit r from the observed ratios, and DISPOSE by the
held-out divergence guard (the ratio identity must continue to hold on unseen terms). REUSE catalog/holonomic_sum's
territory (grandfathered sympy not required — the ratio test is rational-exact). DECLINE if not P-recursive / unproven.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Callable, List, Optional

from conjecture import harness as H


def _fit_poly_ratio(seq: List[Fraction], max_deg: int = 3) -> Optional[List[Fraction]]:
    """Fit r(n) = a[n]/a[n-1] (for n≥1) as a polynomial in n of degree ≤ max_deg, EXACTLY (rational interpolation).
    Returns the polynomial coefficients, or None if no exact low-degree polynomial fits all observed ratios."""
    if any(seq[i] == 0 for i in range(len(seq) - 1)):
        return None
    pts = [(Fraction(n), seq[n] / seq[n - 1]) for n in range(1, len(seq))]
    for deg in range(max_deg + 1):
        if len(pts) < deg + 2:
            break
        # solve for a degree-`deg` polynomial through the first deg+1 points, then check it fits ALL points exactly
        xs = [pts[i][0] for i in range(deg + 1)]
        ys = [pts[i][1] for i in range(deg + 1)]
        coeffs = _lagrange_coeffs(xs, ys)
        if all(_polyeval(coeffs, x) == y for x, y in pts):
            return coeffs
    return None


def _lagrange_coeffs(xs: List[Fraction], ys: List[Fraction]) -> List[Fraction]:
    n = len(xs)
    coeffs = [Fraction(0)] * n
    for i in range(n):
        term = [Fraction(0)] * n
        term[0] = Fraction(1)
        denom = Fraction(1)
        deg = 0
        for j in range(n):
            if j == i:
                continue
            new = [Fraction(0)] * n                            # multiply term by (x - xs[j])
            for k in range(deg + 1):
                new[k + 1] += term[k]
                new[k] -= term[k] * xs[j]
            term = new
            deg += 1
            denom *= (xs[i] - xs[j])
        for k in range(n):
            coeffs[k] += term[k] * ys[i] / denom
    return coeffs


def _polyeval(coeffs: List[Fraction], x: Fraction) -> Fraction:
    return sum(c * x ** k for k, c in enumerate(coeffs))


def conjecture(fn: Callable[[int], object], probe: int = 16, holdout: int = 200) -> H.ConjResult:
    import kernel_verdict as KV
    seq = H.observe(fn, probe)
    if seq is None:
        return H.ConjResult(False, "none", 0, "-", None, "non-deterministic / non-numeric ⇒ ABANDON")
    fseq = [Fraction(x) for x in seq]
    rat = _fit_poly_ratio(fseq)
    if rat is None:
        return H.ConjResult(False, "none", 0, "-", KV.decline("no first-order P-recursive ratio ⇒ DECLINE", "holonomic"),
                            "output is not first-order P-recursive ⇒ DECLINE (wrong structure class)")
    deg = max((k for k, c in enumerate(rat) if c != 0), default=0)
    if H.under_determined(probe, deg + 1):
        return H.ConjResult(False, "holonomic", deg, "-", KV.decline("under-determined ⇒ ABANDON", "holonomic"),
                            f"ratio degree {deg} needs ≥{2 * (deg + 1) + 2} observations ⇒ ABANDON")
    # held-out divergence guard: the P-recursive ratio identity must hold on unseen terms
    try:
        ext = [Fraction(fn(i)) for i in range(probe, probe + holdout)]
    except Exception:  # noqa: BLE001
        return H.ConjResult(False, "holonomic", deg, "-", KV.decline("held-out raised ⇒ DECLINE", "holonomic"), "held-out raised")
    s = fseq + ext
    for n in range(probe, len(s)):
        if s[n - 1] == 0 or s[n] != _polyeval(rat, Fraction(n)) * s[n - 1]:
            return H.ConjResult(False, "holonomic", deg, "-", KV.decline("held-out broke the ratio ⇒ DECLINE", "holonomic"),
                                f"★ matched the probe but the P-recursive ratio broke at held-out {n} ⇒ DECLINE (P-2)")
    cert = KV.Cert(KV.EXACT, "closed_form", passed=True, check_cost=f"rational ratio fit (deg {deg}) + {holdout} held-out",
                   detail=f"first-order P-recursive a[n]=r(n)·a[n-1], r a degree-{deg} polynomial (exact rational fit) "
                          "+ held-out divergence guard")
    return H.ConjResult(True, "holonomic", deg, "blackbox+ratio", KV.exact({"ratio_degree": deg}, "holonomic", "P-recursive", cert),
                        f"disguised P-recursive (factorial/binomial-class) recovered; exact ratio identity + held-out ⇒ EXACT")


def adversarial_battery() -> dict:
    """A disguised factorial (a[n]=n·a[n-1], P-recursive but NOT C-finite — BM fails) folds EXACT via the ratio test
    + held-out; ★ a linear (C-finite) sequence is NOT mis-claimed here (ratio is not polynomial ⇒ DECLINE — it's the
    bm_linrec class); a diverge-after factorial DECLINES."""
    import math
    fact = conjecture(lambda n: math.factorial(n))
    lin = conjecture(lambda n: 3 * n + 1)               # ratio (3n+1)/(3(n-1)+1) is NOT polynomial ⇒ DECLINE (bm class)
    def fact_diverge(n):
        return math.factorial(n) if n < 16 else math.factorial(n) + 1
    adv = conjecture(fact_diverge)
    cases = {"disguised_factorial_folds": fact.issued and fact.structure_class == "holonomic",
             "linear_not_misclaimed": not lin.issued,        # ratio non-polynomial ⇒ DECLINE (it's the bm_linrec class)
             "diverge_after_declines": not adv.issued}
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
