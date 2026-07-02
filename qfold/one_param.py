"""
§AY REL-1 — one-parameter subgroup fold (rotations / collinear boosts / rapidity addition).
================================================================================================================
A one-parameter subgroup M(t)=exp(tG) satisfies M(a)M(b)=M(a+b) and M(t)ᴺ=M(N·t). Collinear boosts add rapidity
Λ(φ₁)Λ(φ₂)=Λ(φ₁+φ₂); same-axis rotations R(θ)ᴺ=R(Nθ). Recognition: a repeated 2×2 isometry's power folds via its
Cayley–Hamilton recurrence (REUSE QLA-2: Mᴺ=tr(M)·M^{N-1}−det(M)·M^{N-2}, rational coefficients), and a product of
SAME-subgroup elements collapses by parameter addition (they commute — REUSE QLA-4).

★ Non-collinear boosts do NOT commute (Thomas–Wigner rotation appears) ⇒ no single subgroup ⇒ DECLINE. Rotations
about different axes ⇒ DECLINE. Float ⇒ DECLINE (no float-EXACT, §1-Q3).
"""
from __future__ import annotations

from typing import Sequence

import kernel_verdict as KV

from . import _la, bch, cayley_hamilton


def subgroup_power_fold(M: Sequence[Sequence]) -> KV.Verdict:
    """Mᴺ for a 2×2 (or n×n) one-parameter element via Cayley–Hamilton (REUSE QLA-2). EXACT (rational tr/det)."""
    v = cayley_hamilton.cayley_hamilton_fold(M)
    if v.status != KV.EXACT:
        return v
    cert = KV.Cert(KV.EXACT, "one_param_subgroup", passed=True, check_cost=v.certificate.check_cost,
                   detail="repeated isometry M(t)ᴺ=M(N·t); the entry sequence is C-finite via Cayley–Hamilton "
                          "(tr/det rational) " + v.certificate.detail)
    return KV.exact({"closed_form": "M^N via C-finite (CH) — parameter addition N·t", **v.result},
                    "one_param_subgroup", v.complexity, cert,
                    reason="Axis-A: one-parameter subgroup recognized; Axis-B O(N·n³)→O(n³·log N) closed form")


def collinear_compose(mats: Sequence[Sequence[Sequence]]) -> KV.Verdict:
    """Compose same-subgroup elements by parameter addition iff they pairwise COMMUTE (collinear). Non-commuting
    (non-collinear boosts ⇒ Thomas rotation) ⇒ DECLINE."""
    try:
        M = [_la.fmat(A) for A in mats]
    except _la.NonExact as e:
        return KV.decline(f"one_param: {e} ⇒ DECLINE (no float-EXACT)", "one_param_subgroup")
    if len(M) < 2:
        return KV.decline("one_param: need ≥2 transforms to compose", "one_param_subgroup")
    for i in range(len(M)):
        for j in range(i + 1, len(M)):
            if not bch.prove_commutativity(M[i], M[j]):
                return KV.decline("one_param: transforms do NOT commute (non-collinear boosts ⇒ Thomas–Wigner "
                                  "rotation / different rotation axes) ⇒ no single subgroup ⇒ DECLINE",
                                  "one_param_subgroup")
    n = len(M[0])
    prod = _la.eye(n)
    for A in M:
        prod = _la.matmul(prod, A)
    cert = KV.Cert(KV.EXACT, "one_param_subgroup", passed=True, check_cost="pairwise commute + product",
                   detail="collinear one-parameter elements commute ⇒ compose by parameter addition into a single "
                          "subgroup element (rapidity/angle adds)")
    return KV.exact({"composed": [[str(x) for x in r] for r in prod], "parameter_addition": True},
                    "one_param_subgroup", "O(n³) single compose", cert,
                    reason="Axis-A: collinear one-parameter composition recognized; Axis-B product folds to one element")


def adversarial_battery() -> dict:
    """★ EXACT: a 2×2 rotation/boost power folds (Cayley–Hamilton); two same-axis rotations compose (commute).
    ★★ DECLINE: a rotation and a boost do NOT commute (Thomas-rotation analog) ⇒ DECLINE; float ⇒ DECLINE."""
    from fractions import Fraction as F
    R1 = [[F(3, 5), F(-4, 5)], [F(4, 5), F(3, 5)]]                  # Pythagorean rotation (rational)
    R2 = [[F(5, 13), F(-12, 13)], [F(12, 13), F(5, 13)]]
    powr = subgroup_power_fold(R1)
    pow_ok = powr.status == KV.EXACT
    comp = collinear_compose([R1, R2])                              # same-axis rotations commute
    comp_ok = comp.status == KV.EXACT and comp.result["parameter_addition"]
    rot = [[0, -1], [1, 0]]; boost = [[2, 0], [0, 1]]              # rotation vs scaling/boost ⇒ don't commute
    noncol = collinear_compose([rot, boost])
    noncol_declines = noncol.status == KV.DECLINE
    flt = collinear_compose([[[1.0, 0.0], [0.0, 1.0]], [[1.0, 0.0], [0.0, 1.0]]])
    flt_declines = flt.status == KV.DECLINE
    cases = {"rotation_power_exact": pow_ok, "collinear_compose_exact": comp_ok,
             "noncollinear_declines": noncol_declines, "float_declines": flt_declines}
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, x in cases.items() if not x]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
