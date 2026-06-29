"""
§AY QFT-2 — Clifford / geometric-algebra normal form (self-impl; cadabra / sympy.physics.hep are FORBIDDEN).
================================================================================================================
The geometric algebra Cl(η) has e_i e_j + e_j e_i = 2η_ij, so every product reduces to a unique NORMAL FORM (a
signed sum of sorted basis blades e_S after contracting repeated indices via the metric). Equivalence of two
expressions is therefore DECIDABLE by comparing normal forms — exact integer/rational coefficients, no z3. The
Dirac algebra {γ^μ,γ^ν}=2η^{μν}I is the Minkowski-metric sub-case.

★ Zero-dep self-impl over stdlib (Fraction + tuples). ★ Axis A only (a decidable equivalence, not a speedup).
★ Out-of-scope (an index beyond the finite metric, i.e. an infinite-dimensional operator algebra / field-operator
product) ⇒ DECLINE (the finite-blade boundary is explicit).
"""
from __future__ import annotations

from fractions import Fraction
from typing import Dict, List, Sequence, Tuple

import kernel_verdict as KV

Blade = Tuple[int, ...]
MV = Dict[Blade, Fraction]


def _blade_mul(ai: Sequence[int], bi: Sequence[int], metric: Sequence[int]) -> Tuple[Fraction, Blade]:
    """Geometric product of two basis blades: reorder to sorted (sign from inversions of DISTINCT indices) then
    contract repeated indices e_i e_i = η_i. Returns (signed coeff, canonical blade)."""
    seq = list(ai) + list(bi)
    inv = sum(1 for i in range(len(seq)) for j in range(i + 1, len(seq)) if seq[i] > seq[j])
    coeff = Fraction((-1) ** inv)
    arr = sorted(seq)
    out: List[int] = []
    i = 0
    while i < len(arr):
        if i + 1 < len(arr) and arr[i] == arr[i + 1]:
            coeff *= metric[arr[i]]                                # e_i e_i = η_i
            i += 2
        else:
            out.append(arr[i])
            i += 1
    return coeff, tuple(out)


def mv_from_blades(blades: Sequence[Tuple[Sequence[int], object]], metric: Sequence[int]) -> MV:
    """Build a canonical multivector from (indices, coeff) terms (each canonicalised via the blade product)."""
    out: MV = {}
    for idxs, c in blades:
        coeff, blade = _blade_mul(idxs, (), metric)
        out[blade] = out.get(blade, Fraction(0)) + coeff * Fraction(c)
        if out[blade] == 0:
            del out[blade]
    return out


def geometric_product(mv1: MV, mv2: MV, metric: Sequence[int]) -> MV:
    out: MV = {}
    for b1, c1 in mv1.items():
        for b2, c2 in mv2.items():
            coeff, blade = _blade_mul(b1, b2, metric)
            out[blade] = out.get(blade, Fraction(0)) + c1 * c2 * coeff
            if out[blade] == 0:
                del out[blade]
    return out


def clifford_equiv(mv1: MV, mv2: MV) -> bool:
    keys = set(mv1) | set(mv2)
    return all(mv1.get(k, Fraction(0)) == mv2.get(k, Fraction(0)) for k in keys)


def ga_equiv_fold(blades1: Sequence[Tuple[Sequence[int], object]], blades2: Sequence[Tuple[Sequence[int], object]],
                  metric: Sequence[int]) -> KV.Verdict:
    """Decide GA-expression equivalence by normal form. EXACT (the decision is exact); DECLINE if any index is outside
    the finite metric (infinite-dimensional operator algebra — out of scope)."""
    dim = len(metric)
    for blades in (blades1, blades2):
        for idxs, _c in blades:
            if any((i < 0 or i >= dim) for i in idxs):
                return KV.decline(f"clifford: index outside finite metric (dim {dim}) ⇒ infinite-dimensional operator "
                                  f"algebra (field operators) ⇒ out of finite-blade scope ⇒ DECLINE", "clifford_ga")
    try:
        nf1 = mv_from_blades(blades1, metric)
        nf2 = mv_from_blades(blades2, metric)
    except (TypeError, ValueError) as e:
        return KV.decline(f"clifford: {e} ⇒ DECLINE", "clifford_ga")
    equal = clifford_equiv(nf1, nf2)
    cert = KV.Cert(KV.EXACT, "clifford_normal_form", passed=True, check_cost="canonical blade reduction (exact ℚ)",
                   detail=f"normal forms compared over Cl(η) (e_ie_j+e_je_i=2η_ij); {'equal' if equal else 'distinct'} "
                          f"by exact coefficient match")
    return KV.exact({"equal": equal, "nf1": {str(k): str(v) for k, v in nf1.items()},
                     "nf2": {str(k): str(v) for k, v in nf2.items()}}, "clifford_ga", "O(terms²) normal form", cert,
                    reason="Axis-A only: GA/Dirac equivalence decided by normal form (no speedup claim)")


def adversarial_battery() -> dict:
    """★ EXACT: e₀e₁ = −e₁e₀ (anticommute), e₀e₀ = η₀ (square), and a Dirac-metric square γ¹γ¹=η₁₁=−1; distinct
    expressions correctly reported NOT equal. ★★ DECLINE: an index beyond the finite metric (infinite-dim) ⇒ DECLINE."""
    eu = [1, 1, 1]                                                  # Euclidean metric, e0,e1,e2
    # e0 e1 vs -(e1 e0)
    e0e1 = geometric_product({(0,): Fraction(1)}, {(1,): Fraction(1)}, eu)
    e1e0 = geometric_product({(1,): Fraction(1)}, {(0,): Fraction(1)}, eu)
    anti = clifford_equiv(e0e1, {k: -v for k, v in e1e0.items()})
    # e0 e0 = η0 = 1 (scalar)
    sq = geometric_product({(0,): Fraction(1)}, {(0,): Fraction(1)}, eu)
    square_ok = sq == {(): Fraction(1)}
    # Dirac: metric (+,-,-,-); γ1 γ1 = η11 = -1
    mink = [1, -1, -1, -1]
    g1g1 = ga_equiv_fold([((1, 1), 1)], [((), -1)], mink)          # γ1γ1 == −1·I
    dirac_ok = g1g1.status == KV.EXACT and g1g1.result["equal"]
    # distinct expressions: e0e1 ≠ e1e0 (no minus) — correctly NOT equal
    distinct = ga_equiv_fold([((0, 1), 1)], [((1, 0), 1)], eu)
    distinct_ok = distinct.status == KV.EXACT and not distinct.result["equal"]
    # DECLINE: index 5 beyond metric dim 3
    oos = ga_equiv_fold([((5,), 1)], [((5,), 1)], eu)
    oos_declines = oos.status == KV.DECLINE
    cases = {"anticommute_exact": anti, "square_metric_exact": square_ok, "dirac_square_exact": dirac_ok,
             "distinct_detected": distinct_ok, "out_of_scope_declines": oos_declines}
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, x in cases.items() if not x]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
