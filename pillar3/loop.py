"""
Pillar 3 · Stage 2 — the iterative compounding loop + diminishing-returns controller (normal mode).
====================================================================================================
profile → apply the best VERIFIED fix → REPROFILE (the next hotspot is now dominant) → repeat. The cumulative
whole-program speedup is MEASURED FRESH each round (Rule 1) — never the product of component multipliers
(the Whatnot honesty check: 3×·20×·6.7× ≠ 5.8×). A DECLINE at any step is skipped, not chained (Rule 4).
Stops at diminishing returns (next marginal whole-program gain < floor).

Program model (concrete, testable): a pipeline of stages, each with a slow and a fast implementation. The
program runs the stages in sequence; a fix = activating a stage's fast impl. The all-slow pipeline is the
neutral baseline and the trusted oracle.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import kernel_verdict as KV
from pillar3 import measure as M
from pillar3 import record as RC


@dataclass
class Stage:
    name: str
    slow: Callable[[Any], Any]
    fast: Callable[[Any], Any]
    fraction: float = 0.0           # profiled share of baseline runtime (Amdahl input for this stage)


@dataclass
class Round:
    applied: str
    cumulative_ratio: float         # FRESH whole-program measurement (all active fixes) vs baseline
    marginal_gain: float            # cumulative_this / cumulative_prev − 1
    hotspot_fraction: float
    amdahl_ceiling: float
    grade: str


@dataclass
class CompoundingReport:
    rounds: List[Round] = field(default_factory=list)
    final_cumulative_ratio: float = 1.0
    stop_reason: str = ""
    declined: List[str] = field(default_factory=list)
    product_of_locals: float = 1.0  # for the honesty check: this is NOT the whole-program number

    def best_single_round_ratio(self) -> float:
        return max((r.cumulative_ratio for r in self.rounds[:1]), default=1.0)


def _pipeline(stages: List[Stage], active: Set[str]) -> Callable[[Any], Any]:
    def run(data):
        out = data
        for s in stages:
            out = (s.fast if s.name in active else s.slow)(out)
        return out
    return run


def compound_optimize(stages: List[Stage], make_input: Callable[[], Any], *, n: int,
                      min_marginal_gain: float = 0.03, samples: int = 5,
                      eq: Callable[[Any, Any], bool] = None) -> CompoundingReport:
    """Walk down the flame graph: each round measure (fresh) the whole-program ratio of every candidate fix vs
    the all-slow baseline, verify it against the baseline oracle, apply the best, repeat until the marginal
    whole-program gain drops below `min_marginal_gain`. Cumulative is always a fresh end-to-end measurement."""
    baseline = _pipeline(stages, set())
    oracle = RC.record_oracle(baseline, [(make_input(),) for _ in range(4)])
    active: Set[str] = set()
    rep = CompoundingReport()
    prev_cumulative = 1.0
    make_args = lambda: (make_input(),)
    while len(active) < len(stages):
        best: Optional[Tuple[Stage, M.SpeedupReport]] = None
        for s in stages:
            if s.name in active:
                continue
            cand = _pipeline(stages, active | {s.name})
            diff = RC.differential_test(cand, oracle, eq)
            if not diff.passed:                                  # Rule 4: skip, do not chain a divergent fix
                if s.name not in rep.declined:
                    rep.declined.append(s.name)
                continue
            sr = M.measure_whole_program(baseline, cand, make_args, n=n,
                                         hotspot_fraction=min(0.999, sum(st.fraction for st in stages
                                                                         if st.name in (active | {s.name}))),
                                         samples=samples)
            if best is None or sr.whole_program_ratio > best[1].whole_program_ratio:
                best = (s, sr)
        if best is None:
            rep.stop_reason = "no remaining verified candidate improves the program"
            break
        stage, sr = best
        marginal = sr.whole_program_ratio / prev_cumulative - 1.0
        if marginal < min_marginal_gain and rep.rounds:
            rep.stop_reason = (f"diminishing returns: next marginal whole-program gain {marginal:.1%} "
                               f"< {min_marginal_gain:.0%}")
            break
        active.add(stage.name)
        rep.rounds.append(Round(stage.name, sr.whole_program_ratio, marginal, sr.hotspot_fraction,
                                sr.amdahl_ceiling, KV.PROBABILISTIC))
        prev_cumulative = sr.whole_program_ratio
    rep.final_cumulative_ratio = prev_cumulative
    if not rep.stop_reason:
        rep.stop_reason = "all stages applied"
    # honesty bookkeeping (the Whatnot fallacy): the PRODUCT of each fix's LOCAL multiplier — measured on the
    # stage ALONE (its own slow/fast ratio), NOT in the pipeline. This is the naive "multiply the component
    # speedups" number that does NOT equal the whole-program result. We surface it precisely to refute it.
    prod = 1.0
    sample_in = make_input()
    for s in stages:
        if s.name in active:
            local = M.time_median(s.slow, lambda: (sample_in,), samples=3) / \
                max(M.time_median(s.fast, lambda: (sample_in,), samples=3), 1e-12)
            prod *= local
    rep.product_of_locals = prod
    return rep


def fresh_end_to_end_ratio(stages: List[Stage], make_input: Callable[[], Any], n: int, samples: int = 5) -> float:
    """An INDEPENDENT fresh measurement of all-fast vs all-slow — used to prove the loop's cumulative number is
    a real end-to-end measurement, not a component product (the Whatnot check)."""
    baseline = _pipeline(stages, set())
    allfast = _pipeline(stages, {s.name for s in stages})
    return M.measure_whole_program(baseline, allfast, lambda: (make_input(),), n=n,
                                   hotspot_fraction=0.99, samples=samples).whole_program_ratio
