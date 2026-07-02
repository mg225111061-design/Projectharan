"""
§X PARADIGM 2 — PROJECTION FOLD (the safest; entirely in the decidable region, no impossible core).
================================================================================================================
A function returning a tuple/record may not fold whole, but the PROJECTION a callsite actually uses can. From liveness
(decidable) we know which outputs are live at a callsite; we fold ONLY the live projection, proving it equivalent.

Example: `stats(arr) -> (sum, min, max)` doesn't fold whole (min/max break the linear recurrence), but a callsite
using only `.0` (sum) folds the sum projection to O(1), never emitting the min/max work.

★ z3 gate (precision 1.0): for each live component π, prove ∀inputs. folded_π == original_π. The folded projection is
used only where proved. Per-callsite, polymorphic: callsite A folds the sum projection, callsite C (using min/max)
keeps the original — issued-vs-applied is naturally per-callsite. NO new certificate kind (each component folds via an
existing mechanism). Adversarial: a projection-fold that changes the live output is REJECTED.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List


@dataclass
class ProjectionFold:
    paradigm: str = "projection"
    mechanism: str = "linear_recurrence"
    applied_callsites: List[str] = field(default_factory=list)
    skipped_callsites: List[str] = field(default_factory=list)
    detail: str = ""

    @property
    def applied(self) -> bool:
        return bool(self.applied_callsites)


def _proj_equiv(folded_comp: Callable, original_comp: Callable, var_names: List[str]) -> bool:
    from catalog.equiv_check import prove_equiv_z3
    return prove_equiv_z3(folded_comp, original_comp, var_names).proved


def fold_live_projection(callsite: str, components: Dict[int, Callable], folded: Dict[int, Callable],
                         live: List[int], var_names: List[str], pf: ProjectionFold) -> bool:
    """At a callsite, fold ONLY the live output components. Applies iff EVERY live component's fold is z3-proved
    equivalent to the original; a non-foldable live component ⇒ keep the original whole (not applied here)."""
    for i in live:
        if i not in folded or not _proj_equiv(folded[i], components[i], var_names):
            pf.skipped_callsites.append(callsite)
            return False
    pf.applied_callsites.append(callsite)
    return True


def adversarial_battery() -> dict:
    """The live projection folds where proved; a projection-fold that CHANGES the live output is rejected; a callsite
    using a non-foldable projection keeps the original."""
    # stats(x) components: .0 = sum-like x*2 (folds), .1 = a non-linear/different shape used as the "min/max" stand-in
    components = {0: lambda e: e["x"] + e["x"], 1: lambda e: e["x"] * e["x"]}
    folded = {0: lambda e: 2 * e["x"], 1: lambda e: e["x"] * e["x"] + 1}   # .0 correct fold; .1 WRONG fold (+1)
    pf = ProjectionFold()
    a_sum = fold_live_projection("cs_uses_sum", components, folded, [0], ["x"], pf)          # live .0 ⇒ folds
    a_wrong = fold_live_projection("cs_uses_comp1", components, folded, [1], ["x"], ProjectionFold())  # .1 wrong ⇒ reject
    # a callsite using a component with NO folded form keeps the original
    a_nofold = fold_live_projection("cs_no_fold", components, {0: folded[0]}, [1], ["x"], ProjectionFold())
    cases = {"live_sum_projection_folds": a_sum, "result_changing_projection_rejected": not a_wrong,
             "nonfoldable_projection_keeps_original": not a_nofold}
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
