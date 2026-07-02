"""
§3 — AST-depth / complexity FAST-TRIAGE, BEFORE the structural proof cache.
===========================================================================
The structural cache (`proof_cache.canonical_key`) α-renames + structurally walks the WHOLE goal and sorts the
assumptions on every call. For a LARGE-but-SIMPLE goal (many nodes, but linear / quantifier-light — trivial for
the solver) that canonicalization costs MORE than just solving, so the cache regresses. Fix: a cheap O(size)
triage that runs first and routes such goals straight to the solver, skipping canonicalization entirely.

The meter is a single pass — node count, max depth, and a "hardness" signal (nonlinear var·var products +
quantifier count) — with NO α-renaming, NO string building, NO sorting. It is a DETERMINISTIC function of the AST
(same goal ⇒ same route), so it changes only the PATH taken, NEVER the verdict (the solver still decides; the
cached and direct verdicts are identical — lossless).
"""
from __future__ import annotations

from typing import List, Tuple

import haran_ast as A

# Measured crossover (see proof_cache.measure_triage): below this node count the structural cache's α-rename is
# cheaper than re-solving; at/above it, for a solver-EASY goal (hardness 0), canonicalization dominates ⇒ skip it.
BIG_NODES = 160


def _children(e):
    if isinstance(e, A.Un):
        return (e.operand,)
    if isinstance(e, A.Bin):
        return (e.lhs, e.rhs)
    if isinstance(e, A.Call):
        return tuple(e.args)
    if isinstance(e, A.Quant):
        return (e.body,)
    return ()


def _has_var(e) -> bool:
    if isinstance(e, A.Var):
        return True
    return any(_has_var(c) for c in _children(e))


def complexity(goal, assumptions: List = ()) -> Tuple[int, int, int]:
    """O(size) single pass → (nodes, depth, hardness). hardness = nonlinear var·var (or var/var) products +
    quantifiers — the solver-difficulty signal. No renaming / strings / sorting (cheaper than canonical_key)."""
    nodes = 0
    max_depth = 0
    hardness = 0

    def walk(e, d):
        nonlocal nodes, max_depth, hardness
        nodes += 1
        if d > max_depth:
            max_depth = d
        if isinstance(e, A.Quant):
            hardness += 1
        elif isinstance(e, A.Bin) and e.op in ("*", "/", "%") and _has_var(e.lhs) and _has_var(e.rhs):
            hardness += 1                                     # nonlinear: var·var (Z3-hard)
        for c in _children(e):
            walk(c, d + 1)

    walk(goal, 1)
    for a in assumptions:
        walk(a, 1)
    return nodes, max_depth, hardness


def route(nodes: int, depth: int, hardness: int) -> str:
    """Deterministic routing. 'solver_direct' = large-but-simple ⇒ skip the cache (canonicalization would cost
    more than solving). 'cache' = small/medium OR structurally rich (the α-rename + O(1) lookup pays off)."""
    if nodes >= BIG_NODES and hardness == 0:
        return "solver_direct"
    return "cache"


def decide(goal, assumptions: List = ()) -> Tuple[str, Tuple[int, int, int]]:
    c = complexity(goal, assumptions)
    return route(*c), c
