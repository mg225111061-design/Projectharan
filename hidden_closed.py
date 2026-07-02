"""
perf-build STAGE 4 — hidden closed-form recovery (the HONEST "O(1)" direction).
================================================================================
Some sequences the C-finite classifier labels O(log n) (companion-matrix power) are SECRETLY polynomials:
a linear recurrence whose characteristic roots are all 1 ⇒ the sequence is a polynomial ⇒ an O(1) closed
form (the companion-matrix O(log n) was a "fake O(log n)"). This module RECOVERS those, EXACTLY, via finite
differences + held-out verification.

★ HONEST BOUNDARIES (non-negotiable) ★
  • EXACT O(1) requires a genuine polynomial (finite differences vanish). C-finite with a non-unit root
    (Fibonacci φ) is NOT polynomial ⇒ EXACT value stays O(log n); O(1) is only a FLOAT approximation
    (Binet) ⇒ graded PROBABILISTIC(ε), NEVER EXACT (float ≠ exact integer). [§4.2]
  • If the VALUE has Θ(n) bits (2^n, n!) then writing it is Ω(n) — the Ω(N) axiom — so we do NOT claim O(1)
    evaluation; we report THETA_N_OUTPUT (a closed FORMULA exists, but exact emission is Ω(output bits)).
  • No structure (random / general code) ⇒ DECLINE. Recovery is domain-specific (numeric); general ≈ 0.
★ SOUND GATE ★ a recovered polynomial is fit on a prefix and must predict HELD-OUT samples EXACTLY (exact
  rational arithmetic) before we call it CLOSED. A wrong fit fails the held-out check ⇒ DECLINE.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import comb
from typing import Callable, List, Optional, Tuple

CLOSED_O1 = "CLOSED_O1"          # genuine polynomial → O(1) field ops, value is polylog bits
OLOGN = "OLOGN"                  # C-finite non-polynomial (e.g. Fibonacci) → EXACT stays O(log n)
THETA_N_OUTPUT = "THETA_N"       # closed formula exists but value has Θ(n) bits ⇒ Ω(n) to emit (Ω(N) axiom)
DECLINE = "DECLINE"


@dataclass
class Recovery:
    status: str
    degree: Optional[int] = None
    coeffs_newton: Optional[List[Fraction]] = None      # Newton forward coefficients Δ^i a(0)
    checked_holdout: int = 0
    detail: str = ""
    grade: str = "EXACT"                                # EXACT for CLOSED_O1; PROBABILISTIC only for approx


def _newton_forward(prefix: List[Fraction]) -> List[Fraction]:
    """Δ^i a(0) for i=0..len-1 (the forward-difference coefficients)."""
    coeffs = []
    row = list(prefix)
    coeffs.append(row[0])
    while len(row) > 1:
        row = [row[i + 1] - row[i] for i in range(len(row) - 1)]
        coeffs.append(row[0])
    return coeffs


def _eval_newton(coeffs: List[Fraction], n: int, deg: int) -> Fraction:
    """a(n) = Σ_{i=0}^{deg} C(n,i)·Δ^i a(0)."""
    return sum(Fraction(comb(n, i)) * coeffs[i] for i in range(deg + 1))


def recover_polynomial(samples: List[Tuple[int, int]], fit: int = None, max_deg: int = 12) -> Optional[Recovery]:
    """`samples` = consecutive (n, a(n)) for n=0,1,2,…  Fit Newton forward differences on a prefix; the degree
    is the highest non-vanishing difference. Accept ONLY if it predicts the HELD-OUT remainder EXACTLY and the
    degree is genuinely bounded (evidence the higher differences vanished, not mere interpolation)."""
    if len(samples) < 4:
        return None
    fit = fit or max(4, (len(samples) * 2) // 3)
    fit = min(fit, len(samples))
    prefix = [Fraction(v) for (_, v) in samples[:fit]]
    coeffs = _newton_forward(prefix)
    # degree = highest index with a nonzero forward difference
    deg = max((i for i, c in enumerate(coeffs) if c != 0), default=0)
    if deg > max_deg or deg >= fit - 1:
        return None                                     # no vanishing higher differences ⇒ not a bounded poly
    holdout = samples[fit:]
    if not holdout:
        return None
    for (n, v) in holdout:                              # ★ sound gate: exact held-out prediction ★
        if _eval_newton(coeffs, n, deg) != Fraction(v):
            return None
    return Recovery(CLOSED_O1, degree=deg, coeffs_newton=coeffs[:deg + 1], checked_holdout=len(holdout),
                    detail=f"degree-{deg} polynomial recovered (Newton forward diffs), held-out-verified on "
                           f"{len(holdout)} points", grade="EXACT")


def classify(seq: Callable[[int], int], m: int = 60, max_deg: int = 12, value_bits_theta_n: bool = False)\
        -> Recovery:
    """Classify a sequence by SAMPLING a(0..m). Polynomial ⇒ CLOSED_O1 (recovered, held-out verified). Else if
    the value grows exponentially (Θ(n) bits) ⇒ THETA_N_OUTPUT. Else ⇒ DECLINE (C-finite non-poly is handled
    by classify_recurrence)."""
    samples = [(n, seq(n)) for n in range(m + 1)]
    rec = recover_polynomial(samples, max_deg=max_deg)
    if rec is not None:
        return rec
    if value_bits_theta_n:
        return Recovery(THETA_N_OUTPUT, detail="closed formula exists but value has Θ(n) bits ⇒ Ω(n) to emit "
                                               "(Ω(N) axiom) — NOT O(1) evaluation")
    return Recovery(DECLINE, detail="no bounded-degree polynomial structure (held-out check failed)")


def classify_recurrence(c: List[int], init: List[int], m: int = 60, max_deg: int = 12) -> Recovery:
    """Given a C-finite recurrence (currently O(log n) via companion), check whether it is SECRETLY a
    polynomial (all characteristic roots = 1) ⇒ recover O(1). Otherwise it stays OLOGN (EXACT O(1) impossible)."""
    import cfinite
    samples = [(n, cfinite.naive_nth(list(c), list(init), n)) for n in range(m + 1)]
    rec = recover_polynomial(samples, max_deg=max_deg)
    if rec is not None:
        rec.detail += " — upgraded from C-finite O(log n) companion to O(1) polynomial"
        return rec
    return Recovery(OLOGN, detail="C-finite with a non-unit characteristic root (e.g. φ): EXACT value stays "
                                  "O(log n) (companion). O(1) is only a float approximation ⇒ PROBABILISTIC.")


def approx_O1_probabilistic(phi: float, psi: float, scale: float, n: int) -> Tuple[float, Recovery]:
    """A float O(1) APPROXIMATION (e.g. Binet a(n) ≈ φ^n/√5) — explicitly PROBABILISTIC/inexact, NEVER EXACT.
    Returns (approx_value, Recovery with grade=PROBABILISTIC and the |error| as ε)."""
    val = (phi ** n) / scale
    return val, Recovery("CLOSED_O1_APPROX", grade="PROBABILISTIC",
                         detail=f"float approximation (Binet-type) — O(1) but INEXACT (round-off); never EXACT")


# ───────────────────────────── §4.3 measurement: recovery rate by category (held-out verified)
def measure_recovery() -> dict:
    """Run the hidden-closed-form kernel over a category-labeled corpus and report the recovered-to-CLOSED_O1
    rate per category (held-out verified). Honest: polynomial-class recovers; Fibonacci/exp/random do not."""
    import cfinite
    corpus = {
        "polynomial-sum": [                                   # secretly O(1) (often mislabeled O(log n))
            lambda n: n * (n + 1) // 2,                       # Σk
            lambda n: n * (n + 1) * (2 * n + 1) // 6,         # Σk²
            lambda n: (n * (n + 1) // 2) ** 2,                # Σk³
            lambda n: n * n,                                  # Σ(2k-1)
            lambda n: 3 * n * n * n - 2 * n + 5,              # arbitrary cubic
        ],
        "cfinite-nonpoly": [                                  # genuinely O(log n) (NOT recoverable to EXACT O(1))
            lambda n: cfinite.naive_nth([1, 1], [0, 1], n),   # Fibonacci
            lambda n: cfinite.naive_nth([1, 1], [2, 1], n),   # Lucas
            lambda n: cfinite.naive_nth([2], [1], n),         # 2^n (also Θ(n) bits)
        ],
        "general-noise": [                                    # no structure ⇒ DECLINE (Ω(N))
            lambda n: (n * 2654435761) % 1000003,
            lambda n: (n * n * 97 + 7 * n + 13) % 9973 + (1 if (n * 31) % 7 == 0 else 0),
        ],
    }
    exponential = {id(corpus["cfinite-nonpoly"][2])}          # 2^n has Θ(n)-bit values
    out = {}
    for cat, seqs in corpus.items():
        recovered = 0
        for s in seqs:
            rec = classify(s, m=40, value_bits_theta_n=(cat == "cfinite-nonpoly"))
            if rec.status == CLOSED_O1 and rec.grade == "EXACT":
                recovered += 1
        out[cat] = {"recovered_O1": recovered, "n": len(seqs),
                    "rate": round(recovered / len(seqs), 3)}
    return out
