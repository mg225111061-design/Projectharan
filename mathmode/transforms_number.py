"""
UNIFIED ARSENAL §4 · T-number-system — number → exact reconstruction (algebraic / rational / generating function).
==================================================================================================================
Re-express a number or sequence into an exact closed object:
  • modular → rational: rational reconstruction recovers p/q from its residue r (mod m). EXACT — certificate
    p ≡ q·r (mod m), exact integer arithmetic.
  • series → rational function: Berlekamp–Massey finds the SHORTEST linear recurrence behind a sequence ⇒ a
    rational generating function P(t)/Q(t). EXACT for the given terms — certificate: the recurrence reproduces
    every supplied term (and the GF's series matches).
  • real → algebraic: PSLQ finds a candidate INTEGER RELATION (minimal polynomial). Per §X this is Tier-1 EXACT
    ONLY when independently verified by an exact symbolic identity (p(value)≡0); a bare NUMERIC match is
    PROBABILISTIC (δ = the working precision), never EXACT — an unverified relation is NOT a certificate.

Honest scope (§X): PSLQ on a float is PROBABILISTIC unless the value is an exact symbolic constant we can verify;
modular→rational and series→BM are EXACT.
"""
from __future__ import annotations

from typing import List, Optional

import sympy as sp

import kernel_verdict as KV

_t = sp.Symbol("t")


