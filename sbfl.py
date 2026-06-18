"""
v27 STAGE 15 (layer 1) — spectrum-based fault localization (SBFL): the cheap statistical ranker.
=================================================================================================
Given test executions — each a (set of covered program elements, pass/fail) — SBFL scores every element
by how strongly its execution CORRELATES with failure, using the classic spectrum counts:

    ef = # FAILing tests that executed e        ep = # PASSing tests that executed e
    nf = # FAILing tests that did NOT execute e  np = # PASSing tests that did NOT execute e

and the standard suspiciousness metrics (Ochiai, DStar/D*², Op2, Tarantula). This is layer 1 of the
funnel: a fast ranking that NARROWS the expensive sound verifier (layer 3) to a few candidates.

★ HONEST (§1.5, §5) ★: this is a RANKING heuristic, NOT a proof — its output is labeled RANKED, never
"confirmed". Op2 is provably optimal for a SINGLE fault; with MULTIPLE faults SBFL degrades (the signals
dilute) — surfaced by `single_fault_optimal`. Confirmation (witness / class-absence) is layer 3's job.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Sequence, Set, Tuple


@dataclass
class Test:
    covered: Set[str]      # program elements (statement / function ids) this test executed
    passed: bool


@dataclass
class Spectrum:
    ef: int
    ep: int
    nf: int
    np: int


def _spectra(tests: Sequence[Test]) -> Dict[str, Spectrum]:
    elems: Set[str] = set()
    for t in tests:
        elems |= t.covered
    total_f = sum(1 for t in tests if not t.passed)
    total_p = sum(1 for t in tests if t.passed)
    out: Dict[str, Spectrum] = {}
    for e in elems:
        ef = sum(1 for t in tests if e in t.covered and not t.passed)
        ep = sum(1 for t in tests if e in t.covered and t.passed)
        out[e] = Spectrum(ef=ef, ep=ep, nf=total_f - ef, np=total_p - ep)
    return out


def _score(s: Spectrum, metric: str) -> float:
    ef, ep, nf, np = s.ef, s.ep, s.nf, s.np
    if metric == "ochiai":
        denom = math.sqrt((ef + nf) * (ef + ep))
        return ef / denom if denom > 0 else 0.0
    if metric == "dstar":                       # D* with * = 2
        denom = ep + nf
        return (ef * ef) / denom if denom > 0 else float(ef * ef) * 1e6   # denom 0 & ef>0 ⇒ very suspicious
    if metric == "op2":                         # Op2: provably optimal for a single fault
        return ef - ep / (ep + np + 1)
    if metric == "tarantula":
        F, P = ef + nf, ep + np
        a = ef / F if F else 0.0
        b = ep / P if P else 0.0
        return a / (a + b) if (a + b) > 0 else 0.0
    raise ValueError(metric)


@dataclass
class Ranking:
    metric: str
    scores: Dict[str, float]
    ranked: List[Tuple[str, float]]
    single_fault_optimal: bool             # Op2 only; and only meaningful for a single fault
    note: str = ""

    def top(self, k: int = 1) -> List[str]:
        return [e for e, _ in self.ranked[:k]]


def suspiciousness(tests: Sequence[Test], metric: str = "ochiai") -> Ranking:
    """Rank program elements by failure-correlation. `metric` ∈ ochiai|dstar|op2|tarantula."""
    spec = _spectra(tests)
    scores = {e: _score(s, metric) for e, s in spec.items()}
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    note = "RANKED (statistical heuristic — NOT a proof; confirm with layer 3)"
    return Ranking(metric, scores, ranked, single_fault_optimal=(metric == "op2"), note=note)


def liblit_increase(observations: Sequence[Tuple[bool, bool]]) -> float:
    """Liblit 'Increase' for one predicate: P(fail | pred TRUE) − P(fail | pred OBSERVED). >0 ⇒ the
    predicate being true raises failure probability (a bug predictor). `observations` = [(pred_true, fail)]."""
    true_obs = [fail for pt, fail in observations if pt]
    all_fail = [fail for _pt, fail in observations]
    if not true_obs or not all_fail:
        return 0.0
    f_true = sum(1 for f in true_obs if f) / len(true_obs)
    f_obs = sum(1 for f in all_fail if f) / len(all_fail)
    return f_true - f_obs


def multi_fault_degradation(tests: Sequence[Test], faults: Sequence[str]) -> Dict[str, object]:
    """Honest report: with >1 fault the single-fault optimality no longer holds — measure how far down the
    ranking the (multiple) true faults sit under Op2."""
    r = suspiciousness(tests, "op2")
    order = [e for e, _ in r.ranked]
    positions = {f: (order.index(f) + 1 if f in order else None) for f in faults}
    return {"faults": list(faults), "positions": positions,
            "single_fault_optimal_applies": len(faults) == 1,
            "note": "Op2 is single-fault optimal; with multiple faults the ranking degrades (signals dilute)"}
