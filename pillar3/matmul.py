"""
Pillar 3 · ROUND 1 #15 — naive O(n³) matmul → blocked/BLAS matmul (EXACT integers under an overflow bound).
============================================================================================================
A hand-rolled triple-loop integer matrix multiply is O(n³) in the interpreter. A blocked/BLAS multiply (numpy
int64 — cache-tiled, vectorized) computes the SAME integer product far faster. Integer matmul is exact UNLESS
a 64-bit accumulator overflows, so — exactly like the NTT convolution — we keep the EXACT grade ONLY under a
PROVEN bound:  |C_ij| ≤ k·max|A|·max|B| < 2^63  ⇒ every entry's int64 value IS the true integer. Bound exceeded
⇒ DECLINE the int64 fast path (Python-bigint or multi-word is the honest extension) — never a wrapped answer.
Certificate = the overflow-bound proof + a full-matrix spot-check vs the naive. A wrong product (transposed /
wrong axis) ⇒ spot-check disagrees ⇒ DECLINE (the moat). UNVERIFIED [no numpy] if the toolchain is absent.
"""
from __future__ import annotations

import random as _rnd
from typing import Callable, List, Optional, Tuple

import kernel_verdict as KV
from pillar3 import lifting as LF

try:
    import numpy as _np
    _NP = True
except Exception:                                            # numpy absent ⇒ UNVERIFIED
    _NP = False

_I64_HALF = 2 ** 63


def matmul_naive(A: List[List[int]], B: List[List[int]]) -> List[List[int]]:
    """Ground-truth O(n³) integer matmul (exact Python ints)."""
    n, k, m = len(A), len(B), len(B[0]) if B else 0
    return [[sum(A[i][t] * B[t][j] for t in range(k)) for j in range(m)] for i in range(n)]


def matmul_numpy(A: List[List[int]], B: List[List[int]]) -> List[List[int]]:
    """Blocked/BLAS integer matmul via numpy int64 (the SAME product, cache-tiled + vectorized)."""
    return (_np.asarray(A, dtype=_np.int64) @ _np.asarray(B, dtype=_np.int64)).tolist()


def matmul_wrong(A: List[List[int]], B: List[List[int]]) -> List[List[int]]:
    """BROKEN: multiplies A by Bᵀ (wrong axis) ⇒ a different product ⇒ spot-check disagrees ⇒ DECLINE."""
    return (_np.asarray(A, dtype=_np.int64) @ _np.asarray(B, dtype=_np.int64).T).tolist()


def _bound(A, B) -> int:
    k = len(B)
    mA = max((abs(x) for row in A for x in row), default=0)
    mB = max((abs(x) for row in B for x in row), default=0)
    return k * mA * mB


def matmul_grade(make_input: Callable[[], tuple], fast_fn: Callable = None, *, n: int, samples: int = 5,
                 residual_iters: int = 0, floor: float = 1.20) -> Tuple[KV.Verdict, Optional[object]]:
    """EXACT iff numpy present AND a PROVEN no-overflow bound holds AND the fast product equals the naive AND a
    whole-program win is measured; bound exceeded / disagreement ⇒ DECLINE; no numpy ⇒ UNVERIFIED (excluded)."""
    if not _NP:
        return KV.decline("matmul UNVERIFIED [no numpy in sandbox] — transform built, excluded", "matmul"), None
    fast_fn = fast_fn or matmul_numpy
    A, B = make_input()
    if _bound(A, B) >= _I64_HALF:                            # the proven exactness condition fails
        return KV.decline("matmul magnitude bound ≥ 2^63 — int64 could overflow; EXACT not certifiable "
                          "(bigint/multi-word is the extension) ⇒ DECLINE fast path", "matmul"), None
    en = matmul_naive(A, B)
    ef = fast_fn(A, B)
    spot_ok = (en == ef)                                     # full-matrix equality on this input
    rep = LF.measure_lift(lambda a, b: matmul_naive(a, b), lambda a, b: fast_fn(a, b),
                          make_input, residual_iters, n=n, samples=samples)
    if not spot_ok:
        v = KV.decline("matmul fast product disagrees with the naive (wrong axis / impossible under the bound) "
                       "⇒ DECLINE", "matmul")
        v.report = rep
        return v, rep
    if not rep.beats(floor):
        v = KV.decline(f"matmul blocked but no whole-program win (×{rep.whole_program_ratio:.2f}) ⇒ DECLINE", "matmul")
        v.report = rep
        return v, rep
    cert = KV.Cert(KV.EXACT, "int64_bound+spotcheck", passed=True, check_cost="O(n²) spot-check",
                   detail=f"blocked/BLAS int64 matmul; proven |C_ij|<2^63 ⇒ exact integers; full-matrix check vs naive")
    v = KV.exact(ef, "matmul", str(rep), cert)
    v.report = rep
    return v, rep


_MM_CACHE: dict = {}


def make_matmul_input(n: int = 160, mag: int = 1000) -> Tuple[List[List[int]], List[List[int]]]:
    """Two n×n integer matrices with |value| ≤ mag, chosen so the proven int64 bound holds (EXACT path)."""
    key = (n, mag)
    if key not in _MM_CACHE:
        rng = _rnd.Random(87)
        A = [[rng.randrange(-mag, mag + 1) for _ in range(n)] for _ in range(n)]
        B = [[rng.randrange(-mag, mag + 1) for _ in range(n)] for _ in range(n)]
        _MM_CACHE[key] = (A, B)
    return _MM_CACHE[key]


def make_matmul_input_overflow(n: int = 64, mag: int = 10 ** 9) -> Tuple[List[List[int]], List[List[int]]]:
    """Huge magnitudes ⇒ the int64 bound is exceeded ⇒ the honest DECLINE path (never a wrapped answer)."""
    rng = _rnd.Random(88)
    A = [[rng.randrange(-mag, mag + 1) for _ in range(n)] for _ in range(n)]
    B = [[rng.randrange(-mag, mag + 1) for _ in range(n)] for _ in range(n)]
    return (A, B)
