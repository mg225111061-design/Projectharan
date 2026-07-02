"""
§V PHASE 1 — PROFILE THE ENGINE: find every repeated computation, rank by (cost × repetition).
================================================================================================================
Before folding, measure. Run the engine on a representative workload and measure BOTH where time goes AND what
repeats — the prime fold/cache targets are the operations that are expensive AND repeated. A cheap one-off isn't worth
caching; an expensive repeated op is the highest-value lookup target.

★ Separate the LLM (Clock A) from the engine (Clock B/C). The LLM's per-call latency is irreducible (external
provider) — its only honest lever is the call COUNT. The engine's own work (parse/verify/fold/proof) is foldable. The
profile states the honest expectation: if the LLM dominates the wall-clock, the response cache (count reduction) is
the big lever and engine-folding accelerates the rest.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List

from enginespeed.folded_ops import FoldedEngine, verify_equiv


@dataclass
class OpProfile:
    op: str
    clock: str                          # "A" (LLM) | "B" (verify) | "C" (engine compute)
    cost_ms: float                      # measured cold cost of ONE call (median-of-k); BLOCKED-modeled for Clock A
    repetitions: int                    # times this op appears in the representative workload
    measured: bool                      # False ⇒ cost is modeled (Clock A, no live egress)

    @property
    def value(self) -> float:           # the ranking key: cost × repetition (expensive AND repeated ⇒ top target)
        return round(self.cost_ms * self.repetitions, 4)


def _representative_workload():
    """A modeled engine workload with deliberate REPETITION (the same inputs recur, as they do across passes)."""
    parses = ["def f(n):\n    return n*n"] * 30 + ["def g(x):\n    return x+1"] * 20      # 50 parses, 2 distinct
    verifies = [("n*(n+1)", "n*n+n")] * 25 + [("(n+1)*(n+1)", "n*n+2*n+1")] * 15         # 40 verifies, 2 distinct
    llm_prompts = ["optimize: sum loop"] * 12 + ["secure: password check"] * 8           # 20 prompts, 2 distinct
    return {"parse": parses, "verify": verifies, "llm": llm_prompts}


def profile_engine(k: int = 5) -> dict:
    """Measure each op-type's cold cost (median-of-k) and its repetition count in the representative workload, then
    rank by (cost × repetition). LLM cost is Clock-A and BLOCKED ⇒ modeled, never a fabricated latency."""
    import clocks
    wl = _representative_workload()
    eng = FoldedEngine()

    # measured cold costs (Clock B/C) on a single representative input each
    parse_src = wl["parse"][0]
    va, vb = wl["verify"][0]
    cost_parse = clocks.measure_repeat("parse", "C", lambda: __import__("ast").parse(parse_src), k=k).median_ms
    cost_verify = clocks.measure_repeat("verify", "B", lambda: verify_equiv(va, vb), k=k).median_ms
    # Clock A (LLM): latency is the provider's and unavailable here ⇒ modeled, flagged not-measured
    cost_llm_modeled = 800.0            # a representative LLM round-trip (ms), MODELED — never measured here

    profiles = [
        OpProfile("parse", "C", round(cost_parse, 4), len(wl["parse"]), True),
        OpProfile("verify", "B", round(cost_verify, 4), len(wl["verify"]), True),
        OpProfile("llm", "A", cost_llm_modeled, len(wl["llm"]), False),
    ]
    ranked = sorted(profiles, key=lambda p: p.value, reverse=True)

    # honest wall-clock split: LLM (modeled) vs engine (measured)
    llm_wall = cost_llm_modeled * len(wl["llm"])
    engine_wall = cost_parse * len(wl["parse"]) + cost_verify * len(wl["verify"])
    total = llm_wall + engine_wall
    # repetition: distinct vs total (the cache opportunity)
    distinct = {"parse": len(set(wl["parse"])), "verify": len(set(map(tuple, wl["verify"]))), "llm": len(set(wl["llm"]))}
    return {
        "ranked_targets": [{"op": p.op, "clock": p.clock, "cost_ms": p.cost_ms, "reps": p.repetitions,
                            "value_cost_x_reps": p.value, "measured": p.measured} for p in ranked],
        "repetition": {op: {"total": len(wl[op]), "distinct": distinct[op],
                            "reuse_fraction": round(1 - distinct[op] / len(wl[op]), 4)} for op in wl},
        "wall_clock_split": {
            "llm_fraction_modeled": round(llm_wall / total, 4), "engine_fraction_measured": round(engine_wall / total, 4),
            "note": "LLM fraction uses a MODELED per-call latency (Clock A, egress BLOCKED) — the honest expectation: "
                    "when the LLM dominates, the response cache (call-COUNT reduction) is the big lever; engine-folding "
                    "accelerates the measured rest (Clock B/C)"},
        "thesis": "rank by cost×repetition; the top targets are expensive AND repeated — exactly what folding the "
                  "engine inward turns into O(1) lookups",
    }
