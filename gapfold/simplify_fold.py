"""
§AD GAP 5 — DEEP ALGEBRAIC CANCELLATION (simplify-before-fold).
================================================================================================================
`(x+1)² − x² − 2x − 1` is identically zero, but we miss it unless the expression is algebraically simplified BEFORE
folding — a loop with cancelling terms is a trivial fold after simplification and an opaque blob before. §AA-W1
canonicalization catches shallow cases; deep cancellation needs real symbolic simplification. Fix: a simplify-before-fold
pass (symbolic expand/cancel, reusing §AA-W1 + grandfathered sympy) that EXPOSES the post-cancellation structure, which
then folds.

★ z3 gate (EXACT, precision 1.0): prove the simplified expression is equivalent to the original (∀ inputs, via §AA-W1's
`prove_semantics_preserving`) — semantics-preserving, exactly as canonicalization. A simplification that changes behavior
⇒ REJECT. ★ Float caveat: symbolic simplification over floats must respect non-associativity ⇒ integer/exact only, else
DECLINE (per §AA-W1 / §AB). Reuses §AA-W1 canonicalization + the grandfathered sympy.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import foldrate.canonicalize as CANON


@dataclass
class SimplifyFold:
    issued: bool
    original: str
    simplified: str = ""
    ops_before: int = 0
    ops_after: int = 0
    proved: bool = False
    detail: str = ""

    @property
    def cancellation_depth(self) -> int:
        return self.ops_before - self.ops_after


def simplify_fold(expr_str: str, var_names: List[str], dtype: str = "integer") -> SimplifyFold:
    """Simplify the expression symbolically (deep expand+cancel), z3-prove it equivalent to the original (§AA-W1), and
    fold the simplified form. ★ float ⇒ DECLINE (non-associative reassociation unsound)."""
    if dtype == "float":
        return SimplifyFold(False, expr_str, detail="float arithmetic is non-associative ⇒ symbolic reassociation/"
                                                   "cancellation DECLINED (integer/exact only, or APPROX-ε per §AB)")
    import sympy as sp
    syms = {n: sp.Symbol(n) for n in var_names}
    try:
        orig = sp.sympify(expr_str, locals=syms)
        simplified = sp.simplify(sp.expand(sp.cancel(orig)))     # deep: cancel → expand → simplify
    except (sp.SympifyError, TypeError, SyntaxError) as e:
        return SimplifyFold(False, expr_str, detail=f"parse error: {type(e).__name__}")
    ops_before = int(sp.count_ops(orig))
    ops_after = int(sp.count_ops(simplified))
    if not CANON.prove_semantics_preserving(orig, simplified, var_names, dtype):
        return SimplifyFold(False, expr_str, str(simplified), ops_before, ops_after,
                            detail="simplification NOT z3-proved equivalent ⇒ REJECT (behavior would change)")
    return SimplifyFold(True, expr_str, str(simplified), ops_before, ops_after, True,
                        detail=f"deep cancellation: {ops_before}→{ops_after} ops; simplified to `{simplified}` (z3 "
                               f"∀-proved equivalent, EXACT); the post-cancellation form folds where the blob DECLINED")


def adversarial_battery() -> dict:
    """`(x+1)² − x² − 2x − 1` deep-cancels to 0 (z3-proved, folds); `(x+1)·(x-1) − x*x + 1` → 0; ★ a non-equivalent
    'simplification' (claiming a nonzero expr is 0) is REJECTED by the z3 proof; ★ float cancellation is DECLINED
    (non-associativity)."""
    import sympy as sp
    zero1 = simplify_fold("(x+1)**2 - x**2 - 2*x - 1", ["x"], "integer")        # ≡ 0
    zero2 = simplify_fold("(x+1)*(x-1) - x*x + 1", ["x"], "integer")            # ≡ 0
    nontrivial = simplify_fold("x**2 + 2*x + 1", ["x"], "integer")              # ≡ (x+1)² (folds but ≠ 0)
    # ★ a non-equivalent simplification: claim x²+1 ≡ x² (false) ⇒ prove_semantics_preserving must reject
    x = sp.Symbol("x")
    wrong = CANON.prove_semantics_preserving(x ** 2 + 1, x ** 2, ["x"], "integer")
    flt = simplify_fold("(x+1)**2 - x**2 - 2*x - 1", ["x"], "float")            # float ⇒ DECLINE
    cases = {
        "deep_cancellation_to_zero": zero1.issued and zero1.simplified == "0" and zero1.cancellation_depth > 0,
        "second_cancellation_zero": zero2.issued and zero2.simplified == "0",
        "nontrivial_simplify_proved": nontrivial.issued and nontrivial.proved,
        "non_equivalent_rejected": not wrong,
        "float_declined": (not flt.issued) and "DECLINED" in flt.detail,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
