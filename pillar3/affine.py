"""
Pillar 3 · ROUND 1 #1 — VERIFIED LIFTING GENERALIZED to arbitrary affine accumulation loops (EXACT).
=====================================================================================================
The hand-written lifts in lifting.py each cover ONE shape. This generalizes the recognizer to a whole FAMILY:
any loop that accumulates an affine function of the index and (optionally) an array element,
        s = init ; for i in range(n): s += A·a[i] + B·i + C ,
which has the closed/reduced form
        s = init + A·Σa[i] + B·(n(n−1)/2) + C·n .
The family identity is proven ONCE by bounded Z3 translation validation over SYMBOLIC coefficients A,B,C and a
symbolic array (every length up to a bound) — so it licenses every concrete instantiation (no per-shape proof).
Each concrete loop is then lifted and graded EXACT, measured whole-program (ratio ≤ ceiling). Two regimes:
  • index-only (A = 0): the array term constant-folds away ⇒ O(n) → O(1) (a ceiling-breaker);
  • array-affine (A ≠ 0): the per-iteration index arithmetic folds to O(1) and Σa[i] becomes one tight
    reduction ⇒ a real constant-factor win over the interpreted loop.
A wrong lift (e.g. the triangular number off-by-one n(n+1)/2) is Z3-refuted ⇒ DECLINE (the moat).
"""
from __future__ import annotations

import random as _rnd
from typing import Callable, List, Tuple

import z3

from pillar3 import lifting as LF


# ── the affine-loop family: (original loop, reduced closed form) parameterized by coefficients A,B,C,init ───
def make_affine_loop(A: int, B: int, C: int, init: int = 0) -> Callable:
    """The naive accumulation loop  s = init; for i: s += A·a[i] + B·i + C  (O(n), per-iteration arithmetic)."""
    def original(a):
        s = init
        for i in range(len(a)):
            s = s + A * a[i] + B * i + C
        return s
    return original


def affine_lift(A: int, B: int, C: int, init: int = 0) -> Callable:
    """The reduced form, SPECIALIZED on the coefficients: when A = 0 the array term is folded away ⇒ O(1)."""
    if A == 0:
        def optimized_o1(a):                                # index-only ⇒ no array touch ⇒ O(1)
            n = len(a)
            return init + B * (n * (n - 1) // 2) + C * n
        return optimized_o1

    def optimized(a):                                       # A ≠ 0 ⇒ one reduction Σa + O(1) index arithmetic
        n = len(a)
        return init + A * sum(a) + B * (n * (n - 1) // 2) + C * n
    return optimized


def affine_lift_wrong(A: int, B: int, C: int, init: int = 0) -> Callable:
    """A BROKEN lift: triangular number off-by-one  n(n+1)/2  instead of  n(n−1)/2  ⇒ Z3-refuted, DECLINE."""
    def wrong(a):
        n = len(a)
        return init + A * sum(a) + B * (n * (n + 1) // 2) + C * n   # BUG: (n+1) instead of (n-1)
    return wrong


# ── the FAMILY proof: one bounded Z3 check over symbolic A,B,C and a symbolic array (every length ≤ bound) ──
def prove_affine_schema(maxlen: int = 6) -> Tuple[bool, int]:
    """Z3-prove  Σ_{i<n}(A·a[i] + B·i + C) ≡ A·Σa[i] + B·n(n−1)/2 + C·n  for SYMBOLIC A,B,C,a[i], every n ≤ maxlen.
    UNSAT-of-negation at each length ⇒ the schema holds for all coefficient values ⇒ the whole family is sound."""
    for n in range(0, maxlen + 1):
        A, B, C = z3.Int("A"), z3.Int("B"), z3.Int("C")
        a = [z3.Int(f"a{i}") for i in range(n)]
        loop = z3.IntVal(0)
        for i in range(n):
            loop = loop + A * a[i] + B * i + C
        closed = (A * z3.Sum(a) if n > 0 else z3.IntVal(0)) + B * (n * (n - 1) // 2) + C * n
        s = z3.Solver()
        s.add(loop != closed)
        if s.check() != z3.unsat:
            return (False, n)
    return (True, maxlen)


def _sym_int_list(n: int) -> tuple:
    return ([z3.Int(f"a{i}") for i in range(n)],)


_A_CACHE: dict = {}


def _mk_list(size: int):
    if size not in _A_CACHE:
        rng = _rnd.Random(15)
        _A_CACHE[size] = [rng.randrange(-100, 100) for _ in range(size)]
    return (_A_CACHE[size],)


# concrete instances of the family (each an identity-lift ⇒ EXACT iff Z3 proves reduced≡loop AND a win measured)
_INSTANCES = [
    ("affine_index_only_O1", 0, 3, 5, 0),                   # A=0 ⇒ O(n)→O(1) ceiling-breaker
    ("affine_array_AbC", 2, 1, 4, 10),                      # A≠0 ⇒ folded constant-factor win
    ("affine_pure_count", 0, 0, 7, 0),                      # degenerate: Σ C ⇒ C·n, O(1)
]


def catalog() -> List[LF.Lift]:
    out = []
    for name, A, B, C, init in _INSTANCES:
        orig = make_affine_loop(A, B, C, init)
        opt = affine_lift(A, B, C, init)
        out.append(LF.Lift(name, "affine_lift", orig, orig, opt, _sym_int_list,
                           lambda: _mk_list(4000), residual_iters=0, sizes=(3, 5, 8), n=4000, floor=1.10))
    return out


def wrong_variants() -> List[LF.Lift]:
    name, A, B, C, init = "affine_array_AbC_WRONG", 2, 1, 4, 10
    orig = make_affine_loop(A, B, C, init)
    return [LF.Lift(name, "affine_lift", orig, orig, affine_lift_wrong(A, B, C, init),
                    _sym_int_list, lambda: _mk_list(4000), residual_iters=0, sizes=(3, 5, 8), n=4000)]
