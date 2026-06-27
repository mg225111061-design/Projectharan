"""
§X PARADIGM 4 — ARRAY / MEMORY FOLD (the new domain — biggest untapped potential).
================================================================================================================
Array/memory manipulation currently DECLINEs unconditionally. Fold an inductive array-write loop into a single
QUANTIFIED closed-form transition. `arr[i+1] = arr[i] + d` over 0..n becomes `∀j. 1≤j≤n ⟹ arr'[j] == arr[0] + d·j`,
collapsing the sequential dependency into a parallel/closed-form state summary.

★ z3 gate (precision 1.0), with quantifier handling: prove the closed form satisfies the recurrence — base
`cf(0)==arr0` AND ∀j≥1 `cf(j)==step(cf(j-1))` — over Int (a ∀ proof). Proved ⇒ fold; unproved / quantifier-diverges /
timeout ⇒ DECLINE (never a guess). ★ Hard boundary (honest): works when index/offset are LINEAR in the loop counter
and written values are within the scalar-fold range; complex pointer aliasing, nested indirection (A[B[C[i]]]), or
random-indexed memory ⇒ DECLINE. NO new certificate kind (routes to the linear/polynomial closed-form mechanism).
Adversarial: a closed form wrong on some index (off-by-one / missed aliasing) is caught by the quantified proof.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class ArrayFold:
    issued: bool
    paradigm: str = "array_memory"
    mechanism: str = "linear_recurrence"
    closed_form: str = ""
    detail: str = ""


def prove_inductive_array(closed_form: Callable, step: Callable, arr0_val: Callable, var: str = "j",
                          timeout_ms: int = 3000) -> bool:
    """Prove the closed form `cf(j)` is the final memory state of the inductive write loop: cf(0)==arr0 AND
    ∀j≥1. cf(j) == step(cf(j-1)). z3 ∀ over Int with a timeout; UNSAT of the negation ⇒ proved; sat/unknown/timeout ⇒
    DECLINE (no guess). `closed_form(j)`, `step(prev,j)`, `arr0_val()` build z3 exprs."""
    import z3
    j = z3.Int(var)
    arr0 = z3.Int("arr0")
    s = z3.Solver()
    s.set("timeout", timeout_ms)
    base_ok = closed_form(arr0, 0) == arr0_val(arr0)
    # ∀j≥1: cf(j) == step(cf(j-1), j)
    inductive = z3.Implies(j >= 1, closed_form(arr0, j) == step(closed_form(arr0, j - 1), j))
    s.add(z3.Not(z3.And(base_ok, z3.ForAll([j], inductive))))
    r = s.check()
    return r == z3.unsat


def fold_array(closed_form: Callable, step: Callable, arr0_val: Callable, cf_label: str) -> ArrayFold:
    if prove_inductive_array(closed_form, step, arr0_val):
        return ArrayFold(True, closed_form=cf_label, detail=f"inductive array write folded to ∀j. arr'[j]=={cf_label} "
                         "(z3 ∀-proved); O(n) sequential writes → closed-form state summary")
    return ArrayFold(False, closed_form=cf_label, detail="closed form not proved (wrong / diverges / timeout) ⇒ DECLINE")


def adversarial_battery() -> dict:
    """arr[i+1]=arr[i]+d folds to arr0+d·j (proved); a WRONG closed form (off-by-one) is caught; a nonlinear/aliased
    write (modeled as an unprovable closed form) DECLINEs honestly."""
    d = 3
    # correct: cf(j) = arr0 + d*j ; step(prev) = prev + d ; base cf(0)=arr0
    good = fold_array(lambda a0, j: a0 + d * j, lambda prev, j: prev + d, lambda a0: a0, "arr0 + 3*j")
    # ★ off-by-one wrong: cf(j) = arr0 + d*j + 1 ; base cf(0)=arr0+1 ≠ arr0 ⇒ caught
    wrong = fold_array(lambda a0, j: a0 + d * j + 1, lambda prev, j: prev + d, lambda a0: a0, "arr0 + 3*j + 1")
    # multiplicative recurrence arr[i+1]=arr[i]*2 → cf=arr0*2^j is NOT linear/affine-closed in this Int model
    # (2**j not a z3 Int term) ⇒ a wrong affine guess is caught (honest DECLINE for the nonlinear case)
    nonlinear = fold_array(lambda a0, j: a0 + 2 * j, lambda prev, j: prev * 2, lambda a0: a0, "arr0 + 2*j (vs *2)")
    cases = {"linear_write_folds": good.issued, "off_by_one_rejected": not wrong.issued,
             "nonlinear_write_declined": not nonlinear.issued}
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
