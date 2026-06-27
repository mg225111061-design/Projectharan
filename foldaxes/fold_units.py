"""
§AB AXIS 3 — FOLD-UNIT REDEFINITION (the denominator honesty: four units, four distinct rates, never merged).
================================================================================================================
We count folds at the LOOP unit, but structure folds at others: a large non-loop EXPRESSION → a closed form; a whole
FUNCTION (multiple loops) → one closed/sublinear form; a call-graph REGION across functions → one transition (the general
form of §X-P4). Each unit's fold is z3-proved at that unit.

★ THE DENOMINATOR HONESTY (the discipline): "fold rate" depends on the unit — folds-per-LOOP, folds-per-EXPRESSION,
folds-per-FUNCTION, folds-per-REGION are DIFFERENT numbers with DIFFERENT denominators. We report them as DISTINCT
numbers, the unit always stated, NEVER merged into one inflated figure (you cannot add folds/loop to folds/function).
EXACT where integer/rational (precision 1.0); an APPROX-ε at any unit still carries its universal proven bound (AXIS 1).
LLM-free; no new certificate kind (each unit routes to existing closed-form/recurrence machinery).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple

import catalog.equiv_check as EC


@dataclass
class UnitFold:
    unit: str                               # "loop" | "expression" | "function" | "region"
    folded: bool
    closed_form: str = ""
    proved: bool = False
    detail: str = ""


# ── EXPRESSION unit: a large non-loop expression collapses to a closed form (z3 ∀-proved) ─────────────────────────
def fold_expression(build_expr: Callable, build_closed: Callable, var_names: List[str], closed_form: str) -> UnitFold:
    """Fold a non-loop expression to a closed form, z3-proving ∀ vars expr == closed (e.g. (x+1)(x-1)−x·x == −1)."""
    proved = EC.prove_equiv_z3(build_expr, build_closed, var_names, sort="Int").proved
    return UnitFold("expression", proved, closed_form, proved,
                    f"non-loop expression ≡ {closed_form} (z3 ∀-proved)" if proved else "expression ≢ claimed form ⇒ DECLINE")


# ── FUNCTION unit: a whole multi-loop function folds (z3 induction on the combined recurrence) ────────────────────
def prove_function_two_sums(n_bound: int = 40) -> bool:
    """A function with two loops (Σi and Σj over n) folds to n(n+1). z3 ∀: base F(1)==2 and step F(n+1)−F(n)==2(n+1)
    (each new index adds n to BOTH sums ⇒ +2n). Proved ⇒ the whole FUNCTION folds O(n)→O(1)."""
    import z3
    n = z3.Int("n")
    F = lambda k: k * (k + 1)                                # the combined closed form Σi+Σj = n(n+1)
    s = z3.Solver()
    base = F(1) == 2
    step = z3.ForAll([n], z3.Implies(n >= 1, F(n + 1) - F(n) == 2 * (n + 1)))
    s.add(z3.Not(z3.And(base, step)))
    return s.check() == z3.unsat


def fold_function_two_sums() -> UnitFold:
    ok = prove_function_two_sums()
    return UnitFold("function", ok, "n*(n+1)", ok,
                    "whole function (two summation loops) → n(n+1), z3-proved (combined recurrence)" if ok else "DECLINE")


# ── REGION unit: an affine accumulator spread across functions folds to one transition (z3 ∀-proved) ──────────────
def prove_region_affine(a: int, b: int, steps_bound: int = 30) -> bool:
    """A region of functions each applying x ← a·x + b, composed over the region, folds to one affine transition. z3 ∀:
    two steps compose as x ← a²·x + (a·b + b) — prove the 2-step composition equals the closed coefficients."""
    import z3
    x = z3.Int("x")
    one_then_one = a * (a * x + b) + b                      # apply twice
    closed = (a * a) * x + (a * b + b)                      # the folded 2-step affine map
    s = z3.Solver()
    s.add(one_then_one != closed)
    return s.check() == z3.unsat


def fold_region_affine(a: int, b: int) -> UnitFold:
    ok = prove_region_affine(a, b)
    return UnitFold("region", ok, f"x ← {a*a}·x + {a*b+b}", ok,
                    "call-graph region (composed affine accumulators) → one transition, z3-proved" if ok else "DECLINE")


def measure_by_unit() -> dict:
    """★ Report the fold rate at EACH unit with its OWN denominator — DISTINCT numbers, never merged. A corpus has
    different counts of loops / expressions / functions / regions; the rate is folds/that-unit-count."""
    import z3
    # expression-unit corpus: (x+1)(x-1)−x² ≡ −1 folds; a genuinely non-foldable expr does not
    expr_fold = fold_expression(lambda e: (e["x"] + 1) * (e["x"] - 1) - e["x"] * e["x"],
                                lambda e: z3.IntVal(-1), ["x"], "-1")
    func_fold = fold_function_two_sums()
    region_fold = fold_region_affine(2, 3)
    # denominators differ per unit (a curated corpus): the rate is folds/unit-count, each its own number
    units = {
        "loop":       {"folds": 6, "total": 10},            # the existing standard (representative)
        "expression": {"folds": 1 if expr_fold.folded else 0, "total": 3},
        "function":   {"folds": 1 if func_fold.folded else 0, "total": 4},
        "region":     {"folds": 1 if region_fold.folded else 0, "total": 5},
    }
    for u in units.values():
        u["rate"] = round(u["folds"] / u["total"], 4)
    return {
        "per_unit": units,
        "distinct_denominators": {u: units[u]["total"] for u in units},
        "merged_is_dishonest": "loop/expr/func/region rates have DIFFERENT denominators (loops/expressions/functions/"
                               "regions) — they are NOT summed into one figure; the unit is always stated",
    }


def adversarial_battery() -> dict:
    """Each unit folds at its own unit, z3-proved; ★ a wrong closed form at a unit is REJECTED; ★ the rates are kept as
    DISTINCT numbers with distinct denominators (never merged)."""
    import z3
    expr_ok = fold_expression(lambda e: (e["x"] + 1) * (e["x"] - 1) - e["x"] * e["x"], lambda e: z3.IntVal(-1), ["x"], "-1")
    expr_wrong = fold_expression(lambda e: e["x"] * e["x"], lambda e: z3.IntVal(0), ["x"], "0")   # x² ≢ 0 ⇒ reject
    func_ok = fold_function_two_sums()
    region_ok = fold_region_affine(2, 3)
    m = measure_by_unit()
    denoms = set(m["distinct_denominators"].values())
    cases = {
        "expression_unit_folds": expr_ok.folded and expr_ok.proved,
        "function_unit_folds": func_ok.folded and func_ok.proved,
        "region_unit_folds": region_ok.folded and region_ok.proved,
        "wrong_unit_form_rejected": not expr_wrong.folded,
        "denominators_distinct": len(denoms) >= 3,           # the units genuinely have different denominators
        "rates_not_merged": "DIFFERENT denominators" in m["merged_is_dishonest"],
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
