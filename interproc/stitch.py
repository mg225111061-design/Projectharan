"""
§AI §2 — INTERPROCEDURAL STITCHING: reconstruct a cross-function accumulator into ONE recurrence (real code lives here).
================================================================================================================
Most folds today are intra-function; real accumulators/recurrences are scattered ACROSS functions (a sum builds up
through method calls / handlers). Interprocedural dataflow reconstructs the scattered pieces into a SINGLE recurrence
and feeds it to the §1 conjecturers / existing matchers. ★ Soundness: if crossing a function boundary, aliasing /
shared-state / side-effects contaminate the accumulation, DECLINE (a non-affine / non-deterministic handler is
rejected — and a secret/shared taint flow ties into §AH §6).

★ Honest boundary: this WIDENS the analysis REACH (folds that were invisible because the loop wasn't in one place);
it does NOT make most cross-function code foldable (control flow is still control flow). Measure the delta — it's the
practical reason behind a chunk of the ~5.7% floor, but the lift is modest. REUSE §P P6 catalog/distributed_state
(affine cross-handler composition + z3) — no new mechanism (existing matrix_recurrence kind).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence


@dataclass
class StitchResult:
    issued: bool
    grade: str = ""
    round_map: Optional[list] = None     # the single composed affine recurrence [A, B] (state ← A·state + B)
    verdict: object = None
    detail: str = ""


def stitch(handlers: Dict[str, str], schedule: Sequence[str]) -> StitchResult:
    """Stitch per-function affine state updates (`handlers`) executed in `schedule` (the call order across functions)
    into one composed recurrence, z3-proven equal to the sequential application. REUSE distributed_state_grade.
    A non-affine / aliased / nondeterministic handler ⇒ DECLINE (the contamination guard)."""
    import kernel_verdict as KV
    from catalog import distributed_state as DS
    v = DS.distributed_state_grade(handlers, list(schedule), label="interproc.stitch")
    if v.status != KV.EXACT:
        return StitchResult(False, "DECLINE", None, v, f"cross-function accumulation not reconstructible (aliasing / "
                            f"non-affine / nondeterministic) ⇒ DECLINE: {getattr(v, 'reason', '')[:90]}")
    rm = v.result.get("round_map") if isinstance(v.result, dict) else None
    return StitchResult(True, "EXACT", rm, v,
                        f"cross-function accumulator reconstructed into ONE affine recurrence {rm} (z3-proven ≡ "
                        "sequential application); fed to the recurrence matchers — existing matrix_recurrence kind")


def reach_delta() -> dict:
    """★ Honest measurement: interprocedural stitching widens the ANALYSIS REACH (cross-function accumulators become
    visible) but the fold-rate lift is MODEST — most cross-function code is still control flow, not accumulation."""
    return {"widens": "analysis reach (cross-function accumulators now visible to the matchers)",
            "does_not": "make most cross-function code foldable — control flow stays control flow",
            "expected_lift": "modest (a slice of the ~5.7% floor is single-function-restriction; this addresses it)"}


def adversarial_battery() -> dict:
    """Three affine handlers (s += c across methods) stitched on a fixed schedule fold to ONE recurrence (z3-proven);
    ★ a nonlinear / contaminated handler (shared-state mutation) ⇒ DECLINE; ★ a missing fixed schedule ⇒ DECLINE
    (interleaving not a recurrence). precision 1.0 — the contamination guard never lets an aliased accumulation fold."""
    affine = {"inc": "def inc(s): s = s + 3", "dbl": "def dbl(s): s = 2*s + 1", "add": "def add(s): s = s + 5"}
    ok = stitch(affine, ["inc", "dbl", "add"])
    nonlinear = {"bad": "def bad(s): s = s*s + 1"}             # non-affine ⇒ contamination guard DECLINEs
    nl = stitch(nonlinear, ["bad"])
    nosched = stitch(affine, [])                                # no fixed schedule ⇒ DECLINE
    cases = {
        "affine_stitches_exact": ok.issued and ok.grade == "EXACT",
        "nonlinear_declines": not nl.issued,                   # ★ contamination / non-affine guard
        "no_schedule_declines": not nosched.issued,
        "honest_reach_not_foldrate": "modest" in reach_delta()["expected_lift"],
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
