"""
§AL core — the SHARED disposer every strip module routes through. ★ S-2: the strip modules only NORMALIZE; this is the
================================================================================================================
single place where a candidate is DISPOSED, and it disposes EXACTLY the way §AI/§AJ does — precheck → router → the five
conjecturers, each gated by z3 ∀-proof + held-out=200. A wrong strip just produces a candidate the gate REJECTS, so no
strip module can ever manufacture a false EXACT — precision 1.0 is held in ONE place, not eight.

★ S-1: no new mechanism / no new disposer — this is a thin re-entry into the existing engine. ★ S-3: any DECLINE→ACCEPT
promotion goes through here (z3). LLM-free, zero-dep.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class StripResult:
    folded: bool
    disguise: str = ""               # which disguise was stripped (recall-priority signal)
    structure_class: str = ""        # the recovered structure (linear_recurrence / polynomial / …)
    verdict: object = None
    detail: str = ""


def fold_via_ai(fn: Callable[[int], object], disguise: str, probe: int = 48) -> StripResult:
    """Dispose a (post-strip) unary oracle through the UNCHANGED §AI/§AJ path: §AJ precheck (skip random) → §AJ router
    (order) → the five §AI conjecturers (z3 ∀-proof + held-out=200). EXACT only when the gate passes; else DECLINE."""
    if fn is None:
        return StripResult(False, disguise, "", None, "no oracle after strip ⇒ nothing to dispose")
    try:
        from conjecture import precheck as PC, router as RT
        pc = PC.worth_conjecturing(fn)
        if not pc.proceed:
            return StripResult(False, disguise, "", None, f"precheck skipped ({pc.signature}) ⇒ DECLINE (fast)")
        r, _, key = RT.first_fold(fn)
        if r is not None and r.issued:
            return StripResult(True, disguise, r.structure_class, r.verdict,
                               f"stripped {disguise} ⇒ {key} folded it (z3 ∀-proof + held-out) ⇒ EXACT")
        return StripResult(False, disguise, "", None, f"stripped {disguise} but the conjecturers DECLINED (z3 gate)")
    except Exception as e:  # noqa: BLE001
        return StripResult(False, disguise, "", None, f"strip/fold raised ({e}) ⇒ DECLINE")


def safe_oracle(fn: Callable[[int], object], n: int) -> Optional[int]:
    """Probe one point defensively (the strip produced fn; confirm it is a numeric unary oracle)."""
    try:
        v = fn(n)
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None
    except Exception:  # noqa: BLE001
        return None
