"""
§BM NEW-10 — Burnside/Pólya orbit count + Hilbert series (closed-form / structure-by-size m10; →Gröbner amplify).
================================================================================================================
  • Burnside (Axis A fold): #orbits = (1/|G|) Σ_g |Fix(g)| — a closed form, no orbit enumeration. ★ re-checked
    against an INDEPENDENT union-find orbit count (the certificate): the two must agree (Burnside's theorem) or
    the input is not a group ⇒ DECLINE.
  • Hilbert series: for the polynomial ring k[x₁..xₙ], dim of the degree-d piece = C(d+n−1, n−1), the coefficients
    of 1/(1−t)ⁿ — a closed-form module-dimension growth, re-checked against a direct monomial count.
★ certificate-or-DECLINE, exact integer arithmetic, zero-dep (stdlib).
"""
from __future__ import annotations

from math import comb
from typing import List, Sequence, Tuple

import kernel_verdict as KV


def _uf_orbits(group: Sequence[Sequence[int]], n: int) -> int:
    """Independent orbit count by union-find over the action of all group elements on {0..n-1}."""
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for g in group:
        for i in range(n):
            ri, rj = find(i), find(g[i])
            if ri != rj:
                parent[ri] = rj
    return len({find(i) for i in range(n)})


def burnside_orbits(group: Sequence[Sequence[int]], n: int) -> KV.Verdict:
    """EXACT orbit count via Burnside iff it matches the independent union-find count (re-checked certificate).
    `group` must be the FULL group (closed). A mismatch ⇒ not a group ⇒ DECLINE."""
    G = [tuple(g) for g in group]
    if not G:
        return KV.decline("burnside: empty group ⇒ DECLINE", "burnside")
    total_fixed = sum(sum(1 for i in range(n) if g[i] == i) for g in G)
    if total_fixed % len(G) != 0:
        return KV.decline("burnside: Σ|Fix(g)| not divisible by |G| ⇒ not a group ⇒ DECLINE", "burnside")
    orbits = total_fixed // len(G)
    uf = _uf_orbits(G, n)
    if orbits != uf:
        return KV.decline(f"burnside: closed-form {orbits} ≠ union-find {uf} ⇒ input not a group ⇒ DECLINE", "burnside")
    cert = KV.Cert(KV.EXACT, "burnside_uf_recheck", passed=True, check_cost="O(|G|·n)",
                   detail=f"#orbits=(1/|G|)Σ|Fix(g)|={orbits}, re-checked == union-find count {uf}")
    return KV.exact({"orbits": orbits}, "burnside", "O(|G|·n)", cert)


def hilbert_poly_ring(n_vars: int, upto: int) -> KV.Verdict:
    """EXACT Hilbert function of k[x₁..xₙ]: dim(degree d) = C(d+n−1, n−1), re-checked against a direct count of
    degree-d monomials (stars-and-bars). The closed form 1/(1−t)ⁿ."""
    coeffs = [comb(d + n_vars - 1, n_vars - 1) for d in range(upto + 1)]

    def _count_monomials(d, k):                          # direct: compositions of d into k non-neg parts
        if k == 1:
            return 1
        return sum(_count_monomials(d - i, k - 1) for i in range(d + 1))

    if any(coeffs[d] != _count_monomials(d, n_vars) for d in range(upto + 1)):
        return KV.decline("hilbert: closed form ≠ direct monomial count ⇒ DECLINE", "hilbert")
    cert = KV.Cert(KV.EXACT, "hilbert_recheck", passed=True, check_cost="O(upto·n)",
                   detail=f"dim(deg d)=C(d+{n_vars}−1,{n_vars}−1) re-checked vs direct count; series 1/(1−t)^{n_vars}")
    return KV.exact({"hilbert": coeffs}, "hilbert", "O(1) per coeff", cert)


def adversarial_battery() -> dict:
    """★ a cyclic group acting on a 2-coloured necklace gives the Burnside orbit count, re-checked by union-find;
    ★ a non-group set ⇒ DECLINE; ★ the Hilbert series of k[x,y] is 1,2,3,4,… (re-checked)."""
    # C₃ acting on 3 positions: e, (012), (021). Orbits of positions under rotation = 1.
    c3 = [(0, 1, 2), (1, 2, 0), (2, 0, 1)]
    orb = burnside_orbits(c3, 3)
    not_grp = burnside_orbits([(1, 0, 2)], 3)            # single transposition is not closed ⇒ DECLINE-ish
    hil = hilbert_poly_ring(2, 5)                        # k[x,y]: dims 1,2,3,4,5,6
    cases = {
        "c3_one_orbit": orb.status == "EXACT" and orb.result["orbits"] == 1,
        "non_group_DECLINE": not_grp.status == "DECLINE",
        "hilbert_k_x_y": hil.status == "EXACT" and hil.result["hilbert"] == [1, 2, 3, 4, 5, 6],
        "exact_carries_cert": orb.certificate is not None and orb.certificate.passed,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
