"""
§X PARADIGM 3 — DUAL / COFUNCTION FOLD (elegant via conservation laws).
================================================================================================================
If `f` doesn't fold but a callsite consumes `f`'s output only through a LINEAR functional φ (sum, weighted-sum/dot),
fold the dual `φ∘f` instead. Sorting never folds, but `sum∘sort == sum` (sorting preserves the sum); `sum∘reverse ==
sum`; `sum∘map(+k) == sum + N·k`. We expand `φ∘f` symbolically over a fixed-size array and prove it equals the folded
form.

★ z3 gate (precision 1.0): over N symbolic elements, prove ∀arr. φ(f(arr)) == folded(arr). Used only where proved.
★ Honest boundary: LINEAR functionals only (sum / weighted-sum / dot). Non-linear functionals (max-with-predicate,
count-with-condition) where the conservation is weaker ⇒ DECLINE. NO new certificate kind. Composes with P1's guards
(e.g. dot-with-constant-weights under an is_constant guard). Adversarial: a dual where f does NOT preserve φ is rejected.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass
class DualFold:
    issued: bool
    paradigm: str = "dual"
    mechanism: str = "linear_recurrence"
    functional: str = ""
    detail: str = ""


def _z3_ints(n: int):
    import z3
    return [z3.Int(f"a{i}") for i in range(n)]


def prove_dual(functional: Callable, f: Callable, folded: Callable, n: int) -> bool:
    """Prove ∀arr (n symbolic Ints). functional(f(arr)) == folded(arr). `f` returns the transformed list, `functional`
    reduces a list to a z3 expr, `folded` gives the closed form directly from arr. True ⇒ the dual fold is sound."""
    import z3
    arr = _z3_ints(n)
    s = z3.Solver()
    s.add(functional(f(arr)) != folded(arr))
    return s.check() == z3.unsat


# linear functionals
def sum_fn(lst):
    out = lst[0]
    for v in lst[1:]:
        out = out + v
    return out


def dot_const(weights):
    return lambda lst: sum_fn([w * x for w, x in zip(weights, lst)])


def fold_dual(functional: Callable, f: Callable, folded: Callable, n: int, name: str) -> DualFold:
    if prove_dual(functional, f, folded, n):
        return DualFold(True, functional=name, detail=f"{name}∘f ≡ folded over {n} elements (z3 ∀-proved) — the dual "
                        "folds though f alone does not")
    return DualFold(False, functional=name, detail=f"{name} not preserved by f ⇒ DECLINE (no sound dual)")


def adversarial_battery() -> dict:
    """sum∘reverse == sum (preserved), sum∘map(+k)... ; a dual where f does NOT preserve the functional is rejected."""
    reverse = lambda arr: list(reversed(arr))
    # sum∘reverse == sum (folded = sum of arr) — sorting/reversal preserves the sum
    d_rev = fold_dual(sum_fn, reverse, sum_fn, 4, "sum")
    # dot-with-constant∘reverse: dot is NOT permutation-invariant ⇒ must DECLINE (the honest boundary)
    w = [1, 2, 3, 4]
    d_dot_rev = fold_dual(dot_const(w), reverse, dot_const(w), 4, "dot_const")
    # ★ adversarial: claim sum∘reverse == (sum + 1) — WRONG ⇒ rejected
    d_wrong = fold_dual(sum_fn, reverse, lambda arr: sum_fn(arr) + 1, 4, "sum")
    cases = {
        "sum_preserved_by_reverse_issued": d_rev.issued,
        "dot_not_permutation_invariant_declined": not d_dot_rev.issued,   # honest: dot isn't preserved by reversal
        "wrong_dual_rejected": not d_wrong.issued,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
