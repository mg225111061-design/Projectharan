"""
v37 STAGE 1.1 — Prony / ESPRIT: recover an exponential-sum recurrence from samples (the data-driven inverse of fold).
=====================================================================================================================
A C-finite sequence is a sum of exponentials f(t)=Σ_{j<k} cⱼ·βⱼᵗ; fold CLOSES such a recurrence symbolically,
Prony RECOVERS it from O(k) samples. Hankel matrix → ESPRIT (SVD + shift-pencil) → roots βⱼ → Vandermonde cⱼ.

★ EXACT certificate (§S1.1): the recovered k-term model must reproduce HELD-OUT samples (not used in the fit).
  Noiseless ⇒ residual ≈ machine-ε ⇒ EXACT (the recurrence is determined). For an integer recurrence we ALSO
  cross-check the recovered coefficients with cfinite.py (must agree). Residual above machine-ε, or no
  singular-value gap (rank ≈ N/2) ⇒ DECLINE (honest: not an exponential sum / too noisy for an EXACT claim). ★
Complexity: O(k) samples (+ a one-time O(N) SVD on the small Hankel) vs O(N) to read the whole sequence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

import sublinear_layer as SL

_MACH_TOL = 1e-7        # held-out residual below this ⇒ EXACT (machine-ε determined)


def _hankel(s: np.ndarray, rows: int) -> np.ndarray:
    cols = len(s) - rows + 1
    return np.array([s[i:i + cols] for i in range(rows)], dtype=complex)


def _estimate_rank(sv: np.ndarray, rel_gap: float = 1e-6) -> int:
    """Numerical rank = #singular values above rel_gap·σ₀. A sharp drop ⇒ a clean k; no drop ⇒ rank≈N/2."""
    if sv[0] == 0:
        return 0
    return int(np.sum(sv > rel_gap * sv[0]))


def recover(samples, k_max: int = 20, validate: int = 4) -> SL.SublinearVerdict:
    """Recover f(t)=Σ cⱼ βⱼᵗ from `samples` via ESPRIT; EXACT iff the held-out residual is ~machine-ε.
    `validate` samples at the tail are HELD OUT (never used in the fit) — the residual on them is the witness."""
    s = np.asarray(samples, dtype=complex)
    N = len(s)
    if N < 6:
        return SL.decline("too few samples for Prony", "prony")
    fit, held = s[:N - validate], s[N - validate:]
    rows = len(fit) // 2
    H = _hankel(fit, rows)
    U, sv, _ = np.linalg.svd(H, full_matrices=False)
    k = _estimate_rank(sv)
    if k == 0 or k > min(k_max, rows - 1):
        return SL.decline(f"no low-rank exponential structure (estimated rank {k}, no singular-value gap)", "prony")
    if k >= rows - 1 or k >= (N - validate) // 2:
        return SL.decline(f"rank≈N/2 (k={k}) — no compression, looks structureless ⇒ DECLINE", "prony")
    # ESPRIT: eigenvalues of the shift pencil on the top-k signal subspace = the βⱼ
    Uk = U[:, :k]
    phi, *_ = np.linalg.lstsq(Uk[:-1], Uk[1:], rcond=None)
    betas = np.linalg.eigvals(phi)
    # Vandermonde solve for cⱼ over the fit samples
    t = np.arange(len(fit))
    V = betas[None, :] ** t[:, None]
    c, *_ = np.linalg.lstsq(V, fit, rcond=None)

    def model(tt):
        return (c[None, :] * (betas[None, :] ** np.asarray(tt)[:, None])).sum(axis=1)
    # ★ the certificate: residual on HELD-OUT samples (not used in the fit) ★
    pred = model(np.arange(N - validate, N))
    residual = float(np.max(np.abs(pred - held))) if validate > 0 else float(np.max(np.abs(model(t) - fit)))
    rel = residual / (np.max(np.abs(s)) + 1e-30)
    if rel > 1e-3:
        return SL.decline(f"held-out residual {rel:.2e} too large — not an exponential sum ⇒ DECLINE", "prony")
    if rel > _MACH_TOL:
        return SL.decline(f"residual {rel:.2e} above machine-ε — noisy, not EXACT-determined (DECLINE EXACT claim)", "prony")
    cert = SL.Certificate(grade=SL.EXACT, kind="residual", passed=True,
                          check_cost=f"O({validate}) held-out samples + O(N) Hankel SVD",
                          epsilon=None, delta=None, bound=rel,
                          detail=f"k={k} exponentials; held-out residual {rel:.2e} ≈ machine-ε ⇒ recurrence determined")
    return SL.SublinearVerdict(SL.EXACT, {"betas": betas, "coeffs": c, "k": k}, "prony",
                              f"O(k) samples, k={k}, N={N}", cert)


def recover_recurrence(samples) -> Tuple[Optional[List[int]], bool, str]:
    """Recover the INTEGER linear recurrence (Prony polynomial = characteristic polynomial) and cross-check it
    with cfinite.py. Returns (coeffs, cfinite_agrees, detail). The Prony poly's roots are the βⱼ; for a real
    integer C-finite sequence the monic char-poly has integer coefficients ⇒ the recurrence a(n)=Σ cᵢa(n-i)."""
    v = recover(samples, validate=4)
    if v.status == SL.DECLINE:
        return None, False, v.reason
    betas = v.result["betas"]
    # characteristic polynomial from the roots: ∏(z-βⱼ) → coefficients (highest first)
    poly = np.real(np.poly(betas))                       # real for a real recurrence
    # a(n) = c1 a(n-1)+...+ck a(n-k): char poly z^k - c1 z^{k-1} - ... - ck ⇒ cᵢ = -poly[i]
    coeffs = [-int(round(x)) for x in poly[1:]]
    # cross-check with cfinite: does this recurrence reproduce the samples?
    import cfinite
    try:
        ok, _ = cfinite.verify_cfinite(coeffs, [int(round(np.real(x))) for x in np.asarray(samples)[:len(coeffs)]])
    except Exception:  # noqa: BLE001
        ok = False
    return coeffs, ok, f"recovered recurrence coeffs={coeffs}, cfinite-agrees={ok}"


SL.register("exponential_sum", recover)
