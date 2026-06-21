"""
Pillar 3 · PHASE A — algorithm recognition (hand-rolled idiom → known optimal), wide.
=====================================================================================
KernelFaRer-in-spirit: recognise a naive implementation of a known algorithm and propose the optimal form.
These idioms carry CONTROL FLOW (max/min/branches), so Z3 bounded translation validation does not apply
(it would need to symbolically execute `if`/`max` over symbolic values) — they are graded PROBABILISTIC by a
STRONG evidence set, not EXACT. The grade is honest: differential over PHASE-I boundary+random inputs, the
PHASE-M metamorphic net (cross-check vs the slow-correct oracle, invariants), and a coherent whole-program
measurement (ratio ≤ ceiling). A subtly-wrong replacement is caught by the net ⇒ DECLINE. (Only a machine-
checked proof earns EXACT — these earn PROBABILISTIC with a stated δ; §X.)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Tuple

import kernel_verdict as KV
from pillar3 import inputgen as IG
from pillar3 import lifting as LF
from pillar3 import metamorphic as MM


@dataclass
class Recognizer:
    name: str
    waste_type: str
    naive: Callable
    fast: Callable
    make_input: Callable[[], tuple]
    residual_iters: int
    gen_inputs: Callable[[], List[tuple]]                 # evidence set (args tuples) for differential + relations
    relations: List[Tuple[str, Callable]] = field(default_factory=list)
    n: int = 0
    floor: float = 1.10


def recognize_and_grade(R: "Recognizer", *, samples: int = 7) -> KV.Verdict:
    """Differential FIRST over a STRONG evidence set (PHASE I); then the metamorphic net incl. cross-check vs the
    slow-correct oracle (PHASE M); then a coherent whole-program measurement (ratio ≤ ceiling). PROBABILISTIC with
    δ from the evidence size; any divergence/violation ⇒ DECLINE. No Z3 here (control flow) ⇒ never EXACT."""
    inputs = R.gen_inputs()
    div = IG.first_divergence(R.naive, R.fast, inputs)
    if div is not None:
        return KV.decline(f"recognizer '{R.name}': differential divergence {div} ⇒ DECLINE", R.waste_type)
    # metamorphic net: cross-check the fast form against the slow-correct oracle on the same evidence
    gen1 = _one_arg_gen(inputs)
    if R.relations:
        ok, detail = MM.metamorphic_gate(lambda x: R.fast(*_as_args(x)), R.relations, gen1, k=min(12, len(inputs)))
        if not ok:
            return KV.decline(f"recognizer '{R.name}': {detail}", R.waste_type)
    rep = LF.measure_lift(R.naive, R.fast, R.make_input, R.residual_iters, n=R.n, samples=samples)
    if not rep.beats(R.floor):
        v = KV.decline(f"recognizer '{R.name}': no whole-program win ≥ {R.floor:.2f}× "
                       f"(measured {rep.whole_program_ratio:.2f}×) ⇒ DECLINE", R.waste_type)
        v.report = rep
        return v
    delta = 3.0 / max(1, len(inputs))
    cert = KV.Cert(KV.PROBABILISTIC, "differential+metamorphic", passed=True, check_cost=f"{len(inputs)} cases",
                   delta=delta, detail=f"strong evidence set (boundary+random+relations), δ={delta:.3f}; control "
                                       f"flow ⇒ no Z3 ⇒ PROBABILISTIC (never EXACT)")
    v = KV.probabilistic(R.fast, R.waste_type, str(rep), cert)
    v.report = rep
    return v


def _as_args(x):
    return x if isinstance(x, tuple) else (x,)


def _one_arg_gen(inputs: List[tuple]):
    """A generator the metamorphic relations can call: yields the FIRST positional arg of each evidence case
    (the data structure the relations operate on)."""
    import itertools
    cyc = itertools.cycle(inputs)
    return lambda: next(cyc)[0]


# ── recognizers ──────────────────────────────────────────────────────────────────────────────────────
# Kadane: maximum-subarray sum, naive O(n²) over all subarrays → single-pass O(n)
def kadane_naive(xs):
    best = xs[0]
    for i in range(len(xs)):
        s = 0
        for j in range(i, len(xs)):
            s += xs[j]
            if s > best:
                best = s
    return best


def kadane_fast(xs):
    best = cur = xs[0]
    for x in xs[1:]:
        cur = x if x > cur + x else cur + x
        if cur > best:
            best = cur
    return best


def kadane_wrong(xs):                                        # cur = max(x, cur) — forgets the running sum
    best = cur = xs[0]
    for x in xs[1:]:
        cur = x if x > cur else cur
        if cur > best:
            best = cur
    return best


# two-sum existence: naive O(n²) pair scan → hash set O(n)
def two_sum_naive(xs, target):
    for i in range(len(xs)):
        for j in range(i + 1, len(xs)):
            if xs[i] + xs[j] == target:
                return True
    return False


def two_sum_fast(xs, target):
    seen = set()
    for x in xs:
        if target - x in seen:
            return True
        seen.add(x)
    return False


def two_sum_wrong(xs, target):                              # allows i==j (uses the same element twice)
    seen = set()
    for x in xs:
        if target - x in seen or target - x == x:
            return True
        seen.add(x)
    return False


import random as _rnd

_KAD_CACHE: dict = {}


def _make_kadane_input(size: int = 240):
    if size not in _KAD_CACHE:
        rng = _rnd.Random(31)
        _KAD_CACHE[size] = [rng.randrange(-30, 30) for _ in range(size)]
    return (_KAD_CACHE[size],)


def _kadane_inputs() -> List[tuple]:
    rng = _rnd.Random(3)
    cases = [([5],), ([-5],), ([1, -2, 3, -1, 2],), ([-1, -2, -3],), ([2, 2, 2],), ([0, 0, 0],)]
    for _ in range(20):
        s = rng.randrange(1, 14)
        cases.append(([rng.randrange(-20, 20) for _ in range(s)],))
    return cases


_TS_CACHE: dict = {}


def _make_two_sum_input(size: int = 600):
    if size not in _TS_CACHE:
        rng = _rnd.Random(37)
        _TS_CACHE[size] = ([rng.randrange(0, 4000) for _ in range(size)], 7919)
    return _TS_CACHE[size]


def _two_sum_inputs() -> List[tuple]:
    rng = _rnd.Random(4)
    cases = [([1, 2, 3], 5), ([1, 2, 3], 100), ([4], 8), ([], 0), ([3, 3], 6), ([3], 6)]
    for _ in range(20):
        xs = [rng.randrange(0, 40) for _ in range(rng.randrange(1, 12))]
        cases.append((xs, rng.randrange(0, 80)))
    return cases


def catalog() -> List[Recognizer]:
    return [
        Recognizer("kadane_max_subarray", "algo_replace", kadane_naive, kadane_fast,
                   lambda: _make_kadane_input(240), residual_iters=200, gen_inputs=_kadane_inputs,
                   relations=[("ge_max_element", lambda f, xs: f(xs) >= max(xs))], n=240, floor=1.15),
        Recognizer("two_sum_hash", "algo_replace", two_sum_naive, two_sum_fast,
                   lambda: _make_two_sum_input(600), residual_iters=120, gen_inputs=_two_sum_inputs,
                   relations=[], n=600, floor=1.15),
    ]
