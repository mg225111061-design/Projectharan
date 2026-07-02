"""
Pillar 3 · PHASE V — wider Z3 equivalence coverage (move transforms PROBABILISTIC → EXACT).
============================================================================================
The biggest accuracy lever: prove more transform classes equivalent so the verifier can award EXACT (a
machine-checked proof) instead of settling for PROBABILISTIC (differential-only). Each class here is proven by
bounded translation validation (Z3 UNSAT-of-negation over symbolic inputs — same engine as equiv.py / lifting),
then still measured whole-program and graded by the ADT (EXACT needs proof AND a real win; speed-neutral ⇒
DECLINE, never "EXACT 1.0×"). An adversarial wrong variant in each class is Z3-refuted ⇒ DECLINE (the moat).

These reuse the lifting grader with spec = original (an identity lift), so the proof obligation is exactly
"optimized ≡ original", graded with a coherent measured f and ratio ≤ ceiling by construction.
"""
from __future__ import annotations

from typing import Callable, List, Tuple

import z3

from pillar3 import lifting as LF


# ── transform classes (each: original, the equivalent optimized, an adversarial WRONG variant) ──────────
# 1) strength reduction:  x**4  →  t=x*x; t*t   (** is materially slower than multiplies; Z3 proves equality)
def sr_original(a):
    return [x ** 4 for x in a]


def sr_optimized(a):
    out = []
    for x in a:
        t = x * x
        out.append(t * t)
    return out


def sr_wrong(a):
    return [x * 4 for x in a]                                # x*4 ≠ x**4 — Z3 refutes


# 2) loop-invariant hoisting:  recompute a*b each iteration  →  hoist it once  (proven identical)
def li_original(a, b, xs):
    out = []
    for x in xs:
        out.append(a * b + x)
    return out


def li_optimized(a, b, xs):
    t = a * b
    out = []
    for x in xs:
        out.append(t + x)
    return out


def li_wrong(a, b, xs):
    t = a + b                                               # hoisted the WRONG expression
    return [t + x for x in xs]


# 3) common-subexpression elimination:  (x+1)*(x+1)  →  t=x+1; t*t   (proven identical; one add saved per item)
def cse_original(a):
    return [(x + 1) * (x + 1) for x in a]


def cse_optimized(a):
    out = []
    for x in a:
        t = x + 1
        out.append(t * t)
    return out


def cse_wrong(a):
    return [(x + 1) * (x - 1) for x in a]                   # x²−1 ≠ (x+1)² — Z3 refutes


def _sym_list(n):
    return ([z3.Int(f"a{i}") for i in range(n)],)


def _sym_abxs(n):
    return (z3.Int("a"), z3.Int("b"), [z3.Int(f"x{i}") for i in range(n)])


# inputs are generated ONCE and cached, so the timed region is the kernel (not input-gen) — a fair, fixed
# workload for base/floor/candidate (read-only kernels); raises the measured hotspot fraction honestly.
import random as _rnd

_LIST_CACHE: dict = {}
_ABXS_CACHE: dict = {}


def _mk_list(size):
    if size not in _LIST_CACHE:
        rng = _rnd.Random(5)
        _LIST_CACHE[size] = [rng.randrange(-500, 500) for _ in range(size)]
    return (_LIST_CACHE[size],)


def _mk_abxs(size):
    if size not in _ABXS_CACHE:
        rng = _rnd.Random(9)
        _ABXS_CACHE[size] = [rng.randrange(-500, 500) for _ in range(size)]
    return (6, 7, _ABXS_CACHE[size])


# each transform as an identity-lift (spec = original): EXACT iff Z3 proves optimized≡original AND a win is measured
def catalog() -> List[LF.Lift]:
    return [
        LF.Lift("strength_reduction_x2", "strength_reduction", sr_original, sr_original, sr_optimized,
                _sym_list, lambda: _mk_list(2600), residual_iters=60, sizes=(3, 5, 8), n=2600, floor=1.02),
        LF.Lift("loop_invariant_hoist", "loop_invariant_hoist", li_original, li_original, li_optimized,
                _sym_abxs, lambda: _mk_abxs(4000), residual_iters=40, sizes=(3, 5, 8), n=4000, floor=1.02),
        LF.Lift("common_subexpr_elim", "cse", cse_original, cse_original, cse_optimized,
                _sym_list, lambda: _mk_list(4000), residual_iters=40, sizes=(3, 5, 8), n=4000, floor=1.02),
    ]


def wrong_variants() -> List[LF.Lift]:
    return [
        LF.Lift("strength_reduction_WRONG", "strength_reduction", sr_original, sr_original, sr_wrong,
                _sym_list, lambda: _mk_list(2600), residual_iters=60, sizes=(3, 5, 8), n=2600),
        LF.Lift("loop_invariant_WRONG", "loop_invariant_hoist", li_original, li_original, li_wrong,
                _sym_abxs, lambda: _mk_abxs(4000), residual_iters=40, sizes=(3, 5, 8), n=4000),
        LF.Lift("cse_WRONG", "cse", cse_original, cse_original, cse_wrong,
                _sym_list, lambda: _mk_list(4000), residual_iters=40, sizes=(3, 5, 8), n=4000),
    ]


def proves_exact(lift: "LF.Lift") -> "Tuple[bool, bool]":
    """(optimized≡original proven?, original≡original proven?) — the two Z3 obligations of an identity lift."""
    lo, so, _ = LF.prove_lift(lift.original, lift.spec, lift.optimized, lift.sym_factory, lift.sizes)
    return so, lo
