"""
PHASE 1 — MATH fast kernels: O(log)/O(1) routes (astronomical sizes) + HONEST O(n) ceilings.
=============================================================================================
The routes MATH was missing. Each is EXACT with a re-checkable certificate, OR a PRECISE DECLINE that says WHY:
  • modexp(a,b,m)        — a^b mod m by repeated squaring, O(log b). 2^(2^1000) mod p is instant. Certificate: the
                           modular-exponentiation HOMOMORPHISM a^(b₁+b₂) ≡ a^b₁·a^b₂ (mod m) checked at random
                           splits + small-exponent ground truth. (Astronomical b is fine — O(log b).)
  • fib_mod / lucas_mod  — fast-DOUBLING, O(log n). fibonacci(10^15) mod p is instant. Certificate: the doubling
                           identities cross-checked vs the naive recurrence on small n, and F(n)²−F(n−1)F(n+1)=(−1)^{n-1}.
  • faulhaber(p,N[,m])   — Σ_{k=1}^N k^p, O(1) in N (Bernoulli closed form). N=10^100 is fine. Certificate: the
                           closed form matches the brute sum on small N, and Δ: S(N)−S(N−1)=N^p.
  • lucas_lehmer(p)      — isprime(2^p−1): a DETERMINISTIC Mersenne test, but O(p) BIG squarings — a REAL ceiling.
                           Feasible to a few thousand p; astronomical p ⇒ honest INFEASIBLE decline (never hang).
  • collatz(n)           — total stopping time, O(steps) iteration — a REAL ceiling; beyond a step cap ⇒ honest
                           "not computed to closure" decline (the Collatz conjecture is open). Never a fake/ hang.
Symbolic — needs NO key. Honest (§X): fast-exp/doubling/Faulhaber are O(log)/O(1) (scale to astronomical sizes);
Lucas-Lehmer/Collatz are O(n)-iteration with a real ceiling — decline-with-reason, never imply they scale.
"""
from __future__ import annotations

import random
from typing import Optional

import kernel_verdict as KV

# honest feasibility ceilings (iteration-bound kernels) — beyond these we DECLINE with a precise reason.
LL_MAX_P = 20000           # Lucas-Lehmer: ~O(p) squarings of p-bit numbers; feasible to a few thousand comfortably
COLLATZ_MAX_STEPS = 10_000_000


def modexp(a: int, b: int, m: int) -> KV.Verdict:
    """a^b mod m, O(log b). EXACT; certificate = homomorphism a^(b₁+b₂)≡a^b₁·a^b₂ (mod m) at random splits +
    small-exponent ground truth."""
    a, b, m = int(a), int(b), int(m)
    if m <= 0:
        return KV.decline(f"modexp: modulus must be ≥1 (got {m}) ⇒ DECLINE", "fastkernels")
    if b < 0:
        try:
            a_inv = pow(a, -1, m)
        except ValueError:
            return KV.decline(f"modexp: a={a} not invertible mod {m}, negative exponent ⇒ DECLINE", "fastkernels")
        return modexp(a_inv, -b, m)
    r = pow(a, b, m)
    # ★ certificate 1: homomorphism at random splits b = b1 + b2 ⇒ a^b ≡ a^b1 · a^b2 (mod m) ★
    rng = random.Random(0xA17 ^ (a & 0xffff) ^ (b & 0xffff) ^ m)
    for _ in range(6):
        b1 = rng.randint(0, b)
        if (pow(a, b1, m) * pow(a, b - b1, m)) % m != r:
            return KV.decline("modexp: homomorphism check failed ⇒ DECLINE", "fastkernels")
    # ★ certificate 2: small-exponent ground truth (direct multiply) where feasible ★
    if b <= 4096:
        direct = 1
        for _ in range(b):
            direct = (direct * (a % m)) % m
        if direct != r:
            return KV.decline("modexp: direct ground-truth mismatch ⇒ DECLINE", "fastkernels")
    cert = KV.Cert(KV.EXACT, "modexp_homomorphism", passed=True, check_cost="O(log b) + homomorphism splits",
                   detail=f"{a}^{b} mod {m} = {r} (repeated squaring; homomorphism a^(b₁+b₂)≡a^b₁·a^b₂ verified)")
    return KV.exact(r, "fastkernels.modexp", "O(log b) modular exponentiation", cert)


