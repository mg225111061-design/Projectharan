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


def _polymul(a: Coef, b: Coef) -> Coef:
    """Full polynomial product (no truncation)."""
    if not a or not b:
        return []
    r = [Fr(0)] * (len(a) + len(b) - 1)
    for i, ai in enumerate(a):
        if ai == 0:
            continue
        for j, bj in enumerate(b):
            if bj:
                r[i + j] += ai * bj
    return r


def bostan_mori(p: Sequence, q: Sequence, n: int) -> Fr:
    """[x^n] of the rational power series P(x)/Q(x) by the BOSTAN–MORI halving recurrence (Q(0) ≠ 0). Each step
    multiplies by Q(−x): P/Q = P·Q(−x) / (Q·Q(−x)); the denominator V = Q·Q(−x) is EVEN, the numerator splits
    into even/odd parts, and [x^n] picks the even (n even) or odd (n odd) part of the numerator over V's even
    part, halving n. O(log n) steps × O(d²) polynomial mults ⇒ O(M(d) log n) — astronomical n is fine."""
    p, q = _f(p), _f(q)
    if not q or q[0] == 0:
        raise ValueError("bostan_mori: Q(0) must be nonzero")
    while n > 0:
        qm = [(-c if (i & 1) else c) for i, c in enumerate(q)]   # Q(−x)
        a = _polymul(p, qm)                                      # P(x)·Q(−x)
        v = _polymul(q, qm)                                      # Q(x)·Q(−x) — even in x
        p = a[n & 1::2]                                          # even (n even) or odd (n odd) part of the numerator
        q = v[0::2]                                              # even part of V (V is even ⇒ this is V as poly in x²)
        n >>= 1
    return p[0] / q[0] if p else Fr(0)


def bostan_mori_grade(p: Sequence, q: Sequence, n: int) -> KV.Verdict:
    """[x^n] P(x)/Q(x) by Bostan–Mori (the n-th term of the C-finite sequence with denominator Q), EXACT over ℚ.
    Certified two ways: for small n a DIRECT series cross-check (P·Q⁻¹ via Newton), and at ANY n the GF defining
    equation Σ_j Q[j]·a_{n−j} = P[n] re-checked from independently-extracted neighbours a_{n−j}. Q(0)=0 / n<0 ⇒
    honest DECLINE."""
    p, q = _f(p), _f(q)
    if n < 0 or not q or q[0] == 0:
        return KV.decline(f"bostan_mori: need n≥0 and Q(0)≠0 ⇒ DECLINE", "newton_series.bostan_mori")
    val = bostan_mori(p, q, n)
    d = len(q) - 1
    how = []
    # (1) direct series cross-check for small n
    if n <= 200:
        coeff = _mul(_trunc(p, n + 1), inv(q, n + 1), n + 1)[n]
        if coeff != val:
            return KV.decline("bostan_mori: ≠ direct series coefficient ⇒ DECLINE (bug guard)", "newton_series.bostan_mori")
        how.append("direct P·Q⁻¹ series")
    # (2) GF recurrence Σ_j Q[j]·a_{n−j} = P[n] at this n (independent neighbours), valid at any n ≥ d
    if n >= d:
        acc = Fr(0)
        for j in range(d + 1):
            aj = val if j == 0 else bostan_mori(p, q, n - j)
            acc += q[j] * aj
        pn = p[n] if n < len(p) else Fr(0)
        if acc != pn:
            return KV.decline(f"bostan_mori: GF recurrence Σ Q[j]·a_(n−j) ≠ P[n] ⇒ DECLINE (bug guard)",
                              "newton_series.bostan_mori")
        how.append("GF recurrence Σ Q[j]·a_(n−j)=P[n]")
    if not how:
        how.append("Bostan–Mori halving (n<deg Q, base extraction)")
    shown = str(val) if (abs(val.numerator) < 10 ** 30 and val.denominator < 10 ** 30) else \
        f"<{val.numerator.bit_length()}-bit value>"
    cert = KV.Cert(KV.EXACT, "bostan_mori_gf", passed=True, check_cost="O(M(d) log n) + cross-check",
                   detail=f"[x^{n}] P/Q = {shown}; certified: {' ∧ '.join(how)}")
    return KV.exact(val, "newton_series.bostan_mori", "Bostan–Mori O(M(d) log n)", cert)


def _strip(p: Coef) -> Coef:
    p = list(p)
    while len(p) > 1 and p[-1] == 0:
        p.pop()
    return p or [Fr(0)]


def _polydivmod(a: Coef, b: Coef) -> Tuple[Coef, Coef]:
    """Exact polynomial division a = q·b + r over ℚ, deg r < deg b."""
    a, b = _strip(a), _strip(b)
    db, lb = len(b) - 1, b[-1]
    r = a[:]
    q = [Fr(0)] * max(1, len(a) - db)
    while True:
        r = _strip(r)
        if len(r) - 1 < db or r == [Fr(0)]:
            break
        coef, shift = r[-1] / lb, (len(r) - 1) - db
        q[shift] = coef
        for i in range(len(b)):
            r[shift + i] -= coef * b[i]
    return _strip(q), _strip(r)


def _poly_eval(coeffs: Coef, x: Fr) -> Fr:
    acc = Fr(0)
    for c in reversed(coeffs):
        acc = acc * x + c
    return acc


def _subproduct(points: List[Fr]) -> Coef:
    prod: Coef = [Fr(1)]
    for x in points:
        prod = _polymul(prod, [-x, Fr(1)])                   # ·(x − xᵢ)
    return prod


def _eval_tree(P: Coef, points: List[Fr]) -> List[Fr]:
    """Fast multipoint evaluation by the subproduct/remainder tree: P mod ∏(x−xᵢ) descends, halving the point set,
    until each leaf is P mod (x−xᵢ) = P(xᵢ)."""
    if len(points) == 1:
        return [_poly_eval(_strip(P), points[0])]
    mid = len(points) // 2
    left, right = points[:mid], points[mid:]
    _, rl = _polydivmod(P, _subproduct(left))
    _, rr = _polydivmod(P, _subproduct(right))
    return _eval_tree(rl, left) + _eval_tree(rr, right)


def multipoint_eval_grade(coeffs: Sequence, points: Sequence) -> KV.Verdict:
    """Evaluate a polynomial at MANY points by the subproduct-tree remainder algorithm (O(M(n) log n)), EXACT
    over ℚ, CERTIFIED against direct Horner at every point (an independent O(n²) oracle). Empty points ⇒ DECLINE."""
    pts = _f(points)
    if not pts:
        return KV.decline("multipoint_eval: no evaluation points ⇒ DECLINE", "newton_series.multipoint")
    P = _f(coeffs)
    fast = _eval_tree(P, pts)
    direct = [_poly_eval(P, x) for x in pts]                  # ★ independent Horner cross-check ★
    if fast != direct:
        return KV.decline("multipoint_eval: tree result ≠ direct Horner ⇒ DECLINE (bug guard)", "newton_series.multipoint")
    cert = KV.Cert(KV.EXACT, "multipoint_subproduct_tree", passed=True, check_cost="O(M(n) log n) + Horner recheck",
                   detail=f"P evaluated at {len(pts)} points via the subproduct/remainder tree ≡ direct Horner "
                          f"(exact over ℚ)")
    return KV.exact(fast, "newton_series.multipoint", "subproduct tree O(M(n) log n)", cert)


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
