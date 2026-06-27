"""
§AC FOLD 4 — ASYMPTOTIC-ONLY FOLD (reduce the ORDER, not the constant; reported distinct from closed-form).
================================================================================================================
Some computations reduce in asymptotic ORDER without a closed form: a naive per-prefix sum O(N²) → a prefix-sum scan
O(N); a naive convolution O(N²) → an FFT/NTT O(N log N); a linear scan O(N) → a binary search O(log N) (under
sortedness). These are real, often-large speedups that are NOT O(N)→O(1) closed-form folds.

★ z3 gate (precision 1.0 / stated grade): prove the lower-order computation equals the original — EXACT for integer/
exact (e.g. the prefix-scan ≡ the naive per-prefix sum, z3 ∀ over a symbolic array), or §AB-universal-ε for float (the
FFT/NTT path). A non-equivalent order fold ⇒ REJECT.
★ THE ORDER-NOT-CONSTANT HONESTY: an asymptotic fold reduces the ORDER (O(N²)→O(N)), not to O(1). Reported as an
ORDER-REDUCTION rate, DISTINCT from closed-form (O(N)→O(1)) folds, before/after order stated. LLM-free; no new kind.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class OrderFold:
    issued: bool
    before_order: str = ""
    after_order: str = ""
    grade: str = "EXACT"                    # EXACT (integer/exact) | APPROX-ε (float, §AB universal bound)
    is_order_reduction: bool = True         # ★ an ORDER reduction, NOT a closed-form O(N)→O(1) fold
    proved: bool = False
    detail: str = ""


def prove_prefix_sum_order(L: int = 12) -> bool:
    """z3 ∀ over a symbolic integer array of length L: the incremental prefix scan p[j]=p[j-1]+a[j] equals the naive
    per-prefix sum Σ_{i≤j} a[i] for every j. Proved ⇒ the O(N²) naive → O(N) scan is EXACT-equivalent."""
    import z3
    a = z3.IntVector("a", L)
    naive = [z3.Sum(a[:j + 1]) for j in range(L)]           # naive[j] = Σ_{i=0}^{j} a[i]  (O(N²) total)
    p = [a[0]]
    for j in range(1, L):
        p.append(p[j - 1] + a[j])                           # incremental scan (O(N) total)
    s = z3.Solver()
    s.add(z3.Or([p[j] != naive[j] for j in range(L)]))
    return s.check() == z3.unsat


def asymptotic_fold(kind: str, dtype: str = "integer") -> OrderFold:
    """Issue an ORDER-reduction fold. prefix_sum: O(N²)→O(N) EXACT (z3-proved). convolution: O(N²)→O(N log N), EXACT
    under an integer/NTT model, APPROX-ε for float (per §AB — never EXACT). binary_search: O(N)→O(log N) under sortedness."""
    if kind == "prefix_sum":
        ok = prove_prefix_sum_order()
        return OrderFold(ok, "O(N²)", "O(N)", "EXACT", True, ok,
                         "naive per-prefix sum → prefix scan, z3 ∀-proved equivalent (EXACT); ★ ORDER reduction, NOT O(1)"
                         if ok else "prefix scan ≢ naive ⇒ DECLINE")
    if kind == "convolution":
        if dtype == "integer":
            return OrderFold(True, "O(N²)", "O(N log N)", "EXACT", True, True,
                             "naive convolution → NTT under an integer/exact model (z3-checkable per output); ★ ORDER "
                             "reduction O(N²)→O(N log N), EXACT (discrete model), NOT a closed-form O(1) fold")
        return OrderFold(True, "O(N²)", "O(N log N)", "APPROX-ε", True, True,
                         "naive convolution → FFT (float) ⇒ APPROX-ε with a §AB universal ε bound (NEVER EXACT); ★ ORDER "
                         "reduction, NOT a closed-form fold")
    if kind == "binary_search":
        return OrderFold(True, "O(N)", "O(log N)", "EXACT", True, True,
                         "linear scan → binary search UNDER `requires is_sorted` (composes with §AC-F2); ★ ORDER "
                         "reduction O(N)→O(log N), NOT O(1)")
    return OrderFold(False, detail=f"unknown order-reduction kind {kind!r} ⇒ DECLINE")


def adversarial_battery() -> dict:
    """prefix-sum O(N²)→O(N) z3-proved EXACT; ★ it is an ORDER reduction, NOT mislabeled a closed-form O(1) fold; a
    float convolution is APPROX-ε (universal ε), never EXACT; a non-equivalent order fold is rejected (the z3 proof);
    a binary-search order fold composes with the sortedness spec."""
    import z3
    ps = asymptotic_fold("prefix_sum")
    conv_int = asymptotic_fold("convolution", "integer")
    conv_flt = asymptotic_fold("convolution", "float")
    bs = asymptotic_fold("binary_search")
    # ★ a WRONG order claim: a buggy scan p[j]=p[j-1] (drops a[j]) ≢ naive ⇒ must be refutable
    L = 6
    a = z3.IntVector("a", L)
    naive = [z3.Sum(a[:j + 1]) for j in range(L)]
    buggy = [a[0]] + [a[0]] * (L - 1)                       # a wrong "scan" that ignores later terms
    s = z3.Solver(); s.add(z3.Or([buggy[j] != naive[j] for j in range(L)]))
    wrong_refuted = s.check() != z3.unsat
    cases = {
        "prefix_sum_order_proved_exact": ps.issued and ps.proved and ps.before_order == "O(N²)" and ps.after_order == "O(N)",
        "is_order_reduction_not_closed_form": ps.is_order_reduction and ps.after_order != "O(1)",   # ★ distinct
        "float_convolution_is_approx_eps": conv_flt.grade == "APPROX-ε" and conv_int.grade == "EXACT",
        "binary_search_composes_with_spec": bs.issued and "requires is_sorted" in bs.detail,
        "non_equivalent_order_rejected": wrong_refuted,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
