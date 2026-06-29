"""
§AL §1.5 — OBJECT-STATE EXTRACT: a recurrence hidden behind object fields / mutable state, advanced by METHOD CALLS.
================================================================================================================
`c = C(); c.step(); c.step(); …` — the sequence lives in `c.<field>` and is produced by method calls, not f(n). The
strip extracts the state machine into the unary oracle `oracle(n) = the method's return after n+1 calls on a FRESH
instance`; §AI + z3 dispose. ★ faithful (it drives the real object); a wrong extraction can't pass the z3 gate.
"""
from __future__ import annotations

from typing import Callable, Optional

from recall import core


def object_oracle(src: str, cls: str = "C", method: str = "step") -> Optional[Callable[[int], object]]:
    """exec the source; return oracle(n) = return of the (n+1)-th `method()` call on a FRESH `cls()` instance."""
    try:
        ns: dict = {}
        exec(compile(src, "<object>", "exec"), ns)           # noqa: S102
        klass = ns.get(cls)
        if klass is None:
            return None

        def oracle(n: int):
            obj = klass()
            m = getattr(obj, method)
            v = None
            for _ in range(n + 1):
                v = m()
            return v
        return oracle if isinstance(oracle(0), (int, float)) and not isinstance(oracle(0), bool) else None
    except Exception:  # noqa: BLE001
        return None


def fold(src: str, cls: str = "C", method: str = "step") -> core.StripResult:
    return core.fold_via_ai(object_oracle(src, cls, method), "object_state(extract)")


def adversarial_battery() -> dict:
    """★ a stateful accumulator object (step() advances a field) — invisible as a raw oracle — folds after extraction
    (z3-gated); ★ a counter object folds; ★ an object stepping a hash/random field DECLINEs (z3 gate holds)."""
    accum = ("class C:\n    def __init__(self):\n        self.s = 0\n        self.k = 0\n    def step(self):\n"
             "        self.k += 1\n        self.s += self.k\n        return self.s\n")
    counter = ("class C:\n    def __init__(self):\n        self.s = 0\n    def step(self):\n        self.s += 2\n        return self.s\n")
    rnd = ("class C:\n    def __init__(self):\n        self.n = 0\n    def step(self):\n        import hashlib\n"
           "        self.n += 1\n        return int.from_bytes(hashlib.sha256(str(self.n).encode()).digest()[:6], 'big')\n")
    ra, rc, rr = fold(accum), fold(counter), fold(rnd)
    cases = {
        "accumulator_object_folds": ra.folded,
        "counter_object_folds": rc.folded,
        "random_object_declines": not rr.folded,                 # ★ z3/precheck gate holds (no false EXACT)
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
