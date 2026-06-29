"""
§AL §1.7 — STRENGTH-REDUCTION INVERSE: restore the closed form a compiler's strength reduction hid as accumulation.
================================================================================================================
A multiplication compiled to repeated addition (`for k: t += c` ≡ c·n) or an exponentiation to repeated multiplication
(`for: x *= r` ≡ x₀·rⁿ) is the classic strength-reduction DISGUISE. The strip drives the accumulation form as a unary
oracle and lets §AI recover the closed form (linear / geometric); z3 disposes. ★ Honest overlap: a *source* with a
plain `s += c` loop is already foldable by the verified lifter — this module's added recall is the BLACK-BOX form
(accumulation behind a callable, where the source isn't available to the static lifter).
"""
from __future__ import annotations

from typing import Callable

from recall import core


def fold(fn: Callable[[int], object]) -> core.StripResult:
    """Drive the accumulation/iteration oracle through §AI: repeated-add ⇒ linear, repeated-mul ⇒ geometric. z3 gates."""
    return core.fold_via_ai(fn, "strength_reduction(inverse)")


def adversarial_battery() -> dict:
    """★ repeated-addition (t += 7, n times) folds as a linear closed form (= 7n, z3-gated); ★ repeated-multiplication
    (x *= 3) folds as geometric (= x₀·3ⁿ); ★ a data-dependent accumulation (adds str-digit of k) DECLINEs."""
    def repeated_add(n):
        t = 0
        for _ in range(n):
            t += 7
        return t

    def repeated_mul(n):
        x = 1
        for _ in range(n):
            x *= 3
        return x

    def data_dep(n):
        import hashlib
        t = 0
        for k in range(n):
            t += hashlib.sha256(str(k).encode()).digest()[0]   # genuinely random step (not strength-reducible)
        return t
    ra, rm, dd = fold(repeated_add), fold(repeated_mul), fold(data_dep)
    cases = {
        "repeated_add_folds_linear": ra.folded,
        "repeated_mul_folds_geometric": rm.folded,
        "data_dependent_declines": not dd.folded,                # ★ z3 gate holds (genuinely random step ⇒ DECLINE)
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
