"""
Pillar 3 · ROUND 1 #2 — egg-style EQUALITY SATURATION wired into Pillar-3 (EXACT algebraic simplification).
============================================================================================================
A hot per-element expression can be algebraically wasteful (2·x + 3·x + 0·x + x·1 …). Equality saturation
(equality_saturation.optimize) explores all rewrites in an e-graph, extracts the cheapest equivalent term, and
— crucially — CERTIFIES the rewrite with Z3 (∀ vars: term ≡ rewrite) before reporting it (UNSOUND_BLOCKED if a
rewrite is not provably equal). This wires that proven optimizer into a Pillar-3 recognizer: it compiles the
wasteful expression and its Z3-certified simpler form to per-element evaluators, measures the whole-program win
(fewer operations per element), and grades EXACT. A proposed rewrite that is NOT Z3-equivalent ⇒ DECLINE (the
moat) — exactly the kernel check the e-graph already enforces.
"""
from __future__ import annotations

from typing import Callable, List, Optional, Tuple

import z3

import equality_saturation as ES
import kernel_verdict as KV
from pillar3 import lifting as LF


def compile_term(t) -> Callable:
    """Compile a Term ( ("const",v) | ("var",n) | ("+"/"*", l, r) ) to a closure env->value (no per-eval walk)."""
    k = t[0]
    if k == "const":
        v = t[1]
        return lambda env: v
    if k == "var":
        n = t[1]
        return lambda env: env[n]
    l, r = compile_term(t[1]), compile_term(t[2])
    if k == "+":
        return lambda env: l(env) + r(env)
    return lambda env: l(env) * r(env)                       # "*"


def _z3_equiv(term, other) -> bool:
    env = {}
    for v in ES._vars(term, set()) | ES._vars(other, set()):
        env[v] = z3.Int(v)
    s = z3.Solver()
    s.add(ES._to_z3(term, env) != ES._to_z3(other, env))
    return s.check() == z3.unsat


def egraph_grade(term, make_input: Callable[[], tuple], *, n: int, samples: int = 5, residual_iters: int = 0,
                 floor: float = 1.10, force_opt=None, max_iters: int = 8) -> Tuple[KV.Verdict, Optional[object]]:
    """Saturate→extract→Z3-certify the simpler form, compile both, measure the whole-program win, grade EXACT.
    `force_opt` (a proposed rewrite) is Z3-checked directly — a non-equivalent rewrite ⇒ DECLINE (the moat).
    max_iters is bounded (the e-graph grows combinatorially under distribution); whatever is extracted is
    Z3-certified equivalent regardless, so a bounded saturation only affects the GAIN, never correctness."""
    if force_opt is not None:
        best = force_opt
        if not _z3_equiv(term, best):                        # the e-graph's own kernel check, as the moat
            return KV.decline("e-graph: proposed rewrite is NOT Z3-equivalent ⇒ DECLINE", "egraph"), None
        before, after = ES.term_size(term), ES.term_size(best)
    else:
        v = ES.optimize(term, max_iters)
        if v.status != "OPTIMIZED":                          # NO_GAIN or UNSOUND_BLOCKED ⇒ nothing to ship
            return KV.decline(f"e-graph: {v.status} ({v.detail}) ⇒ DECLINE", "egraph"), None
        best, before, after = v.optimized, v.before, v.after
    fn_n, fn_o = compile_term(term), compile_term(best)
    naive = lambda arr: [fn_n(e) for e in arr]
    opt = lambda arr: [fn_o(e) for e in arr]
    rep = LF.measure_lift(lambda a: naive(a), lambda a: opt(a), make_input, residual_iters, n=n, samples=samples)
    if not rep.beats(floor):
        v = KV.decline(f"e-graph simpler form ({before}→{after} nodes) but no whole-program win "
                       f"(×{rep.whole_program_ratio:.2f}) ⇒ DECLINE", "egraph")
        v.report = rep
        return v, rep
    cert = KV.Cert(KV.EXACT, "egraph_z3_equiv", passed=True, check_cost="Z3 ∀-vars",
                   detail=f"equality saturation; Z3-proven term≡rewrite; {before}→{after} nodes")
    vv = KV.exact(best, "egraph", str(rep), cert)
    vv.report = rep
    return vv, rep


# ── a wasteful expression that collapses to k·x, and the inputs over which to evaluate it ───────────────
def build_wasteful(k_terms: int = 10):
    """Σ over i of (x·i) plus identity noise (x·1, 0·x) — all collapses to (x · K). Big before, 3 nodes after."""
    V = lambda nm: ("var", nm)
    C = lambda v: ("const", v)
    A = lambda a, b: ("+", a, b)
    M = lambda a, b: ("*", a, b)
    t = M(V("x"), C(1))
    for i in range(2, k_terms + 1):
        t = A(t, M(V("x"), C(i)))
    t = A(t, M(C(0), V("x")))                                # + 0·x  (identity noise)
    t = A(t, M(V("x"), C(1)))                                # + x·1
    return t


_W = build_wasteful(5)                                       # 27 nodes → collapses to (x · 16); fast to saturate
_WRONG = ("*", ("var", "x"), ("const", 999))                 # a deliberately non-equivalent "simplification"

_ENV_CACHE: dict = {}


def make_expr_input(n: int = 40000):
    if n not in _ENV_CACHE:
        import random as _rnd
        rng = _rnd.Random(57)
        _ENV_CACHE[n] = ([{"x": rng.randrange(-1000, 1000)} for _ in range(n)],)
    return _ENV_CACHE[n]
