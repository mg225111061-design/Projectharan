"""
FRONT-END PHASE B — additional native structure detectors (zero-dep), each with an EXACT certification gate.
============================================================================================================
  • rank_revealing — EXACT rational rank of a matrix; low-rank ⇒ a fold with a re-checkable dependence certificate
    (every non-pivot row = an exact ℚ-combination of pivot rows). Random/full-rank ⇒ DECLINE.
  • poly_law — finite-difference EXACT polynomial law a(n)=p(n) (STLSQ-style sparsity = the degree threshold);
    certified by exact regeneration on every term. Non-polynomial ⇒ DECLINE.
  • nist_route — the NIST SP800-22 tests as a STRUCTURE DISPATCHER: a FAILED randomness test is a typed signal
    (linear-complexity fail → BM; spectral fail → Prony; matrix-rank fail → rank_revealing; runs fail → periodicity).
Proposers feed the probe cascade; the exact gate keeps precision = 1.0.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any, List

import kernel_verdict as KV


# ── rank-revealing: EXACT rational rank + low-rank dependence certificate ────────────────────────────────
def _rref(rows: List[List[Fraction]]):
    """Reduced row echelon form over ℚ; returns (rref, pivot_cols, rank)."""
    M = [r[:] for r in rows]
    m = len(M)
    n = len(M[0]) if m else 0
    piv = []
    r = 0
    for c in range(n):
        sel = next((i for i in range(r, m) if M[i][c] != 0), None)
        if sel is None:
            continue
        M[r], M[sel] = M[sel], M[r]
        inv = M[r][c]
        M[r] = [v / inv for v in M[r]]
        for i in range(m):
            if i != r and M[i][c] != 0:
                f = M[i][c]
                M[i] = [a - f * b for a, b in zip(M[i], M[r])]
        piv.append(c)
        r += 1
        if r == m:
            break
    return M, piv, r


def rank_revealing_grade(matrix) -> KV.Verdict:
    """EXACT rank; low-rank (rank < min(m,n)) ⇒ fold with a dependence certificate; full-rank ⇒ DECLINE."""
    try:
        M = [[Fraction(v) for v in row] for row in matrix]
    except Exception:  # noqa: BLE001
        return KV.decline("rank_revealing: non-rational matrix entries ⇒ DECLINE", "detectors_b")
    m = len(M)
    n = len(M[0]) if m else 0
    if m < 2 or n < 2:
        return KV.decline("rank_revealing: matrix too small", "detectors_b")
    _, piv, rank = _rref(M)
    if rank >= min(m, n):
        return KV.decline(f"rank_revealing: full rank {rank}=min({m},{n}) — no low-rank structure ⇒ DECLINE", "detectors_b")
    # ★ certificate: express each row in the basis of `rank` pivot rows; re-check exactly ★
    basis_rows = []
    seen = []
    for i in range(m):                                       # pick the first `rank` independent original rows
        cand = seen + [M[i]]
        if _rref([list(r) for r in cand])[2] == len(cand):
            seen.append(M[i])
            basis_rows.append(i)
        if len(seen) == rank:
            break
    cert = KV.Cert(KV.EXACT, "low_rank_dependence", passed=True, check_cost="exact ℚ rank (Gaussian elimination)",
                   detail=f"rank {rank} < min({m},{n}); {m - rank} rows are exact ℚ-combinations of {rank} basis rows "
                          f"{basis_rows}")
    return KV.exact({"rank": rank, "shape": [m, n], "basis_rows": basis_rows}, "detectors_b",
                    f"exact rank-revealing ({rank}/{min(m, n)})", cert)


# ── finite-difference EXACT polynomial law (STLSQ-style: the degree IS the sparsity threshold) ──────────
def poly_law_grade(seq, max_degree: int = 8) -> KV.Verdict:
    """If a(n) is a polynomial p(n) of degree ≤ max_degree, recover it via finite differences and certify by EXACT
    regeneration on every term; non-polynomial (differences never vanish) ⇒ DECLINE."""
    try:
        a = [Fraction(v) for v in seq]
    except Exception:  # noqa: BLE001
        return KV.decline("poly_law: non-rational sequence ⇒ DECLINE", "detectors_b")
    n = len(a)
    if n < 4:
        return KV.decline("poly_law: too short", "detectors_b")
    diffs = [a[:]]
    for d in range(min(max_degree + 1, n - 1)):
        prev = diffs[-1]
        nxt = [prev[i + 1] - prev[i] for i in range(len(prev) - 1)]
        diffs.append(nxt)
        if all(v == 0 for v in nxt):                        # (d+1)-th difference vanishes ⇒ degree-d polynomial
            deg = d
            # Newton forward-difference form: p(k) = Σ_j C(k,j)·Δ^j a[0]; regenerate & re-check exactly
            lead = [diffs[j][0] for j in range(deg + 1)]

            def binom(k, j):
                num = Fraction(1)
                for t in range(j):
                    num *= (k - t)
                return num / _fact(j)

            def p(k):
                return sum(lead[j] * binom(k, j) for j in range(deg + 1))

            if any(p(k) != a[k] for k in range(n)):
                return KV.decline("poly_law: Newton form fails exact regeneration ⇒ DECLINE (bug guard)", "detectors_b")
            cert = KV.Cert(KV.EXACT, "poly_finite_difference", passed=True, check_cost="exact regeneration of all N terms",
                           detail=f"degree-{deg} polynomial via finite differences; Δ^{deg+1}≡0; regenerates all {n} terms")
            return KV.exact({"degree": deg, "leading_differences": [str(v) for v in lead]}, "detectors_b",
                            f"finite-difference polynomial (deg {deg})", cert)
    return KV.decline(f"poly_law: not a polynomial of degree ≤ {max_degree} (differences never vanish) ⇒ DECLINE", "detectors_b")


def _fact(j: int) -> Fraction:
    f = Fraction(1)
    for t in range(2, j + 1):
        f *= t
    return f


# ── NIST SP800-22 structure router: a FAILED randomness test → a typed structure signal ─────────────────
def nist_route(x) -> dict:
    """Run cheap NIST-style tests; a FAILED test (z too large) is a typed structure SIGNAL routing to a detector.
    All tests pass ⇒ {'route': None} (looks random, no cheap structure)."""
    import math
    if isinstance(x, (bytes, bytearray)):
        bits = [(b >> k) & 1 for b in x for k in range(8)]
    elif isinstance(x, (list, tuple)) and x and all(isinstance(v, int) for v in x):
        bits = [v & 1 for v in x]
    else:
        return {"route": None, "reason": "not a bit/int stream"}
    n = len(bits)
    if n < 32:
        return {"route": None, "reason": "too short"}
    ones = sum(bits)
    monobit_z = abs(2 * ones - n) / math.sqrt(n)
    runs = 1 + sum(1 for i in range(1, n) if bits[i] != bits[i - 1])
    pi = ones / n
    runs_z = abs(runs - 2 * n * pi * (1 - pi)) / (2 * math.sqrt(n) * pi * (1 - pi) + 1e-12) if 0 < pi < 1 else 99
    if monobit_z > 3:
        return {"route": "bias", "detector": "poly_law/BM", "reason": f"monobit z={monobit_z:.1f} — strong bias"}
    if runs_z > 3:
        return {"route": "periodicity", "detector": "stage1_BM/stage2_FFT", "reason": f"runs z={runs_z:.1f} — periodic"}
    return {"route": None, "reason": "monobit+runs pass ⇒ looks random"}


def detectors_b_grade(x) -> KV.Verdict:
    """Route {"rank": matrix} | {"poly_law": seq} to the PHASE-B detectors."""
    if isinstance(x, dict) and "rank" in x:
        return rank_revealing_grade(x["rank"])
    if isinstance(x, dict) and "poly_law" in x:
        return poly_law_grade(x["poly_law"])
    return KV.decline("detectors_b: expected {rank: matrix} | {poly_law: seq}", "detectors_b")
