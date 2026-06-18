"""
v26 STAGE 6b — linearizability checker (Wing-Gong / Porcupine-style backtracking search).
==========================================================================================
Given a concurrent HISTORY of operations (each with a call time, return time, op, arg, observed result)
and a SEQUENTIAL spec, decide whether some linearization exists: a total order that (a) respects
real-time precedence — if op A returns before op B is called, A precedes B — and (b) reproduces every
observed result when the ops are applied to the spec in that order.

  history : list of dicts {id, call, ret, op, arg, result}
  apply_  : (state, op, arg) -> (new_state, result)   — the sequential specification
  init    : initial spec state

Verdicts:  LINEARIZABLE | NOT_LINEARIZABLE (the history is the witness) | UNMODELED.

★ HONEST LIMITS ★: linearizability checking is NP-complete → this is a bounded backtracking search
(exponential worst case; fine for short histories). NOT_LINEARIZABLE is a definite refutation (no order
reproduces the results); LINEARIZABLE means a valid order was found for THIS history.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass
class LinVerdict:
    status: str                          # LINEARIZABLE | NOT_LINEARIZABLE | UNMODELED
    order: Optional[List[int]] = None    # a witnessing linearization (op ids) when LINEARIZABLE
    detail: str = ""

    def __str__(self):
        if self.status == "LINEARIZABLE":
            return f"LINEARIZABLE — witness order (op ids): {self.order}"
        if self.status == "NOT_LINEARIZABLE":
            return "NOT_LINEARIZABLE — no order respecting real-time precedence reproduces the results"
        return f"{self.status} — {self.detail}"


def is_linearizable(history: List[dict], apply_: Callable, init) -> LinVerdict:
    """Wing-Gong backtracking: repeatedly linearize a real-time-minimal op whose result the spec
    reproduces, recursing on the rest. See module docstring."""
    if not history:
        return LinVerdict("LINEARIZABLE", order=[])
    for o in history:
        if not all(k in o for k in ("id", "call", "ret", "op", "result")):
            return LinVerdict("UNMODELED", detail="each op needs id/call/ret/op/result")

    def search(remaining: List[dict], state, order: List[int]) -> Optional[List[int]]:
        if not remaining:
            return order
        # an op is eligible to go NEXT iff no other remaining op MUST precede it (r.ret <= o.call)
        minimal = [o for o in remaining
                   if not any(r is not o and r["ret"] <= o["call"] for r in remaining)]
        for o in minimal:
            ns, res = apply_(state, o["op"], o.get("arg"))
            if res == o["result"]:
                got = search([r for r in remaining if r is not o], ns, order + [o["id"]])
                if got is not None:
                    return got
        return None

    order = search(list(history), init, [])
    if order is not None:
        return LinVerdict("LINEARIZABLE", order=order)
    return LinVerdict("NOT_LINEARIZABLE")


# --- a ready-made sequential spec: a read/write register (handy for tests & demos) ---
def register_apply(state, op, arg):
    if op == "write":
        return (arg, "ok")
    if op == "read":
        return (state, state)
    raise ValueError(f"unknown register op {op}")
