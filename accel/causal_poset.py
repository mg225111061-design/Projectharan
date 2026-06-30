"""
§BC ACCEL Round-5 CA-1 — CAUSAL POSET + Dilworth: the EXACT parallelism bound (not a new speedup).
================================================================================================================
★ Axis Y (runtime acceleration), NOT fold — and per the directive this round adds **no new speedup**: it makes
the parallelism the existing gates already prove safe *exact* instead of pairwise/heuristic. `verified_parallel`
proves which I/O calls are independent (disjoint read/write sets = `_conflicts`); here we lift that pairwise
independence into a **partial order** (a ≺ b iff a precedes b in program order AND they conflict, so b must wait
for a), and read two classical invariants off it:

  • **Dilworth (1950)**: max antichain = min chain cover ⇒ the PROVABLY-MAXIMUM number of ops that may run at once
    (the exact width — no schedule can run more concurrently while respecting the proven dependences).
  • **Longest chain (Mirsky)**: the DAG's longest path ⇒ the EXACT Amdahl critical path (the serial floor — no
    schedule, however many cores, can finish below it).

So the "acceleration" is the SAME independence `sep_alias`/`verified_parallel` already prove; the NEW thing is the
exact ceiling: max concurrency = width, exact Amdahl bound = total / critical-path (unit cost). This replaces the
estimate with a theorem. ★ Never summed with fold-rate (Axis X) or the Clocks — Axis Y only. Reordering legality
stays the existing gates' job; a dependence we cannot rule out is kept (conservative ⇒ an edge ⇒ sequential).

Zero-dep: pure stdlib (Kuhn bipartite matching for Dilworth, DAG longest path). No "relativistic acceleration"
(banned) — this is Lamport happens-before / Dilworth combinatorics, a tighter bound, not a faster clock.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Set, Tuple

from accel.pipeline import Acceleration, proved, rejected
from accel.verified_parallel import _conflicts


def _conflict_pairs(tasks: List[Dict]) -> Set[Tuple[int, int]]:
    """The unordered conflicting pairs (i,j), i<j: one writes what the other reads/writes (true/anti/output dep)."""
    pairs: Set[Tuple[int, int]] = set()
    for i in range(len(tasks)):
        ri, wi = set(tasks[i].get("reads", [])), set(tasks[i].get("writes", []))
        for j in range(i + 1, len(tasks)):
            rj, wj = set(tasks[j].get("reads", [])), set(tasks[j].get("writes", []))
            if (wi & rj) or (wj & ri) or (wi & wj):
                pairs.add((i, j))
    return pairs


def build_poset(tasks: List[Dict]) -> Dict[int, Set[int]]:
    """The strict precedence ≺ as transitive closure: i ≺ j (i must finish before j) iff i precedes j in PROGRAM
    ORDER and they conflict. Independent pairs are incomparable (⇒ may run concurrently). Conservative: any pair
    we cannot prove independent IS an edge (kept sequential) — never a missed dependence."""
    n = len(tasks)
    succ: Dict[int, Set[int]] = {i: set() for i in range(n)}
    pairs = _conflict_pairs(tasks)
    for (i, j) in pairs:                                  # i<j in program order ⇒ i ≺ j (j waits for i)
        succ[i].add(j)
    # transitive closure (Floyd–Warshall reachability) so Dilworth uses the full comparability relation
    for k in range(n):
        for i in range(n):
            if k in succ[i]:
                succ[i] |= succ[k]
    return succ


def _comparable(succ: Dict[int, Set[int]]) -> Set[Tuple[int, int]]:
    return {(i, j) for i in succ for j in succ[i]}


def dilworth_width(succ: Dict[int, Set[int]]) -> int:
    """Max antichain size = min chain cover (Dilworth) = n − (max bipartite matching on the strict comparability
    relation). This is the provably-maximum number of mutually-incomparable ops ⇒ the exact max concurrency."""
    n = len(succ)
    if n == 0:
        return 0
    adj = {i: sorted(succ[i]) for i in succ}              # left i → right j for every i ≺ j
    match_r: Dict[int, int] = {}

    def aug(u: int, seen: Set[int]) -> bool:
        for v in adj[u]:
            if v in seen:
                continue
            seen.add(v)
            if v not in match_r or aug(match_r[v], seen):
                match_r[v] = u
                return True
        return False

    matching = sum(1 for u in range(n) if aug(u, set()))
    return n - matching                                   # min chain cover = max antichain (Dilworth)


def longest_chain(succ: Dict[int, Set[int]]) -> int:
    """The DAG's longest path (in #nodes) = the critical path = the EXACT Amdahl serial floor (height of the poset)."""
    n = len(succ)
    memo: Dict[int, int] = {}

    def depth(u: int) -> int:
        if u in memo:
            return memo[u]
        d = 1 + max((depth(v) for v in succ[u]), default=0)
        memo[u] = d
        return d

    return max((depth(i) for i in range(n)), default=0)


