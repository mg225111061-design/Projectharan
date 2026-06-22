"""
Pillar 3 · ROUND 3 #72 — complexity certificate (prove the asymptotic CLASS actually improved, not just speed).
================================================================================================================
A speedup on one input size can be a mere constant factor. An ASYMPTOTIC win is different: the advantage grows
with n. This certificate measures the naive and fast region at several sizes, fits the empirical growth exponent
(log-log slope of time vs n), and certifies the fast version is in a STRICTLY LOWER complexity class
(fast_exponent < naive_exponent by a margin). It is an EMPIRICAL certificate ⇒ PROBABILISTIC (measured growth,
reported with the fitted exponents and R²) — never EXACT. Honesty: a pair in the SAME class (both ~O(n)) yields
≈equal exponents ⇒ NOT an asymptotic improvement ⇒ DECLINE (we never claim an asymptotic jump that isn't there).
This is the verification behind every "O(n²)→O(n log n)" claim: the class change is MEASURED, not asserted.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Callable, List, Tuple

import kernel_verdict as KV


@dataclass
class ComplexityCert:
    verdict: "KV.Verdict"
    naive_exp: float
    fast_exp: float
    naive_r2: float
    fast_r2: float
    sizes: Tuple[int, ...]


def _fit_loglog(sizes: List[int], times: List[float]) -> Tuple[float, float]:
    """Least-squares slope of log(time) vs log(n) = the empirical power-law exponent; also returns R²."""
    xs = [math.log(s) for s in sizes]
    ys = [math.log(max(t, 1e-9)) for t in times]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx if sxx else 0.0
    intercept = my - slope * mx
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    r2 = 1.0 - ss_res / ss_tot if ss_tot else 1.0
    return slope, r2


def _time_at(fn: Callable, make_input_n: Callable[[int], tuple], n: int, repeats: int) -> float:
    best = math.inf
    for _ in range(repeats):
        args = make_input_n(n)
        t = time.perf_counter()
        fn(*args)
        best = min(best, time.perf_counter() - t)            # best-of-k (robust to scheduling jitter)
    return best


def certify_complexity(naive: Callable, fast: Callable, make_input_n: Callable[[int], tuple],
                       sizes: Tuple[int, ...], *, margin: float = 0.4, repeats: int = 5) -> ComplexityCert:
    """Measure naive & fast at each size, fit the growth exponents, and certify fast is a STRICTLY LOWER class
    (naive_exp − fast_exp ≥ margin) with good fits. Else DECLINE (no asymptotic improvement — only constant factor)."""
    nt = [_time_at(naive, make_input_n, s, repeats) for s in sizes]
    ft = [_time_at(fast, make_input_n, s, repeats) for s in sizes]
    ne, nr2 = _fit_loglog(list(sizes), nt)
    fe, fr2 = _fit_loglog(list(sizes), ft)
    detail = f"naive ~O(n^{ne:.2f}) (R²={nr2:.2f}) vs fast ~O(n^{fe:.2f}) (R²={fr2:.2f}) over n∈{sizes}"
    if (ne - fe) < margin or nr2 < 0.9:
        v = KV.decline(f"no asymptotic-class improvement: {detail} (Δexp {ne - fe:.2f} < {margin}) ⇒ DECLINE", "complexity")
        return ComplexityCert(v, ne, fe, nr2, fr2, sizes)
    cert = KV.Cert(KV.PROBABILISTIC, "empirical_complexity", passed=True, check_cost=f"{len(sizes)} sizes ×{repeats}",
                   delta=round(1.0 - fr2, 4) + 1e-6, detail=detail + f"; Δexp={ne - fe:.2f} ⇒ strictly lower class")
    v = KV.probabilistic(fast, "complexity", detail, cert)
    return ComplexityCert(v, ne, fe, nr2, fr2, sizes)


# ── demo regions: a genuine asymptotic jump (O(n²)→O(n)) vs a mere constant-factor pair (both O(n)) ────────
def prefix_naive(a):
    out = []
    for i in range(len(a)):
        s = 0
        for j in range(i + 1):                               # O(n²) total
            s += a[j]
        out.append(s)
    return out


def prefix_fast(a):
    out = []
    s = 0
    for x in a:                                              # O(n) single pass
        s += x
        out.append(s)
    return out


def linear_slow(a):
    s = 0
    for x in a:                                              # O(n) with a big constant (3 ops/elem)
        s += (x * 3 + 1) - 1
    return s


def linear_fast(a):
    return sum(a)                                            # O(n) with a small constant — SAME class as linear_slow


def make_list_n(n: int):
    import random as _rnd
    rng = _rnd.Random(n * 2654435761 & 0xFFFFFFFF)
    return ([rng.randrange(-100, 100) for _ in range(n)],)
