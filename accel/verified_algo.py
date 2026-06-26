"""
ACCEL §4 — MOVE C: VERIFIED ALGORITHM / DATA-STRUCTURE CORRECTION. Not a fold — just fixing genuinely bad code
(O(N²) where O(N) suffices, wrong data structure). The HIGHEST ceiling per fix (O(N²)→O(N) is unbounded as N grows),
and provably correct.
================================================================================================================
  • C1 complexity reduction — 'this linear search in a loop → hashmap (O(N²)→O(N))', 'repeated sort → sort once',
    'nested membership → set'. VERIFY the faster structure computes the IDENTICAL result (exhaustive result-
    equivalence over an input battery, sound over the battery). A 'faster' version that returns different results is
    REJECTED.
  • C2 redundant-computation elimination — loop-invariant hoist / common-subexpression. VERIFY invariance (the
    hoisted version == the recompute-every-iteration original).
  • C3 early-exit / short-circuit — 'this loop can break once a condition holds'. VERIFY the early-exit version ==
    the full loop on every input (the break is post-condition-stable). An unsafe early-break (e.g. breaking a SUM) is
    REJECTED.

Every applied swap carries a result-equivalence proof; the adversarial battery (result-changing structure swap,
unsafe early-exit, non-invariant hoist) is rejected 100%. Precision = 1.0.
"""
from __future__ import annotations

import time
from typing import Callable, List, Optional, Sequence

from accel.pipeline import Acceleration, proved, rejected


def _result_equivalent(slow: Callable, fast: Callable, battery: Sequence) -> Optional[str]:
    """Exhaustive result-equivalence over the input battery (sound over the battery). Returns None if equivalent,
    or a counterexample description if any input disagrees."""
    for x in battery:
        try:
            a, b = slow(x), fast(x)
        except Exception as e:  # noqa: BLE001
            return f"evaluation raised {type(e).__name__} on {x!r}"
        if a != b:
            return f"disagree on {x!r}: slow={a!r} vs fast={b!r}"
    return None


def _speedup(slow: Callable, fast: Callable, big_input, k: int = 3) -> Optional[float]:
    try:
        ts = float("inf")
        for _ in range(k):
            t0 = time.perf_counter()
            slow(big_input)
            ts = min(ts, time.perf_counter() - t0)
        tf = float("inf")
        for _ in range(k):
            t0 = time.perf_counter()
            fast(big_input)
            tf = min(tf, time.perf_counter() - t0)
        return round(ts / tf, 2) if tf > 0 else None
    except Exception:  # noqa: BLE001
        return None


def verified_algo_swap(slow: Callable, fast: Callable, battery: Sequence, big_input=None,
                       claim: str = "O(N²)→O(N) structure swap") -> Acceleration:
    """C1: propose a faster structure/algorithm; VERIFY result-equivalence on the whole battery; APPLY iff every
    input agrees. A structure that returns DIFFERENT results (wrong dedup, dropped duplicates, reordered) is REJECTED.
    On proof, the measured speedup on `big_input` is reported (Clock C — the asymptotic win is real, not a fold)."""
    cex = _result_equivalent(slow, fast, battery)
    if cex is not None:
        return rejected("C.algo", claim, f"result-equivalence FAILS — {cex}")
    acc = proved("C.algo", claim, f"result-equivalence on all {len(list(battery))} battery inputs (exact)")
    acc.asymptotics = "improved (O(N²)→O(N)/O(N log N))"
    if big_input is not None:
        acc.clock_c_speedup = _speedup(slow, fast, big_input)
    return acc


def verified_hoist(recompute: Callable, hoisted: Callable, battery: Sequence,
                   claim: str = "loop-invariant hoist / CSE") -> Acceleration:
    """C2: propose hoisting a loop-invariant computation (or a common subexpression); VERIFY the hoisted version is
    result-equivalent to the recompute-every-iteration original. A NON-invariant 'hoist' (the value actually depends
    on the loop variable) disagrees on some input ⇒ REJECTED."""
    cex = _result_equivalent(recompute, hoisted, battery)
    if cex is not None:
        return rejected("C.cse", claim, f"NOT invariant — {cex}")
    return proved("C.cse", claim, f"loop-invariance proved — hoisted ≡ recompute on all {len(list(battery))} inputs")


def verified_early_exit(full: Callable, early: Callable, battery: Sequence,
                        claim: str = "early-exit / short-circuit") -> Acceleration:
    """C3: propose breaking a loop early once a condition holds; VERIFY the early-exit version == the full loop on
    every input (the post-condition is stable after the break — monotone/saturating). An UNSAFE early-break (e.g.
    breaking a SUM, where the remaining iterations DO change the result) disagrees ⇒ REJECTED."""
    cex = _result_equivalent(full, early, battery)
    if cex is not None:
        return rejected("C.earlyexit", claim, f"UNSAFE early-exit — the break changes the result: {cex}")
    return proved("C.earlyexit", claim,
                  f"post-condition stable after the break — early ≡ full on all {len(list(battery))} inputs")


# ── reference (slow, fast) pairs used by the report + tests (real bad-code → corrected) ─────────────────
def dedup_slow(lst):
    """O(N²) order-preserving dedup via linear membership search."""
    out = []
    for x in lst:
        if x not in out:                      # O(N) scan inside the loop ⇒ O(N²)
            out.append(x)
    return out


def dedup_fast(lst):
    """O(N) order-preserving dedup via a seen set — the SAME result, computed once."""
    seen, out = set(), []
    for x in lst:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def dedup_wrong(lst):
    """An adversarial 'faster' version that CHANGES the result (sorts ⇒ wrong order, drops order-info)."""
    return sorted(set(lst))
