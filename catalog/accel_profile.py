"""
EXTREME ACCELERATION PHASE 0 — profile GENERATED code, rank its hot-paths, set the layer ordering by MEASUREMENT.
==================================================================================================================
The acceleration layers (native / SIMD / cores / cache-layout / superopt / PGO) are CONSTANT-FACTOR — generated
general code has no foldable structure (or the fold engine would already collapse it), so there is no asymptotic
win here, only large constants. To spend effort where it pays (Amdahl), we first MEASURE what generated code
actually spends time on.

The benchmark is a set of pure-Python compute kernels in the shape an LLM typically emits (readable loops): an
elementwise transform, an associative reduction, an AXPY map, a Horner polynomial eval, and an array-of-structs
field sum. Each is profiled by median-of-k wall-clock (Clock C — emitted/generated compute; clocks §0), ranked by
wall-clock share, and tagged with the layer that applies to it. Cold paths are documented and LEFT (accelerating
them is Amdahl-foolish). The ranking sets the PHASE 1–7 ordering — by measurement, not guess.
"""
from __future__ import annotations

import math
from typing import Callable, Dict, List, Tuple


# ── the generated-code benchmark: readable pure-Python kernels (what an LLM emits) ──────────────────────
def _gen_data(n: int, seed: int = 7) -> List[float]:
    import random
    rng = random.Random(seed)
    return [rng.uniform(-3.0, 3.0) for _ in range(n)]


def k_elementwise(xs: List[float]) -> List[float]:
    """A pure elementwise map (no cross-element dependence) — the canonical SIMD/vectorize target."""
    return [math.sin(x) * math.cos(x) + math.sqrt(abs(x)) for x in xs]


def k_reduction(xs: List[float]) -> float:
    """An associative reduction (Σ x²) — vectorizable AND parallelizable (lane-independent)."""
    s = 0.0
    for x in xs:
        s += x * x
    return s


def k_axpy(xs: List[float], a: float = 2.5, b: float = 1.25) -> List[float]:
    """y = a·x + b — a trivially data-parallel map."""
    return [a * x + b for x in xs]


def k_poly_horner(xs: List[float]) -> List[float]:
    """Evaluate a fixed degree-4 polynomial at each point — a loop-free hot instruction sequence (superopt/native)."""
    out = []
    for x in xs:
        out.append(((((3.0 * x + 2.0) * x - 1.0) * x + 4.0) * x - 5.0))   # Horner form
    return out


def k_aos_field_sum(xs: List[float]) -> float:
    """Sum one field across an array-of-structs (poor locality) — the cache-layout (AoS→SoA) target."""
    structs = [{"a": x, "b": -x, "c": x * 0.5} for x in xs]               # the AoS the generated code built
    s = 0.0
    for rec in structs:
        s += rec["a"]                                                      # touches 1 of 3 fields, strided in cache
    return s


# (kernel, applicable-layers in priority order) — the layer tag is set by layout_simd's tier analysis below
_KERNELS: List[Tuple[str, Callable, str]] = [
    ("elementwise_map", k_elementwise, "map"),
    ("assoc_reduction", k_reduction, "reduction"),
    ("axpy_map", k_axpy, "map"),
    ("poly_horner", k_poly_horner, "map"),
    ("aos_field_sum", k_aos_field_sum, "io"),     # 'io'-like locality penalty; really a layout target
]


def _layers_for(name: str, kind: str) -> List[str]:
    """Which acceleration layers apply to a kernel — driven by layout_simd's dependence/tier analysis (the
    same legality analysis that later GATES each transform), not by guesswork."""
    import layout_simd as LS
    layers: List[str] = []
    tier = LS.analyze(LS.Kernel(name, kind, op="+" if kind == "reduction" else None))
    if tier.tier == "A":                                  # provably lane-independent ⇒ SIMD + cores apply
        layers += ["simd", "cores"]
    if name == "aos_field_sum":
        layers = ["cache_layout"] + layers                # strided field access ⇒ AoS→SoA is the primary win
    if name in ("poly_horner",):
        layers += ["superopt", "native"]                  # loop-free arithmetic ⇒ superopt + native lowering
    if kind in ("map", "reduction"):
        layers += ["native"]                              # interpreter removal applies to every numeric loop
    # de-dup preserving order
    seen, out = set(), []
    for l in layers:
        if l not in seen:
            seen.add(l)
            out.append(l)
    return out or ["native"]


def profile(n: int = 20000, k: int = 5) -> dict:
    """Median-of-k wall-clock profile (Clock C) of the generated-code benchmark; rank hot-paths by share; tag the
    applicable layer(s) per path. Returns the ranking + the measurement-driven PHASE 1–7 ordering."""
    import clocks
    xs = _gen_data(n)
    rows = []
    for name, fn, kind in _KERNELS:
        stat = clocks.measure_repeat(f"gen:{name}", "C", lambda fn=fn: fn(xs), k=k, warmup=1)
        rows.append({"kernel": name, "kind": kind, "median_ms": stat.median_ms,
                     "layers": _layers_for(name, kind)})
    total = sum(r["median_ms"] for r in rows) or 1e-12
    for r in rows:
        r["wall_share"] = round(r["median_ms"] / total, 4)
    rows.sort(key=lambda r: r["median_ms"], reverse=True)
    # the hot-paths are those above an Amdahl-meaningful share; the rest are cold (documented, left alone)
    hot = [r for r in rows if r["wall_share"] >= 0.05]
    cold = [r["kernel"] for r in rows if r["wall_share"] < 0.05]
    # measurement-driven layer ordering: by the total wall-share each layer can address (most impactful first)
    layer_share: Dict[str, float] = {}
    for r in hot:
        for l in r["layers"]:
            layer_share[l] = layer_share.get(l, 0.0) + r["wall_share"]
    layer_order = [l for l, _ in sorted(layer_share.items(), key=lambda kv: kv[1], reverse=True)]
    return {
        "clock": "C (emitted/generated compute)", "n": n, "k": k,
        "ranked_hot_paths": [{"kernel": r["kernel"], "wall_share": r["wall_share"], "median_ms": r["median_ms"],
                              "layers": r["layers"]} for r in hot],
        "cold_paths_left_alone": cold,
        "layer_order_by_measured_share": layer_order,
        "layer_addressable_share": {l: round(s, 4) for l, s in sorted(layer_share.items(), key=lambda kv: -kv[1])},
        "asymptotics": "UNCHANGED — every layer is a constant factor; ordering by measured wall-share (Amdahl)",
        "honest_note": "cold paths (<5% share) are LEFT untouched; accelerating them is Amdahl-foolish",
    }
