"""
qmkernel/holonomic_specfun.py — §BR STAGE 3 NEW-8: closed-form special-function PDE family recognition.
============================================================================================================
QHO (Hermite) · hydrogen radial (confluent hypergeometric / Kummer) · tunneling (Airy) — all satisfy a
polynomial-coefficient linear ODE (holonomic/D-finite). This module is a HYBRID, exactly matching what
QMKERNEL_INDEX.md §4 found:
  • Hermite is ALREADY registered in `mathmode.special_holonomic.REGISTRY` — this is PURE LABEL-ROUTING (0 new
    logic) to that unmodified function, per the directive's own instruction for the recognized case.
  • Airy and confluent hypergeometric (Kummer) are registered NOWHERE (they appear only as NEGATIVE markers in
    kovacic.py/decision_integration.py's non-Liouvillian rejection lists — a different, opposite use). Their
    annihilators are genuinely net-new here, built with the SAME certificate methodology (coefficients +
    substitution check) as `special_holonomic.py` uses for its five families — but as a SEPARATE registry
    inside qmkernel, not an edit to that already-tested production file (0 diff, same protective posture as
    the Kasteleyn note in slater.py).
★ m10 structure-by-size recognition branch: recognizing that a NAMED function belongs to a SPECIFIC bounded
family of polynomial-coefficient ODEs is exactly "structure by (annihilator) size/shape." No 15th mechanism.
★ certificate: substitute the CANDIDATE annihilator into the CONCRETE special function and verify the residual
is EXACTLY 0 (sympy symbolic differentiation + simplify) — never merely cited as a textbook fact.
"""
from __future__ import annotations

from typing import Union

import sympy as sp

import kernel_verdict as KV
from qmkernel import lane as LN

_x = sp.Symbol("_qk_holonomic_x")


# ── Hermite: PURE ROUTING to the already-recognized mathmode.special_holonomic (0 new logic) ───────────
def hermite_holonomic(n: int) -> KV.Verdict:
    from mathmode import special_holonomic as SH
    return SH.register("hermite", n)


# ── Airy: genuinely net-new registration (not recognized anywhere in the repo as holonomic) ─────────────
def airy_holonomic(which: str = "Ai") -> KV.Verdict:
    """y″−xy=0 (Airy's equation). `which` ∈ {"Ai","Bi"} selects Ai(x) or Bi(x) as the concrete witness."""
    if which not in ("Ai", "Bi"):
        return KV.decline(f"unknown Airy branch {which!r}, expected Ai or Bi", "qmkernel.holonomic_specfun")
    coeffs = {2: sp.Integer(1), 1: sp.Integer(0), 0: -_x}
    fn = sp.airyai(_x) if which == "Ai" else sp.airybi(_x)
    residual = sp.simplify(sum(coeffs[i] * sp.diff(fn, _x, i) for i in coeffs if i > 0) + coeffs[0] * fn)
    if residual != 0:
        return KV.decline(f"Airy annihilator residual {residual} ≠ 0 ⇒ DECLINE", "qmkernel.holonomic_specfun")
    cert = KV.Cert(KV.EXACT, "airy_annihilator_substitution", passed=True,
                   check_cost="L(f)≡0 via sympy symbolic differentiation + simplify",
                   detail=f"y″−xy=0; L({which})≡0 verified by substitution (net-new — not in "
                          "mathmode.special_holonomic's registry, no repo file edited)")
    return KV.exact({"family": "airy", "which": which, "coeffs": coeffs, "fn": fn},
                    "qmkernel.holonomic_specfun", "O(1) symbolic", cert)


# ── confluent hypergeometric (Kummer): genuinely net-new registration ───────────────────────────────────
def confluent_hypergeometric_holonomic(a, b) -> KV.Verdict:
    """x·y″+(b−x)·y′−a·y=0 (Kummer's equation), witness M(a,b,x)=₁F₁(a;b;x) — the hydrogen-atom radial
    equation's governing ODE family."""
    a, b = sp.sympify(a), sp.sympify(b)
    coeffs = {2: _x, 1: (b - _x), 0: -a}
    fn = sp.hyper([a], [b], _x)
    try:
        residual = sp.simplify(sp.hyperexpand(sum(coeffs[i] * sp.diff(fn, _x, i) for i in (1, 2)) + coeffs[0] * fn))
    except Exception as e:  # noqa: BLE001 — a genuine symbolic failure declines, never crashes
        return KV.decline(f"could not verify Kummer annihilator symbolically: {type(e).__name__}: {e}",
                          "qmkernel.holonomic_specfun")
    if residual != 0:
        return KV.decline(f"Kummer annihilator residual {residual} ≠ 0 ⇒ DECLINE", "qmkernel.holonomic_specfun")
    cert = KV.Cert(KV.EXACT, "kummer_annihilator_substitution", passed=True,
                   check_cost="L(f)≡0 via sympy symbolic differentiation + hyperexpand + simplify",
                   detail=f"x·y″+({b}−x)·y′−{a}·y=0; L(₁F₁({a};{b};x))≡0 verified by substitution "
                          "(net-new — zero hits repo-wide before this module)")
    return KV.exact({"family": "confluent_hypergeometric", "a": a, "b": b, "coeffs": coeffs, "fn": fn},
                    "qmkernel.holonomic_specfun", "O(1) symbolic", cert)


