"""
Pillar 3 · Stage 5 — GPU/SIMD offload, Amdahl-gated and whole-program-honest (Rules 1/2 enforced hardest).
==========================================================================================================
A kernel speedup is NOT a whole-program speedup. Before offloading anything, this computes and SHOWS the Amdahl
ceiling 1/(1−f); if the kernel does not dominate (ceiling below a worthwhile threshold) it DECLINES the offload
as "not worth it" — even for a 700× kernel. When it does offload, it reports the WHOLE-PROGRAM ratio, never the
kernel ratio. GPU is absent in this sandbox ⇒ GPU offload is UNVERIFIED; SIMD/vectorize via numpy is real here.
"""
from __future__ import annotations

import math
import random as _rnd
from typing import Any, Callable, List, Optional, Tuple

import kernel_verdict as KV
from pillar3 import measure as M
from pillar3 import record as RC


# ── reusable SIMD demo kernels (a heavy element-wise transcendental map — numpy vectorizes it for real) ──
_SIMD_CACHE: dict = {}


def make_demo_input(size: int = 6000) -> tuple:
    if size not in _SIMD_CACHE:
        rng = _rnd.Random(7)
        _SIMD_CACHE[size] = [rng.uniform(0.0, 50.0) for _ in range(size)]
    return (_SIMD_CACHE[size],)


def scalar_demo_kernel(xs):
    return [math.sqrt(x) + math.sin(x) + math.cos(x) + math.log(x + 1.0) for x in xs]


def simd_demo_kernel(xs):
    import numpy as np
    a = np.asarray(xs, dtype=float)
    return np.sqrt(a) + np.sin(a) + np.cos(a) + np.log(a + 1.0)


def simd_demo_wrong(xs):
    import numpy as np
    a = np.asarray(xs, dtype=float)
    return np.sqrt(a) + np.sin(a) + np.cos(a) + np.log(a + 2.0)            # +2 ≠ +1 — differential refutes


def demo_eq(a, b) -> bool:
    import numpy as np
    return bool(np.allclose(np.asarray(a, dtype=float), np.asarray(b, dtype=float), rtol=1e-9, atol=1e-9))


def demo_cases(k: int = 4) -> List[tuple]:
    return [make_demo_input() for _ in range(k)]


def amdahl_gate(hotspot_fraction: float, min_speedup: float = 2.0) -> "tuple[bool, float]":
    """(worth_offloading, ceiling). The system states its own ceiling BEFORE attempting the offload (Rule 2)."""
    ceiling = (1.0 / (1.0 - hotspot_fraction)) if hotspot_fraction < 1.0 else float("inf")
    return (ceiling >= min_speedup, ceiling)


def consider_offload_coherent(scalar_kernel: Callable, simd_kernel: Callable, make_input: Callable[[], tuple],
                              residual_iters: int, *, n: int, oracle_cases: List[tuple], min_ceiling: float = 2.0,
                              floor: float = 1.10, eq: Optional[Callable] = None, samples: int = 7,
                              device: str = "simd") -> KV.Verdict:
    """PHASE O (deeper): Amdahl-gate on the MEASURED hotspot fraction, then a coherent whole-program measurement
    (residual + kernel, via the lifting floor-pipeline so ratio ≤ ceiling by construction). The SIMD/numpy path is
    measured for real; GPU is UNVERIFIED [no GPU]; a non-dominant kernel DECLINEs even if its kernel speedup is
    huge (700× kernel at 4% of runtime ⇒ ≤1.04× whole-program ⇒ DECLINE). Float outputs ⇒ PROBABILISTIC, never EXACT."""
    from pillar3 import lifting as LF
    from pillar3 import record as RC

    if device == "gpu":
        return KV.decline("GPU offload UNVERIFIED [BLOCKED: no GPU in sandbox] — candidate built, excluded from "
                          "auto-apply (Rule 6); the SIMD/numpy path is the verified one here", "offload")
    # differential FIRST (float-tolerant): the scalar kernel is the gold oracle
    oracle = RC.record_oracle(scalar_kernel, oracle_cases)
    diff = RC.differential_test(simd_kernel, oracle, eq)
    if not diff.passed:
        return KV.decline(f"vectorized kernel diverges ({diff.mismatches}/{diff.n}) ⇒ DECLINE", "offload")
    # coherent whole-program measurement: f is MEASURED, ratio ≤ ceiling by construction
    rep = LF.measure_lift(scalar_kernel, simd_kernel, make_input, residual_iters, n=n, samples=samples)
    worth, ceiling = amdahl_gate(rep.hotspot_fraction, min_ceiling)
    if not worth:
        return KV.decline(f"offload NOT worth it: kernel is only {rep.hotspot_fraction:.0%} of runtime → Amdahl "
                          f"ceiling {ceiling:.2f}× < {min_ceiling}× whole-program ⇒ DECLINE (even a huge kernel "
                          f"speedup can't help here)", "offload")
    if not rep.beats(floor):
        v = KV.decline(f"vectorized but no whole-program win ≥ {floor:.2f}× (measured {rep.whole_program_ratio:.2f}×, "
                       f"ceiling {rep.amdahl_ceiling:.2f}×) ⇒ DECLINE", "offload")
        v.report = rep
        return v
    cert = KV.Cert(KV.PROBABILISTIC, "differential", passed=True, check_cost=f"{diff.n} float cases",
                   delta=diff.rule_of_three_delta,
                   detail=f"SIMD/numpy vectorized; whole-program (NOT kernel) ratio; Amdahl ceiling "
                          f"{rep.amdahl_ceiling:.1f}×; floats ⇒ PROBABILISTIC (never EXACT)")
    v = KV.probabilistic(simd_kernel, "offload", str(rep), cert)
    v.report = rep
    return v


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
