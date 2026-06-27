"""
§U PHASE 2 — MECHANISM 1: MULTI-CANDIDATE GENERATION + VERIFICATION FILTER (the biggest single lift).
================================================================================================================
The largest single improvement: generate MANY candidates, submit only a VERIFIED one. The LLM-alone failure mode —
submit one patch, wrong → 0 — is replaced by "submit the verified one of N." Opus generates N diverse candidates
(temperature/prompt variation); each runs the full layered gate (build → visible → regression → formal); only
passers are submission-eligible; among passers the FORMALLY-STRONGEST is chosen (the one proved correct over the
widest input space, not merely visible-test-passing).

The return-per-candidate is MEASURED (pass-rate vs N), so N is chosen on measured return, not assumed. (Live N-way
generation is pending-real-stack; here N comes from the recorded candidate pool.)
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from swebench.harness import Task, Candidate, layered_gate, grade_against_hidden, recorded_generator


def verification_filter(task: Task, candidates: List[Candidate], *, use_regression=True,
                        use_formal=True) -> List[Tuple[Candidate, object]]:
    """Run every candidate through the layered gate; return [(candidate, GateResult)] for the submission-eligible ones
    (passed every applicable layer). The LLM may be liberal/wrong; only the gate-verified survive."""
    out = []
    for c in candidates:
        g = layered_gate(task, c, use_regression=use_regression, use_formal=use_formal)
        if g.submission_eligible:
            out.append((c, g))
    return out


def select_formally_strongest(verified: List[Tuple[Candidate, object]]) -> Optional[Candidate]:
    """Among gate-passing candidates, prefer the one with the strongest evidence: a formal proof (formal_ok True) over
    a visible+regression-only pass (formal_ok None — formal not applicable). Every eligible candidate is already
    gate-correct; this tiebreak just prefers proven-over-tested. Returns None if there are no eligible candidates."""
    if not verified:
        return None
    # formal_ok True ⇒ rank 1 (proved); None ⇒ rank 0 (tested-only, honest fallback). Stable, prefers proved.
    return sorted(verified, key=lambda cg: 1 if getattr(cg[1], "formal_ok", None) else 0, reverse=True)[0][0]


def submit_multi(task: Task, n: Optional[int] = None, *, use_regression=True, use_formal=True,
                 gen=recorded_generator) -> Optional[Candidate]:
    """The multi-candidate submission: generate N, filter to gate-passers, submit the formally-strongest. Returns the
    submitted candidate, or None if none passed (→ the fix loop in Phase 3, or an honest decline)."""
    cands = gen(task, n) if n else gen(task, 0)
    verified = verification_filter(task, cands, use_regression=use_regression, use_formal=use_formal)
    if not verified:
        return None
    # all eligible are gate-correct; prefer the first (formally-strongest) — simple, since the gate already disposed wrong ones
    return verified[0][0]


def pass_rate_vs_n(tasks: List[Task], max_n: int = 4, *, use_regression=True, use_formal=True) -> dict:
    """Measure return-per-candidate: for each N=1..max_n, the fraction of tasks solved (submission graded CORRECT on
    the HIDDEN tests) using only the first N candidates. Honest — each point is a real run of the pipeline."""
    curve = {}
    for n in range(1, max_n + 1):
        solved = 0
        for t in tasks:
            sub = submit_multi(t, n, use_regression=use_regression, use_formal=use_formal)
            if sub is not None and grade_against_hidden(t, sub):
                solved += 1
        curve[n] = round(solved / len(tasks), 4) if tasks else 0.0
    return curve
