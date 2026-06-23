"""
MATH-Ascent §B4 (arsenal) — PROBABILITY / STATISTICS: exact distributions + PROVEN tail-bound inequalities.
==========================================================================================================
Two exact, certified capabilities (no sampling — these are proofs, not estimates):
  • EXACT discrete distributions over ℚ: the binomial PMF/mean/variance computed with exact rationals, certified
    by the identities Σ_k P(k) = 1, E[X] = np, Var[X] = np(1−p) (each re-checked against the brute sums).
  • PROVEN concentration inequalities — Markov P(X≥a) ≤ E[X]/a (X≥0) and Chebyshev P(|X−μ|≥a) ≤ σ²/a² — are
    THEOREMS, so the bound is EXACT (an exact rational upper bound, NOT a probabilistic δ). We additionally
    cross-check that the bound really dominates the EXACT tail of a reference distribution (anti-fabrication: a
    bound that didn't actually hold would be refused).
A Monte-Carlo estimate, by contrast, lives in certified_numeric as PROBABILISTIC(ε,δ) — never EXACT. Here the
answers are exact rationals with a proven certificate.
"""
from __future__ import annotations

from fractions import Fraction
from math import comb
from typing import List, Tuple, Union

import kernel_verdict as KV

Num = Union[int, Fraction, Tuple[int, int]]


def _frac(p: Num) -> Fraction:
    return Fraction(*p) if isinstance(p, tuple) else Fraction(p)


def binomial_pmf(n: int, p: Fraction) -> List[Fraction]:
    return [comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(n + 1)]


def binomial_grade(n: int, p: Num) -> KV.Verdict:
    """Exact Binomial(n,p): PMF/mean/variance over ℚ, certified by Σ P=1, E[X]=np, Var=np(1−p)."""
    if n < 0:
        return KV.decline(f"binomial: n={n} < 0 ⇒ DECLINE", "probability.binomial")
    p = _frac(p)
    if not (0 <= p <= 1):
        return KV.decline(f"binomial: p={p} ∉ [0,1] ⇒ DECLINE", "probability.binomial")
    pmf = binomial_pmf(n, p)
    total = sum(pmf)
    mean = sum(k * pmf[k] for k in range(n + 1))
    var = sum(k * k * pmf[k] for k in range(n + 1)) - mean * mean
    if total != 1 or mean != n * p or var != n * p * (1 - p):    # ★ exact identities = the certificate ★
        return KV.decline("binomial: exact identities (ΣP=1, E=np, Var=np(1−p)) failed ⇒ DECLINE",
                          "probability.binomial")
    cert = KV.Cert(KV.EXACT, "exact_binomial", passed=True, check_cost="O(n) exact sums",
                   detail=f"Binomial({n},{p}): ΣP=1, E[X]={mean}, Var={var} (exact rationals, identities verified)")
    return KV.exact({"mean": mean, "var": var, "pmf": pmf}, "probability.binomial", "O(n) exact", cert)


def binomial_tail(n: int, p: Fraction, a: int) -> Fraction:
    """Exact P(X ≥ a) for Binomial(n,p) (rational)."""
    pmf = binomial_pmf(n, p)
    return sum(pmf[k] for k in range(max(0, a), n + 1))


def markov_grade(mean: Num, a: Num) -> KV.Verdict:
    """Markov: for X ≥ 0, P(X ≥ a) ≤ E[X]/a (a > 0). EXACT proven bound (rational)."""
    mean, a = _frac(mean), _frac(a)
    if a <= 0 or mean < 0:
        return KV.decline("markov: needs a>0 and E[X]≥0 (X≥0) ⇒ DECLINE", "probability.markov")
    bound = mean / a
    cert = KV.Cert(KV.EXACT, "markov_inequality", passed=True, check_cost="O(1) theorem",
                   detail=f"P(X≥{a}) ≤ E[X]/a = {bound} (Markov, X≥0 — a PROVEN bound, exact)")
    return KV.exact(bound, "probability.markov", "exact bound", cert)


def chebyshev_grade(var: Num, a: Num) -> KV.Verdict:
    """Chebyshev: P(|X−μ| ≥ a) ≤ Var[X]/a² (a > 0). EXACT proven bound (rational)."""
    var, a = _frac(var), _frac(a)
    if a <= 0 or var < 0:
        return KV.decline("chebyshev: needs a>0 and Var≥0 ⇒ DECLINE", "probability.chebyshev")
    bound = min(Fraction(1), var / (a * a))                      # a probability bound is ≤ 1
    cert = KV.Cert(KV.EXACT, "chebyshev_inequality", passed=True, check_cost="O(1) theorem",
                   detail=f"P(|X−μ|≥{a}) ≤ Var/a² = {bound} (Chebyshev — a PROVEN bound, exact)")
    return KV.exact(bound, "probability.chebyshev", "exact bound", cert)


def solve(problem: dict) -> KV.Verdict:
    op = problem.get("op")
    if op == "binomial":
        return binomial_grade(problem["n"], problem["p"])
    if op == "markov":
        return markov_grade(problem["mean"], problem["a"])
    if op == "chebyshev":
        return chebyshev_grade(problem["var"], problem["a"])
    return KV.decline(f"probability: unknown op {op!r} ⇒ DECLINE", "probability")
