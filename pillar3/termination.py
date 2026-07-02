"""
Pillar 3 · ROUND 3 #71 — termination via ranking functions (Z3-checked, SOUND).
=================================================================================
Many transforms (loop reordering, fusion, parallelization, speculative execution) are only valid for loops
that TERMINATE. A ranking function r(s) witnesses termination: under the loop guard, r is bounded below and
STRICTLY DECREASES each step, so the loop cannot run forever (no infinite descent over ℤ≥0). Z3 discharges both
obligations for a candidate r; if both hold the loop PROVABLY terminates (a machine-checked certificate ⇒
EXACT). If Z3 finds a state where r does not decrease / is unbounded, we CANNOT prove termination ⇒ DECLINE
(sound: we never ASSUME termination — a transform that needs it stays unapplied). Clock-B verification.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

import z3

import kernel_verdict as KV


@dataclass
class TermResult:
    verdict: "KV.Verdict"
    proved: bool
    counterexample: Optional[str]


def proves_termination(cond: Callable, step: Callable, rank: Callable) -> Tuple[bool, Optional[str]]:
    """Z3: does rank witness termination?  ∀x: cond(x) ⇒ rank(x) ≥ 0  AND  cond(x) ⇒ rank(step(x)) < rank(x).
    Both UNSAT-of-negation ⇒ proven. Returns (proved, counterexample-reason)."""
    x = z3.Int("x")
    s_bb = z3.Solver()
    s_bb.add(z3.And(cond(x), z3.Not(rank(x) >= 0)))          # a guarded state where r < 0 ⇒ not bounded below
    s_dec = z3.Solver()
    s_dec.add(z3.And(cond(x), z3.Not(rank(step(x)) < rank(x))))   # a guarded step where r does not strictly drop
    if s_bb.check() == z3.sat:
        return False, f"not bounded below (e.g. x={s_bb.model()[x]})"
    if s_dec.check() == z3.sat:
        return False, f"does not strictly decrease (e.g. x={s_dec.model()[x]})"
    if s_bb.check() == z3.unknown or s_dec.check() == z3.unknown:
        return False, "z3 unknown — conservatively unproven"
    return True, None


def termination_grade(name: str, cond: Callable, step: Callable, rank: Callable) -> TermResult:
    """EXACT iff a ranking function PROVES termination; else DECLINE (never assume termination — sound)."""
    proved, cex = proves_termination(cond, step, rank)
    if proved:
        cert = KV.Cert(KV.EXACT, "ranking_function", passed=True, check_cost="Z3 (2 ∀-goals)",
                       detail=f"{name}: ranking function bounded-below & strictly-decreasing under the guard ⇒ terminates")
        return TermResult(KV.exact(name, f"terminates:{name}", "Clock-B termination proof", cert), True, None)
    return TermResult(KV.decline(f"{name}: cannot prove termination ({cex}) ⇒ DECLINE (do not assume it)",
                                 f"terminates:{name}"), False, cex)


# ── batteries: terminating loops (each with a ranking function) and non-terminating ones (no rank works) ───
def terminating():
    return [
        # while x>0: x -= 3        rank = x
        ("countdown_by_3", lambda x: x > 0, lambda x: x - 3, lambda x: x),
        # while x>5: x -= 1         rank = x-5
        ("down_to_5", lambda x: x > 5, lambda x: x - 1, lambda x: x - 5),
        # while x<100: x += 7       rank = 100 - x
        ("up_to_100", lambda x: x < 100, lambda x: x + 7, lambda x: 100 - x),
        # while x>0: x = x/2 (integer halving, x≥1)  rank = x
        ("halving", lambda x: x > 0, lambda x: x / 2, lambda x: x),
    ]


def nonterminating():
    return [
        # while x>0: x += 1         r=x increases ⇒ not decreasing (genuinely diverges)
        ("incr_forever", lambda x: x > 0, lambda x: x + 1, lambda x: x),
        # while x>0: x -= 1 but claim rank = x+10 ... still decreases; use a real non-term: while x!=0: x-=2
        # (from an odd start never reaches 0) — rank=x not bounded below under guard x!=0
        ("step_over_zero", lambda x: x != 0, lambda x: x - 2, lambda x: x),
    ]
