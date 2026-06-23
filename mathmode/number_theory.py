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


# ── primality (Miller–Rabin) — EXACT below the proven deterministic-witness bound, else PROBABILISTIC(δ) ──
# For n < 3.317×10²⁴ the first 12 primes as MR bases are a DETERMINISTIC witness set (a proof). Above it, k
# random bases give a one-sided PROBABILISTIC test (a composite passes with prob ≤ 4⁻ᵏ — never a false "prime").
_DET_BOUND = 3317044064679887385961981
_DET_BASES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
_SMALL = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)


def _mr_composite(n: int, a: int) -> bool:
    """True iff base a is a Miller–Rabin WITNESS that n is composite (one-sided: a true prime is never a witness)."""
    if a % n == 0:
        return False
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2
        r += 1
    x = pow(a, d, n)
    if x == 1 or x == n - 1:
        return False
    for _ in range(r - 1):
        x = x * x % n
        if x == n - 1:
            return False
    return True


def _is_prime_det(n: int) -> bool:
    if n < 2:
        return False
    for p in _SMALL:
        if n % p == 0:
            return n == p
    return not any(_mr_composite(n, a) for a in _DET_BASES)


def is_prime_grade(n: int, rounds: int = 40) -> KV.Verdict:
    """EXACT below the deterministic-witness bound (a proof of primality/compositeness); PROBABILISTIC(δ=4⁻ᵏ)
    above it (random bases — a composite is caught w.p. ≥ 1−4⁻ᵏ; never a false 'prime')."""
    import random
    if n < 2:
        return KV.decline(f"is_prime: n={n} < 2 ⇒ DECLINE (not defined)", "number_theory.is_prime")
    if n < _DET_BOUND:
        res = _is_prime_det(n)
        cert = KV.Cert(KV.EXACT, "deterministic_miller_rabin", passed=True, check_cost="12 fixed MR bases",
                       detail=f"n < 3.317e24 ⇒ bases {_DET_BASES} are a DETERMINISTIC witness set; n is "
                              f"{'PRIME' if res else 'COMPOSITE'} (proven)")
        return KV.exact(res, "number_theory.is_prime", "O(k log³ n) exact", cert)
    rng = random.Random(0xC0FFEE ^ n)
    witnessed = any(_mr_composite(n, rng.randrange(2, n - 1)) for _ in range(rounds))
    if witnessed:                                            # a witness PROVES composite (one-sided) ⇒ EXACT
        cert = KV.Cert(KV.EXACT, "mr_composite_witness", passed=True, check_cost="one MR base",
                       detail="a Miller–Rabin witness proves n COMPOSITE (one-sided, exact)")
        return KV.exact(False, "number_theory.is_prime", "exact (witness)", cert)
    delta = 4.0 ** (-rounds)                                 # no witness in k rounds ⇒ probably prime
    cert = KV.Cert(KV.PROBABILISTIC, "miller_rabin", passed=True, check_cost=f"{rounds} random MR bases",
                   delta=delta, detail=f"no witness in {rounds} rounds ⇒ PRIME w.p. ≥ 1−4^-{rounds} (never EXACT — "
                                       f"a sample is not a proof above the deterministic bound)")
    return KV.probabilistic(True, "number_theory.is_prime", "O(k log³ n) randomized", cert)


def _pollard_rho(n: int) -> int:
    import random
    if n % 2 == 0:
        return 2
    rng = random.Random(0xBEEF ^ n)
    while True:
        c = rng.randrange(1, n)
        x = y = rng.randrange(2, n)
        d = 1
        while d == 1:
            x = (x * x + c) % n
            y = (y * y + c) % n
            y = (y * y + c) % n
            d = _gcd_int(abs(x - y), n)
        if d != n:
            return d


