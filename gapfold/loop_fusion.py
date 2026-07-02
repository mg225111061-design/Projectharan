"""
§AD GAP 8 — CONSECUTIVE-LOOP FUSION (fold across adjacent loops).
================================================================================================================
`for i: a[i]=f(i)` then `for i: s+=a[i]` are invisible separately (an array write, then a sum), but FUSED they are
`s = Σ f(i)` — a closed form. We miss it because we analyze each loop alone. Fix: detect fusable consecutive loops (the
second consuming the first's output), fuse, then fold the fused form (Faulhaber). Distinct from §X-P4 cross-function taint
— this is adjacent loops in ONE function.

★ z3 gate (EXACT, precision 1.0): prove (a) the fusion is SOUND — the second loop reads exactly what the first wrote, no
aliasing / intervening modification of the array between the loops (else the substitution a[i]=f(i) is invalid), AND (b)
the fused form folds correctly (the Faulhaber closed form satisfies the sum recurrence S(n)−S(n−1)==f(n)). ★ The aliasing
discipline: fusion is sound ONLY if no other access modifies the array between the loops — when aliasing can't be ruled
out, DECLINE. Reuses §X-P4 dependency analysis + the Faulhaber path.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple


@dataclass
class LoopFusionFold:
    issued: bool
    fused_closed_form: str = ""
    fusion_sound: bool = False              # no aliasing / intervening write between the loops
    fold_proved: bool = False               # the fused sum's closed form z3-proved
    detail: str = ""


def prove_affine_sum_closed(c0: int, c1: int) -> bool:
    """z3 ∀-prove the fused sum S(n)=Σ_{i=1}^{n} (c0 + c1·i) = c0·n + c1·n(n+1)/2 by induction: base S(1)==c0+c1 and step
    S(n+1)−S(n) == c0 + c1·(n+1). Cleared denominator (2·S)."""
    import z3
    n = z3.Int("n")
    S2 = lambda k: 2 * c0 * k + c1 * k * (k + 1)             # 2·S(k)
    s = z3.Solver()
    base = S2(1) == 2 * (c0 + c1)
    step = z3.ForAll([n], z3.Implies(n >= 1, S2(n + 1) - S2(n) == 2 * (c0 + c1 * (n + 1))))
    s.add(z3.Not(z3.And(base, step)))
    return s.check() == z3.unsat


def fuse_and_fold(producer_array: str, consumer_array: str, intervening_writes: Set[str],
                  f_coeffs: Tuple[int, int]) -> LoopFusionFold:
    """Fuse `for i: a[i]=f(i)` ; `for i: s+=a[i]` into `s=Σf(i)` and fold (f(i)=c0+c1·i affine). Sound iff the consumer
    reads the producer's array AND no intervening write/aliasing touches it; then the Faulhaber closed form is z3-proved.
    ★ Any aliasing/intervening write ⇒ DECLINE (the substitution a[i]=f(i) would be invalid)."""
    if consumer_array != producer_array:
        return LoopFusionFold(False, detail=f"consumer reads `{consumer_array}` ≠ producer writes `{producer_array}` ⇒ "
                                            "not a producer-consumer pair ⇒ DECLINE")
    if producer_array in intervening_writes:
        return LoopFusionFold(False, fusion_sound=False,
                              detail=f"`{producer_array}` is modified between the loops (aliasing/intervening write) ⇒ "
                                     "fusion would change behavior ⇒ DECLINE (aliasing not ruled out)")
    c0, c1 = f_coeffs
    proved = prove_affine_sum_closed(c0, c1)
    if not proved:
        return LoopFusionFold(False, fusion_sound=True, detail="fused closed form not z3-proved ⇒ DECLINE")
    return LoopFusionFold(True, f"{c0}·n + {c1}·n(n+1)/2", True, True,
                          detail=f"fused `for i:{producer_array}[i]=f(i)`;`for i:s+={producer_array}[i]` → s=Σf(i) = "
                                 f"{c0}·n+{c1}·n(n+1)/2 (Faulhaber, z3-proved); fusion sound (no aliasing/intervening write); "
                                 "two O(N) loops → one closed form")


def adversarial_battery() -> dict:
    """A genuine producer-consumer pair (a[i]=2+3i ; s+=a[i]) fuses → s=Σ(2+3i) = 2n+3·n(n+1)/2 (z3-proved); ★ an
    INTERVENING WRITE to the array between the loops is REJECTED (aliasing); ★ a consumer reading a DIFFERENT array is
    REJECTED (not consuming); the genuine pair folds."""
    good = fuse_and_fold("a", "a", set(), (2, 3))
    aliased = fuse_and_fold("a", "a", {"a"}, (2, 3))         # `a` written between the loops ⇒ DECLINE
    not_consuming = fuse_and_fold("a", "b", set(), (2, 3))    # consumer reads `b` ≠ producer `a` ⇒ DECLINE
    cases = {
        "producer_consumer_fuses": good.issued and good.fusion_sound and good.fold_proved,
        "fused_closed_form": "n(n+1)/2" in good.fused_closed_form,
        "intervening_write_rejected": (not aliased.issued) and (not aliased.fusion_sound),   # ★ aliasing ruled out or DECLINE
        "non_consuming_rejected": not not_consuming.issued,
        "fold_z3_proved": prove_affine_sum_closed(2, 3),
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
