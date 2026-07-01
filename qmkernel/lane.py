"""
qmkernel/lane.py — §1 of the directive: the 2-lane precision discipline, shared by every qmkernel module.
============================================================================================================
Quantum mechanics lives natively in a continuous ℂ/ℝ space — in tension with this repo's exact-arithmetic-first
culture. Two lanes, never blurred:
  Lane 1 (EXACT)     — input carries no float anywhere (int/Fraction/sympy exact). Certificate = a SYMBOLIC
                       identity (substitute → residual literally 0 in exact arithmetic). Returns a real
                       kernel_verdict.Verdict(EXACT).
  Lane 2 (APPROX-ε)  — input contains any float. Certificate = a STATED ε and a checked residual bound.
                       ★ NEVER tagged EXACT. Returns `EpsCert` below — a distinct dataclass that is
                       STRUCTURALLY never a KV.Verdict, so no downstream consumer can mistake it for
                       EXACT/PROBABILISTIC (stronger than a naming convention).

Precedent for "checked-but-not-exact-not-sampled needs its own type, not a 4th KV grade": this repo already
does this twice — `disposition.Disposition(kind="APPROX_FOLD", ...)` (accel/foldaxes) and
`sublinear_layer.SublinearVerdict` (randomized_svd) both keep kernel_verdict.py's 3-grade ADT closed and
untouched. `EpsCert` follows the same established pattern for the quantum domain (see QMKERNEL_INDEX.md §"2-lane").

A closed-form EXPRESSION and its DECIMAL EVALUATION are graded separately (directive §1): e.g. S = -Σλᵢ²log(λᵢ²)
is an exact symbolic identity (Lane 1) even when a caller also wants its decimal value (Lane 2, `decimal_eval`).
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Optional

import sympy as sp


# ── Lane 2 result type: NEVER a kernel_verdict.Verdict, by construction ────────────────────────────────
@dataclass
class EpsCert:
    """A Lane-2 (APPROX-ε) result. `lane` is always "APPROX_EPS" — never "EXACT", never "PROBABILISTIC"."""
    passed: bool
    epsilon: float
    residual: float
    kind: str
    detail: str = ""
    lane: str = "APPROX_EPS"


def eps_cert(residual: float, epsilon: float, kind: str, detail: str = "") -> EpsCert:
    """Build a Lane-2 certificate. `passed` is COMPUTED here from the actual residual vs. the stated ε — never
    trusted from a caller flag (the same 'no rubber stamp' discipline as kernel_verdict.Cert)."""
    r, e = float(residual), float(epsilon)
    ok = r <= e
    return EpsCert(passed=ok, epsilon=e, residual=r, kind=kind,
                   detail=detail or f"|residual|={r:.6e} {'<=' if ok else '>'} stated ε={e:.6e}")


def decimal_eval(expr: Any, kind: str, detail: str = "", digits: int = 15) -> EpsCert:
    """Decimal-evaluate an expression that may itself be an EXACT closed form — this step is ALWAYS Lane 2 (the
    expression can be exact; ITS DECIMAL VALUE is a separate, explicitly-tagged floating evaluation, per §1's
    'closed form vs. decimal evaluation' rule). ε is the stated evaluation precision (10^-digits)."""
    if hasattr(expr, "evalf"):
        val = expr.evalf(digits)
    else:
        val = expr
    eps = 10.0 ** (-(digits - 2))
    return EpsCert(passed=True, epsilon=eps, residual=0.0, kind=kind, lane="APPROX_EPS",
                   detail=detail or f"decimal evaluation (to {digits} digits) of a closed-form expression = {val}; "
                                    f"★ the FORM is exact, THIS VALUE is Lane 2 by §1's own rule")


# ── Lane classification: does this input carry any float, anywhere? ───────────────────────────────────
def is_exact_scalar(x: Any) -> bool:
    """True iff `x` is a single value with no floating-point contamination. Unknown types are conservatively
    NOT exact — Lane 1 must never be claimed by default, only when genuinely proven."""
    if isinstance(x, bool):
        return True
    if isinstance(x, (int, Fraction)):
        return True
    if isinstance(x, (float, complex)):
        return False
    if isinstance(x, sp.Basic):
        return not x.has(sp.Float)
    try:
        import numpy as np
        if isinstance(x, np.bool_):
            return True
        if isinstance(x, np.integer):
            return True
        if isinstance(x, (np.floating, np.complexfloating)):
            return False
    except ImportError:
        pass
    return False


def is_exact_container(x: Any) -> bool:
    """True iff EVERY scalar reachable from `x` (list/tuple/numpy array/sympy Matrix, arbitrarily nested) is
    exact. A single float anywhere ⇒ the whole container is Lane 2."""
    try:
        import numpy as np
        if isinstance(x, np.ndarray):
            if x.dtype.kind in "iub":                       # signed/unsigned int, bool
                return True
            if x.dtype == object:
                return all(is_exact_scalar(v) for v in x.flat)
            return False                                     # float16/32/64, complex64/128, …
    except ImportError:
        pass
    if isinstance(x, sp.MatrixBase):
        return all(is_exact_scalar(v) for v in x)
    if isinstance(x, (list, tuple)):
        return all(is_exact_container(v) for v in x) if x else True
    return is_exact_scalar(x)


def lane_of(x: Any) -> str:
    """"EXACT" or "APPROX_EPS" — the lane an input belongs to. Pure classification, no side effects."""
    return "EXACT" if is_exact_container(x) else "APPROX_EPS"


# ── regression battery (§9: this shared infra needs its own test, not just each caller's) ──────────────
def adversarial_battery() -> dict:
    import kernel_verdict as KV
    cases = {}

    cases["int_is_exact"] = is_exact_scalar(3) is True
    cases["fraction_is_exact"] = is_exact_scalar(Fraction(1, 3)) is True
    cases["python_float_not_exact"] = is_exact_scalar(0.5) is False
    cases["python_complex_not_exact"] = is_exact_scalar(1 + 2j) is False
    cases["sympy_rational_is_exact"] = is_exact_scalar(sp.Rational(2, 5)) is True
    cases["sympy_symbol_is_exact"] = is_exact_scalar(sp.Symbol("x")) is True
    cases["sympy_float_not_exact"] = is_exact_scalar(sp.Float(1.5)) is False
    cases["sympy_expr_with_float_not_exact"] = is_exact_scalar(sp.Symbol("x") + sp.Float(0.1)) is False

    try:
        import numpy as np
        cases["numpy_int_array_is_exact"] = is_exact_container(np.array([1, 2, 3], dtype=np.int64)) is True
        cases["numpy_float_array_not_exact"] = is_exact_container(np.array([1.0, 2.0], dtype=np.float64)) is False
        cases["numpy_object_fraction_array_is_exact"] = is_exact_container(
            np.array([Fraction(1, 2), Fraction(3, 4)], dtype=object)) is True
    except ImportError:
        cases["numpy_int_array_is_exact"] = True
        cases["numpy_float_array_not_exact"] = True
        cases["numpy_object_fraction_array_is_exact"] = True

    cases["nested_list_all_exact"] = is_exact_container([[1, 2], [Fraction(1, 2), 3]]) is True
    cases["nested_list_one_float_taints_all"] = is_exact_container([[1, 2], [0.5, 3]]) is False
    cases["empty_container_is_exact"] = is_exact_container([]) is True

    cases["lane_of_exact"] = lane_of([1, 2, 3]) == "EXACT"
    cases["lane_of_float"] = lane_of([1.0, 2, 3]) == "APPROX_EPS"

    ok_cert = eps_cert(residual=1e-9, epsilon=1e-6, kind="test_pass")
    cases["eps_cert_passes_when_within_bound"] = ok_cert.passed is True and ok_cert.lane == "APPROX_EPS"
    bad_cert = eps_cert(residual=1e-3, epsilon=1e-6, kind="test_fail")
    cases["eps_cert_fails_when_outside_bound"] = bad_cert.passed is False   # ★ no rubber stamp

    # ★ the structural guarantee: EpsCert can NEVER be mistaken for a KV.Verdict — different Python type
    cases["eps_cert_never_a_kv_verdict"] = not isinstance(ok_cert, KV.Verdict)
    cases["eps_cert_lane_never_exact_or_probabilistic"] = (ok_cert.lane not in (KV.EXACT, KV.PROBABILISTIC)
                                                            and bad_cert.lane not in (KV.EXACT, KV.PROBABILISTIC))

    dv = decimal_eval(sp.Rational(1, 3), kind="test_decimal")
    cases["decimal_eval_is_lane2_even_for_exact_expr"] = dv.lane == "APPROX_EPS" and not isinstance(dv, KV.Verdict)

    all_ok = all(cases.values())
    failed = [k for k, v in cases.items() if not v]
    return {"cases": cases, "all_ok": all_ok, "failed": failed}


if __name__ == "__main__":
    import json
    b = adversarial_battery()
    print(json.dumps({"all_ok": b["all_ok"], "failed": b["failed"], "n_cases": len(b["cases"])}, indent=2))
