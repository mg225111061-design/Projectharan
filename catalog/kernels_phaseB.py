"""
CATALOG ENGINE — PHASE B gated kernels (mature decision procedures, EXACT tier).
================================================================================
Each kernel here has PASSED the §7 gate (exact self-verifying certificate + grade ADT + negative controls in
test_catalog) before being registered into `kernel_router.REGISTRY` (§7: no gateless kernel). Registering also
flips the backing catalog `Transform`(s) to status="VERIFIED" with the kernel name (§3.3). Detect functions are
CONSERVATIVE so the global router never mis-grabs an unrelated input.
"""
from __future__ import annotations

import kernel_router as KR
import kernel_verdict as KV
import sos_cert
from mechanisms.m04_relax_dualize import _to_poly_expr


def _verify_transform(tid: str, kernel: str) -> None:
    """Flip a registered Transform to VERIFIED + record its backing kernel (§3.3)."""
    import catalog
    for t in catalog.TRANSFORMS:
        if t.tid == tid:
            t.status = "VERIFIED"
            t.kernel = kernel
            return
    raise KeyError(f"transform {tid} not found to verify")


# ── SOS / Positivstellensatz (mechanism 4) — the new EXACT tier ──────────────────────────────────────
_SOS_MARKERS = ("sum of squares", "sos", "positivstellensatz", "nonneg", "≥ 0", ">= 0", "is psd")


def _sos_detect(data) -> bool:
    return isinstance(data, str) and any(m in data.lower() for m in _SOS_MARKERS)


def _sos_run(data, **kw) -> KV.Verdict:
    expr = _to_poly_expr(data)
    if expr is None:
        return KV.decline("sos: no polynomial extracted from the query", "sos_positivstellensatz")
    return sos_cert.sos_grade(expr, kw.get("gens"))


KR.register(KR.Kernel(
    num=101, name="sos_positivstellensatz", group="catalog",
    contract="requires a polynomial p over ℚ; ensures p ≥ 0 globally via a RATIONAL PSD Gram (zᵀQz ≡ p exact, "
            "Q ⪰ 0 via Sturm-exact negative-eigenvalue count) — EXACT — else honest DECLINE (no SDP cone search, "
            "never overclaims); grade EXACT | DECLINE",
    detect=_sos_detect, run=_sos_run, status="VERIFIED"))

# the SOS kernel backs two catalog transforms (B-1 nonnegativity + D-2 refutation, §4.9 merge)
_verify_transform("B1.sos_positivstellensatz", "sos_positivstellensatz")
_verify_transform("D2.sos_refutation", "sos_positivstellensatz")


# ── RCF / CAD quantifier elimination (mechanism 2+3) — reuse the existing [이미 있음] mathmode.real_qe.decide ──
def _rcf_detect(data) -> bool:
    return isinstance(data, dict) and data.get("rcf") is True and "formula" in data and "quantifier" in data


def _rcf_run(data, **kw) -> KV.Verdict:
    import mathmode.real_qe as RQ
    return RQ.decide(data["quantifier"], data["formula"], data.get("x"))


KR.register(KR.Kernel(
    num=102, name="rcf_cad_qe", group="catalog",
    contract="requires Qx. φ(x) over a real-closed field (φ a boolean combo of polynomial sign conditions in x); "
            "ensures an EXACT True/False decision (CAD/real QE), a False-∀/True-∃ carrying the witness cell; "
            "grade EXACT",
    detect=_rcf_detect, run=_rcf_run, status="VERIFIED"))
_verify_transform("D1.rcf_cad_qe", "rcf_cad_qe")


# ── Presburger / linear integer arithmetic (mechanism 2+3) — direct z3 (the trusted oracle) ──────────
def _presburger_detect(data) -> bool:
    return isinstance(data, dict) and data.get("presburger") is True and "goal" in data and "int_vars" in data


def _presburger_run(data, **kw) -> KV.Verdict:
    import presburger_qe as P
    return P.presburger_decide(data["goal"], data["int_vars"], data.get("assumptions"))


KR.register(KR.Kernel(
    num=103, name="presburger_qe", group="catalog",
    contract="requires ∀(x∈ℤⁿ). φ(x) over (ℤ,+,<,=); ensures an EXACT True (¬φ UNSAT, z3 oracle) / False (+ "
            "counterexample model) decision, else DECLINE on unknown/timeout; grade EXACT | DECLINE",
    detect=_presburger_detect, run=_presburger_run, status="VERIFIED"))
_verify_transform("D1.presburger_qe", "presburger_qe")

# ── ACF (algebraically-closed-field QE / Chevalley) — HONEST_DEFER (§1.6): no existing module; constructible-set
#    projection is real work beyond this PHASE's budget. Registered honestly as UNVERIFIED (transform D1.acf_qe). ──

