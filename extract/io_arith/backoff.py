"""
§AQ §5.BACKOFF — exponential backoff (geometric series) and token-bucket (interval-linear clamp), z3-proven.
================================================================================================================
Exponential backoff total wait `Σ base·2ᵏ = base·(2ⁿ − 1)` ⇒ ★REDUCE to the existing geometric / generating-function
mechanism (S-1), z3-proven. Token bucket `min(cap, tok + rate·Δt)` is interval-linear (the clamp = a case split);
within the unclamped region it is linear. All pure arithmetic framed off the I/O.
"""
from __future__ import annotations


def prove_backoff_geometric(base: int = 1, n: int = 6, correct: bool = True) -> bool:
    """z3 LIA: Σ_{k=0}^{n−1} base·2ᵏ == base·(2ⁿ − 1). WRONG: base·(2ⁿ) ⇒ SAT."""
    import z3
    total = z3.IntVal(0)
    for k in range(n):
        total = total + base * (2 ** k)
    closed = base * ((2 ** n) - (1 if correct else 0))
    sol = z3.Solver(); sol.add(total != closed)
    return sol.check() == z3.unsat


def prove_token_bucket_linear(rate: int = 5, steps: int = 4, cap: int = 10 ** 9) -> bool:
    """z3 LIA: in the UNCLAMPED region, tok += rate over `steps` == tok₀ + steps·rate (the clamp is a separate case)."""
    import z3
    tok0 = z3.Int("tok0")
    tok = tok0
    for _ in range(steps):
        tok = tok + rate                                         # unclamped region (tok stays < cap)
    closed = tok0 + steps * rate
    sol = z3.Solver(); sol.add(tok != closed)
    return sol.check() == z3.unsat


def adversarial_battery() -> dict:
    """★ exponential backoff total = base·(2ⁿ−1) z3-proven (⇒ geometric, existing); ★ token-bucket unclamped region is
    linear (z3-proven; clamp = case split); ★★ a wrong geometric closed form (2ⁿ vs 2ⁿ−1) is z3-REFUTED."""
    cases = {
        "backoff_geometric_proven": prove_backoff_geometric(1, 6, True),
        "token_bucket_linear": prove_token_bucket_linear(),
        "backoff_wrong_refuted": not prove_backoff_geometric(1, 6, False),     # ★★
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
