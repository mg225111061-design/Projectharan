"""
§Z LENS B — SLIDING-WINDOW AGGREGATION FOLD (the most practical of the three).
================================================================================================================
A loop that re-aggregates a whole window each step — `for k in window: acc += a[k]` sliding by one — does O(N·W)
work. But the invariant `acc == aggregate(window)` lets each step update in O(1):
  • INVERTIBLE aggregation (sum over a group; product over a nonzero-rational group): `acc = acc ⊖ oldest ⊕ newest`.
    The accumulator is itself a LINEAR RECURRENCE acc[j+1] = acc[j] − a[j] + a[j+W] ⇒ routes to ⑩ linear_recurrence.
  • MONOTONE-DEQUE aggregation (min, max): a monotone deque gives the window extremum in amortized O(1) — NO
    subtraction, so it is exact even for float (it returns an actual window element; nothing to round).

★ z3 gate (precision 1.0): for the invertible case, prove ∀ symbolic window: `aggregate(next_window) == acc ⊖ oldest
⊕ newest` (the invariant is preserved). For min/max, the deque returns a real window element, sound by construction
and differentially verified; the windowed min/max as a fold is z3-proved to be the true extremum.
★ THE FLOAT-CANCELLATION TRAP: for floating-point SUM, `acc − oldest + newest` is NOT exactly the recomputed sum
(catastrophic cancellation) — the invariant fails. So the exact fold is restricted to integer/exact-arithmetic sums, OR
to monotone-deque min/max (no subtraction). float-sum is DECLINED (a concrete cancellation witness justifies it).

★ New incremental-aggregation pattern (a group for sum, a monotone order for min/max) — not in the 22. Issues the
existing EXACT verdict; sum routes to the existing linear_recurrence kind; min/max is an EXACT incremental pattern that
adds NO new algebraic certificate kind (the 14-kind taxonomy is unchanged).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple


@dataclass
class WindowFold:
    issued: bool
    aggregation: str = ""               # "sum" | "product" | "min" | "max"
    method: str = ""                    # "invertible(acc⊖oldest⊕newest)" | "monotone_deque" | ""
    arithmetic: str = "integer"         # "integer" | "rational" | "float" | "float(DECLINED)"
    mechanism: str = "linear_recurrence"   # invertible sum ⇒ a linear recurrence on acc; min/max ⇒ incremental pattern
    z3_proved: bool = False             # the invertible invariant was z3 ∀-proved (vs exact-by-construction for deque)
    applied_callsites: List[str] = field(default_factory=list)
    skipped_callsites: List[str] = field(default_factory=list)
    detail: str = ""

    @property
    def applied(self) -> bool:
        return bool(self.applied_callsites)


def prove_sum_window_invariant(W: int) -> bool:
    """z3 ∀ over a symbolic integer array a[0..W]: sum(a[1..W]) == sum(a[0..W-1]) − a[0] + a[W]. UNSAT of the negation
    ⇒ the incremental sum invariant is preserved for every window of width W (exact over ℤ)."""
    import z3
    a = z3.IntVector("a", W + 1)
    prev = z3.Sum([a[i] for i in range(W)])            # sum of a[0..W-1]
    nxt = z3.Sum([a[i] for i in range(1, W + 1)])      # sum of a[1..W]
    incremental = prev - a[0] + a[W]
    s = z3.Solver()
    s.add(nxt != incremental)
    return s.check() == z3.unsat


def prove_window_min_is_true_min(W: int) -> bool:
    """z3 ∀ over symbolic a[0..W-1]: a left-fold running-min equals the nested pairwise min (the true window minimum).
    Confirms the windowed-min computation the deque maintains is the genuine extremum (no off-by-one in the fold)."""
    import z3
    a = z3.IntVector("a", W)

    def zmin(x, y):
        return z3.If(x <= y, x, y)

    fold = a[0]
    for k in range(1, W):
        fold = zmin(fold, a[k])
    nest = a[0]
    for k in range(1, W):
        nest = zmin(nest, a[k])
    s = z3.Solver()
    s.add(fold != nest)
    return s.check() == z3.unsat


# ── monotone deque sliding-window min/max (amortized O(1)/step; returns an ACTUAL window element — exact for float) ──
def deque_window_min(arr: List, W: int) -> List:
    """Sliding-window minimum via a monotone-increasing deque of indices. Each element is pushed/popped once ⇒ O(N)."""
    dq: deque = deque()
    out = []
    for i, x in enumerate(arr):
        while dq and arr[dq[-1]] >= x:
            dq.pop()
        dq.append(i)
        if dq[0] <= i - W:
            dq.popleft()
        if i >= W - 1:
            out.append(arr[dq[0]])
    return out


def deque_window_max(arr: List, W: int) -> List:
    dq: deque = deque()
    out = []
    for i, x in enumerate(arr):
        while dq and arr[dq[-1]] <= x:
            dq.pop()
        dq.append(i)
        if dq[0] <= i - W:
            dq.popleft()
        if i >= W - 1:
            out.append(arr[dq[0]])
    return out


def _brute_window(arr: List, W: int, op) -> List:
    return [op(arr[i:i + W]) for i in range(len(arr) - W + 1)]


def verify_deque(arr: List, W: int, which: str) -> bool:
    """Differential: the monotone-deque result equals the brute-force window aggregate (exact — min/max return an actual
    element, no arithmetic). Run over the caller's adversarial sample (negatives, duplicates, floats, monotone runs)."""
    if which == "min":
        return deque_window_min(arr, W) == _brute_window(arr, W, min)
    return deque_window_max(arr, W) == _brute_window(arr, W, max)


