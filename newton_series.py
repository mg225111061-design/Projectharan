"""
HARAN #14 (Group A) — NEWTON ITERATION on formal power series (inversion / sqrt / exp / log).
=============================================================================================
Newton's method doubles the known precision each step (quadratic convergence): to refine a length-k solution to
length 2k costs one truncated multiply, so reaching order N costs O(M(N)) total (a geometric sum), not O(N·M).
Everything is EXACT — coefficients are Python `Fraction`s, so the answer is the true rational power series, and
the CERTIFICATE is the defining identity verified EXACTLY to the truncation order N:
  • inv(A)  : A·B ≡ 1            (mod x^N)     [requires A(0) ≠ 0]
  • sqrt(A) : S² ≡ A            (mod x^N)     [requires A(0) a perfect rational square]
  • log(A)  : (exp∘log)(A) ≡ A  (mod x^N)     [requires A(0) = 1]
  • exp(A)  : (log∘exp)(A) ≡ A  (mod x^N)     [requires A(0) = 0]
A precondition violation is an honest DECLINE (the operation is undefined there), never a fabricated answer. This
is the verified series-arithmetic core the higher kernels (Bostan–Mori GF extraction, holonomic) build on.
"""
from __future__ import annotations

from fractions import Fraction as Fr
from typing import List, Sequence

import kernel_verdict as KV

Coef = List[Fr]


def _f(seq: Sequence) -> Coef:
    return [x if isinstance(x, Fr) else Fr(x) for x in seq]


def _trunc(a: Coef, n: int) -> Coef:
    a = a[:n]
    return a + [Fr(0)] * (n - len(a))


def _mul(a: Coef, b: Coef, n: int) -> Coef:
    """Truncated product (a·b) mod x^n (schoolbook — O(n²), fine inside the geometric Newton schedule)."""
    r = [Fr(0)] * n
    for i, ai in enumerate(a[:n]):
        if ai == 0:
            continue
        for j, bj in enumerate(b[: n - i]):
            if bj:
                r[i + j] += ai * bj
    return r


def inv(a: Sequence, n: int) -> Coef:
    """B with A·B ≡ 1 (mod x^n), A(0) ≠ 0. Newton: B ← B·(2 − A·B)."""
    a = _f(a)
    if not a or a[0] == 0:
        raise ValueError("inv: A(0) must be nonzero")
    b = [1 / a[0]]
    k = 1
    while k < n:
        k = min(2 * k, n)
        ab = _mul(_trunc(a, k), b, k)
        two_minus = [(Fr(2) if i == 0 else Fr(0)) - ab[i] for i in range(k)]
        b = _mul(b, two_minus, k)
    return _trunc(b, n)


def deriv(a: Coef) -> Coef:
    return [a[i] * i for i in range(1, len(a))]


def integ(a: Coef) -> Coef:
    return [Fr(0)] + [a[i] / (i + 1) for i in range(len(a))]


def log(a: Sequence, n: int) -> Coef:
    """L with L = log A (mod x^n), A(0) = 1. L = ∫ A'/A."""
    a = _f(a)
    if not a or a[0] != 1:
        raise ValueError("log: A(0) must be 1")
    la = _mul(_trunc(deriv(a), n), inv(a, n), n)
    return _trunc(integ(la), n)


def exp(a: Sequence, n: int) -> Coef:
    """E with E = exp A (mod x^n), A(0) = 0. Newton: E ← E·(1 + A − log E)."""
    a = _f(a)
    if a and a[0] != 0:
        raise ValueError("exp: A(0) must be 0")
    e = [Fr(1)]
    k = 1
    while k < n:
        k = min(2 * k, n)
        le = log(_trunc(e, k), k)
        corr = [( (Fr(1) if i == 0 else Fr(0)) + (a[i] if i < len(a) else Fr(0)) - le[i] ) for i in range(k)]
        e = _mul(_trunc(e, k), corr, k)
    return _trunc(e, n)


def sqrt(a: Sequence, n: int) -> Coef:
    """S with S² ≡ A (mod x^n), A(0) a perfect rational square. Newton: S ← (S + A·S⁻¹)/2."""
    a = _f(a)
    if not a or a[0] == 0:
        raise ValueError("sqrt: A(0) must be nonzero")
    from math import isqrt
    num, den = a[0].numerator, a[0].denominator
    rn, rd = isqrt(num), isqrt(den)
    if rn * rn != num or rd * rd != den:
        raise ValueError("sqrt: A(0) is not a perfect rational square")
    s = [Fr(rn, rd)]
    half = Fr(1, 2)
    k = 1
    while k < n:
        k = min(2 * k, n)
        si = inv(s, k)
        asi = _mul(_trunc(a, k), si, k)
        s = [half * (s[i] if i < len(s) else Fr(0)) + half * asi[i] for i in range(k)]
    return _trunc(s, n)


_OPS = {"inv": inv, "sqrt": sqrt, "exp": exp, "log": log}


def newton_series_grade(op: str, coeffs: Sequence, n: int) -> KV.Verdict:
    """Compute a power-series `op` ∈ {inv,sqrt,exp,log} of `coeffs` to order `n` by Newton iteration, EXACT over
    ℚ, and CERTIFY by the defining identity verified exactly to order n (A·B≡1 / S²≡A / exp∘log≡A / log∘exp≡A).
    A precondition violation (A(0)=0 for inv/sqrt, A(0)≠1 for log, A(0)≠0 for exp, non-square A(0) for sqrt) is an
    honest DECLINE."""
    if op not in _OPS or n < 1:
        return KV.decline(f"newton_series: bad op {op!r} / n={n} ⇒ DECLINE", "newton_series")
    a = _f(coeffs)
    try:
        out = _OPS[op](a, n)
    except ValueError as e:
        return KV.decline(f"newton_series.{op}: {e} ⇒ DECLINE (operation undefined here)", "newton_series")
    # ── certificate: the defining identity, verified EXACTLY to order n ──
    one = [Fr(1)] + [Fr(0)] * (n - 1)
    if op == "inv":
        ok, ident = _mul(_trunc(a, n), out, n) == one, "A·B ≡ 1"
    elif op == "sqrt":
        ok, ident = _mul(out, out, n) == _trunc(a, n), "S² ≡ A"
    elif op == "log":                                          # exp(log A) ≡ A
        ok, ident = exp(out, n) == _trunc(a, n), "exp(log A) ≡ A"
    else:                                                      # exp: log(exp A) ≡ A
        ok, ident = log(out, n) == _trunc(a, n), "log(exp A) ≡ A"
    if not ok:
        return KV.decline(f"newton_series.{op}: identity {ident} FAILED to order {n} ⇒ DECLINE (bug guard)",
                          "newton_series")
    cert = KV.Cert(KV.EXACT, f"newton_series_{op}", passed=True, check_cost=f"one truncated mul, identity to x^{n}",
                   detail=f"{op}(A) to order {n}: {ident} verified exactly over ℚ (Newton, quadratic convergence)")
    return KV.exact(out, "newton_series", f"Newton {op} O(M(n))", cert)
