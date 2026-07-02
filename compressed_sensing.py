"""
v37 STAGE 1.3 — compressed sensing + Fuchs DUAL CERTIFICATE (the flagship per-instance witness).
=================================================================================================
Recover a k-sparse N-vector x from m=O(k log(N/k)) linear measurements y=Ax. The recovery SOLVER is
UNTRUSTED (here: numpy OMP — cvxpy basis-pursuit is [BLOCKED]); what makes the result EXACT is a per-instance
DUAL CERTIFICATE, not a uniform property.

★ NEVER verify RIP (§1.7) — it is NP-hard. ★ Instead the Fuchs/KKT optimality witness on the recovered support
S: x is the UNIQUE ℓ1-minimizer ⟺ the dual v = Aᵀ A_S (A_Sᵀ A_S)⁻¹ sign(x_S) satisfies
  (i)  v_S = sign(x_S)              (by construction; verified)
  (ii) ‖v_{Sᶜ}‖_∞ < 1               (STRICT, with margin)
  (iii) A_S has full column rank
All strict ⇒ EXACT (unique exact recovery certified for THIS instance, by ℓ1 strong duality). Any failure /
no margin ⇒ DECLINE. The check is O(mN) ≪ the combinatorial search; it is a per-instance optimality witness.
"""
from __future__ import annotations

import numpy as np

import sublinear_layer as SL


def _omp(A: np.ndarray, y: np.ndarray, k: int, tol: float = 1e-10):
    """Orthogonal matching pursuit: greedy support recovery (the UNTRUSTED solver). Returns (support, x_S)."""
    m, N = A.shape
    residual = y.astype(float).copy()
    support: list = []
    xs = np.zeros(0)
    for _ in range(min(k, m)):
        corr = np.abs(A.T @ residual)
        corr[support] = -1.0
        j = int(np.argmax(corr))
        support.append(j)
        As = A[:, support]
        xs, *_ = np.linalg.lstsq(As, y, rcond=None)
        residual = y - As @ xs
        if np.linalg.norm(residual) < tol:
            break
    return support, xs


def recover(data, k: int = None, margin: float = 1e-6) -> SL.SublinearVerdict:
    """`data` = (A, y) with y = A x for some k-sparse x. OMP recovers the support; the Fuchs dual certificate
    certifies (or refutes) UNIQUE exact recovery for this instance → EXACT or DECLINE."""
    A, y = np.asarray(data[0], dtype=float), np.asarray(data[1], dtype=float)
    m, N = A.shape
    k = k or max(1, m // 4)
    support, xs = _omp(A, y, k)
    if not support:
        return SL.decline("OMP recovered empty support", "compressed_sensing")
    # reconstruct + measurement residual (the recovered x must explain y)
    As = A[:, support]
    resid = float(np.linalg.norm(y - As @ xs))
    if resid > 1e-6 * (np.linalg.norm(y) + 1e-30):
        return SL.decline(f"recovery does not explain the measurements (residual {resid:.2e}) ⇒ DECLINE", "compressed_sensing")
    # (iii) A_S full column rank
    sv = np.linalg.svd(As, compute_uv=False)
    if sv.min() <= 1e-9:
        return SL.decline("A_S rank-deficient — no unique-recovery certificate", "compressed_sensing")
    # ★ build the Fuchs dual certificate v = Aᵀ A_S (A_Sᵀ A_S)⁻¹ sign(x_S) ★
    sgn = np.sign(xs)
    G = As.T @ As
    v = A.T @ (As @ np.linalg.solve(G, sgn))
    # (i) v_S = sign(x_S) by construction (verify it holds numerically)
    i_ok = np.allclose(v[support], sgn, atol=1e-7)
    # (ii) STRICT ‖v_{Sᶜ}‖_∞ < 1 (with margin)
    mask = np.ones(N, dtype=bool); mask[support] = False
    off_max = float(np.max(np.abs(v[mask]))) if mask.any() else 0.0
    if not i_ok:
        return SL.decline("dual v_S != sign(x_S) — no Fuchs certificate", "compressed_sensing")
    if off_max >= 1.0 - margin:
        return SL.decline(f"‖v_Sᶜ‖_∞={off_max:.4f} not strictly < 1 (no margin) — NOT certified unique ⇒ DECLINE",
                          "compressed_sensing")
    x = np.zeros(N); x[support] = xs
    cert = SL.Certificate(grade=SL.EXACT, kind="dual_cert", passed=True,
                          check_cost=f"O(m·N)=O({m}·{N}) — per-instance Fuchs witness (NOT RIP)",
                          bound=off_max,
                          detail=f"Fuchs: v_S=sign(x_S) ✓, ‖v_Sᶜ‖∞={off_max:.4f}<1 (margin {1-off_max:.4f}), "
                                 f"A_S full-rank ✓ ⇒ x is the UNIQUE ℓ1 minimizer (exact recovery certified)")
    return SL.SublinearVerdict(SL.EXACT, {"x": x, "support": support, "k": len(support)}, "compressed_sensing",
                              f"m=O(k log(N/k)), m={m}, N={N}, k={len(support)}", cert)


SL.register("sparse_recovery", recover)


def make_instance(N: int, k: int, m: int, seed: int = 0):
    """A random k-sparse instance: x (k-sparse), Gaussian A (m×N), y=Ax."""
    rng = np.random.default_rng(seed)
    x = np.zeros(N)
    supp = rng.choice(N, size=k, replace=False)
    x[supp] = rng.choice([-1.0, 1.0], size=k) * rng.uniform(1, 5, size=k)
    A = rng.standard_normal((m, N)) / np.sqrt(m)
    return A, A @ x, x