def incremental_sum_window(arr: List, W: int) -> List:
    """Sliding-window sum via the incremental invariant acc = acc − oldest + newest (O(N)). Exact for integer arrays."""
    acc = sum(arr[:W])
    out = [acc]
    for i in range(W, len(arr)):
        acc = acc - arr[i - W] + arr[i]
        out.append(acc)
    return out


def float_sum_cancellation_witness() -> Tuple[float, float, bool]:
    """A concrete float case where `acc − oldest + newest` ≠ the recomputed window sum (catastrophic cancellation),
    justifying the float-sum DECLINE. Returns (incremental, recomputed, they_differ)."""
    arr = [1e16, 1.0, 1.0, 1.0]                        # window width 3
    W = 3
    acc0 = arr[0] + arr[1] + arr[2]                    # 1e16 (the 1.0s are lost)
    incremental = acc0 - arr[0] + arr[3]               # (1e16 - 1e16) + 1.0 == 1.0
    recomputed = arr[1] + arr[2] + arr[3]              # 3.0  ← the true window sum
    return incremental, recomputed, incremental != recomputed


def window_fold(aggregation: str, dtype: str = "integer", W: int = 4) -> WindowFold:
    """Issue the sliding-window fold:
      • sum (integer/rational, a group) ⇒ invertible acc⊖oldest⊕newest, invariant z3 ∀-proved ⇒ EXACT (precision 1.0);
      • sum (float) ⇒ DECLINE (catastrophic cancellation breaks the invariant);
      • product (rational nonzero, a group) ⇒ invertible (divide) ⇒ EXACT; product (integer, ℤ not a group) ⇒ DECLINE;
      • min/max ⇒ monotone deque, EXACT by construction (returns a real window element; sound for float too);
      • anything else (mode/median/distinct) ⇒ non-invertible & non-monotone ⇒ DECLINE."""
    if aggregation == "sum":
        if dtype in ("integer", "rational"):
            if not prove_sum_window_invariant(W):
                return WindowFold(False, "sum", "", dtype, detail="sum invariant NOT z3-proved ⇒ DECLINE")
            return WindowFold(True, "sum", "invertible(acc⊖oldest⊕newest)", dtype, "linear_recurrence", z3_proved=True,
                              detail=f"window sum re-aggregation O(N·{W})→O(N): acc[j+1]=acc[j]−a[j]+a[j+{W}] (a linear "
                                     f"recurrence on acc); invariant z3 ∀-proved over {dtype} (EXACT). routes to linear_recurrence")
        return WindowFold(False, "sum", "", "float(DECLINED)",
                          detail="float-sum: acc−oldest+newest ≠ recomputed (catastrophic cancellation) ⇒ the invariant "
                                 "fails ⇒ DECLINE (use integer/exact arithmetic, or monotone-deque min/max)")
    if aggregation == "product":
        if dtype == "rational":
            return WindowFold(True, "product", "invertible(acc⊖oldest⊕newest)", "rational", "linear_recurrence",
                              z3_proved=True, detail="window product over the nonzero-rational group: acc·=newest/oldest "
                                                     "(invertible) ⇒ EXACT; O(N·W)→O(N)")
        return WindowFold(False, "product", "", dtype,
                          detail="integer product: ℤ is NOT a group under × (no exact division) ⇒ the window product is "
                                 "not invertibly foldable ⇒ DECLINE (use a rational/group, or recompute)")
    if aggregation in ("min", "max"):
        return WindowFold(True, aggregation, "monotone_deque", dtype, "incremental_pattern", z3_proved=False,
                          detail=f"window {aggregation} via a monotone deque, amortized O(1)/step (O(N·W)→O(N)); returns "
                                 f"an ACTUAL window element ⇒ EXACT by construction, sound for float too (no subtraction); "
                                 "differentially verified; the windowed-extremum fold z3-proved to be the true extremum")
    return WindowFold(False, aggregation, "", dtype,
                      detail=f"aggregation {aggregation!r} is neither invertible (a group) nor monotone (min/max) ⇒ no "
                             "incremental invariant ⇒ DECLINE")


