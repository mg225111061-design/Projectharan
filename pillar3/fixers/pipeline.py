"""
Pillar 3 · Stage 1 — the VERIFY → MEASURE → GRADE pipeline (the safety net; Rules 3/4).
========================================================================================
Every proposed fix passes through here before it can be accepted. It runs differential testing against the
trusted-original oracle FIRST (Rule 4 — a divergent fix never gets measured/accepted), then the whole-program
measurement (Rule 1), then grades with Pillar 1's enforced ADT (Rule 3):
  • differential FAILS  → DECLINE (behavior diverges) — the safety net.
  • differential PASSES but no whole-program win ≥ floor → DECLINE (no "EXACT 1.0×").
  • win ≥ floor + EXACT-justified (by-construction / exhaustive closed domain) → EXACT (δ must be None).
  • win ≥ floor, differential-only → PROBABILISTIC(ε,δ) with δ = rule-of-three 3/n.
"""
from __future__ import annotations

from typing import Any, Callable, List, Optional, Tuple

import kernel_verdict as KV
from pillar3 import measure as M
from pillar3 import record as RC


def apply_and_grade(slow_fn: Callable, candidate_fn: Callable, make_args: Callable[[], tuple], *,
                    n: int, hotspot_fraction: float, oracle: List[Tuple[tuple, Any]],
                    waste_type: str, floor: float = 1.10, eq: Callable[[Any, Any], bool] = None,
                    exact_justification: Optional[str] = None, samples: int = 7) -> KV.Verdict:
    """Grade a proposed fix. Returns a kernel_verdict.Verdict; the SpeedupReport is attached as .report."""
    # Rule 4: differential FIRST — a divergent fix is never measured or accepted
    diff = RC.differential_test(candidate_fn, oracle, eq)
    if not diff.passed:
        v = KV.decline(f"behavior diverges ({diff.mismatches}/{diff.n} differ; first {diff.first_mismatch}) "
                       f"⇒ DECLINE", waste_type)
        v.report = None
        return v
    # Rule 1: whole-program measurement, neutral baseline
    rep = M.measure_whole_program(slow_fn, candidate_fn, make_args, n=n, hotspot_fraction=hotspot_fraction,
                                  samples=samples)
    if not rep.beats(floor):
        v = KV.decline(f"no whole-program win ≥ {floor:.2f}× (measured {rep.whole_program_ratio:.2f}×, "
                       f"Amdahl ceiling {rep.amdahl_ceiling:.1f}×) ⇒ DECLINE (not 'EXACT 1.0×')", waste_type)
        v.report = rep
        return v
    # Rule 3: grade. EXACT only with a real justification (proof / by-construction / exhaustive closed domain).
    if exact_justification:
        cert = KV.Cert(KV.EXACT, exact_justification, passed=True, check_cost=f"O(n)={diff.n} oracle cases",
                       detail=f"{waste_type}: differential PASS on {diff.n} cases + EXACT by {exact_justification}")
        v = KV.exact(candidate_fn, waste_type, str(rep), cert)
    else:
        cert = KV.Cert(KV.PROBABILISTIC, "differential", passed=True, check_cost=f"O(n)={diff.n} oracle cases",
                       delta=diff.rule_of_three_delta,
                       detail=f"{waste_type}: differential PASS on {diff.n} cases, no proof ⇒ δ=3/n")
        v = KV.probabilistic(candidate_fn, waste_type, str(rep), cert)
    v.report = rep
    v.amdahl_p = hotspot_fraction
    v.crossover_n = n
    return v
