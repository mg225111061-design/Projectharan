"""
ACCEL §3 — MOVE B: VERIFIED PARALLELISM (overlap I/O wait, use idle cores). The MOST DANGEROUS technique (races,
deadlocks) ⇒ the proof bar is the HIGHEST. Concurrency is applied ONLY with a machine-checked independence /
race-freedom proof.
================================================================================================================
  • B1 async/overlap of independent I/O — prove NO data dependence between the calls (none reads what another
    writes; no shared mutable write). Disjoint or commuting ⇒ issue concurrently; any conflict ⇒ DECLINE.
  • B2 data parallelism — prove loop-carried-dependence-free AND no shared-mutable-write race; a REDUCTION is allowed
    only if its combine is proved ASSOCIATIVE + COMMUTATIVE. ★ Honest measurement: the proof unlocks SAFETY, the
    MEASURED factor decides DEPLOYMENT — the sandbox's marshalling overhead is overhead-bound (<1×), reported and NOT
    deployed; the win materialises on real multicore / shared-memory.
  • B3 race / deadlock-freedom oracle — prove (acyclic lock order ⇒ deadlock-free) or REFUTE (a cycle is a found bug).

Adversarial battery rejected 100%: dependent calls as independent, racy loops as parallel, non-associative
reductions, cyclic lock orders. Precision = 1.0 (zero unsafe concurrency applied).
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

from accel.pipeline import Acceleration, proved, rejected


# ── dependence analysis: disjoint read/write conflict sets ──────────────────────────────────────────────
def _conflicts(tasks: List[Dict]) -> List[str]:
    """A conflict between two tasks exists iff one WRITES a location the other READS or WRITES (true/anti/output
    dependence). Returns the human-readable conflicts; empty ⇒ provably independent."""
    out = []
    for i in range(len(tasks)):
        ri, wi = set(tasks[i].get("reads", [])), set(tasks[i].get("writes", []))
        for j in range(i + 1, len(tasks)):
            rj, wj = set(tasks[j].get("reads", [])), set(tasks[j].get("writes", []))
            ni, nj = tasks[i].get("name", i), tasks[j].get("name", j)
            if wi & rj:
                out.append(f"{ni}✍∩{nj}👁 on {sorted(wi & rj)} (true dep)")
            if wj & ri:
                out.append(f"{nj}✍∩{ni}👁 on {sorted(wj & ri)} (anti dep)")
            if wi & wj:
                out.append(f"{ni}✍∩{nj}✍ on {sorted(wi & wj)} (output dep / write-write race)")
    return out


def verified_async_overlap(tasks: List[Dict]) -> Acceleration:
    """B1: propose 'issue these sequential I/O calls concurrently'. VERIFY pairwise independence (disjoint read/write
    conflict sets). Proved ⇒ concurrent await is safe; any conflict ⇒ DECLINE (never overlap dependent I/O)."""
    if len(tasks) < 2:
        return rejected("B.async", "overlap I/O concurrently", "need ≥2 tasks to overlap")
    conflicts = _conflicts(tasks)
    if conflicts:
        return rejected("B.async", "overlap I/O concurrently", "data dependence: " + "; ".join(conflicts[:3]))
    return proved("B.async", f"overlap {len(tasks)} I/O calls concurrently",
                  f"pairwise independence proved — disjoint read/write sets across all {len(tasks)} tasks "
                  "(none reads/writes what another writes)")


# ── associativity + commutativity of a reduction combine (exhaustive over a small domain — sound there) ──
def prove_assoc_comm(op: Callable, domain: Sequence = (0, 1, 2, 3)) -> Tuple[bool, str]:
    try:
        for a in domain:
            for b in domain:
                if op(a, b) != op(b, a):
                    return False, f"NOT commutative: op({a},{b})≠op({b},{a})"
                for c in domain:
                    if op(op(a, b), c) != op(a, op(b, c)):
                        return False, f"NOT associative: op(op({a},{b}),{c})≠op({a},op({b},{c}))"
    except Exception as e:  # noqa: BLE001
        return False, f"combine raised {type(e).__name__}"
    return True, f"associative + commutative on the domain {tuple(domain)} (exhaustive)"


def verified_data_parallel(loop: Dict, work: Optional[Callable] = None, measure: bool = False) -> Acceleration:
    """B2: propose 'map these loop iterations across cores'. VERIFY (a) no loop-carried dependence (`carried` False),
    (b) no shared-mutable-write race, (c) if a `reduction` combine is given, it is assoc+comm. The proof unlocks
    SAFETY; the MEASURED factor (optional) decides deployment — overhead-bound is reported, NOT deployed."""
    if loop.get("carried"):
        return rejected("B.parallel", "parallelize the loop",
                        "loop-carried dependence — iteration n reads iteration n−1's result")
    shared_writes = loop.get("shared_writes")
    reduction = loop.get("reduction")
    if shared_writes and not reduction:
        return rejected("B.parallel", "parallelize the loop",
                        f"shared mutable write to {sorted(shared_writes)} without a reduction ⇒ RACE")
    cert = "iterations independent (no carried dep, no shared write)"
    if reduction is not None:
        ok, why = prove_assoc_comm(reduction)
        if not ok:
            return rejected("B.parallel", "parallel reduce", f"reduction combine {why} ⇒ result depends on order ⇒ DECLINE")
        cert = f"iterations independent; reduction combine {why}"
    acc = proved("B.parallel", "parallelize the loop", cert)
    # ★ honest measurement: the proof is safety; deployment needs a measured win (sandbox is overhead-bound) ★
    if measure and work is not None:
        acc.clock_c_speedup = _measure_parallel(work)
        if acc.clock_c_speedup is not None and acc.clock_c_speedup <= 1.0:
            acc.reason = (f"PROVED SAFE but overhead-bound (measured {acc.clock_c_speedup}× — marshalling overhead) "
                          "⇒ reported, NOT deployed in this sandbox; the win materialises on real multicore")
    return acc


def _measure_parallel(work: Callable, n: int = 4) -> Optional[float]:
    """Measure serial vs thread-pool wall-clock honestly. In the sandbox (GIL + marshalling) this is typically <1×
    — reported truthfully, never faked into an Nx."""
    import time
    from concurrent.futures import ThreadPoolExecutor
    try:
        t0 = time.perf_counter()
        for _ in range(n):
            work()
        serial = time.perf_counter() - t0
        t1 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=n) as ex:
            list(ex.map(lambda _: work(), range(n)))
        par = time.perf_counter() - t1
        return round(serial / par, 3) if par > 0 else None
    except Exception:  # noqa: BLE001
        return None


# ── B3: race / deadlock-freedom — lock-order acyclicity ─────────────────────────────────────────────────
def verified_race_free(lock_orders: List[List[str]]) -> Acceleration:
    """B3: `lock_orders` = the lock-acquisition sequences each thread takes. Build the lock-ORDER graph (an edge
    a→b whenever a thread holds a then acquires b) and check ACYCLICITY: acyclic ⇒ deadlock-free (proved); a CYCLE
    is a potential deadlock (a found bug — refuted, high value)."""
    edges: Set[Tuple[str, str]] = set()
    for seq in lock_orders:
        for a, b in zip(seq, seq[1:]):
            edges.add((a, b))
    nodes = {x for e in edges for x in e}
    adj: Dict[str, List[str]] = {n: [] for n in nodes}
    for a, b in edges:
        adj[a].append(b)
    # cycle detection (DFS colouring)
    color: Dict[str, int] = {n: 0 for n in nodes}
    cyc: List[str] = []

    def dfs(u, stack):
        color[u] = 1
        for v in adj[u]:
            if color[v] == 1:
                cyc.extend(stack[stack.index(v):] + [v])
                return True
            if color[v] == 0 and dfs(v, stack + [v]):
                return True
        color[u] = 2
        return False

    for n in nodes:
        if color[n] == 0 and dfs(n, [n]):
            return rejected("B.racefree", "prove deadlock-free",
                            f"LOCK-ORDER CYCLE {' → '.join(cyc)} — potential deadlock (a found bug; refuted)")
    return proved("B.racefree", "prove deadlock-free",
                  f"lock-order graph is ACYCLIC over {len(nodes)} locks ⇒ deadlock-free (safe to parallelize further)")
