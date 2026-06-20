"""
Pillar 3 · Stage 5 — GPU/SIMD offload, Amdahl-gated and whole-program-honest (Rules 1/2 enforced hardest).
==========================================================================================================
A kernel speedup is NOT a whole-program speedup. Before offloading anything, this computes and SHOWS the Amdahl
ceiling 1/(1−f); if the kernel does not dominate (ceiling below a worthwhile threshold) it DECLINES the offload
as "not worth it" — even for a 700× kernel. When it does offload, it reports the WHOLE-PROGRAM ratio, never the
kernel ratio. GPU is absent in this sandbox ⇒ GPU offload is UNVERIFIED; SIMD/vectorize via numpy is real here.
"""
from __future__ import annotations

from typing import Any, Callable, List, Optional, Tuple

import kernel_verdict as KV
from pillar3 import measure as M
from pillar3 import record as RC


def amdahl_gate(hotspot_fraction: float, min_speedup: float = 2.0) -> "tuple[bool, float]":
    """(worth_offloading, ceiling). The system states its own ceiling BEFORE attempting the offload (Rule 2)."""
    ceiling = (1.0 / (1.0 - hotspot_fraction)) if hotspot_fraction < 1.0 else float("inf")
    return (ceiling >= min_speedup, ceiling)


def consider_offload(slow_fn: Callable, fast_fn: Callable, make_args: Callable[[], tuple], *,
                     n: int, hotspot_fraction: float, oracle: List[Tuple[tuple, Any]],
                     kernel_speedup_hint: float = None, min_speedup: float = 2.0, floor: float = 1.20,
                     eq: Callable[[Any, Any], bool] = None, samples: int = 5, device: str = "simd") -> KV.Verdict:
    """Amdahl-gate FIRST: if the kernel doesn't dominate, DECLINE without offloading (no false big number). GPU
    device ⇒ UNVERIFIED (absent). Otherwise verify + measure WHOLE-PROGRAM (never kernel) + grade."""
    worth, ceiling = amdahl_gate(hotspot_fraction, min_speedup)
    if not worth:
        hint = f"a {kernel_speedup_hint:.0f}× kernel would still be only " if kernel_speedup_hint else ""
        return KV.decline(f"offload NOT worth it: kernel is {hotspot_fraction:.0%} of runtime → Amdahl ceiling "
                          f"{ceiling:.2f}× < {min_speedup}× ({hint}≤{ceiling:.2f}× whole-program) ⇒ DECLINE", "offload")
    if device == "gpu":
        return KV.decline("GPU offload UNVERIFIED [BLOCKED: no GPU in sandbox] — transform built, excluded "
                          "from auto-apply (Rule 6); SIMD/vectorize path is the verified one here", "offload")
    diff = RC.differential_test(fast_fn, oracle, eq)
    if not diff.passed:
        return KV.decline(f"offloaded kernel diverges ({diff.mismatches}/{diff.n}) ⇒ DECLINE", "offload")
    rep = M.measure_whole_program(slow_fn, fast_fn, make_args, n=n, hotspot_fraction=hotspot_fraction, samples=samples)
    if not rep.beats(floor):
        v = KV.decline(f"offloaded but no whole-program win ≥ {floor:.2f}× (measured {rep.whole_program_ratio:.2f}×, "
                       f"ceiling {ceiling:.2f}×) ⇒ DECLINE", "offload")
        v.report = rep
        return v
    cert = KV.Cert(KV.PROBABILISTIC, "differential", passed=True, check_cost=f"O(n)={diff.n} cases",
                   delta=diff.rule_of_three_delta,
                   detail=f"SIMD/vectorized; whole-program (NOT kernel) ratio; Amdahl ceiling {ceiling:.1f}×")
    v = KV.probabilistic(fast_fn, "offload", str(rep), cert)
    v.report = rep
    return v