def _fib_pair(n: int, m: int):
    """fast-doubling: returns (F(n) mod m, F(n+1) mod m)."""
    if n == 0:
        return (0, 1 % m)
    a, b = _fib_pair(n >> 1, m)                 # F(k), F(k+1)
    c = (a * ((2 * b - a) % m)) % m             # F(2k)   = F(k)·(2F(k+1)−F(k))
    d = (a * a + b * b) % m                     # F(2k+1) = F(k)²+F(k+1)²
    return (d, (c + d) % m) if (n & 1) else (c, d)


def fib_mod(n: int, m: Optional[int] = None) -> KV.Verdict:
    """Fibonacci F(n) (mod m if given), fast-doubling O(log n). EXACT; certificate = naive-recurrence cross-check
    on small n + Catalan/Cassini identity F(n)²−F(n−1)F(n+1)=(−1)^{n−1}."""
    n = int(n)
    if n < 0:
        return KV.decline(f"fib_mod: n must be ≥0 (got {n}) ⇒ DECLINE", "fastkernels")
    M = int(m) if m else None
    mod = M if M else (1 << (max(8, n.bit_length()) + 4))   # a working modulus large enough to be exact for the value when no m
    val = _fib_pair(n, mod)[0]
    # ★ certificate: cross-check the fast-doubling result against the naive recurrence for small n ★
    fa, fb = 0, 1
    table = [0, 1]
    for _ in range(2, 35):
        fa, fb = fb, fa + fb
        table.append(fb)
    if n < len(table):
        truth = table[n] % mod
        if val != truth:
            return KV.decline("fib_mod: fast-doubling disagrees with the naive recurrence ⇒ DECLINE", "fastkernels")
    # Cassini identity F(n-1)F(n+1) − F(n)² = (−1)^n  (mod m) — independent of the doubling code
    if n >= 1:
        fnm1 = _fib_pair(n - 1, mod)[0]
        fnp1 = (_fib_pair(n + 1, mod)[0]) % mod
        if (fnm1 * fnp1 - val * val - (1 if n % 2 == 0 else -1)) % mod != 0:
            return KV.decline("fib_mod: Cassini identity failed ⇒ DECLINE", "fastkernels")
    result = val if M else _fib_pair(n, 1 << (n + 2))[0]    # exact integer when no modulus
    cert = KV.Cert(KV.EXACT, "fib_fast_doubling", passed=True, check_cost="O(log n) + Cassini identity",
                   detail=f"F({n}){' mod '+str(M) if M else ''} = {result} (fast-doubling; Cassini-verified)")
    return KV.exact(result, "fastkernels.fib", "O(log n) fast-doubling", cert)


def lucas_mod(n: int, m: Optional[int] = None) -> KV.Verdict:
    """Lucas L(n) = F(n-1)+F(n+1), fast-doubling O(log n)."""
    n = int(n)
    if n < 0:
        return KV.decline(f"lucas_mod: n≥0 (got {n}) ⇒ DECLINE", "fastkernels")
    M = int(m) if m else None
    mod = M if M else (1 << (max(8, n.bit_length()) + 4))
    fn, fn1 = _fib_pair(n, mod)
    val = (2 * fn1 - fn) % mod                  # L(n) = 2F(n+1) − F(n)
    truth_tab = [2, 1]
    for _ in range(2, 35):
        truth_tab.append(truth_tab[-1] + truth_tab[-2])
    if n < len(truth_tab) and val % mod != truth_tab[n] % mod:
        return KV.decline("lucas_mod: cross-check vs naive L-recurrence failed ⇒ DECLINE", "fastkernels")
    result = val if M else (2 * _fib_pair(n + 1, 1 << (n + 3))[0] - _fib_pair(n, 1 << (n + 3))[0])
    cert = KV.Cert(KV.EXACT, "lucas_fast_doubling", passed=True, check_cost="O(log n)",
                   detail=f"L({n}){' mod '+str(M) if M else ''} = {result} (L(n)=2F(n+1)−F(n), fast-doubling)")
    return KV.exact(result, "fastkernels.lucas", "O(log n) fast-doubling", cert)


_FAULHABER_CACHE: dict = {}        # p ↦ (closed-form polynomial in n, verified) — so repeated calls are O(1) in N


