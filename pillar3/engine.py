"""
Pillar 3 · PHASE M — the mode-aware optimisation engine (the loop controller that routes through ModePolicy).
=============================================================================================================
This is the single controller every stage routes through. It does NOT hard-code behaviour: for the active
`ModePolicy` it (1) fires only detectors in `enabled_detectors`, (2) reaches Z3 only via `verifier`
at/below `verifier_tier`, (3) ships only grades in `acceptable_grades` (the grade floor), (4) attacks
`max_hotspots`, iterates `max_iterations`, and stops per the mode's stop condition. Every speedup is a fresh,
warmup-aware, whole-program measurement (Rule 1) carrying its hotspot fraction and Amdahl ceiling (Rule 2);
the cumulative number is re-measured fresh each round, never a product of locals (Rule 4 / Whatnot).

A program is modelled as a pipeline of stages over a shared `data` dict; each candidate fix activates a
stage's fast implementation. The all-slow pipeline is the neutral baseline and the trusted oracle.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import kernel_verdict as KV
from pillar3 import complexity as CX
from pillar3 import measure as M
from pillar3 import record as RC
from pillar3 import verifier as V
from pillar3.mode import Mode, ModePolicy


@dataclass
class Candidate:
    """One proposed fix = activating a pipeline stage's fast implementation. `detector` is gated by the mode's
    enabled_detectors. `prove_fn` (optional) is the Z3 proof, reached ONLY through the verifier tier.
    `exact_justification` marks a by-construction EXACT (an identity needing no Z3)."""
    name: str
    waste_type: str
    detector: str
    slow: Callable[[Dict], Dict]
    fast: Callable[[Dict], Dict]
    fraction: float                                  # profiled share of baseline runtime (Amdahl input)
    prove_fn: Optional[Callable[[], "Tuple[bool, Optional[str]]"]] = None
    exact_justification: Optional[str] = None
    eq: Optional[Callable[[Any, Any], bool]] = None
    region_size: int = 1                             # for CHEAP_CERT small-region gating
    floor: float = 1.02


@dataclass
class Shipped:
    name: str
    waste_type: str
    detector: str
    grade: str
    ratio: float                                     # cumulative fresh whole-program ratio after this fix
    ceiling: float
    hotspot_fraction: float


@dataclass
class Declined:
    name: str
    waste_type: str
    detector: str
    reason: str


@dataclass
class EngineReport:
    mode: str
    shipped: List[Shipped] = field(default_factory=list)
    declined: List[Declined] = field(default_factory=list)
    attempted_detectors: Set[str] = field(default_factory=set)
    rounds: int = 0
    cumulative_ratio: float = 1.0                    # last round's fresh whole-program ratio
    fresh_cumulative_ratio: float = 1.0             # independent fresh all-active re-measure (Whatnot check)
    final_ceiling: float = float("inf")
    z3_calls: int = 0
    latency_s: float = 0.0
    ran_complexity_sweep: bool = False
    sweep_sizes: List[int] = field(default_factory=list)
    sweep_klass: str = ""
    hotspots_attacked: int = 0
    stop_reason: str = ""

    def shipped_names(self) -> Set[str]:
        return {s.name for s in self.shipped}

    def shipped_grades(self) -> Set[str]:
        return {s.grade for s in self.shipped}


def _pipeline(cands: List[Candidate], active: Set[str], residual: Optional[Callable[[Dict], Dict]]):
    def run(data: Dict) -> Dict:
        out = dict(data)
        if residual is not None:
            out = residual(out)
        for c in cands:
            out = (c.fast if c.name in active else c.slow)(out)
        return out
    return run


def _floor_pipeline(cands: List[Candidate], active: Set[str], residual: Optional[Callable[[Dict], Dict]]):
    """The Amdahl time-floor for `active`: residual + inactive-slow, with active stages PASSED THROUGH (the
    unreachable limit of an infinitely-fast fix). Times only — output is not comparable. Because the real
    candidate runs active-fast (≥ passthrough), the measured ratio is ≤ T_base/T_floor = ceiling by const."""
    def run(data: Dict) -> Dict:
        out = dict(data)
        if residual is not None:
            out = residual(out)
        for c in cands:
            out = out if c.name in active else c.slow(out)
        return out
    return run


def _measure_coherent(baseline_pipe, cand_pipe, floor_pipe, make_args, *, n: int, samples: int,
                      t_base: float) -> M.SpeedupReport:
    """A whole-program ratio AND its Amdahl ceiling from one measurement session: f = 1 − T_floor/T_base (the
    real hotspot fraction of the active set), ceiling = 1/(1−f) = T_base/T_floor, ratio = T_base/T_cand. The
    floor is clamped ≤ the candidate (it cannot beat the infinitely-fast limit), so ratio ≤ ceiling holds."""
    t_floor = M.time_median(floor_pipe, make_args, samples)
    t_cand = M.time_median(cand_pipe, make_args, samples)
    t_floor = min(t_floor, t_cand)                          # residual+inactive ≤ fully-fixed pipeline (clamp)
    f = max(0.0, min(0.999, 1.0 - t_floor / max(t_base, 1e-12)))
    ratio = t_base / max(t_cand, 1e-12)
    return M.SpeedupReport(whole_program_ratio=ratio, hotspot_fraction=f, n=n, samples=samples,
                           warmup_discarded=1, orig_median_s=t_base, cand_median_s=t_cand)


def _decide_grade(policy: ModePolicy, c: Candidate) -> "Tuple[str, str]":
    """Grade a (already differential-passing) candidate under the mode's verifier tier. by-construction EXACT
    needs no Z3; otherwise the verifier tier decides whether a Z3 certificate is even attempted (Rule 5)."""
    if c.exact_justification:
        return KV.EXACT, f"by-construction ({c.exact_justification})"
    attempted, proven, info = V.attempt_certificate(policy.verifier_tier, c.prove_fn, region_size=c.region_size)
    if attempted:
        if proven:
            return KV.EXACT, "Z3 bounded translation validation"
        if info and "counterexample" in str(info):
            return KV.DECLINE, f"Z3 REFUTED equivalence ({info})"     # the moat: a wrong swap caught
        return KV.PROBABILISTIC, f"Z3 inconclusive ({info}) — differential only"
    return KV.PROBABILISTIC, f"differential only ({info})"


def optimize(candidates: List[Candidate], make_input: Callable[[], Dict], *, mode: Mode, n: int,
             residual: Optional[Callable[[Dict], Dict]] = None,
             sweep_fn: Optional[Callable[[int], None]] = None,
             sweep_sizes: Tuple[int, ...] = (200, 800, 3200)) -> EngineReport:
    """Drive profile→fix→verify→measure→reprofile under the active mode's contract. Returns an EngineReport."""
    policy = ModePolicy.for_mode(mode)
    V.reset_z3_checks()
    t0 = time.perf_counter()
    rep = EngineReport(mode=mode.value)

    baseline = _pipeline(candidates, set(), residual)
    oracle = RC.record_oracle(baseline, [(make_input(),) for _ in range(3)])
    make_args = lambda: (make_input(),)
    t_base = M.time_median(baseline, make_args, ModePolicy.for_mode(mode).samples)  # neutral baseline (once)

    # complexity sweep — policy-gated (extend always; fast never)
    if policy.runs_complexity_sweep and sweep_fn is not None:
        fit = CX.measure_complexity(sweep_fn, list(sweep_sizes))
        rep.ran_complexity_sweep = True
        rep.sweep_sizes = list(sweep_sizes)
        rep.sweep_klass = fit.klass

    # the profiler is ground truth for WHERE: order candidates by hotspot fraction (largest first)
    ordered = sorted(candidates, key=lambda c: -c.fraction)
    pool = ordered if policy.max_hotspots is None else ordered[:policy.max_hotspots]

    active: Set[str] = set()
    prev_cumulative = 1.0
    declined_detectors: Set[str] = set()
    for c in pool:
        if not policy.detector_enabled(c.detector):       # detector-gating (Rule: not enabled ⇒ does not fire)
            continue
        rep.attempted_detectors.add(c.detector)
        rep.hotspots_attacked += 1

        # Rule 4: differential FIRST — a divergent fix is never measured or accepted
        cand_pipe = _pipeline(candidates, active | {c.name}, residual)
        diff = RC.differential_test(cand_pipe, oracle, c.eq)
        if not diff.passed:
            rep.declined.append(Declined(c.name, c.waste_type, c.detector,
                                         f"differential FAILED ({diff.mismatches}/{diff.n}) ⇒ DECLINE"))
            continue

        grade, note = _decide_grade(policy, c)
        if grade == KV.DECLINE:                            # Z3 refuted (or other hard reject)
            rep.declined.append(Declined(c.name, c.waste_type, c.detector, note))
            continue
        if not policy.grade_acceptable(grade):             # grade-floor gating (mode-dependent, not the fixer)
            rep.declined.append(Declined(c.name, c.waste_type, c.detector,
                                         f"grade {grade} below {mode.value} floor "
                                         f"{sorted(policy.acceptable_grades)} ⇒ DECLINE ({note})"))
            continue

        # Rule 1/2: fresh whole-program measurement carrying a CONSISTENT hotspot fraction + Amdahl ceiling
        # (ratio ≤ ceiling by construction, from one measurement session via the floor pipeline)
        floor_pipe = _floor_pipeline(candidates, active | {c.name}, residual)
        sr = _measure_coherent(baseline, cand_pipe, floor_pipe, make_args, n=n, samples=policy.samples,
                               t_base=t_base)
        if not sr.beats(c.floor):
            rep.declined.append(Declined(c.name, c.waste_type, c.detector,
                                         f"no whole-program win ≥ {c.floor:.2f}× (got {sr.whole_program_ratio:.2f}×)"))
            continue

        marginal = sr.whole_program_ratio / prev_cumulative - 1.0
        if (not policy.stop_on_first_win) and rep.shipped and marginal < policy.marginal_floor:
            rep.stop_reason = (f"diminishing returns: next marginal whole-program gain {marginal:.1%} "
                               f"< {policy.marginal_floor:.0%}")
            break

        active.add(c.name)
        rep.shipped.append(Shipped(c.name, c.waste_type, c.detector, grade, sr.whole_program_ratio,
                                   sr.amdahl_ceiling, sr.hotspot_fraction))
        rep.rounds += 1
        prev_cumulative = sr.whole_program_ratio
        rep.final_ceiling = sr.amdahl_ceiling

        if policy.stop_on_first_win:
            rep.stop_reason = "first accepted win (fast)"
            break
        if rep.rounds >= policy.max_iterations:
            rep.stop_reason = f"max iterations ({policy.max_iterations}) reached"
            break

    if not rep.stop_reason:
        rep.stop_reason = "every enabled detector tried"

    # independent fresh all-active re-measure (the Whatnot honesty check)
    if active:
        fresh = _measure_coherent(baseline, _pipeline(candidates, active, residual),
                                  _floor_pipeline(candidates, active, residual), make_args, n=n,
                                  samples=policy.samples, t_base=t_base)
        rep.fresh_cumulative_ratio = fresh.whole_program_ratio
        rep.cumulative_ratio = prev_cumulative
        rep.final_ceiling = fresh.amdahl_ceiling
    rep.z3_calls = V.z3_check_count()
    rep.latency_s = time.perf_counter() - t0
    return rep
