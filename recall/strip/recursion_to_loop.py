"""
§AL §1.1 — RECURSION → LOOP: defeat recursion/CPS/trampoline disguises by MEMOIZING into a feasible unary oracle.
================================================================================================================
A naive recursive `fib(n)=fib(n-1)+fib(n-2)` is O(2ⁿ) — probing fib(0..47) is INFEASIBLE, so the §AI black-box never
even sees it. The strip rebinds the recursive name to a MEMOIZED version (semantics-preserving for a pure function),
collapsing O(2ⁿ)→O(n) so the oracle is probeable; §AI + z3 then dispose. ★ A wrong memoization is impossible (caching
a pure function preserves it), and z3 still gates ⇒ precision unchanged.
"""
from __future__ import annotations

from typing import Callable, Optional

from recall import core


def memoized_oracle(src: str, entry: str) -> Optional[Callable[[int], object]]:
    """exec the source, rebind the entry to an lru_cache wrapper so internal recursive calls hit the cache (O(2ⁿ)→O(n))."""
    import functools
    try:
        ns: dict = {}
        exec(compile(src, "<recursion>", "exec"), ns)        # noqa: S102 — deterministic corpus/sample code
        fn = ns.get(entry)
        if not callable(fn):
            return None
        cached = functools.lru_cache(maxsize=None)(fn)
        ns[entry] = cached                                    # ★ recursive calls now resolve to the memoized version
        return cached
    except Exception:  # noqa: BLE001
        return None


def fold(src: str, entry: str = "f") -> core.StripResult:
    fn = memoized_oracle(src, entry)
    return core.fold_via_ai(fn, "recursion(memoized)")


def adversarial_battery() -> dict:
    """★ a NAIVE exponential Fibonacci (infeasible to probe raw) folds after memoization (linear_recurrence, z3-gated);
    ★ a recursive but non-C-finite function (digit-sum-by-recursion base-10) stays DECLINE (z3 gate holds — no false
    EXACT); ★ memoization preserves semantics (the folded recurrence matches the naive function)."""
    naive_fib = "def f(n):\n    return n if n < 2 else f(n-1) + f(n-2)\n"
    r = fold(naive_fib)
    # a recursive digit-sum (base-10) — recursive form, but not C-finite/holonomic ⇒ must DECLINE
    rec_ds = "def f(n):\n    return 0 if n == 0 else (n % 10) + f(n // 10)\n"
    d = fold(rec_ds)
    # semantics check: the memoized oracle equals the naive function on small n (sanity)
    mo = memoized_oracle(naive_fib, "f")
    naive_ref = [0, 1, 1, 2, 3, 5, 8, 13]
    sem_ok = mo is not None and [mo(i) for i in range(8)] == naive_ref
    cases = {
        "naive_exp_fib_folds_after_memo": r.folded and r.structure_class == "linear_recurrence",
        "recursive_nonfoldable_declines": not d.folded,          # ★ z3 gate holds (no false EXACT)
        "memoization_preserves_semantics": sem_ok,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
