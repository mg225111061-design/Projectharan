"""
§AI §1.1 — LINEAR-RECURRENCE conjecturer (Berlekamp-Massey). Defeats: disguised Fibonacci / linear DP.
================================================================================================================
A thin wrapper: observe the output, recover the minimal LFSR/C-finite recurrence with Berlekamp-Massey (REUSE
native_sequence), then dispose via the harness's held-out + z3 ∀-proof gate. No new mechanism (existing
linear_recurrence kind), no new disposer.
"""
from __future__ import annotations

from typing import Callable

from conjecture import harness as H


def conjecture(fn: Callable[[int], object], probe: int = 24, holdout: int = 200) -> H.ConjResult:
    """Recover a linear recurrence from the black-box output and z3-verify the companion closed form ∀n."""
    r = H.conjecture_verify(fn, probe, holdout)
    if r.issued:
        r.structure_class = "linear_recurrence"
    return r


def adversarial_battery() -> dict:
    """A disguised Fibonacci (closure) folds EXACT (BM + held-out + z3); ★ a diverge-after-probe adversary DECLINES."""
    def make_fib():
        memo = {0: 0, 1: 1}
        def f(n):
            if n not in memo:
                f(n - 1); memo[n] = memo[n - 1] + memo[n - 2]
            return memo[n]
        return f
    fib = conjecture(make_fib())
    def diverge(n):
        a, b = 0, 1
        for _ in range(n):
            a, b = b, a + b
        return a if n < 24 else a + 1
    adv = conjecture(diverge)
    cases = {"disguised_linear_folds": fib.issued and fib.structure_class == "linear_recurrence",
             "diverge_after_declines": not adv.issued}
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
