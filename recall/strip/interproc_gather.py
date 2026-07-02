"""
§AL §1.3 — INTERPROCEDURAL GATHER (§AI §2 strengthened): an accumulator scattered across functions/methods/handlers,
================================================================================================================
reconstructed by whole-program dataflow into ONE recurrence. ★ REUSE `interproc.stitch` (§AI §2 — affine cross-handler
composition, z3-proven ≡ the sequential application). No new mechanism; this module is the §AL front-door to it.
"""
from __future__ import annotations

from typing import Dict, Sequence

from recall import core


def fold(handlers: Dict[str, str], schedule: Sequence[str]) -> core.StripResult:
    """Stitch affine per-function updates into one recurrence (REUSE interproc.stitch); z3 disposes."""
    try:
        from interproc import stitch as ST
        v = ST.stitch(handlers, list(schedule))
        if v.issued and v.grade == "EXACT":
            return core.StripResult(True, "interproc(gather)", "matrix_recurrence", v.verdict,
                                    f"cross-function accumulator stitched into ONE recurrence {v.round_map} (z3 ≡ sequential)")
        return core.StripResult(False, "interproc(gather)", "", v.verdict, "non-affine/aliased/no-schedule ⇒ DECLINE")
    except Exception as e:  # noqa: BLE001
        return core.StripResult(False, "interproc(gather)", "", None, f"stitch raised ({e}) ⇒ DECLINE")


def adversarial_battery() -> dict:
    """★ three affine updates scattered across functions stitch into one recurrence (z3-gated, REUSE §AI §2); ★ a
    non-affine handler is DECLINEd by the contamination guard (no false EXACT)."""
    affine = {"inc": "def inc(s): s = s + 3", "dbl": "def dbl(s): s = 2*s + 1", "add": "def add(s): s = s + 5"}
    r = fold(affine, ["inc", "dbl", "add"])
    bad = fold({"bad": "def bad(s): s = s*s + 1"}, ["bad"])
    cases = {"interproc_stitches": r.folded, "nonaffine_declines": not bad.folded}
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