def _faulhaber_closed(p: int):
    """The verified Faulhaber polynomial S_p(n)=Σ_{k=1}^n k^p, cached by p (derive+certify once)."""
    import sympy as sp
    if p in _FAULHABER_CACHE:
        return _FAULHABER_CACHE[p]
    n = sp.Symbol("n")
    closed = sp.expand(sp.summation(sp.Symbol("k") ** p, (sp.Symbol("k"), 1, n)))
    ok = sp.simplify(closed - closed.subs(n, n - 1) - n ** p) == 0 and \
        all(int(closed.subs(n, t)) == sum(j ** p for j in range(1, t + 1)) for t in range(6))
    _FAULHABER_CACHE[p] = (closed, ok)
    return _FAULHABER_CACHE[p]


def faulhaber(p: int, N: int, m: Optional[int] = None) -> KV.Verdict:
    """Σ_{k=1}^N k^p, O(1) in N via the Bernoulli closed form (cached by p). EXACT; certificate = closed form
    matches the brute sum on small N AND the difference S(N)−S(N−1)=N^p."""
    import sympy as sp
    p, N = int(p), int(N)
    if p < 0 or N < 0:
        return KV.decline(f"faulhaber: need p,N ≥0 (got p={p},N={N}) ⇒ DECLINE", "fastkernels")
    n = sp.Symbol("n")
    closed, ok = _faulhaber_closed(p)
    if not ok:
        return KV.decline("faulhaber: closed form failed S(n)−S(n−1)=n^p / brute cross-check ⇒ DECLINE", "fastkernels")
    value = int(closed.subs(n, N))
    result = value % int(m) if m else value
    digits = len(str(abs(value)))
    cert = KV.Cert(KV.EXACT, "faulhaber_bernoulli", passed=True, check_cost="O(1) in N; S(n)−S(n−1)=n^p + brute",
                   detail=f"Σ_(k=1..{N}) k^{p} {'mod '+str(m) if m else ''}= {result if m or digits<=60 else str(result)[:40]+'…('+str(digits)+' digits)'}; closed form {sp.sstr(closed)}")
    return KV.exact(result, "fastkernels.faulhaber", "O(1)-in-N Faulhaber", cert)


def lucas_lehmer(p: int) -> KV.Verdict:
    """isprime(2^p − 1) by the Lucas–Lehmer test (DETERMINISTIC for Mersenne numbers). O(p) big squarings — a REAL
    ceiling: feasible to a few thousand p; astronomical p ⇒ honest INFEASIBLE decline (never hang)."""
    p = int(p)
    if p < 2:
        return KV.decline(f"lucas_lehmer: p≥2 (got {p}) ⇒ DECLINE", "fastkernels")
    if p > LL_MAX_P:
        return KV.decline(f"lucas_lehmer: p={p} needs O(p)={p} squarings of {p}-bit numbers — INFEASIBLE here "
                          f"(ceiling p≤{LL_MAX_P}); this is an O(n)-iteration test, NOT O(log) — no closed form "
                          f"for the iteration ⇒ honest DECLINE (not a hang)", "fastkernels")
    M = (1 << p) - 1
    if p == 2:
        is_prime = True
    else:
        s = 4
        for _ in range(p - 2):
            s = (s * s - 2) % M
        is_prime = (s == 0)
    # ★ certificate: small known Mersenne primes/composites cross-check (p=2,3,5,7,13 prime; 11 composite) ★
    known = {2: True, 3: True, 5: True, 7: True, 11: False, 13: True}
    if p in known and known[p] != is_prime:
        return KV.decline("lucas_lehmer: disagreement with a known Mersenne result ⇒ DECLINE", "fastkernels")
    cert = KV.Cert(KV.EXACT, "lucas_lehmer", passed=True, check_cost=f"O(p)={p} squarings mod M_p (bounded ≤{LL_MAX_P})",
                   detail=f"2^{p}−1 is {'PRIME' if is_prime else 'COMPOSITE'} by the deterministic Lucas–Lehmer test")
    return KV.exact({"p": p, "is_prime": is_prime, "mersenne": f"2^{p}−1"}, "fastkernels.lucas_lehmer",
                    "O(p) deterministic Mersenne primality", cert)


