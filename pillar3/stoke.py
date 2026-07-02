"""
Pillar 3 · ROUND 1 #4 — STOKE-style stochastic superoptimization wired into Pillar-3 (PROBABILISTIC).
=====================================================================================================
superopt.superopt is a STOKE-spirit superoptimizer: it searches an e-graph for the lowest-COST equivalent of a
hot straight-line expression and — before returning it — VERIFIES the rewrite by Schwartz–Zippel (agreement at
many random points over a large prime field; an unverified rewrite is DEFERred, never returned). Because the
equivalence is established by RANDOMIZED testing (not a proof), the honest grade is PROBABILISTIC with the
Schwartz–Zippel error bound as δ — NEVER EXACT (Constitution Rule 3). This wires that proven search into a
Pillar-3 recognizer: compile the wasteful expression and its verified cheaper form, measure the whole-program
win, grade PROBABILISTIC(δ). STOKE's deployment model — expensive build-time SEARCH, O(1) runtime lookup of the
verified optimum — is exercised too. A wrong rewrite ⇒ Schwartz–Zippel refutes ⇒ DECLINE (the moat).
"""
from __future__ import annotations

from typing import Callable, Optional, Tuple

import kernel_verdict as KV
import superopt as SO
from pillar3 import lifting as LF


def compile_term(t) -> Callable:
    """Compile a superopt Term ( ("const",v) | ("var",n) | ("+"/"-"/"*", l, r) ) to a closure env->value."""
    k = t[0]
    if k == "const":
        v = t[1]
        return lambda e: v
    if k == "var":
        n = t[1]
        return lambda e: e[n]
    l, r = compile_term(t[1]), compile_term(t[2])
    if k == "+":
        return lambda e: l(e) + r(e)
    if k == "-":
        return lambda e: l(e) - r(e)
    return lambda e: l(e) * r(e)                             # "*"


# the Schwartz–Zippel bound underflows float to 0.0; floor it to a representable positive so the grade reads
# clearly PROBABILISTIC (a randomized check, however strong, is never EXACT) — and never understate it as 0.
_DELTA_FLOOR = 1e-300


def stoke_grade(term, make_input: Callable[[], tuple], *, n: int, samples: int = 5, residual_iters: int = 0,
                floor: float = 1.10, iters: int = 10, force_opt=None) -> Tuple[KV.Verdict, Optional[object]]:
    """Run the STOKE search, compile both forms, measure the whole-program win, grade PROBABILISTIC(δ) by the
    Schwartz–Zippel bound. `force_opt` is verified directly — a non-equivalent rewrite ⇒ DECLINE (the moat)."""
    if force_opt is not None:
        ok, eps = SO.verify_equiv(term, force_opt)
        if not ok:
            return KV.decline("STOKE: proposed rewrite FAILS Schwartz–Zippel equivalence ⇒ DECLINE", "stoke"), None
        best = force_opt
    else:
        r = SO.superopt(term, iters=iters)
        if r.status != "OPTIMIZED" or not r.verified:        # NOCHANGE / DEFER (incl. failed verification)
            return KV.decline(f"STOKE: {r.status} ({r.detail}) ⇒ DECLINE", "stoke"), None
        best, eps = r.optimized, r.error_prob
    fn_n, fn_o = compile_term(term), compile_term(best)
    naive = lambda arr: [fn_n(e) for e in arr]
    opt = lambda arr: [fn_o(e) for e in arr]
    rep = LF.measure_lift(lambda a: naive(a), lambda a: opt(a), make_input, residual_iters, n=n, samples=samples)
    if not rep.beats(floor):
        v = KV.decline(f"STOKE cheaper form but no whole-program win (×{rep.whole_program_ratio:.2f}) ⇒ DECLINE", "stoke")
        v.report = rep
        return v, rep
    delta = max(float(eps), _DELTA_FLOOR)
    cert = KV.Cert(KV.PROBABILISTIC, "stoke_schwartz_zippel", passed=True, check_cost="24 random points / 2^61-1 field",
                   delta=delta, detail="STOKE search; Schwartz–Zippel-verified equivalent (randomized, not a proof) "
                                       f"⇒ PROBABILISTIC δ≤{delta:.0e}; never EXACT")
    v = KV.probabilistic(best, "stoke", str(rep), cert)
    v.report = rep
    return v, rep


# ── a wasteful ring expression STOKE reduces (6x + 8 from a 12-cost form), and inputs to evaluate it ────
def build_wasteful_ring():
    V = lambda nm: ("var", nm)
    C = lambda v: ("const", v)
    A = lambda a, b: ("+", a, b)
    M = lambda a, b: ("*", a, b)
    # 2x + 3x + 0·x + (2·4) + x   ≡   6x + 8
    return A(M(V("x"), C(2)), A(M(V("x"), C(3)), A(M(C(0), V("x")), A(M(C(2), C(4)), V("x")))))


_W = build_wasteful_ring()
_WRONG = ("*", ("var", "x"), ("const", 7))                   # 7x ≠ 6x+8 — Schwartz–Zippel refutes

_ENV_CACHE: dict = {}


def make_ring_input(n: int = 80000):
    if n not in _ENV_CACHE:
        import random as _rnd
        rng = _rnd.Random(59)
        _ENV_CACHE[n] = ([{"x": rng.randrange(-1000, 1000)} for _ in range(n)],)
    return _ENV_CACHE[n]


def runtime_cache_hit(term=None) -> bool:
    """STOKE deployment: warm the build-time cache with the verified optimum, then confirm an O(1) runtime hit."""
    term = term or _W
    SO.warm_runtime_cache([term])
    _opt, hit = SO.optimize_runtime(term)
    return hit
