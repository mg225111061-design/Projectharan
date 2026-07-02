"""
Pillar 3 · ROUND 3 #64 — CEGAR: counterexample-guided abstraction refinement for loop invariants (Z3, EXACT).
==============================================================================================================
A coarse invariant often can't prove a safety property; CEGAR refines it. Start from the weakest invariant
(True); if it can't prove ¬bad, a spurious counterexample exists (a state the invariant admits but that
violates the property). Refine by adding a candidate predicate that (a) keeps the invariant INDUCTIVE
(init⇒I, I∧guard⇒I[next]) and (b) tightens it, then retry. Converge to a PROVEN inductive invariant ⇒ EXACT
(a machine-checked safety proof), or exhaust the candidates ⇒ DECLINE. When the property is genuinely false, a
bounded reachability check exhibits the real counterexample (REFUTED) — never a false "safe" (a wrong safe is a
correctness bug). Demonstrates the loop: x:=x+2 from 0 can't prove x≠51 until refined with the predicate x is
EVEN; the genuinely-reachable x=50 is correctly NOT proved (real bug found by bounded reachability).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

import z3

import kernel_verdict as KV


def _valid(claim) -> bool:
    s = z3.Solver()
    s.add(z3.Not(claim))
    return s.check() == z3.unsat


def _reachable_bounded(init_val: int, trans_int: Callable, guard_int: Callable, bad_int: Callable, k: int) -> bool:
    """Concrete bounded reachability: does the loop reach a bad state within k steps? (witnesses a REAL bug.)"""
    x = init_val
    for _ in range(k):
        if bad_int(x):
            return True
        if not guard_int(x):
            break
        x = trans_int(x)
    return bad_int(x)


@dataclass
class CEGARResult:
    verdict: "KV.Verdict"
    status: str                    # PROVEN | REFUTED | CANNOT_PROVE
    invariant: List[str]
    iterations: int


def cegar_prove(name: str, init, trans, guard, bad, candidates: List[Callable], *,
                init_val: int, trans_int: Callable, guard_int: Callable, bad_int: Callable,
                max_iters: int = 12, bmc_depth: int = 80) -> CEGARResult:
    """init/trans/guard/bad : (z3 Int x) -> z3 expr.  candidates : refining predicates (each a named fn of x).
    Returns a CEGARResult; PROVEN ⇒ EXACT (inductive invariant proves ¬bad), real bug ⇒ DECLINE (REFUTED)."""
    x = z3.Int("x")
    preds: List[Callable] = []
    for it in range(max_iters):
        I = z3.And(*[p(x) for p in preds]) if preds else z3.BoolVal(True)
        I_next = z3.And(*[p(trans(x)) for p in preds]) if preds else z3.BoolVal(True)
        base = _valid(z3.Implies(init(x), I))
        step = _valid(z3.Implies(z3.And(I, guard(x)), I_next))
        proves = _valid(z3.Implies(I, z3.Not(bad(x))))
        if base and step and proves:
            cert = KV.Cert(KV.EXACT, "cegar_inductive_invariant", passed=True, check_cost="Z3 (base+step+safety)",
                           detail=f"{name}: refined inductive invariant {[p.__name__ for p in preds]} proves ¬bad")
            return CEGARResult(KV.exact(name, f"cegar:{name}", "safety EXACT", cert), "PROVEN",
                               [p.__name__ for p in preds], it)
        # refine: add a candidate that keeps inductiveness (a spurious-cex-eliminating predicate)
        added = False
        for c in candidates:
            if c in preds:
                continue
            np = preds + [c]
            I2 = z3.And(*[p(x) for p in np])
            I2n = z3.And(*[p(trans(x)) for p in np])
            if _valid(z3.Implies(init(x), I2)) and _valid(z3.Implies(z3.And(I2, guard(x)), I2n)):
                preds.append(c)
                added = True
                break
        if not added:
            break
    # could not prove — is it a REAL bug (bounded reachability) or just out of candidate strength?
    if _reachable_bounded(init_val, trans_int, guard_int, bad_int, bmc_depth):
        v = KV.decline(f"{name}: property is FALSE — bad state reachable (bounded reachability witness) ⇒ DECLINE", f"cegar:{name}")
        return CEGARResult(v, "REFUTED", [p.__name__ for p in preds], max_iters)
    v = KV.decline(f"{name}: could not find a refining inductive invariant from the candidate pool ⇒ DECLINE", f"cegar:{name}")
    return CEGARResult(v, "CANNOT_PROVE", [p.__name__ for p in preds], max_iters)


# ── the worked system: x:=x+2 from 0 while x<100; candidate refining predicates ─────────────────────────
def _even(x):
    return x % 2 == 0


def _nonneg(x):
    return x >= 0


def _le100(x):
    return x <= 100


_even.__name__ = "x%2==0"
_nonneg.__name__ = "x>=0"
_le100.__name__ = "x<=100"
CANDIDATES = [_even, _nonneg, _le100]

_SYS = dict(init=lambda x: x == 0, trans=lambda x: x + 2, guard=lambda x: x < 100,
            init_val=0, trans_int=lambda x: x + 2, guard_int=lambda x: x < 100)
