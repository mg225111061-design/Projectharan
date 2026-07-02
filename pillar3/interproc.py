"""
Pillar 3 · ROUND 3 #74 — interprocedural summaries (purity across the call graph) → EXACT memoization.
======================================================================================================
#68 proves purity for a SINGLE function and conservatively rejects ANY call to a non-builtin helper. That is
too weak for real code, which is split across functions. This computes a purity SUMMARY over the call graph by
a monotone fixpoint: a function is pure iff its body is pure GIVEN that its callees are already proven pure.
Start from the leaves, propagate upward until no change. A top-level function reachable to only-pure callees is
then provably pure ⇒ memoizable EXACT — even though it calls helpers. If any reachable callee is impure (I/O,
mutation, nondeterminism), the summary leaves the caller IMPURE ⇒ DECLINE (sound: a wrong "pure" is a bug).
"""
from __future__ import annotations

from typing import Callable, Dict, Optional, Tuple

import kernel_verdict as KV
from pillar3 import lifting as LF
from pillar3 import purity as PU


def purity_summary(functions: Dict[str, Callable]) -> Dict[str, Tuple[bool, str]]:
    """Monotone fixpoint: repeatedly mark a function pure if is_pure holds GIVEN the currently-proven-pure set.
    Returns {name: (pure, reason)}. Sound: a function only becomes pure once all the callees it relies on are."""
    pure_names: set = set()
    reasons: Dict[str, str] = {}
    changed = True
    while changed:
        changed = False
        for name, fn in functions.items():
            if name in pure_names:
                continue
            ok, why = PU.is_pure(fn, known_pure=pure_names)
            reasons[name] = why
            if ok:
                pure_names.add(name)
                changed = True
    return {name: (name in pure_names, reasons.get(name, "impure")) for name in functions}


def memoize_grade_ip(fn: Callable, fn_name: str, functions: Dict[str, Callable], make_input: Callable[[], tuple], *,
                     n: int, samples: int = 5, residual_iters: int = 0, floor: float = 1.20
                     ) -> Tuple[KV.Verdict, Optional[object]]:
    """Prove `fn_name` pure INTERPROCEDURALLY (whole reachable callee set pure), then memoize ⇒ EXACT. If the
    summary leaves it impure ⇒ DECLINE (some reachable callee has an effect)."""
    summary = purity_summary(functions)
    pure, why = summary.get(fn_name, (False, "not in call graph"))
    if not pure:
        return KV.decline(f"interprocedural purity NOT proven for {fn_name} ({why}) ⇒ DECLINE memoization", "memoize_ip"), None

    def naive(workload):
        return [fn(x) for x in workload]

    def memoized(workload):
        cache = {}
        out = []
        for x in workload:
            if x not in cache:
                cache[x] = fn(x)
            out.append(cache[x])
        return out

    wl = make_input()[0]
    if naive(wl) != memoized(wl):
        return KV.decline("memoized ≠ naive (purity summary was wrong) ⇒ DECLINE", "memoize_ip"), None
    rep = LF.measure_lift(lambda w: naive(w), lambda w: memoized(w), make_input, residual_iters, n=n, samples=samples)
    if not rep.beats(floor):
        v = KV.decline(f"interprocedurally pure but no whole-program win (×{rep.whole_program_ratio:.2f}) ⇒ DECLINE", "memoize_ip")
        v.report = rep
        return v, rep
    cert = KV.Cert(KV.EXACT, "interprocedural_purity_memoization", passed=True, check_cost="call-graph purity fixpoint",
                   detail=f"{fn_name} pure across its call graph ({why}); memoization behavior-preserving ⇒ EXACT")
    v = KV.exact(memoized, "memoize_ip", str(rep), cert)
    v.report = rep
    return v, rep


# ── a PURE call graph (top-level calls helpers, all pure) and an IMPURE one (a reachable helper does I/O) ───
def _h_square(x):
    return x * x


def _h_poly(x):
    return _h_square(x) - 3 * x + 7                          # calls _h_square (pure)


def compute_pure(x):
    s = 0
    for i in range(250):
        s += _h_poly(x + i) % 1000                          # calls _h_poly → _h_square (whole graph pure)
    return s


PURE_GRAPH = {"_h_square": _h_square, "_h_poly": _h_poly, "compute_pure": compute_pure}


def _h_io(x):
    print(x)                                                # I/O ⇒ impure
    return x * x


def compute_impure(x):
    return sum(_h_io(x + i) for i in range(8))              # reaches an impure helper


IMPURE_GRAPH = {"_h_io": _h_io, "compute_impure": compute_impure}


_WL_CACHE: dict = {}


def make_workload(unique: int = 60, reps: int = 5000):
    if (unique, reps) not in _WL_CACHE:
        import random as _rnd
        rng = _rnd.Random(45)
        _WL_CACHE[(unique, reps)] = ([rng.randrange(unique) for _ in range(reps)],)
    return _WL_CACHE[(unique, reps)]
