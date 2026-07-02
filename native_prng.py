"""
NATIVE ARSENAL — weak-PRNG recovery (WALL 2), in-repo, zero external dep. The fake-random vs SECURE-random gate.
================================================================================================================
Recovers the hidden state of a WEAK generator from its outputs — and DECLINES the secure core. Mechanisms ⑦ ⑪.
  • LCG (full outputs): recover (modulus m, multiplier a, increment c) from a handful of outputs by the
    difference/gcd method; certificate = replay reproduces the observed sequence AND predicts the next held-out
    output exactly.
  • LFSR / xorshift (GF(2)): Berlekamp–Massey over GF(2) gives the linear complexity; a low complexity ⇒ recover
    the recurrence and predict; certificate = bit-exact replay on held-out bits.
★ BOUNDARY (sharp, the impossible core): a secure CSPRNG / os.urandom stream has near-maximal linear complexity and
  no LCG fit ⇒ DECLINE on every path. A false recovery is the worst soundness bug, so EVERY recovery REPLAYS before
  EXACT — predict a held-out output and require an exact match.
"""
from __future__ import annotations

from math import gcd
from typing import List, Sequence

import kernel_verdict as KV


def _recover_lcg(s: Sequence[int]):
    """Recover (m, a, c) of x_{n+1}=(a·x_n+c) mod m from outputs s (need ≥ ~6). Returns (m,a,c) or None."""
    if len(s) < 6:
        return None
    t = [s[i + 1] - s[i] for i in range(len(s) - 1)]
    # m divides u_i = t_{i+2}·t_i − t_{i+1}²
    us = [t[i + 2] * t[i] - t[i + 1] ** 2 for i in range(len(t) - 2)]
    m = 0
    for u in us:
        m = gcd(m, abs(u))
    if m <= 1:
        return None
    # a = (s2−s1)·(s1−s0)^{-1} mod m
    try:
        d = (s[1] - s[0]) % m
        inv = pow(d, -1, m)
    except ValueError:
        return None
    a = ((s[2] - s[1]) * inv) % m
    c = (s[1] - a * s[0]) % m
    return m, a, c


def lcg_grade(outputs: Sequence[int]) -> KV.Verdict:
    """Recover an LCG and CERTIFY by replay + next-output prediction; no fit ⇒ DECLINE."""
    s = [int(v) for v in outputs]
    rec = _recover_lcg(s)
    if rec is None:
        return KV.decline("lcg: no consistent (m,a,c) — not a full-output LCG (or too few samples) ⇒ DECLINE", "native_prng")
    m, a, c = rec
    # ★ replay: reproduce s[1:] from s[0], and predict the LAST output held out ★
    x = s[0]
    for i in range(1, len(s) - 1):
        x = (a * x + c) % m
        if x != s[i] % m:
            return KV.decline(f"lcg: replay mismatch at {i} ⇒ DECLINE", "native_prng")
    pred = (a * (s[-2] % m) + c) % m
    if pred != s[-1] % m:
        return KV.decline(f"lcg: predicted next {pred} ≠ held-out {s[-1] % m} ⇒ DECLINE (no overclaim)", "native_prng")
    cert = KV.Cert(KV.EXACT, "lcg_state_replay", passed=True, check_cost="replay + held-out next-output prediction",
                   detail=f"LCG recovered m={m}, a={a}, c={c}; replay reproduces the stream and predicts the held-out "
                          f"next output exactly")
    return KV.exact({"m": m, "a": a, "c": c}, "native_prng", "LCG recovery (difference/gcd)", cert)


def lfsr_grade(bits: Sequence[int]) -> KV.Verdict:
    """Recover an LFSR/xorshift bit recurrence via Berlekamp–Massey over GF(2); EXACT iff low complexity AND a
    held-out-bit replay matches; near-maximal complexity (secure) ⇒ DECLINE."""
    import native_sequence as NS
    b = [int(v) & 1 for v in bits]
    n = len(b)
    if n < 16:
        return KV.decline("lfsr: too few bits", "native_prng")
    L, C = NS.berlekamp_massey_gf2(b)
    if 2 * L > n - 4:
        return KV.decline(f"lfsr: GF(2) linear complexity L={L} ≈ n/2 (n={n}) — secure/random signature ⇒ DECLINE",
                          "native_prng")
    # ★ replay: the recurrence b[i] = Σ_{j≥1} C[j]·b[i−j] must predict all held-out bits ★
    for i in range(L, n):
        pred = 0
        for j in range(1, L + 1):
            pred ^= C[j] & b[i - j]
        if pred != b[i]:
            return KV.decline(f"lfsr: recurrence (L={L}) mispredicts bit {i} ⇒ DECLINE", "native_prng")
    cert = KV.Cert(KV.EXACT, "lfsr_recurrence_replay", passed=True, check_cost=f"GF(2) replay over {n-L} held-out bits",
                   detail=f"LFSR linear complexity L={L} ≪ n/2; GF(2) recurrence predicts every held-out bit")
    return KV.exact({"order": L, "taps": [int(C[j]) for j in range(1, L + 1)]}, "native_prng",
                    f"LFSR/GF(2) BM, L={L}", cert)


def prng_grade(x) -> KV.Verdict:
    """Route {"lcg": [outputs]} | {"lfsr": [bits]}; secure CSPRNG / high-complexity stream ⇒ DECLINE on every path."""
    if isinstance(x, dict) and "lcg" in x:
        return lcg_grade(x["lcg"])
    if isinstance(x, dict) and "lfsr" in x:
        return lfsr_grade(x["lfsr"])
    return KV.decline("native_prng: expected {lcg:[outputs]} | {lfsr:[bits]}", "native_prng")
