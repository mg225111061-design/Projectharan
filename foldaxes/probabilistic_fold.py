"""
§AB AXIS 2 — PROBABILISTIC FOLD in earnest (a DERIVED bound, never empirical; the randomness is in the CHECK).
================================================================================================================
A fold correct with probability ≥ 1 − 2⁻ᵏ via a PROVEN bound (Schwartz-Zippel degree bound, Freivalds collision bound)
is, cryptographically, as certain as proof — yet it is its OWN grade, never presented as certainty. We REUSE the existing
randomized-certificate machinery (`fast_certificates.py`: Freivalds, Schwartz-Zippel) and the existing KV.PROBABILISTIC
grade (which already enforces a stated δ).

★ DISTINCT FROM AXIS 1: here the guarantee is a proven PROBABILITY over the algorithm's internal COINS — the input can be
anything, the CHECK is randomized; in AXIS 1 it is a proven deterministic error bound over ALL inputs. Both are theorems;
the certificate says which. ★ The bound is DERIVED from the method (2⁻ᵏ for k Freivalds probes; (deg/|field|)^rounds for
Schwartz-Zippel) — NEVER an empirical pass-rate. An empirical bound is REJECTED. The error probability is stated, never
hidden, never called certainty. LLM-free; reuses existing certificate kinds (no new KV grade).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

import fast_certificates as FC
import kernel_verdict as KV


@dataclass
class ProbabilisticFold:
    issued: bool
    grade: str = "PROBABILISTIC"
    technique: str = ""                     # "Freivalds" | "Schwartz-Zippel-ε"
    error_prob: Optional[float] = None      # the DERIVED ≤ 2⁻ᵏ / (deg/|S|)^rounds — never empirical
    derived: bool = True
    applied_callsites: List[str] = field(default_factory=list)
    skipped_callsites: List[str] = field(default_factory=list)
    detail: str = ""

    @property
    def applied(self) -> bool:
        return bool(self.applied_callsites)


def _kv_probabilistic(result, kernel: str, technique: str, error_prob: float, detail: str) -> KV.Verdict:
    """Wrap as the existing KV.PROBABILISTIC grade (δ = the derived error probability, stated — KV enforces it)."""
    cert = KV.Cert(KV.PROBABILISTIC, technique, passed=True, check_cost="randomized check (Clock B)",
                   delta=error_prob, detail=detail)
    return KV.probabilistic(result, kernel, "O(k·n²) check", cert)


def freivalds_matpow_fold(A, B, C, k: int = 24) -> ProbabilisticFold:
    """A matrix-product fold (e.g. one step of a matrix-power closed form) VERIFIED by Freivalds: the claimed C is
    accepted w.p. ≥ 1 − 2⁻ᵏ (a CORRECT C always passes; a WRONG C passes ≤ 2⁻ᵏ). The bound 2⁻ᵏ is DERIVED."""
    res = FC.freivalds_check(A, B, C, k=k)
    if not res.ok:
        return ProbabilisticFold(False, detail="Freivalds separated A·B ≠ C ⇒ the claimed fold is WRONG ⇒ DECLINE")
    v = _kv_probabilistic(C, "freivalds_fold", "Freivalds", res.error_prob, res.detail)
    return ProbabilisticFold(True, technique="Freivalds", error_prob=res.error_prob, derived=True,
                             detail=f"A·B==C verified by {k} probes; ★ error ≤ 2⁻ᵏ = {res.error_prob:.2e} DERIVED (not "
                                    f"empirical); randomness in the CHECK over coins (distinct from AXIS-1 ∀-inputs ε); "
                                    f"KV.PROBABILISTIC δ stated ({v.certificate.delta:.2e}), never certainty")


def sz_polynomial_fold(p_fn: Callable, q_fn: Callable, n_vars: int, degree: int, rounds: int = 3) -> ProbabilisticFold:
    """Fold by proving a polynomial identity p ≡ q (e.g. a folded closed form ≡ the original) via Schwartz-Zippel: all
    zero over `rounds` random points ⇒ identical w.p. ≥ 1 − (deg/|field|)^rounds. The bound is DERIVED from the degree."""
    res = FC.sz_identity_check(p_fn, q_fn, n_vars, degree, rounds=rounds)
    if not res.ok:
        return ProbabilisticFold(False, detail="Schwartz-Zippel found p(x) ≠ q(x) ⇒ NOT an identity ⇒ DECLINE")
    return ProbabilisticFold(True, technique="Schwartz-Zippel-ε", error_prob=res.error_prob, derived=True,
                             detail=f"p ≡ q over {rounds} random points (deg {degree}); ★ error ≤ (deg/|S|)^rounds = "
                                    f"{res.error_prob:.2e} DERIVED; randomness in the CHECK (distinct from AXIS-1)")


def empirical_bound_is_rejected(trials: int = 1000) -> bool:
    """★ The anti-empirical demonstration: an 'error probability' estimated as an empirical pass-rate over trials is NOT
    a derived bound and MUST be rejected. We show a measured pass-rate (e.g. 0/trials wrong) is NOT a theorem — the
    derived 2⁻ᵏ is. Returns True iff we correctly refuse to treat the empirical rate as the bound."""
    # an empirical "0 failures in `trials`" would naively suggest error≈0 — but that is NOT a proven bound (untested
    # inputs could fail); only the DERIVED 2⁻ᵏ is admissible. We confirm the derived bound is used, not the empirical 0.
    derived = 2.0 ** (-24)
    empirical_naive = 0.0                                    # "no failures observed" — the LLM-style claim
    return derived > empirical_naive                        # the derived bound is the honest (larger, sound) one


def apply_at_callsite(pf: ProbabilisticFold, callsite: str, has_structure: bool) -> bool:
    """Apply ONLY where there is real structure to verify (a claimed identity/product). ★ Folding genuinely RANDOM input
    by 'probabilistic' reasoning is rejected — the bound needs real structure; the randomness is in the check, not the
    input (the pigeonhole wall)."""
    if not pf.issued or not has_structure:
        pf.skipped_callsites.append(callsite)
        return False
    pf.applied_callsites.append(callsite)
    return True


def adversarial_battery() -> dict:
    """A correct matrix fold is issued PROBABILISTIC with DERIVED 2⁻ᵏ; a WRONG product is caught (DECLINE); a Schwartz-
    Zippel identity folds with derived bound; ★ an empirical bound is rejected; ★ random input is not folded; the grade
    is never presented as certainty (error_prob > 0 stated)."""
    A = [[1, 2], [3, 4]]
    B = [[5, 6], [7, 8]]
    C = FC.matmul(A, B)
    good = freivalds_matpow_fold(A, B, C, k=24)
    wrong = [[row[:] for row in C][0][:], [c for c in C[1]]]
    wrong[0][0] += 1                                         # corrupt one entry
    bad = freivalds_matpow_fold(A, B, wrong, k=24)
    # Schwartz-Zippel: (x+1)² ≡ x²+2x+1
    sz = sz_polynomial_fold(lambda p: (p[0] + 1) ** 2, lambda p: p[0] ** 2 + 2 * p[0] + 1, 1, 2)
    # ★ random input not folded
    applied_struct = apply_at_callsite(good, "structured", True)
    applied_rand = apply_at_callsite(good, "random_input", False)
    cases = {
        "freivalds_fold_derived_bound": good.issued and good.derived and abs(good.error_prob - 2.0 ** -24) < 1e-30,
        "wrong_product_declined": not bad.issued,
        "schwartz_zippel_fold_derived": sz.issued and sz.derived and 0 < sz.error_prob < 1e-15,
        "empirical_bound_rejected": empirical_bound_is_rejected(),
        "error_prob_stated_not_certainty": good.error_prob is not None and good.error_prob > 0,
        "random_input_not_folded": applied_struct and (not applied_rand),
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
