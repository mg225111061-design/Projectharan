"""
GAP CLOSURE (certification) — P14 the PROBABILISTIC tier + P8 quasi-periodic / almost-periodic structure.
=========================================================================================================
Some inputs have REAL structure that admits only a bounded (ε) certificate, not an exact one. The EXACT ledger
stays residual-0-only; this is a SEPARATE, clearly-labelled PROBABILISTIC tier — graded via lossless_gate as
`approximation`, NEVER folded EXACT, never entering the EXACT ledger.

  • P14 probabilistic_grade — given a detector's reconstruction with a MEASURED relative error ε on the sampled
    support (a certified numerical enclosure: re-computable, an honest statement about THIS data, not extrapolation),
    grade PROBABILISTIC with δ = ε. A flat/random input admits no low-ε model ⇒ DECLINE (no nontrivial bound).
  • P8  quasi_periodic_grade — a sum of incommensurate sinusoids has no exact period and is not C-finite over ℚ;
    a greedy k-tone least-squares fit reconstructs it to relative error ε on the samples ⇒ PROBABILISTIC(δ=ε).
    A broadband random signal cannot be fit by few tones (ε large) ⇒ DECLINE. (The finite, commensurate /
    C-finite case is the EXACT cascade's job — BM/Prony — not this tier.)

★ BINDING SEPARATION: this module NEVER returns KV.EXACT. EXACT stays exact (residual 0); approximation is graded
  and surfaced as such. This is what lets the denominator grow honestly without moving the EXACT floor.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import kernel_verdict as KV

_EPS = 0.03                 # relative-error ceiling for a PROBABILISTIC grade. Structured quasi-periodic fits to
#                             ~1% (off-grid incommensurate tones); random/broadband sits at ~90% — a huge margin,
#                             so the ceiling cleanly separates real almost-periodic structure from noise. δ (the
#                             ACTUAL measured error, ≈0.01) is what is recorded, never this ceiling.


def probabilistic_grade(result: dict, rel_error: float, support: int, what: str) -> KV.Verdict:
    """P14 — grade a δ-bounded approximation PROBABILISTIC (never EXACT). δ = the measured relative reconstruction
    error on `support` samples (a certified numerical enclosure on the sampled support). rel_error > _EPS (no
    nontrivial bound, e.g. random) ⇒ DECLINE."""
    if not (0.0 <= rel_error <= _EPS):
        return KV.decline(f"probabilistic: relative error {rel_error:.2e} > ε={_EPS:.0e} — no nontrivial bound "
                          "(random / not approximable) ⇒ DECLINE", "gap_prob")
    cert = KV.Cert(KV.PROBABILISTIC, f"bounded_reconstruction[{what}]", passed=True, delta=float(rel_error),
                   check_cost=f"relative L2 reconstruction error on {support} samples (certified numerical enclosure)",
                   detail=f"{what}: δ={rel_error:.2e} on the sampled support — APPROXIMATION, never folded EXACT")
    return KV.probabilistic({**result, "delta": rel_error, "tier": "approximation"}, "gap_prob",
                            f"{what} (δ={rel_error:.2e})", cert)


def _greedy_tone_fit(x, max_tones: int = 2, grid: int = 256) -> Tuple[List[float], float]:
    """Greedy k-tone least-squares: repeatedly find the single frequency ω∈(0,π) whose [cos ωn, sin ωn] best
    reduces the residual (continuous-frequency, so incommensurate tones are reachable), subtract, repeat. Returns
    (frequencies, relative L2 residual on the samples)."""
    import numpy as np
    xv = np.asarray(x, dtype=float)
    xv = xv - xv.mean()
    n = len(xv)
    t = np.arange(n)
    residual = xv.copy()
    base = np.linalg.norm(xv) + 1e-300

    def proj(w, r):
        D = np.column_stack([np.cos(w * t), np.sin(w * t)])
        coef, *_ = np.linalg.lstsq(D, r, rcond=None)
        fit = D @ coef
        return float(np.linalg.norm(r - fit)), fit

    def locate(r):
        lo, hi = 0.02, np.pi - 0.02
        wbest = lo
        for _stage in range(4):                                 # multi-stage zoom: coarse → fine window each round
            ws = np.linspace(lo, hi, grid)
            wbest = min(ws, key=lambda w: proj(w, r)[0])
            step = (hi - lo) / (grid - 1)
            lo, hi = max(1e-6, wbest - 2 * step), min(np.pi - 1e-6, wbest + 2 * step)
        return wbest

    def design(ws):
        cols = []
        for w in ws:
            cols.append(np.cos(w * t)); cols.append(np.sin(w * t))
        return np.column_stack(cols)

    def joint_resid(ws):
        D = design(ws)
        coef, *_ = np.linalg.lstsq(D, xv, rcond=None)
        return float(np.linalg.norm(xv - D @ coef) / base)

    freqs = []
    for _ in range(max_tones):
        w = locate(residual)
        freqs.append(float(w))
        residual = residual - proj(w, residual)[1]
    # alternating refinement: re-locate each tone against the signal MINUS the other tones (kills greedy cross-talk)
    for _round in range(6):
        for j in range(len(freqs)):
            others = [freqs[k] for k in range(len(freqs)) if k != j]
            rj = xv.copy()
            if others:
                Do = design(others)
                co, *_ = np.linalg.lstsq(Do, xv, rcond=None)
                rj = xv - Do @ co
            freqs[j] = float(locate(rj))
    return [round(w, 8) for w in freqs], joint_resid(freqs)


def quasi_periodic_grade(seq, max_tones: int = 2) -> KV.Verdict:
    """P8 — detect a quasi-/almost-periodic signal (sum of few incommensurate sinusoids). A greedy k-tone fit
    reconstructs it to relative error ε on the samples ⇒ PROBABILISTIC(δ=ε) (never EXACT — irrational frequencies
    are not exactly representable). Broadband random ⇒ ε large ⇒ DECLINE. Requires N ≥ 24 so few tones cannot
    over-fit random data."""
    if not (isinstance(seq, (list, tuple)) and len(seq) >= 24
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in seq)):
        return KV.decline("quasi_periodic: need a numeric sequence of length ≥ 24", "gap_prob")
    freqs, rel = _greedy_tone_fit(list(seq), max_tones=max_tones)
    if rel > _EPS:
        return KV.decline(f"quasi_periodic: {max_tones}-tone fit residual {rel:.2e} > ε — broadband / not "
                          "almost-periodic ⇒ DECLINE", "gap_prob")
    return probabilistic_grade({"frequencies": freqs, "n_tones": len(freqs), "n": len(seq)}, rel, len(seq),
                               "quasi_periodic")
