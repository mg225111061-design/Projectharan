"""
v34 STAGE 3 — Rust acceleration via ctypes (dependency-0: no PyO3/maturin/cffi/flint/faer).
=============================================================================================
Loads the std-only Rust cdylib (rust_accel/target/release/libfold_accel.so) through ctypes and exposes
NTT-based polynomial multiplication mod P=998244353. The Rust path is DIFFERENTIAL-TESTED against the Python
reference (must be IDENTICAL — no fake speedup) and timed against same-algorithm Python.

If the shared library is absent (rustc unavailable / not built), every entry point returns a [BLOCKED] status
with the reason — we never fabricate a Rust number.
"""
from __future__ import annotations

import ctypes
import os
import time
from dataclasses import dataclass
from typing import List, Optional

P = 998_244_353
G = 3
_SO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rust_accel", "target", "release", "libfold_accel.so")
_LIB = None
_LOAD_ERR = None


def _lib():
    global _LIB, _LOAD_ERR
    if _LIB is not None or _LOAD_ERR is not None:
        return _LIB
    try:
        lib = ctypes.CDLL(_SO)
        lib.ntt_poly_mul.argtypes = [ctypes.POINTER(ctypes.c_uint64), ctypes.c_size_t,
                                     ctypes.POINTER(ctypes.c_uint64), ctypes.c_size_t,
                                     ctypes.POINTER(ctypes.c_uint64)]
        lib.ntt_poly_mul.restype = ctypes.c_size_t
        lib.fold_accel_modulus.restype = ctypes.c_uint64
        assert lib.fold_accel_modulus() == P
        _LIB = lib
    except Exception as e:  # noqa: BLE001
        _LOAD_ERR = f"[BLOCKED: {type(e).__name__}: {e}]"
    return _LIB


def available() -> bool:
    return _lib() is not None


def poly_mul_rust(a: List[int], b: List[int]) -> Optional[List[int]]:
    """(a*b) mod P via the Rust NTT. None if the lib is unavailable ([BLOCKED])."""
    lib = _lib()
    if lib is None:
        return None
    ca = (ctypes.c_uint64 * len(a))(*[x % P for x in a])
    cb = (ctypes.c_uint64 * len(b))(*[x % P for x in b])
    out = (ctypes.c_uint64 * (len(a) + len(b) - 1))()
    rlen = lib.ntt_poly_mul(ca, len(a), cb, len(b), out)
    return [out[i] for i in range(rlen)]


# ── Python references (same field) ──
def poly_mul_schoolbook(a: List[int], b: List[int]) -> List[int]:
    """Ground-truth O(d²) multiplication mod P."""
    out = [0] * (len(a) + len(b) - 1)
    for i, ai in enumerate(a):
        for j, bj in enumerate(b):
            out[i + j] = (out[i + j] + ai * bj) % P
    return out


def _ntt_py(a: List[int], invert: bool) -> None:
    n = len(a)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit; bit >>= 1
        j ^= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    length = 2
    while length <= n:
        root = pow(G, (P - 1) // length, P)
        wlen = pow(root, P - 2, P) if invert else root
        i = 0
        while i < n:
            w = 1
            for k in range(length // 2):
                u = a[i + k]
                v = a[i + k + length // 2] * w % P
                a[i + k] = (u + v) % P
                a[i + k + length // 2] = (u - v) % P
                w = w * wlen % P
            i += length
        length <<= 1
    if invert:
        ninv = pow(n, P - 2, P)
        for i in range(n):
            a[i] = a[i] * ninv % P


def poly_mul_python_ntt(a: List[int], b: List[int]) -> List[int]:
    """Same NTT ALGORITHM as Rust, in pure Python (for an apples-to-apples language comparison)."""
    rlen = len(a) + len(b) - 1
    n = 1
    while n < rlen:
        n <<= 1
    fa = [x % P for x in a] + [0] * (n - len(a))
    fb = [x % P for x in b] + [0] * (n - len(b))
    _ntt_py(fa, False); _ntt_py(fb, False)
    fc = [fa[i] * fb[i] % P for i in range(n)]
    _ntt_py(fc, True)
    return fc[:rlen]


@dataclass
class RustMeasurement:
    status: str                 # OK | BLOCKED
    degree: int = 0
    rust_ms: float = 0.0
    python_ntt_ms: float = 0.0
    python_school_ms: float = 0.0
    speedup_vs_python_ntt: float = 0.0
    speedup_vs_school: float = 0.0
    differential_ok: bool = False
    detail: str = ""


def differential_test(trials: int = 5, dmax: int = 64, seed: int = 3) -> bool:
    """Rust NTT result must EQUAL the schoolbook ground truth on random inputs (no fake speedup)."""
    import random
    if not available():
        return False
    rng = random.Random(seed)
    for _ in range(trials):
        da, db = rng.randint(1, dmax), rng.randint(1, dmax)
        a = [rng.randrange(P) for _ in range(da)]
        b = [rng.randrange(P) for _ in range(db)]
        if poly_mul_rust(a, b) != poly_mul_schoolbook(a, b):
            return False
    return True


def measure(degree: int = 2048, seed: int = 1) -> RustMeasurement:
    """[Clock B/C] Rust NTT vs Python NTT (same algorithm) and vs Python schoolbook, with differential check.
    [BLOCKED] if the Rust lib is unavailable — never a fabricated number."""
    if not available():
        return RustMeasurement("BLOCKED", detail=_LOAD_ERR or "libfold_accel.so not built")
    import random
    rng = random.Random(seed)
    a = [rng.randrange(P) for _ in range(degree)]
    b = [rng.randrange(P) for _ in range(degree)]
    diff_ok = differential_test()
    t = time.perf_counter(); poly_mul_rust(a, b); rust_ms = (time.perf_counter() - t) * 1000
    t = time.perf_counter(); poly_mul_python_ntt(a, b); pyntt_ms = (time.perf_counter() - t) * 1000
    # schoolbook only at a smaller degree (O(d²) is too slow at 2048) — measure at 256 and note
    sdeg = min(degree, 256)
    sa, sb = a[:sdeg], b[:sdeg]
    t = time.perf_counter(); poly_mul_schoolbook(sa, sb); sch_ms = (time.perf_counter() - t) * 1000
    return RustMeasurement("OK", degree, round(rust_ms, 3), round(pyntt_ms, 3), round(sch_ms, 3),
                           round(pyntt_ms / rust_ms, 1) if rust_ms > 0 else 1.0,
                           round(sch_ms / rust_ms, 1) if rust_ms > 0 else 1.0, diff_ok,
                           f"Rust NTT vs Python NTT (same algo) @deg{degree}; schoolbook @deg{sdeg}")
