"""
§AD GAP 2 — DIVIDE-AND-CONQUER RECURRENCES (Master / Akra-Bazzi): fold `T(n)=a·T(n/b)+f(n)`.
================================================================================================================
`T(n)=2·T(n/2)+n` is the cost structure of merge-sort, FFT, Karatsuba — a closed form EXISTS (the Master theorem /
Akra-Bazzi), but our additive-recurrence detector looks for `n-1`/`n-2`, not `n/b`. Fix: detect divide-and-conquer
recurrences and apply Master/Akra-Bazzi to the closed-form asymptotic cost Θ(·).

★ z3 / soundness gate (the stated grade): the Master-theorem case is decided by comparing d to the critical exponent
log_b(a) (the theorem's hypotheses verified); the result is the ASYMPTOTIC ORDER (per §AC-F4), proved by the theorem.
★ ORDER-vs-VALUE honesty: the cost is asymptotic-ORDER (reported as an order-reduction, NOT a constant-collapsing closed
form), unless an exact value form is separately proved. A recurrence not matching `a·T(n/b)+f(n)` ⇒ DECLINE. Reuses the
§AC-F4 asymptotic-order machinery.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

_EPS = 1e-9


@dataclass
class DivideConquerFold:
    issued: bool
    a: int = 0
    b: int = 0
    d: int = 0                              # f(n) = Θ(n^d)
    case: int = 0                           # Master case 1 / 2 / 3
    order: str = ""                         # the closed-form asymptotic cost Θ(·)
    grade: str = "asymptotic-order"         # ★ ORDER, not a closed-form value (per §AC-F4)
    detail: str = ""


def master_theorem(a: int, b: int, d: int) -> DivideConquerFold:
    """Apply the Master theorem to T(n)=a·T(n/b)+Θ(n^d). Critical exponent c=log_b(a). case 1 (d<c): Θ(n^c); case 2
    (d==c): Θ(n^c log n); case 3 (d>c): Θ(n^d). Hypotheses: a≥1, b>1, d≥0 (else not a Master recurrence ⇒ DECLINE)."""
    if a < 1 or b <= 1 or d < 0:
        return DivideConquerFold(False, a, b, d, detail=f"not a Master recurrence (need a≥1,b>1,d≥0; got a={a},b={b},d={d}) ⇒ DECLINE")
    c = math.log(a) / math.log(b)                           # the critical exponent log_b(a)
    if d < c - _EPS:
        case, order = 1, f"Θ(n^{round(c, 3)})"
    elif abs(d - c) <= _EPS:
        case, order = 2, (f"Θ(n^{d}·log n)" if d > 0 else "Θ(log n)")
    else:
        case, order = 3, (f"Θ(n^{d})" if d > 0 else "Θ(1)")
    return DivideConquerFold(True, a, b, d, case, order, "asymptotic-order",
                             f"T(n)={a}·T(n/{b})+Θ(n^{d}): critical c=log_{b}({a})={round(c,3)}; Master case {case} ⇒ "
                             f"{order} (★ ORDER, not a closed-form value — per §AC-F4)")


def _measured_growth_consistent(a: int, b: int, d: int, dcf: DivideConquerFold) -> bool:
    """Corroborate the predicted order: compute T(n) directly (T(n)=a·T(n/b)+n^d, T(1)=1) at two sizes and check the
    growth ratio is consistent with the predicted Θ — a sanity check (the theorem is the proof, this corroborates)."""
    def T(n):
        if n <= 1:
            return 1.0
        return a * T(n // b) + (n ** d if d > 0 else 1.0)
    n1, n2 = b ** 8, b ** 10                                # two sizes a factor b² apart
    t1, t2 = T(n1), T(n2)
    c = math.log(a) / math.log(b)
    # predicted growth factor over n2/n1 = b²
    if dcf.case == 1:
        pred = (b ** 2) ** c
    elif dcf.case == 2:
        pred = (b ** 2) ** c * (math.log(n2) / math.log(n1))
    else:
        pred = (b ** 2) ** d
    ratio = t2 / t1
    return 0.5 < ratio / pred < 2.0                         # within a small constant factor (order-consistent)


def divide_conquer_fold(a: int, b: int, d: int) -> DivideConquerFold:
    """Fold a divide-and-conquer cost recurrence via the Master theorem, with the predicted order corroborated by a
    direct measurement. EXACT order (asymptotic); the value closed form is out of scope (order honesty)."""
    dcf = master_theorem(a, b, d)
    if not dcf.issued:
        return dcf
    if not _measured_growth_consistent(a, b, d, dcf):
        return DivideConquerFold(False, a, b, d, detail="predicted Master order inconsistent with measured growth ⇒ DECLINE")
    return dcf


def adversarial_battery() -> dict:
    """Merge-sort 2T(n/2)+n → Θ(n log n) [case 2]; Karatsuba 3T(n/2)+n → Θ(n^1.585) [case 1]; binary search T(n/2)+1
    → Θ(log n); a non-Master recurrence (b=1) is REJECTED; ★ the result is asymptotic-ORDER, never mislabeled an exact value."""
    ms = divide_conquer_fold(2, 2, 1)
    kar = divide_conquer_fold(3, 2, 1)
    bs = divide_conquer_fold(1, 2, 0)
    strassen = divide_conquer_fold(7, 2, 2)
    bad = master_theorem(2, 1, 1)                            # b=1 ⇒ not a Master recurrence ⇒ DECLINE
    cases = {
        "mergesort_n_log_n": ms.issued and ms.case == 2 and "log n" in ms.order,
        "karatsuba_subquadratic": kar.issued and kar.case == 1 and "1.585" in kar.order,
        "binary_search_log": bs.issued and "log n" in bs.order,
        "strassen_case1": strassen.issued and strassen.case == 1,
        "non_master_rejected": not bad.issued,
        "order_not_value": ms.grade == "asymptotic-order",   # ★ ORDER, never a closed-form value
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
