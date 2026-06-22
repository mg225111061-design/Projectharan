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


# ── item 49 — membership filter (Bloom): exact O(n) list membership → O(1) filter, FP ε, NO false negatives ─
import math as _math


class Bloom:
    def __init__(self, n: int, fp: float = 0.01):
        n = max(1, n)
        self.m = max(8, int(-n * _math.log(fp) / (_math.log(2) ** 2)))
        self.k = max(1, int(round(self.m / n * _math.log(2))))
        self.bits = bytearray((self.m + 7) // 8)

    def _idx(self, x, i):
        return (hash((x, i, 0x9E3779B1)) % self.m)

    def add(self, x):
        for i in range(self.k):
            j = self._idx(x, i)
            self.bits[j >> 3] |= (1 << (j & 7))

    def __contains__(self, x):
        for i in range(self.k):
            j = self._idx(x, i)
            if not (self.bits[j >> 3] >> (j & 7)) & 1:
                return False
        return True


def membership_exact(pool, queries):                        # pool is a LIST ⇒ each `in` is O(n)
    return [q in pool for q in queries]


def membership_bloom(pool, queries):                        # O(1)/query, false-positive ε, zero false negatives
    b = Bloom(len(pool))
    for x in pool:
        b.add(x)
    return [q in b for q in queries]


def membership_bloom_broken(pool, queries):                 # adversarial: adds only half ⇒ FALSE NEGATIVES ⇒ DECLINE
    b = Bloom(len(pool))
    for x in pool[::2]:
        b.add(x)
    return [q in b for q in queries]


def bloom_grade(pool, queries, residual_iters=0, *, approx_fn=None, eps_target=0.08, n=0, samples=7):
    approx_fn = approx_fn or membership_bloom
    exact = membership_exact(pool, queries)
    approx = approx_fn(pool, queries)
    false_neg = sum(1 for e, a in zip(exact, approx) if e and not a)
    false_pos = sum(1 for e, a in zip(exact, approx) if a and not e)
    nonmembers = sum(1 for e in exact if not e)
    eps = false_pos / max(1, nonmembers)
    rep = LF.measure_lift(lambda p, q: membership_exact(p, q), lambda p, q: approx_fn(p, q),
                          lambda: (pool, queries), residual_iters, n=n, samples=samples)
    if false_neg > 0:                                       # the Bloom invariant: NO false negatives
        v = KV.decline(f"Bloom produced {false_neg} FALSE NEGATIVES (invariant broken) ⇒ DECLINE", "approx")
        v.report = rep
        return ApproxResult(v, eps, 0.0, rep.whole_program_ratio, rep.amdahl_ceiling)
    if eps > eps_target or not rep.beats(1.10):
        v = KV.decline(f"Bloom FP ε={eps:.3f} > {eps_target} or no win (×{rep.whole_program_ratio:.2f}) ⇒ DECLINE", "approx")
        v.report = rep
        return ApproxResult(v, eps, 0.0, rep.whole_program_ratio, rep.amdahl_ceiling)
    cert = KV.Cert(KV.PROBABILISTIC, "bloom_filter", passed=True, check_cost=f"{len(queries)} queries",
                   delta=max(eps, 1e-6), detail=f"false-positive ε={eps:.4f}, ZERO false negatives (verified)")
    v = KV.probabilistic(approx_fn, "approx", str(rep), cert)
    v.report = rep
    return ApproxResult(v, eps, 0.0, rep.whole_program_ratio, rep.amdahl_ceiling)


_BLOOM_CACHE: dict = {}


def make_bloom_input(npool=3000, nq=3000):
    key = (npool, nq)
    if key not in _BLOOM_CACHE:
        rng = _rnd.Random(101)
        pool = [rng.randrange(0, npool * 8) for _ in range(npool)]
        pset = set(pool)
        # ~30% members, 70% non-members (so the exact O(n) scan dominates and Bloom's O(1) pre-check wins)
        q = []
        for _ in range(nq):
            q.append(rng.choice(pool) if rng.random() < 0.3 else rng.randrange(npool * 8, npool * 16))
        _BLOOM_CACHE[key] = (pool, q)
    return _BLOOM_CACHE[key]

