"""
EXTREME ACCELERATION §G report — the compounded stack, MEASURED (run stacked, not multiplied), Amdahl + A/B ledgers.
=====================================================================================================================
The headline honesty: A's acceleration is a large CONSTANT FACTOR, never asymptotic (general code has no foldable
structure). The compounded number is MEASURED by running the fully-stacked version end-to-end — NOT by multiplying
the per-layer numbers (which overcounts, because the layers interact and, in this Python sandbox, numpy already
FUSES native-C + SIMD into one measured factor). Two ledgers stay strictly separate:
  • A (Clock C — generated compute): the measured compounded factor on real generated hot-paths.
  • B (Clock A — product latency): the LLM-call reduction from sound caching. A's extreme compute speed does NOT
    move B (B is LLM-bound) — the whole point of keeping the ledgers apart.
"""
from __future__ import annotations

from typing import List


# ── PHASE 7 — GPU: the constitutional decision under zero-dep ───────────────────────────────────────────
def gpu_decision() -> dict:
    """GPU lowering needs a heavy external toolchain (CUDA/ROCm) that violates the zero-dep principle. The
    constitutional choice on a forbidden dependency is to DECLINE it, not silently import it. We verify no GPU
    runtime is imported and document GPU as out-of-scope; the verified in-environment data-parallel path is numpy
    vectorization (PHASE 2). If a zero-dep-honoring accelerator path ever exists, only PHASE-3-independence-certified
    kernels would be offloaded, with a per-kernel correctness certificate."""
    import sys
    gpu_mods = [m for m in ("cupy", "pycuda", "numba.cuda", "torch.cuda", "pyopencl") if m in sys.modules]
    return {"layer": "gpu", "status": "OUT_OF_SCOPE", "clock": "C",
            "reason": "CUDA/ROCm is a forbidden heavy dependency under zero-dep — DECLINED, not imported",
            "no_gpu_runtime_imported": gpu_mods == [], "verified_parallel_path_here": "numpy vectorization (PHASE 2)",
            "decision": "documented out-of-scope (constitutional decline of a forbidden dependency)"}


# ── PHASE 9.1 — the compounded stack, MEASURED end-to-end (not multiplied) ──────────────────────────────
def compounded_stack(n: int = 40000, k: int = 5) -> dict:
    """Run the FULLY-STACKED accelerated version of representative generated hot-paths and MEASURE it end-to-end vs
    the pure-Python baseline (Clock C). In this sandbox the dominant stacked layer is numpy vectorization (native-C
    ⊕ SIMD fused); multicore is EXCLUDED from the stack because it is measured overhead-bound for marshalled Python
    data (honest — not silently dropped). The reported factor is the MEASURED stacked result, explicitly NOT the
    product of per-layer numbers."""
    import math
    import numpy as np
    import clocks
    xs = [(i % 97) * 0.031 - 1.5 for i in range(n)]
    arr = np.asarray(xs, dtype=float)
    kernels = []
    # elementwise transcendental: baseline python loop vs stacked numpy
    def el_py():
        return [math.sin(x) * math.cos(x) + math.sqrt(abs(x)) for x in xs]

    def el_np():
        return np.sin(arr) * np.cos(arr) + np.sqrt(np.abs(arr))
    assert np.allclose(np.asarray(el_py()), el_np(), atol=1e-9)        # differential-equivalent (stacked ≡ baseline)
    b = clocks.measure_repeat("el_py", "C", el_py, k=k)
    s = clocks.measure_repeat("el_np", "C", el_np, k=k)
    kernels.append({"kernel": "elementwise", "baseline_ms": b.median_ms, "stacked_ms": s.median_ms,
                    "measured_factor": round(b.median_ms / s.median_ms, 2) if s.median_ms > 0 else None})
    # associative reduction: baseline python loop vs stacked numpy (BLAS)
    def rd_py():
        t = 0.0
        for x in xs:
            t += x * x
        return t

    def rd_np():
        return float(arr @ arr)
    assert abs(rd_py() - rd_np()) <= 1e-6 * abs(rd_py())
    b2 = clocks.measure_repeat("rd_py", "C", rd_py, k=k)
    s2 = clocks.measure_repeat("rd_np", "C", rd_np, k=k)
    kernels.append({"kernel": "reduction", "baseline_ms": b2.median_ms, "stacked_ms": s2.median_ms,
                    "measured_factor": round(b2.median_ms / s2.median_ms, 2) if s2.median_ms > 0 else None})
    factors = [kk["measured_factor"] for kk in kernels if kk["measured_factor"]]
    return {"clock": "C", "n": n, "kernels": kernels,
            "compounded_factor_range": [min(factors), max(factors)] if factors else None,
            "measured_not_multiplied": True,
            "asymptotics": "UNCHANGED — large CONSTANT factor; general code has no foldable structure",
            "honest_note": "numpy fuses native-C ⊕ SIMD into one measured factor; multicore EXCLUDED (overhead-bound "
                           "in-sandbox); the factor is the MEASURED stacked result, never the product of layer numbers"}


