"""
Pillar 3 · CONTINUUM — polynomial (degree-≤2) loop-sum → Faulhaber closed form, EXACT FOR ALL n (k-induction).
=============================================================================================================
A loop  s = Σ_{i<n} (a·i² + b·i + c)  is O(n). Its closed form  a·n(n-1)(2n-1)/6 + b·n(n-1)/2 + c·n  is O(1).
Unlike the bounded-Z3 lifts, this is proven EXACT FOR ALL n by k-induction (#65): base closed(0)=0 ∧ step
closed(n)+(a·n²+b·n+c)=closed(n+1) — both Z3 ∀-goals. So it's an EXACT O(n)→O(1) ceiling-breaker valid on the
WHOLE unbounded domain (not just a sampled/bounded one). A wrong closed form fails the inductive step ⇒ DECLINE.
Wires the k-induction prover into a measured Pillar-3 lift: prove-for-all-n + a coherent whole-program measure.
"""
from __future__ import annotations

from typing import Callable, Optional, Tuple

import kernel_verdict as KV
from pillar3 import kinduction as KI
from pillar3 import lifting as LF


def closed_z3(a: int, b: int, c: int) -> Callable:
    """The closed form as a function of a z3 Int (z3 integer division '/'). Used for the k-induction proof."""
    return lambda k: a * (k * (k - 1) * (2 * k - 1) / 6) + b * (k * (k - 1) / 2) + c * k


def closed_num(a: int, b: int, c: int) -> Callable:
    """The closed form in exact Python integers ('//'). O(1). Used for the numeric measurement."""
    return lambda n: a * (n * (n - 1) * (2 * n - 1) // 6) + b * (n * (n - 1) // 2) + c * n


def naive(a: int, b: int, c: int) -> Callable:
    def loop(n):
        s = 0
        for i in range(n):
            s += a * i * i + b * i + c                       # O(n)
        return s
    return loop


def _step(a: int, b: int, c: int) -> Callable:
    return lambda s, n: s + (a * n * n + b * n + c)


def polysum_grade(a: int, b: int, c: int, *, n: int, samples: int = 5, residual_iters: int = 0,
                  floor: float = 1.30, closed_override: Callable = None) -> Tuple[KV.Verdict, Optional[object]]:
    """Prove the closed form for ALL n by k-induction, then measure the O(n)→O(1) whole-program win. EXACT iff
    proven AND a win; a wrong closed form fails the inductive step ⇒ DECLINE."""
    cz = closed_override or closed_z3(a, b, c)
    ind = KI.prove_closed_form(f"polysum_{a}_{b}_{c}", cz, _step(a, b, c), 0)
    if ind.verdict.status != KV.EXACT:
        return KV.decline(f"polysum: closed form NOT proven for all n (base={ind.base_ok}, step={ind.step_ok}) ⇒ DECLINE",
                          "polysum"), None
    nf, cf = naive(a, b, c), closed_num(a, b, c)
    rep = LF.measure_lift(lambda nn: nf(nn), lambda nn: cf(nn), lambda: (n,), residual_iters, n=n, samples=samples)
    if not rep.beats(floor):
        v = KV.decline(f"polysum: proven but no whole-program win (×{rep.whole_program_ratio:.2f}) ⇒ DECLINE", "polysum")
        v.report = rep
        return v, rep
    cert = KV.Cert(KV.EXACT, "kinduction_closed_form", passed=True, check_cost="Z3 base+step (∀n)",
                   detail=f"Σ(a·i²+b·i+c), a={a} b={b} c={c}: closed form ≡ loop for ALL n by induction; O(n)→O(1)")
    v = KV.exact(cf, "polysum", str(rep), cert)
    v.report = rep
    return v, rep


# a deliberately-wrong closed form (drops the −1 in the quadratic term) for the moat
def wrong_closed_z3(a: int, b: int, c: int) -> Callable:
    return lambda k: a * (k * k * (2 * k - 1) / 6) + b * (k * (k - 1) / 2) + c * k    # k·k instead of k·(k−1)


INSTANCES = [(3, 2, 5), (1, 0, 0), (2, -4, 7)]