# ── the top-level dispatcher (by family name) ───────────────────────────────────────────────────────────
def recognize(family: str, **kwargs) -> Union[KV.Verdict, LN.EpsCert]:
    if family == "hermite":
        return hermite_holonomic(kwargs.get("n", 0))
    if family == "airy":
        return airy_holonomic(kwargs.get("which", "Ai"))
    if family == "confluent_hypergeometric":
        return confluent_hypergeometric_holonomic(kwargs.get("a"), kwargs.get("b"))
    return KV.decline(f"unrecognized special-function family {family!r}", "qmkernel.holonomic_specfun")


# ── adversarial battery ─────────────────────────────────────────────────────────────────────────────────
def adversarial_battery() -> dict:
    cases = {}

    # Hermite: routing works, and genuinely reaches the EXISTING mathmode.special_holonomic (not a duplicate)
    v1 = hermite_holonomic(4)
    cases["hermite_routing_exact"] = v1.status == KV.EXACT
    cases["hermite_routing_matches_dispatcher"] = recognize("hermite", n=4).status == KV.EXACT
    import mathmode.special_holonomic as SH
    v1_direct = SH.register("hermite", 4)
    cases["hermite_routing_result_matches_direct_call"] = (v1.status == v1_direct.status and
                                                            sp.simplify(v1.result["fn"] - v1_direct.result["fn"]) == 0)

    # Airy: net-new, both branches
    v2 = airy_holonomic("Ai")
    cases["airy_ai_exact"] = v2.status == KV.EXACT
    v3 = airy_holonomic("Bi")
    cases["airy_bi_exact"] = v3.status == KV.EXACT
    v4 = airy_holonomic("Ci")   # not a real branch
    cases["airy_unknown_branch_declines"] = v4.status == KV.DECLINE

    # confluent hypergeometric: net-new, a couple of (a,b) pairs including the hydrogen-radial-relevant shape
    v5 = confluent_hypergeometric_holonomic(sp.Rational(1, 2), sp.Rational(3, 2))
    cases["kummer_half_exact"] = v5.status == KV.EXACT
    v6 = confluent_hypergeometric_holonomic(-2, 1)   # a negative integer -> M(a,b,x) is a POLYNOMIAL (Laguerre-related)
    cases["kummer_negative_integer_a_exact"] = v6.status == KV.EXACT

    # a WRONG annihilator must be caught (adversarial: same coeffs pattern but wrong sign) -- direct residual check
    wrong_coeffs = {2: _x, 1: (sp.Rational(3, 2) - _x), 0: sp.Rational(1, 2)}   # sign flipped on the 'a' term
    fn_check = sp.hyper([sp.Rational(1, 2)], [sp.Rational(3, 2)], _x)
    wrong_residual = sp.simplify(sp.hyperexpand(sum(wrong_coeffs[i] * sp.diff(fn_check, _x, i) for i in (1, 2)) +
                                                wrong_coeffs[0] * fn_check))
    cases["wrong_annihilator_correctly_nonzero"] = wrong_residual != 0   # confirms the certificate is a REAL check

    # dispatcher: unrecognized family declines
    v7 = recognize("bessel_j_prime_variant")
    cases["unrecognized_family_declines"] = v7.status == KV.DECLINE

    all_ok = all(cases.values())
    failed = [k for k, v_ in cases.items() if not v_]
    return {"cases": cases, "all_ok": all_ok, "failed": failed}


if __name__ == "__main__":
    import json
    b = adversarial_battery()
    print(json.dumps({"all_ok": b["all_ok"], "failed": b["failed"], "n_cases": len(b["cases"])}, indent=2))
