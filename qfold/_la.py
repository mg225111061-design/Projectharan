"""
§AY shared EXACT linear algebra (ℚ via fractions.Fraction; floats are REJECTED on the EXACT path — §1.8/§1-Q3).
================================================================================================================
Tiny zero-dep helpers reused by the qfold recognition branches. Matrix×matrix reuses cfinite._matmul (ring-generic,
exact). Everything is exact rational; any float input raises NonExact ⇒ the caller DECLINEs (never a float-EXACT).
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Sequence

import cfinite  # reuse _matmul / _matpow (ring-generic, exact integers/rationals)


class NonExact(ValueError):
    """Raised when a float (or otherwise inexact) value reaches the EXACT path ⇒ the caller must DECLINE."""


def exact(x) -> Fraction:
    """Coerce to an EXACT Fraction. A float is inexact by nature ⇒ NonExact (no float-EXACT, ever)."""
    if isinstance(x, bool):
        return Fraction(int(x))
    if isinstance(x, float):
        raise NonExact(f"float {x!r} on the EXACT path — rationals/integers only (§1-Q3)")
    if isinstance(x, Fraction):
        return x
    if isinstance(x, int):
        return Fraction(x)
    # numpy integer / Fraction-like / int-string: accept only if it round-trips exactly through int
    try:
        if hasattr(x, "is_integer") and isinstance(x, float):  # belt-and-suspenders
            raise NonExact("float")
        return Fraction(x)
    except NonExact:
        raise
    except Exception as e:  # noqa: BLE001
        raise NonExact(f"inexact/uncoercible value {x!r}: {e}")


def fmat(M: Sequence[Sequence]) -> List[List[Fraction]]:
    return [[exact(x) for x in row] for row in M]


def fvec(v: Sequence) -> List[Fraction]:
    return [exact(x) for x in v]


def matvec(A: Sequence[Sequence[Fraction]], v: Sequence[Fraction]) -> List[Fraction]:
    return [sum((A[i][j] * v[j] for j in range(len(v))), Fraction(0)) for i in range(len(A))]


def dot(w: Sequence[Fraction], v: Sequence[Fraction]) -> Fraction:
    return sum((w[i] * v[i] for i in range(len(v))), Fraction(0))


def matmul(A, B):
    """General (rectangular) exact matrix product. (cfinite._matmul is square-only; this handles N×r · r×M too.)"""
    if not A or not B:
        return []
    rows, inner, cols = len(A), len(B), len(B[0])
    return [[sum((A[i][k] * B[k][j] for k in range(inner)), Fraction(0)) for j in range(cols)] for i in range(rows)]


def matsub(A, B):
    return [[A[i][j] - B[i][j] for j in range(len(A[0]))] for i in range(len(A))]


def eye(n: int) -> List[List[Fraction]]:
    return [[Fraction(1) if i == j else Fraction(0) for j in range(n)] for i in range(n)]


def shift_down(n: int) -> List[List[Fraction]]:
    """Lower shift Z (1's on the subdiagonal): (Z x)_i = x_{i-1}. The canonical Toeplitz displacement operator."""
    return [[Fraction(1) if i == j + 1 else Fraction(0) for j in range(n)] for i in range(n)]


def rank_exact(M: Sequence[Sequence[Fraction]]) -> int:
    """Exact rational rank via gpu.hidden_structure.exact_rank_factorization (RREF over ℚ). Reuse, no double-count."""
    from gpu import hidden_structure as HS
    fr = HS.exact_rank_factorization([[exact(x) for x in row] for row in M])
    return 0 if fr is None else fr[2]
