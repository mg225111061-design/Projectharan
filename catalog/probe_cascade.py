"""
FRONT-END (Research 2) — the PROBE CASCADE: cheapest-first structure detectors, every candidate gated by an
EXACT certification check before it may fold. Proposers may be liberal/heuristic; the certifier is the disposer.
=================================================================================================================
★ CENTRAL INVARIANT: a detector only PROPOSES a candidate; the candidate's OWN native core re-certifies it in EXACT
  arithmetic (Berlekamp–Massey re-substitution over ℚ, Re-Pair lossless round-trip, Prony residual, integer-relation
  full-precision re-check). `cascade()` NEVER returns a non-DECLINE verdict that lacks a passed certificate — a wrong
  proposal fails the exact gate and the input falls through to DECLINE. This is what makes aggressive detection sound.

Stages (cheapest → most expensive), escalate-on-hit:
  0  compressibility + randomness SCREEN — O(N): incompressible AND random-looking ⇒ DECLINE immediately (the
     Viola–Jones first stage — cheaply rejects the bulk of true-random input).
  1  Berlekamp–Massey (native_sequence) — O(N²): L≪N/2 ⇒ C-finite recurrence candidate (re-substitution gate).
  2  FFT + autocorrelation → Prony (existing sparse_fft/prony) — concentrated spectrum ⇒ exponential-sum candidate.
  3  escalation: integer-relation (native_lattice LLL) for short real vectors; Re-Pair SLP for byte/str data.
The randomness core (BM L≈N/2, flat spectrum, incompressible) finds nothing and every gate fails ⇒ DECLINE.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

import kernel_verdict as KV


@dataclass
class CascadeResult:
    verdict: KV.Verdict
    stage: int                 # which cascade stage produced the certified fold (−1 = DECLINE)
    kind: str                  # c_finite | exponential_sum | slp | integer_relation | none
    tier: str                  # certificate strength: "exact" (ℚ re-substitution / lossless) | "exact_numeric" (Prony ≈ε)
    trace: List[str]           # per-stage outcome, for debugging / the precision audit

    @property
    def grade(self) -> str:
        return self.verdict.status


def _is_int_seq(x) -> bool:
    return isinstance(x, (list, tuple)) and len(x) >= 6 and all(isinstance(v, int) and not isinstance(v, bool) for v in x)


def _is_num_seq(x) -> bool:
    return isinstance(x, (list, tuple)) and len(x) >= 8 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in x)


def _monobit_runs_random(bits: List[int]) -> bool:
    """A cheap two-test randomness screen (NIST monobit + runs). True ⇒ 'looks random' (no cheap structure)."""
    import math
    n = len(bits)
    if n < 16:
        return False
    ones = sum(bits)
    s = abs(2 * ones - n) / math.sqrt(n)
    if s > 2.5:                                              # strongly biased ⇒ NOT random ⇒ structure
        return False
    runs = 1 + sum(1 for i in range(1, n) if bits[i] != bits[i - 1])
    pi = ones / n
    if pi in (0.0, 1.0):
        return False
    exp_runs = 2 * n * pi * (1 - pi)
    z = abs(runs - exp_runs) / (2 * math.sqrt(n) * pi * (1 - pi) + 1e-12)
    return s <= 2.5 and z <= 2.5                             # both tests pass ⇒ looks random


def _stage0_screen(x) -> Tuple[str, str]:
    """O(N) reject: incompressible (MDL) AND random-looking ⇒ ('reject', why). Else ('proceed', hint)."""
    from catalog import decline_boundary as DB
    if isinstance(x, str):
        return "proceed", "string (not screened — may be code/markup)"
    m = DB.mdl_two_part(x)
    compresses = bool(m and m["compresses"])
    looks_random = False
    if isinstance(x, (bytes, bytearray)):
        bits = [(b >> k) & 1 for b in x for k in range(8)]
        looks_random = _monobit_runs_random(bits)
    elif _is_int_seq(x):
        bits = [v & 1 for v in x]                           # LSB stream as a cheap randomness proxy
        looks_random = _monobit_runs_random(bits)
    if (m is not None and not compresses) and looks_random:
        return "reject", f"incompressible (MDL ratio {m['ratio']}) AND monobit/runs random ⇒ no cheap structure"
    return "proceed", ("compressible" if compresses else "inconclusive")


def cascade(x: Any) -> CascadeResult:
    """Run the detector cascade; return the FIRST candidate that passes its EXACT certification gate, else DECLINE.
    Each detector's native core does its own exact re-check — the cascade never folds an uncertified candidate."""
    trace: List[str] = []

    # ── Stage 0: cheap reject ──────────────────────────────────────────────────────────────────────────
    decision, why = _stage0_screen(x)
    trace.append(f"stage0[{decision}]: {why}")
    if decision == "reject":
        return CascadeResult(KV.decline(f"probe_cascade stage0: {why} ⇒ DECLINE", "probe_cascade"), -1, "none", "—", trace)

    # ── Matrix branch: exact rank-revealing (a low-rank matrix is a fold; full-rank ⇒ DECLINE) ──────────
    if isinstance(x, (list, tuple)) and len(x) >= 2 and all(isinstance(r, (list, tuple)) and len(r) >= 2 for r in x):
        from catalog import detectors_b as DBd
        vr = DBd.rank_revealing_grade(x)
        trace.append(f"matrix[rank-revealing]: {vr.status}")
        return CascadeResult(vr, 2, "low_rank", "exact", trace) if vr.status == KV.EXACT else \
            CascadeResult(KV.decline(f"probe_cascade: matrix full-rank (trace={trace})", "probe_cascade"), -1, "none", "—", trace)

    # ── Stage 1: Berlekamp–Massey (C-finite recurrence), exact ℚ re-substitution gate ───────────────────
    if _is_num_seq(x):
        import native_sequence as NS
        v = NS.bm_grade(list(x))
        trace.append(f"stage1[BM]: {v.status}")
        if v.status == KV.EXACT:
            return CascadeResult(v, 1, "c_finite", "exact", trace)
        # Stage 1b: explicit finite-difference polynomial law (closed form, complements BM's recurrence)
        from catalog import detectors_b as DBd
        vp = DBd.poly_law_grade(list(x))
        trace.append(f"stage1b[poly_law]: {vp.status}")
        if vp.status == KV.EXACT:
            return CascadeResult(vp, 1, "poly_law", "exact", trace)

    # ── Stage 2: FFT/autocorrelation → Prony exponential-sum, residual gate ─────────────────────────────
    if _is_num_seq(x):
        v2 = _stage2_spectral(list(x))
        trace.append(f"stage2[FFT→Prony]: {v2.status}")
        if v2.status == KV.EXACT:
            return CascadeResult(v2, 2, "exponential_sum", "exact_numeric", trace)

    # ── Stage 3: escalation — integer-relation (short real vector) / Re-Pair SLP (bytes/str) ────────────
    if isinstance(x, (list, tuple)) and 2 <= len(x) <= 12 and all(isinstance(v, (int, float)) for v in x):
        import native_lattice as NL
        v3 = NL.integer_relation([float(v) for v in x])
        trace.append(f"stage3[int-relation]: {v3.status}")
        if v3.status == KV.EXACT:
            return CascadeResult(v3, 3, "integer_relation", "exact", trace)
    if isinstance(x, (bytes, bytearray, str)):
        import native_sequence as NS
        v3 = NS.repair_grade(x)
        trace.append(f"stage3[Re-Pair SLP]: {v3.status}")
        if v3.status == KV.EXACT:
            return CascadeResult(v3, 3, "slp", "exact", trace)

    return CascadeResult(KV.decline(f"probe_cascade: no stage produced a certified candidate (trace={trace})",
                                    "probe_cascade"), -1, "none", "—", trace)


