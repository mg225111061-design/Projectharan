"""
§AD GAP 6 — THE FLOAT-EXACT SUBSET (the float that is genuinely EXACT, proved by IEEE-754 theory).
================================================================================================================
`x*2.0`, `x*0.5`, multiplication by powers of two, and similar are BIT-EXACT in IEEE-754 (only the exponent changes, no
mantissa rounding) — yet we treat ALL float as approximate (DECLINE or APPROX-ε). Fix: identify the float ops that are
PROVABLY bit-exact and fold them as EXACT — not APPROX-ε, EXACT — because they genuinely produce the exact result.

★ z3 gate (EXACT ONLY when proved bit-exact): the discriminator is ROUNDING-MODE INDEPENDENCE — if `fpMul(RNE,x,c) ==
fpMul(RTP,x,c)` for all x in the domain, NO rounding decision was made ⇒ the op is bit-exact. z3's FloatingPoint theory
proves it (Float32). ★ EXACT ONLY where this holds; everything else — the vast majority of float arithmetic — stays
APPROX-ε (§AB) or DECLINE. NO silent promotion: `x*3.0` (rounding-mode-dependent ⇒ inexact) claimed EXACT is REJECTED.
Reuses z3's IEEE-754 theory + the §AB grade boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class FloatExactFold:
    issued: bool                            # folded as EXACT (genuinely bit-exact)
    grade: str = "EXACT"                    # "EXACT" (bit-exact proved) | "APPROX-ε/DECLINE" (not bit-exact)
    multiplier: float = 0.0
    bit_exact: bool = False
    domain: str = "normal, |x| ≤ 1e30 (Float32)"
    detail: str = ""


def prove_bit_exact_scale(c_val: float) -> bool:
    """z3 IEEE-754 (Float32): is `x*c` bit-exact over the normal, non-overflow domain? Discriminator = rounding-mode
    independence — ∃ x with fpMul(RNE,x,c) ≠ fpMul(RTP,x,c)? unsat ⇒ no rounding ever ⇒ BIT-EXACT."""
    import z3
    fp = z3.FPSort(8, 24)
    x = z3.FP("x", fp)
    c = z3.FPVal(c_val, fp)
    s = z3.Solver()
    s.add(z3.Not(z3.fpIsNaN(x)), z3.Not(z3.fpIsInf(x)), z3.Not(z3.fpIsSubnormal(x)), z3.Not(z3.fpIsZero(x)))
    s.add(z3.fpLEQ(z3.fpAbs(x), z3.FPVal(1e30, fp)))         # bound away from overflow (the stated domain)
    s.add(z3.Not(z3.fpEQ(z3.fpMul(z3.RNE(), x, c), z3.fpMul(z3.RTP(), x, c))))
    return s.check() == z3.unsat


def float_exact_fold(c_val: float) -> FloatExactFold:
    """Fold `x*c` as EXACT iff z3 proves it bit-exact (rounding-mode independent) over the domain. ★ Otherwise it is NOT
    promoted to EXACT — it stays APPROX-ε/DECLINE (no silent promotion of inexact float)."""
    exact = prove_bit_exact_scale(c_val)
    if exact:
        return FloatExactFold(True, "EXACT", c_val, True,
                              detail=f"x*{c_val} is BIT-EXACT over the normal/non-overflow domain (z3 IEEE-754: "
                                     "rounding-mode independent ⇒ no rounding) ⇒ folds EXACT (not APPROX-ε)")
    return FloatExactFold(False, "APPROX-ε/DECLINE", c_val, False,
                          detail=f"x*{c_val} is NOT bit-exact (rounding-mode dependent ⇒ rounding occurs) ⇒ stays "
                                 "APPROX-ε/DECLINE (NO silent promotion to EXACT)")


def adversarial_battery() -> dict:
    """x*2.0 and x*4.0 (powers of two) fold EXACT (z3 bit-exact); ★ x*3.0 and x*1.1 are NOT bit-exact ⇒ NOT promoted to
    EXACT (stay APPROX-ε/DECLINE); ★ a non-bit-exact op claimed EXACT is REJECTED; x*0.5 is honestly NOT universally
    bit-exact over normals (underflow at the bottom) ⇒ not claimed EXACT."""
    two = float_exact_fold(2.0)
    four = float_exact_fold(4.0)
    three = float_exact_fold(3.0)
    onepoint1 = float_exact_fold(1.1)
    half = float_exact_fold(0.5)                             # underflows at the smallest normals ⇒ not universal-exact
    cases = {
        "pow2_up_folds_exact": two.issued and two.grade == "EXACT" and two.bit_exact,
        "pow4_folds_exact": four.issued and four.grade == "EXACT",
        "times_three_not_exact": (not three.issued) and three.grade == "APPROX-ε/DECLINE",   # ★ no promotion
        "times_1_1_not_exact": not onepoint1.issued,
        "half_not_universally_exact": not half.issued,        # ★ honest: underflow boundary ⇒ not claimed EXACT
        "no_silent_promotion": "no silent promotion".lower() in three.detail.lower(),
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
