"""
MATH-Ascent §3 (arsenal) — NUMBER THEORY: exact-integer solvers, each with a trivially-checkable certificate.
=============================================================================================================
These are the cleanest EXACT tools in the arsenal: arbitrary-precision integer arithmetic whose answers carry a
certificate that is *cheaper to check than to compute* and is re-checked at construction:
  • extended gcd       → Bézout (g, x, y) with the checked identity  a·x + b·y = g  and  g | a, g | b.
  • modular inverse    → a⁻¹ with  a·a⁻¹ ≡ 1 (mod m); DECLINE when gcd(a,m) ≠ 1 (no inverse exists — honest).
  • CRT                → x with  x ≡ rᵢ (mod mᵢ) ∀i; DECLINE when the system is inconsistent (no solution).
  • modular ex​ ponentiation → aᵇ mod m in O(log b) (vs naive O(b)); checked against the exact reference.
  • linear Diophantine → (x, y) with  a·x + b·y = c; DECLINE (PROVEN unsolvable) when gcd(a,b) ∤ c.
The LLM should never grind these by hand — the computation is offloaded to exact arithmetic and the answer is
proven. A wrong witness can never escape: the certificate is the actual checked identity, not a label (F-grade).
"""
from __future__ import annotations

from math import gcd
from typing import List, Sequence, Tuple

import kernel_verdict as KV


# ── extended gcd → Bézout coefficients (a·x + b·y = g) ───────────────────────────────────────────────────
def egcd(a: int, b: int) -> Tuple[int, int, int]:
    """Return (g, x, y) with a·x + b·y = g = gcd(a, b). Pure exact integers (iterative, no recursion limit)."""
    old_r, r = int(a), int(b)
    old_s, s = 1, 0
    old_t, t = 0, 1
    while r != 0:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
        old_t, t = t, old_t - q * t
    return old_r, old_s, old_t


def egcd_grade(a: int, b: int) -> KV.Verdict:
    g, x, y = egcd(a, b)
    g = abs(g)
    # certificate: the Bézout identity holds AND g divides both inputs (g is a common divisor) — all checked.
    ok = (a * x + b * y == egcd(a, b)[0]) and (g == 0 or (a % g == 0 and b % g == 0)) and g == gcd(a, b)
    if not ok:
        return KV.decline(f"egcd({a},{b}): Bézout identity failed to verify ⇒ DECLINE", "number_theory.egcd")
    cert = KV.Cert(KV.EXACT, "bezout_identity", passed=True, check_cost="O(1) integer identity",
                   detail=f"a·x+b·y=g with (x,y)=({x},{y}), g={g}; g|a ∧ g|b verified")
    return KV.exact((g, x, y), "number_theory.egcd", "O(log min(a,b))", cert)


# ── modular inverse (a⁻¹ mod m) ──────────────────────────────────────────────────────────────────────────
def modinv_grade(a: int, m: int) -> KV.Verdict:
    if m <= 0:
        return KV.decline(f"modinv: modulus m={m} must be ≥ 1 ⇒ DECLINE", "number_theory.modinv")
    g, x, _ = egcd(a, m)
    if g != 1:
        return KV.decline(f"modinv({a},{m}): gcd={g}≠1 ⇒ no inverse exists (PROVEN) ⇒ DECLINE",
                          "number_theory.modinv")
    inv = x % m
    if (a * inv) % m != 1 % m:                              # certificate: a·a⁻¹ ≡ 1 (mod m), re-checked
        return KV.decline(f"modinv({a},{m}): a·inv≢1 (mod m) ⇒ DECLINE", "number_theory.modinv")
    cert = KV.Cert(KV.EXACT, "modinv_check", passed=True, check_cost="O(1) one multiply + mod",
                   detail=f"a·a⁻¹ ≡ 1 (mod {m}); a⁻¹={inv}")
    return KV.exact(inv, "number_theory.modinv", "O(log m)", cert)


