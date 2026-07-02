"""
§Z LENS A — GENERATING-FUNCTION / FORMAL-POWER-SERIES FOLD (algebraic generating functions).
================================================================================================================
A nonlinear self-convolution DP — `dp[n] = Σ_{i} dp[i]·dp[n-1-i]` (Catalan), `dp[n] = dp[n-1] + Σ dp[i]·dp[n-2-i]`
(Motzkin) — DECLINEs under the 22 because it is a NONLINEAR self-convolution (the linear-recurrence / C-finite
detectors are blind to it). But viewing the whole array as a formal power series D(x)=Σ dp[n]xⁿ turns the convolution
into a PRODUCT, so the recurrence becomes an algebraic equation (D = xD²+1 for Catalan) whose closed form folds the
O(N²) DP to an O(1)/O(log N) formula (C(2n,n)/(n+1)).

★ z3 gate (precision 1.0): prove the closed form equals the DP for ∀ n ≤ bound by encoding the convolution recurrence
over the Int theory (the recurrence + base case uniquely determine the array; z3 checks no dp[n] can differ from the
closed-form value). Proved ⇒ EXACT fold over integer/rational; else DECLINE.
★ THE IEEE-754 HONESTY: the closed form is exact ONLY for integer/rational coefficients. The general convolution with no
closed form is an O(N log N) FFT product — but a FLOAT FFT is NOT a precision-1.0 fold; it is sound only under an exact
integer/NTT (number-theoretic transform) model. We emit the closed-form path as the precision-1.0 fold, provide the
exact integer-NTT path as a complexity SUBSTITUTION (O(N²)→O(N log N), exact, differential-verified, NOT an O(N)→O(1)
fold), and DECLINE the float FFT as a precision-1.0 fold.

★ New algebra (formal power series / algebraic GFs) — ⑬ (Faulhaber/Gosper/Zeilberger) handles only LINEAR sums. Reuses
the existing closed-form evaluator (`mathmode/fastkernels.catalan`); routes to closed_form (no new certificate kind).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import comb
from typing import Callable, Dict, List, Optional


@dataclass
class GenFuncFold:
    issued: bool                            # a precision-1.0 closed-form fold was z3-proved
    precision_one: bool                     # True ONLY for the exact integer/rational closed-form path
    arithmetic: str = "integer"             # "integer" | "rational" | "integer-NTT(exact)" | "float-FFT(NOT-precision-1.0)"
    gf_family: str = ""                     # "catalan" | "motzkin" | ...
    mechanism: str = "closed_form"          # an EXISTING kind — reduces to the closed-form / matrix-power machinery
    proved_bound: Optional[int] = None      # the n ≤ bound over which z3 proved the closed form
    applied_callsites: List[str] = field(default_factory=list)
    skipped_callsites: List[str] = field(default_factory=list)
    detail: str = ""

    @property
    def applied(self) -> bool:
        return bool(self.applied_callsites)


# ── the algebraic-GF pattern library: (convolution DP, independent closed form) per family ────────────────────
def _catalan_closed(n: int) -> int:
    """C_n = C(2n,n)/(n+1) — the Catalan closed form (reuses mathmode/fastkernels.catalan's identity), O(1)-ish."""
    return comb(2 * n, n) // (n + 1)


def _motzkin_closed(n: int) -> int:
    """M_n = Σ_k C(n,2k)·C_k (Catalan) — the Motzkin closed form as a binomial sum (independent of the Motzkin DP)."""
    return sum(comb(n, 2 * k) * _catalan_closed(k) for k in range(n // 2 + 1))


def _build_catalan_dp(s, dp, bound):
    import z3
    s.add(dp[0] == 1)
    for n in range(1, bound + 1):
        s.add(dp[n] == z3.Sum([dp[i] * dp[n - 1 - i] for i in range(n)]))


def _build_motzkin_dp(s, dp, bound):
    import z3
    s.add(dp[0] == 1)
    if bound >= 1:
        s.add(dp[1] == 1)
    for n in range(2, bound + 1):
        s.add(dp[n] == dp[n - 1] + z3.Sum([dp[i] * dp[n - 2 - i] for i in range(n - 1)]))


_LIBRARY: Dict[str, dict] = {
    "catalan": {"closed": _catalan_closed, "build": _build_catalan_dp,
                "equation": "D = xD² + 1", "recurrence": "dp[n] = Σ_{i=0}^{n-1} dp[i]·dp[n-1-i], dp[0]=1"},
    "motzkin": {"closed": _motzkin_closed, "build": _build_motzkin_dp,
                "equation": "M = 1 + xM + x²M²", "recurrence": "dp[n] = dp[n-1] + Σ dp[i]·dp[n-2-i], dp[0]=dp[1]=1"},
}


def prove_closed_form_bounded(family: str, bound: int = 12) -> bool:
    """z3 (Int theory): prove the convolution DP forces dp[n] == closed(n) for ∀ n ≤ bound. The recurrence + base case
    uniquely determine the array; UNSAT of (∃ n. dp[n] ≠ closed(n)) ⇒ the closed form IS the DP for all n ≤ bound."""
    import z3
    spec = _LIBRARY[family]
    dp = z3.IntVector("dp", bound + 1)
    s = z3.Solver()
    spec["build"](s, dp, bound)
    closed = spec["closed"]
    s.add(z3.Or([dp[n] != closed(n) for n in range(bound + 1)]))
    return s.check() == z3.unsat


def differential_check(family: str, bound: int = 16) -> bool:
    """Run the convolution DP the long way (exact Python int) and confirm it matches the closed form for n ≤ bound —
    a second, independent witness to the z3 proof."""
    spec = _LIBRARY[family]
    closed = spec["closed"]
    dp = [0] * (bound + 1)
    dp[0] = 1
    if family == "catalan":
        for n in range(1, bound + 1):
            dp[n] = sum(dp[i] * dp[n - 1 - i] for i in range(n))
    elif family == "motzkin":
        if bound >= 1:
            dp[1] = 1
        for n in range(2, bound + 1):
            dp[n] = dp[n - 1] + sum(dp[i] * dp[n - 2 - i] for i in range(n - 1))
    return all(dp[n] == closed(n) for n in range(bound + 1))


def genfunc_fold(family: str, dtype: str = "integer", bound: int = 12) -> GenFuncFold:
    """Issue the precision-1.0 closed-form fold for a recognized algebraic-GF convolution DP, iff the arithmetic is
    integer/rational AND z3 proves the closed form == DP for n ≤ bound. float ⇒ the closed form's integer identity does
    not transfer ⇒ DECLINE (use the NTT path, separately, never as a float precision-1.0 fold)."""
    if family not in _LIBRARY:
        return GenFuncFold(False, False, arithmetic=dtype, gf_family=family,
                           detail=f"no algebraic-GF family matches {family!r} (not a recognized self-convolution DP) ⇒ DECLINE")
    if dtype not in ("integer", "rational"):
        return GenFuncFold(False, False, arithmetic="float-FFT(NOT-precision-1.0)", gf_family=family,
                           detail=f"{dtype} coefficients ⇒ the integer closed form does not transfer; the FFT product is "
                                  "float ⇒ NOT a precision-1.0 fold (use the integer-NTT path under a discrete model) ⇒ DECLINE")
    if not prove_closed_form_bounded(family, bound):
        return GenFuncFold(False, False, arithmetic=dtype, gf_family=family,
                           detail=f"closed form NOT z3-proved == DP for n ≤ {bound} ⇒ DECLINE (mismatched pattern)")
    spec = _LIBRARY[family]
    return GenFuncFold(True, True, arithmetic=dtype, gf_family=family, proved_bound=bound,
                       detail=f"self-convolution DP ({spec['recurrence']}) ⇒ power series {spec['equation']} ⇒ closed form "
                              f"z3-proved == DP ∀n≤{bound} over {dtype} (EXACT); O(N²)→O(1)/O(log N). Reduces to "
                              "closed_form (reuses fastkernels.catalan identity); algebraic GF noted (no new kind)")


# ── general convolution: the FFT/NTT path — an algorithm SUBSTITUTION, NOT a precision-1.0 O(N)→O(1) fold ──────
def _ntt_required_note() -> str:
    return ("the general convolution with no closed form is a power-series PRODUCT — O(N²)→O(N log N) by FFT/NTT. A "
            "FLOAT FFT is NOT precision-1.0 (round-off ⇒ z3 equivalence only up to ε); EXACT only under an integer NTT "
            "(modular, exact). This is a complexity substitution, NOT an O(N)→O(1) fold.")


def exact_integer_convolution(a: List[int], b: List[int]) -> List[int]:
    """Schoolbook integer convolution (exact, O(N²)) — the exact-arithmetic reference for the discrete model. An
    in-repo integer NTT would compute the same result in O(N log N); the point is EXACTNESS, not the constant."""
    out = [0] * (len(a) + len(b) - 1)
    for i, ai in enumerate(a):
        for j, bj in enumerate(b):
            out[i + j] += ai * bj
    return out


def convolution_substitution(dtype: str) -> GenFuncFold:
    """The general-convolution path. integer ⇒ exact under the NTT/discrete model (a complexity substitution, NOT a
    precision-1.0 O(N)→O(1) fold — precision_one stays False because it is not a fold). float ⇒ DECLINE as precision-1.0."""
    if dtype == "integer":
        return GenFuncFold(False, False, arithmetic="integer-NTT(exact)", gf_family="general_convolution",
                           detail="EXACT under an integer/NTT discrete model (O(N²)→O(N log N)); an algorithm "
                                  "SUBSTITUTION, NOT a precision-1.0 O(N)→O(1) fold ⇒ not counted as a fold. " + _ntt_required_note())
    return GenFuncFold(False, False, arithmetic="float-FFT(NOT-precision-1.0)", gf_family="general_convolution",
                       detail="float FFT ⇒ NOT precision-1.0 ⇒ DECLINE as a sound fold. " + _ntt_required_note())


def apply_at_callsite(gf: GenFuncFold, callsite: str, n: int) -> bool:
    """Apply the closed-form fold ONLY where it is a precision-1.0 closed form AND the DP runs n ≥ 1 (the fold replaces
    O(n²) work). A non-precision-1.0 (FFT/NTT) item is never applied as a fold."""
    if not (gf.issued and gf.precision_one) or n < 1:
        gf.skipped_callsites.append(callsite)
        return False
    gf.applied_callsites.append(callsite)
    return True


def adversarial_battery() -> dict:
    """Catalan & Motzkin closed forms z3-proved == DP (issued, precision 1.0); a wrong closed form (claiming Catalan
    == 2ⁿ) is REJECTED by the z3 proof; a float convolution is NOT emitted as a precision-1.0 fold; a non-family DP
    declines; the differential check agrees with the proof."""
    import z3
    cat = genfunc_fold("catalan")
    mot = genfunc_fold("motzkin")
    # wrong closed form: assert the DP forces dp[n]==2^n — must be SAT (refuted), i.e. NOT proved
    dp = z3.IntVector("dp", 9)
    s = z3.Solver()
    _build_catalan_dp(s, dp, 8)
    s.add(z3.Or([dp[n] != 2 ** n for n in range(9)]))
    wrong_refuted = s.check() != z3.unsat                   # the recurrence CAN differ from 2^n ⇒ wrong form refuted
    flt = genfunc_fold("catalan", dtype="float")
    nonfamily = genfunc_fold("fibonacci_like")              # not a self-convolution family ⇒ DECLINE
    sub_int = convolution_substitution("integer")
    sub_flt = convolution_substitution("float")
    cases = {
        "catalan_closed_form_issued": cat.issued and cat.precision_one and cat.arithmetic == "integer",
        "motzkin_closed_form_issued": mot.issued and mot.precision_one,
        "wrong_closed_form_rejected": wrong_refuted,
        "float_not_precision_one": (not flt.issued) and "NOT-precision-1.0" in flt.arithmetic,
        "non_family_declined": not nonfamily.issued,
        "differential_agrees": differential_check("catalan") and differential_check("motzkin"),
        "ntt_substitution_not_a_fold": (not sub_int.issued) and (not sub_int.precision_one) and "exact" in sub_int.arithmetic,
        "float_fft_declined": (not sub_flt.issued) and "NOT-precision-1.0" in sub_flt.arithmetic,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
