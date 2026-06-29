"""
§AL §1.4 — CLOSURE UNWRAP: state captured in a closure / higher-order factory, produced by REPEATED CALLS rather than
================================================================================================================
by f(n). `make()` returns a `step()` that bumps captured state — the sequence is step(),step(),… not a unary oracle, so
§AI can't see it. The strip builds the unary oracle `oracle(n) = value after n+1 calls of a FRESH instance` (fresh each
probe ⇒ deterministic), then §AI + z3 dispose. ★ semantics-faithful (it just iterates the real closure).
"""
from __future__ import annotations

from typing import Callable, Optional

from recall import core


def closure_oracle(src: str, factory: str = "make") -> Optional[Callable[[int], object]]:
    """exec the source; return oracle(n) = (n+1)-th value from a FRESH `factory()` step-closure (deterministic)."""
    try:
        ns: dict = {}
        exec(compile(src, "<closure>", "exec"), ns)          # noqa: S102
        make = ns.get(factory)
        if not callable(make):
            return None

        def oracle(n: int):
            step = make()
            v = None
            for _ in range(n + 1):
                v = step()
            return v
        return oracle if isinstance(oracle(0), (int, float)) and not isinstance(oracle(0), bool) else None
    except Exception:  # noqa: BLE001
        return None


def fold(src: str, factory: str = "make") -> core.StripResult:
    return core.fold_via_ai(closure_oracle(src, factory), "closure(unwrap)")


def adversarial_battery() -> dict:
    """★ a counter closure (step bumps captured state) — invisible as a raw unary oracle — folds after unwrap (linear,
    z3-gated); ★ an accumulator closure (running total of an arithmetic step) folds; ★ a closure stepping a chaotic map
    DECLINEs (z3 gate holds)."""
    counter = ("def make():\n    s = [0]\n    def step():\n        s[0] += 1\n        return s[0]\n    return step\n")
    accum = ("def make():\n    s = [0]\n    k = [0]\n    def step():\n        k[0] += 1\n        s[0] += k[0]\n        return s[0]\n    return step\n")
    chaos = ("def make():\n    x = [0.3]\n    def step():\n        x[0] = 3.9 * x[0] * (1 - x[0])\n        return int(x[0] * 1000)\n    return step\n")
    rc, ra, rx = fold(counter), fold(accum), fold(chaos)
    cases = {
        "counter_closure_folds": rc.folded,
        "accumulator_closure_folds": ra.folded,
        "chaotic_closure_declines": not rx.folded,               # ★ z3/precheck gate holds
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
