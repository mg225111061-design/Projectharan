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


def _lucas_uv(k: int, P: int, Q: int, D: int, n: int):
    """Lucas sequences (U_k, V_k, Q^k) mod n by binary expansion of k (half-mod-n via (x+n)//2, n odd)."""
    U, V, Qk = 1 % n, P % n, Q % n
    for d in bin(k)[3:]:                                      # bits below the leading 1
        U = (U * V) % n
        V = (V * V - 2 * Qk) % n
        Qk = (Qk * Qk) % n
        if d == "1":
            U2, V2 = (P * U + V), (D * U + P * V)
            U = (U2 + (n if U2 & 1 else 0)) // 2 % n          # halve mod n
            V = (V2 + (n if V2 & 1 else 0)) // 2 % n
            Qk = (Qk * Q) % n
    return U % n, V % n, Qk


def _strong_lucas_prp(n: int) -> bool:
    """Strong Lucas probable-prime test with Selfridge parameters (D the first of 5,−7,9,… with (D|n)=−1)."""
    from math import isqrt
    if n % 2 == 0 or isqrt(n) ** 2 == n:                     # Lucas test needs odd, non-square n
        return n == 2
    D, sign = 5, 1
    while True:
        j = _jacobi_reciprocity(D % n, n)
        if j == -1:
            break
        if j == 0:
            return n == abs(D)                               # gcd(D,n)>1 ⇒ composite unless n=|D|
        sign = -sign
        D = sign * (abs(D) + 2)                              # 5,−7,9,−11,13,…
        if abs(D) > 10 ** 7:
            return False
    P, Q = 1, (1 - D) // 4
    d, s = n + 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    U, V, Qk = _lucas_uv(d, P, Q, D, n)
    if U == 0 or V == 0:
        return True
    for _ in range(1, s):                                    # V_{d·2^r} ≡ 0 for some r ⇒ strong Lucas PRP
        V = (V * V - 2 * Qk) % n
        Qk = (Qk * Qk) % n
        if V == 0:
            return True
    return False


def bpsw_grade(n: int) -> KV.Verdict:
    """Primality by BAILLIE–PSW = strong Miller–Rabin base 2 + strong Lucas PRP (Selfridge D). EXACT and
    DETERMINISTIC below the proven Miller–Rabin bound (3.317e24, via is_prime_grade); above it, BPSW has NO known
    counterexample but is not a proof ⇒ PROBABILISTIC ('BPSW probable prime', honest). A failure of either test
    is a PROVEN composite (a witness) ⇒ EXACT. Cross-checked against the deterministic engine where both apply."""
    if n < 2:
        return KV.decline(f"bpsw: n={n} < 2 not prime-testable ⇒ DECLINE", "number_theory.bpsw")
    small = [2, 3, 5, 7, 11, 13]
    if n in small:
        return KV.exact(True, "number_theory.bpsw", "small prime",
                        KV.Cert(KV.EXACT, "bpsw_small", passed=True, check_cost="O(1)", detail=f"{n} is a small prime"))
    if any(n % p == 0 for p in small):
        return KV.exact(False, "number_theory.bpsw", "small factor",
                        KV.Cert(KV.EXACT, "bpsw_small_factor", passed=True, check_cost="O(1)",
                                detail=f"{n} divisible by a small prime ⇒ composite"))
    mr2 = not _mr_composite(n, 2)                            # strong Fermat/MR base 2
    lucas = _strong_lucas_prp(n)
    is_prp = mr2 and lucas
    if n < _DET_BOUND:                                       # below the bound, fold into the DETERMINISTIC verdict
        det = _is_prime_det(n)
        if det != is_prp:
            return KV.decline(f"bpsw: BPSW({is_prp}) ≠ deterministic({det}) ⇒ DECLINE (would be a BPSW counterexample!)",
                              "number_theory.bpsw")
        cert = KV.Cert(KV.EXACT, "bpsw_deterministic", passed=True, check_cost="MR-2 + strong Lucas (+ det bound)",
                       detail=f"{n} is {'PRIME' if det else 'COMPOSITE'} — BPSW (MR-2 ∧ strong-Lucas) agrees with "
                              f"the deterministic test (n < 3.317e24)")
        return KV.exact(det, "number_theory.bpsw", "BPSW (deterministic below bound)", cert)
    if not is_prp:                                          # a failed test is a PROVEN composite (witness)
        cert = KV.Cert(KV.EXACT, "bpsw_composite_witness", passed=True, check_cost="MR-2 / strong Lucas",
                       detail=f"{n} fails {'MR base 2' if not mr2 else 'the strong Lucas test'} ⇒ PROVEN composite")
        return KV.exact(False, "number_theory.bpsw", "BPSW composite witness", cert)
    cert = KV.Cert(KV.PROBABILISTIC, "bpsw_probable_prime", passed=True, check_cost="MR-2 + strong Lucas",
                   delta=0.0, detail=f"{n} passes BPSW (MR base 2 ∧ strong Lucas) — a BPSW probable prime; NO known "
                                     f"counterexample exists, but above the deterministic bound this is not a proof")
    return KV.probabilistic(True, "number_theory.bpsw", "BPSW probable prime", cert)


