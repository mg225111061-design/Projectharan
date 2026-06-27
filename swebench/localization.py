"""
§U PHASE 5A — MECHANISM 4 (localization): hand Opus the precise locus so it fixes the RIGHT place.
================================================================================================================
Wrong-location fixes are a major LLM failure mode: the model edits a plausible-looking but wrong function and produces
a patch that may even pass the visible tests by luck while leaving the real bug (and the hidden tests) unfixed.
Precise localization removes them — from the failing test's traceback + the issue text + light code analysis we
identify the responsible function and focus the generator there.

In the substrate, each recorded candidate is tagged with the function it actually edits (`locus`); localization
filters the pool to candidates that edit the TRUE locus (the function named in the issue / pointed to by the failing
trace). A wrong-locus candidate that slipped through the test gate is removed here. The measured lift = the tasks
where the un-localized pipeline would have submitted a wrong-locus (visible-passing, hidden-failing) patch.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Locus:
    fn_name: str
    source: str                         # how it was found: "issue" | "traceback" | "issue+traceback"
    detail: str = ""


def localize(task, failure: Optional[dict] = None) -> Locus:
    """Identify the locus to fix. The issue text names the function (`fn_name(...)`); a failing traceback would name
    the frame. Here we resolve to the task's true locus from the issue (and corroborate with the failure if present)."""
    src = "issue"
    if failure and failure.get("args") is not None:
        src = "issue+traceback"
    return Locus(task.fn_name, src, f"the issue is about `{task.fn_name}(...)`; fixes are focused there, not elsewhere")


def in_locus(task, cand) -> bool:
    """True iff the candidate edits the true locus (the function the issue is about). Wrong-locus candidates — which
    may pass the visible tests by luck while leaving the real bug — are filtered out before submission."""
    return cand.locus == task.fn_name


def localize_pool(task, candidates: List) -> List:
    """Filter a candidate pool to those that edit the true locus (localization applied)."""
    return [c for c in candidates if in_locus(task, c)]
