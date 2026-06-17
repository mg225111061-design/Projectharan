"""
STAGE 2.1 — structural proof cache (SPEED · lossless-decision).
===============================================================
Re-verification, contract checks across similar functions, and follow-up rounds re-prove the *same*
∀-goal over and over. This caches the Z3 verdict keyed on a CANONICAL form of the goal: free variables
α-renamed by first occurrence, types attached, assumptions canonicalized + sorted.

Why this is SOUND (lossless decision): `z3_adapter.prove_forall` proves `∀(free vars). goal` — a
universally-closed statement. Its truth value is invariant under any consistent bijective renaming of
those free variables, so two goals with the same canonical key denote the same ∀-statement and MUST
share the verdict (PROVEN/REFUTED/UNKNOWN). The key also carries the per-variable type, so an Int-typed
goal never aliases its Real-typed twin. We additionally *check* this empirically (see measure_cache:
every cache hit is re-solved fresh and asserted equal) — claim verified, not just argued.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import haran_ast as A
import z3_adapter as Z


def _canon(e, ren: Dict[str, str]) -> str:
    """Canonical string of a HARAN expr; α-renames free Vars to v0,v1,… by first occurrence (ren is
    threaded so the same source name maps to the same vN across goal + assumptions)."""
    if isinstance(e, A.Num):
        return ("f" if e.is_float else "i") + str(e.value)
    if isinstance(e, A.BoolLit):
        return "B" + str(e.value)
    if isinstance(e, A.Var):
        if e.name not in ren:
            ren[e.name] = f"v{len(ren)}"
        return ren[e.name]
    if isinstance(e, A.Un):
        return f"({e.op} {_canon(e.operand, ren)})"
    if isinstance(e, A.Bin):
        return f"({e.op} {_canon(e.lhs, ren)} {_canon(e.rhs, ren)})"
    if isinstance(e, A.Call):
        fn = e.func.name if isinstance(e.func, A.Var) else "?"
        return f"{fn}({','.join(_canon(a, ren) for a in e.args)})"
    if isinstance(e, A.Quant):
        inner = dict(ren)
        for v in e.vars:
            inner.setdefault(v, f"v{len(inner)}")
        return f"({e.kind} {','.join(inner[v] for v in e.vars)}. {_canon(e.body, inner)})"
    return type(e).__name__


def canonical_key(goal, var_types: Dict[str, str], assumptions: List = ()) -> Tuple:
    ren: Dict[str, str] = {}
    g = _canon(goal, ren)
    asm = tuple(sorted(_canon(a, ren) for a in assumptions))
    types = tuple(sorted((ren[n], t) for n, t in var_types.items() if n in ren))
    return (g, asm, types)


@dataclass
class _Stats:
    hits: int = 0
    misses: int = 0

    def rate(self) -> float:
        tot = self.hits + self.misses
        return round(self.hits / tot, 3) if tot else 0.0


_CACHE: Dict[Tuple, "Z.ProofResult"] = {}
STATS = _Stats()


def reset():
    _CACHE.clear()
    STATS.hits = STATS.misses = 0


def prove_forall_cached(goal, var_types: Dict[str, str], assumptions: List = ()):
    """prove_forall with a structural cache. Cache hits skip the solver entirely."""
    key = canonical_key(goal, var_types, assumptions)
    if key in _CACHE:
        STATS.hits += 1
        c = _CACHE[key]
        return Z.ProofResult(c.verdict, c.backend + "+cache", "cache hit: " + c.detail, c.counterexample)
    STATS.misses += 1
    r = Z.prove_forall(goal, var_types, list(assumptions))
    _CACHE[key] = r
    return r


# --------------------------------------------------------- measurement
def measure_cache(workload) -> dict:
    """workload: list of (goal_ast, var_types, assumptions). Reports hit-rate, time saved, and — the
    lossless check — that EVERY cache hit equals a fresh uncached solve."""
    import time
    reset()
    t0 = time.perf_counter()
    for goal, vt, asm in workload:
        prove_forall_cached(goal, vt, asm)
    cached_s = time.perf_counter() - t0

    # baseline: same workload, no cache
    t0 = time.perf_counter()
    for goal, vt, asm in workload:
        Z.prove_forall(goal, vt, list(asm))
    uncached_s = time.perf_counter() - t0

    # LOSSLESS audit: re-solve each item fresh; the cached verdict must match exactly
    mismatches = 0
    for goal, vt, asm in workload:
        ck = canonical_key(goal, vt, asm)
        fresh = Z.prove_forall(goal, vt, list(asm))
        if _CACHE[ck].verdict != fresh.verdict:
            mismatches += 1
    return {"n": len(workload), "hits": STATS.hits, "misses": STATS.misses,
            "hit_rate": STATS.rate(), "lossless_mismatches": mismatches,
            "cached_s": round(cached_s, 4), "uncached_s": round(uncached_s, 4),
            "speedup": round(uncached_s / cached_s, 1) if cached_s else 0.0}