# ── modular → rational ──────────────────────────────────────────────────────────────────────────────────────
def modular_to_rational(r: int, m: int) -> KV.Verdict:
    """Recover p/q with p ≡ q·r (mod m), |p|,q ≤ √(m/2), via the extended-Euclid remainder stop. EXACT."""
    r, m = int(r) % int(m), int(m)
    nbound = int((m // 2) ** 0.5)
    while (nbound + 1) ** 2 <= m // 2:
        nbound += 1
    r0, r1, s0, s1 = m, r, 0, 1
    while r1 > nbound and r1 != 0:
        q = r0 // r1
        r0, r1, s0, s1 = r1, r0 - q * r1, s1, s0 - q * s1
    num, den = r1, s1
    if den < 0:
        num, den = -num, -den
    if den == 0 or den > nbound or abs(num) > nbound or (num - den * r) % m != 0:
        return KV.decline(f"modular_to_rational: no rational p/q with |p|,q≤√(m/2) for r≡{r} (mod {m}) ⇒ DECLINE", "transforms_number")
    cert = KV.Cert(KV.EXACT, "rational_reconstruction", passed=True, check_cost="p ≡ q·r (mod m), exact",
                   detail=f"{r} (mod {m}) reconstructs to {num}/{den}; {num} ≡ {den}·{r} (mod {m}) verified")
    return KV.exact(sp.Rational(num, den), "transforms_number.modular_to_rational", "EXACT (rational reconstruction)", cert)


# ── series → rational function (Berlekamp–Massey over ℚ) ──────────────────────────────────────────────────────
def _berlekamp_massey(seq: List[sp.Rational]) -> List[sp.Rational]:
    """Shortest linear recurrence a_n = Σ_{i≥1} c_i a_{n-i}: returns [c_1,…,c_L] over ℚ."""
    s = [sp.Rational(x) for x in seq]
    C, B = [sp.Integer(1)], [sp.Integer(1)]
    L, mm, b = 0, 1, sp.Integer(1)
    for n in range(len(s)):
        d = s[n] + sum(C[i] * s[n - i] for i in range(1, L + 1))
        if d == 0:
            mm += 1
        elif 2 * L <= n:
            T = list(C)
            coef = d / b
            while len(C) < len(B) + mm:
                C.append(sp.Integer(0))
            for i in range(len(B)):
                C[i + mm] -= coef * B[i]
            L, B, b, mm = n + 1 - L, T, d, 1
        else:
            coef = d / b
            while len(C) < len(B) + mm:
                C.append(sp.Integer(0))
            for i in range(len(B)):
                C[i + mm] -= coef * B[i]
            mm += 1
    return [-C[i] for i in range(1, L + 1)]                  # a_n = Σ c_i a_{n-i}


def series_to_rational(terms: List) -> KV.Verdict:
    """Find the minimal linear recurrence behind a sequence (Berlekamp–Massey) ⇒ rational generating function.
    EXACT for the supplied terms; certificate = the recurrence reproduces EVERY given term."""
    seq = [sp.Rational(x) for x in terms]
    c = _berlekamp_massey(seq)
    L = len(c)
    if L == 0:
        return KV.decline("series_to_rational: zero/empty sequence ⇒ DECLINE", "transforms_number")
    # ★ certificate: recurrence a_n = Σ c_i a_{n-i} reproduces every supplied term beyond the first L ★
    for n in range(L, len(seq)):
        if sp.simplify(seq[n] - sum(c[i - 1] * seq[n - i] for i in range(1, L + 1))) != 0:
            return KV.decline(f"series_to_rational: recurrence fails at term {n} ⇒ DECLINE (not linear-recurrent of order {L})", "transforms_number")
    # generating function: Q(t) = 1 − Σ c_i t^i ; P(t) = (A(t)·Q(t)) truncated to degree < L
    Q = 1 - sum(c[i - 1] * _t ** i for i in range(1, L + 1))
    A = sum(seq[n] * _t ** n for n in range(len(seq)))
    P = sp.expand(A * Q)
    P = sum(P.coeff(_t, k) * _t ** k for k in range(L))      # truncate to degree < L
    gf = sp.simplify(P / Q)
    cert = KV.Cert(KV.EXACT, "berlekamp_massey", passed=True, check_cost="recurrence reproduces all terms",
                   detail=f"order-{L} recurrence a_n=Σc_i a_(n-i), c={c}; generating function {sp.sstr(gf)}")
    return KV.exact({"order": L, "recurrence": c, "generating_function": gf},
                    "transforms_number.series_to_rational", "EXACT (Berlekamp–Massey rational GF)", cert)


# ── real → algebraic (PSLQ; EXACT only if symbolically verified) ──────────────────────────────────────────────
def recognize_algebraic(value, max_deg: int = 6, dps: int = 50) -> KV.Verdict:
    """PSLQ a candidate minimal polynomial for `value`. If `value` is an EXACT sympy constant and p(value)≡0 is
    verified symbolically ⇒ EXACT; if `value` is a bare float (no exact form) ⇒ PROBABILISTIC (δ=precision),
    never EXACT (an unverified numeric relation is NOT a certificate — §X)."""
    import mpmath
    expr = sp.sympify(value)
    is_exact = not expr.is_Float and expr.free_symbols == set()
    mpmath.mp.dps = dps
    try:
        xf = mpmath.mpf(str(sp.N(expr, dps))) if expr.is_real else None
        xf = mpmath.mpf(str(sp.N(expr, dps)))
    except Exception:  # noqa: BLE001
        return KV.decline("recognize_algebraic: value is not a real number ⇒ DECLINE", "transforms_number")
    for deg in range(1, max_deg + 1):
        rel = mpmath.pslq([xf ** k for k in range(deg + 1)], maxcoeff=10 ** 9, maxsteps=10 ** 5)
        if rel and any(rel):
            x = sp.Symbol("x")
            poly = sum(int(rel[k]) * x ** k for k in range(deg + 1))
            if sp.Poly(poly, x).degree() < 1:
                continue
            if is_exact and sp.simplify(poly.subs(x, expr)) == 0:
                cert = KV.Cert(KV.EXACT, "pslq_verified", passed=True, check_cost="p(value)≡0 symbolic",
                               detail=f"{sp.sstr(expr)} is a root of {sp.sstr(poly)}=0 (PSLQ candidate, "
                                      f"SYMBOLICALLY verified ⇒ EXACT)")
                return KV.exact({"minimal_polynomial": poly, "value": expr}, "transforms_number.recognize_algebraic",
                                "EXACT (verified integer relation)", cert)
            if not is_exact:
                resid = abs(float(sum(int(rel[k]) * xf ** k for k in range(deg + 1))))
                delta = float(mpmath.mpf(10) ** (-dps + 2))
                cert = KV.Cert(KV.PROBABILISTIC, "pslq_numeric", passed=True, check_cost=f"{dps}-digit residual",
                               delta=delta, detail=f"NUMERIC integer relation {sp.sstr(poly)}=0 holds to {dps} "
                                                   f"digits (residual≈{resid:.1e}) — PROBABILISTIC, NOT a proof (§X)")
                return KV.probabilistic({"candidate_polynomial": poly}, "transforms_number.recognize_algebraic",
                                        "PROBABILISTIC (unverified numeric relation)", cert)
    return KV.decline(f"recognize_algebraic: no integer relation up to degree {max_deg} ⇒ DECLINE", "transforms_number")


def solve(problem: dict) -> KV.Verdict:
    """ops: 'modular_to_rational' (r,m), 'series_to_rational' (terms), 'recognize_algebraic' (value)."""
    op = problem.get("op")
    if op == "modular_to_rational":
        return modular_to_rational(problem["r"], problem["m"])
    if op == "series_to_rational":
        return series_to_rational(problem["terms"])
    if op == "recognize_algebraic":
        return recognize_algebraic(problem["value"], problem.get("max_deg", 6))
    return KV.decline(f"transforms_number: unknown op {op!r} ⇒ DECLINE", "transforms_number")
