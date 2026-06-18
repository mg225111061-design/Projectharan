"""
v33 STAGE 0 — three-clock measurement harness (Clock A / B / C never mixed; build-time is NOT a clock).
======================================================================================================
Every speed number in this project is labeled by the clock it belongs to. Mixing them is a lie (rule 5).

  • Clock A — the LLM call / spec.   Proxy here = SPEC SIZE (chars/tokens the model must read/emit). Live
                                     call latency needs a key+egress → [BLOCKED] (never a fake number).
  • Clock B — verification.          Wall-clock of checking a certificate (SMT solve, PIT, telescoping check).
  • Clock C — the EMITTED code.      Wall-clock of running the produced code (naive loop vs folded closed form).
  • build-time — offline "soup".     Proving 3000+ families, algorithm discovery, superopt. NOT a clock — it
                                     is paid ONCE at build and amortized; reported SEPARATELY (rule 7).

Reproducibility (rule 0.x / §0): `measure_repeat` runs k times and reports the MEDIAN + relative stdev so a
baseline is reproducible to <2% before we trust a before/after comparison.
"""
from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

CLOCKS = ("A", "B", "C")
BUILD_TIME = "build-time"          # explicitly NOT a clock


@dataclass
class Sample:
    label: str
    clock: str                     # "A" | "B" | "C" | "build-time"
    ms: float
    note: str = ""

    def __str__(self):
        tag = f"[Clock {self.clock}]" if self.clock in CLOCKS else f"[{self.clock}]"
        return f"{tag} {self.label}: {self.ms:.3f}ms {self.note}"


@dataclass
class RepeatStat:
    label: str
    clock: str
    median_ms: float
    rel_stdev: float               # stdev / mean (reproducibility proxy)
    n: int
    samples: List[float] = field(default_factory=list)

    @property
    def reproducible(self) -> bool:
        return self.rel_stdev < 0.02      # <2% (rule 0): trust before/after only when stable


def _time_ms(fn: Callable) -> float:
    t = time.perf_counter()
    fn()
    return (time.perf_counter() - t) * 1000.0


def measure(label: str, clock: str, fn: Callable, note: str = "") -> Sample:
    """One labeled timing. `clock` ∈ {A,B,C,build-time}."""
    assert clock in CLOCKS or clock == BUILD_TIME, f"unknown clock {clock}"
    return Sample(label, clock, _time_ms(fn), note)


def measure_repeat(label: str, clock: str, fn: Callable, k: int = 7, warmup: int = 1) -> RepeatStat:
    """Run `fn` k times (after `warmup`); report MEDIAN + relative stdev. Use for reproducible baselines."""
    for _ in range(warmup):
        fn()
    xs = [_time_ms(fn) for _ in range(k)]
    mean = statistics.mean(xs) or 1e-9
    return RepeatStat(label, clock, round(statistics.median(xs), 4),
                      round(statistics.pstdev(xs) / mean, 4), k, [round(x, 4) for x in xs])


# ── Clock A proxy: spec size (no live LLM here → call latency is [BLOCKED]) ──────────────────────────
def clock_A_spec_size(spec: str) -> Sample:
    """Clock A proxy = the size of the spec the model must read/emit (chars). Smaller spec ⇒ less Clock A.
    The actual call latency is [BLOCKED] (needs a key + egress)."""
    return Sample("spec_size", "A", float(len(spec)), note="(chars; live call latency [BLOCKED: key/egress])")


@dataclass
class BeforeAfter:
    label: str
    clock: str
    before_ms: float
    after_ms: float

    @property
    def ratio(self) -> float:
        return round(self.before_ms / self.after_ms, 3) if self.after_ms > 0 else 1.0

    @property
    def regressed(self) -> bool:
        # ★ runtime wall-clock regression = the after path is SLOWER than before (beyond 2% noise). ★
        return self.after_ms > self.before_ms * 1.02

    def __str__(self):
        verdict = "REGRESSION" if self.regressed else ("speedup" if self.ratio > 1.02 else "neutral")
        return f"[Clock {self.clock}] {self.label}: {self.before_ms:.3f}→{self.after_ms:.3f}ms ({self.ratio}×, {verdict})"


def before_after(label: str, clock: str, before_fn: Callable, after_fn: Callable, k: int = 7) -> BeforeAfter:
    """Median-of-k before vs after on the SAME clock — the honest regression test (rule 3)."""
    b = measure_repeat(label + "/before", clock, before_fn, k=k)
    a = measure_repeat(label + "/after", clock, after_fn, k=k)
    return BeforeAfter(label, clock, b.median_ms, a.median_ms)
