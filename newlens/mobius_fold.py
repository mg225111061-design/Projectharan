"""
§Z LENS C — PROJECTIVE / MÖBIUS FOLD: ★ HONEST OVERLAP — this is ALREADY built (reuse §P P5, count ZERO new).
================================================================================================================
A fractional recurrence x ← (a·x+b)/(c·x+d) DECLINEs under the 22 as nonlinear (the division), but it is a LINEAR map
on the projective line ℙ¹: lift x = u/v to [u,v]ᵀ and the update is the 2×2 matrix [[a,b],[c,d]], so N iterations fold
to Mᴺ in O(log N).

★ THE HONEST FINDING (binding under the §X/§Y/§Z no-double-count spine): this is the IDENTICAL construction already
shipped as `catalog/mobius_fold.py` (§P P5 — "Möbius rational-recurrence face of ⑬"): the same PGL₂ lift, the same Mᴺ
binary-exponentiation fold, the same z3 cleared-denominator polynomial identity, the same matrix_recurrence kind, the
same ad−bc=0 / pole guards. The directive's "no overlap" check named QF_BV/Galois/stride — but the real overlap is
against our OWN prior work. So LENS C is NOT new to this repo. We REUSE §P P5 (no duplication), add only the §Z
refinements below, and count the projective fold as ZERO new fold-rate contribution (already counted in §P).

★ THE §Z REFINEMENTS (the only genuinely-added value): (1) an EXPLICIT orbit nonzero-denominator guard for a GIVEN
initial state x₀ — §P P5 notes the pole as a "decidable island" but does not check a specific orbit; we iterate the
exact-rational orbit and DECLINE if c·xₙ+d = 0 is ever hit; (2) the float IEEE-754 caveat — exact over rational,
DECLINED for float (the projective closed form holds over ℝ but float division accumulates round-off).

★ Reuses matrix_recurrence (existing kind, via §P P5); no new certificate kind; no double-count.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import List, Optional, Tuple


@dataclass
class MobiusFold:
    issued: bool                            # the homographic fold is valid here (reusing §P P5 + the orbit guard)
    new_contribution: bool = False          # ★ ALWAYS False — the projective fold is §P P5, counted ZERO (no double-count)
    arithmetic: str = "rational"            # "rational" | "float(DECLINED)"
    mechanism: str = "matrix_recurrence"    # reuses §P P5's existing kind
    orbit_guard_ok: Optional[bool] = None   # the explicit nonzero-denominator guard along THIS x₀'s orbit (the §Z add)
    first_pole_step: Optional[int] = None
    applied_callsites: List[str] = field(default_factory=list)
    skipped_callsites: List[str] = field(default_factory=list)
    detail: str = ""

    @property
    def applied(self) -> bool:
        return bool(self.applied_callsites)


def orbit_nonzero_denominator_guard(a, b, c, d, x0, N: int) -> Tuple[bool, Optional[int]]:
    """★ §Z refinement: iterate the EXACT-rational orbit x₀…x_{N-1} and prove c·xₙ+d ≠ 0 at every step actually taken
    (a division by zero = an undefined orbit ⇒ DECLINE that initial state). Returns (ok, first_pole_step)."""
    x = Fraction(x0)
    for n in range(N):
        denom = Fraction(c) * x + d
        if denom == 0:
            return False, n
        x = (Fraction(a) * x + b) / denom
    return True, None


def _pgl2_valid(a, b, c, d) -> bool:
    """Reuse §P P5's z3-proved PGL₂ fold verdict: EXACT iff the homographic map folds soundly (ad−bc ≠ 0 + the cleared-
    denominator polynomial identity proved). This is the existing machinery — we do NOT re-derive it."""
    import kernel_verdict as KV
    import catalog.mobius_fold as P5
    return P5.mobius_fold_grade(a, b, c, d).status == KV.EXACT


def mobius_fold(a, b, c, d, x0=1, N: int = 16, dtype: str = "rational") -> MobiusFold:
    """Issue the homographic fold for x ← (a·x+b)/(c·x+d) iterated N times from x₀, REUSING §P P5's PGL₂ machinery and
    ADDING the §Z orbit guard + float caveat. ★ new_contribution is ALWAYS False — the projective fold is already
    counted in §P, so this contributes ZERO to the NEW fold rate (no double-count)."""
    if dtype not in ("rational", "integer"):
        return MobiusFold(False, False, arithmetic="float(DECLINED)",
                          detail="float operands ⇒ the projective closed form is exact over ℝ/ℚ but IEEE-754 division "
                                 "accumulates round-off ⇒ DECLINE (exact only for rational; FPSort out of scope)")
    if not _pgl2_valid(a, b, c, d):
        return MobiusFold(False, False, arithmetic=dtype,
                          detail="§P P5 PGL₂ fold does not hold (ad−bc = 0 degenerate, or identity unproved) ⇒ DECLINE")
    ok, pole_n = orbit_nonzero_denominator_guard(a, b, c, d, x0, N)
    if not ok:
        return MobiusFold(False, False, arithmetic=dtype, orbit_guard_ok=False, first_pole_step=pole_n,
                          detail=f"orbit from x₀={x0} hits the pole c·x+d=0 at step {pole_n} (undefined) ⇒ DECLINE "
                                 "(the §Z explicit orbit guard — §P P5 alone marks the pole an island)")
    return MobiusFold(True, False, arithmetic=dtype, mechanism="matrix_recurrence", orbit_guard_ok=True,
                      detail=f"x←({a}x+{b})/({c}x+{d}) lifts to ℙ¹: Mᴺ binary-exp fold O(N)→O(log N), z3-proved by §P P5 "
                             f"(REUSED, not duplicated); §Z orbit guard: c·xₙ+d≠0 ∀n<{N} from x₀={x0} (exact-rational). "
                             "★ new_contribution=False — already counted in §P, ZERO new fold rate (no double-count)")


def apply_at_callsite(mf: MobiusFold, callsite: str, n: int) -> bool:
    """Apply ONLY where issued and n ≥ 1. ★ Even when applied, this contributes ZERO to the NEW fold rate (the report
    excludes new_contribution=False) — the callsite is real but the fold is §P P5's, already counted."""
    if not mf.issued or n < 1:
        mf.skipped_callsites.append(callsite)
        return False
    mf.applied_callsites.append(callsite)
    return True