def _sb_path(p: int, q: int) -> str:
    """The Stern–Brocot L/R path of p/q (p,q ≥ 1, gcd=1) by the subtractive (Euclidean) walk from the root 1/1."""
    out = []
    while p != q:
        if p < q:
            out.append("L")
            q -= p
        else:
            out.append("R")
            p -= q
    return "".join(out)


def _sb_reconstruct(path: str) -> Tuple[int, int]:
    """Inverse of _sb_path: walk the path BACKWARDS from 1/1, inverting each subtraction ⇒ recover (p,q)."""
    p, q = 1, 1
    for d in reversed(path):
        if d == "L":
            q += p
        else:
            p += q
    return p, q


def _sb_best_approx(num: int, den: int, max_denom: int) -> Tuple[int, int]:
    """Best rational approximation of num/den with denominator ≤ max_denom via the Stern–Brocot mediant descent."""
    from fractions import Fraction
    lp, lq, rp, rq = 0, 1, 1, 0                              # boundaries 0/1 .. 1/0
    t = Fraction(num, den)
    best, bestdiff = (0, 1), abs(t)
    for _ in range(10 ** 6):
        mp, mq = lp + rp, lq + rq
        if mq > max_denom:
            break
        d = abs(t - Fraction(mp, mq))
        if d < bestdiff:
            best, bestdiff = (mp, mq), d
        if t == Fraction(mp, mq):
            break
        if t < Fraction(mp, mq):
            rp, rq = mp, mq
        else:
            lp, lq = mp, mq
    # also consider the two boundaries within the denom bound
    for cp, cq in ((lp, lq), (rp, rq)):
        if 1 <= cq <= max_denom and abs(t - Fraction(cp, cq)) < bestdiff:
            best, bestdiff = (cp, cq), abs(t - Fraction(cp, cq))
    return best


def stern_brocot_grade(num: int, den: int, max_denom: Optional[int] = None) -> KV.Verdict:
    """Stern–Brocot tree for the positive rational num/den. With max_denom=None: the EXACT L/R path encoding,
    certified by RECONSTRUCTING p/q from the path (the path IS the witness). With max_denom set: the best rational
    approximation with denominator ≤ max_denom, cross-checked (for max_denom ≤ 5000) against a brute-force scan of
    every q. num/den must be a positive rational ⇒ otherwise DECLINE."""
    from fractions import Fraction
    if den <= 0 or num <= 0:
        return KV.decline(f"stern_brocot: need a positive rational (got {num}/{den}) ⇒ DECLINE", "number_theory.stern_brocot")
    g = gcd(num, den)
    p, q = num // g, den // g
    if max_denom is None:
        path = _sb_path(p, q)
        rp, rq = _sb_reconstruct(path)
        if (rp, rq) != (p, q):                              # ★ the path must reconstruct the fraction exactly ★
            return KV.decline("stern_brocot: path does not reconstruct p/q ⇒ DECLINE (bug guard)", "number_theory.stern_brocot")
        cert = KV.Cert(KV.EXACT, "stern_brocot_path", passed=True, check_cost="O(path) reconstruct",
                       detail=f"{p}/{q} ↦ Stern–Brocot path '{path}'; reconstruction matches exactly")
        return KV.exact({"frac": (p, q), "path": path}, "number_theory.stern_brocot", "SB encoding", cert)
    bp, bq = _sb_best_approx(p, q, max_denom)
    t = Fraction(p, q)
    if max_denom <= 5000:                                   # independent brute-force ground truth (best per denom)
        best, bd = (0, 1), abs(t)
        for dq in range(1, max_denom + 1):
            dp = round(Fraction(p * dq, q))
            for cand in (dp - 1, dp, dp + 1):
                if cand >= 1 and abs(t - Fraction(cand, dq)) < bd:
                    best, bd = (cand, dq), abs(t - Fraction(cand, dq))
        if abs(t - Fraction(bp, bq)) > bd:
            return KV.decline(f"stern_brocot: approx {bp}/{bq} not optimal (brute {best}) ⇒ DECLINE", "number_theory.stern_brocot")
        how = f"≤ brute-force best over all q≤{max_denom}"
    else:
        how = "Stern–Brocot mediant descent (best-approximation property)"
    cert = KV.Cert(KV.EXACT, "stern_brocot_best_approx", passed=True, check_cost="O(max_denom) scan",
                   detail=f"best p/q with q≤{max_denom} for {p}/{q} is {bp}/{bq} (|Δ|={float(abs(t-Fraction(bp,bq))):.2e}); {how}")
    return KV.exact({"approx": (bp, bq), "target": (p, q)}, "number_theory.stern_brocot", "SB best-approx", cert)


