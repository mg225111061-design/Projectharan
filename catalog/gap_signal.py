"""
GAP CLOSURE (detection) — signal structure the time/Fourier probes miss, each proposer→EXACT-disposer.
========================================================================================================
  • Gap 7  modulated_grade        — a[n] = ρ·a[n-P] (carrier × period-P pattern); exact ℚ re-synthesis gate.
  • Gap 3  piecewise_grade        — the sequence splits into segments, each its OWN exact recurrence (partial fold).
  • Gap 4  nonfourier_sparse_grade— k-sparse in a non-Fourier basis (Walsh–Hadamard / Haar); exact lossless + sparse.

★ Every disposer is EXACT (integer/ℚ — never float): re-synthesis residual = 0 / lossless round-trip with a sparse
  coefficient support. A random signal is dense in every basis, has no constant modulation ratio, and no segment
  recurrence ⇒ DECLINE on every path. Precision stays 1.0. (Quasi-periodic / almost-periodic structure that is only
  ε-certifiable is handled by the PROBABILISTIC tier in gap_prob.py — never folded EXACT here.)
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Optional

import kernel_verdict as KV


def _is_num_seq(x, lo: int = 8) -> bool:
    return (isinstance(x, (list, tuple)) and len(x) >= lo
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in x))


def _q(v):
    return Fraction(v).limit_denominator(10**12) if isinstance(v, float) else Fraction(v)


# ── Gap 7 — modulated: a[n] = ρ · a[n-P] (carrier ρ^(1/P) × period-P base), exact ℚ re-synthesis ────────
def modulated_grade(seq) -> KV.Verdict:
    if not _is_num_seq(seq):
        return KV.decline("modulated: need a numeric sequence of length ≥ 8", "gap_signal")
    a = [_q(v) for v in seq]
    n = len(a)
    for P in range(2, min(7, n // 2)):                          # P≥2 (P=1 is pure-geometric — BM's job)
        if any(a[i] == 0 for i in range(n - P)):
            continue
        ratios = [a[i + P] / a[i] for i in range(n - P)]
        if len(set(ratios)) != 1:
            continue
        rho = ratios[0]
        if rho == 1:                                            # period-P exactly repeating ⇒ plain periodic, not modulated
            continue
        # EXACT disposer: re-synthesize a[n] = ρ^((i-r)/P)·a[r], r=i%P, residual = 0
        ok = all(a[i] == rho ** (i // P) * a[i % P] for i in range(n))
        if not ok:
            continue
        cert = KV.Cert(KV.EXACT, "modulated", passed=True, check_cost=f"ℚ re-synthesis over {n} terms (period {P})",
                       detail=f"a[n]=ρ·a[n-{P}], ρ={rho}; carrier × period-{P} base regenerates every term, residual=0")
        return KV.exact({"period": P, "rho": str(rho), "base": [str(a[i]) for i in range(P)], "n": n},
                        "gap_signal.modulated", f"modulated (period {P}, ρ={rho})", cert)
    return KV.decline("modulated: no constant period-P modulation ratio ⇒ DECLINE (not carrier×periodic)", "gap_signal")


# ── Gap 3 — piecewise: segment the input, each segment its OWN exact linear recurrence (partial fold) ───
def piecewise_grade(seq, min_seg: int = 8) -> KV.Verdict:
    import native_sequence as NS
    if not _is_num_seq(seq, lo=2 * min_seg):
        return KV.decline(f"piecewise: need length ≥ {2 * min_seg} to admit ≥2 segments", "gap_signal")
    n = len(seq)
    whole = NS.bm_grade(list(seq))
    if whole.status == KV.EXACT:
        return KV.decline("piecewise: the WHOLE sequence is already one linear recurrence (BM) — not piecewise", "gap_signal")
    # scan candidate change-points on a coarse grid; require BOTH segments to certify their own recurrence
    for cut in range(min_seg, n - min_seg + 1):
        left = NS.bm_grade(list(seq[:cut]))
        if left.status != KV.EXACT:
            continue
        right = NS.bm_grade(list(seq[cut:]))
        if right.status != KV.EXACT:
            continue
        cert = KV.Cert(KV.EXACT, "piecewise[composition]", passed=True,
                       check_cost=f"two BM recurrences, each ℚ run-forward certified (cut={cut})",
                       detail=f"segment [0:{cut}] order {left.result['order']} ⊕ [{cut}:{n}] order {right.result['order']}; "
                              "each segment regenerates exactly (partial fold of the structured segments)")
        return KV.exact({"cut": cut, "left_order": left.result["order"], "right_order": right.result["order"],
                         "n": n}, "gap_signal.piecewise", f"piecewise (cut {cut})", cert)
    return KV.decline("piecewise: no change-point splits the input into two exactly-recurrent segments ⇒ DECLINE", "gap_signal")


# ── Gap 4 — non-Fourier sparse: k-sparse in Walsh–Hadamard / Haar (exact, lossless) ────────────────────
def _is_pow2(n: int) -> bool:
    return n >= 4 and (n & (n - 1)) == 0


def _wht(a: List[Fraction]) -> List[Fraction]:
    """Walsh–Hadamard transform (exact, ±1 entries). Self-inverse up to a factor n; length must be a power of 2."""
    a = list(a)
    n = len(a)
    h = 1
    while h < n:
        for i in range(0, n, h * 2):
            for j in range(i, i + h):
                x, y = a[j], a[j + h]
                a[j], a[j + h] = x + y, x - y
        h *= 2
    return a


def _haar(a: List[Fraction]) -> List[Fraction]:
    """Haar wavelet transform (exact ℚ): repeated (average, difference) pyramid; length must be a power of 2."""
    a = list(a)
    n = len(a)
    out = [Fraction(0)] * n
    length = n
    work = list(a)
    pos = n
    while length > 1:
        half = length // 2
        nxt = [Fraction(0)] * half
        for i in range(half):
            s = (work[2 * i] + work[2 * i + 1]) / 2
            d = (work[2 * i] - work[2 * i + 1]) / 2
            nxt[i] = s
            out[pos - half + i] = d                            # detail coefficients at this level
        work = nxt
        pos -= half
        length = half
    out[0] = work[0]                                            # the final scaling coefficient
    return out


def nonfourier_sparse_grade(seq) -> KV.Verdict:
    """Gap 4 — detect k-sparsity in a non-Fourier basis portfolio (Walsh–Hadamard, Haar). EXACT: the transform is
    lossless over ℚ and the coefficient support is sparse (k ≤ n/4) — a compressed exact representation. A signal
    dense in every basis in the portfolio (random) ⇒ DECLINE. Honest limit: the portfolio is finite; structure
    sparse only outside it is missed (DECLINE, not a false positive)."""
    if not _is_num_seq(seq) or not _is_pow2(len(seq)):
        return KV.decline("nonfourier_sparse: need a numeric sequence of power-of-2 length ≥ 4", "gap_signal")
    a = [_q(v) for v in seq]
    n = len(a)
    kmax = max(2, n // 4)
    for name, coeffs in (("walsh_hadamard", _wht(a)), ("haar", _haar(a))):
        nz = [i for i, c in enumerate(coeffs) if c != 0]
        if 0 < len(nz) <= kmax:
            cert = KV.Cert(KV.EXACT, f"nonfourier_sparse[{name}]", passed=True,
                           check_cost=f"lossless {name} transform over ℚ; support |k|={len(nz)} ≤ {kmax}",
                           detail=f"{len(nz)}-sparse in the {name} basis (dense in time/Fourier) — exact compressed form")
            return KV.exact({"basis": name, "k": len(nz), "support": nz[:16], "n": n},
                            "gap_signal.nonfourier", f"{len(nz)}-sparse in {name}", cert)
    return KV.decline("nonfourier_sparse: dense in every basis in the portfolio (Walsh–Hadamard, Haar) ⇒ DECLINE", "gap_signal")
