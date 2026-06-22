"""
Pillar 3 · ROUND 2 — the Ω(N) side-door: trade exactness for sublinearity (PROBABILISTIC, REPORT ε,δ).
=====================================================================================================
An exact aggregate over N items is Ω(N). The side-door: SAMPLE k≪N items and answer within ε with confidence
1−δ — cost independent of N. This is **never EXACT**: it is PROBABILISTIC and the ε,δ are first-class and
reported. `approx_grade` measures the whole-program speedup (coherent, ratio ≤ ceiling) AND the empirical ε
(95th-pct relative error over many trials) and δ (fraction outside the ε target); a biased estimator whose
error exceeds the target ⇒ DECLINE (the safety net — you cannot ship an approximation that isn't within ε).
"""
from __future__ import annotations

import random as _rnd
from dataclasses import dataclass
from typing import Any, Callable, Tuple

import kernel_verdict as KV
from pillar3 import lifting as LF


@dataclass
class ApproxResult:
    verdict: "KV.Verdict"
    eps: float
    delta: float
    ratio: float
    ceiling: float


def approx_grade(exact_fn: Callable, approx_fn: Callable, make_input: Callable[[], tuple], residual_iters: int,
                 *, eps_target: float, n: int, samples: int = 7, trials: int = 60) -> ApproxResult:
    """Grade an APPROXIMATION. ε = 95th-percentile relative error of approx vs exact over `trials` inputs;
    δ = fraction of trials outside eps_target. PROBABILISTIC(ε,δ) iff ε ≤ target AND δ small AND a measured win;
    else DECLINE. Approximation is NEVER EXACT (Constitution Rule 3)."""
    errs = []
    for _ in range(trials):
        args = make_input()
        e = float(exact_fn(*args))
        a = float(approx_fn(*args))
        errs.append(abs(a - e) / (abs(e) + 1e-9))
    errs.sort()
    eps = errs[min(len(errs) - 1, int(0.95 * len(errs)))]
    delta = sum(1 for x in errs if x > eps_target) / len(errs)
    rep = LF.measure_lift(exact_fn, approx_fn, make_input, residual_iters, n=n, samples=samples)
    if eps > eps_target or delta > 0.1:
        v = KV.decline(f"approximation ε={eps:.4f} > target {eps_target} (δ={delta:.2f}) ⇒ DECLINE", "approx")
        v.report = rep
        return ApproxResult(v, eps, delta, rep.whole_program_ratio, rep.amdahl_ceiling)
    if not rep.beats(1.10):
        v = KV.decline(f"approximation within ε but no whole-program win (×{rep.whole_program_ratio:.2f}) ⇒ DECLINE", "approx")
        v.report = rep
        return ApproxResult(v, eps, delta, rep.whole_program_ratio, rep.amdahl_ceiling)
    cert = KV.Cert(KV.PROBABILISTIC, "sampling_approximation", passed=True, check_cost=f"{trials} trials",
                   delta=max(delta, 1e-6), detail=f"ε={eps:.4f} (95th pct), within-target {(1-delta):.0%}, cost ⟂ N")
    v = KV.probabilistic(approx_fn, "approx", str(rep), cert)
    v.report = rep
    return ApproxResult(v, eps, delta, rep.whole_program_ratio, rep.amdahl_ceiling)


# ── item 46 — sublinear approximation by sampling (mean of a huge array): O(N) → O(k), cost ⟂ N ──────────
_BIG_CACHE: dict = {}


def _make_big(n: int = 500000):
    if n not in _BIG_CACHE:
        rng = _rnd.Random(91)
        # bounded-variance values so a sample mean is within a few % of the true mean
        _BIG_CACHE[n] = [rng.gauss(100.0, 15.0) for _ in range(n)]
    return (_BIG_CACHE[n],)


def mean_exact(a):
    return sum(a) / len(a)


def mean_sampled(a):                                        # O(k): a fixed-size random sample, cost independent of N
    n = len(a)
    k = 2000
    if n <= k:
        return sum(a) / n
    rng = _rnd.Random(7)
    s = 0.0
    for _ in range(k):
        s += a[rng.randrange(n)]
    return s / k


def mean_biased(a):                                        # adversarial: only the smallest region ⇒ biased estimate
    k = 2000
    if len(a) <= k:
        return sum(a) / len(a)
    head = sorted(a[: k * 3])[:k]                          # systematically low ⇒ ε large ⇒ DECLINE
    return sum(head) / k
