"""
STAGE 2 — Clock B (verification): fast probabilistic certificates that skip the slow exact check.
====================================================================================================
★ Clock B ONLY ★ — these make VERIFICATION faster, not the LLM call (A) or the generated code (C). Each
certificate states its TYPE and, when randomized, its ONE-SIDED error probability (rule 5):

  • Freivalds (Monte-Carlo): verify a matrix product A·B = C in O(k·n²) instead of recomputing in O(n³).
    One-sided: a CORRECT product always passes; a WRONG one passes with probability ≤ 2^-k. (cert: "Freivalds")
  • Schwartz-Zippel (ε): verify a POLYNOMIAL IDENTITY p ≡ q by evaluating p−q at random points instead of
    expanding symbolically. One-sided: identical polys always pass; distinct ones pass with prob ≤ d/|S|
    per round (≤ (d/|S|)^rounds overall). (cert: "Schwartz-Zippel-ε")

If a fast certificate accepts, the expensive full check is skipped (and labeled as such). These are SOUND
in the one-sided sense: a "FAIL" is always a real discrepancy (no false rejection); a "PASS" carries the
stated ε. We never report ε as 0 unless the check is exact.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

Matrix = List[List[int]]


@dataclass
class CertResult:
    ok: bool
    cert_type: str            # "Freivalds" | "Schwartz-Zippel-ε" | "exact" | "residual"
    error_prob: float         # one-sided error probability of a PASS (0.0 only when exact)
    detail: str = ""

    def __str__(self):
        eps = "0 (exact)" if self.error_prob == 0 else f"≤ {self.error_prob:.2e}"
        return f"{'PASS' if self.ok else 'FAIL'} [{self.cert_type}] error≤{eps} — {self.detail}"


# ── Freivalds: O(k·n²) randomized check of A·B == C ─────────────────────────────────────────────────
def _matvec(M: Matrix, v: Sequence[int]) -> List[int]:
    return [sum(M[i][j] * v[j] for j in range(len(v))) for i in range(len(M))]


def matmul(A: Matrix, B: Matrix) -> Matrix:
    n, m, p = len(A), len(B), len(B[0])
    return [[sum(A[i][k] * B[k][j] for k in range(m)) for j in range(p)] for i in range(n)]


def freivalds_check(A: Matrix, B: Matrix, C: Matrix, k: int = 24, seed: int = 0) -> CertResult:
    """Verify A·B == C with k random {0,1} probes. CORRECT C → always PASS; WRONG C → PASS prob ≤ 2^-k."""
    rng = random.Random(seed)
    n = len(B[0])
    for _ in range(k):
        r = [rng.randint(0, 1) for _ in range(n)]
        # A(Br) vs Cr — if they ever differ, the product is DEFINITELY wrong (no false reject)
        if _matvec(A, _matvec(B, r)) != _matvec(C, r):
            return CertResult(False, "Freivalds", 0.0, "A·B ≠ C (a probe separated them — definitely wrong)")
    return CertResult(True, "Freivalds", 2.0 ** (-k), f"A·B == C verified by {k} probes in O(k·n²)")


# ── Schwartz-Zippel: verify a polynomial identity p ≡ q by random evaluation ────────────────────────
def sz_identity_check(p_fn, q_fn, n_vars: int, degree: int, rounds: int = 3,
                      field: int = (1 << 61) - 1, seed: int = 0) -> CertResult:
    """p_fn, q_fn: callables taking a tuple of `n_vars` ints → int. Evaluate (p−q) mod a large prime at
    random points: all zero ⇒ identical with error ≤ (d/|S|)^rounds; any nonzero ⇒ DISTINCT (no false reject)."""
    rng = random.Random(seed)
    S = field
    for _ in range(rounds):
        pt = tuple(rng.randrange(S) for _ in range(n_vars))
        if (p_fn(pt) - q_fn(pt)) % S != 0:
            return CertResult(False, "Schwartz-Zippel-ε", 0.0, "p(x) ≠ q(x) at a random point — distinct")
    per = degree / S
    return CertResult(True, "Schwartz-Zippel-ε", per ** rounds,
                      f"p ≡ q over {rounds} random points (deg {degree}, |S|=prime)")


# ── measurement [Clock B]: certificate vs the exact recompute it replaces ───────────────────────────
@dataclass
class CertMeasurement:
    name: str
    exact_ms: float
    cert_ms: float
    speedup: float
    cert_type: str
    error_prob: float
    correct_pass: bool
    wrong_caught: bool


def measure_freivalds(n: int = 160, k: int = 24, seed: int = 1) -> CertMeasurement:
    import time
    rng = random.Random(seed)
    A = [[rng.randint(-9, 9) for _ in range(n)] for _ in range(n)]
    B = [[rng.randint(-9, 9) for _ in range(n)] for _ in range(n)]
    C = matmul(A, B)
    t = time.perf_counter(); recompute_ok = (matmul(A, B) == C); exact_ms = (time.perf_counter() - t) * 1000
    t = time.perf_counter(); cert = freivalds_check(A, B, C, k=k); cert_ms = (time.perf_counter() - t) * 1000
    wrong = [row[:] for row in C]; wrong[0][0] += 1          # corrupt ONE entry
    caught = not freivalds_check(A, B, wrong, k=k).ok
    return CertMeasurement("freivalds_matmul", round(exact_ms, 2), round(cert_ms, 2),
                           round(exact_ms / cert_ms, 1) if cert_ms > 0 else 1.0, cert.cert_type,
                           cert.error_prob, cert.ok and recompute_ok, caught)