def adversarial_battery() -> dict:
    """A safe-orbit homographic folds (issued, but new_contribution=False ⇒ zero new); ★ an orbit that hits a zero
    denominator is DECLINED by the §Z guard; a float fold is DECLINED (IEEE-754); a degenerate ad−bc=0 map is DECLINED
    (via §P P5); ★ the zero-new-count invariant holds (no double-count with §P)."""
    safe = mobius_fold(1, 1, 1, 2, x0=1, N=20)              # x→(x+1)/(x+2), orbit stays positive ⇒ denom≠0
    pole = mobius_fold(0, 1, 1, 0, x0=0, N=5)               # x→1/x from x₀=0 ⇒ denom=0 at step 0 ⇒ DECLINE
    flt = mobius_fold(1, 1, 1, 2, x0=1, N=20, dtype="float")
    degen = mobius_fold(2, 2, 1, 1, x0=1, N=5)              # ad−bc = 2−2 = 0 ⇒ §P declines
    applied = apply_at_callsite(safe, "iir_hot", 100000)
    cases = {
        "safe_orbit_issued": safe.issued and safe.orbit_guard_ok,
        "zero_new_contribution": (not safe.new_contribution) and (not pole.new_contribution),  # ★ no double-count
        "zero_denominator_orbit_declined": (not pole.issued) and pole.first_pole_step == 0,
        "float_declined": (not flt.issued) and flt.arithmetic == "float(DECLINED)",
        "degenerate_declined": not degen.issued,
        "applied_but_still_zero_new": applied and (not safe.new_contribution),
        "reuses_matrix_recurrence": safe.mechanism == "matrix_recurrence",
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
