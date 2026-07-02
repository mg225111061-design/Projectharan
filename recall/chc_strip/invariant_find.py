"""
§AP §6.1 — INVARIANT FIND: is the array loop a SELF-referential recurrence (scalarizable) or data-dependent? + a z3
================================================================================================================
CHC-style INDUCTIVE-invariant proof for the affine case. An array loop `a[i] = expr` is scalarizable to a unary
recurrence in n iff its right-hand side reads the array ONLY at fixed negative offsets a[i−k] (k≥1 constant) and reads
NO external array/data — then a[n] is a pure function of n (O(n) loop ⇒ O(1)/O(log n) closed form). If the body reads
`data[i]` (external input) or a non-fixed offset (a[n−i], a[i+1]), it is NOT scalarizable (DECLINE — honest).

★ The z3/CHC core: given the recovered scalar closed form (a polynomial in i) and the affine update a[i]=A·a[i−1]+B·i+C,
`verify_inductive_z3` PROVES the closed form satisfies the recurrence ∀ i — a genuine inductive invariant, not a fit.
A wrong closed form is refuted. ★ S-2: the invariant is z3-proven, never assumed.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from fractions import Fraction
from typing import List, Optional


@dataclass
class ScalarInfo:
    scalarizable: bool
    order: int = 0
    external_data: bool = False
    detail: str = ""


def analyze(src: str) -> ScalarInfo:
    """AST: find the array updated as `arr[i] = …` in the loop; classify its RHS array reads."""
    try:
        tree = ast.parse(src)
    except Exception as e:  # noqa: BLE001
        return ScalarInfo(False, 0, False, f"parse error ({e}) ⇒ not scalarizable")
    # locate the loop index and the array-update assignment
    idx = arr = None
    rhs = None
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            for stmt in ast.walk(node):
                if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                        and isinstance(stmt.targets[0], ast.Subscript)
                        and isinstance(stmt.targets[0].value, ast.Name)
                        and isinstance(stmt.targets[0].slice, ast.Name)
                        and stmt.targets[0].slice.id == node.target.id):
                    idx, arr, rhs = node.target.id, stmt.targets[0].value.id, stmt.value
                    break
            if rhs is not None:
                break
    if rhs is None:
        return ScalarInfo(False, 0, False, "no `arr[i] = …` self-update loop found ⇒ not a scalarizable array recurrence")
    order = 0
    external = False
    for sub in ast.walk(rhs):
        if isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name):
            if sub.value.id != arr:
                external = True                                   # reads a DIFFERENT array (data[i]) ⇒ data-dependent
                continue
            off = _fixed_neg_offset(sub.slice, idx)
            if off is None:
                return ScalarInfo(False, 0, external, f"array read {arr}[…] is not a fixed negative offset (a[n−i] / "
                                  "a[i+1] / a[2i]) ⇒ not a single-index recurrence ⇒ DECLINE")
            order = max(order, off)
    if external:
        return ScalarInfo(False, order, True, "RHS reads an external data array (a[i] depends on input) ⇒ NOT "
                          "scalarizable to a closed form in n ⇒ honest DECLINE")
    return ScalarInfo(True, order, False, f"self-referential array recurrence of order {order} (RHS reads only "
                      f"{arr}[i−k], k≥1) ⇒ scalarizable to a unary recurrence in n")


def _fixed_neg_offset(slc: ast.AST, idx: str) -> Optional[int]:
    """Return k>0 if `slc` is `idx - k` (constant), else None. `idx` alone counts as offset 0 (the write target use)."""
    if isinstance(slc, ast.Name) and slc.id == idx:
        return 0
    if (isinstance(slc, ast.BinOp) and isinstance(slc.op, ast.Sub)
            and isinstance(slc.left, ast.Name) and slc.left.id == idx
            and isinstance(slc.right, ast.Constant) and isinstance(slc.right.value, int) and slc.right.value >= 1):
        return slc.right.value
    return None


def verify_inductive_z3(poly_coeffs: List[Fraction], a_coef: int, i_coef: int, const: int) -> bool:
    """★ z3 CHC inductive proof: the closed form g(i)=Σ poly_coeffs[d]·iᵈ satisfies g(i) = a_coef·g(i−1) + i_coef·i +
    const  ∀ i. UNSAT of the negation ⇒ the invariant is a theorem (a wrong closed form is SAT ⇒ refuted)."""
    import z3
    i = z3.Real("i")

    def g(x):
        return z3.Sum([z3.RealVal(float(c)) * x ** d for d, c in enumerate(poly_coeffs)]) if poly_coeffs else z3.RealVal(0)
    s = z3.Solver()
    s.add(g(i) != a_coef * g(i - 1) + i_coef * i + const)
    return s.check() == z3.unsat
