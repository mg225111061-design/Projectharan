"""
Pillar 3 · Stage 4 — algorithm recognition (hand-rolled idiom → known/optimized form).
=======================================================================================
Structural recognition of a naive implementation of a known algorithm/idiom (KernelFaRer in spirit — GEMM
idiom recognition). Recognition only PROPOSES; equivalence is decided by equiv.py and speedup by the measure
harness (Rule 5). Two recognizers here:
  • naive matmul (triple nested loop, C[i][j] += A[i][k]*B[k][j])  → an optimized-order / library replacement.
  • naive exponential self-recursion (fn calls itself ≥2×)         → a memoized / DP replacement.
"""
from __future__ import annotations

import ast
import inspect
import textwrap
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class Recognized:
    kind: str
    matched: bool
    evidence: str


def _ast_of(fn: Callable) -> Optional[ast.AST]:
    try:
        return ast.parse(textwrap.dedent(inspect.getsource(fn)))
    except (OSError, TypeError, SyntaxError):
        return None


def recognize_matmul(fn: Callable) -> Recognized:
    """Detect a triple-nested loop with a multiply-accumulate of two 2-D-subscripted operands — the GEMM idiom."""
    tree = _ast_of(fn)
    if tree is None:
        return Recognized("matmul", False, "source unavailable")
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        depth = sum(1 for s in ast.walk(node) if isinstance(s, ast.For))
        if depth < 3:
            continue
        # look for `acc += <2D subscript> * <2D subscript>` inside
        for s in ast.walk(node):
            mults = [m for m in ast.walk(s) if isinstance(m, ast.BinOp) and isinstance(m.op, ast.Mult)]
            for m in mults:
                if _is_2d_subscript(m.left) and _is_2d_subscript(m.right):
                    return Recognized("matmul", True, "triple loop with C += A[i][k]·B[k][j] (GEMM idiom)")
    return Recognized("matmul", False, "no GEMM idiom")


def _is_2d_subscript(node) -> bool:
    return isinstance(node, ast.Subscript) and isinstance(node.value, ast.Subscript)


def recognize_exp_recursion(fn: Callable) -> Recognized:
    """Detect a function that calls itself ≥2 times in one body → exponential blow-up, memoizable to DP."""
    tree = _ast_of(fn)
    if tree is None:
        return Recognized("exp_recursion", False, "source unavailable")
    name = fn.__name__
    self_calls = sum(1 for n in ast.walk(tree)
                     if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == name)
    if self_calls >= 2:
        return Recognized("exp_recursion", True, f"{self_calls} self-calls → exponential; memoize to DP")
    return Recognized("exp_recursion", False, f"{self_calls} self-call(s)")
