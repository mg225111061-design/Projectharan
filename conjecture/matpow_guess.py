"""
§AI §1.4 — MATRIX-POWER conjecturer. Defeats: disguised mutual / coupled recurrence (state transition).
================================================================================================================
Recover the linear recurrence (via the harness), realize its O(log N) companion-matrix-power closed form (REUSE
§AD gapfold/mutual_recursion.mat_pow), and CROSS-CHECK that the matrix power reproduces the iterated terms exactly,
plus the harness's z3 ∀-proof + held-out guard. The fold is O(N) iteration → O(log N) matrix power. No new mechanism.
"""
from __future__ import annotations

from typing import Callable, List

from conjecture import harness as H


def _companion(coeffs: List[int]) -> List[List[int]]:
    L = len(coeffs)
    return [list(coeffs)] + [[1 if c == r else 0 for c in range(L)] for r in range(L - 1)]


def conjecture(fn: Callable[[int], object], probe: int = 24, holdout: int = 200) -> H.ConjResult:
    import kernel_verdict as KV
    r = H.conjecture_verify(fn, probe, holdout)
    if not r.issued:
        return r
    coeffs = [int(c) for c in r.verdict.result.get("coeffs", [])] if isinstance(r.verdict.result, dict) else []
    L = len(coeffs)
    if L < 1:
        return H.ConjResult(False, "matrix_power", 0, "-", KV.decline("no companion ⇒ DECLINE", "matpow"), "no recurrence")
    # ★ cross-check: the companion-matrix power reproduces the iterated terms EXACTLY (O(log N) ≡ O(N))
    from gapfold.mutual_recursion import mat_pow
    seq = [int(fn(i)) for i in range(probe)]
    M = _companion(coeffs)
    ok = True
    for n in range(L, probe):
        Mn = mat_pow(M, n - (L - 1))                          # advance the initial window to step n
        init = [seq[L - 1 - k] for k in range(L)]            # [a_{L-1}, …, a_0]
        val = sum(Mn[0][c] * init[c] for c in range(L))
        if val != seq[n]:
            ok = False
            break
    if not ok:
        return H.ConjResult(False, "matrix_power", L, "-", KV.decline("companion matpow ≠ iteration ⇒ DECLINE", "matpow"),
                            "matrix-power realization disagreed with iteration ⇒ DECLINE")
    return H.ConjResult(True, "matrix_power", L, "blackbox+z3+matpow", r.verdict,
                        f"O(N) iteration → O(log N) companion matrix power (order {L}); matpow≡iteration cross-checked "
                        "+ harness z3 ∀-proof + held-out ⇒ EXACT")


def adversarial_battery() -> dict:
    """A disguised order-2 coupled recurrence (Fibonacci-class) folds to an O(log N) matrix power (matpow≡iteration
    cross-checked + z3 + held-out); ★ a diverge-after adversary DECLINES."""
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
    cases = {"matpow_folds": fib.issued and fib.structure_class == "matrix_power",
             "diverge_declines": not adv.issued}
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
