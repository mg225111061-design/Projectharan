"""
v40 PHASE 2 — structured-matrix kernels (numeric coverage). Displacement structure + verifier registration.
=============================================================================================================
Flagship: a TOEPLITZ matrix-vector product is a CONVOLUTION (displacement rank 2; Kailath–Kung–Morf 1979), so
T·v collapses O(n²)→O(n log n) via the exact-integer NTT (rust_accel, P=998244353).

★ EXACT, soundly ★ NTT computes the convolution mod P. We keep the EXACT grade only when a PROVEN magnitude
  bound guarantees no wraparound: |(T·v)_i| ≤ n·max|t|·max|v| < P/2 ⇒ every entry's true integer is recovered
  exactly (signed mod P). If the bound is exceeded we DECLINE the fast path (multi-modular CRT is the honest
  extension, not done here) — never a wrong/wrapped answer. Certificate = the bound proof + an O(n) spot-check.

Also registers the existing PROBABILISTIC verifier Freivalds(40) into the unified router (reuse, not rebuild).
"""
from __future__ import annotations

import time
from typing import Any, List

import kernel_verdict as KV
import kernel_router as R

_P = 998244353
_HALF = _P // 2


def _to_signed(x: int) -> int:
    return x - _P if x > _HALF else x


def _ntt_conv(a: List[int], b: List[int]) -> List[int]:
    """Exact integer convolution via NTT (rust) with schoolbook fallback. Inputs reduced mod P."""
    import rust_accel as RA
    am = [x % _P for x in a]
    bm = [x % _P for x in b]
    if RA.available():
        out = RA.poly_mul_rust(am, bm)
        if out is not None:
            return out
    return RA.poly_mul_schoolbook(am, bm)


# ── 32 · Toeplitz mat-vec via convolution: O(n²) → O(n log n), EXACT under a proven bound ──────────────
def _toeplitz_detect(d: Any) -> bool:
    return (isinstance(d, dict) and d.get("kind") == "toeplitz_matvec"
            and {"col", "row", "v"} <= d.keys() and len(d["col"]) == len(d["v"]))


def _toeplitz_run(d: Any, **kw) -> KV.Verdict:
    col: List[int] = [int(x) for x in d["col"]]      # first column  (T[i,0] = col[i])
    row: List[int] = [int(x) for x in d["row"]]      # first row     (T[0,j] = row[j]); row[0] must == col[0]
    v: List[int] = [int(x) for x in d["v"]]
    n = len(col)
    if len(row) != n or (n and row[0] != col[0]):
        return KV.decline("toeplitz needs len(row)==len(col) and row[0]==col[0]", "toeplitz_matvec")
    if n == 0:
        return KV.decline("empty system", "toeplitz_matvec")
    # generating sequence t_seq[k] = t[k-(n-1)], k=0..2n-2, where t[d]=col[d] (d≥0), t[-d]=row[d] (d>0)
    t_seq = [row[n - 1 - k] for k in range(n - 1)] + [col[i] for i in range(n)]   # length 2n-1
    # PROVEN no-wraparound bound for EXACT
    bound = n * max((abs(x) for x in (col + row)), default=0) * max((abs(x) for x in v), default=0)
    if bound >= _HALF:
        return KV.decline(f"magnitude bound {bound} ≥ P/2 — NTT could wrap; EXACT not certifiable "
                          f"(multi-modular CRT is the extension) ⇒ DECLINE fast path", "toeplitz_matvec")
    conv = _ntt_conv(t_seq, v)                        # (T·v)_i = conv[i + n - 1]
    res = [_to_signed(conv[i + n - 1] % _P) for i in range(n)]
    # fast EXACT certificate: the bound proves exactness; corroborate with an O(n) spot-check on a few rows
    import random
    rng = random.Random(0)
    rows = rng.sample(range(n), min(6, n))
    spot_ok = all(res[i] == sum(_t(col, row, i, j) * v[j] for j in range(n)) for i in rows)
    cert = KV.Cert(KV.EXACT, "displacement_bound+spotcheck", passed=spot_ok, check_cost="O(n)",
                   detail=f"Toeplitz=convolution (displacement rank 2); proven |entry|<P/2 ⇒ NTT exact; "
                          f"{len(rows)} rows spot-checked vs naive")
    if not spot_ok:
        return KV.decline("toeplitz NTT spot-check disagreed (should be impossible under the bound)", "toeplitz_matvec")
    return KV.exact(res, "toeplitz_matvec", "O(n log n) compute", cert)


def _t(col, row, i, j):
    return col[i - j] if i >= j else row[j - i]


def measure_toeplitz() -> dict:
    """COMPUTE collapse O(n²)→O(n log n) for T·v. Crossover = smallest n where NTT beats naive."""
    import random
    rng = random.Random(1)
    crossover, pts = None, []
    for n in (64, 256, 1024, 4096):
        col = [rng.randint(-3, 3) for _ in range(n)]
        row = [col[0]] + [rng.randint(-3, 3) for _ in range(n - 1)]
        v = [rng.randint(-3, 3) for _ in range(n)]
        t = time.perf_counter()
        naive = [sum(_t(col, row, i, j) * v[j] for j in range(n)) for i in range(n)]
        tn = (time.perf_counter() - t) * 1000
        t = time.perf_counter()
        vd = _toeplitz_run({"kind": "toeplitz_matvec", "col": col, "row": row, "v": v})
        tf = (time.perf_counter() - t) * 1000
        ok = (vd.status == KV.EXACT and vd.result == naive)
        pts.append((n, round(tn, 2), round(tf, 2), ok))
        if crossover is None and tf < tn:
            crossover = n
    return {"kernel": "toeplitz_matvec", "collapse": "compute O(n²)→O(n log n) (Toeplitz=convolution)",
            "crossover_n": crossover, "points_(n,naive_ms,ntt_ms,exact)": pts,
            "amdahl_p": "high when the Toeplitz product dominates (signal/linear-system inner loops)"}


# ── 40 · Freivalds matmul check (existing PROBABILISTIC verifier) registered into the unified router ────
def _matmulchk_detect(d: Any) -> bool:
    return isinstance(d, dict) and d.get("kind") == "matmul_check" and {"A", "B", "C"} <= d.keys()


def _matmulchk_run(d: Any, **kw) -> KV.Verdict:
    import numpy as np
    import freivalds as FV
    k = int(d.get("k", 24))
    sv = FV.verify_matmul((np.asarray(d["A"]), np.asarray(d["B"]), np.asarray(d["C"])), k=k)
    if sv.status == KV.DECLINE:
        return KV.decline(sv.reason, "freivalds")
    c = sv.certificate                                # adapt SublinearVerdict → router Verdict (grades match)
    return KV.probabilistic(sv.result, "freivalds", sv.complexity,
                            KV.Cert(KV.PROBABILISTIC, c.kind, c.passed, c.check_cost,
                                    epsilon=c.epsilon, delta=c.delta, bound=c.bound, detail=c.detail))


def register_all():
    R.register(R.Kernel(32, "toeplitz_matvec", "F",
                        "requires Toeplitz(col,row) ∧ n·max|t|·max|v| < P/2  "
                        "ensures result = T·v exact ∧ grade=EXACT ∧ cost=O(n log n) else DECLINE",
                        _toeplitz_detect, _toeplitz_run))
    R.register(R.Kernel(40, "freivalds", "G",
                        "requires A,B,C matrices  ensures A·B=C verified ∧ grade=PROBABILISTIC(δ=2⁻ᵏ) ∧ "
                        "cost=O(k·n²), one-sided (no false reject)",
                        _matmulchk_detect, _matmulchk_run))


register_all()
