"""
v26 STAGE 4 — data-race & deadlock detector (lockset + lock-order-cycle).
=========================================================================
Operates on an explicit concurrency MODEL (HARAN has no threads): a dict {thread_id: [event, ...]},
each event a tuple (op, target) with op ∈ {"acq","rel","rd","wr"} and target a lock or variable name.

  • Data race (Eraser-style lockset): two CONFLICTING accesses — different threads, same variable, at
    least one a write — whose held-lock sets are DISJOINT (no common lock protects both) → RACE, with
    the concrete racing pair as the witness.
  • Deadlock (lock-order inversion): if any thread acquires L while holding H, add edge H→L; a cycle in
    this graph (e.g. t1: A then B; t2: B then A) → DEADLOCK, with the lock cycle as the witness.

Verdicts:  RACE_FREE | RACE (pair) | DEADLOCK (cycle) | UNMODELED.

★ HONEST LIMITS (labeled) ★:
  • Lockset is the classic data-race PRINCIPLE for LOCK-based synchronization. If threads synchronize by
    other means (fork/join order, signals, atomics), a reported pair may be ordered in reality — i.e. the
    detector can OVER-report (recall-favoring, like RacerD). It is sound for the lock model: RACE_FREE
    means "every conflicting access pair shares a lock" under the provided events.
  • A deadlock cycle is a NECESSARY lock-order-inversion condition (a standard warning), not a proof the
    schedule will deadlock at runtime.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

Event = Tuple[str, str]


@dataclass
class RaceVerdict:
    status: str                          # RACE_FREE | RACE | DEADLOCK | UNMODELED
    races: List[dict] = field(default_factory=list)      # [{var, a, b}]
    cycles: List[List[str]] = field(default_factory=list)
    detail: str = ""

    def __str__(self):
        if self.status == "DEADLOCK":
            return f"DEADLOCK — lock-order cycle {self.cycles[0]} (lock-order inversion)"
        if self.status == "RACE":
            r = self.races[0]
            return (f"RACE on '{r['var']}': {r['a']} vs {r['b']} (conflicting, disjoint locksets) "
                    f"[+{len(self.races)-1} more]" if len(self.races) > 1 else
                    f"RACE on '{r['var']}': {r['a']} vs {r['b']} (conflicting, disjoint locksets)")
        if self.status == "RACE_FREE":
            return "RACE_FREE (lock model) — every conflicting access pair shares a lock; no lock cycle."
        return f"{self.status} — {self.detail}"


def _accesses(threads: Dict[str, List[Event]]):
    """Yield (tid, idx, op, var, frozenset(locks_held)) for each rd/wr, tracking the per-thread lockset."""
    out = []
    for tid, evs in threads.items():
        held = []
        for idx, (op, tgt) in enumerate(evs):
            if op == "acq":
                held.append(tgt)
            elif op == "rel":
                if tgt in held:
                    held.remove(tgt)
            elif op in ("rd", "wr"):
                out.append((tid, idx, op, tgt, frozenset(held)))
    return out


def _lock_order_edges(threads: Dict[str, List[Event]]):
    """Edges H→L for every 'acquire L while holding H' (lock-order inversion graph)."""
    edges = set()
    for evs in threads.values():
        held = []
        for op, tgt in evs:
            if op == "acq":
                for h in held:
                    edges.add((h, tgt))
                held.append(tgt)
            elif op == "rel" and tgt in held:
                held.remove(tgt)
    return edges


def _find_cycle(edges) -> Optional[List[str]]:
    """Return a cycle in the directed graph `edges` (set of (u,v)), or None."""
    adj: Dict[str, List[str]] = {}
    for u, v in edges:
        adj.setdefault(u, []).append(v)
    WHITE, GREY, BLACK = 0, 1, 2
    color: Dict[str, int] = {}
    stack: List[str] = []

    def dfs(u) -> Optional[List[str]]:
        color[u] = GREY
        stack.append(u)
        for v in adj.get(u, []):
            if color.get(v, WHITE) == GREY:        # back-edge → cycle
                return stack[stack.index(v):] + [v]
            if color.get(v, WHITE) == WHITE:
                c = dfs(v)
                if c:
                    return c
        stack.pop()
        color[u] = BLACK
        return None

    for n in list(adj):
        if color.get(n, WHITE) == WHITE:
            c = dfs(n)
            if c:
                return c
    return None


def detect_races(threads: Dict[str, List[Event]]) -> RaceVerdict:
    """Detect data races (lockset) and deadlocks (lock-order cycle) on an explicit concurrency model."""
    if not threads or len(threads) < 1:
        return RaceVerdict("UNMODELED", detail="no threads in the model")
    cycle = _find_cycle(_lock_order_edges(threads))
    if cycle:
        return RaceVerdict("DEADLOCK", cycles=[cycle])
    accs = _accesses(threads)
    races = []
    for i in range(len(accs)):
        for j in range(i + 1, len(accs)):
            t1, i1, o1, v1, L1 = accs[i]
            t2, i2, o2, v2, L2 = accs[j]
            if t1 != t2 and v1 == v2 and ("wr" in (o1, o2)) and not (L1 & L2):
                races.append({"var": v1,
                              "a": f"{t1}#{i1}:{o1}", "b": f"{t2}#{i2}:{o2}"})
    if races:
        return RaceVerdict("RACE", races=races)
    return RaceVerdict("RACE_FREE")


def race_feedback(v: RaceVerdict) -> str:
    """Witness → concrete fix instruction for the loop."""
    if v.status == "RACE" and v.races:
        r = v.races[0]
        return (f"DATA RACE on '{r['var']}': {r['a']} and {r['b']} conflict with no common lock. "
                f"Fix: guard every access to '{r['var']}' with the SAME lock (or make it immutable / "
                f"thread-local).")
    if v.status == "DEADLOCK" and v.cycles:
        return (f"DEADLOCK risk: lock-order cycle {v.cycles[0]}. Fix: acquire these locks in one global "
                f"order in every thread (lock-ordering discipline).")
    return ""
