"""
Pillar 3 · ROUND 1 #8 — naive convolution O(n²) → NTT O(n log n), EXACT under a proven no-wraparound bound.
============================================================================================================
A hand-rolled discrete convolution  c[k] = Σ_i a[i]·b[k−i]  is O(n²). The number-theoretic transform computes
it in O(n log n) with EXACT INTEGER arithmetic mod P=998244353 (no float error). This wires the existing
proven NTT (rust_accel; pure-Python NTT fallback — same algorithm) into a Pillar-3 recognizer.

★ EXACT, soundly (matches kernels_structured.toeplitz) ★ NTT gives the convolution mod P. We keep the EXACT
grade ONLY when a PROVEN magnitude bound guarantees no wraparound:  |c[k]| ≤ min(|a|,|b|)·max|a|·max|b| < P/2
⇒ every entry's signed mod-P value IS the true integer. If the bound is exceeded ⇒ DECLINE the fast path
(multi-modular CRT is the honest extension, not done here) — never a wrong/wrapped answer. The certificate is
the bound proof + an O(n) spot-check vs the naive. A corrupted NTT ⇒ spot-check disagrees ⇒ DECLINE (the moat).
"""
from __future__ import annotations

import random as _rnd
from typing import Callable, List, Optional, Tuple

import kernel_verdict as KV
import rust_accel as RA
from pillar3 import lifting as LF

_P = RA.P
_HALF = _P // 2


def _to_signed(x: int) -> int:
    return x - _P if x > _HALF else x


def conv_naive(a: List[int], b: List[int]) -> List[int]:
    """True integer convolution, O(n²) (the hot region we want to replace)."""
    out = [0] * (len(a) + len(b) - 1)
    for i, ai in enumerate(a):
        for j, bj in enumerate(b):
            out[i + j] += ai * bj
    return out


def conv_ntt(a: List[int], b: List[int]) -> List[int]:
    """Exact-integer convolution via NTT mod P, mapped back to signed integers, O(n log n). (rust if present,
    else the identical pure-Python NTT — both O(n log n).)"""
    am = [x % _P for x in a]
    bm = [x % _P for x in b]
    raw = None
    if RA.available():
        raw = RA.poly_mul_rust(am, bm)
    if raw is None:
        raw = RA.poly_mul_python_ntt(am, bm)
    return [_to_signed(x % _P) for x in raw]


def conv_ntt_wrong(a: List[int], b: List[int]) -> List[int]:
    """A BROKEN fast path: skips the signed remap (leaves values in [0,P)) ⇒ wrong for negative entries ⇒
    spot-check disagrees ⇒ DECLINE."""
    am = [x % _P for x in a]
    bm = [x % _P for x in b]
    raw = RA.poly_mul_python_ntt(am, bm)
    return [x % _P for x in raw]                              # BUG: no _to_signed → wrong on negative results


def _bound(a: List[int], b: List[int]) -> int:
    return min(len(a), len(b)) * max((abs(x) for x in a), default=0) * max((abs(x) for x in b), default=0)


def conv_grade(make_input: Callable[[], Tuple[List[int], List[int]]], fast_fn: Callable = None, *,
               n: int, samples: int = 5, residual_iters: int = 0,
               floor: float = 1.20) -> Tuple[KV.Verdict, Optional[object]]:
    """EXACT iff a PROVEN no-wraparound bound holds AND the fast result equals the naive on a spot-check AND a
    whole-program win is measured; bound exceeded or spot-check disagreement ⇒ DECLINE (never a wrapped answer)."""
    fast_fn = fast_fn or conv_ntt
    a, b = make_input()
    if _bound(a, b) >= _HALF:                                 # the proven exactness condition fails
        return KV.decline(f"convolution magnitude bound ≥ P/2 — NTT could wrap; EXACT not certifiable "
                          f"(multi-modular CRT is the extension) ⇒ DECLINE fast path", "convolution"), None
    en = conv_naive(a, b)
    ef = fast_fn(a, b)
    spot_ok = (en == ef)                                      # full equality on this input (the strongest spot-check)
    rep = LF.measure_lift(lambda x, y: conv_naive(x, y), lambda x, y: fast_fn(x, y),
                          make_input, residual_iters, n=n, samples=samples)
    if not spot_ok:
        v = KV.decline("convolution NTT result disagrees with the naive (impossible under the bound ⇒ a wrong "
                       "fast path) ⇒ DECLINE", "convolution")
        v.report = rep
        return v, rep
    if not rep.beats(floor):
        v = KV.decline(f"convolution NTT but no whole-program win (×{rep.whole_program_ratio:.2f}) ⇒ DECLINE",
                       "convolution")
        v.report = rep
        return v, rep
    cert = KV.Cert(KV.EXACT, "ntt_bound+spotcheck", passed=True, check_cost="O(n) spot-check",
                   detail=f"NTT convolution mod P={_P}; proven |c[k]|<P/2 ⇒ exact integers; full-vector check vs naive")
    v = KV.exact(ef, "convolution", str(rep), cert)
    v.report = rep
    return v, rep


_CONV_CACHE: dict = {}


def make_conv_input(n: int = 2000, mag: int = 300) -> Tuple[List[int], List[int]]:
    """Two length-n integer sequences with |value| ≤ mag chosen so the proven bound stays < P/2 (EXACT path)."""
    key = (n, mag)
    if key not in _CONV_CACHE:
        rng = _rnd.Random(83)
        a = [rng.randrange(-mag, mag + 1) for _ in range(n)]
        b = [rng.randrange(-mag, mag + 1) for _ in range(n)]
        _CONV_CACHE[key] = (a, b)
    return _CONV_CACHE[key]


def make_conv_input_overflow(n: int = 2048, mag: int = 100000) -> Tuple[List[int], List[int]]:
    """Large magnitudes ⇒ the proven bound is exceeded ⇒ the honest DECLINE path (never a wrapped answer)."""
    rng = _rnd.Random(84)
    return ([rng.randrange(-mag, mag + 1) for _ in range(n)],
            [rng.randrange(-mag, mag + 1) for _ in range(n)])
