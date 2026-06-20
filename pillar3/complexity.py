"""
Pillar 3 · Stage 0 — empirical computational complexity fitter (the flagship detector).
========================================================================================
The Goldsmith–Aiken–Wilkerson (ESEC-FSE 2007) trend-prof method: run a target across input sizes spanning
orders of magnitude, fit time (or op-count) to a power law y = a·n^b by least squares on log-log, and report
the empirical exponent b with R². An exponent meaningfully above the expected one flags an accidental
super-linearity ("empirically O(n^1.97), R²=0.99 → likely accidentally quadratic"). Pure numpy.
"""
from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from typing import Callable, List

import numpy as np


@dataclass
class ComplexityFit:
    exponent: float             # fitted b in y = a·n^b
    coeff: float                # fitted a
    r2: float                   # goodness of fit on log-log
    sizes: List[int]
    times: List[float]
    klass: str                  # human label: "O(1)" "O(log n)" "O(n)" "O(n log n)" "O(n^b)" …
    superlinear: bool           # b meaningfully > 1 (after log-correction heuristic)

    def __str__(self):
        return (f"empirically {self.klass} (b={self.exponent:.2f}, R²={self.r2:.3f}) over "
                f"n∈[{self.sizes[0]},{self.sizes[-1]}]" + ("  ⚠ super-linear" if self.superlinear else ""))


def fit_power_law(sizes: List[int], times: List[float]) -> "tuple[float, float, float]":
    """log(t) = log(a) + b·log(n) least squares. Returns (b, a, R²)."""
    x = np.log(np.asarray(sizes, dtype=float))
    y = np.log(np.asarray(times, dtype=float))
    A = np.vstack([x, np.ones_like(x)]).T
    (b, loga), *_ = np.linalg.lstsq(A, y, rcond=None)
    yhat = A @ np.array([b, loga])
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return float(b), float(np.exp(loga)), r2


def _classify(b: float, sizes: List[int], times: List[float]) -> "tuple[str, bool]":
    """Map the exponent to a class. n·log n looks like n^~1.1 on a power-law fit, so we test an n·log n model
    too and prefer it when it fits better than a pure power law near b≈1."""
    if b < 0.3:
        return "O(1)", False
    if b < 0.85:
        # could be O(log n): fit t = a·log n
        x = np.log(np.asarray(sizes, dtype=float))
        y = np.asarray(times, dtype=float)
        if np.corrcoef(x, y)[0, 1] > 0.97:
            return "O(log n)", False
        return f"O(n^{b:.2f})", False
    if b <= 1.2:
        # distinguish O(n) from O(n log n) by which model fits the raw data better (R² of a least-squares fit)
        n = np.asarray(sizes, dtype=float)
        t = np.asarray(times, dtype=float)

        def r2_model(basis):
            A = np.vstack([basis, np.ones_like(basis)]).T
            coef, *_ = np.linalg.lstsq(A, t, rcond=None)
            yhat = A @ coef
            ss_res = float(np.sum((t - yhat) ** 2))
            ss_tot = float(np.sum((t - t.mean()) ** 2))
            return 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
        if r2_model(n * np.log(n)) > r2_model(n) + 1e-6:
            return "O(n log n)", False
        return "O(n)", False
    if b < 1.6:
        return f"O(n^{b:.2f})", True
    if b < 2.4:
        return "O(n²)", True
    if b < 3.4:
        return "O(n³)", True
    return f"O(n^{b:.2f})", True


def measure_complexity(fn: Callable[[int], None], sizes: List[int], *, samples: int = 3, warmup: int = 1) -> ComplexityFit:
    """Time `fn(n)` at each size (median of `samples`), fit the power law, classify, flag super-linearity."""
    times = []
    for n in sizes:
        for _ in range(warmup):
            fn(n)
        rs = []
        for _ in range(samples):
            t = time.perf_counter()
            fn(n)
            rs.append(time.perf_counter() - t)
        times.append(statistics.median(rs))
    b, a, r2 = fit_power_law(sizes, times)
    klass, superlinear = _classify(b, sizes, times)
    return ComplexityFit(b, a, r2, list(sizes), times, klass, superlinear)


def fit_counts(sizes: List[int], counts: List[int]) -> ComplexityFit:
    """Same fit but on op-COUNTS (deterministic, noise-free) instead of wall-clock — preferred when a counter
    is available (trend-prof fits basic-block run counts, not time)."""
    b, a, r2 = fit_power_law(sizes, [float(c) for c in counts])
    klass, superlinear = _classify(b, sizes, [float(c) for c in counts])
    return ComplexityFit(b, a, r2, list(sizes), [float(c) for c in counts], klass, superlinear)
