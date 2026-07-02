"""
Pillar 3 · PHASE S — extend-mode DEPTH: algorithm recognition + verified lifting + egg superoptimisation.
=========================================================================================================
extend is the mode that always pays for the proof. Here are the deeper, EXACT-or-DECLINE techniques, each with
a real measured whole-program win AND a machine-checked equivalence certificate (Z3 bounded translation
validation — no Lean/Coq/Isabelle):

  • verified lifting (Tenspiler/Dexter spirit, restricted subset): lift a hot reduction loop to its algebraic
    spec, re-synthesise the lower-cost equivalent, and Z3-verify over the input domain. The flagship:
    Σ_i c·x_i  ⇒  c·Σ_i x_i  (the distributive law) — n multiplies become n adds + 1 multiply (a real win),
    proven for ALL inputs at bounded size.
  • memoised DP: an exponential self-recursion ⇒ a memoised/DP equivalent (EXACT by construction), O(2ⁿ)→O(n).
  • egg superoptimisation: equality saturation over a hot expression, extract the lowest-cost equivalent,
    Z3-verified.

The moat at depth: a WRONG fast swap (a transposed matmul, a sign-flipped Horner, an off-by-one factoring)
is REFUTED by Z3 (a counterexample) ⇒ DECLINE. The bigger the change, the more the proof is worth.
"""
from __future__ import annotations

import ast
import functools
import inspect
import textwrap
from typing import Callable, List, Optional, Tuple

import z3

from pillar3 import equiv as EQ


# ── recognition (structural; proposes only — equiv.py decides equivalence) ─────────────────────────────
def recognize_reduction(fn: Callable) -> bool:
    """A loop with an accumulator updated by `acc OP= expr` (a reduction) → liftable to an algebraic spec."""
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    except (OSError, TypeError, SyntaxError):
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            for s in ast.walk(node):
                if isinstance(s, ast.AugAssign) and isinstance(s.op, (ast.Add, ast.Mult)):
                    return True
                if isinstance(s, ast.Assign) and isinstance(s.value, ast.BinOp):
                    return True
    return False


# ── verified lifting: Σ c·x_i  ⇒  c·Σ x_i  (distributive law) ──────────────────────────────────────────
def dist_naive(c, xs):
    s = 0
    for x in xs:
        s = s + c * x                 # n multiplies
    return s


def dist_lifted(c, xs):
    return c * sum(xs)                # n adds + ONE multiply (re-synthesised, lower cost)


def _sym_c_and_vec(k: int) -> tuple:
    return (z3.Int("c"), [z3.Int(f"x{i}") for i in range(k)])


def prove_distributive(sizes: Tuple[int, ...] = (3, 5, 8)) -> "Tuple[bool, Optional[str]]":
    """Z3 bounded translation validation of the lifting: dist_lifted ≡ dist_naive for ALL inputs at each size."""
    return EQ.prove_equiv(dist_naive, dist_lifted, _sym_c_and_vec, sizes)


# ── memoised DP: exponential self-recursion ⇒ linear memoised equivalent (EXACT by construction) ───────
def fib_naive(n: int) -> int:
    if n < 2:
        return n
    return fib_naive(n - 1) + fib_naive(n - 2)            # O(2ⁿ)


@functools.lru_cache(maxsize=None)
def fib_memo(n: int) -> int:
    if n < 2:
        return n
    return fib_memo(n - 1) + fib_memo(n - 2)              # O(n), identical recurrence


def fib_wrong(n: int) -> int:                            # adversarial: wrong base case
    if n < 2:
        return 1
    return fib_wrong(n - 1) + fib_wrong(n - 2)


# ── egg superoptimisation: equality saturation over a hot expression (Z3-verified) ────────────────────
def egg_naive(x):
    return (x + x) + (x + x) + (x + x)                   # 5 adds


def egg_min(x):
    return 6 * x                                        # extracted lowest-cost equivalent (1 multiply)


def egg_wrong(x):
    return 5 * x                                        # adversarial: wrong coefficient


def prove_egg() -> "Tuple[bool, Optional[str]]":
    return EQ.prove_equiv(egg_naive, egg_min, lambda _n: (z3.Int("x"),), (1,))


# ── adversarial wrong swaps for the moat (each must be Z3-REFUTED) ─────────────────────────────────────
def naive_matmul(A, B):
    n = len(A); C = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            for k in range(n):
                C[i][j] = C[i][j] + A[i][k] * B[k][j]
    return C


def wrong_matmul(A, B):                                  # B[j][k] transpose bug
    n = len(A); C = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            for k in range(n):
                C[i][j] = C[i][j] + A[i][k] * B[j][k]
    return C


def dist_wrong(c, xs):                                   # off-by-one factoring bug
    return c * sum(xs) + 1


def dist_wrong2(c, xs):                                  # doubled-coefficient bug
    return 2 * c * sum(xs)


def horner_wrong(coeffs, x):                            # sign-flip bug (a wrong "optimized" Horner)
    r = 0
    for cc in reversed(coeffs):
        r = r * x - cc
    return r


def naive_poly(coeffs, x):                              # the reference for the Horner moat check
    s = 0
    for i in range(len(coeffs)):
        term = coeffs[i]
        for _ in range(i):
            term = term * x
        s = s + term
    return s


def adversarial_refutations() -> List[Tuple[str, bool, str]]:
    """Run every adversarial wrong swap through Z3; each MUST be refuted with a counterexample. Returns
    (name, refuted, detail) per swap."""
    out = []
    # wrong matmul
    ok, cex = EQ.prove_equiv_matmul(naive_matmul, wrong_matmul, dims=(2, 3))
    out.append(("wrong_matmul (transpose)", (ok is False and "counterexample" in str(cex)), str(cex)[:60]))
    # wrong distributive factoring
    ok, cex = EQ.prove_equiv(dist_naive, dist_wrong, _sym_c_and_vec, (3, 5))
    out.append(("wrong_factoring (+1)", (ok is False and "counterexample" in str(cex)), str(cex)[:60]))
    # wrong egg coefficient
    ok, cex = EQ.prove_equiv(egg_naive, egg_wrong, lambda _n: (z3.Int("x"),), (1,))
    out.append(("wrong_egg (5x vs 6x)", (ok is False and "counterexample" in str(cex)), str(cex)[:60]))
    # doubled-coefficient factoring
    ok, cex = EQ.prove_equiv(dist_naive, dist_wrong2, _sym_c_and_vec, (3, 5))
    out.append(("wrong_factoring (2c)", (ok is False and "counterexample" in str(cex)), str(cex)[:60]))
    # sign-flipped Horner vs naive poly eval
    ok, cex = EQ.prove_equiv(naive_poly, horner_wrong, EQ.sym_poly_inputs, (3, 5))
    out.append(("wrong_horner (sign)", (ok is False and "counterexample" in str(cex)), str(cex)[:60]))
    return out
