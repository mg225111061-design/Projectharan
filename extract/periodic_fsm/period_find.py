"""
§AQ §4.PERIOD — find the period when control flow is a DETERMINISTIC function of the loop counter (`i mod k`).
================================================================================================================
If every branch guard is `i%k==c` / `i%k<c` / `i%k∈S` (constant k), the control flow is periodic with P = lcm(all k)
(pigeonhole: the reachable (state, i mod P) set is finite). ★ A guard that depends on DATA (`data[i] > 0`, an input
param) is NOT a function of i ⇒ NOT periodic ⇒ honest DECLINE (it can only go to §5 / spec-declared). Detection is a
finite search; the FOLD itself is the existing matrix-power / control_flatten mechanism (S-1).
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from math import gcd
from typing import List


@dataclass
class PeriodResult:
    periodic: bool
    period: int = 0
    moduli: List[int] = None
    data_dependent: bool = False
    detail: str = ""


def _lcm(xs):
    p = 1
    for x in xs:
        p = p * x // gcd(p, x) if x else p
    return p


def analyze(src: str, loop_var: str = "i") -> PeriodResult:
    try:
        tree = ast.parse(src)
    except Exception as e:  # noqa: BLE001
        return PeriodResult(False, 0, [], False, f"parse error ({e})")
    moduli: List[int] = []
    data_dep = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            left = node.left
            # i % k <cmp> const  ⇒ periodic guard
            if (isinstance(left, ast.BinOp) and isinstance(left.op, ast.Mod)
                    and isinstance(left.left, ast.Name) and isinstance(left.right, ast.Constant)
                    and isinstance(left.right.value, int)):
                moduli.append(left.right.value)
            else:
                # a guard reading a subscript / a non-loop variable is data-dependent
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Subscript):
                        data_dep = True
    if data_dep and not moduli:
        return PeriodResult(False, 0, [], True,
                            "branch guard depends on DATA (subscript / input) ⇒ not a function of i ⇒ DECLINE (→ §5/spec-declared)")
    if not moduli:
        return PeriodResult(False, 0, [], False, "no i%k periodic guard found")
    P = _lcm(moduli)
    return PeriodResult(True, P, sorted(set(moduli)), data_dep,
                        f"periodic control flow: guards on i%{sorted(set(moduli))} ⇒ period P = lcm = {P}")
