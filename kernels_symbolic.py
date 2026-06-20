"""
v40 PHASE 3 — algebraic / symbolic closed-form kernels.
========================================================
New EXACT kernels (integer-exact) + registration of the existing C-finite engine into the unified router.
  • 12 Walsh–Hadamard transform : O(n²) → O(n log n), EXACT (involutive certificate).
  • 1  C-finite recurrence n-th term : O(n) → O(log n) via companion-matrix power (cfinite engine; verified).

§0.1: both are COMPUTE collapses (not representation). EXACT = exact integer arithmetic.
"""
from __future__ import annotations

import time
from typing import Any, List

import kernel_verdict as KV
import kernel_router as R


# ── 12 · Walsh–Hadamard transform: O(n²) → O(n log n), EXACT integer (involution certificate) ──────────
def _wht_inplace(a: List[int]) -> List[int]:
    n = len(a)
    h = 1
    while h < n:
        for i in range(0, n, h * 2):
            for j in range(i, i + h):
                x, y = a[j], a[j + h]
                a[j], a[j + h] = x + y, x - y
        h *= 2
    return a


def _wht_detect(d: Any) -> bool:
    if not (isinstance(d, dict) and d.get("kind") == "walsh_hadamard" and isinstance(d.get("data"), list)):
        return False
    n = len(d["data"])
    return n > 0 and (n & (n - 1)) == 0          # power of two


def _wht_run(d: Any, **kw) -> KV.Verdict:
    a = [int(x) for x in d["data"]]
    n = len(a)
    out = _wht_inplace(a[:])
    # fast EXACT certificate: WHT is involutive up to scale — WHT(WHT(x)) = n·x (O(n log n), exact integers)
    back = _wht_inplace(out[:])
    ok = all(back[i] == n * a[i] for i in range(n))
    cert = KV.Cert(KV.EXACT, "wht_involution", passed=ok, check_cost="O(n log n)",
                   detail="Hadamard butterfly; WHT∘WHT = n·I verified (exact integers)")
    if not ok:
        return KV.decline("WHT involution check failed", "walsh_hadamard")
    return KV.exact(out, "walsh_hadamard", "O(n log n) compute", cert)


def measure_wht() -> dict:
    """COMPUTE collapse O(n²)→O(n log n). Crossover vs the naive Hadamard matrix product (±1 entries)."""
    def naive(a):
        n = len(a)
        # H[i,j] = (-1)^popcount(i&j); (H·a)[i] = Σ_j H[i,j] a[j]  → O(n²)
        out = [0] * n
        for i in range(n):
            s = 0
            for j in range(n):
                s += a[j] if bin(i & j).count("1") % 2 == 0 else -a[j]
            out[i] = s
        return out
    crossover, pts = None, []
    import random
    rng = random.Random(0)
    for log in (8, 10, 12):
        n = 1 << log
        a = [rng.randint(-5, 5) for _ in range(n)]
        t = time.perf_counter(); nv = naive(a); tn = (time.perf_counter() - t) * 1000
        t = time.perf_counter(); fv = _wht_run({"kind": "walsh_hadamard", "data": a}); tf = (time.perf_counter() - t) * 1000
        ok = (fv.status == KV.EXACT and fv.result == nv)
        pts.append((n, round(tn, 1), round(tf, 2), ok))
        if crossover is None and tf < tn:
            crossover = n
    return {"kernel": "walsh_hadamard", "collapse": "compute O(n²)→O(n log n)", "crossover_n": crossover,
            "points_(n,naive_ms,wht_ms,exact)": pts, "amdahl_p": "high in spectral/coding inner loops"}


# ── 1 · C-finite recurrence n-th term: O(n) → O(log n) via companion-matrix power (existing engine) ────
def _cfin_detect(d: Any) -> bool:
    return (isinstance(d, dict) and d.get("kind") == "linear_recurrence"
            and isinstance(d.get("c"), list) and isinstance(d.get("init"), list) and "n" in d)


def _cfin_run(d: Any, **kw) -> KV.Verdict:
    import cfinite
    c, init, n = [int(x) for x in d["c"]], [int(x) for x in d["init"]], int(d["n"])
    if len(init) != len(c) or n < 0:
        return KV.decline("linear_recurrence needs len(init)==len(c), n≥0", "cfinite")
    ok, _checked = cfinite.verify_cfinite(c, init)               # companion ≡ naive on a probe set (EXACT, integers)
    if not ok:
        return KV.decline("recurrence failed companion≡naive verification", "cfinite")
    val = cfinite.companion_nth(c, init, n)                      # O(log n) matrix power, exact
    cert = KV.Cert(KV.EXACT, "companion_equiv", passed=True, check_cost="O(d³ log n) probe",
                   detail=f"order-{len(c)} C-finite; companion-matrix power ≡ naive recurrence (exact integers)")
    return KV.exact(val, "cfinite", "O(log n) compute", cert)


def measure_cfinite() -> dict:
    """COMPUTE collapse O(n)→O(log n): companion-matrix power vs naive recurrence iteration (Fibonacci)."""
    import cfinite
    crossover, pts = None, []
    c, init = [1, 1], [0, 1]
    for n in (1000, 20000, 100000):
        t = time.perf_counter(); cfinite.naive_nth(c, init, n); tn = (time.perf_counter() - t) * 1000
        t = time.perf_counter(); cfinite.companion_nth(c, init, n); tf = (time.perf_counter() - t) * 1000
        pts.append((n, round(tn, 1), round(tf, 3)))
        if crossover is None and tf < tn:
            crossover = n
    return {"kernel": "cfinite", "collapse": "compute O(n)→O(log n)", "crossover_n": crossover,
            "points_us": pts, "amdahl_p": "high when the recurrence loop dominates"}


def register_all():
    R.register(R.Kernel(12, "walsh_hadamard", "B",
                        "requires len(data) power of two  ensures WHT(data) exact ∧ grade=EXACT ∧ cost=O(n log n)",
                        _wht_detect, _wht_run))
    R.register(R.Kernel(1, "cfinite", "A",
                        "requires C-finite recurrence (c,init) verified  ensures n-th term exact ∧ grade=EXACT "
                        "∧ cost=O(log n)",
                        _cfin_detect, _cfin_run))


register_all()
