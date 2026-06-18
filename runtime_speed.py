"""
STAGE 3 — Clock C (generated-code execution): make the PRODUCED code run faster.
=================================================================================
★ Clock C ONLY ★ — this is the speed of the code we emit, NOT the LLM call (A) or verification (B). Two
levers, fold preferred (it changes the asymptotics; JIT only the constant factor):

  • fold collapse: a closeable loop (polynomial sum → Faulhaber, linear recurrence → companion/Bostan-Mori,
    prefix sum) becomes O(1)/O(log n) and is BIT-EXACT. If it does NOT close → HONEST_DEFER (never a fake
    "folded"; Rice). Cert types: "exact-closed-form".
  • JIT: compile a verified numeric kernel to native (Numba); the compile cost is paid ONCE (cached) and
    amortized. Constant-factor only. If Numba is unavailable → [BLOCKED], not faked.

Honest reporting: fold's win GROWS with n (asymptotic); we report the fold HIT-RATE so it's clear this only
helps closeable code. JIT timing is taken over repeated runs (not a single sub-resolution call).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

import cfinite
import fold_kernels as FK


@dataclass
class FoldSpeed:
    status: str               # FOLDED | DEFER
    n: int = 0
    naive_ms: float = 0.0
    closed_ms: float = 0.0
    speedup: float = 1.0
    bit_exact: bool = False
    closed_form: str = ""
    cert_type: str = "exact-closed-form"
    detail: str = ""


def fold_sum_speedup(body_naive: Callable[[int], int], haran_code: str, n: int) -> FoldSpeed:
    """Measure [Clock C] for a Σ-fold: naive O(n) loop vs the O(1) closed form at `n`, asserting bit-exact.
    `body_naive(n)` computes the naive sum; `haran_code` is the HARAN fold the engine closes."""
    v = FK.fold_certificate(haran_code)
    if v.status != "FOLDED":
        return FoldSpeed("DEFER", n=n, detail=f"does not close ({v.status}) — HONEST_DEFER, no fake fold")
    import sympy
    sym = sympy.Symbol("n")
    try:
        cf = sympy.sympify(v.closed_form)
    except Exception:  # noqa: BLE001
        return FoldSpeed("DEFER", n=n, detail="closed form not evaluable — DEFER")
    t = time.perf_counter(); naive = body_naive(n); naive_ms = (time.perf_counter() - t) * 1000
    t = time.perf_counter(); closed = int(cf.subs(sym, n)); closed_ms = (time.perf_counter() - t) * 1000
    return FoldSpeed("FOLDED", n=n, naive_ms=round(naive_ms, 3), closed_ms=round(closed_ms, 4),
                     speedup=round(naive_ms / closed_ms, 1) if closed_ms > 0 else 1.0,
                     bit_exact=(naive == closed), closed_form=v.closed_form,
                     detail=f"O(n)→O(1) at n={n}; win grows with n")


# a small corpus to measure the fold HIT-RATE (closeable vs not — honest "only closeable code")
_FOLD_CORPUS = [
    ("fn f(n: Nat) -> Nat { fold k in 1..n { k } }", True),
    ("fn f(n: Nat) -> Nat { fold k in 1..n { k*k } }", True),
    ("fn f(n: Nat) -> Nat { fold k in 1..n { k*k*k } }", True),
    ("fn f(n: Nat) -> Nat { match n { 0 => 0 1 => 1 _ => f(n-1) + f(n-2) } }", True),   # fib (cfinite)
    ("fn f(n: Nat) -> Nat { fold k in 1..n { 1 / k } }", False),                        # Σ1/k — not closeable
    ("fn f(n: Nat) -> Nat { fold k in 1..n { is_prime(k) } }", False),                  # data-dependent
]


def measure_fold_rate() -> dict:
    closed = sum(1 for code, _ in _FOLD_CORPUS if FK.fold_certificate(code).status == "FOLDED")
    return {"closed": closed, "total": len(_FOLD_CORPUS), "rate": round(closed / len(_FOLD_CORPUS), 2),
            "note": "fold helps ONLY closeable code; non-closeable → HONEST_DEFER"}


# ── JIT (Numba) — constant-factor native speedup; honest repeated timing; [BLOCKED] if unavailable ──
@dataclass
class JitSpeed:
    status: str               # JITTED | BLOCKED
    n: int = 0
    py_ms: float = 0.0
    jit_ms: float = 0.0
    speedup: float = 1.0
    equal: bool = False
    compile_ms: float = 0.0
    detail: str = ""


def jit_sumsq_speedup(n: int = 2_000_000, reps: int = 3) -> JitSpeed:
    """Measure [Clock C] interpreter vs Numba-JIT on a verified, DATA-DEPENDENT kernel (Σ xᵢ² over an input
    array) — data-dependence stops the compiler from constant-folding the loop (which would give a fake
    speedup), and bounded values keep it within int64 so it stays BIT-EXACT with Python's bigint."""
    try:
        from numba import njit
        import numpy as np
    except Exception as e:  # noqa: BLE001
        return JitSpeed("BLOCKED", n=n, detail=f"Numba/numpy unavailable ([BLOCKED: {type(e).__name__}])")
    rng = np.random.default_rng(7)
    xs = rng.integers(0, 100, size=n, dtype=np.int64)        # bounded → Σx² ≤ n·10⁴ < int64 (no overflow)
    py_list = xs.tolist()

    @njit(cache=False)
    def k_jit(arr):
        a = 0
        for i in range(arr.shape[0]):
            a += arr[i] * arr[i]
        return a

    def k_py(lst):
        a = 0
        for x in lst:
            a += x * x
        return a
    t = time.perf_counter(); k_jit(xs[:1000]); compile_ms = (time.perf_counter() - t) * 1000   # compile/warm
    best_jit = min(_time(lambda: k_jit(xs)) for _ in range(reps))
    best_py = min(_time(lambda: k_py(py_list)) for _ in range(reps))
    return JitSpeed("JITTED", n=n, py_ms=round(best_py, 2), jit_ms=round(best_jit, 3),
                    speedup=round(best_py / best_jit, 1) if best_jit > 0 else 1.0,
                    equal=(int(k_jit(xs)) == k_py(py_list)), compile_ms=round(compile_ms, 1),
                    detail="data-dependent native kernel; compile amortized (cached); constant-factor (Clock C)")


def _time(fn) -> float:
    t = time.perf_counter(); fn(); return (time.perf_counter() - t) * 1000
