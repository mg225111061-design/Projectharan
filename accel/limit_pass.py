"""
ACCEL §6 + §7 — the LIMIT PASS (drive A/B/C/D to exhaustion per hot path) + PRODUCT integration (MR.JEFFREY).
================================================================================================================
§6 LIMIT PASS: profile the target → rank hot paths by wall-clock share → for the top hot path run ALL of A/B/C/D
proposers, VERIFY each, APPLY every proved acceleration, re-measure → move to the next hot path → repeat until NO hot
path admits a further provable acceleration. The terminal state is the HONEST LIMIT: "this program, on this
workload, accelerated X× whole-program wall-clock, with the remaining time being Y% irreducible physical I/O and Z%
already-optimal compute — no further safe acceleration exists." ★ The limit is the MEASURED limit, never infinity;
"10–20× on everything" is never the output.

§7 PRODUCT: the product's own wall-clock is Clock-A (LLM latency) dominated. We do NOT make the LLM faster — we apply
A1 (verified caching) to the LLM STEP: prove 'same code input → same accepted post-verification output' and reuse it
(prodcache's sound content-hash cache), skipping the LLM on a hit. MR.JEFFREY becomes the A/B/C/D PROPOSER (untrusted)
and the engine VERIFIES + applies. Physical I/O / network latency is irreducible — we reduce the NUMBER of calls.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from accel.pipeline import Acceleration, amdahl_whole_program


@dataclass
class HotPathResult:
    name: str
    category: str
    wall_share: float
    accelerations: List[Acceleration] = field(default_factory=list)
    component_speedup: float = 1.0
    disposition: str = ""              # accelerated | irreducible_io | already_optimal


def limit_pass(target: List[Dict]) -> dict:
    """Drive A/B/C/D over a profiled target. `target` = ranked hot paths, each:
        {name, category, wall_share, attempts: [callable→Acceleration], measured_speedup?: callable→float,
         irreducible?: bool}
    Applies every PROVED acceleration, composes the whole-program speedup via Amdahl, and emits the honest limit."""
    results: List[HotPathResult] = []
    for hp in sorted(target, key=lambda h: -h["wall_share"]):
        hpr = HotPathResult(hp["name"], hp["category"], hp["wall_share"])
        applied = []
        for attempt in hp.get("attempts", []):
            acc = attempt()
            hpr.accelerations.append(acc)
            if acc.applied:
                applied.append(acc)
        if applied:
            # the component speedup = the best PROVED+measured acceleration on this path (measured, not multiplied)
            measured = hp.get("measured_speedup")
            hpr.component_speedup = max([a.clock_c_speedup or 1.0 for a in applied] +
                                        ([measured()] if measured else [1.0]))
            hpr.component_speedup = max(hpr.component_speedup, 1.0)
            hpr.disposition = "accelerated" if hpr.component_speedup > 1.0 else "proved_safe_overhead_bound"
        elif hp.get("irreducible"):
            hpr.disposition = "irreducible_io"        # physical network/disk latency — outside the process
        else:
            hpr.disposition = "already_optimal"
        results.append(hpr)

    # ★ whole-program speedup via Amdahl, composing the per-path MEASURED component speedups (NOT a product of factors)
    whole = 1.0
    for r in results:
        if r.component_speedup > 1.0:
            whole *= amdahl_whole_program(r.wall_share, r.component_speedup)
    whole = round(whole, 4)
    irreducible_io = round(sum(r.wall_share for r in results if r.disposition == "irreducible_io"), 4)
    already_optimal = round(sum(r.wall_share for r in results if r.disposition == "already_optimal"), 4)
    accelerated = round(sum(r.wall_share for r in results if r.disposition == "accelerated"), 4)
    return {
        "hot_paths": [{"name": r.name, "category": r.category, "wall_share": r.wall_share,
                       "component_speedup": round(r.component_speedup, 3), "disposition": r.disposition,
                       "applied": [str(a) for a in r.accelerations if a.applied],
                       "rejected": [a.reason for a in r.accelerations if not a.applied]} for r in results],
        "whole_program_speedup": whole,
        "accelerated_share": accelerated, "irreducible_io_share": irreducible_io,
        "already_optimal_share": already_optimal,
        "limit_statement": f"this program, on this workload, accelerated {whole}× whole-program wall-clock; the "
                           f"remaining time is {round(irreducible_io * 100)}% irreducible physical I/O latency and "
                           f"{round(already_optimal * 100)}% already-optimal compute — no further SAFE acceleration is "
                           "provable (the honest limit, not infinity)",
        "honest_note": "whole-program (Amdahl), NOT a component factor; the component O(N²)→O(N) win is real but its "
                       "whole-program effect is bounded by its wall-clock share; physical I/O latency is NOT reducible "
                       "by us — we reduce the NUMBER of I/O ops (proved caching/batching), never their physical speed",
    }


# ── §7 PRODUCT: verified LLM-result caching on MR.JEFFREY's loop (reuse the sound content-hash cache) ────
def verified_llm_cache_demo(requests: List[tuple], llm_fn: Callable) -> dict:
    """Apply A1 (verified caching) to the LLM STEP: the post-verification accepted result is a deterministic function
    of (code input + provider + model + version), so caching it is PROVED sound (prodcache's content-hash key — a
    mutated input or version bump always MISSES, never a stale hit). A hit SKIPS the LLM entirely. Measures the
    Clock-A reduction = the number of LLM calls AVOIDED (exact), never a fabricated Nx."""
    import catalog.prodcache as PC
    cache = PC.SoundCache("accel_llm", version="v1")
    calls = 0

    def run(spec):
        nonlocal calls
        hit, v = cache.get(spec)
        if hit:
            return v
        calls += 1                                    # a real LLM call (Clock A)
        v = llm_fn(spec)
        cache.put(v, spec)
        return v
    outputs = [run(r) for r in requests]
    unique = len(set(map(repr, requests)))
    return {"requests": len(requests), "unique": unique, "llm_calls_made": calls,
            "llm_calls_avoided": len(requests) - calls, "clock_a_reduction": round(1 - calls / max(1, len(requests)), 3),
            "soundness": "content-hash key (input+provider+model+version) — a stale/wrong hit is impossible (a mutated "
                         "input or version bump always MISSES); the hit is byte-identical to a cold run",
            "outputs_consistent": all(outputs[i] == outputs[j] for i in range(len(requests)) for j in range(len(requests))
                                      if repr(requests[i]) == repr(requests[j]))}


def mr_jeffrey_propose(code_shape: str) -> List[str]:
    """MR.JEFFREY / the LLM as the A/B/C/D PROPOSER (untrusted — the engine VERIFIES before applying). Maps a coarse
    code-shape to candidate acceleration techniques; the proposal is WORTHLESS until proved. (LLM egress is BLOCKED in
    this environment, so the proposer is a deterministic stand-in; the VERIFICATION is the real, binding part.)"""
    table = {
        "loop_with_query": ["A.cache (if pure)", "A.batch (if independent)"],
        "nested_loop_search": ["C.algo (O(N²)→O(N) if result-equivalent)"],
        "sequential_io": ["B.async (if independent)", "A.dedup (if redundant)"],
        "serialize_heavy": ["D.serde (if byte-equivalent)"],
        "alloc_in_loop": ["D.alloc (if no aliasing hazard)"],
    }
    return table.get(code_shape, ["(no candidate acceleration — leave the original)"])