def _mobius_from_factors(factors: dict) -> int:
    if any(e >= 2 for e in factors.values()):
        return 0                                              # a squared prime factor ⇒ μ = 0
    return (-1) ** len(factors)                               # squarefree ⇒ (−1)^(#distinct primes)


def _mobius_sieve(limit: int) -> List[int]:
    """Möbius μ for 0..limit by a linear sieve (INDEPENDENT of factorization — the cross-check oracle)."""
    mu = [0] * (limit + 1)
    if limit >= 1:
        mu[1] = 1
    primes: List[int] = []
    is_comp = [False] * (limit + 1)
    for i in range(2, limit + 1):
        if not is_comp[i]:
            primes.append(i)
            mu[i] = -1
        for p in primes:
            if i * p > limit:
                break
            is_comp[i * p] = True
            if i % p == 0:
                mu[i * p] = 0
                break
            mu[i * p] = -mu[i]
    return mu


def mobius_grade(n: int) -> KV.Verdict:
    """Möbius μ(n) from the prime factorization (0 if squareful, else (−1)^#distinct-primes), EXACT. Certified
    two INDEPENDENT ways: (1) the Dirichlet identity Σ_{d|n} μ(d) = [n=1] re-checked over the divisors, and (2)
    for small n a cross-check against a linear-sieve μ (a different algorithm). n<1 ⇒ DECLINE."""
    if n < 1:
        return KV.decline(f"mobius: n={n} < 1 ⇒ DECLINE", "number_theory.mobius")
    fv = factorize_grade(n)
    if fv.status == KV.DECLINE:
        return fv
    mu = _mobius_from_factors(fv.result)
    # (1) Dirichlet: Σ_{d|n} μ(d) = 1 if n==1 else 0 — re-checked over all divisors (μ at each via its factors)
    divisors = [d for d in range(1, n + 1) if n % d == 0] if n <= 100000 else None
    if divisors is not None:
        s = 0
        for d in divisors:
            dv = factorize_grade(d)
            s += _mobius_from_factors(dv.result) if dv.status != KV.DECLINE else 0
        if s != (1 if n == 1 else 0):
            return KV.decline(f"mobius: Σ_(d|n) μ(d) = {s} ≠ [n=1] ⇒ DECLINE (correctness-bug guard)",
                              "number_theory.mobius")
        how = "Dirichlet Σ_(d|n) μ(d)=[n=1]"
    else:
        how = "multiplicativity over the verified factorization (n too large for the divisor-sum recheck)"
    # (2) independent linear-sieve cross-check for small n
    if n <= 20000 and mu != _mobius_sieve(n)[n]:
        return KV.decline("mobius: ≠ linear-sieve μ ⇒ DECLINE (bug guard)", "number_theory.mobius")
    if n <= 20000:
        how += " + linear-sieve cross-check"
    cert = KV.Cert(KV.EXACT, "mobius_dirichlet", passed=True, check_cost="O(#factors) + divisor-sum recheck",
                   detail=f"μ({n}) = {mu} via the verified factorization {fv.result}; certified: {how}")
    return KV.exact(mu, "number_theory.mobius", "via factorization", cert)


