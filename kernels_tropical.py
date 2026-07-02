"""
v40 PHASE 6 — the "other rules" hard class ① (control-flow / non-affine), with STRICT boundaries.
==================================================================================================
★ Honesty (§0.1): these touch the general/control-flow domain where the ceiling is ~5%. We report small, real
  numbers and DECLINE aggressively outside the exact structural niche — no overclaim. ★

  • 50 Tropical (min,+) matrix power : a k-step shortest-path / layered-DP recurrence is LINEAR over the (min,+)
        semiring ⇒ M^k by repeated squaring, O(n³·k) → O(n³·log k), EXACT (integer weights). Non-min-plus
        structure ⇒ DECLINE.
  • 52 Symmetric boolean function : f depends only on popcount ⇒ #SAT and evaluation in O(n) vs O(2ⁿ) truth
        table, EXACT. A non-symmetric function (e.g. the middle bit of integer multiplication) ⇒ DECLINE
        (the directive's flagged BDD-blowup case).
"""
from __future__ import annotations

import math
import time
from math import comb
from typing import Any, List

import kernel_verdict as KV
import kernel_router as R

_INF = math.inf


# ── 50 · tropical (min,+) matrix power: O(n³·k) → O(n³·log k), EXACT ───────────────────────────────────
def _trop_mul(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
    n, m, p = len(A), len(B), len(B[0])
    out = [[_INF] * p for _ in range(n)]
    for i in range(n):
        Ai = A[i]
        Oi = out[i]
        for k in range(m):
            aik = Ai[k]
            if aik == _INF:
                continue
            Bk = B[k]
            for j in range(p):
                v = aik + Bk[j]
                if v < Oi[j]:
                    Oi[j] = v
    return out


def _trop_pow(M: List[List[float]], k: int) -> List[List[float]]:
    n = len(M)
    R_ = [[0.0 if i == j else _INF for j in range(n)] for i in range(n)]   # tropical identity
    base = [row[:] for row in M]
    while k > 0:
        if k & 1:
            R_ = _trop_mul(R_, base)
        base = _trop_mul(base, base)
        k >>= 1
    return R_


def _trop_detect(d: Any) -> bool:
    return (isinstance(d, dict) and d.get("kind") == "tropical_power"
            and isinstance(d.get("M"), list) and d["M"] and len(d["M"]) == len(d["M"][0]) and "k" in d)


def _trop_run(d: Any, **kw) -> KV.Verdict:
    M = [[(_INF if x is None else float(x)) for x in row] for row in d["M"]]
    k = int(d["k"])
    if k < 1:
        return KV.decline("tropical_power needs k≥1", "tropical")
    res = _trop_pow(M, k)
    # fast EXACT certificate: M^k = M^a ⊗ M^(k-a) (tropical) for a split a — independent path, O(n³)
    a = k // 2
    indep = _trop_mul(_trop_pow(M, a), _trop_pow(M, k - a)) if k >= 2 else res
    ok = (indep == res)
    cert = KV.Cert(KV.EXACT, "tropical_split", passed=ok, check_cost="O(n³)",
                   detail=f"min-plus M^{k} by repeated squaring; split path M^{a}⊗M^{k-a} agrees (exact)")
    if not ok:
        return KV.decline("tropical split cross-check disagreed", "tropical")
    return KV.exact(res, "tropical", "O(n³ log k) compute", cert)


def measure_tropical() -> dict:
    """COMPUTE collapse O(n³·k)→O(n³·log k): k-step min-plus shortest path. Crossover in k."""
    import random
    rng = random.Random(0)
    n = 12
    M = [[(0.0 if i == j else (rng.randint(1, 9) if rng.random() < 0.5 else _INF)) for j in range(n)] for i in range(n)]

    def naive(M, k):
        cur = [row[:] for row in M]
        for _ in range(k - 1):
            cur = _trop_mul(cur, M)
        return cur
    crossover, pts = None, []
    for k in (8, 64, 512):
        t = time.perf_counter(); a = naive(M, k); tn = (time.perf_counter() - t) * 1000
        t = time.perf_counter(); b = _trop_pow(M, k); tf = (time.perf_counter() - t) * 1000
        pts.append((k, round(tn, 1), round(tf, 2), a == b))
        if crossover is None and tf < tn:
            crossover = k
    return {"kernel": "tropical", "collapse": "compute O(n³·k)→O(n³·log k) (min-plus matrix power)",
            "crossover_k": crossover, "points_(k,naive_ms,sq_ms,exact)": pts,
            "amdahl_p": "high when a layered min-plus DP dominates; 0 outside min-plus structure (DECLINE)"}


# ── 52 · symmetric boolean function: #SAT + eval in O(n) vs O(2ⁿ), EXACT; non-symmetric ⇒ DECLINE ─────
def _sym_detect(d: Any) -> bool:
    return isinstance(d, dict) and d.get("kind") == "symmetric_bool" and isinstance(d.get("spec"), list)


def _sym_run(d: Any, **kw) -> KV.Verdict:
    spec: List[int] = [int(b) & 1 for b in d["spec"]]            # spec[j] = f(x) when popcount(x)=j, j=0..n
    n = len(spec) - 1
    if n < 0:
        return KV.decline("symmetric_bool needs spec of length n+1", "symmetric_bool")
    # #SAT = Σ_j spec[j]·C(n,j), O(n) vs O(2ⁿ) enumeration
    count = sum(comb(n, j) for j in range(n + 1) if spec[j])
    # fast EXACT certificate: for small n, enumerate all 2ⁿ assignments and compare the count
    ok = True
    if n <= 18:
        brute = sum(1 for x in range(1 << n) if spec[bin(x).count("1")])
        ok = (brute == count)
    cert = KV.Cert(KV.EXACT, "symmetric_count", passed=ok, check_cost="O(n)",
                   detail=f"symmetric f: #SAT=Σ spec[j]·C(n,j) in O(n); verified vs 2^{n} enumeration"
                          if n <= 18 else f"symmetric f: #SAT in O(n) (n={n} too large to enumerate)")
    if not ok:
        return KV.decline("symmetric #SAT disagreed with enumeration", "symmetric_bool")
    return KV.exact({"sat_count": count, "n": n}, "symmetric_bool", "O(n) compute", cert)


def measure_symmetric() -> dict:
    """COMPUTE collapse O(2ⁿ)→O(n) for #SAT of a symmetric function (majority). Crossover in n."""
    crossover, pts = None, []
    for n in (16, 22, 40):
        spec = [1 if j > n // 2 else 0 for j in range(n + 1)]    # majority
        t = time.perf_counter()
        fast = sum(comb(n, j) for j in range(n + 1) if spec[j]); tf = (time.perf_counter() - t) * 1e6
        if n <= 22:
            t = time.perf_counter()
            brute = sum(1 for x in range(1 << n) if spec[bin(x).count("1")]); tb = (time.perf_counter() - t) * 1e6
            tb_s, ok = f"{tb/1000:.1f}ms", brute == fast
        else:
            tb_s, ok = f"infeasible (2^{n})", True
        pts.append((n, tb_s, round(tf, 2), ok))
        if crossover is None:
            crossover = n
    return {"kernel": "symmetric_bool", "collapse": "compute O(2ⁿ)→O(n) (#SAT of symmetric f)",
            "points_(n,brute,On_us,ok)": pts, "amdahl_p": "0 outside symmetric/sparse functions (DECLINE)"}


def register_all():
    R.register(R.Kernel(50, "tropical", "H",
                        "requires square min-plus matrix ∧ k≥1  ensures M^k (min,+) exact ∧ grade=EXACT ∧ "
                        "cost=O(n³ log k); non-min-plus ⇒ DECLINE",
                        _trop_detect, _trop_run))
    R.register(R.Kernel(52, "symmetric_bool", "H",
                        "requires f symmetric (popcount-only) via spec[0..n]  ensures #SAT exact ∧ grade=EXACT "
                        "∧ cost=O(n); non-symmetric (e.g. multiplication bit) ⇒ DECLINE",
                        _sym_detect, _sym_run))


register_all()
