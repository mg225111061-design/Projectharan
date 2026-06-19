"""
v37 STAGE 2.3 — low-rank matrix completion (SVT) + a HELD-OUT-entry certificate with a stated δ.
================================================================================================
Recover a rank-r N×N matrix from O(rN polylog N) observed entries via nuclear-norm minimization. We use SVT
(singular value thresholding — iterative, pure numpy; tau=5N, δ=1.9 per Cai–Candès–Shen) since cvxpy's SDP is
[BLOCKED].

★ GRADE = PROBABILISTIC. The witness is a HELD-OUT set of h observed entries (sampled uniformly, NEVER shown to
  the fit) that the recovery must predict. Two numbers, both MEASURED:
    • ε  = held-out relative RMS residual (the magnitude of the out-of-sample error), and
    • δ  = a stated CONFIDENCE for a binomial-tail (rule-of-three style) bound: if all h held-out entries are
           predicted within the per-entry tolerance θ (zero violations), then the fraction of ALL entries whose
           per-entry error exceeds θ is ≤ p₀ = 1 − δ^(1/h), with confidence 1−δ. ★
★ The EXACT Candès–Recht DUAL certificate (W: P_T(W)=UV*, ‖P_{T⊥}(W)‖<1) needs the SDP dual ⇒ [BLOCKED: cvxpy]
  — we do NOT fake it. The held-out binomial-tail bound is the honest sublinear PROBABILISTIC witness. ★
"""
from __future__ import annotations

import numpy as np

import sublinear_layer as SL


def _svt(mask: np.ndarray, observed: np.ndarray, tau: float, delta: float, iters: int = 500):
    """Singular value thresholding iteration for nuclear-norm minimization on the observed set
    (Cai–Candès–Shen 2010). Converges to a low-rank fit of the *fit* entries; early-stops on the observed
    residual."""
    Y = np.zeros_like(observed)
    X = np.zeros_like(observed)
    for _ in range(iters):
        U, s, Vt = np.linalg.svd(Y, full_matrices=False)
        s_t = np.maximum(s - tau, 0.0)               # soft-threshold the singular values
        X = (U * s_t) @ Vt
        Y = Y + delta * mask * (observed - X)
        if np.linalg.norm(mask * (observed - X)) <= 1e-8 * (np.linalg.norm(mask * observed) + 1e-30):
            break
    return X


def complete(data, r: int = None, holdout_frac: float = 0.2, tol: float = 1e-2,
             theta: float = 1e-3, confidence: float = 1e-6) -> SL.SublinearVerdict:
    """`data` = (M_observed, mask) where mask marks observed entries (M_observed=0 elsewhere). Recover via SVT;
    ACCEPT (PROBABILISTIC) iff the recovery predicts every HELD-OUT observed entry within the per-entry tolerance
    θ (zero violations), the held-out RMS ≤ tol, and the fit is low-rank. The stated δ = `confidence`; the
    certified bound is p₀ = 1 − δ^(1/h) on the fraction of entries exceeding θ."""
    M_obs, mask = np.asarray(data[0], dtype=float), np.asarray(data[1], dtype=bool)
    N = M_obs.shape[0]
    n_obs = int(mask.sum())
    if n_obs < 3 * N:
        return SL.decline(f"too few observations ({n_obs} < 3N) — under-determined ⇒ DECLINE", "matrix_completion")
    rng = np.random.default_rng(0)
    # hold out a fraction of observed entries as the witness (disjoint from the fit set)
    obs_idx = np.argwhere(mask)
    held = obs_idx[rng.choice(len(obs_idx), size=max(1, int(holdout_frac * len(obs_idx))), replace=False)]
    fit_mask = mask.copy()
    for (i, j) in held:
        fit_mask[i, j] = False
    X = _svt(fit_mask, M_obs * fit_mask, tau=5.0 * N, delta=1.9, iters=500)

    # ★ certificate: out-of-sample prediction of HELD-OUT entries (never used in the fit) ★
    held_vals = np.array([M_obs[i, j] for (i, j) in held])
    pred_vals = np.array([X[i, j] for (i, j) in held])
    h = len(held)
    rms = float(np.linalg.norm(pred_vals - held_vals)) / (float(np.linalg.norm(held_vals)) + 1e-30)
    # per-entry violations at relative tolerance θ (absolute floor 1.0 guards near-zero true entries)
    violations = int(np.sum(np.abs(pred_vals - held_vals) > theta * (np.abs(held_vals) + 1.0)))
    sv = np.linalg.svd(X, compute_uv=False)
    eff_rank = int(np.sum(sv > 1e-6 * sv[0]))

    # binomial-tail bound: v==0 over h i.i.d.-sampled held-out entries ⇒ true violation rate ≤ p₀ at confidence δ
    p0 = 1.0 - confidence ** (1.0 / h)
    rank_ok = (r is None) or (eff_rank <= 3 * r)
    if violations > 0 or rms > tol or not rank_ok:
        return SL.decline(
            f"held-out witness FAILED ({violations}/{h} per-entry violations, RMS {rms:.2e}, rank≈{eff_rank}) "
            f"— recovery not certified ⇒ DECLINE", "matrix_completion")

    cert = SL.Certificate(grade=SL.PROBABILISTIC, kind="held_out_binomial", passed=True,
                          check_cost=f"O(h)={h} held-out observed entries (sublinear in N²)",
                          epsilon=rms, delta=confidence, bound=p0,
                          detail=f"rank≈{eff_rank}; {h} held-out entries all predicted within θ={theta} "
                                 f"(0 violations), RMS={rms:.2e}. Binomial tail ⇒ ≤{p0:.2e} fraction of entries "
                                 f"exceed θ at confidence {1 - confidence:.6f}. EXACT dual cert needs SDP "
                                 f"⇒ [BLOCKED: cvxpy] — held-out binomial bound is the honest witness.")
    return SL.SublinearVerdict(SL.PROBABILISTIC, {"X": X, "rank": eff_rank}, "matrix_completion",
                              f"O(rN polylog N) entries, N={N}, obs={n_obs}", cert)


SL.register("matrix_completion", complete)


def make_instance(N: int, r: int, frac: float, seed: int = 0):
    rng = np.random.default_rng(seed)
    M = rng.standard_normal((N, r)) @ rng.standard_normal((r, N))
    mask = rng.random((N, N)) < frac
    return M * mask, mask, M
