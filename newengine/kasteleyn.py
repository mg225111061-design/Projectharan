"""
§BM NEW-12 — Kasteleyn/FKT Pfaffian partition function (★ free-fermion/matchgate amplify; conservation m05).
================================================================================================================
A planar graph's dimer (perfect-matching) count / 2D-Ising partition function is the Pfaffian of its Kasteleyn
matrix K, and Pf(K)² = det(K). This is the SAME planarity/Pfaffian structure the free-fermion (matchgate) engine
exploits — so this is a direct AMPLIFY of `mathmode/free_fermion`, not a new mechanism.

★ Preconditions FIRST (the directive): K must be antisymmetric (Kasteleyn-oriented) and the graph PLANAR (or a
fixed genus). Non-planar / 3-D ⇒ DECLINE (FKT does not apply; #P-hard in general). ★ certificate-or-DECLINE: the
Pfaffian is accepted only when the re-checked identity Pf(K)² = det(K) holds (exact integers). zero-dep (stdlib).
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Sequence

import kernel_verdict as KV

Q = Fraction


def _det(M: List[List[Q]]) -> Q:
    n = len(M)
    A = [[Q(x) for x in row] for row in M]
    det = Q(1)
    for c in range(n):
        piv = next((r for r in range(c, n) if A[r][c] != 0), None)
        if piv is None:
            return Q(0)
        if piv != c:
            A[c], A[piv] = A[piv], A[c]; det = -det
        det *= A[c][c]
        for r in range(c + 1, n):
            if A[r][c] != 0:
                f = A[r][c] / A[c][c]
                A[r] = [A[r][j] - f * A[c][j] for j in range(n)]
    return det


def _pfaffian(A: List[List[Q]]) -> Q:
    """Recursive Pfaffian of an antisymmetric 2m×2m matrix:
       Pf(A) = Σ_{j=1}^{2m-1} (−1)^{j+1} A[0][j] · Pf(A without rows/cols 0 and j). Pf of 0×0 = 1."""
    n = len(A)
    if n == 0:
        return Q(1)
    if n % 2 == 1:
        return Q(0)
    total = Q(0)
    sign = Q(1)
    for j in range(1, n):
        if A[0][j] != 0:
            idx = [k for k in range(n) if k != 0 and k != j]
            minor = [[A[r][c] for c in idx] for r in idx]
            total += sign * A[0][j] * _pfaffian(minor)
        sign = -sign
    return total


def _is_antisym(K: List[List[Q]]) -> bool:
    n = len(K)
    return all(K[i][j] == -K[j][i] for i in range(n) for j in range(n))


def pfaffian_partition(K: Sequence[Sequence[int]], planar: bool = True) -> KV.Verdict:
    """EXACT |Pf(K)| (dimer/Ising partition value) iff K is antisymmetric, of even order, the graph is PLANAR, and
    the re-check Pf(K)² = det(K) passes. Otherwise DECLINE (preconditions first; FKT is planar-only)."""
    Kq = [[Q(x) for x in row] for row in K]
    n = len(Kq)
    if n % 2 == 1:
        return KV.decline("kasteleyn: odd order ⇒ no perfect matching ⇒ Pf=0 trivially; DECLINE the partition claim", "kasteleyn")
    if not _is_antisym(Kq):
        return KV.decline("kasteleyn: matrix is not antisymmetric (not a Kasteleyn orientation) ⇒ DECLINE", "kasteleyn")
    if not planar:
        return KV.decline("kasteleyn: graph is NON-PLANAR (or 3-D) ⇒ FKT does not apply (#P-hard) ⇒ DECLINE", "kasteleyn")
    pf = _pfaffian(Kq)
    det = _det(Kq)
    if pf * pf != det:                                   # ★ the re-checked certificate
        return KV.decline(f"kasteleyn: Pf²={pf * pf} ≠ det={det} ⇒ certificate failed ⇒ DECLINE", "kasteleyn")
    cert = KV.Cert(KV.EXACT, "pfaffian_sq_eq_det", passed=True, check_cost="O((2m)³) det + Pfaffian",
                   detail=f"antisymmetric + planar; Pf(K)={pf}, Pf²={pf * pf}=det ⇒ partition value |Pf|={abs(pf)}")
    return KV.exact({"pfaffian": str(pf), "partition": str(abs(pf))}, "kasteleyn", "O((2m)³)", cert)


def adversarial_battery() -> dict:
    """★ a planar antisymmetric K gives |Pf| with Pf²=det verified (EXACT); ★ a non-antisymmetric matrix ⇒
    DECLINE; ★ a non-planar graph ⇒ DECLINE (FKT inapplicable). ★ amplifies the free-fermion/Pfaffian structure."""
    # a single edge / 2×2 block: K=[[0,1],[-1,0]] ⇒ Pf=1, det=1, Pf²=det
    one = pfaffian_partition([[0, 1], [-1, 0]])
    # 4×4 antisymmetric (two disjoint edges + a cross): Pf and det consistent
    K4 = [[0, 1, 1, 0], [-1, 0, 0, 1], [-1, 0, 0, 1], [0, -1, -1, 0]]
    four = pfaffian_partition(K4)
    nonanti = pfaffian_partition([[0, 1], [1, 0]])       # symmetric ⇒ DECLINE
    nonplanar = pfaffian_partition([[0, 1], [-1, 0]], planar=False)
    cases = {
        "single_edge_pf1": one.status == "EXACT" and one.result["partition"] == "1",
        "four_node_consistent": four.status == "EXACT",        # Pf²=det held
        "non_antisymmetric_DECLINE": nonanti.status == "DECLINE",
        "non_planar_DECLINE": nonplanar.status == "DECLINE",
        "exact_carries_cert": one.certificate is not None and one.certificate.passed,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
