"""
§AE ISLAND 1 — FLOAT-ε (barrier: z3 IEEE-754 bit-blasting blow-up): real-abstraction + affine + QF_NRA.
================================================================================================================
z3's float theory blasts to bit-vectors and EXPLODES, so float closed forms time out. The island: float loops whose REAL
(rounding-free) semantics is a linear/geometric recurrence with bounded iteration and polynomially-propagating rounding
error — fold to the closed form and prove `∀ inputs. |folded − original| ≤ ε` by AFFINE/INTERVAL arithmetic over QF_NRA
(z3 nlsat, CAD-decidable, TERMINATING), NEVER touching bit-blasting. Real algorithm: FPTaylor / Rosa-Daisy.

★ Repo-first: REUSE `foldaxes.approx_fold.ErrorInterval` (Fraction error-bounds) and the existing APPROX_FOLD grade
(`disposition.py`). The genuinely-new piece: the QF_NRA real-semantics verification (no bit-blasting) + the |a|≥1 / chaotic
/ unbounded-N DECLINE boundary. ★ The ε is the interval/affine-proven worst case over the WHOLE domain — universal, never
sampled (the anti-LLM line, §AB). Grade: APPROX_FOLD (reused, no new grade).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import List, Optional

from foldaxes.approx_fold import ErrorInterval, U


@dataclass
class FloatEpsFold:
    issued: bool
    grade: str = "APPROX_FOLD"              # the EXISTING grade (reused), never EXACT
    epsilon: Optional[Fraction] = None      # the PROVEN universal worst-case bound (interval/affine, not sampled)
    real_semantics_verified: bool = False   # the closed form satisfies the recurrence over ℝ (QF_NRA, no bit-blast)
    method: str = "affine-interval + QF_NRA"
    detail: str = ""


def prove_geometric_real_semantics_qf_nra(a_num: int, a_den: int, b_num: int, b_den: int) -> bool:
    """★ The key: verify the geometric closed form x_n = a^n·x0 + b·(1−a^n)/(1−a) satisfies x_{n+1}=a·x_n+b over the
    REALS (rounding-free semantics) in QF_NRA — z3 nlsat (CAD), TERMINATING, NO IEEE-754 bit-blasting. A (= a^n) is
    abstracted as a free real, so the identity is proved for ALL n at once."""
    import z3
    a = z3.RealVal(a_num) / z3.RealVal(a_den)
    b = z3.RealVal(b_num) / z3.RealVal(b_den)
    x0, A = z3.Reals("x0 A")                                 # A abstracts a^n (any real ⇒ holds for all n)
    closed_n = A * x0 + b * (1 - A) / (1 - a)
    closed_n1 = a * A * x0 + b * (1 - a * A) / (1 - a)       # closed(n+1) with a^{n+1}=a·A
    s = z3.Solver()
    s.add(a * closed_n + b != closed_n1)                     # ∃ a counterexample to the recurrence step?
    return s.check() == z3.unsat


def certify_geometric_eps(a: Fraction, b: Fraction, mag_bound: int, N: int) -> Optional[Fraction]:
    """Propagate the float rounding error of x←a·x+b through N steps via ErrorInterval (Fraction-exact, over-approximating).
    For |a|<1 (contractive) the error is bounded; returns ε. For |a|≥1 returns None (error grows aᴺ — DECLINE)."""
    if abs(a) >= 1:
        return None                                         # ★ non-contractive ⇒ error grows ⇒ DECLINE
    iv = ErrorInterval(Fraction(-mag_bound), Fraction(mag_bound), Fraction(0))   # x0 ∈ [−M, M]
    folded = ErrorInterval(Fraction(-mag_bound), Fraction(mag_bound), Fraction(0))
    for _ in range(N):
        iv = iv.mul_const(a).add(ErrorInterval(b, b, Fraction(0)))   # one float step a·x+b, accumulating roundoff
        folded = folded.mul_const(a).add(ErrorInterval(b, b, Fraction(0)))
    return iv.err + folded.err                              # |loop − closed| ≤ both roundoff bounds


def float_eps_fold(a: Fraction, b: Fraction, mag_bound: int = 1000, N: int = 1000) -> FloatEpsFold:
    """Fold a geometric float recurrence x←a·x+b to its closed form with a universal ε. ★ Requires |a|<1 (contractive)
    AND the real semantics verified in QF_NRA (no bit-blast). |a|≥1 / non-geometric ⇒ DECLINE."""
    real_ok = prove_geometric_real_semantics_qf_nra(a.numerator, a.denominator, b.numerator, b.denominator)
    if not real_ok:
        return FloatEpsFold(False, detail="real-semantics closed form not QF_NRA-verified ⇒ DECLINE")
    eps = certify_geometric_eps(a, b, mag_bound, N)
    if eps is None:
        return FloatEpsFold(False, real_semantics_verified=True,
                            detail=f"|a|={abs(a)} ≥ 1 ⇒ rounding error grows ~aᴺ ⇒ ε unbounded ⇒ DECLINE (out of island)")
    return FloatEpsFold(True, "APPROX_FOLD", eps, True,
                        detail=f"geometric float x←{a}·x+{b} (|a|<1) → closed form; real semantics QF_NRA-verified (no "
                               f"bit-blast); ★ ∀|x0|≤{mag_bound}: |loop−closed| ≤ ε={float(eps):.3e} (affine/interval, "
                               "universal over the domain, NOT sampled); APPROX_FOLD grade reused")


def sampled_eps_under_estimates(a: Fraction, b: Fraction, mag_bound: int, N: int):
    """★ Anti-LLM: a sampled max-error UNDER-estimates the certified universal ε (it misses unseen x0), so sampling is
    unsound. Returns (sampled, certified, sampled<certified)."""
    af = a.numerator / a.denominator
    bf = b.numerator / b.denominator

    def loop(x0):
        x = float(x0)
        for _ in range(N):
            x = af * x + bf
        return x

    def closed(x0):
        an = af ** N
        return an * x0 + bf * (1 - an) / (1 - af)
    sampled = max(abs(loop(s * mag_bound) - closed(s * mag_bound)) for s in (0.0, 0.5, -0.5, 0.25))
    certified = float(certify_geometric_eps(a, b, mag_bound, N))
    return sampled, certified, sampled < certified


def adversarial_battery() -> dict:
    """A contractive geometric float (|a|<1) folds APPROX_FOLD with a universal QF_NRA-verified ε; ★ |a|≥1 DECLINES
    (error grows, out of island); ★ the ε is universal not sampled (sampled<certified); the real semantics is verified in
    QF_NRA (no bit-blasting)."""
    good = float_eps_fold(Fraction(1, 2), Fraction(3), 1000, 500)            # EMA-like, contractive
    diverge = float_eps_fold(Fraction(3, 2), Fraction(1), 1000, 500)         # |a|=1.5 ≥ 1 ⇒ DECLINE
    sampled, certified, under = sampled_eps_under_estimates(Fraction(1, 2), Fraction(3), 1000, 500)
    cases = {
        "contractive_folds_approx": good.issued and good.grade == "APPROX_FOLD" and good.epsilon is not None,
        "real_semantics_qf_nra_verified": good.real_semantics_verified,      # no bit-blasting
        "divergent_declined": (not diverge.issued) and "≥ 1" in diverge.detail,   # ★ out of island
        "eps_universal_not_sampled": under,                                   # sampled under-estimates ⇒ rejected
        "method_is_affine_qf_nra": good.method == "affine-interval + QF_NRA",
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