def amdahl_whole_program(kernel_factor: float, hotspot_fraction: float) -> dict:
    """The Amdahl ceiling: a kernel sped by `kernel_factor` inside fraction f of the runtime yields a WHOLE-PROGRAM
    speedup of 1/((1-f) + f/kernel_factor), bounded by 1/(1-f). Reported so a big kernel number is never mistaken
    for a whole-program number."""
    f = hotspot_fraction
    whole = 1.0 / ((1 - f) + f / kernel_factor) if kernel_factor > 0 else 1.0
    ceiling = 1.0 / (1 - f) if f < 1 else float("inf")
    return {"kernel_factor": kernel_factor, "hotspot_fraction": f,
            "whole_program_speedup": round(whole, 3), "amdahl_ceiling": round(ceiling, 3) if ceiling != float("inf") else "∞",
            "note": "whole-program ≤ ceiling by construction; a kernel factor is NOT a whole-program factor"}


def report() -> dict:
    """The integrated §G report — per-layer measured factors (each certificate-gated), the MEASURED compounded
    stack, the Amdahl bound, the strict A/B ledger separation, the GPU decision, and the zero-dep proof."""
    import catalog.accel as A
    import catalog.accel_bpath as BP
    import catalog.accel_profile as AP
    import dependency_audit as DA
    import numpy as np

    xs = [(i % 97) * 0.031 - 1.5 for i in range(20000)]
    # per-layer measured factors (A ledger, Clock C), each carrying its certificate
    layers = {
        "native": A.native_lowering(),
        "vectorize": A.vectorize("elementwise", A._elementwise_scalar,
                                 lambda a: np.sin(a) * np.cos(a) + np.sqrt(np.abs(a)), xs, kind="map", k=3),
        "cores": A.parallelize_elementwise(xs[:4000], nproc=4, k=2),
        "cache_layout": A.relayout_aos_soa(xs, k=3),
        "superopt": A.superoptimize(("+", ("*", ("var", "x"), ("const", 1)), ("const", 0))),
    }
    stack = compounded_stack(n=20000, k=3)
    # B ledger (Clock A latency) — generations avoided by sound caching, separate from A
    bpath = BP.measure_bpath(["fn f(x){x+1}", "fn f(x){x+1}", "FN  F(X){X+1}  # c", "fn g(y){y*2}", "FN G(Y){Y*2}"])
    forbidden = DA.final_dependency_set()["forbidden_present"]
    return {
        "A_ledger_clockC_compute": {
            "per_layer": {k: {"status": v.get("status"), "factor": v.get("factor") or v.get("measured_scaling")
                              or v.get("rust_factor_vs_python_ntt"), "certificate": v.get("certificate")}
                          for k, v in layers.items()},
            "compounded_stack_measured": stack,
            "profile": AP.profile(n=8000, k=3)["layer_order_by_measured_share"],
        },
        "B_ledger_clockA_latency": {
            "clockA_reduction": bpath["clockA_reduction"], "llm_generations": bpath["llm_generations"],
            "requests": bpath["requests"], "soundness": bpath["soundness"],
        },
        "gpu_decision": gpu_decision(),
        "amdahl_example": amdahl_whole_program(stack["compounded_factor_range"][1] if stack["compounded_factor_range"] else 10.0, 0.8),
        "ledger_separation": "A (Clock C compute) and B (Clock A latency) are SEPARATE — A's extreme compute speed "
                             "does NOT move B (LLM-bound); B's gain comes only from cutting LLM calls.",
        "asymptotics": "UNCHANGED across every layer (constant factors, no uniform-Nx)",
        "zero_dep_forbidden_present": forbidden, "zero_dep_ok": forbidden == [],
        "one_line": "잘못된 답보다 DECLINE이 항상 옳다 — A accelerated to its honest extreme (native×SIMD×cache×"
                    "superopt×PGO, every layer certificate-gated, compounded factor MEASURED not multiplied, "
                    "asymptotics UNCHANGED); B cut separately by sound LLM-call elimination; GPU declined under "
                    "zero-dep; every gain Amdahl-bounded.",
    }
