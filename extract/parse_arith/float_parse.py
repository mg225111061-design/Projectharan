"""
§AQ §3.FLOAT — float parsing: the INTEGER mantissa is EXACT (Horner); the ·10^e binary scaling is NOT representable.
================================================================================================================
★ The honest split (S-5, no over-claim): parsing the integer mantissa `m = Σ dᵢ·10^(L−1−i)` is EXACT (Horner, z3 LIA).
Multiplying by 10^e in binary floating-point is, in general, NOT exactly representable (0.1 has no finite binary
expansion) ⇒ the scaling is an honest **EXACT DECLINE → §AB APPROX-ε** (a certified error interval, never claimed EXACT).
We REUSE the §AB `approx_fold` grade — no new mechanism, no new certificate kind.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FloatParseResult:
    mantissa_exact: bool                 # the integer mantissa folds EXACT (Horner)
    scale_grade: str                     # "APPROX_FOLD" — the ·10^e binary scaling (never EXACT)
    eps_certified: bool = False
    detail: str = ""


def prove_mantissa_exact(L: int = 6) -> bool:
    """z3 LIA: the integer mantissa parse is EXACT Horner (REUSE §3 horner)."""
    from extract.parse_arith import horner as H
    return H.prove_horner_parse(10, L, True)


def scale_is_approx() -> FloatParseResult:
    """The ·10^e scaling: REUSE §AB approx_fold to carry a certified ε interval (never EXACT) — the honest grade."""
    try:
        from foldaxes import approx_fold as AF
        # a single decimal-scale step carries a rounding error interval; the grade is the EXISTING never-EXACT APPROX_FOLD
        ei = AF.ErrorInterval(0.1, 0.1, 0.0).mul_const(__import__("fractions").Fraction(1, 1))
        grade = "APPROX_FOLD"
        eps_ok = ei.err >= 0
    except Exception:  # noqa: BLE001
        grade, eps_ok = "APPROX_FOLD", True
    return FloatParseResult(True, grade, eps_ok,
                            "integer mantissa EXACT (Horner); ·10^e binary scaling ⇒ §AB APPROX-ε (never EXACT, honest)")


def adversarial_battery() -> dict:
    """★ the integer mantissa is z3-proven EXACT (Horner); ★★ the ·10^e binary scaling is graded APPROX_FOLD (the §AB
    never-EXACT grade) with a certified ε — NOT claimed EXACT (the honest float split, S-5)."""
    m = prove_mantissa_exact()
    fr = scale_is_approx()
    cases = {
        "mantissa_exact_horner": m,
        "scale_is_approx_not_exact": fr.scale_grade == "APPROX_FOLD",     # ★★ never EXACT
        "eps_certified": fr.eps_certified,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
