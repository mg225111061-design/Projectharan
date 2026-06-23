"""
Pillar 3 · ROUND 2 #59 — jump threading / branch simplification (Z3, SOUND) — a verified transform.
====================================================================================================
A nested branch is REDUNDANT when the outer guard already determines the inner condition:
   if outer(x): if inner(x): A else B      with   outer ⇒ inner   ⟹   the inner test always takes A.
Z3 proves outer ⇒ inner (or outer ⇒ ¬inner); proven ⇒ the inner branch can be THREADED to its constant
outcome — a behavior-preserving simplification ⇒ EXACT (a verified transform / Clock-B). If the implication
does NOT hold (Z3 counterexample), the inner branch is live ⇒ DECLINE (threading it would change behavior).
Honest: pure-Python interpreter timing barely moves (~1×); the win is realized at the COMPILED/IR level, so we
report this as a VERIFIED SIMPLIFICATION (no speedup claim in-sandbox), not a measured Clock-A/C win.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Tuple

import z3

import kernel_verdict as KV


@dataclass
class ThreadResult:
    verdict: "KV.Verdict"
    redundant: bool
    always: Optional[bool]        # the constant outcome of the inner test under the outer guard
    counterexample: Optional[str]


def _valid(claim) -> Tuple[bool, Optional[str]]:
    s = z3.Solver()
    s.add(z3.Not(claim))
    r = s.check()
    if r == z3.unsat:
        return True, None
    if r == z3.sat:
        return False, str(s.model())
    return False, "z3 unknown"


def analyze_branch(name: str, outer: Callable, inner: Callable) -> ThreadResult:
    """Z3: under the outer guard, is the inner test a constant? outer⇒inner (always True) or outer⇒¬inner (always
    False) ⇒ the inner branch threads to that constant ⇒ EXACT. Neither ⇒ the inner branch is live ⇒ DECLINE."""
    x = z3.Int("x")
    imp_true, _ = _valid(z3.Implies(outer(x), inner(x)))
    imp_false, cex = _valid(z3.Implies(outer(x), z3.Not(inner(x))))
    if imp_true or imp_false:
        always = True if imp_true else False
        cert = KV.Cert(KV.EXACT, "branch_redundancy_proof", passed=True, check_cost="Z3 outer⇒inner",
                       detail=f"{name}: outer guard ⇒ inner test is always {always} ⇒ inner branch threaded "
                              f"(behavior-preserving simplification)")
        return ThreadResult(KV.exact(name, f"thread:{name}", "verified simplification (Clock-B)", cert), True, always, None)
    v = KV.decline(f"{name}: inner test is LIVE under the outer guard (counterexample {cex}) ⇒ cannot thread ⇒ DECLINE",
                   f"thread:{name}")
    return ThreadResult(v, False, None, cex)


# ── batteries: redundant nested branches (threadable) and live ones (must keep) ─────────────────────────
def redundant_branches():
    return [
        ("gt5_implies_gt0", lambda x: x > 5, lambda x: x > 0),          # outer ⇒ inner True
        ("gt5_implies_not_lt0", lambda x: x > 5, lambda x: x < 0),      # outer ⇒ inner False
        ("eq10_implies_even_or", lambda x: x == 10, lambda x: x > 3),   # outer ⇒ inner True
        ("ge0_and_le0_dead", lambda x: z3.And(x >= 100, x < 50), lambda x: x > 0),  # outer is unsat ⇒ vacuously redundant
    ]


def live_branches():
    return [
        ("gt5_not_imply_gt10", lambda x: x > 5, lambda x: x > 10),      # x=6..10 violates both directions
        ("gt0_not_imply_even", lambda x: x > 0, lambda x: x % 2 == 0),  # parity is live under x>0
    ]