def causal_schedule(tasks: List[Dict]) -> Acceleration:
    """Compute the EXACT parallel schedule bound for a partially-dependent op set. proved() carries the
    Dilworth width (max concurrency) and the critical path (exact Amdahl ceiling = n / critical_path at unit cost);
    a fully-sequential chain ⇒ width 1 / ceiling 1× (honestly: NO speedup). Never overlaps a proven dependence."""
    n = len(tasks)
    if n < 2:
        return rejected("CA.poset", "exact parallel schedule bound", "need ≥2 ops to schedule")
    succ = build_poset(tasks)
    width = dilworth_width(succ)
    crit = longest_chain(succ)
    ceiling = round(n / crit, 3) if crit else 1.0         # exact Amdahl ceiling at unit cost (≤ #cores caveat)
    detail = (f"causal poset of {n} ops (≺ = program-order ∧ read/write conflict, transitively closed); "
              f"Dilworth max-antichain (width) = {width} ⇒ provably-max concurrency; longest chain = {crit} ⇒ "
              f"EXACT Amdahl critical path ⇒ ceiling = n/crit = {ceiling}× at unit cost (≤ #cores). This is a "
              f"tighter BOUND on the independence the gates already prove — not a new speedup, never summed with "
              f"fold-rate or the Clocks.")
    return proved("CA.poset", f"schedule {n} ops: width {width}, critical path {crit}", detail)


def adversarial_battery() -> dict:
    """sequential chain ⇒ width 1 / ceiling 1× (no speedup); independent ⇒ width n / ceiling n×; two parallel
    chains ⇒ width 2 / crit 2 / ceiling 2×; a dependence is NEVER scheduled concurrently (conservative)."""
    out = {}
    # fully-dependent chain a0→a1→a2→a3 (each writes x, next reads x): width 1, crit 4
    chain = [{"name": f"a{k}", "reads": (["x"] if k else []), "writes": ["x"]} for k in range(4)]
    s = build_poset(chain)
    out["chain_width1"] = dilworth_width(s) == 1 and longest_chain(s) == 4
    # fully-independent (disjoint locations): width 4, crit 1 ⇒ embarrassingly parallel
    indep = [{"name": f"b{k}", "reads": [f"r{k}"], "writes": [f"w{k}"]} for k in range(4)]
    si = build_poset(indep)
    out["indep_width4"] = dilworth_width(si) == 4 and longest_chain(si) == 1
    # two parallel chains: a0→a1 (on x), b0→b1 (on y), a⊥b ⇒ width 2, crit 2, ceiling 2×
    two = [{"name": "a0", "writes": ["x"]}, {"name": "a1", "reads": ["x"], "writes": ["x"]},
           {"name": "b0", "writes": ["y"]}, {"name": "b1", "reads": ["y"], "writes": ["y"]}]
    s2 = build_poset(two)
    out["two_chains_width2"] = dilworth_width(s2) == 2 and longest_chain(s2) == 2
    sched2 = causal_schedule(two)
    out["two_chains_ceiling2x"] = (sched2.proved and "ceiling = n/crit = 2.0×" in sched2.certificate)
    # ★ a real dependence is never lost: a writes x, b reads x ⇒ they are comparable (an edge), not concurrent
    dep = [{"name": "a", "writes": ["x"]}, {"name": "b", "reads": ["x"]}]
    out["dependence_kept"] = dilworth_width(build_poset(dep)) == 1     # comparable ⇒ width 1 ⇒ sequential
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
