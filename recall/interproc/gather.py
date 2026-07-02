"""
§AP §4.3 — GATHER the (unaliased) handler summaries along the schedule into ONE recurrence (REUSE §AI §2 stitch).
================================================================================================================
After §4.2 has resolved local aliases, the cross-function accumulator is a chain of plain affine maps; `interproc.stitch`
composes them along the fixed schedule into one round map s ← A·s + B and z3-PROVES the composition ≡ the sequential
application (and N rounds = the matrix power, O(log N)). No new mechanism — this is the existing stitch, fed by the
unaliased handlers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Sequence


@dataclass
class GatherResult:
    folded: bool
    round_map: Optional[list] = None
    detail: str = ""


def gather(handlers: Dict[str, str], schedule: Sequence[str]) -> GatherResult:
    """Stitch the unaliased affine handlers along `schedule` (z3-proven ≡ sequential). DECLINE on residual coupling."""
    try:
        from interproc import stitch as ST
        v = ST.stitch(handlers, list(schedule))
        return GatherResult(v.issued and v.grade == "EXACT", v.round_map, v.detail)
    except Exception as e:  # noqa: BLE001
        return GatherResult(False, None, f"gather raised ({e}) ⇒ DECLINE")
