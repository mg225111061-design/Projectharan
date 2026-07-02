"""
§AO §1.2 — PROBABILITY-AXIOM verification: an accelerated statistical kernel must keep Σp=1, 0≤p≤1 (and PSD covariance).
================================================================================================================
An accelerated Markov / normalization / mixing kernel p ← P·p preserves the probability axioms IFF P is column-
stochastic (every column sums to 1) AND non-negative (entries ≥ 0). We z3-prove Σ(P·p)==Σ(p) ∀p (mass = 1 preserved,
QF_LRA) and check non-negativity (so p ≥ 0 ⇒ P·p ≥ 0). A kernel that lets probability leak (column sum ≠ 1) or go
negative ⇒ REJECT the acceleration. ★ false "valid distribution" = 0.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class ProbabilityResult:
    valid: bool
    verdict: object = None
    detail: str = ""


def verify_probability(P: List[List[float]]) -> ProbabilityResult:
    """z3 (QF_LRA): Σ(P·p) == Σ(p) ∀p (normalization preserved) + all entries ≥ 0 (non-negativity preserved)."""
    import z3
    import kernel_verdict as KV
    from fractions import Fraction
    n = len(P)
    if n == 0 or any(len(r) != n for r in P):
        return ProbabilityResult(False, KV.decline("probability: non-square kernel", "accel.probability"), "shape")
    if any(P[i][j] < 0 for i in range(n) for j in range(n)):
        return ProbabilityResult(False, KV.decline("probability: negative entry ⇒ p can go < 0 ⇒ REJECT", "accel.probability"),
                                 "negative transition entry")
    p = [z3.Real(f"p{i}") for i in range(n)]
    Pp = [z3.Sum([z3.RealVal(Fraction(P[i][j]).limit_denominator(10 ** 9)) * p[j] for j in range(n)]) for i in range(n)]
    s = z3.Solver()
    s.add(z3.Sum(Pp) != z3.Sum(p))                          # ∃p where total probability is NOT preserved?
    if s.check() == z3.unsat:
        cert = KV.Cert(KV.EXACT, "invariant", passed=True, check_cost="z3 QF_LRA ∀p: Σ(Pp)==Σp + nonneg",
                       detail="accelerated stochastic kernel preserves Σp=1 ∀p and non-negativity — probability axioms z3-proven")
        return ProbabilityResult(True, KV.exact({"n": n}, "accel.probability", "probability-preserving", cert),
                                 "Σp=1 preserved ∀p (column-stochastic) and entries ≥ 0")
    return ProbabilityResult(False, KV.decline("probability: Σp NOT preserved (probability leaks) ⇒ REJECT", "accel.probability"),
                             "normalization broken — acceleration rejected")


def adversarial_battery() -> dict:
    """★ a column-stochastic transition (a real Markov step, accelerated) preserves Σp=1 ∀p (z3-proven); ★ a kernel
    that lets probability LEAK (column sum 0.9) is REJECTED; ★ a kernel with a NEGATIVE entry is REJECTED (false
    "valid distribution" 0)."""
    # column-stochastic 3×3 (columns sum to 1)
    stoch = [[0.5, 0.2, 0.3], [0.3, 0.5, 0.3], [0.2, 0.3, 0.4]]
    ok = verify_probability(stoch)
    leak = [[0.5, 0.2, 0.3], [0.3, 0.5, 0.3], [0.1, 0.2, 0.3]]      # column 0 sums 0.9 ⇒ leaks
    lk = verify_probability(leak)
    neg = [[1.2, 0.0, 0.0], [-0.2, 1.0, 0.0], [0.0, 0.0, 1.0]]      # negative entry
    ng = verify_probability(neg)
    cases = {
        "stochastic_preserves_mass": ok.valid,
        "leaky_kernel_rejected": not lk.valid,                  # ★ probability leak rejected
        "negative_entry_rejected": not ng.valid,                # ★ non-negativity enforced
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
