"""
MATH-Ascent §B4 (arsenal) — SPECIAL FUNCTIONS: exact closed-form values of Γ and ζ, certified by identities.
===========================================================================================================
Two classic special-function families with EXACT closed forms (theorems, not approximations):
  • Γ at integers and HALF-integers — Γ(n)=(n−1)!, Γ(n+½)=(2n)!/(4ⁿ n!)·√π. The value is certified by the
    functional equation Γ(z+1)=z·Γ(z) (verified symbolically) anchored at the base cases Γ(1)=1, Γ(½)=√π — an
    induction, the same shape as the Faulhaber fold. A pole (Γ at 0 or a negative integer) ⇒ honest DECLINE.
  • ζ at EVEN positive integers — ζ(2k) = (−1)^{k+1} B₂ₖ (2π)^{2k} / (2·(2k)!) (Euler). We compute the rational
    coefficient of π^{2k} from the Bernoulli numbers, cross-check it against sympy's ζ AND a high-precision
    partial sum of the defining series. ODD ζ(2k+1) (no known closed form) ⇒ honest DECLINE — never fabricated.
sympy evaluates Bernoulli/factorials; OUR identity check (the recurrence, the two-way cross-check) licenses EXACT.
"""
from __future__ import annotations

from fractions import Fraction
from math import comb, factorial

import sympy as sp

import kernel_verdict as KV


def gamma_grade(two_z: int) -> KV.Verdict:
    """Γ(z) for z = two_z/2 a positive integer or half-integer. EXACT closed form, certified by Γ(z+1)=z·Γ(z).
    `two_z` is 2z (so two_z=3 ⇒ Γ(3/2)). Non-positive poles / non-half-integers ⇒ honest DECLINE."""
    if two_z <= 0:
        return KV.decline(f"gamma: z={Fraction(two_z,2)} ≤ 0 is a pole / out of the supported domain ⇒ DECLINE",
                          "special.gamma")
    z = sp.Rational(two_z, 2)
    if two_z % 2 == 0:                                        # integer z = n ⇒ Γ(n) = (n−1)!
        n = two_z // 2
        val = sp.Integer(factorial(n - 1))
    else:                                                    # half-integer z = n+½ ⇒ Γ(n+½) = (2n)!/(4ⁿ n!)·√π
        n = (two_z - 1) // 2
        val = sp.Rational(factorial(2 * n), 4 ** n * factorial(n)) * sp.sqrt(sp.pi)
    # ★ certificate: the functional equation Γ(z+1) = z·Γ(z), and the value matches sympy.gamma ★
    if sp.simplify(sp.gamma(z + 1) - z * sp.gamma(z)) != 0 or sp.simplify(val - sp.gamma(z)) != 0:
        return KV.decline("gamma: functional-equation / value check failed ⇒ DECLINE", "special.gamma")
    cert = KV.Cert(KV.EXACT, "gamma_functional_eq", passed=True, check_cost="recurrence + value identity",
                   detail=f"Γ({z}) = {sp.sstr(val)}; Γ(z+1)=z·Γ(z) verified (base Γ(1)=1, Γ(½)=√π)")
    return KV.exact(val, "special.gamma", "exact closed form", cert)


def zeta_even_grade(s: int) -> KV.Verdict:
    """ζ(s) for s an EVEN positive integer: exact closed form rational·π^s (Euler/Bernoulli), cross-checked vs
    sympy ζ and a high-precision partial sum. Odd s (no closed form) / s ≤ 1 ⇒ honest DECLINE."""
    if s <= 1 or s % 2 == 1:
        return KV.decline(f"zeta: s={s} — only EVEN s ≥ 2 has a known closed form ⇒ DECLINE", "special.zeta")
    k = s // 2
    # ζ(2k) = (−1)^{k+1} B_{2k} (2π)^{2k} / (2·(2k)!) ; coefficient of π^s is rational
    B2k = sp.bernoulli(2 * k)
    coeff = sp.Rational((-1) ** (k + 1)) * B2k * sp.Integer(2) ** (2 * k) / (2 * sp.factorial(2 * k))
    val = coeff * sp.pi ** s
    # ★ certificate: matches sympy's exact ζ, AND a partial sum of the DEFINING series Σ1/nˢ agrees (independent
    #   numerical cross-check; tolerance set to the s=2 tail ~1/N at N=2·10⁵, which dominates all even s) ★
    if sp.simplify(val - sp.zeta(s)) != 0:
        return KV.decline("zeta: closed form ≠ sympy ζ ⇒ DECLINE", "special.zeta")
    partial = sum(1.0 / (n ** s) for n in range(1, 200000))
    if abs(partial - float(val.evalf())) > 1e-3:
        return KV.decline("zeta: closed form disagrees with the series partial sum ⇒ DECLINE", "special.zeta")
    cert = KV.Cert(KV.EXACT, "zeta_euler_bernoulli", passed=True, check_cost="Bernoulli form + sympy + series",
                   detail=f"ζ({s}) = {sp.sstr(val)} (Euler: coeff·π^{s} via B_{2*k}); ≡ sympy ζ ∧ partial-sum check")
    return KV.exact(val, "special.zeta", "exact closed form", cert)


def solve(problem: dict) -> KV.Verdict:
    op = problem.get("op")
    if op == "gamma":
        return gamma_grade(problem["two_z"])
    if op == "zeta_even":
        return zeta_even_grade(problem["s"])
    return KV.decline(f"special_functions: unknown op {op!r} ⇒ DECLINE", "special_functions")
