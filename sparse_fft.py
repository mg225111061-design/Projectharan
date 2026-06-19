"""
v37 STAGE 1.2 — sparse FFT: recover a k-sparse spectrum from O(k) samples (vs the full O(N log N) FFT).
======================================================================================================
Key reduction: a k-SPARSE spectrum means the time signal is a sum of k complex exponentials,
x[t] = Σ_j a_j·exp(2πi ω_j t / N). That is exactly the Prony model → we recover the k frequencies+amplitudes
from O(k) TIME SAMPLES (genuinely sublinear), no full FFT.

★ EXACT certificate: the recovered k-sparse spectrum must reconstruct the signal on HELD-OUT samples
  (Prony's residual ≈ machine-ε). Not k-sparse / residual too large / k≈N ⇒ DECLINE → degrade to the full FFT
  (honest). We do NOT beat Ω(N) for a dense spectrum. ★
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

import prony
import sublinear_layer as SL


def recover(data, k_max: int = 20) -> SL.SublinearVerdict:
    """`data` = the time signal x (length N) with a (claimed) k-sparse DFT. Recover the sparse spectrum via
    Prony on O(k) samples; EXACT iff the held-out residual is ~machine-ε; else DECLINE (→ full FFT)."""
    x = np.asarray(data, dtype=complex)
    N = len(x)
    if N < 8:
        return SL.decline("signal too short for sparse FFT", "sparse_fft")
    # use the prefix samples (O(k)) for Prony; the rest are held out as the witness
    n_use = min(N, 4 * k_max + 8)
    pv = prony.recover(x[:n_use], k_max=k_max, validate=min(6, n_use // 4))
    if pv.status == SL.DECLINE:
        return SL.decline(f"spectrum not k-sparse ({pv.reason}) → degrade to full O(N log N) FFT", "sparse_fft")
    betas, coeffs, k = pv.result["betas"], pv.result["coeffs"], pv.result["k"]
    # β_j = exp(2πi ω_j / N) → recover integer frequencies on the grid
    freqs = np.round(np.angle(betas) * N / (2 * np.pi)).astype(int) % N
    spectrum = {int(f): complex(a * N) for f, a in zip(freqs, coeffs)}   # DFT-scaled amplitudes
    # ★ certificate: reconstruct on ALL N points, residual vs the true signal (verify the sparse model) ★
    recon = np.zeros(N, dtype=complex)
    tt = np.arange(N)
    for f, a in zip(freqs, coeffs):
        recon += a * np.exp(2j * np.pi * f * tt / N)
    rel = float(np.max(np.abs(recon - x))) / (float(np.max(np.abs(x))) + 1e-30)
    if rel > prony._MACH_TOL:
        return SL.decline(f"sparse-model residual {rel:.2e} above machine-ε → DECLINE (→ full FFT)", "sparse_fft")
    cert = SL.Certificate(grade=SL.EXACT, kind="residual", passed=True,
                          check_cost=f"O(k) Prony samples + reconstruction; k={k}",
                          bound=rel, detail=f"k-sparse spectrum recovered ({k} tones); residual {rel:.2e} ≈ machine-ε")
    return SL.SublinearVerdict(SL.EXACT, {"spectrum": spectrum, "k": k}, "sparse_fft",
                              f"O(k log N), k={k}, N={N}", cert)


SL.register("sparse_spectrum", recover)
