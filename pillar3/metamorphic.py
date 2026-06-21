"""
Pillar 3 · PHASE M — metamorphic relations + cross-checking (zero human audit, catches what differential misses).
=================================================================================================================
Differential testing only checks "same output as the slow original on the inputs we happened to record." A wrong
fix can slip through if the recorded inputs don't exercise the bug. Two automated nets close that gap:

  • METAMORPHIC RELATIONS — properties the transform must preserve regardless of input (a sort is permutation-
    invariant, idempotent, output-sorted, multiset-preserving; a sum is order-invariant up to FP tolerance; a
    memoized pure function equals the unmemoized one). A violation ⇒ DECLINE, even if differential passed.
  • CROSS-CHECKING — compute the result two independent ways; disagreement ⇒ DECLINE.

The whole gate is automated (no human in the loop). It only ever turns a borderline pass into a DECLINE — it
never manufactures a win (Constitution Rule 6: honest UNVERIFIED/DECLINE over a fake pass).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Tuple


@dataclass
class MRResult:
    name: str
    held: bool
    witness: Optional[str] = None


def _eq(a: Any, b: Any, tol: float = 1e-9) -> bool:
    if isinstance(a, float) or isinstance(b, float):
        return abs(float(a) - float(b)) <= tol * (1 + abs(float(b)))
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_eq(x, y, tol) for x, y in zip(a, b))
    return a == b


def _is_sorted(xs) -> bool:
    return all(xs[i] <= xs[i + 1] for i in range(len(xs) - 1))


# ── relation builders (each takes the candidate fn + one sample input, returns held? ) ─────────────────
def rel_idempotent(name: str = "idempotent") -> Tuple[str, Callable]:
    return name, lambda f, x: _eq(f(list(f(x))), f(x))


def rel_permutation_invariant(rng: random.Random) -> Tuple[str, Callable]:
    def holds(f, x):
        y = list(x)
        rng.shuffle(y)
        return _eq(f(y), f(x))
    return "permutation_invariant", holds


def rel_output_sorted() -> Tuple[str, Callable]:
    return "output_sorted", lambda f, x: _is_sorted(f(x))


def rel_multiset_preserved() -> Tuple[str, Callable]:
    return "multiset_preserved", lambda f, x: sorted(f(x)) == sorted(x)


def rel_sum_order_invariant(rng: random.Random, tol: float = 1e-9) -> Tuple[str, Callable]:
    def holds(f, x):
        y = list(x)
        rng.shuffle(y)
        return _eq(f(x), f(y), tol)
    return "sum_order_invariant", holds


def rel_equals_reference(ref: Callable, name: str = "equals_reference") -> Tuple[str, Callable]:
    return name, lambda f, x: _eq(f(x), ref(x))


# ── the gate ───────────────────────────────────────────────────────────────────────────────────────────
def check_relations(candidate: Callable, relations: List[Tuple[str, Callable]],
                    gen: Callable[[], Any], k: int = 12) -> List[MRResult]:
    """Run each relation over k generated inputs; the first failing input is the witness."""
    out: List[MRResult] = []
    for name, holds in relations:
        bad = None
        for _ in range(k):
            x = gen()
            try:
                if not holds(candidate, x):
                    bad = x
                    break
            except Exception as e:  # noqa: BLE001 — a relation that errors is a violation, not a pass
                bad = f"raised {type(e).__name__}: {e}"
                break
        out.append(MRResult(name, bad is None, None if bad is None else f"violated on {bad!r}"))
    return out


def cross_check(fn_a: Callable, fn_b: Callable, gen: Callable[[], Any], k: int = 12,
                eq: Optional[Callable] = None) -> Tuple[bool, Optional[str]]:
    """Two independent implementations must agree on every generated input; first disagreement is the witness."""
    eqf = eq or _eq
    for _ in range(k):
        x = gen()
        if not eqf(fn_a(x), fn_b(x)):
            return False, f"cross-check disagreement on {x!r}"
    return True, None


def metamorphic_gate(candidate: Callable, relations: List[Tuple[str, Callable]], gen: Callable[[], Any],
                     *, cross: Optional[Callable] = None, k: int = 12) -> Tuple[bool, str]:
    """Returns (ok, detail). ok=False ⇒ the caller DECLINEs (the fix violated an invariant or a cross-check).
    This gate can only DOWNGRADE a borderline pass to DECLINE; it never produces a win."""
    results = check_relations(candidate, relations, gen, k)
    violated = [r for r in results if not r.held]
    if violated:
        v = violated[0]
        return False, f"metamorphic relation '{v.name}' {v.witness} ⇒ DECLINE"
    if cross is not None:
        ok, w = cross_check(candidate, cross, gen, k)
        if not ok:
            return False, f"{w} ⇒ DECLINE"
    held = ", ".join(r.name for r in results)
    return True, f"all {len(results)} metamorphic relations held ({held}){' + cross-check agreed' if cross else ''}"


# ── reference relation packs for common transform families ─────────────────────────────────────────────
def sort_relations(rng: random.Random) -> List[Tuple[str, Callable]]:
    return [rel_output_sorted(), rel_idempotent(), rel_permutation_invariant(rng), rel_multiset_preserved()]


def sum_relations(rng: random.Random, tol: float = 1e-9) -> List[Tuple[str, Callable]]:
    return [rel_sum_order_invariant(rng, tol)]