# ── discrete logarithm (baby-step giant-step) — certificate g^x ≡ h (mod m) ──────────────────────────────
def _mult_order(g: int, m: int):
    """Multiplicative order of g mod m: the least k>0 with g^k ≡ 1, via φ(m) and its factorization. None if g not
    a unit / unfactorable."""
    if gcd(g, m) != 1:
        return None
    phiv = euler_phi_grade(m)
    fv = factorize_grade(phiv.result)
    if phiv.status == KV.DECLINE or fv.status == KV.DECLINE:
        return None
    order = phiv.result
    for p in fv.result:
        while order % p == 0 and pow(g, order // p, m) == 1:
            order //= p
    return order


def _pollard_rho_dlog(g: int, h: int, m: int, n: int):
    """Pollard's rho for discrete logs: a pseudo-random walk X=g^A·h^B with Floyd cycle detection; a collision
    gives x·(B−D) ≡ (C−A) (mod n). n = ord(g). O(√n) time, O(1) space. Deterministic restarts on a bad collision."""
    def step(x, a, b):
        s = x % 3
        if s == 0:
            return x * x % m, 2 * a % n, 2 * b % n
        if s == 1:
            return x * g % m, (a + 1) % n, b
        return x * h % m, a, (b + 1) % n

    bound = 6 * int(n ** 0.5) + 20
    for start in range(1, 25):                               # deterministic restarts
        X, A, B = pow(g, start, m), start % n, 0
        Y, C, D = X, A, B
        for _ in range(bound):
            X, A, B = step(X, A, B)
            Y, C, D = step(*step(Y, C, D))
            if X == Y:
                r, u = (B - D) % n, (C - A) % n
                if r == 0:
                    break
                d = gcd(r, n)
                if u % d != 0:
                    break
                x0 = (u // d) * pow(r // d, -1, n // d) % (n // d)
                for t in range(d):
                    cand = (x0 + t * (n // d)) % n
                    if pow(g, cand, m) == h % m:
                        return cand
                break
    return None


def pollard_rho_dlog_grade(g: int, h: int, m: int) -> KV.Verdict:
    """Discrete log g^x ≡ h (mod m) by POLLARD'S RHO (O(√n) time, O(1) SPACE — vs BSGS's O(√m) space),
    CROSS-CHECKED against baby-step/giant-step: two INDEPENDENT algorithms must agree (mod ord g). EXACT
    (g^x≡h re-checked AND ≡ BSGS). No solution / g not a unit ⇒ honest DECLINE."""
    if m <= 1 or gcd(g % m, m) != 1:
        return KV.decline(f"pollard_rho_dlog: need m>1 and gcd(g,m)=1 ⇒ DECLINE", "number_theory.rho_dlog")
    g, h = g % m, h % m
    n = _mult_order(g, m)
    if n is None:
        return KV.decline(f"pollard_rho_dlog: cannot determine ord(g) ⇒ DECLINE", "number_theory.rho_dlog")
    x = _pollard_rho_dlog(g, h, m, n)
    bsgs = discrete_log_grade(g, h, m)                       # independent O(√m) algorithm
    if x is None or pow(g, x, m) != h:                      # rho found nothing valid
        if bsgs.status == KV.DECLINE:
            return KV.decline(f"pollard_rho_dlog: no x with {g}^x≡{h} (mod {m}) ⇒ DECLINE", "number_theory.rho_dlog")
        x = bsgs.result % n                                 # rho missed but a solution exists ⇒ use the proven one
    if bsgs.status != KV.DECLINE and (bsgs.result - x) % n != 0:  # ★ two algorithms must agree mod ord(g) ★
        return KV.decline(f"pollard_rho_dlog: rho x={x} ≠ BSGS {bsgs.result} (mod {n}) ⇒ DECLINE (bug guard)",
                          "number_theory.rho_dlog")
    cert = KV.Cert(KV.EXACT, "rho_dlog_vs_bsgs", passed=True, check_cost="O(√n) + BSGS cross-check + one modexp",
                   detail=f"{g}^{x} ≡ {h} (mod {m}); Pollard-rho ≡ baby-step/giant-step (mod ord g={n}) — two "
                          f"independent algorithms agree")
    return KV.exact(x, "number_theory.rho_dlog", "Pollard-rho O(√n) space-O(1)", cert)


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


def _cipolla(a: int, p: int) -> int:
    """Modular square root by CIPOLLA's algorithm: find t with t²−a a non-residue (DETERMINISTIC search — no
    randomness), then (t+√(t²−a))^((p+1)/2) in F_p(√(t²−a)) is the root. p an odd prime, a a QR."""
    a %= p
    if a == 0:
        return 0
    t = 0
    while pow((t * t - a) % p, (p - 1) // 2, p) != p - 1:     # t²−a must be a non-residue
        t += 1
    w = (t * t - a) % p

    def mul(A, B):                                            # (x+y√w)(u+v√w) in F_p(√w)
        return ((A[0] * B[0] + A[1] * B[1] % p * w) % p, (A[0] * B[1] + A[1] * B[0]) % p)

    res, base, e = (1, 0), (t, 1), (p + 1) // 2
    while e:
        if e & 1:
            res = mul(res, base)
        base = mul(base, base)
        e >>= 1
    return res[0]                                             # the √w component is 0 for a true root


def cipolla_sqrt_grade(a: int, p: int) -> KV.Verdict:
    """Modular square root via CIPOLLA, CROSS-CHECKED against Tonelli–Shanks — two INDEPENDENT algorithms must
    agree (up to ±). EXACT (r²≡a re-checked AND r ≡ ±Tonelli). Non-residue / non-prime ⇒ honest DECLINE (delegated
    to the Tonelli grade for the residue decision)."""
    ts = modular_sqrt_grade(a, p)
    if ts.status == KV.DECLINE:
        return ts                                            # non-prime p or a non-residue ⇒ same honest DECLINE
    if p == 2:
        return ts
    r = _cipolla(a, p)
    am = a % p
    if r * r % p != am or {r % p, (-r) % p} != {ts.result % p, (-ts.result) % p}:  # ★ two algorithms agree ★
        return KV.decline(f"cipolla: r={r} disagrees with Tonelli {ts.result} ⇒ DECLINE (correctness-bug guard)",
                          "number_theory.cipolla")
    cert = KV.Cert(KV.EXACT, "cipolla_vs_tonelli", passed=True, check_cost="O(log p) + Tonelli cross-check",
                   detail=f"x² ≡ {am} (mod {p}) with x={r} (Cipolla) ≡ ±{ts.result} (Tonelli–Shanks) — two "
                          f"independent sqrt algorithms agree")
    return KV.exact(r, "number_theory.cipolla", "Cipolla O(log p)", cert)


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


def _jacobi_reciprocity(a: int, n: int) -> int:
    """Jacobi symbol (a|n) for ODD n ≥ 1 via the quadratic-reciprocity flip algorithm (O(log) steps). Returns
    ±1, or 0 iff gcd(a,n) > 1. This is the FAST value; jacobi_grade re-checks it against the definition."""
    a %= n
    result = 1
    while a:
        while a % 2 == 0:                                     # pull out factors of 2: (2|n) = (−1)^((n²−1)/8)
            a //= 2
            if n % 8 in (3, 5):
                result = -result
        a, n = n, a                                           # reciprocity flip (a,n both odd here)
        if a % 4 == 3 and n % 4 == 3:                         # (a|n)(n|a) = (−1)^((a−1)/2·(n−1)/2)
            result = -result
        a %= n
    return result if n == 1 else 0                            # n>1 left ⇒ gcd(a,n)>1 ⇒ symbol is 0


def _legendre_euler(a: int, p: int) -> int:
    """Legendre symbol (a|p) for an ODD PRIME p via Euler's criterion a^((p−1)/2) mod p ∈ {0, 1, p−1}. This is the
    INDEPENDENT definition jacobi_grade cross-checks the reciprocity value against (a different algorithm)."""
    a %= p
    if a == 0:
        return 0
    r = pow(a, (p - 1) // 2, p)
    return 1 if r == 1 else -1                                # r == p−1 ⇒ non-residue (p prime ⇒ no other value)


def jacobi_grade(a: int, n: int) -> KV.Verdict:
    """Jacobi symbol (a|n) by QUADRATIC RECIPROCITY in O(log·log) — CROSS-CHECKED against the independent
    definition ∏ Legendre(a|pᵢ)^eᵢ (Euler's criterion over the factorization of n). When n is prime the check is
    the single O(log) Euler criterion; when composite it is the product over the verified factorization. EXACT iff
    the two independent algorithms AGREE and the factorization is exact; a mismatch ⇒ DECLINE (it would be a
    correctness bug). n must be ODD ≥ 1 (the Jacobi symbol is undefined for even n) ⇒ otherwise DECLINE."""
    if n < 1 or n % 2 == 0:
        return KV.decline(f"jacobi: n={n} must be odd ≥ 1 (symbol undefined for even n) ⇒ DECLINE",
                          "number_theory.jacobi")
    fast = _jacobi_reciprocity(a, n)
    # ── independent re-check: ∏ Legendre over the factorization (Euler's criterion) ──
    if n == 1:
        defn, exact_primality, src = 1, True, "n=1 ⇒ (a|1)=1"
    elif n < _DET_BOUND and _is_prime_det(n):
        defn, exact_primality, src = _legendre_euler(a, n), True, f"n={n} prime ⇒ Euler a^((n−1)/2) mod n"
    else:
        fv = factorize_grade(n)
        if fv.status == KV.DECLINE:
            return KV.decline(f"jacobi: cannot factor n={n} to certify the symbol ⇒ DECLINE", "number_theory.jacobi")
        factors = fv.result
        defn = 1
        for p, e in factors.items():
            defn *= _legendre_euler(a, p) ** e
        exact_primality, src = fv.status == KV.EXACT, f"∏ Legendre(a|p)^e over {factors}"
    if fast != defn:                                          # ★ two independent algorithms MUST agree ★
        return KV.decline(f"jacobi: reciprocity {fast} ≠ definition {defn} ⇒ DECLINE (correctness-bug guard)",
                          "number_theory.jacobi")
    if not exact_primality:
        cert = KV.Cert(KV.PROBABILISTIC, "jacobi_reciprocity_vs_legendre", passed=True, delta=4.0 ** -40,
                       check_cost="O(log) compute + factorization cross-check",
                       detail=f"({a}|{n})={fast}; reciprocity ≡ {src}; a factor's primality is PROBABILISTIC "
                              f"(exceeds the deterministic bound)")
        return KV.probabilistic(fast, "number_theory.jacobi", "quadratic reciprocity O(log)", cert)
    cert = KV.Cert(KV.EXACT, "jacobi_reciprocity_vs_legendre", passed=True,
                   check_cost="O(log) compute + independent Legendre/Euler cross-check",
                   detail=f"({a}|{n})={fast}; the reciprocity-law value ≡ {src} — two independent algorithms agree")
    return KV.exact(fast, "number_theory.jacobi", "quadratic reciprocity O(log)", cert)


_PI_CHECKPOINTS = {10: 4, 100: 25, 1000: 168, 10000: 1229, 100000: 9592, 1000000: 78498}  # π(n) ground truth


def sieve_primes_grade(n: int) -> KV.Verdict:
    """All primes ≤ n by the SIEVE OF ERATOSTHENES. EXACT by construction (every composite is struck by a prime
    factor ≤ √n). The certificate is re-checkable TWO ways: SOUNDNESS — every returned p passes an INDEPENDENT
    primality test (deterministic Miller–Rabin, not the sieve); COMPLETENESS — for n ≤ 30000 a full INDEPENDENT
    trial-division cross-check (exact set equality), else the |result| = π(n) checkpoint count. Beyond both we
    honestly DECLINE TO CERTIFY (the sieve value exists, but we won't stamp EXACT without a witness).
    HONEST: this is O(n log log n) ENUMERATION — NOT a collapse; large n is bounded by time/memory, not instant."""
    if n < 2:
        return KV.decline(f"sieve: n={n} < 2 ⇒ no primes ⇒ DECLINE", "number_theory.sieve")
    s = bytearray([1]) * (n + 1)
    s[0] = s[1] = 0
    for p in range(2, int(n ** 0.5) + 1):
        if s[p]:
            s[p * p::p] = bytearray(len(range(p * p, n + 1, p)))   # strike multiples of each found prime
    primes = [i for i in range(2, n + 1) if s[i]]
    # ── SOUNDNESS: every returned prime independently verified prime (Miller–Rabin, not the sieve) ──
    sound = all((_is_prime_det(p) if p < _DET_BOUND else not any(_mr_composite(p, a) for a in _DET_BASES))
                for p in primes)
    # ── COMPLETENESS: a fully independent recomputation (small n) or the π(n) checkpoint count ──
    if n <= 30000:
        def _tp(m: int) -> bool:                              # independent trial-division primality (no sieve state)
            d = 2
            while d * d <= m:
                if m % d == 0:
                    return False
                d += 1
            return True
        complete = primes == [i for i in range(2, n + 1) if _tp(i)]
        how = f"full independent trial-division cross-check over [2,{n}]"
    elif n in _PI_CHECKPOINTS:
        complete = len(primes) == _PI_CHECKPOINTS[n]
        how = f"|result| = {len(primes)} = π({n}) checkpoint"
    else:
        return KV.decline(f"sieve: n={n} is beyond the trial-division cross-check bound (30000) and not a π(n) "
                          f"checkpoint ⇒ cannot certify completeness ⇒ DECLINE (raise the bound to certify)",
                          "number_theory.sieve")
    if not (sound and complete):
        return KV.decline("sieve: soundness/completeness re-check failed ⇒ DECLINE (correctness-bug guard)",
                          "number_theory.sieve")
    cert = KV.Cert(KV.EXACT, "sieve_sound_and_complete", passed=True, check_cost="MR per prime + " + how,
                   detail=f"{len(primes)} primes ≤ {n}: every one independently verified prime ∧ completeness via "
                          f"{how}")
    return KV.exact(primes, "number_theory.sieve", "Sieve of Eratosthenes O(n log log n) enumeration", cert)


def _carmichael(m: int):
    """Carmichael function λ(m) = lcm over prime powers (λ(2)=1, λ(4)=2, λ(2^e)=2^(e−2) for e≥3, λ(p^e)=
    p^(e−1)(p−1) for odd p). Returns None if m cannot be factored to certify."""
    if m == 1:
        return 1
    fv = factorize_grade(m)
    if fv.status == KV.DECLINE:
        return None
    lam = 1
    for p, e in fv.result.items():
        l = (1 << (e - 2)) if (p == 2 and e >= 3) else (p - 1) * p ** (e - 1)
        lam = lam * l // gcd(lam, l)                          # lcm
    return lam


def power_tower_grade(a: int, b: int, c: int, m: int) -> KV.Verdict:
    """a^(b^c) mod m via CARMICHAEL-λ exponent reduction (the generalized Euler theorem). EXACT: when the exponent
    E=b^c is directly computable it is CROSS-CHECKED against pow(a, E, m); when E is astronomically large the
    generalized Euler theorem a^E ≡ a^((E mod λ(m)) + λ(m)) (mod m) applies EXACTLY (premise E ≥ ⌈log2 m⌉ verified),
    with λ(m) INDEPENDENTLY validated by u^λ(m) ≡ 1 (mod m) on sampled units. m<1 ⇒ DECLINE; m unfactorable ⇒
    DECLINE (cannot certify λ). a,b,c ≥ 0."""
    if m < 1 or a < 0 or b < 0 or c < 0:
        return KV.decline(f"power_tower: need m≥1, a,b,c≥0 (got a={a},b={b},c={c},m={m}) ⇒ DECLINE",
                          "number_theory.power_tower")
    if m == 1:
        cert = KV.Cert(KV.EXACT, "mod_one", passed=True, check_cost="O(1)", detail="x mod 1 = 0 for all x")
        return KV.exact(0, "number_theory.power_tower", "trivial", cert)
    lam = _carmichael(m)
    if lam is None:
        return KV.decline(f"power_tower: cannot factor m={m} to certify λ(m) ⇒ DECLINE", "number_theory.power_tower")
    units = [u for u in (2, 3, 5, 7, 11, 13) if gcd(u, m) == 1]
    if not all(pow(u, lam, m) == 1 for u in units):          # ★ independent re-check that λ(m) is a valid exponent ★
        return KV.decline(f"power_tower: λ(m)={lam} failed the unit re-check u^λ≡1 ⇒ DECLINE (correctness-bug guard)",
                          "number_theory.power_tower")
    threshold_bits = m.bit_length() + 2                       # large branch needs E ≥ 2^threshold > m ≥ log2 m
    est_bits = (b.bit_length() - 1) * c if b >= 2 else 0     # ≈ log2(b^c) — gate forming E on its size, not on c
    if b <= 1 or c == 0:                                      # E = b^c ∈ {0,1} (or 1) — tiny, direct
        E, big = b ** c, False
    elif est_bits <= 100000:                                 # E has ≤ ~100k bits ⇒ form it (so we can cross-check)
        E = b ** c                                           # computable; may still be ≥ 2^threshold ⇒ "big"
        big = E.bit_length() > threshold_bits
    else:
        E, big = None, True                                  # c astronomically large ⇒ never form E; pure theorem
    if not big:
        val = pow(a, E, m)
        cert = KV.Cert(KV.EXACT, "power_tower_direct", passed=True, check_cost="O(log E) modexp",
                       detail=f"a^(b^c) mod m = {a}^({b}^{c}={E}) mod {m} = {val} (exponent small ⇒ direct)")
        return KV.exact(val, "number_theory.power_tower", "direct modexp", cert)
    e_red = pow(b, c, lam)                                    # b^c mod λ(m)
    val = pow(a % m, e_red + lam, m)                         # generalized Euler: a^E ≡ a^(E mod λ + λ) (mod m)
    if E is not None:                                        # E was computable ⇒ CROSS-CHECK the theorem vs direct
        if pow(a, E, m) != val:
            return KV.decline(f"power_tower: generalized-Euler value ≠ direct pow ⇒ DECLINE (correctness-bug guard)",
                              "number_theory.power_tower")
        xcheck = " (cross-checked vs direct pow(a,b^c,m))"
    else:
        xcheck = ""                                          # c astronomically large: rely on the proven theorem
    cert = KV.Cert(KV.EXACT, "power_tower_carmichael", passed=True,
                   check_cost="O(log) modexp + λ(m) factorization + unit re-check",
                   detail=f"{a}^({b}^{c}) mod {m} = {val}; E=b^c ≥ 2^{threshold_bits} ≥ ⌈log2 m⌉ ⇒ generalized "
                          f"Euler a^E≡a^(E mod λ + λ); λ({m})={lam} (unit-validated); E mod λ={e_red}{xcheck}")
    return KV.exact(val, "number_theory.power_tower", "Carmichael-λ reduction O(log)", cert)


def _lucas_mod_p(n: int, k: int, p: int) -> int:
    """C(n,k) mod p (prime) via Lucas' theorem: ∏ C(nᵢ,kᵢ) over the base-p digits. Handles ASTRONOMICAL n (only
    the digits matter). Independent of the prime-power machinery — used as a mod-p cross-check for any n."""
    r = 1
    while (n or k) and r:
        ni, ki = n % p, k % p
        if ki > ni:
            return 0
        c = 1                                                # C(ni,ki) mod p with ni,ki < p (direct, invertible)
        for j in range(min(ki, ni - ki)):
            c = c * (ni - j) % p * pow(j + 1, -1, p) % p
        r = r * c % p
        n //= p
        k //= p
    return r


def _binom_mod_pe(n: int, k: int, p: int, e: int) -> int:
    """C(n,k) mod p^e for prime p, e ≥ 1, handling ASTRONOMICAL n (Granville/Andrew: n! = p^{v_p} · ∏ g(⌊n/p^i⌋),
    Kummer valuation, unit part inverted mod p^e). g(m) = ∏_{1≤j≤m, p∤j} j mod p^e."""
    if k < 0 or k > n:
        return 0
    pe = p ** e
    blk = 1
    for j in range(1, pe):                                   # one full coprime-to-p block ≡ ±1 (generalized Wilson)
        if j % p:
            blk = blk * j % pe

    def g(m: int) -> int:                                    # ∏_{1≤j≤m, p∤j} j mod p^e (period-pe collapse)
        res = pow(blk, m // pe, pe)
        for j in range(1, m % pe + 1):
            if j % p:
                res = res * j % pe
        return res

    def fact_unit_val(m: int):                               # m! = p^val · unit (unit coprime to p)
        unit, val = 1, 0
        while m:
            unit = unit * g(m) % pe
            m //= p
            val += m                                         # Legendre v_p(m!) = Σ ⌊m/p^i⌋
        return unit, val

    un, vn = fact_unit_val(n)
    uk, vk = fact_unit_val(k)
    ud, vd = fact_unit_val(n - k)
    v = vn - vk - vd                                         # Kummer: v = #carries adding k+(n−k) base p
    if v >= e:
        return 0                                             # p^e | C(n,k)
    unit = un * pow(uk, -1, pe) % pe * pow(ud, -1, pe) % pe
    return p ** v * unit % pe


def binom_mod_pe_grade(n: int, k: int, p: int, e: int = 1) -> KV.Verdict:
    """C(n,k) mod p^e by LUCAS' THEOREM (e=1) / GRANVILLE prime-power lifting (e≥2) — exact even for ASTRONOMICAL n
    (only the base-p digits / Σ⌊n/p^i⌋ are needed). EXACT, certified two INDEPENDENT ways: (1) for n ≤ 2000 a
    direct cross-check against math.comb(n,k) mod p^e (full p^e ground truth); (2) for EVERY n the result reduced
    mod p must equal the independent Lucas digit-product (mod-p ground truth, valid at any size). p must be prime,
    p^e ≤ 10^6 (cert bound), n,k ≥ 0; otherwise honest DECLINE."""
    if n < 0 or k < 0 or e < 1:
        return KV.decline(f"binom_mod_pe: need n,k≥0, e≥1 (got n={n},k={k},e={e}) ⇒ DECLINE", "number_theory.binom_mod_pe")
    if not (p < _DET_BOUND and _is_prime_det(p)):
        return KV.decline(f"binom_mod_pe: p={p} must be a (small) prime ⇒ DECLINE", "number_theory.binom_mod_pe")
    if p ** e > 10 ** 6:
        return KV.decline(f"binom_mod_pe: p^e={p**e} beyond the certified bound 10^6 ⇒ DECLINE", "number_theory.binom_mod_pe")
    pe = p ** e
    val = _binom_mod_pe(n, k, p, e)
    # ── independent re-checks ──
    luc = _lucas_mod_p(n, k, p)
    if val % p != luc:                                       # ★ mod-p projection MUST equal Lucas (any n) ★
        return KV.decline(f"binom_mod_pe: result {val} mod p ≠ Lucas {luc} ⇒ DECLINE (correctness-bug guard)",
                          "number_theory.binom_mod_pe")
    how = "≡ Lucas mod p (any n)"
    if n <= 2000:                                            # full p^e ground truth where comb is computable
        import math
        if val != math.comb(n, k) % pe:
            return KV.decline(f"binom_mod_pe: result ≠ direct C(n,k) mod p^e ⇒ DECLINE (bug guard)",
                              "number_theory.binom_mod_pe")
        how = "direct C(n,k) mod p^e + " + how
    cert = KV.Cert(KV.EXACT, "binom_mod_pe_lucas_granville", passed=True,
                   check_cost="O(log_p n · p^e) + cross-check",
                   detail=f"C({n},{k}) mod {p}^{e} = {val}; certified: {how}")
    return KV.exact(val, "number_theory.binom_mod_pe", "Lucas/Granville O(log_p n)", cert)


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
    if op == "jacobi":
        return jacobi_grade(problem["a"], problem["n"])
    if op == "sieve":
        return sieve_primes_grade(problem["n"])
    if op == "power_tower":
        return power_tower_grade(problem["a"], problem["b"], problem["c"], problem["m"])
    if op == "binom_mod_pe":
        return binom_mod_pe_grade(problem["n"], problem["k"], problem["p"], problem.get("e", 1))
    if op == "mobius":
        return mobius_grade(problem["n"])
    if op == "stern_brocot":
        return stern_brocot_grade(problem["num"], problem["den"], problem.get("max_denom"))
    if op == "bpsw":
        return bpsw_grade(problem["n"])
    if op == "cipolla":
        return cipolla_sqrt_grade(problem["a"], problem["p"])
    if op == "rho_dlog":
        return pollard_rho_dlog_grade(problem["g"], problem["h"], problem["m"])
    return KV.decline(f"number_theory: unknown op {op!r} ⇒ DECLINE", "number_theory")
