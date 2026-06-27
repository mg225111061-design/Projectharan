"""
§U PHASE 3 — MECHANISM 2: EXECUTION-FEEDBACK FIX LOOP (repair the failures).
================================================================================================================
A failed candidate is not a dead end — feed its PRECISE failure back to Opus and repair. The failure can be a build
error, a failing visible test, a broken regression, or — richest of all — a CONCRETE FORMAL COUNTEREXAMPLE naming the
exact input on which the patch is wrong (the hidden-test input). Unlike a generic test failure, that counterexample
hands the model the precise edge case to fix; it is feedback no plain test-runner can give.

Iterate generate → verify → repair until a candidate passes the full gate or the per-task budget (repair rounds) is
hit. Budget-stop returns the best VERIFIED candidate so far, or an honest DECLINE if none verified — never an
unverified patch gambled on the hidden suite.

★ SUBSTRATE: live repair (Opus regenerating from the feedback) is pending-real-stack (egress BLOCKED). Here the
repair is the task's recorded `repair_src` — the patch the model produces WHEN HANDED THE COUNTEREXAMPLE — and it is
re-run through the full gate, so a repair that is still wrong is REJECTED (the honest-unsolved task), never waved
through. The counterexample being the unlock models exactly "the formal counterexample is the key feedback."
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from swebench.harness import Task, Candidate, layered_gate, grade_against_hidden, recorded_generator
from swebench.multi_candidate import verification_filter
from swebench.formal_check import formal_correct
from swebench.harness import compile_fn, run_cases


def structured_feedback(task: Task, cand: Candidate) -> dict:
    """Capture the precise failure of a candidate as structured feedback for repair. Prefers the FORMAL COUNTEREXAMPLE
    (the richest), else the failing visible/regression test, else the build error."""
    fn = compile_fn(cand.src, task.fn_name)
    if fn is None:
        return {"kind": "build", "detail": "patch does not compile"}
    vok, vf = run_cases(fn, task.visible)
    if not vok:
        return {"kind": "visible", **vf}
    if task.regression:
        rok, rf = run_cases(fn, task.regression)
        if not rok:
            return {"kind": "regression", **rf}
    fr = formal_correct(task, fn)
    if fr.applicable and not fr.proved:
        return {"kind": "formal_counterexample", **(fr.counterexample or {}),
                "detail": "the exact input on which the patch is wrong (the hidden-test failure)"}
    return {"kind": "none"}


def extract_counterexample(task: Task) -> Optional[dict]:
    """Find a formal counterexample from the candidate pool — the best visible-passing-but-formally-wrong candidate
    yields the exact failing input to hand the repair step."""
    for c in task.candidates:
        fn = compile_fn(c.src, task.fn_name)
        if fn is None:
            continue
        vok, _ = run_cases(fn, task.visible)
        if not vok:
            continue
        fr = formal_correct(task, fn)
        if fr.applicable and not fr.proved and fr.counterexample:
            return fr.counterexample
    return None


def repair(task: Task, counterexample: Optional[dict]) -> Optional[Candidate]:
    """Repair from the counterexample (models Opus regenerating given the exact failing input). The repair is the
    task's recorded `repair_src`, UNLOCKED only by a real counterexample; it is re-gated by the caller, so a
    still-wrong repair is rejected. Returns the repaired candidate, or None if no repair is available."""
    if counterexample is None or not task.repair_src:
        return None
    return Candidate(task.repair_src, task.fn_name, "repaired-from-counterexample")


@dataclass
class FixLoopResult:
    submitted: Optional[Candidate]
    solved_by: Optional[str]            # "candidate" (a generated one passed) | "fix_loop" (repair passed) | None (decline)
    rounds: int                         # repair rounds used
    used_counterexample: bool
    detail: str = ""


def solve_with_fixloop(task: Task, *, budget: int = 2, use_regression=True, use_formal=True,
                       gen=recorded_generator) -> FixLoopResult:
    """The full single-task loop: generate → gate-filter → if a survivor, submit it (solved_by=candidate); else pull
    the formal counterexample, repair, re-gate, iterate to pass-or-budget; else honest DECLINE (submit nothing)."""
    cands = gen(task, 0)
    verified = verification_filter(task, cands, use_regression=use_regression, use_formal=use_formal)
    if verified:
        return FixLoopResult(verified[0][0], "candidate", 0, False,
                             "a generated candidate passed the full gate (no repair needed)")
    # no candidate passed — repair from the formal counterexample (the richest feedback)
    cex = extract_counterexample(task)
    rounds = 0
    while rounds < budget:
        rounds += 1
        rep = repair(task, cex)
        if rep is None:
            break
        g = layered_gate(task, rep, use_regression=use_regression, use_formal=use_formal)
        if g.submission_eligible:
            return FixLoopResult(rep, "fix_loop", rounds, cex is not None,
                                 "no candidate passed; repaired from the formal counterexample and the fix passed the "
                                 "full gate (a task solved ONLY by the fix loop)")
        # repair still wrong → its own counterexample would feed the next round; here the recorded repair is fixed,
        # so a still-wrong repair converges to DECLINE rather than looping forever
        cex = g.counterexample or cex
    return FixLoopResult(None, None, rounds, cex is not None,
                         "no candidate and no in-budget repair passed the full gate ⇒ honest DECLINE (never submit an "
                         "unverified patch gambled on the hidden suite — precision preserved)")
