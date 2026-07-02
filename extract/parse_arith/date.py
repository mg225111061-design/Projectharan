"""
§AQ §3.DATE — date→epoch leap-year arithmetic = polynomial + 400-year PERIODIC, z3-RE-VERIFIED (S-2).
================================================================================================================
The Gregorian leap-day count `F(y) = ⌊y/4⌋ − ⌊y/100⌋ + ⌊y/400⌋` is periodic with period 400 (exactly 97 leap days per
400-year cycle) ⇒ ★REDUCE to the existing polynomial + periodic mechanism (S-1). ★★ S-2: this is one of the AI
hand-derived closed forms — z3 PROVES the 400-year periodicity (F(y+400)−F(y)=97 ∀y) and REFUTES the naive Julian
`⌊y/4⌋` (100 ≠ 97 leap days/cycle). Observation ≠ proof.
"""
from __future__ import annotations


def prove_gregorian_period(correct: bool = True) -> bool:
    """z3 LIA (integer division): F(y+400) − F(y) == 97  ∀ y ≥ 0, where F is the Gregorian leap-day count. The WRONG
    (Julian) variant drops the −⌊y/100⌋+⌊y/400⌋ terms ⇒ 100 leap days/cycle ⇒ z3 SAT (≠97)."""
    import z3
    y = z3.Int("y")

    def F(t):
        if correct:
            return t / 4 - t / 100 + t / 400                      # z3 Int '/' is floor-division for nonneg
        return t / 4                                              # Julian (wrong for Gregorian)
    sol = z3.Solver()
    sol.add(y >= 0, F(y + 400) - F(y) != 97)
    return sol.check() == z3.unsat


def prove_is_leap_period() -> bool:
    """z3: the predicate is_leap(y) = (y%4==0 ∧ y%100≠0) ∨ y%400==0 is 400-periodic (is_leap(y) == is_leap(y+400))."""
    import z3
    y = z3.Int("y")

    def is_leap(t):
        return z3.Or(z3.And(t % 4 == 0, t % 100 != 0), t % 400 == 0)
    sol = z3.Solver()
    sol.add(y >= 0, is_leap(y) != is_leap(y + 400))
    return sol.check() == z3.unsat


def adversarial_battery() -> dict:
    """★★ z3 PROVES the Gregorian leap-day count is 400-year periodic with 97 leap days/cycle (the AI closed form
    re-verified, S-2); ★ the is_leap predicate is z3-proven 400-periodic; ★★ the naive Julian formula is z3-REFUTED
    (100 ≠ 97)."""
    cases = {
        "gregorian_period_97_proven": prove_gregorian_period(True),
        "is_leap_400_periodic": prove_is_leap_period(),
        "julian_refuted": not prove_gregorian_period(False),       # ★★ S-2
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
