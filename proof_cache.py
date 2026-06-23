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
    triaged_direct: int = 0          # §3: large-but-simple goals routed straight to the solver (cache skipped)

    def rate(self) -> float:
        tot = self.hits + self.misses
        return round(self.hits / tot, 3) if tot else 0.0


_CACHE: Dict[Tuple, "Z.ProofResult"] = {}
STATS = _Stats()

# A3: optional SEMANTIC 2nd level (semantic_cache). OFF by default ⇒ behavior byte-identical to before (no
# regression, existing tests unaffected). semantic_cache.decide_and_wire() flips this ON only if a break-even
# gate (hit rate among structural misses ≥ 11.4%) passes on the fix-loop traffic proxy. Lossless either way.
SEMANTIC_ENABLED = False


def reset():
    _CACHE.clear()
    STATS.hits = STATS.misses = STATS.triaged_direct = 0


# §3 toggle (default ON): the fast-triage layer before the cache. OFF ⇒ byte-identical to the pre-§3 path.
TRIAGE_ENABLED = True


def prove_forall_cached(goal, var_types: Dict[str, str], assumptions: List = ()):
    """prove_forall with a structural cache. Cache hits skip the solver entirely. §3: a cheap O(size) triage runs
    FIRST — a large-but-simple goal (many nodes, solver-easy) is routed straight to the solver, skipping the
    canonical_key α-rename whose cost would exceed the solve. The verdict is identical either way (lossless —
    the solver still decides); triage only changes the PATH. When SEMANTIC_ENABLED, a structural MISS falls
    through to a lossless semantic 2nd level before the solver (A3, break-even gated)."""
    if TRIAGE_ENABLED:
        import proof_triage as PT
        if PT.route(*PT.complexity(goal, assumptions)) == "solver_direct":
            STATS.triaged_direct += 1
            return Z.prove_forall(goal, var_types, list(assumptions))   # skip canonicalization (it'd cost more)
    key = canonical_key(goal, var_types, assumptions)
    if key in _CACHE:
        STATS.hits += 1
        c = _CACHE[key]
        return Z.ProofResult(c.verdict, c.backend + "+cache", "cache hit: " + c.detail, c.counterexample)
    STATS.misses += 1
    if SEMANTIC_ENABLED:                                       # 2nd level, only if the gate enabled it
        try:
            import semantic_cache as _SC
            sr = _SC.consult(goal, var_types, assumptions)
            if sr is not None:
                _CACHE[key] = sr                              # promote so the next identical goal hits L1
                return sr
        except Exception:  # noqa: BLE001 — a 2nd-level glitch must never break proving
            pass
    r = Z.prove_forall(goal, var_types, list(assumptions))
    _CACHE[key] = r
    if SEMANTIC_ENABLED:
        try:
            import semantic_cache as _SC
            _SC.store(goal, var_types, assumptions, r)
        except Exception:  # noqa: BLE001
            pass
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


def measure_triage(k_terms: int = 120, n_goals: int = 24) -> dict:
    """§3 regression demo + fix. Build n DISTINCT large-but-simple linear goals (no cache hits ⇒ canonical_key is
    pure overhead). Without triage the structural cache LOSES (canonicalization > solve); WITH triage the goals
    route straight to the solver and the overhead vanishes. Verdicts are identical (lossless); routes deterministic."""
    import time
    import z3_adapter as Z
    import proof_triage as PT
    global TRIAGE_ENABLED

    goals = []
    for g in range(n_goals):
        terms = " + ".join(f"x{i}" for i in range(k_terms))
        pred = f"{terms} >= {terms} - {g + 1}"               # distinct per g, still linear & true (hardness 0)
        vt = {f"x{i}": "Int" for i in range(k_terms)}
        goals.append((Z.parse_predicate(pred, vt), vt))

    routes = [PT.route(*PT.complexity(go, [])) for go, _ in goals]
    routes2 = [PT.route(*PT.complexity(go, [])) for go, _ in goals]   # determinism: same route every time
    nodes0, depth0, hard0 = PT.complexity(goals[0][0], [])

    def run() -> float:
        reset()
        t = time.perf_counter()
        for go, vt in goals:
            prove_forall_cached(go, vt)
        return time.perf_counter() - t

    saved = TRIAGE_ENABLED
    TRIAGE_ENABLED = False
    off_s = run()                                            # cache pays canonical_key on every distinct goal
    TRIAGE_ENABLED = True
    on_s = run()
    direct = STATS.triaged_direct
    t = time.perf_counter()
    for go, vt in goals:                                     # uncached baseline (no cache, no canonicalization)
        Z.prove_forall(go, vt, [])
    uncached_s = time.perf_counter() - t
    mism = 0
    for go, vt in goals:                                     # lossless: triage-direct verdict == fresh solve
        if prove_forall_cached(go, vt).verdict != Z.prove_forall(go, vt, []).verdict:
            mism += 1
    TRIAGE_ENABLED = saved
    return {"k_terms": k_terms, "n_goals": n_goals, "nodes_per_goal": nodes0, "depth": depth0, "hardness": hard0,
            "all_routed_direct": direct == n_goals, "deterministic": routes == routes2,
            "triage_off_s": round(off_s, 4), "triage_on_s": round(on_s, 4), "uncached_s": round(uncached_s, 4),
            "regressed_without_triage": off_s > uncached_s, "fixed_with_triage": on_s <= off_s,
            "overhead_removed_pct": round((off_s - on_s) / off_s * 100, 1) if off_s else 0.0,
            "lossless_mismatches": mism}
