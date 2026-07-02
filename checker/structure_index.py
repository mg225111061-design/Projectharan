"""
§BD CHK-1 — STRUCTURE INDEXING (the speed core): one O(N) AST pass marks where each pattern is *possible*.
================================================================================================================
The whole point is to avoid O(N×P): instead of running P patterns over N lines, we index, in a SINGLE traversal,
the *sites* where each pattern could even apply (division sites, loops, exception handlers, resource handles,
None-compares, …). The pattern scan (CHK-2) then visits only the relevant sites ⇒ O(relevant) ≪ O(N×P). Reuses
`extract.classify.effect_gate` to classify purity / I/O / nondeterminism (part of the structure).
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class StructureIndex:
    parsed: bool
    syntax_error: Optional[str] = None
    n_lines: int = 0
    division_sites: List[ast.AST] = field(default_factory=list)      # /, //, % with a non-literal divisor
    loops: List[ast.AST] = field(default_factory=list)               # For / While
    except_handlers: List[ast.ExceptHandler] = field(default_factory=list)
    resource_opens: List[ast.AST] = field(default_factory=list)      # open(...) calls
    with_opens: int = 0                                              # open(...) inside a `with` (safe)
    none_compares: List[ast.Compare] = field(default_factory=list)   # x == None / != None
    mutable_default_args: List[ast.AST] = field(default_factory=list)
    while_true: List[ast.While] = field(default_factory=list)
    asserts: List[ast.Assert] = field(default_factory=list)
    dynamic_calls: List[ast.AST] = field(default_factory=list)       # eval/exec/__import__/compile ⇒ DEFER trigger
    functions: List[ast.FunctionDef] = field(default_factory=list)
    effect: str = "unknown"                                          # pure | io | nondet (from effect_gate)


_DYNAMIC = {"eval", "exec", "compile", "__import__"}


def _is_literal_nonzero(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and node.value != 0


def build_index(src: str) -> StructureIndex:
    """One pass over the AST. Records pattern-possible sites so the scan can skip irrelevant lines."""
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return StructureIndex(parsed=False, syntax_error=f"{e.msg} (line {e.lineno})")
    idx = StructureIndex(parsed=True, n_lines=src.count("\n") + 1)

    # mark open() calls that sit directly inside a `with` as safe (their handle is managed)
    safe_open_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.With):
            for item in node.items:
                c = item.context_expr
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == "open":
                    safe_open_ids.add(id(c))

    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            if not _is_literal_nonzero(node.right):
                idx.division_sites.append(node)
        elif isinstance(node, (ast.For, ast.While)):
            idx.loops.append(node)
            if isinstance(node, ast.While) and isinstance(node.test, ast.Constant) and node.test.value is True:
                idx.while_true.append(node)
        elif isinstance(node, ast.ExceptHandler):
            idx.except_handlers.append(node)
        elif isinstance(node, ast.Compare):
            if any(isinstance(c, ast.Constant) and c.value is None for c in node.comparators) and \
               any(isinstance(op, (ast.Eq, ast.NotEq)) for op in node.ops):
                idx.none_compares.append(node)
        elif isinstance(node, ast.Assert):
            idx.asserts.append(node)
        elif isinstance(node, ast.FunctionDef):
            idx.functions.append(node)
            for d in node.args.defaults + node.args.kw_defaults:
                if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                    idx.mutable_default_args.append(d)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "open":
                if id(node) in safe_open_ids:
                    idx.with_opens += 1
                else:
                    idx.resource_opens.append(node)
            elif node.func.id in _DYNAMIC:
                idx.dynamic_calls.append(node)

    try:
        from extract.classify import effect_gate as EG
        idx.effect = EG.classify_effect(src).effect      # "pure" | "io" | "nondet" | "opaque"
    except Exception:  # noqa: BLE001 — effect classification is best-effort; never breaks the index
        idx.effect = "unknown"
    return idx
