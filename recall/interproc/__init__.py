"""
§AP §4 — INTERPROC SUMMARY: summarize → unalias → gather. Mostly REUSES §AI §2 (`interproc.stitch`); the genuine
================================================================================================================
recall win is §4.2 unalias — copy-propagating local state-aliases so a laundered-but-affine cross-function accumulator
(`t = s; s = 2*t + 1`) folds instead of false-DECLINING. The gather z3-proves the composition ≡ sequential; genuine
multi-state coupling stays an honest DECLINE. No new mechanism, no new certificate kind.
"""
from __future__ import annotations

from typing import Dict, Sequence

from recall.interproc import summarize as SUM, unalias as UA, gather as GA


def fold(handlers: Dict[str, str], schedule: Sequence[str]) -> GA.GatherResult:
    """Summarize, resolve local aliases, then stitch along the schedule (z3-gated)."""
    clean = UA.unalias(handlers)
    return GA.gather(clean, schedule)


def adversarial_battery() -> dict:
    """★ a LAUNDERED-but-affine handler (`t = s; s = 2*t + 1`) folds AFTER unalias — and ★★ false-DECLINEs WITHOUT it
    (the genuine §4.2 delta); ★ three clean affine handlers stitch into one recurrence (z3-proven ≡ sequential, REUSE
    §AI §2); ★★ genuine multi-STATE coupling (`def h(s, u): s = s + u`) stays an honest DECLINE; ★ a non-affine handler
    DECLINEs."""
    laundered = {"a": "def a(s):\n    t = s\n    s = 2*t + 1\n    return s",
                 "b": "def b(s):\n    u = s\n    s = u + 5\n    return s"}
    with_unalias = fold(laundered, ["a", "b"])
    without_unalias = GA.gather(laundered, ["a", "b"])            # ★★ the delta: stitch alone sees free symbol t/u

    clean = {"inc": "def inc(s): s = s + 3", "dbl": "def dbl(s): s = 2*s + 1", "add": "def add(s): s = s + 5"}
    clean_ok = fold(clean, ["inc", "dbl", "add"])

    coupled = {"h": "def h(s, u): s = s + u"}                     # genuine 2-state coupling ⇒ not one recurrence
    coupled_decline = fold(coupled, ["h"])
    nonaffine = fold({"q": "def q(s): s = s*s + 1"}, ["q"])       # non-affine ⇒ DECLINE

    cases = {
        "laundered_folds_after_unalias": with_unalias.folded,
        "laundered_declines_without_unalias": not without_unalias.folded,   # ★★ the genuine §4.2 contribution
        "clean_affine_stitches": clean_ok.folded,
        "coupled_multistate_declines": not coupled_decline.folded,          # ★★ real aliasing stays DECLINE
        "nonaffine_declines": not nonaffine.folded,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