def _stage2_spectral(seq) -> KV.Verdict:
    """FFT peak / autocorrelation hint → Prony exponential-sum recovery with a reconstruction-residual gate."""
    import numpy as np
    x = np.asarray(seq, dtype=float)
    n = len(x)
    if n < 8:
        return KV.decline("stage2: too short", "probe_cascade")
    # cheap hint: a concentrated spectrum (few dominant FFT bins) ⇒ worth a Prony attempt
    spec = np.abs(np.fft.rfft(x - x.mean()))
    if spec.sum() <= 0:
        return KV.decline("stage2: zero spectrum", "probe_cascade")
    top = np.sort(spec)[::-1]
    concentration = float(top[:max(1, n // 16)].sum() / spec.sum())
    if concentration < 0.5:                                 # spread spectrum ⇒ not a sparse exponential sum
        return KV.decline(f"stage2: spectrum not concentrated ({concentration:.2f}) ⇒ no exponential-sum hint", "probe_cascade")
    try:
        import prony
        v = prony.recover(list(x))
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"stage2: prony raised {type(e).__name__}", "probe_cascade")
    if v.status != KV.EXACT:
        return KV.decline(f"stage2: prony did not certify ({v.reason[:50]})", "probe_cascade")
    c = v.certificate
    cert = KV.Cert(KV.EXACT, "exponential_sum", passed=True, check_cost=c.check_cost, bound=c.bound,
                   detail=f"FFT concentration {concentration:.2f} → Prony k={v.result.get('k')} tones; residual {c.bound:.2e}")
    return KV.exact({"k": v.result.get("k"), "spectrum": v.result.get("spectrum")}, "probe_cascade",
                    "FFT→Prony exponential sum", cert)
