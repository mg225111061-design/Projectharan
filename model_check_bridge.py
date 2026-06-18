"""
v26 STAGE 6a — explicit-state model checker (TLA+/TLC-style core).
==================================================================
BFS reachability over a FINITE transition system: from the initial states, explore all reachable states;
if any reachable state violates the invariant, return a concrete counterexample TRACE (init → … → bad).
This is the core TLC does (the LLM drafts a spec/impl; the checker refutes with a trace; the loop fixes).

  check_model(inits, transition, invariant, max_states):
    inits       : iterable of hashable states
    transition  : state -> iterable of successor states
    invariant   : state -> bool  (must hold in every reachable state)

Verdicts:  MODEL_OK (invariant holds on all explored reachable states) | MODEL_COUNTEREXAMPLE (trace) |
           UNMODELED (state space exceeded the bound → inconclusive).

★ HONEST LIMITS ★: bounded / finite-state (state explosion). MODEL_OK means "no violation within the
explored reachable set up to `max_states`"; if the bound is hit before fixpoint, the result is UNMODELED
(inconclusive), never a false MODEL_OK.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Iterable, List


@dataclass
class MCVerdict:
    status: str                          # MODEL_OK | MODEL_COUNTEREXAMPLE | UNMODELED
    trace: List = field(default_factory=list)
    states_explored: int = 0
    detail: str = ""

    def __str__(self):
        if self.status == "MODEL_COUNTEREXAMPLE":
            return f"MODEL_COUNTEREXAMPLE — invariant violated; trace ({len(self.trace)} steps): {self.trace}"
        if self.status == "MODEL_OK":
            return f"MODEL_OK (bounded) — invariant holds on all {self.states_explored} reachable states explored"
        return f"{self.status} — {self.detail}"


def check_model(inits: Iterable, transition: Callable, invariant: Callable,
                max_states: int = 200000) -> MCVerdict:
    parent = {}
    seen = set()
    q = deque()
    for s in inits:
        if s not in seen:
            seen.add(s); parent[s] = None; q.append(s)
    explored = 0
    while q:
        s = q.popleft()
        explored += 1
        if not invariant(s):
            trace = []
            cur = s
            while cur is not None:
                trace.append(cur); cur = parent[cur]
            return MCVerdict("MODEL_COUNTEREXAMPLE", trace=list(reversed(trace)), states_explored=explored)
        if len(seen) > max_states:
            return MCVerdict("UNMODELED", states_explored=explored,
                             detail=f"state space exceeded {max_states} (bounded — inconclusive)")
        for t in transition(s):
            if t not in seen:
                seen.add(t); parent[t] = s; q.append(t)
    return MCVerdict("MODEL_OK", states_explored=explored)
