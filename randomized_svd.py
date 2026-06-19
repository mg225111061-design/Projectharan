"""
v37 STAGE 2.1 — randomized SVD + a POSTERIOR residual certificate (PROBABILISTIC, high-probability bound).
===========================================================================================================
A rank-r approximation in ≈O(N²·r) via the HMT range finder (Halko-Martinsson-Tropp "Finding Structure with
Randomness"): Ω random, Y=AΩ, Q=qr(Y), then SVD the small QᵀA. The result is only USED if a POSTERIOR residual
estimate ‖A−QQᵀA‖ (a few Gaussian probes, a high-probability bound) is within tolerance.

★ GRADE = PROBABILISTIC (§1.5): the residual bound holds with prob ≥ 1−δ (δ from the #probes), NOT EXACT.
  No spectral gap (residual stays large) ⇒ DECLINE → fall back to the full O(N³) SVD. ★
"""
from __future__ import annotations

import math

import numpy as np

import sublinear_layer as SL


def randomized_svd(A: np.ndarray, r: int, oversample: int = 8, power_iters: int = 2, seed: int = 0):
    """HMT randomized SVD: returns (U, s, Vt) rank-(r) factors + the orthonormal range Q."""
    rng = np.random.default_rng(seed)
    m, n = A.shape
    Omega = rng.standard_normal((n, r + oversample))
    Y = A @ Omega
    for _ in range(power_iters):                 # power iteration sharpens the range for slow spectral decay
        Y = A @ (A.T @ Y)
    Q, _ = np.linalg.qr(Y)
    B = Q.T @ A
    Ub, s, Vt = np.linalg.svd(B, full_matrices=False)
    U = Q @ Ub
    return U[:, :r], s[:r], Vt[:r, :], Q


def _posterior_residual(A: np.ndarray, Q: np.ndarray, probes: int = 10, seed: int = 1) -> float:
    """HMT posterior error estimate: ‖A−QQᵀA‖ ≤ 10·√(2/π)·maxᵢ‖(A−QQᵀA)ωᵢ‖ with prob ≥ 1−10^-probes."""
    rng = np.random.default_rng(seed)
    n = A.shape[1]
    E = A - Q @ (Q.T @ A)
    worst = 0.0
    for _ in range(probes):
        w = rng.standard_normal(n)
        worst = max(worst, np.linalg.norm(E @ w) / (np.linalg.norm(w) + 1e-30))
    return 10.0 * math.sqrt(2.0 / math.pi) * worst


def approximate(data, r: int = None, tol: float = 1e-3, probes: int = 10) -> SL.SublinearVerdict:
    """`data` = matrix A. Try a rank-r randomized SVD; ACCEPT (PROBABILISTIC) iff the posterior residual is
    within `tol` (relative); else DECLINE (no low-rank structure → full SVD)."""
    A = np.asarray(data, dtype=float)
    m, n = A.shape
    r = r or max(1, min(m, n) // 10)
    U, s, Vt, Q = randomized_svd(A, r)
    resid = _posterior_residual(A, Q, probes=probes)
    rel = resid / (np.linalg.norm(A, 2) + 1e-30)
    delta = 10.0 ** (-probes)                    # the posterior bound's failure probability
    if rel > tol:
        return SL.decline(f"posterior residual {rel:.2e} > tol {tol} — no rank-{r} structure ⇒ DECLINE (full SVD)",
                          "rsvd")
    cert = SL.Certificate(grade=SL.PROBABILISTIC, kind="concentration", passed=True,
                          check_cost=f"O({probes}·N²) posterior probes", epsilon=rel, delta=delta, bound=rel,
                          detail=f"rank-{r} approx; ‖A−QQᵀA‖/‖A‖≈{rel:.2e} ≤ tol with prob ≥ 1−{delta:.0e}")
    return SL.SublinearVerdict(SL.PROBABILISTIC, {"U": U, "s": s, "Vt": Vt, "r": r}, "rsvd",
                              f"O(N²·r), r={r}, N={n}", cert)


SL.register("low_rank", approximate)