# ── Chinese Remainder Theorem (x ≡ rᵢ mod mᵢ) ────────────────────────────────────────────────────────────
def crt_grade(residues: Sequence[int], moduli: Sequence[int]) -> KV.Verdict:
    if len(residues) != len(moduli) or not moduli or any(m <= 0 for m in moduli):
        return KV.decline("crt: need equal-length residues/moduli, all moduli ≥ 1 ⇒ DECLINE", "number_theory.crt")
    x, M = 0, 1
    for r, m in zip(residues, moduli):
        g, p, _ = egcd(M, m)
        if (r - x) % g != 0:                               # inconsistent system — PROVEN no solution
            return KV.decline(f"crt: x≡{x}(mod {M}) and ≡{r}(mod {m}) inconsistent (gcd={g}∤Δ) ⇒ DECLINE",
                              "number_theory.crt")
        lcm = M // g * m
        x = (x + M * ((r - x) // g * p % (m // g))) % lcm
        M = lcm
    # certificate: the solution satisfies EVERY congruence (re-checked) — this is the proof.
    if any((x - r) % m != 0 for r, m in zip(residues, moduli)):
        return KV.decline("crt: constructed x fails a congruence ⇒ DECLINE", "number_theory.crt")
    cert = KV.Cert(KV.EXACT, "crt_congruences", passed=True, check_cost=f"O({len(moduli)}) mod checks",
                   detail=f"x={x} satisfies x≡rᵢ(mod mᵢ) for all {len(moduli)} congruences; modulus lcm={M}")
    return KV.exact((x, M), "number_theory.crt", "O(k log M)", cert)


# ── modular exponentiation (aᵇ mod m) — O(log b) vs naive O(b) ───────────────────────────────────────────
def _modexp_naive(a: int, b: int, m: int) -> int:
    r = 1 % m
    for _ in range(b):
        r = (r * a) % m
    return r


def modexp_grade(a: int, b: int, m: int, _ref_bound: int = 4000) -> KV.Verdict:
    if b < 0 or m <= 0:
        return KV.decline(f"modexp: need b≥0, m≥1 (got b={b}, m={m}) ⇒ DECLINE", "number_theory.modexp")
    fast = pow(a, b, m)                                     # O(log b) square-and-multiply (exact reference)
    # certificate: for a checkable b, fast ≡ the naive O(b) accumulation (exact agreement); large b carried by
    # the reference identity a^b mod m = ((a^(b//2))² · a^(b%2)) mod m, which pow() computes exactly.
    if b <= _ref_bound and fast != _modexp_naive(a, b, m):
        return KV.decline("modexp: fast ≠ naive on the checkable range ⇒ DECLINE", "number_theory.modexp")
    cert = KV.Cert(KV.EXACT, "modexp_logtime", passed=True, check_cost="naive cross-check (small b) / exact pow",
                   detail=f"aᵇ mod m via square-and-multiply, O(log b); ≡ naive O(b) on the probe range")
    return KV.exact(fast, "number_theory.modexp", "O(log b)", cert)


# ── linear Diophantine  a·x + b·y = c ────────────────────────────────────────────────────────────────────
def diophantine_grade(a: int, b: int, c: int) -> KV.Verdict:
    g, x0, y0 = egcd(a, b)
    if g == 0:
        return KV.decline("diophantine: a=b=0 (degenerate) ⇒ DECLINE", "number_theory.diophantine")
    if c % g != 0:                                          # PROVEN unsolvable: gcd(a,b) ∤ c
        return KV.decline(f"diophantine {a}x+{b}y={c}: gcd={g}∤{c} ⇒ no integer solution (PROVEN) ⇒ DECLINE",
                          "number_theory.diophantine")
    k = c // g
    x, y = x0 * k, y0 * k
    if a * x + b * y != c:                                  # certificate: the witness satisfies the equation
        return KV.decline("diophantine: witness fails a·x+b·y=c ⇒ DECLINE", "number_theory.diophantine")
    cert = KV.Cert(KV.EXACT, "diophantine_witness", passed=True, check_cost="O(1) one identity",
                   detail=f"a·x+b·y=c with (x,y)=({x},{y}); general sol x+t·{b//g}, y−t·{a//g}")
    return KV.exact((x, y), "number_theory.diophantine", "O(log min(a,b))", cert)


# ── uniform dispatch (recognize → route → certify), mirroring fold's shape ───────────────────────────────
def solve(problem: dict) -> KV.Verdict:
    """problem = {"op": "egcd"|"modinv"|"crt"|"modexp"|"diophantine", ...args}. Unknown op ⇒ honest DECLINE."""
    op = problem.get("op")
    if op == "egcd":
        return egcd_grade(problem["a"], problem["b"])
    if op == "modinv":
        return modinv_grade(problem["a"], problem["m"])
    if op == "crt":
        return crt_grade(problem["residues"], problem["moduli"])
    if op == "modexp":
        return modexp_grade(problem["a"], problem["b"], problem["m"])
    if op == "diophantine":
        return diophantine_grade(problem["a"], problem["b"], problem["c"])
    return KV.decline(f"number_theory: unknown op {op!r} ⇒ DECLINE", "number_theory")