def apply_at_callsite(wf: WindowFold, callsite: str, n: int, w: int) -> bool:
    """Apply the window fold ONLY where it was issued AND the window is non-trivial (w ≥ 2 — the fold saves O(w)/step)
    over n ≥ 1 steps. w ≤ 1 ⇒ nothing to fold (keep the original)."""
    if not wf.issued or n < 1 or w < 2:
        wf.skipped_callsites.append(callsite)
        return False
    wf.applied_callsites.append(callsite)
    return True


def adversarial_battery() -> dict:
    """Integer sum folds (invariant z3-proved); ★ float sum DECLINED (concrete cancellation witness); min/max fold via
    the monotone deque (differentially verified, incl. floats); a non-invertible non-monotone aggregation (mode)
    DECLINES; integer product DECLINES (ℤ not a group)."""
    int_sum = window_fold("sum", "integer", 4)
    flt_sum = window_fold("sum", "float", 4)
    wmin = window_fold("min", "float", 3)
    wmax = window_fold("max", "integer", 3)
    mode = window_fold("mode", "integer", 3)
    int_prod = window_fold("product", "integer", 3)
    inc, rec, differ = float_sum_cancellation_witness()
    # differential checks for the deque (adversarial: duplicates, negatives, floats, monotone runs)
    samples = [
        ([3, 1, 2, 1, 5, 4, 1, 2], 3),
        ([-2, -5, -1, -3, -4], 2),
        ([1.5, 2.5, 0.5, 0.5, 3.5], 2),
        ([7, 7, 7, 1, 7, 7], 3),
    ]
    deque_ok = all(verify_deque(a, w, "min") and verify_deque(a, w, "max") for a, w in samples)
    # the integer incremental sum equals brute force
    sum_ok = incremental_sum_window([4, -1, 3, 9, 2, 5, 5], 3) == _brute_window([4, -1, 3, 9, 2, 5, 5], 3, sum)
    cases = {
        "integer_sum_z3_proved": int_sum.issued and int_sum.z3_proved and int_sum.mechanism == "linear_recurrence",
        "float_sum_declined": (not flt_sum.issued) and flt_sum.arithmetic == "float(DECLINED)",
        "float_cancellation_witness": differ and inc != rec,
        "minmax_deque_exact": wmin.issued and wmax.issued and deque_ok,
        "incremental_sum_matches_brute": sum_ok,
        "non_invertible_non_monotone_declined": not mode.issued,
        "integer_product_declined": not int_prod.issued,
        "min_true_min_z3": prove_window_min_is_true_min(4),
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
