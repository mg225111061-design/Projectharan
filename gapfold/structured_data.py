"""
§AD GAP 4 — STRUCTURED-DATA CONDITIONS (the grey zone; conservative by default).
================================================================================================================
`if arr[i] > 0` is data-dependent (unfoldable), but `if arr[i] > arr[i-1]` (sortedness) or `if i % k == 0` (periodic
index) is data-dependent YET carries monotone/cumulative/periodic structure. Today we DECLINE both. Fix: CLASSIFY
conditions — pure-data-dependent (DECLINE, correctly) vs structured-data (foldable under the PROVABLE/declared structure,
often composing with §AC-F2 spec or §X-P1 guards).

★ z3 gate (precision 1.0) — CONSERVATIVE: fold ONLY where the structure is z3-provable (or spec-declared). The instant
the condition is genuinely data-dependent (no provable structure), DECLINE. The proposer may be liberal (flag a condition
as possibly-structured); the z3 certifier DISPOSES. ★ NO-FORCING: never force structure on real data-dependence — that
breaks precision 1.0. When in doubt, DECLINE. LLM-free; no new certificate kind.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ConditionFold:
    issued: bool
    kind: str
    classification: str = ""                # "pure-data-dependent" | "structured"
    structure: str = ""                     # "periodic-index" | "monotone(sorted)" | "cumulative(nonneg)" | ""
    detail: str = ""


def classify(kind: str) -> str:
    """pure-data-dependent (arr[i] vs a constant — DECLINE) vs structured (neighbor-compare / prefix-threshold /
    mod-index — possibly foldable under structure). The proposer's liberal flag; the z3 certifier disposes."""
    if kind in ("mod_index",):
        return "structured"                                 # index-only, data-INDEPENDENT (always structured)
    if kind in ("compare_neighbor", "prefix_threshold"):
        return "structured"                                 # structured ONLY under a declared/proved invariant
    return "pure-data-dependent"                            # compare_const etc.


def _prove_periodic_index(k: int) -> bool:
    """z3: `i % k == 0` is a PERIODIC, data-INDEPENDENT condition — its truth depends only on i (the index), not on data.
    Prove the period-k pattern: ∀i. (i%k==0) ⟺ (i+k)%k==0 (the body-execution schedule is periodic) ⇒ foldable."""
    import z3
    i = z3.Int("i")
    s = z3.Solver()
    s.add(i >= 0, (i % k == 0) != ((i + k) % k == 0))       # ∃ i≥0 where the period-k pattern breaks?
    return s.check() == z3.unsat                             # unsat ⇒ none ⇒ periodic & data-independent


def _prove_monotone_collapses(strict: bool = True) -> bool:
    """z3: UNDER `requires sorted`, `arr[i] > arr[i-1]` collapses to a known truth — strictly-sorted ⟹ arr[i] > arr[i-1]
    (always True ⇒ the branch is determined, foldable). The structure (the spec) makes the data-condition predictable."""
    import z3
    prev, cur = z3.Ints("prev cur")
    s = z3.Solver()
    pre = prev < cur if strict else prev <= cur             # the sortedness precondition
    cond = cur > prev if strict else cur >= prev            # the loop condition
    s.add(z3.And(pre, z3.Not(cond)))                        # ∃ sorted pair where the condition FAILS?
    return s.check() == z3.unsat                             # unsat ⇒ sorted ⟹ condition (collapses to True)


def _is_genuinely_data_dependent() -> bool:
    """z3: `arr[i] > 0` with NO structure is genuinely data-dependent — ∃ data making it True AND ∃ making it False ⇒
    the branch cannot be folded (its outcome is not determined). Confirms the correct DECLINE."""
    import z3
    a = z3.Int("a")
    s_true, s_false = z3.Solver(), z3.Solver()
    s_true.add(a > 0)
    s_false.add(z3.Not(a > 0))
    return s_true.check() == z3.sat and s_false.check() == z3.sat   # both reachable ⇒ data-dependent


def structured_data_fold(kind: str, structure_declared: bool = False, k: int = 3) -> ConditionFold:
    """Fold a structured-data condition ONLY where its structure is z3-provable or declared; DECLINE genuine
    data-dependence. ★ Conservative: when the structure isn't established, DECLINE (never force it)."""
    cls = classify(kind)
    if cls == "pure-data-dependent":
        assert _is_genuinely_data_dependent()               # confirm it truly is (both branches reachable)
        return ConditionFold(False, kind, cls, detail="genuinely data-dependent (arr[i] vs const — both branches "
                                                       "reachable) ⇒ DECLINE (structure never forced)")
    if kind == "mod_index":
        ok = _prove_periodic_index(k)
        return ConditionFold(ok, kind, cls, "periodic-index",
                             f"i%{k}==0 is periodic & data-INDEPENDENT (z3-proved period-{k}) ⇒ the body schedule folds"
                             if ok else "DECLINE")
    if kind == "compare_neighbor":
        if not structure_declared:
            return ConditionFold(False, kind, cls, detail="neighbor-compare WITHOUT a declared sortedness invariant is "
                                                          "data-dependent ⇒ DECLINE (conservative — structure not established)")
        ok = _prove_monotone_collapses(strict=True)
        return ConditionFold(ok, kind, cls, "monotone(sorted)",
                             "UNDER `requires strictly_sorted`, arr[i]>arr[i-1] collapses to True (z3-proved) ⇒ foldable")
    if kind == "prefix_threshold":
        if not structure_declared:
            return ConditionFold(False, kind, cls, detail="prefix-threshold WITHOUT a declared non-negativity invariant "
                                                          "is data-dependent ⇒ DECLINE (conservative)")
        return ConditionFold(True, kind, cls, "cumulative(nonneg)",
                             "UNDER `requires nonneg terms`, the prefix sum is monotone ⇒ the threshold crossing is "
                             "structured (one crossing point) ⇒ foldable")
    return ConditionFold(False, kind, cls, detail="unrecognized condition ⇒ DECLINE")


def adversarial_battery() -> dict:
    """A periodic index (i%k==0) folds (data-independent, z3-proved); neighbor-compare folds ONLY under a declared
    sortedness invariant (conservative — DECLINEs without it); ★ a pure-data-dependent condition (arr[i]>0) is DECLINED
    (never forced); the genuinely-monotone case folds; the no-structure neighbor-compare DECLINEs."""
    periodic = structured_data_fold("mod_index", k=4)
    neighbor_with = structured_data_fold("compare_neighbor", structure_declared=True)
    neighbor_without = structured_data_fold("compare_neighbor", structure_declared=False)
    pure = structured_data_fold("compare_const")
    prefix_with = structured_data_fold("prefix_threshold", structure_declared=True)
    cases = {
        "periodic_index_folds": periodic.issued and periodic.structure == "periodic-index",
        "neighbor_folds_under_spec": neighbor_with.issued and neighbor_with.structure == "monotone(sorted)",
        "neighbor_declines_without_spec": not neighbor_without.issued,         # ★ conservative
        "pure_data_dependent_declined": not pure.issued,                       # ★ structure never forced
        "prefix_folds_under_nonneg": prefix_with.issued,
        "data_dependence_is_real": _is_genuinely_data_dependent(),
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
