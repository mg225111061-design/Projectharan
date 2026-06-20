"""
Pillar 3 · Stage 0 — neutral-baseline WHOLE-PROGRAM measurement harness (the single source of truth).
======================================================================================================
Every speedup number in Pillar 3 comes from here. A SpeedupReport REFUSES to exist without `n` and
`hotspot_fraction` (Rule 1/2) — so no number can be reported without its operating point and its Amdahl
ceiling. The ratio is a measured, warmup-aware, median wall-clock ratio of the WHOLE program (Clock C).
Kernel speedup is never reported here; only whole-program.
"""
from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class SpeedupReport:
    whole_program_ratio: float          # measured orig_median / cand_median (Clock C, whole program)
    hotspot_fraction: float             # fraction of original runtime in the region being fixed (Amdahl input)
    n: int                              # the operating-point workload size (a ratio is meaningless without it)
    samples: int
    warmup_discarded: int
    orig_median_s: float
    cand_median_s: float
    amdahl_ceiling: float = 0.0         # 1/(1-hotspot_fraction); the system states its own ceiling (Rule 2)

    def __post_init__(self):
        if self.n is None or self.hotspot_fraction is None:
            raise ValueError("SpeedupReport refuses to exist without n AND hotspot_fraction (Rule 1/2)")
        if not (0.0 <= self.hotspot_fraction <= 1.0):
            raise ValueError(f"hotspot_fraction must be in [0,1], got {self.hotspot_fraction}")
        self.amdahl_ceiling = (1.0 / (1.0 - self.hotspot_fraction)) if self.hotspot_fraction < 1.0 else float("inf")

    def beats(self, floor: float) -> bool:
        return self.whole_program_ratio >= floor

    def __str__(self):
        return (f"{self.whole_program_ratio:.2f}× whole-program @n={self.n} "
                f"(hotspot {self.hotspot_fraction:.0%}, Amdahl ceiling {self.amdahl_ceiling:.1f}×; "
                f"orig {self.orig_median_s*1e3:.2f}ms → cand {self.cand_median_s*1e3:.2f}ms, "
                f"median of {self.samples}, {self.warmup_discarded} warmup discarded)")


def time_median(fn: Callable, make_args: Callable[[], tuple], samples: int = 7, warmup: int = 1) -> float:
    """Median wall-clock of fn over `samples` runs after discarding `warmup` (fresh args each run so mutation
    or caching inside the candidate cannot leak across runs)."""
    for _ in range(warmup):
        fn(*make_args())
    ts = []
    for _ in range(samples):
        args = make_args()
        t = time.perf_counter()
        fn(*args)
        ts.append(time.perf_counter() - t)
    return statistics.median(ts)


def time_best(fn: Callable, make_args: Callable[[], tuple], samples: int = 7, warmup: int = 1) -> float:
    """Best-of-k (minimum) wall-clock — the least-contended run. For CPU-bound deterministic work the minimum is
    the most stable estimator of the true cost (it filters ALL upward OS/GC contention, which the median does
    not when a spike is sustained across several samples). Fresh args each run."""
    for _ in range(warmup):
        fn(*make_args())
    best = float("inf")
    for _ in range(samples):
        args = make_args()
        t = time.perf_counter()
        fn(*args)
        best = min(best, time.perf_counter() - t)
    return best


def measure_whole_program(original: Callable, candidate: Callable, make_args: Callable[[], tuple], *,
                          n: int, hotspot_fraction: float, samples: int = 7, warmup: int = 1,
                          timer: Callable = None) -> SpeedupReport:
    """The neutral-baseline whole-program ratio: timer(original) / timer(candidate) on the SAME workload, at the
    original's normal optimization level. `timer` defaults to the median; pass `time_best` for CPU-bound work
    where the minimum (least-contended run) is the more stable estimator. `hotspot_fraction` comes from the
    profiler (the Amdahl input). Refuses to produce a number without n and hotspot_fraction."""
    if n is None or hotspot_fraction is None:
        raise ValueError("measure_whole_program requires n AND hotspot_fraction (Rule 1/2)")
    timer = timer or time_median
    orig = timer(original, make_args, samples, warmup)
    cand = timer(candidate, make_args, samples, warmup)
    ratio = orig / cand if cand > 0 else float("inf")
    return SpeedupReport(whole_program_ratio=ratio, hotspot_fraction=hotspot_fraction, n=n,
                         samples=samples, warmup_discarded=warmup, orig_median_s=orig, cand_median_s=cand)


def amdahl_ceiling(hotspot_fraction: float) -> float:
    """max_possible_speedup = 1/(1-f). The system states its own ceiling BEFORE attempting a fix (Rule 2)."""
    return (1.0 / (1.0 - hotspot_fraction)) if hotspot_fraction < 1.0 else float("inf")
