"""
v26.2 STAGE 9a — sound runtime-transform analyzer + differential-equivalence gate (3-tier ceiling).
====================================================================================================
"Speed up the disordered (non-mathematical) domain — but only where structure is PROVABLE, and never
change the answer." This is the verification half of the runtime engine. It does two things:

  1. analyze(kernel)  → a 3-TIER classification with a safety decision (the honest ceiling, §1.3/§3):
       tier A  — provably parallel/vectorizable: a reduction with an ASSOCIATIVE op, or an elementwise
                 MAP, with NO loop-carried dependence and NO aliasing/escape (no type-punning/raw view).
                 (anchors: simdjson 4–25×, SoA 6–13×, vector crypto ~2× — IN NATIVE CODE.)
       tier B  — 1–3× at best: general control flow, data-structure swaps, bounds-check elision.
       tier C  — ~1× PHYSICS FLOOR, no speedup promised: latency-bound IO, truly random data
                 (Kolmogorov), inherently sequential dependence.
  2. measure(scalar_fn, fast_fn, data) → run BOTH, assert DIFFERENTIAL EQUIVALENCE (identical output —
       ★ never a wrong transform ★), measure wall-clock, return the speedup. <1.1× ⇒ NO_GAIN (revert,
       §1.10). Output mismatch ⇒ MISMATCH (reject).

★ HONEST LIMIT (this sandbox) ★: no numpy / no native backend, so true SIMD speedups are NOT measurable
here — a SIMD-eligible (tier A) kernel is classified as such but its speedup is reported
[BLOCKED: no SIMD/native backend]. The measurable runtime win in this environment is associative
PARALLELISM (see parallel_algebra.py: 1.76× on 4 cores). The analyzer + equivalence gate are the
transferable contribution (they make the native transform SAFE to apply where a backend exists).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional

_ASSOC_OPS = {"+", "*", "max", "min", "and", "or"}


@dataclass
class Kernel:
    name: str
    kind: str                 # "reduction" | "map" | "io" | "random" | "sequential"
    op: Optional[str] = None  # for reductions
    loop_carried_dep: bool = False
    aliasing: bool = False    # pointer aliasing / escape / type-punning / raw serialization view


@dataclass
class TierVerdict:
    tier: str                 # A | B | C
    safe: bool                # safe to apply a parallel/vector transform
    reason: str
    def __str__(self):
        return f"tier {self.tier} (safe={self.safe}) — {self.reason}"


def analyze(k: Kernel) -> TierVerdict:
    if k.kind in ("io", "random", "sequential"):
        floor = {"io": "device-latency", "random": "Kolmogorov-incompressible", "sequential": "sequential-dependence"}
        return TierVerdict("C", False, f"tier-C physics floor ({floor[k.kind]}) — no speedup promised")
    if k.aliasing:
        return TierVerdict("B", False, "aliasing / escape / type-punning present — vector/layout transform "
                           "is UNSAFE here (cannot prove non-overlap); ≤ tier B with scalar-equivalent only")
    if k.loop_carried_dep:
        return TierVerdict("B", False, "loop-carried dependence — lanes not independent; not vectorizable")
    if k.kind == "reduction":
        if k.op in _ASSOC_OPS:
            return TierVerdict("A", True, f"associative reduction ('{k.op}'), lane-independent, no aliasing "
                               "→ parallel/vectorizable (lossless)")
        return TierVerdict("B", False, f"reduction op '{k.op}' not provably associative → not parallelizable")
    if k.kind == "map":
        return TierVerdict("A", True, "elementwise map, lane-independent, no aliasing → vectorizable")
    return TierVerdict("B", False, "no provable parallel/vector structure")


@dataclass
class TransformVerdict:
    status: str               # OPTIMIZED | NO_GAIN | MISMATCH | BLOCKED | DECLINED
    tier: str = "?"
    speedup: float = 1.0
    workload: str = ""
    detail: str = ""
    def __str__(self):
        if self.status == "OPTIMIZED":
            return f"OPTIMIZED (tier {self.tier}) {self.speedup:.2f}× ({self.workload}; equivalence verified)"
        return f"{self.status} (tier {self.tier}) — {self.detail or self.workload}"


def differential_equivalent(scalar_fn: Callable, fast_fn: Callable, samples) -> bool:
    """The never-a-wrong-transform gate: both implementations must agree on every sample."""
    return all(scalar_fn(s) == fast_fn(s) for s in samples)


def measure(kernel: Kernel, scalar_fn: Callable, fast_fn: Optional[Callable], data,
            equiv_samples=None, workload: str = "") -> TransformVerdict:
    """Classify, gate on differential equivalence, then measure scalar_fn vs fast_fn on `data`."""
    tv = analyze(kernel)
    if not tv.safe:
        return TransformVerdict("DECLINED", tier=tv.tier, detail=tv.reason)
    if fast_fn is None:
        return TransformVerdict("BLOCKED", tier=tv.tier, workload=workload,
                                detail="tier-A eligible but no native/SIMD backend in this sandbox to measure")
    samples = equiv_samples if equiv_samples is not None else [data]
    if not differential_equivalent(scalar_fn, fast_fn, samples):
        return TransformVerdict("MISMATCH", tier=tv.tier, detail="transformed output ≠ scalar reference — rejected")
    t = time.perf_counter(); r1 = scalar_fn(data); s_scalar = time.perf_counter() - t
    t = time.perf_counter(); r2 = fast_fn(data); s_fast = time.perf_counter() - t
    if r1 != r2:
        return TransformVerdict("MISMATCH", tier=tv.tier, detail="output mismatch on the measured input — rejected")
    speedup = s_scalar / s_fast if s_fast > 0 else 1.0
    if speedup < 1.1:
        return TransformVerdict("NO_GAIN", tier=tv.tier, speedup=speedup, workload=workload,
                                detail=f"measured {speedup:.2f}× (<1.1×) — reverted (§1.10)")
    return TransformVerdict("OPTIMIZED", tier=tv.tier, speedup=speedup, workload=workload)
