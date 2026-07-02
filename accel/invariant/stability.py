"""
§AO §1.3 — STABILITY / CONVERGENCE verification: an accelerated time-integration kernel must NOT blow up.
================================================================================================================
An accelerated explicit time-stepper is stable iff its von-Neumann amplification factor satisfies |g| ≤ 1 for every
Fourier mode — otherwise the truncation error grows exponentially (garbage at speed). For the explicit-diffusion
update the amplification is g(θ) = 1 − 4c·sin²(θ/2); substituting s = sin²(θ/2) ∈ [0,1] gives g = 1 − 4c·s, and we
z3-prove (QF_LRA, no trig) ∀s∈[0,1]: −1 ≤ 1 − 4c·s ≤ 1 — i.e. the CFL bound 0 ≤ c ≤ ½. A CFL-violating acceleration
(c > ½) ⇒ z3 finds a mode where |g| > 1 ⇒ REJECT. ★ false "stable" = 0.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Optional


@dataclass
class StabilityResult:
    stable: bool
    cfl_number: Optional[Fraction] = None
    verdict: object = None
    detail: str = ""


def verify_cfl_diffusion(c) -> StabilityResult:
    """z3 (QF_LRA): ∀ s∈[0,1]. |1 − 4c·s| ≤ 1 — the explicit-diffusion amplification is bounded (stable) at CFL `c`.
    c ≤ ½ ⇒ stable; c > ½ ⇒ z3 returns a mode with |g|>1 ⇒ DECLINE (the accelerated stepper would diverge)."""
    import z3
    import kernel_verdict as KV
    cf = Fraction(c).limit_denominator(10 ** 9)
    s = z3.Real("s")
    g = 1 - 4 * z3.RealVal(cf) * s
    solver = z3.Solver()
    solver.add(s >= 0, s <= 1, z3.Or(g > 1, g < -1))       # ∃ mode where |g| > 1 (unstable)?
    if solver.check() == z3.unsat:
        cert = KV.Cert(KV.EXACT, "invariant", passed=True, check_cost="z3 QF_LRA ∀s∈[0,1]: |1−4c·s|≤1",
                       detail=f"explicit-diffusion amplification |g|≤1 ∀ mode at CFL c={cf} ≤ ½ — von-Neumann stability z3-proven")
        return StabilityResult(True, cf, KV.exact({"cfl": str(cf)}, "accel.stability", "von-Neumann stable", cert),
                               f"stable: |g|≤1 ∀ mode at c={cf}")
    return StabilityResult(False, cf, KV.decline(f"stability: CFL c={cf} > ½ ⇒ |g|>1 for some mode ⇒ truncation error "
                           "blows up ⇒ REJECT acceleration", "accel.stability"), f"UNSTABLE at c={cf} (CFL violated)")


def adversarial_battery() -> dict:
    """★ an accelerated diffusion stepper at the CFL limit c=½ is STABLE (z3-proven |g|≤1 ∀ mode); ★ c=¼ stable; ★★ a
    CFL-VIOLATING acceleration c=0.6 is REJECTED (z3 finds an unstable mode — false "stable" 0); ★ c=1.0 rejected."""
    half = verify_cfl_diffusion(Fraction(1, 2))
    quarter = verify_cfl_diffusion(Fraction(1, 4))
    over = verify_cfl_diffusion(Fraction(3, 5))            # 0.6 > 0.5 ⇒ unstable
    one = verify_cfl_diffusion(Fraction(1))
    cases = {
        "cfl_half_stable": half.stable,
        "cfl_quarter_stable": quarter.stable,
        "cfl_violated_rejected": not over.stable,               # ★★ false "stable" 0
        "cfl_one_rejected": not one.stable,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
