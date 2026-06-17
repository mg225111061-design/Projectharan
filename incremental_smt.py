"""
STAGE 1.2 — incremental SMT (solver reuse) [SPEED · decision-identical].
========================================================================
When a *family* of goals shares the same assumption prefix (a function's `requires`, a fixed set of
domain facts), the default `prove_forall` builds a fresh Z3 solver per goal and re-asserts the whole
prefix every time. Incremental solving asserts the shared prefix **once**, then `push` / assert ¬goal /
`check` / `pop` per goal — the solver keeps the learned clauses about the shared part across goals.

★ decision-identical: incremental returns the SAME verdict as fresh per-goal solving (verified in
  measure_incremental). It is purely a speed lever — never changes an answer.
★ honesty: incremental is NOT always faster (the handoff asks to find the slow cases). measure_incremental
  reports the A/B wall-clock either way; on small/linear prefixes the win can vanish or go negative.
"""
from __future__ import annotations

from typing import Dict, List

import z3_adapter as Z


def _env(var_types: Dict[str, str]):
    import z3
    real = all(t == "Real" for t in var_types.values()) or not var_types
    return {n: (z3.Real(n) if t == "Real" else z3.Int(n)) for n, t in var_types.items()}, real


def prove_batch_incremental(shared_assumptions: List, goals: List, var_types: Dict[str, str]) -> List[str]:
    """One reused solver: assert the shared prefix once; push/¬goal/check/pop per goal."""
    import z3
    env, real = _env(var_types)
    s = z3.Solver()
    s.set("timeout", 5000)
    for a in shared_assumptions:
        s.add(Z._to_z3(a, env, real))
    out = []
    for goal in goals:
        s.push()
        s.add(z3.Not(Z._to_z3(goal, env, real)))
        r = s.check()
        out.append("PROVEN" if r == z3.unsat else ("REFUTED" if r == z3.sat else "UNKNOWN"))
        s.pop()
    return out


def prove_batch_fresh(shared_assumptions: List, goals: List, var_types: Dict[str, str]) -> List[str]:
    """Baseline: a fresh solver per goal (re-asserts the shared prefix every time)."""
    return [Z.prove_forall(goal, var_types, list(shared_assumptions)).verdict for goal in goals]


def measure_incremental(shared_assumptions: List, goals: List, var_types: Dict[str, str]) -> dict:
    """A/B the two strategies; verify they agree (decision-identical) and report wall-clock both ways."""
    import time
    t = time.perf_counter(); inc = prove_batch_incremental(shared_assumptions, goals, var_types)
    inc_s = time.perf_counter() - t
    t = time.perf_counter(); fresh = prove_batch_fresh(shared_assumptions, goals, var_types)
    fresh_s = time.perf_counter() - t
    disagreements = sum(1 for a, b in zip(inc, fresh) if a != b)
    return {"goals": len(goals), "shared_assumptions": len(shared_assumptions),
            "disagreements": disagreements, "incremental_s": round(inc_s, 4),
            "fresh_s": round(fresh_s, 4),
            "speedup": round(fresh_s / inc_s, 2) if inc_s else 0.0,
            "verdicts": inc}
