"""
Pillar 3 · Stage 0 — profiler (GROUND TRUTH for where time goes; Rule 5).
==========================================================================
Runs a target entrypoint under cProfile, returns cost centers ranked by cumulative time with each function's
share of total runtime (the Amdahl input). Warmup-aware. The LLM/heuristics never decide where the time goes —
this does.
"""
from __future__ import annotations

import cProfile
import pstats
import time
from dataclasses import dataclass, field
from typing import Callable, List, Tuple


@dataclass
class Hotspot:
    name: str                   # "file:lineno(func)"
    cumtime: float              # cumulative seconds (incl. callees)
    tottime: float              # seconds in this function only (exclusive)
    fraction: float             # tottime / total exclusive time = this function's share of runtime (Amdahl)
    ncalls: int


@dataclass
class ProfileResult:
    hotspots: List[Hotspot] = field(default_factory=list)   # ranked by cumtime (where time goes)
    total_s: float = 0.0                                     # wall-clock of the profiled run

    def top(self) -> Hotspot:
        return self.hotspots[0]

    def hotspot_fraction(self, name_substr: str = None) -> float:
        """Share of runtime of the top hotspot (or the first whose name matches name_substr). This is the
        Amdahl input handed to the measure harness."""
        if name_substr is not None:
            for h in self.hotspots:
                if name_substr in h.name:
                    return h.fraction
            return 0.0
        return self.hotspots[0].fraction if self.hotspots else 0.0


def profile(entrypoint: Callable, *args, warmup: int = 1, exclude_substr: Tuple[str, ...] = ("profiler.py",)) -> ProfileResult:
    """Profile one call of `entrypoint(*args)` (after `warmup` untimed runs). Returns hotspots ranked by
    cumulative time with each function's exclusive-time fraction of the run."""
    for _ in range(warmup):
        entrypoint(*args)
    pr = cProfile.Profile()
    t0 = time.perf_counter()
    pr.enable()
    entrypoint(*args)
    pr.disable()
    total = time.perf_counter() - t0
    st = pstats.Stats(pr)
    rows: List[Hotspot] = []
    tot_excl = 0.0
    raw = []
    for func, (cc, nc, tt, ct, _callers) in st.stats.items():       # (file, line, name)
        fname = f"{func[0].split('/')[-1]}:{func[1]}({func[2]})"
        if any(x in fname for x in exclude_substr):
            continue
        raw.append((fname, ct, tt, cc))
        tot_excl += tt
    for fname, ct, tt, cc in raw:
        rows.append(Hotspot(fname, ct, tt, (tt / tot_excl) if tot_excl > 0 else 0.0, cc))
    rows.sort(key=lambda h: h.cumtime, reverse=True)
    return ProfileResult(rows, total)


def rank_by_self_time(pr: ProfileResult) -> List[Hotspot]:
    """The functions doing the most EXCLUSIVE work (the true fix targets), highest fraction first."""
    return sorted(pr.hotspots, key=lambda h: h.tottime, reverse=True)
