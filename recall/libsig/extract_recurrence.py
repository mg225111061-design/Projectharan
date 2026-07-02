"""
§AP §2.2 — EXTRACT the recurrence behind the recognized idiom and DISPOSE it through the existing z3 gate.
================================================================================================================
Given the idiom (§2.1) and the idiom's unary oracle (the real computation as a function of n), route to the EXISTING
lens and let it dispose: popcount → `recall.k_regular.fold` (M22, the R=44 lens); cumsum/diff/cumprod/IIR/EMA →
`recall.core.fold_via_ai` (the conjecturers: linear/polynomial/geometric/C-finite, z3 ∀-proof + held-out); transcendental
DFT/FFT → an honest DECLINE (it is not a fold). ★ S-1: no new disposer. A misrecognized idiom yields an oracle the gate
REJECTS ⇒ no false EXACT.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class ExtractResult:
    folded: bool
    idiom: str = ""
    lens: str = ""
    structure: str = ""
    detail: str = ""


def extract_and_fold(idiom: str, lens: str, oracle: Optional[Callable[[int], object]]) -> ExtractResult:
    """Dispose the idiom's oracle through the existing lens. `oracle(n)` is the idiom's value at index n."""
    if lens == "decline" or oracle is None:
        return ExtractResult(False, idiom, lens, "", f"{idiom!r} is transcendental / no oracle ⇒ honest DECLINE (not a fold)")
    if lens == "k_automatic":
        from recall import k_regular as KR
        r = KR.fold(oracle)
        return ExtractResult(r.folded, idiom, lens, r.kind, r.detail)
    if lens == "window":
        # uniform moving-average / running aggregate: the incremental recurrence is linear ⇒ the conjecturers dispose
        # the running-aggregate oracle (the §Z window lens is the production path; here the recurrence is C-finite).
        from recall import core
        r = core.fold_via_ai(oracle, f"libsig({idiom})")
        return ExtractResult(r.folded, idiom, "window→conjecture", r.structure_class, r.detail)
    # default: the conjecturers (linear / polynomial / geometric / C-finite)
    from recall import core
    r = core.fold_via_ai(oracle, f"libsig({idiom})")
    return ExtractResult(r.folded, idiom, lens, r.structure_class, r.detail)
