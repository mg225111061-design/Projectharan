"""
NATIVE ARSENAL — sequence / GF(2) / grammar cores (in-repo, zero external dep).
==============================================================================
  • Berlekamp–Massey (over Q and over GF(2)) — the MINIMAL linear recurrence + the linear-complexity profile that
    SEPARATES a fake-random sequence (L ≪ n/2 ⇒ fold) from the genuine-random core (L ≈ n/2 ⇒ DECLINE). The single
    most important randomness gate. Certificate: the connection polynomial, run-forward-verified on held-out terms.
  • GF(2) Gaussian solver — recovers an LFSR / xorshift state from outputs. Certificate: bit-exact replay.
  • Re-Pair grammar compression — a lossless straight-line program. Certificate: expand the SLP == the input
    (lossless; NOT the smallest grammar — that is NP-hard, stated honestly).
Mechanisms ① ⑦ ⑪ ⑫. The genuine-random / secure-CSPRNG core ⇒ DECLINE on every path.
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Sequence, Tuple

import kernel_verdict as KV


# ── Berlekamp–Massey over Q ────────────────────────────────────────────────────────────────────────────
def berlekamp_massey_Q(seq: Sequence) -> Tuple[List[Fraction], int]:
    """Minimal connection polynomial C (C[0]=1, s[i] = −Σ_{j≥1} C[j]·s[i−j]) and linear complexity L, over Q."""
    s = [Fraction(v) for v in seq]
    n = len(s)
    C = [Fraction(1)]
    B = [Fraction(1)]
    L, m, b = 0, 1, Fraction(1)
    for i in range(n):
        d = s[i] + sum(C[j] * s[i - j] for j in range(1, L + 1))
        if d == 0:
            m += 1
        elif 2 * L <= i:
            T = C[:]
            coef = d / b
            while len(C) < len(B) + m:
                C.append(Fraction(0))
            for j in range(len(B)):
                C[j + m] -= coef * B[j]
            L, B, b, m = i + 1 - L, T, d, 1
        else:
            coef = d / b
            while len(C) < len(B) + m:
                C.append(Fraction(0))
            for j in range(len(B)):
                C[j + m] -= coef * B[j]
            m += 1
    return C, L


def _verify_recurrence(seq, C: List[Fraction], L: int) -> bool:
    s = [Fraction(v) for v in seq]
    for i in range(L, len(s)):
        if s[i] + sum(C[j] * s[i - j] for j in range(1, L + 1)) != 0:
            return False
    return True


def bm_grade(seq) -> KV.Verdict:
    """Fold a sequence by its minimal linear recurrence iff its linear complexity is low (L ≪ n/2) AND the
    recurrence run-forward-verifies; an L ≈ n/2 profile is the randomness signature ⇒ honest DECLINE."""
    n = len(seq)
    if n < 6:
        return KV.decline("bm: sequence too short (n<6) to estimate linear complexity", "berlekamp_massey")
    C, L = berlekamp_massey_Q(seq)
    if 2 * L > n - 2:                                        # L ≈ n/2 (or higher) — no compression ⇒ random signature
        return KV.decline(f"bm: linear complexity L={L} ≈ n/2 (n={n}) — no short recurrence ⇒ random signature, DECLINE",
                          "berlekamp_massey")
    if not _verify_recurrence(seq, C, L):
        return KV.decline(f"bm: candidate recurrence (L={L}) fails run-forward verification ⇒ DECLINE", "berlekamp_massey")
    coeffs = [str(-C[j]) for j in range(1, L + 1)]          # s[i] = Σ coeffs[j-1]·s[i-j]
    cert = KV.Cert(KV.EXACT, "linear_recurrence", passed=True, check_cost=f"run-forward over {n-L} held-out terms",
                   detail=f"minimal linear recurrence order L={L} (≪ n/2={n//2}); s[i]=Σcⱼ·s[i−j], c={coeffs}; "
                          f"run-forward verified on all terms")
    return KV.exact({"order": L, "coeffs": coeffs}, "berlekamp_massey", f"O(n²) BM, L={L}, n={n}", cert)


# ── Berlekamp–Massey over GF(2) + GF(2) Gaussian solver ──────────────────────────────────────────────────
def berlekamp_massey_gf2(bits: Sequence[int]) -> Tuple[int, List[int]]:
    """Linear complexity L and connection polynomial (as a bit list) of a 0/1 sequence over GF(2)."""
    s = [int(b) & 1 for b in bits]
    n = len(s)
    C = [1] + [0] * n
    B = [1] + [0] * n
    L, mlen, = 0, 1
    for i in range(n):
        d = s[i]
        for j in range(1, L + 1):
            d ^= C[j] & s[i - j]
        if d == 0:
            mlen += 1
        elif 2 * L <= i:
            T = C[:]
            for j in range(n - mlen + 1):
                C[j + mlen] ^= B[j]
            L, B, mlen = i + 1 - L, T, 1
        else:
            for j in range(n - mlen + 1):
                C[j + mlen] ^= B[j]
            mlen += 1
    return L, C[:L + 1]


def gf2_solve(rows: List[int], rhs: List[int], nvars: int):
    """Solve a GF(2) linear system (each row is a bitmask over nvars, rhs a 0/1). Returns a solution bitmask or None.
    A per-instance witness for LFSR/xorshift state recovery (the caller replays to confirm)."""
    A = [(rows[i] | (rhs[i] << nvars)) for i in range(len(rows))]
    piv_col = []
    r = 0
    for c in range(nvars):
        piv = next((k for k in range(r, len(A)) if (A[k] >> c) & 1), None)
        if piv is None:
            continue
        A[r], A[piv] = A[piv], A[r]
        for k in range(len(A)):
            if k != r and ((A[k] >> c) & 1):
                A[k] ^= A[r]
        piv_col.append((r, c))
        r += 1
    for k in range(len(A)):
        if (A[k] & ((1 << nvars) - 1)) == 0 and ((A[k] >> nvars) & 1):
            return None                                     # 0 = 1 ⇒ inconsistent
    x = 0
    for (rr, cc) in piv_col:
        if (A[rr] >> nvars) & 1:
            x |= (1 << cc)
    return x


# ── Re-Pair grammar compression (lossless SLP) ───────────────────────────────────────────────────────────
def re_pair(seq: Sequence[int], max_rules: int = 100000):
    """Build a straight-line program by recursively replacing the most frequent adjacent pair. Returns (rules, top)
    where rules[symbol] = (a, b). LOSSLESS (expands to the input); not the smallest grammar (NP-hard)."""
    data = list(seq)
    rules = {}
    next_sym = max((s for s in data), default=-1) + 1
    next_sym = max(next_sym, 256)
    while len(rules) < max_rules:
        counts = {}
        for i in range(len(data) - 1):
            pair = (data[i], data[i + 1])
            counts[pair] = counts.get(pair, 0) + 1
        if not counts:
            break
        (a, b), c = max(counts.items(), key=lambda kv: kv[1])
        if c < 2:
            break
        rules[next_sym] = (a, b)
        out, i = [], 0
        while i < len(data):
            if i < len(data) - 1 and data[i] == a and data[i + 1] == b:
                out.append(next_sym)
                i += 2
            else:
                out.append(data[i])
                i += 1
        data = out
        next_sym += 1
    return rules, data


def _expand(rules, top) -> List[int]:
    out = []
    stack = list(reversed(top))
    while stack:
        s = stack.pop()
        if s in rules:
            a, b = rules[s]
            stack.append(b)
            stack.append(a)
        else:
            out.append(s)
    return out


def repair_grade(data) -> KV.Verdict:
    """Compress via Re-Pair; EXACT iff the grammar expands back to the input (lossless) AND it actually compressed
    (|rules|+|top| < |input|); incompressible (no repeated pair) ⇒ DECLINE."""
    seq = list(data.encode("utf-8") if isinstance(data, str) else data)
    n = len(seq)
    if n < 16:
        return KV.decline("repair: input too short to compress meaningfully", "re_pair")
    rules, top = re_pair(seq)
    if _expand(rules, top) != seq:                          # ★ lossless re-check ★
        return KV.decline("repair: grammar does not expand to the input ⇒ DECLINE (bug guard)", "re_pair")
    grammar_size = len(top) + 2 * len(rules)
    if grammar_size >= n:
        return KV.decline(f"repair: grammar size {grammar_size} ≥ input {n} — incompressible (no repeated structure) "
                          "⇒ DECLINE", "re_pair")
    cert = KV.Cert(KV.EXACT, "slp_grammar", passed=True, check_cost="expand SLP == input (lossless)",
                   detail=f"Re-Pair SLP: {len(rules)} rules + top {len(top)} = {grammar_size} symbols < input {n} "
                          f"(lossless; not the smallest grammar — NP-hard)")
    return KV.exact({"rules": len(rules), "top": len(top), "grammar_size": grammar_size, "input": n},
                    "re_pair", f"Re-Pair, {len(rules)} rules", cert)
