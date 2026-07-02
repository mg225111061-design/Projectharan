"""
Pillar 3 · ROUND 3 #61 — bounded model checking (BMC): bounded-depth equivalence/safety, shallowest counterexample.
==================================================================================================================
BMC unrolls a stateful transition system k steps and asks Z3, over ALL input sequences of length ≤ k, whether a
property can fail (here: whether an "optimized" transition diverges from the spec). UNSAT at every depth ≤ k ⇒
the two agree for EVERY input sequence up to depth k — EXACT on that bounded-depth domain (the same kind of
∀-inputs/bounded guarantee the bounded equiv-lifts give). SAT at some depth ⇒ a concrete counterexample TRACE
at the SHALLOWEST depth — the optimization is wrong ⇒ DECLINE (BMC is the adversarial bug-finder: it reports the
exact input sequence that breaks it). Pairs with #65 k-induction: BMC discharges the base window, induction the
rest — together = EXACT for all n.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Tuple

import z3

import kernel_verdict as KV


@dataclass
class BMCResult:
    verdict: "KV.Verdict"
    safe_to_depth: int
    counterexample_depth: Optional[int]
    trace: Optional[dict]


def _unroll(trans: Callable, s0, xs):
    s = s0
    for x in xs:
        s = trans(s, x)
    return s


def bmc_equiv(name: str, spec: Callable, opt: Callable, s0, k: int) -> BMCResult:
    """Find the SHALLOWEST input sequence (length ≤ k) on which `opt`'s state diverges from `spec`'s, starting
    from s0. None within k ⇒ EXACT to depth k (∀ inputs). A divergence ⇒ DECLINE with the counterexample trace."""
    for d in range(1, k + 1):
        xs = [z3.Int(f"x{i}") for i in range(d)]
        sa = _unroll(spec, s0, xs)
        sb = _unroll(opt, s0, xs)
        s = z3.Solver()
        s.add(sa != sb)
        r = s.check()
        if r == z3.sat:
            m = s.model()
            trace = {f"x{i}": (m[xs[i]].as_long() if m[xs[i]] is not None else 0) for i in range(d)}
            v = KV.decline(f"{name}: BMC found a divergence at depth {d} (trace {trace}) ⇒ DECLINE (optimization wrong)",
                           f"bmc:{name}")
            return BMCResult(v, d - 1, d, trace)
        if r == z3.unknown:
            v = KV.decline(f"{name}: BMC z3 unknown at depth {d} ⇒ conservatively DECLINE", f"bmc:{name}")
            return BMCResult(v, d - 1, None, None)
    cert = KV.Cert(KV.EXACT, "bmc_bounded_equiv", passed=True, check_cost=f"Z3 ∀-inputs, depths 1..{k}",
                   detail=f"{name}: opt ≡ spec for EVERY input sequence of length ≤ {k} (bounded-depth EXACT)")
    return BMCResult(KV.exact(name, f"bmc:{name}", f"bounded-depth EXACT (k={k})", cert), k, None, None)


# ── stateful transitions: an equivalent optimization (EXACT to depth k) and a buggy one (BMC finds the trace) ─
def spec_accumulate(s, x):
    return s + x                                            # the reference running accumulator


def opt_accumulate_ok(s, x):
    return (s + x) + 0                                      # a trivially-equivalent "optimization"


def opt_accumulate_bug(s, x):
    return s + x + z3.If(x > 10, z3.IntVal(1), z3.IntVal(0))   # BUG: off-by-one when x>10 (divergence at depth 1)


def spec_clamp(s, x):
    # running sum clamped at ≥ 0 each step
    return z3.If(s + x < 0, z3.IntVal(0), s + x)


def opt_clamp_bug(s, x):
    # BUG: clamps the INPUT not the running sum ⇒ diverges once a negative drives the true sum below 0 later
    return (z3.If(x < 0, z3.IntVal(0), x)) + s