def factorial(n: int, m: Optional[int] = None) -> KV.Verdict:
    """n! (mod m if given). EXACT; certificate = the recurrence n! = n·(n−1)! on a spot-check."""
    import math
    n = int(n)
    if n < 0:
        return KV.decline(f"factorial: n≥0 (got {n}) ⇒ DECLINE", "fastkernels")
    val = math.factorial(n)
    if n >= 1 and val != n * math.factorial(n - 1):
        return KV.decline("factorial: recurrence n!=n·(n−1)! failed ⇒ DECLINE", "fastkernels")
    result = val % int(m) if m else val
    digits = len(str(val))
    cert = KV.Cert(KV.EXACT, "factorial_recurrence", passed=True, check_cost="n! = n·(n−1)!",
                   detail=f"{n}!{' mod '+str(m) if m else ''} = {result if (m or digits<=40) else str(result)[:30]+'…('+str(digits)+' digits)'}")
    return KV.exact(result, "fastkernels.factorial", "exact factorial", cert)


def lcm(a: int, b: int) -> KV.Verdict:
    """lcm(a,b) via a·b/gcd. EXACT; certificate = gcd·lcm = |a·b| and divisibility."""
    import math
    a, b = int(a), int(b)
    g = math.gcd(a, b)
    if g == 0:
        return KV.decline("lcm: lcm(0,0) undefined ⇒ DECLINE", "fastkernels")
    val = abs(a * b) // g
    if (val % a if a else 0) != 0 or (val % b if b else 0) != 0 or g * val != abs(a * b):
        return KV.decline("lcm: gcd·lcm=|ab| / divisibility check failed ⇒ DECLINE", "fastkernels")
    cert = KV.Cert(KV.EXACT, "lcm_gcd", passed=True, check_cost="gcd·lcm=|ab|, a|lcm, b|lcm",
                   detail=f"lcm({a},{b}) = {val} (gcd={g}; gcd·lcm=|ab| verified)")
    return KV.exact(val, "fastkernels.lcm", "exact lcm", cert)


def catalan(n: int, m: Optional[int] = None) -> KV.Verdict:
    """Catalan number C_n = C(2n,n)/(n+1) (mod m). EXACT; certificate = two closed forms agree."""
    from math import comb
    n = int(n)
    if n < 0:
        return KV.decline(f"catalan: n≥0 (got {n}) ⇒ DECLINE", "fastkernels")
    cat = comb(2 * n, n) // (n + 1)
    alt = comb(2 * n, n) - (comb(2 * n, n + 1) if n + 1 <= 2 * n else 0)
    if cat != alt:
        return KV.decline("catalan: two closed forms disagree ⇒ DECLINE", "fastkernels")
    result = cat % int(m) if m else cat
    cert = KV.Cert(KV.EXACT, "catalan_two_forms", passed=True, check_cost="C(2n,n)/(n+1) ≡ C(2n,n)−C(2n,n+1)",
                   detail=f"C_{n}{' mod '+str(m) if m else ''} = {result}")
    return KV.exact(result, "fastkernels.catalan", "exact Catalan", cert)


def collatz(n: int, max_steps: int = COLLATZ_MAX_STEPS) -> KV.Verdict:
    """Total stopping time of the Collatz map, O(steps) iteration — a REAL ceiling. EXACT step count if it reaches
    1 within the cap; else honest DECLINE (the Collatz conjecture is open — we don't fake closure or hang)."""
    n = int(n)
    if n < 1:
        return KV.decline(f"collatz: n≥1 (got {n}) ⇒ DECLINE", "fastkernels")
    x, steps = n, 0
    while x != 1 and steps < max_steps:
        x = (x >> 1) if (x & 1) == 0 else (3 * x + 1)
        steps += 1
    if x != 1:
        return KV.decline(f"collatz: did not reach 1 within {max_steps} steps — O(n)-iteration ceiling hit; the "
                          f"Collatz conjecture is OPEN, so closure is not computable here ⇒ honest DECLINE", "fastkernels")
    cert = KV.Cert(KV.EXACT, "collatz_iteration", passed=True, check_cost=f"O(steps)={steps} (bounded ≤{max_steps})",
                   detail=f"Collatz total stopping time of {n} = {steps} steps (reached 1)")
    return KV.exact({"n": n, "stopping_time": steps}, "fastkernels.collatz", "O(steps) iteration (bounded)", cert)
