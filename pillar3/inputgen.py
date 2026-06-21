"""
Pillar 3 · PHASE I — stronger input generation (shrink δ, catch what a tiny random sample misses).
==================================================================================================
PROBABILISTIC(ε,δ) is only as trustworthy as the inputs behind it. A 3-sample random check gives δ=3/3=1.0 —
nearly meaningless. This module builds a much stronger evidence set: boundary/edge enumeration (empty, singleton,
zeros, ±extremes, duplicates, sorted/reversed), property-based random over many sizes, and Z3-guided inputs that
drive a branch predicate down BOTH paths (a concolic-lite step). δ is reported from the real sample size (rule of
three, 3/n) — it shrinks as n grows. The slow-correct original is the gold oracle; the first divergence is the
witness. This never invents a win — it only makes a wrong fix more likely to be caught (Rule 6).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Tuple

import z3

from pillar3 import verifier as _V


# ── building blocks ─────────────────────────────────────────────────────────────────────────────────────
def boundary_ints() -> List[int]:
    return [0, 1, -1, 2, -2, 3, 255, 256, -256, 1023, 1024, 10 ** 6, -(10 ** 6)]


def edge_lists() -> List[List[int]]:
    """The shapes a random mid-size sample almost never produces but bugs love."""
    return [[], [0], [1], [-1], [0, 0], [1, 1, 1], [2, 1], [1, 2], list(range(6)), list(range(6))[::-1],
            [5] * 6, [0, 0, 1, 1, 2, 2], [-3, -3, 4, 4]]


def float_edges() -> List[float]:
    """Floating-point boundary values bugs love: zeros (incl. −0.0), tiny/huge, subnormal-ish, and the
    non-finite specials. (NaN/inf are returned so a transform that mishandles them is exercised.)"""
    return [0.0, -0.0, 1.0, -1.0, 0.5, -0.5, 1e-12, -1e-12, 1e12, -1e12,
            float("inf"), float("-inf"), float("nan")]


def random_floats(rng: random.Random, k: int = 16, scale: float = 1000.0) -> List[float]:
    return [(rng.random() - 0.5) * scale for _ in range(k)]


def float_list_evidence(rng: Optional[random.Random] = None) -> "Evidence":
    """Evidence set for float-list kernels: edge-bearing lists (incl. specials) + random over several sizes."""
    rng = rng or random.Random(0)
    fe = float_edges()
    inputs: List[Any] = [[], [0.0], [-0.0], [float("nan")], [float("inf"), 1.0], list(fe)]
    for s in (1, 2, 5, 16, 50):
        inputs.append(random_floats(rng, s))
    n = len(inputs)
    return Evidence(inputs, 3.0 / n if n else 1.0, n)


def random_lists(rng: random.Random, sizes=(0, 1, 2, 3, 8, 25, 64), lo: int = -50, hi: int = 50) -> List[List[int]]:
    out: List[List[int]] = []
    for s in sizes:
        for _ in range(3):
            out.append([rng.randrange(lo, hi) for _ in range(s)])
    return out


def z3_guided_branch(pred_builder: Callable[[Any], Any]) -> List[int]:
    """Concolic-lite: given a predicate over a symbolic int, solve for one input that SATISFIES it and one that
    NEGATES it, so both branches are covered. Returns the concrete ints Z3 found (skips a side if unsat)."""
    found: List[int] = []
    x = z3.Int("x")
    for want in (pred_builder(x), z3.Not(pred_builder(x))):
        s = z3.Solver()
        s.add(want)
        _V.note_z3_check()
        if s.check() == z3.sat:
            found.append(s.model()[x].as_long())
    return found


# ── the generated evidence set + δ ──────────────────────────────────────────────────────────────────────
@dataclass
class Evidence:
    inputs: List[Any]
    delta: float            # rule of three: 3/n
    n: int


def list_evidence(rng: Optional[random.Random] = None) -> Evidence:
    rng = rng or random.Random(0)
    inputs = edge_lists() + random_lists(rng)
    n = len(inputs)
    return Evidence(inputs, 3.0 / n if n else 1.0, n)


def int_evidence(rng: Optional[random.Random] = None, pred_builder: Optional[Callable] = None) -> Evidence:
    rng = rng or random.Random(0)
    vals = boundary_ints() + [rng.randrange(-1000, 1000) for _ in range(20)]
    if pred_builder is not None:
        vals += z3_guided_branch(pred_builder)              # ensure both branches of a predicate are hit
    n = len(vals)
    return Evidence([(v,) if not isinstance(v, tuple) else v for v in vals], 3.0 / n if n else 1.0, n)


def first_divergence(original: Callable, candidate: Callable, inputs: List[Any],
                     eq: Optional[Callable] = None) -> Optional[Any]:
    """The slow-correct `original` is the gold oracle. Returns the first input where candidate disagrees (or
    raises where the original didn't), else None. `inputs` may be raw args or 1-arg values."""
    from pillar3.metamorphic import _eq as _deep_eq
    eqf = eq or _deep_eq
    for x in inputs:
        args = x if isinstance(x, tuple) else (x,)
        try:
            want = original(*args)
        except Exception:
            continue                                        # original itself errors here — not a fair witness
        try:
            got = candidate(*args)
        except Exception as e:  # noqa: BLE001
            return f"{args!r} → candidate raised {type(e).__name__}: {e}"
        if not eqf(got, want):
            return f"{args!r} → original={want!r} candidate={got!r}"
    return None
