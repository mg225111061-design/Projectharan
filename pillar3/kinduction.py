"""
Pillar 3 · ROUND 3 #65 — k-induction: prove a loop invariant / closed form for UNBOUNDED n (Z3, EXACT).
=======================================================================================================
Bounded Z3 (the lifting/affine validators) proves an identity only up to a finite size. k-induction lifts that
to ALL n: prove the base case(s) AND the inductive step (assume the property at n, prove it at n+1); together
they cover the unbounded domain by mathematical induction — Z3 discharges both as ∀-goals. So a closed form
that matched a recurrence on bounded lengths is PROMOTED to EXACT FOR ALL n (a strict accuracy gain — the moat
widens from "bounded-domain EXACT" to "all-n EXACT"). If the inductive step fails (Z3 counterexample), the
closed form is NOT valid in general ⇒ DECLINE (never extrapolate an identity that doesn't actually induct).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

import z3

import kernel_verdict as KV


def _valid(claim) -> Tuple[bool, Optional[str]]:
    """A ∀-goal is valid iff its negation is UNSAT. Returns (valid, counterexample-or-None)."""
    s = z3.Solver()
    s.add(z3.Not(claim))
    r = s.check()
    if r == z3.unsat:
        return True, None
    if r == z3.sat:
        return False, str(s.model())
    return False, "z3 unknown"


@dataclass
class InductionResult:
    verdict: "KV.Verdict"
    base_ok: bool
    step_ok: bool
    counterexample: Optional[str]


def prove_closed_form(name: str, closed: Callable, recur_step: Callable, init_val: int) -> InductionResult:
    """Prove  closed(n) == S(n)  for ALL n≥0, where S(0)=init_val and S(n+1)=recur_step(S(n), n). By induction:
    base  closed(0)==init_val  AND  step  recur_step(closed(n), n) == closed(n+1)  (∀ n≥0). Both ⇒ EXACT-all-n."""
    n = z3.Int("n")
    base_ok, _ = _valid(closed(z3.IntVal(0)) == z3.IntVal(init_val))
    step_ok, cex = _valid(z3.Implies(n >= 0, recur_step(closed(n), n) == closed(n + 1)))
    if base_ok and step_ok:
        cert = KV.Cert(KV.EXACT, "k_induction", passed=True, check_cost="Z3 base + step (∀n)",
                       detail=f"{name}: closed form ≡ recurrence for ALL n≥0 by induction (base ∧ step proven)")
        return InductionResult(KV.exact(name, f"induct:{name}", "unbounded-n EXACT", cert), True, True, None)
    why = "base case fails" if not base_ok else f"inductive step fails (cex {cex})"
    return InductionResult(KV.decline(f"{name}: closed form NOT valid for all n — {why} ⇒ DECLINE", f"induct:{name}"),
                           base_ok, step_ok, cex)


def prove_invariant(name: str, inv: Callable, init, transition: Callable) -> InductionResult:
    """Prove a loop invariant inv(s) holds for ALL reachable states: base inv(init) AND step inv(s) ⇒ inv(transition(s))."""
    s = z3.Int("s")
    base_ok, _ = _valid(inv(init))
    step_ok, cex = _valid(z3.Implies(inv(s), inv(transition(s))))
    if base_ok and step_ok:
        cert = KV.Cert(KV.EXACT, "k_induction_invariant", passed=True, check_cost="Z3 base + step",
                       detail=f"{name}: invariant holds for every reachable state (base ∧ step proven)")
        return InductionResult(KV.exact(name, f"inv:{name}", "unbounded invariant", cert), True, True, None)
    why = "base fails" if not base_ok else f"step fails (cex {cex})"
    return InductionResult(KV.decline(f"{name}: not an inductive invariant — {why} ⇒ DECLINE", f"inv:{name}"),
                           base_ok, step_ok, cex)


# ── batteries: closed forms proven for ALL n (these PROMOTE the bounded affine/Faulhaber lifts to unbounded) ─
def closed_forms():
    return [
        # Σ_{i<n} i = n(n-1)/2     S(n+1)=S(n)+n
        ("sum_i", lambda k: k * (k - 1) / 2, lambda s, n: s + n, 0),
        # Σ_{i<n} i² = n(n-1)(2n-1)/6   S(n+1)=S(n)+n²  (Faulhaber)
        ("sum_i2", lambda k: k * (k - 1) * (2 * k - 1) / 6, lambda s, n: s + n * n, 0),
        # Σ_{i<n} (2i+1) = n²   S(n+1)=S(n)+(2n+1)
        ("sum_odd", lambda k: k * k, lambda s, n: s + (2 * n + 1), 0),
    ]


def wrong_closed_forms():
    return [
        # n(n+1)/2 is NOT Σ_{i<n} i (off by the index window) — step fails
        ("sum_i_WRONG", lambda k: k * (k + 1) / 2, lambda s, n: s + n, 0),
        # n² is NOT Σ_{i<n} i² — step fails
        ("sum_i2_WRONG", lambda k: k * k, lambda s, n: s + n * n, 0),
    ]


def invariants():
    return [
        ("even_x", lambda x: x % 2 == 0, z3.IntVal(0), lambda x: x + 2),
        ("nonneg", lambda x: x >= 0, z3.IntVal(5), lambda x: x + 3),
    ]
