"""
v29 STAGE 27 — missing-info detector (schema-coverage over requirement slots).  ★cheapest + exact★
====================================================================================================
Over the S26 requirement schema, check which clearly-needed slots are UNBOUND (EARS-style coverage). This
is the dominant failure we break: HumanEvalComm shows 60%+ of code-LLMs SILENTLY emit code on an
incomplete prompt (Pass@1 drops 35-52%). We instead DETECT the gap and either reasonably complete it or
escalate the rare critical one.

Policy (fail-safe, §1.12/§1.13):
  • COMPLETE          — the core slots are bound → proceed.
  • MINOR missing     — a defaultable slot is absent → REASONABLE DEFAULT + STATED ASSUMPTION (does NOT ask,
                        does NOT block).
  • CRITICAL missing  — a slot that cannot be sensibly defaulted (e.g. no goal at all) → escalate to S30
                        (which still mostly PROCEEDs); never a silent wrong action, never a hard block.

★ HONEST (§1.4) ★: completeness is measured against the ASSUMED schema, NOT absolute (Rice) — the schema
itself is a modeling choice. The presence/absence of a slot is EXACT; whether it MATTERS (minor vs
critical) is a heuristic, so the response is always graceful (default+state or escalate), never a block.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from requirement_parser import RequirementSchema

# the core slots a coding task is expected to bind, and reasonable defaults for the defaultable ones
_CORE = ("goals", "inputs", "outputs")
_DEFAULTS: Dict[str, str] = {
    "inputs": "infer the input type from the goal (e.g. a list/number/string as the goal implies)",
    "outputs": "return the computed result; raise a clear error on invalid input",
    "error_behavior": "raise a clear, typed error on invalid input rather than failing silently",
    "edge_cases": "handle empty / boundary inputs (empty list, 0, negative) explicitly",
}
# slots whose absence cannot be defaulted — there is simply no task/contract to proceed with
_CRITICAL_IF_ABSENT = ("goals",)


@dataclass
class MissingReport:
    status: str                               # COMPLETE | MISSING
    missing: List[str] = field(default_factory=list)
    minor: Dict[str, str] = field(default_factory=dict)     # slot -> reasonable default + stated assumption
    critical: List[str] = field(default_factory=list)       # → escalate to S30 (still usually PROCEED)
    detail: str = ""

    @property
    def escalate_to_s30(self) -> bool:
        return bool(self.critical)

    def assumptions(self) -> List[str]:
        """The stated assumptions a fail-safe completion would carry forward (for the user to see)."""
        return [f"assumed {slot}: {default}" for slot, default in self.minor.items()]

    def __str__(self):
        if self.status == "COMPLETE":
            return "COMPLETE — core requirement slots are bound"
        return (f"MISSING {self.missing} — minor(defaulted)={list(self.minor)} "
                f"critical(→S30)={self.critical}")


def detect_missing(req: RequirementSchema, extra_expected: tuple = ("error_behavior", "edge_cases")) -> MissingReport:
    """Flag unbound slots; default the minor ones (with a stated assumption), escalate the critical ones.
    `extra_expected` are non-core, always-defaultable considerations (error behavior / edge cases)."""
    rep = MissingReport(status="COMPLETE")
    # core coverage
    for slot in _CORE:
        if not getattr(req, slot, None):
            rep.missing.append(slot)
            if slot in _CRITICAL_IF_ABSENT:
                rep.critical.append(slot)
            elif slot in _DEFAULTS:
                rep.minor[slot] = _DEFAULTS[slot]
    # extra (always defaultable) considerations — only surfaced as MINOR when there IS a task
    if req.goals:
        text = req.raw.lower()
        for slot in extra_expected:
            # error behaviour / edge cases are "covered" if the prompt ANYWHERE speaks to them
            mentioned = any(k in text
                            for k in (("error", "raise", "invalid", "exception") if slot == "error_behavior"
                                      else ("empty", "edge", "boundary", "zero", "negative")))
            if not mentioned and slot in _DEFAULTS:
                rep.minor[slot] = _DEFAULTS[slot]
                rep.missing.append(slot)
    if rep.missing:
        rep.status = "MISSING"
    rep.detail = ("escalate a critical gap to S30 (no task to default)" if rep.critical
                  else "reasonable defaults + stated assumptions (no question asked)" if rep.minor
                  else "core slots bound")
    return rep
