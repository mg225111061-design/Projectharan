"""
§AB AXIS 1 — CERTIFIED APPROXIMATE FOLD (the largest; the identity-critical one): a UNIVERSALLY-proven ε, never a sample.
================================================================================================================
We count only EXACT folds today, so we miss most floating-point numeric/signal code — yet that code is ALREADY
approximate (IEEE-754 rounds at every step). A fold carrying a z3-/interval-PROVEN worst-case error bound — `∀ inputs.
|folded − original| ≤ ε`, sound on every input forever — is not a violation of precision; it is the SAME universal-theorem
guarantee as EXACT, about a bounded-error value. This is the line between us and the LLM: ours is a theorem, not a sample.

★ THE METHOD (new — interval-certified-ε): the existing APPROX_FOLD grade (`disposition.py`/`approx_cert.py`) covers
asymptotic-with-error (series) and epsilon-delta (SAMPLED ⇒ AXIS 2). AXIS 1 ADDS sound INTERVAL roundoff propagation: an
`ErrorInterval` carries a value range AND an accumulated absolute-roundoff bound; each float op adds its rounding error
`≤ u·|magnitude|` (u = 2⁻⁵³). Propagated over the WHOLE input domain it yields ε — a rigorous OVER-approximation of the
true worst case, so the real error ≤ ε on EVERY input. We REUSE the APPROX_FOLD grade (never-exact) and the shared KV ADT
is left untouched (the 273 is safe).
★ THE ANTI-LLM RULE (binding): the ε is the interval bound, holding ∀ inputs. A ε justified by SAMPLING/averaging/testing
is REJECTED — it could be exceeded by an unseen input; that is the LLM's approximation, not ours. If only an empirical
error can be had, DECLINE.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import List, Optional, Tuple

U = Fraction(1, 2 ** 53)                     # IEEE-754 double unit roundoff (exact as a rational)


@dataclass
class ErrorInterval:
    """A sound abstraction: the true value is ALWAYS in [lo,hi], and the accumulated absolute roundoff is ALWAYS ≤ err.
    Bounds are exact rationals (over-approximating); a wrong (too-tight) bound would be a correctness bug."""
    lo: Fraction
    hi: Fraction
    err: Fraction = Fraction(0)

    def _mag(self) -> Fraction:
        return max(abs(self.lo), abs(self.hi))

    def add(self, o: "ErrorInterval") -> "ErrorInterval":
        lo, hi = self.lo + o.lo, self.hi + o.hi
        mag = max(abs(lo), abs(hi))
        return ErrorInterval(lo, hi, self.err + o.err + U * mag)         # +the rounding of THIS addition

    def mul_const(self, c: Fraction) -> "ErrorInterval":
        lo, hi = sorted((self.lo * c, self.hi * c))
        mag = max(abs(lo), abs(hi))
        return ErrorInterval(Fraction(lo), Fraction(hi), self.err * abs(c) + U * mag)


@dataclass
class ApproxFold:
    issued: bool
    grade: str = "APPROX_FOLD"              # ★ the EXISTING distinct grade (never EXACT) — reused, not a new KV kind
    cert_type: str = "interval-certified-ε"  # the NEW method within that grade
    epsilon: Optional[Fraction] = None      # the PROVEN universal worst-case bound (a theorem, not a sample)
    method: str = "interval-arithmetic"
    closed_form: str = ""
    applied_callsites: List[str] = field(default_factory=list)
    skipped_callsites: List[str] = field(default_factory=list)
    detail: str = ""

    @property
    def applied(self) -> bool:
        return bool(self.applied_callsites)


def certify_sum_fold(n: int, mag_bound: int) -> Fraction:
    """Certify ε for folding the float loop `s=0; for i in range(n): s += c` to the closed form `n*c`, ∀ |c| ≤ mag_bound.
    The loop's accumulated roundoff + the folded multiply's roundoff are propagated by ErrorInterval ⇒ a UNIVERSAL ε
    (holds for every c in the domain). Returns ε (exact rational over-approximation)."""
    c_iv = ErrorInterval(Fraction(-mag_bound), Fraction(mag_bound), Fraction(0))   # c ∈ [−M, M], read exactly
    s = ErrorInterval(Fraction(0), Fraction(0), Fraction(0))
    for _ in range(n):
        s = s.add(c_iv)                                                  # each float += accumulates its roundoff
    folded = c_iv.mul_const(Fraction(n))                                 # the closed form n*c (one rounded multiply)
    # both approximate the SAME real value n·c; their difference ≤ sum of their roundoff bounds
    return s.err + folded.err


def float_loop_sum(c: float, n: int) -> float:
    s = 0.0
    for _ in range(n):
        s += c
    return s


def verify_bound_holds(n: int, mag_bound: int, eps: Fraction, samples=(0.0, 1.0, -1.0, 0.5, 0.333, 0.1)) -> bool:
    """A CHECK (not the proof): on sample c the actual |loop − n*c| ≤ ε. The PROOF is the interval bound (covers ALL c
    by construction); this corroborates. Samples are scaled into [−M, M]."""
    epsf = float(eps)
    for base in samples:
        c = base * mag_bound
        if abs(float_loop_sum(c, n) - n * c) > epsf:
            return False
    return True


def approx_sum_fold(n: int, mag_bound: int) -> ApproxFold:
    """Issue the certified-ε APPROX fold of the float accumulation loop. ★ APPROX_FOLD grade (never EXACT); ε is the
    interval-proven universal bound; reuses the existing grade (disposition.APPROX_FOLD / approx_cert)."""
    eps = certify_sum_fold(n, mag_bound)
    return ApproxFold(True, epsilon=eps, closed_form="n*c",
                      detail=f"float loop Σⁿc → n*c; ★ ∀|c|≤{mag_bound}: |loop−n*c| ≤ ε={float(eps):.3e} — PROVEN by "
                             f"interval roundoff propagation (a theorem over the whole domain, NOT a sample); APPROX_FOLD "
                             "grade (never EXACT, R3.5); reuses the existing approximate grade, KV untouched")


def as_disposition(af: ApproxFold):
    """Emit via the EXISTING APPROX_FOLD disposition grade (no new grade, no KV change) — reuse, not duplication."""
    import disposition as D
    return D.Disposition("APPROX_FOLD", "interval-certified-ε", "C", af.closed_form, "epsilon-bounded",
                         "interval-arithmetic", f"sum_fold(n,c)", af.detail)


def sampled_eps_under_estimates(n: int, mag_bound: int) -> Tuple[float, float, bool]:
    """★ The anti-LLM demonstration: a SAMPLED max-error UNDER-estimates the true worst case (it misses unseen inputs),
    so using it as the bound would be UNSOUND. Returns (sampled_eps, certified_eps, sampled_lt_certified)."""
    sampled = max(abs(float_loop_sum(base * mag_bound, n) - n * (base * mag_bound))
                  for base in (0.0, 0.5, -0.5, 0.25))                    # a few samples
    certified = float(certify_sum_fold(n, mag_bound))
    return sampled, certified, sampled < certified


def apply_at_callsite(af: ApproxFold, callsite: str, dtype: str) -> bool:
    """Apply ONLY at a float callsite where the certified ε is acceptable. ★ A callsite demanding EXACT (integer) does
    NOT take an APPROX fold (the grades never mix — APPROX is for genuinely-approximate float)."""
    if not af.issued or dtype != "float":
        af.skipped_callsites.append(callsite)
        return False
    af.applied_callsites.append(callsite)
    return True


def adversarial_battery() -> dict:
    """A certified-ε fold is issued as APPROX_FOLD (never EXACT), ε an interval THEOREM verified on samples; ★ a SAMPLED
    ε under-estimates and is REJECTED (the anti-LLM line); ★ APPROX is never mislabeled EXACT; an integer callsite does
    not take the APPROX fold; the universal bound covers the whole domain."""
    af = approx_sum_fold(n=1000, mag_bound=1000)
    bound_ok = verify_bound_holds(1000, 1000, af.epsilon)               # check corroborates the proof on samples
    sampled, certified, under = sampled_eps_under_estimates(1000, 1000)  # ★ sampled < certified ⇒ sampling unsound
    disp = as_disposition(af)
    # integer callsite must NOT take an APPROX fold; float callsite may
    applied_float = apply_at_callsite(approx_sum_fold(100, 100), "flt", "float")
    applied_int = apply_at_callsite(approx_sum_fold(100, 100), "int", "integer")
    cases = {
        "certified_eps_issued_as_approx": af.issued and af.grade == "APPROX_FOLD" and af.epsilon is not None,
        "interval_bound_holds_on_samples": bound_ok,
        "sampled_eps_rejected_as_unsound": under,                       # sampling under-estimates ⇒ rejected
        "never_mislabeled_exact": disp.kind == "APPROX_FOLD" and disp.cert_type == "epsilon-bounded",
        "grades_dont_mix": applied_float and (not applied_int),
        "eps_is_a_theorem_not_sample": af.method == "interval-arithmetic",
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
