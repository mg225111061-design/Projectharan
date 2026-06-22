"""
Pillar 3 · ROUND 1 #5 — PARTIAL EVALUATION / specialization on fixed inputs (EXACT, Z3-proven).
================================================================================================
When part of a function's input is fixed (known ahead of the hot loop), the generic code re-does, on EVERY
call, work that depends only on the fixed part — opcode dispatch, structure walks, zero-weight multiplies.
Partial evaluation (Futamura) splits the computation: do the fixed-dependent work ONCE at specialization time,
emit a residual that does only the variable-dependent work. The residual is EQUAL to the generic function with
those inputs fixed — proven here by bounded Z3 translation validation (the same engine as lifting/equiv) — so
it is graded EXACT (not PROBABILISTIC), measured whole-program (ratio ≤ ceiling). A mis-specialization (a wrong
residual) is caught by the differential oracle AND Z3-refuted ⇒ DECLINE (the moat).

  • interpreter specialization (1st Futamura projection): a generic AST interpreter, specialized on a FIXED
    program, becomes a straight-line residual with all opcode dispatch resolved at specialization time.
  • sparse linear-map specialization: dot(weights, x) with FIXED weights drops the zero terms and the loop,
    emitting only the surviving `Σ wᵢ·xᵢ` — the generic form pays for every (incl. zero) weight, every call.
"""
from __future__ import annotations

import random as _rnd
from typing import Callable, List, Tuple

import z3

from pillar3 import lifting as LF


# ── 1) interpreter specialization — the FIRST FUTAMURA PROJECTION (specialize interp w.r.t. a fixed program) ─
# AST nodes: ("const", v) | ("var", i) | ("add"|"sub"|"mul", left, right).
def interp(node, env):
    """Generic interpreter — walks the AST and DISPATCHES on the opcode on EVERY evaluation (the overhead PE
    removes). Runs symbolically (z3 exprs) and numerically (ints) on the same code."""
    t = node[0]
    if t == "const":
        return node[1]
    if t == "var":
        return env[node[1]]
    if t == "add":
        return interp(node[1], env) + interp(node[2], env)
    if t == "sub":
        return interp(node[1], env) - interp(node[2], env)
    if t == "mul":
        return interp(node[1], env) * interp(node[2], env)
    raise ValueError(f"bad node {node!r}")


def specialize(node) -> Callable:
    """Partial-evaluate interp w.r.t. a FIXED program: walk the AST ONCE (here), emit a residual closure that
    computes directly with NO per-evaluation opcode dispatch. residual(env) ≡ interp(node, env) by construction
    (proven by Z3 over symbolic env)."""
    t = node[0]
    if t == "const":
        v = node[1]
        return lambda env: v
    if t == "var":
        i = node[1]
        return lambda env: env[i]
    if t == "add":
        l, r = specialize(node[1]), specialize(node[2])
        return lambda env: l(env) + r(env)
    if t == "sub":
        l, r = specialize(node[1]), specialize(node[2])
        return lambda env: l(env) - r(env)
    if t == "mul":
        l, r = specialize(node[1]), specialize(node[2])
        return lambda env: l(env) * r(env)
    raise ValueError(f"bad node {node!r}")


def specialize_wrong(node) -> Callable:
    """A BROKEN partial evaluator: mis-compiles 'mul' as 'add' (a wrong residual). Differential + Z3 catch it."""
    t = node[0]
    if t == "const":
        v = node[1]
        return lambda env: v
    if t == "var":
        i = node[1]
        return lambda env: env[i]
    if t == "add":
        l, r = specialize_wrong(node[1]), specialize_wrong(node[2])
        return lambda env: l(env) + r(env)
    if t == "sub":
        l, r = specialize_wrong(node[1]), specialize_wrong(node[2])
        return lambda env: l(env) - r(env)
    if t == "mul":
        l, r = specialize_wrong(node[1]), specialize_wrong(node[2])
        return lambda env: l(env) + r(env)                  # BUG: 'mul' compiled as 'add'
    raise ValueError(f"bad node {node!r}")


def _build_ast():
    """A fixed program in 4 variables, deepened so opcode dispatch (not arithmetic) dominates the runtime."""
    V = lambda i: ("var", i)
    C = lambda v: ("const", v)
    A = lambda a, b: ("add", a, b)
    S = lambda a, b: ("sub", a, b)
    M = lambda a, b: ("mul", a, b)
    ast = S(M(S(A(M(V(0), V(1)), V(2)), V(3)), A(V(0), M(V(1), V(2)))), A(M(V(3), V(3)), V(0)))
    for _ in range(4):
        ast = A(M(ast, V(1)), S(ast, C(1)))
    return ast


