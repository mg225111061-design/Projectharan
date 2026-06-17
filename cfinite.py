"""
STAGE 3.1 — pure-Python C-finite (linear-recurrence) closed-form verifier.
==========================================================================
A C-finite sequence  f(n) = c0·f(n−1) + c1·f(n−2) + … + c_{d−1}·f(n−d)  (Fibonacci, Pell, Tribonacci,
…) has an O(log n) evaluation via companion-matrix power-by-squaring, versus the O(n) naive recurrence.
The two are equal **by theorem** (the companion matrix is the linear map of the recurrence), so this is
a LOSSLESS speedup: identical integer values, O(log n) ring operations instead of O(n).

Previously HARAN could only certify this via a Rust `cfinite_nth` binary (absent in this deployment →
every recurrence fell to UNKNOWN). This module does it in pure Python with **exact integer arithmetic**
and a real equivalence check (companion-power ≡ naive across several n) before issuing CLOSED.

Convention (matches closure_classifier.extract_linear_recurrence):
  c    = [c0, …, c_{d−1}]   coefficients of f(n−1), …, f(n−d)
  init = [f(0), …, f(d−1)]  the d initial terms
"""
from __future__ import annotations

from typing import List, Sequence, Tuple


def naive_nth(c: Sequence[int], init: Sequence[int], n: int) -> int:
    """O(n) reference evaluation of the linear recurrence (exact integers)."""
    d = len(c)
    if n < len(init):
        return init[n]
    window = list(init[-d:])                       # [f(k-d), …, f(k-1)] sliding
    val = window[-1]
    for _ in range(len(init), n + 1):
        # f = c0·f(k-1) + c1·f(k-2) + … ; window[-1-i] is f(k-1-i)
        val = sum(c[i] * window[-1 - i] for i in range(d))
        window.append(val)
        window.pop(0)
    return val


def _matmul(A: List[List[int]], B: List[List[int]]) -> List[List[int]]:
    d = len(A)
    return [[sum(A[i][k] * B[k][j] for k in range(d)) for j in range(d)] for i in range(d)]


def _matpow(M: List[List[int]], p: int) -> List[List[int]]:
    d = len(M)
    R = [[1 if i == j else 0 for j in range(d)] for i in range(d)]   # identity
    base = [row[:] for row in M]
    while p > 0:                                    # power-by-squaring → O(log p) matmuls
        if p & 1:
            R = _matmul(R, base)
        base = _matmul(base, base)
        p >>= 1
    return R


def companion_nth(c: Sequence[int], init: Sequence[int], n: int) -> int:
    """O(log n) evaluation via companion-matrix power. Exact integers (no float)."""
    d = len(c)
    if n < d:
        return init[n]
    # state v_{d-1} = [f(d-1), f(d-2), …, f(0)]^T ;  v_k = C · v_{k-1}
    C = [[c[j] for j in range(d)]] + \
        [[1 if k == i - 1 else 0 for k in range(d)] for i in range(1, d)]
    P = _matpow(C, n - (d - 1))
    v = [init[d - 1 - i] for i in range(d)]
    return sum(P[0][k] * v[k] for k in range(d))    # (P · v)[0] = f(n)


def verify_cfinite(c: Sequence[int], init: Sequence[int],
                   ns: Sequence[int] = (8, 16, 24, 40, 63)) -> Tuple[bool, List[int]]:
    """Certify the closed form: companion_nth ≡ naive_nth for every n in `ns` (exact int).
    Returns (ok, checked_ns). ok=True ⇒ the O(log n) companion form is a verified lossless replacement."""
    if not c or len(init) != len(c):
        return (False, [])
    checked = []
    for n in ns:
        if companion_nth(c, init, n) != naive_nth(c, init, n):
            return (False, checked)
        checked.append(n)
    return (True, checked)