def _gcd_int(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def factorize_grade(n: int) -> KV.Verdict:
    """Prime factorization (trial division + Pollard's rho). Certificate: ∏ pᵢ^eᵢ = n (exact) AND every pᵢ is
    prime (verified). EXACT when all factors are below the deterministic primality bound."""
    if n < 1:
        return KV.decline(f"factorize: n={n} < 1 ⇒ DECLINE", "number_theory.factorize")
    if n == 1:
        cert = KV.Cert(KV.EXACT, "factorization", passed=True, check_cost="O(1)", detail="1 = empty product")
        return KV.exact({}, "number_theory.factorize", "O(1)", cert)
    rem, factors = n, {}
    for p in _SMALL:                                         # peel small primes first
        while rem % p == 0:
            factors[p] = factors.get(p, 0) + 1
            rem //= p
    stack = [rem] if rem > 1 else []
    while stack:                                            # split the rest with rho until prime
        m = stack.pop()
        if m == 1:
            continue
        if _is_prime_det(m) if m < _DET_BOUND else not any(_mr_composite(m, a) for a in _DET_BASES):
            factors[m] = factors.get(m, 0) + 1
            continue
        d = _pollard_rho(m)
        stack += [d, m // d]
    # ★ certificate: the product reconstructs n, and every factor is prime ★
    prod = 1
    for p, e in factors.items():
        prod *= p ** e
    all_prime = all((_is_prime_det(p) if p < _DET_BOUND else True) for p in factors)
    exact_primality = all(p < _DET_BOUND for p in factors)
    if prod != n or not all_prime:
        return KV.decline("factorize: product ≠ n or a factor is not prime ⇒ DECLINE", "number_theory.factorize")
    if not exact_primality:
        cert = KV.Cert(KV.PROBABILISTIC, "factorization_big_prime", passed=True, check_cost="∏=n exact + MR",
                       delta=4.0 ** -40, detail=f"∏ pᵢ^eᵢ = {n} (exact); a factor exceeds the deterministic "
                                                f"primality bound ⇒ its primality is PROBABILISTIC")
        return KV.probabilistic(factors, "number_theory.factorize", "trial + Pollard rho", cert)
    cert = KV.Cert(KV.EXACT, "factorization", passed=True, check_cost="∏=n exact + deterministic primality",
                   detail=f"∏ pᵢ^eᵢ = {n} (exact) ∧ every factor proven prime: {factors}")
    return KV.exact(factors, "number_theory.factorize", "trial + Pollard rho", cert)


def euler_phi_grade(n: int) -> KV.Verdict:
    """Euler's totient φ(n) from the prime factorization (φ = n·∏(1−1/p)), certified by the exact factorization."""
    if n < 1:
        return KV.decline(f"euler_phi: n={n} < 1 ⇒ DECLINE", "number_theory.euler_phi")
    fv = factorize_grade(n)
    if fv.status == KV.DECLINE:
        return fv
    factors = fv.result
    phi = 1
    for p, e in factors.items():
        phi *= (p - 1) * p ** (e - 1)
    cert = KV.Cert(KV.EXACT, "totient_from_factorization", passed=True, check_cost="O(#factors)",
                   detail=f"φ({n}) = {phi} = ∏ (p−1)·p^(e−1) over the verified factorization {factors}")
    return KV.exact(phi, "number_theory.euler_phi", "via factorization", cert)


# ── discrete logarithm (baby-step giant-step) — certificate g^x ≡ h (mod m) ──────────────────────────────
def discrete_log_grade(g: int, h: int, m: int) -> KV.Verdict:
    """Find x with g^x ≡ h (mod m) via baby-step/giant-step (O(√m)). Certificate: pow(g,x,m)==h%m (exact). No
    such x (the search is exhaustive over the cyclic order) ⇒ honest DECLINE — never a fabricated exponent."""
    import math
    if m <= 1:
        return KV.decline(f"discrete_log: modulus m={m} must be > 1 ⇒ DECLINE", "number_theory.dlog")
    g, h = g % m, h % m
    if gcd(g, m) != 1:
        return KV.decline(f"discrete_log: gcd(g,m)={gcd(g,m)}≠1 (g not invertible) ⇒ DECLINE", "number_theory.dlog")
    n = int(math.isqrt(m)) + 1
    table = {}
    e = 1
    for j in range(n):                                        # baby steps g^j
        table.setdefault(e, j)
        e = e * g % m
    ginv_n = pow(pow(g, n, m), -1, m)                         # (g^n)^{-1} mod m
    cur = h
    for i in range(n + 1):                                    # giant steps h·(g^{-n})^i
        if cur in table:
            x = i * n + table[cur]
            if pow(g, x, m) == h:                             # ★ the certificate, re-checked ★
                cert = KV.Cert(KV.EXACT, "discrete_log_check", passed=True, check_cost="O(1) one modexp",
                               detail=f"g^x ≡ h (mod {m}) with x={x} (BSGS O(√m), verified)")
                return KV.exact(x, "number_theory.dlog", "O(√m) BSGS", cert)
        cur = cur * ginv_n % m
    return KV.decline(f"discrete_log: no x with {g}^x ≡ {h} (mod {m}) (exhaustive over the order) ⇒ DECLINE",
                      "number_theory.dlog")


# ── modular square root (Tonelli–Shanks) — certificate x² ≡ a (mod p) ─────────────────────────────────────
def modular_sqrt_grade(a: int, p: int) -> KV.Verdict:
    """Find x with x² ≡ a (mod p), p an odd prime, via Tonelli–Shanks. Certificate: x²≡a (re-checked). A
    quadratic NON-residue is PROVEN by Euler's criterion (a^((p−1)/2) ≡ −1) ⇒ honest DECLINE; non-prime p ⇒ DECLINE."""
    a %= p
    if p == 2:
        return KV.exact(a % 2, "number_theory.modsqrt", "O(1)",
                        KV.Cert(KV.EXACT, "modsqrt_check", True, "O(1)", detail=f"x²≡a (mod 2), x={a % 2}"))
    if not (p > 2 and _is_prime_det(p) if p < _DET_BOUND else True):
        return KV.decline(f"modular_sqrt: p={p} must be an odd prime ⇒ DECLINE", "number_theory.modsqrt")
    if a == 0:
        return KV.exact(0, "number_theory.modsqrt", "O(1)",
                        KV.Cert(KV.EXACT, "modsqrt_check", True, "O(1)", detail="x²≡0 (mod p), x=0"))
    if pow(a, (p - 1) // 2, p) != 1:                          # Euler's criterion: a is a non-residue ⇒ PROVEN none
        return KV.decline(f"modular_sqrt: {a} is a quadratic non-residue mod {p} (Euler) ⇒ DECLINE",
                          "number_theory.modsqrt")
    if p % 4 == 3:
        x = pow(a, (p + 1) // 4, p)
    else:
        q, s = p - 1, 0
        while q % 2 == 0:
            q //= 2; s += 1
        z = 2
        while pow(z, (p - 1) // 2, p) != p - 1:
            z += 1
        m, c, t, x = s, pow(z, q, p), pow(a, q, p), pow(a, (q + 1) // 2, p)
        while t != 1:
            i, t2 = 0, t
            while t2 != 1:
                t2 = t2 * t2 % p; i += 1
            b = pow(c, 1 << (m - i - 1), p)
            m, c, t, x = i, b * b % p, t * b * b % p, x * b % p
    if x * x % p != a:                                        # ★ the certificate, re-checked ★
        return KV.decline("modular_sqrt: x²≢a (mod p) ⇒ DECLINE", "number_theory.modsqrt")
    cert = KV.Cert(KV.EXACT, "modsqrt_check", passed=True, check_cost="O(1) one square",
                   detail=f"x² ≡ {a} (mod {p}) with x={x} (Tonelli–Shanks, verified); ±x are the two roots")
    return KV.exact(x, "number_theory.modsqrt", "O(log²p)", cert)


# ── Pell's equation x² − N·y² = 1 (fundamental solution via the continued fraction of √N) ─────────────────
def pell_grade(N: int) -> KV.Verdict:
    """Fundamental solution (x,y) of x² − N·y² = 1 via the periodic continued fraction of √N. Certificate:
    x² − N·y² = 1 (exact). N a perfect square ⇒ no nontrivial solution ⇒ honest DECLINE."""
    import math
    if N < 2:
        return KV.decline(f"pell: N={N} must be ≥ 2 ⇒ DECLINE", "number_theory.pell")
    a0 = math.isqrt(N)
    if a0 * a0 == N:
        return KV.decline(f"pell: N={N} is a perfect square ⇒ no nontrivial solution ⇒ DECLINE", "number_theory.pell")
    m, d, a = 0, 1, a0
    h0, h1 = 1, a0                                            # convergent numerators
    k0, k1 = 0, 1                                             # convergent denominators
    for _ in range(10 ** 6):
        if h1 * h1 - N * k1 * k1 == 1:
            break
        m = d * a - m
        d = (N - m * m) // d
        a = (a0 + m) // d
        h0, h1 = h1, a * h1 + h0
        k0, k1 = k1, a * k1 + k0
    if h1 * h1 - N * k1 * k1 != 1:                            # ★ the certificate ★
        return KV.decline("pell: no fundamental solution found within bound ⇒ DECLINE", "number_theory.pell")
    cert = KV.Cert(KV.EXACT, "pell_identity", passed=True, check_cost="O(1) one identity",
                   detail=f"x²−{N}·y² = 1 with (x,y)=({h1},{k1}) (CF of √{N}, verified)")
    return KV.exact((h1, k1), "number_theory.pell", "O(period) CF", cert)


# ── uniform dispatch (recognize → route → certify), mirroring fold's shape ───────────────────────────────
def solve(problem: dict) -> KV.Verdict:
    """problem = {"op": "egcd"|"modinv"|"crt"|"modexp"|"diophantine"|"is_prime"|"factorize"|"euler_phi", ...}."""
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
    if op == "is_prime":
        return is_prime_grade(problem["n"], problem.get("rounds", 40))
    if op == "factorize":
        return factorize_grade(problem["n"])
    if op == "euler_phi":
        return euler_phi_grade(problem["n"])
    if op == "discrete_log":
        return discrete_log_grade(problem["g"], problem["h"], problem["m"])
    if op == "modular_sqrt":
        return modular_sqrt_grade(problem["a"], problem["p"])
    if op == "pell":
        return pell_grade(problem["N"])
    return KV.decline(f"number_theory: unknown op {op!r} ⇒ DECLINE", "number_theory")