_AST = _build_ast()


def interp_fixed(env):
    return interp(_AST, env)


_specialized = specialize(_AST)
_specialized_wrong = specialize_wrong(_AST)


def _sym_env(n: int) -> tuple:
    return ([z3.Int(f"v{i}") for i in range(n)],)


_ENV_CACHE: dict = {}


def _make_env(_size_ignored=4):
    if "env" not in _ENV_CACHE:
        rng = _rnd.Random(23)
        _ENV_CACHE["env"] = [rng.randrange(-20, 20) for _ in range(4)]
    return (_ENV_CACHE["env"],)


# ── 2) sparse linear-map specialization — dot(weights, x) with FIXED weights → only the surviving terms ─────
def dot_generic(weights, x):
    """Generic dot product — pays for EVERY weight (including zeros) on EVERY call."""
    s = 0
    for i in range(len(weights)):
        s = s + weights[i] * x[i]
    return s


def specialize_dot(weights) -> Callable:
    """Partial-evaluate dot w.r.t. FIXED weights: keep only nonzero terms, bake the constants, drop the loop.
    residual(x) ≡ dot(weights, x) (proven by Z3 over symbolic x)."""
    terms = [(i, int(w)) for i, w in enumerate(weights) if w != 0]

    def residual(x):
        s = 0
        for i, w in terms:                                  # only the surviving terms; no zero multiplies
            s = s + w * x[i]
        return s
    return residual


def specialize_dot_wrong(weights) -> Callable:
    """BROKEN: also drops a NONZERO term (an over-aggressive 'dead-weight' elimination) ⇒ wrong residual."""
    terms = [(i, int(w)) for i, w in enumerate(weights) if w != 0]
    terms = terms[:-1] if len(terms) > 1 else terms         # BUG: drops a live term

    def residual(x):
        s = 0
        for i, w in terms:
            s = s + w * x[i]
        return s
    return residual


# a sparse fixed weight vector (mostly zeros) — the generic loop wastes time on every zero, every call
_WEIGHTS = [0, 3, 0, 0, 5, 0, 0, 0, 2, 0, 0, 7, 0, 0, 0, 0, 4, 0, 0, 6, 0, 0, 0, 0, 9, 0, 0, 0, 0, 0, 0, 8]
_dot_specialized = specialize_dot(_WEIGHTS)
_dot_specialized_wrong = specialize_dot_wrong(_WEIGHTS)


def dot_fixed(x):
    return dot_generic(_WEIGHTS, x)


def _sym_x(n: int) -> tuple:
    return ([z3.Int(f"x{i}") for i in range(n)],)


_X_CACHE: dict = {}


def _make_x(_size_ignored=None):
    if "x" not in _X_CACHE:
        rng = _rnd.Random(29)
        _X_CACHE["x"] = [rng.randrange(-50, 50) for _ in range(len(_WEIGHTS))]
    return (_X_CACHE["x"],)


_W = len(_WEIGHTS)


# ── catalog: each partial-eval as an identity-lift (spec = original) ⇒ EXACT iff Z3 proves residual≡generic ─
def catalog() -> List[LF.Lift]:
    return [
        LF.Lift("partial_eval_interpreter", "partial_eval", interp_fixed, interp_fixed, _specialized,
                _sym_env, lambda: _make_env(4), residual_iters=0, sizes=(4, 5), n=0, floor=1.10),
        LF.Lift("partial_eval_sparse_dot", "partial_eval", dot_fixed, dot_fixed, _dot_specialized,
                _sym_x, lambda: _make_x(), residual_iters=0, sizes=(_W, _W), n=_W, floor=1.10),
    ]


def wrong_variants() -> List[LF.Lift]:
    return [
        LF.Lift("partial_eval_interpreter_WRONG", "partial_eval", interp_fixed, interp_fixed, _specialized_wrong,
                _sym_env, lambda: _make_env(4), residual_iters=0, sizes=(4, 5), n=0),
        LF.Lift("partial_eval_sparse_dot_WRONG", "partial_eval", dot_fixed, dot_fixed, _dot_specialized_wrong,
                _sym_x, lambda: _make_x(), residual_iters=0, sizes=(_W, _W), n=_W),
    ]
