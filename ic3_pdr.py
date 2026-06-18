"""
v27 STAGE 17b — unbounded safety by k-induction (IC3/PDR family), complementing bounded model checking.
========================================================================================================
S6's model checker is BOUNDED (it explores states up to a depth). This proves safety for ALL reachable
states (infinite horizon) by k-induction over an SMT transition system:

    base step   : no state reachable within k transitions from init violates the property (else UNSAFE+trace)
    induction   : if the property held for k consecutive states, it holds at the (k+1)-th (k-inductive)
    ⇒ both hold : SAFE — the property is an inductive invariant for the whole (infinite) state space.

Predicates are Z3 callables on state dicts (init(s), trans(s,s'), prop(s)) — the same style as S6 — so the
solver is the trusted kernel. UNSAFE returns a concrete counterexample trace; not-k-inductive-within-bound
returns UNKNOWN (honest — needs a stronger invariant), never a false SAFE.

★ HONEST (§1.9, §5) ★: the implemented method is k-INDUCTION (a sound SMT-based unbounded-safety procedure
in the IC3/PDR/SAT-model-checking family). Full IC3/PDR clause-learning + interpolation is the extension
point — NOT claimed built here. SMT may return UNKNOWN on hard nonlinear systems; that is reported, never
hidden.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import z3

State = Dict[str, z3.ArithRef]
Pred1 = Callable[[State], z3.BoolRef]
Pred2 = Callable[[State, State], z3.BoolRef]


@dataclass
class SafetyVerdict:
    status: str                  # SAFE | UNSAFE | UNKNOWN
    method: str = "k-induction"
    k: int = 0
    invariant: str = ""
    trace: List[Dict[str, int]] = field(default_factory=list)
    detail: str = ""

    def __str__(self):
        if self.status == "SAFE":
            return f"SAFE (k-induction, k={self.k}): property is an inductive invariant — {self.invariant}"
        if self.status == "UNSAFE":
            return f"UNSAFE: counterexample trace {self.trace}"
        return f"UNKNOWN — {self.detail}"


def _state(varnames: List[str], tag: str) -> State:
    return {v: z3.Int(f"{v}_{tag}") for v in varnames}


def _model_trace(m, states: List[State], varnames: List[str]) -> List[Dict[str, int]]:
    out = []
    for s in states:
        row = {}
        for v in varnames:
            val = m.eval(s[v], model_completion=True)
            row[v] = val.as_long() if hasattr(val, "as_long") else str(val)
        out.append(row)
    return out


def prove_safety(varnames: List[str], init: Pred1, trans: Pred2, prop: Pred1,
                 max_k: int = 8, invariant_str: str = "prop") -> SafetyVerdict:
    """k-induction: increase k until the property is k-inductive (SAFE), a base counterexample appears
    (UNSAFE + trace), or the bound is hit (UNKNOWN — not k-inductive, needs strengthening)."""
    for k in range(1, max_k + 1):
        # ── base: is there a path of length <k from init that violates prop at some step? ──
        base = z3.Solver()
        bs = [_state(varnames, f"b{i}") for i in range(k)]
        base.add(init(bs[0]))
        for j in range(k - 1):
            base.add(trans(bs[j], bs[j + 1]))
        base.add(z3.Or([z3.Not(prop(bs[i])) for i in range(k)]))
        r = base.check()
        if r == z3.sat:
            return SafetyVerdict("UNSAFE", k=k, trace=_model_trace(base.model(), bs, varnames),
                                 detail=f"reachable property violation within {k} steps")
        if r == z3.unknown:
            return SafetyVerdict("UNKNOWN", k=k, detail="SMT returned unknown on the base case")
        # ── induction: assume prop for k consecutive states + transitions, derive prop at the next ──
        step = z3.Solver()
        ss = [_state(varnames, f"s{i}") for i in range(k + 1)]
        for j in range(k):
            step.add(prop(ss[j]))
            step.add(trans(ss[j], ss[j + 1]))
        step.add(z3.Not(prop(ss[k])))
        r2 = step.check()
        if r2 == z3.unsat:
            return SafetyVerdict("SAFE", k=k, invariant=invariant_str,
                                 detail=f"property is {k}-inductive")
        if r2 == z3.unknown:
            return SafetyVerdict("UNKNOWN", k=k, detail="SMT returned unknown on the induction step")
        # else: not yet k-inductive (a CTI exists) — try a larger k
    return SafetyVerdict("UNKNOWN", k=max_k,
                         detail=f"not k-inductive within k≤{max_k} — needs a stronger invariant (honest)")
