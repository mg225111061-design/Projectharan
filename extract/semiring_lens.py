"""
§AQ §7 — Q12 SEMIRING LENS (an ORGANIZING frame, not a build item). "Any loop = a semiring path problem; N iterations =
================================================================================================================
the matrix closure (Kleene star)." The lens names which semiring a loop's accumulation lives in:
  ℕ (+, ×)        — COUNT      (e.g. §6 I/O counts)         → EXACT
  (min, +)        — COST       (shortest-path / DP)          → EXACT
  Boolean (∨, ∧)  — REACHABILITY (control-flow reach)        → EXACT
  GF(2) (⊕, ∧)    — PARITY / CRC (§2)                        → EXACT
  probability (+, ×) over [0,1] — STOCHASTIC                 → ★ PROBABILISTIC (never EXACT, aggregated separately)
★ This is a unifying view over §2..§6, NOT a new mechanism (S-1). ★ Dual metric: Axis B ≈ 0 (counts/closures are cheap),
Axis A broadly positive. The probability semiring is the honest exception — graded PROBABILISTIC, kept out of the
EXACT numerator.
"""
from __future__ import annotations

from dataclasses import dataclass

_SEMIRINGS = {
    "count": {"carrier": "ℕ", "ops": "(+, ×)", "grade": "EXACT", "example": "§6 I/O counts"},
    "cost": {"carrier": "(min,+)", "ops": "(min, +)", "grade": "EXACT", "example": "shortest-path / DP"},
    "reach": {"carrier": "Boolean", "ops": "(∨, ∧)", "grade": "EXACT", "example": "control-flow reachability"},
    "parity": {"carrier": "GF(2)", "ops": "(⊕, ∧)", "grade": "EXACT", "example": "§2 CRC / parity"},
    "probability": {"carrier": "[0,1]", "ops": "(+, ×)", "grade": "PROBABILISTIC", "example": "Markov / stochastic"},
}


@dataclass
class SemiringView:
    semiring: str
    grade: str
    detail: str = ""


def classify(reduction: str) -> SemiringView:
    """Name the semiring of a loop's accumulation op (organizing only)."""
    r = reduction.lower()
    if any(k in r for k in ("count", "+", "sum", "num")):
        sr = "count"
    elif "min" in r or "max" in r or "cost" in r or "dist" in r:
        sr = "cost"
    elif "or" in r or "any" in r or "reach" in r or "bool" in r:
        sr = "reach"
    elif "xor" in r or "^" in r or "parity" in r or "crc" in r:
        sr = "parity"
    elif "prob" in r or "*p" in r or "markov" in r:
        sr = "probability"
    else:
        sr = "count"
    meta = _SEMIRINGS[sr]
    return SemiringView(sr, meta["grade"], f"{sr} semiring {meta['carrier']} {meta['ops']} ⇒ {meta['grade']} (Kleene-star matrix closure)")


def adversarial_battery() -> dict:
    """★ the four deterministic semirings (count/cost/reach/parity) grade EXACT (Kleene-star = matrix closure, a unifying
    view over §2..§6); ★★ the PROBABILITY semiring grades PROBABILISTIC — never EXACT, aggregated separately (honest)."""
    cases = {
        "count_exact": classify("count += 1").grade == "EXACT",
        "cost_exact": classify("dist = min(dist, d)").grade == "EXACT",
        "reach_exact": classify("reached = reached or e").grade == "EXACT",
        "parity_exact": classify("crc ^= b").grade == "EXACT",
        "probability_is_probabilistic": classify("p = p * markov").grade == "PROBABILISTIC",   # ★★ not EXACT
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
