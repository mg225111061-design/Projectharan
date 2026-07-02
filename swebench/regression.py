"""
§U PHASE 4 — MECHANISM 3: REGRESSION VERIFICATION (catch what the patch breaks).
================================================================================================================
A patch that fixes the target issue but breaks an existing passing test is a failure. Opus focuses on the issue and
routinely misses collateral breakage; regression verification catches exactly that. A candidate must pass the target
(visible) tests AND not break the repo's existing passing tests. A regressing candidate is rejected and fed to the
fix loop.

★ SOUND SCOPING: where running the whole suite is expensive, scope to the tests reachable from the patched code
(dependency-aware), proved to cover the patch's blast radius — never skip regression on a guess that "it's probably
fine." Here the task carries its existing-passing subset and we run it in full (the bench is small); the scoping rule
is stated as the deployment policy and the substrate runs the full declared set (no silent skip).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class RegressionResult:
    ran: int                            # number of existing-passing tests checked
    ok: bool                            # True ⇒ none regressed
    broken: Optional[dict] = None       # the first existing test the patch broke (input + expected + got)
    detail: str = ""


def check_regression(task, patched_fn: Callable) -> RegressionResult:
    """Confirm the patched function still passes the repo's existing passing tests (no collateral breakage)."""
    from swebench.harness import run_cases
    if not task.regression:
        return RegressionResult(0, True, None, "no existing-passing tests declared for this task (nothing to regress)")
    ok, fail = run_cases(patched_fn, task.regression)
    if ok:
        return RegressionResult(len(task.regression), True, None,
                                f"all {len(task.regression)} existing passing tests still pass (no regression)")
    return RegressionResult(len(task.regression), False,
                            {"args": fail.get("args"), "expected": fail.get("expected"), "got": fail.get("got")},
                            "candidate fixes the target but BREAKS an existing passing test ⇒ rejected (a real "
                            "would-be false pass the LLM would have submitted)")


def would_be_regression(task, cand) -> bool:
    """True iff this candidate passes the target (visible) tests but REGRESSES an existing one — the exact false pass
    a test-only-on-the-issue pipeline would have shipped. Measured across the bench."""
    from swebench.harness import compile_fn, run_cases
    fn = compile_fn(cand.src, task.fn_name)
    if fn is None:
        return False
    vok, _ = run_cases(fn, task.visible)
    if not vok or not task.regression:
        return False
    rok, _ = run_cases(fn, task.regression)
    return not rok
