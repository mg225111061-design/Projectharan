"""
v37 STAGE 3 — spiked/planted spectrum detection (BBP threshold), with the statistical-computational gap honest.
================================================================================================================
Detect a planted rank-1 signal in noise (spiked Wigner: M = (λ/N)·vvᵀ + W). By the BBP phase transition the top
eigenvalue DETACHES from the bulk edge iff the signal strength exceeds threshold; power iteration finds λ₁ and
the top eigenvector in O(N²) (no full O(N³) eigendecomposition).

★ GRADE = PROBABILISTIC: the witness is the SPECTRAL GAP — λ₁ above the BBP/Marchenko-Pastur edge with margin ⇒
  "signal present" + eigenvector; below ⇒ DECLINE. ★
★ CRITICAL HONESTY (§S3.1, §6.9): this certifies DETECTABILITY above BBP — it is NOT a proof of ABSENCE below.
  In a statistical-computational gap a signal may EXIST yet be efficiently undetectable; we therefore NEVER
  claim "no signal", only "not efficiently detectable" ⇒ DECLINE. ★
"""
from __future__ import annotations

import numpy as np

import sublinear_layer as SL


def _power_top(M: np.ndarray, iters: int = 200, seed: int = 0):
    """Top eigenvalue + eigenvector by power iteration (O(N²) per step; no full eig)."""
    rng = np.random.default_rng(seed)
    n = M.shape[0]
    v = rng.standard_normal(n); v /= np.linalg.norm(v)
    lam = 0.0
    for _ in range(iters):
        w = M @ v
        lam = float(v @ w)
        nv = np.linalg.norm(w)
        if nv < 1e-30:
            break
        v = w / nv
    return lam, v


def detect(data, margin: float = 0.15) -> SL.SublinearVerdict:
    """`data` = a symmetric N×N matrix (normalized spiked Wigner). If λ₁ exceeds the bulk edge (≈2 for the
    standard normalization) with margin ⇒ signal PRESENT (eigenvector) ; else DECLINE ('not detectable',
    NOT 'no signal')."""
    M = np.asarray(data, dtype=float)
    M = (M + M.T) / 2.0
    N = M.shape[0]
    lam1, v1 = _power_top(M)
    # estimate the bulk edge from the bulk std (off-leading) — Wigner semicircle edge ≈ 2σ√N for unnormalized;
    # for the standard spiked model normalized so bulk edge ≈ 2, use the empirical bulk scale.
    bulk_std = float(np.std(M)) * np.sqrt(N)
    edge = 2.0 * bulk_std                              # Marchenko-Pastur / Wigner bulk edge
    gap = lam1 - edge
    if gap <= margin * edge:
        return SL.decline(f"λ₁={lam1:.2f} not above bulk edge {edge:.2f} with margin — NOT efficiently detectable "
                          f"(NOT a proof of absence; statistical-computational gap) ⇒ DECLINE", "planted")
    cert = SL.Certificate(grade=SL.PROBABILISTIC, kind="spectral_gap", passed=True,
                          check_cost="O(N²) power iteration (no full eig)", epsilon=None, delta=0.05,
                          bound=float(gap),
                          detail=f"λ₁={lam1:.2f} > BBP/MP edge {edge:.2f} by {gap:.2f} (margin) ⇒ planted signal "
                                 f"present; eigenvector estimated. Detectability cert, NOT an absence proof.")
    return SL.SublinearVerdict(SL.PROBABILISTIC, {"lambda1": lam1, "eigvec": v1, "edge": edge}, "planted",
                              f"O(N²), N={N}", cert)


SL.register("planted_signal", detect)


def make_spiked(N: int, snr: float, seed: int = 0):
    """Spiked Wigner: M = snr·vvᵀ/√N + W (W symmetric Gaussian). snr large ⇒ above BBP (detectable)."""
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(N); v /= np.linalg.norm(v)
    W = rng.standard_normal((N, N)) / np.sqrt(N)
    W = (W + W.T) / 2.0
    return snr * np.outer(v, v) + W, v
