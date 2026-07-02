"""
§AY QLA-4 — BCH commutator decision (exponential product → single exponential).
================================================================================================================
[A,B]=0 ⟺ eᴬeᴮ = e^{A+B} (Baker–Campbell–Hausdorff). A product of matrix exponentials e^{A_1}…e^{A_k} collapses to
e^{ΣA_i} EXACTLY iff all pairwise commutators vanish. The commutator test is exact rational linear algebra
(A_iA_j − A_jA_i = 0 entrywise) — no z3 induction; the equivalence is the BCH theorem.

★ Non-commuting ⇒ BCH has higher-order terms ⇒ EXACT collapse is FORBIDDEN (DECLINE; a Trotter splitting would be a
PROBABILISTIC approximation, never EXACT). Float matrices ⇒ DECLINE (no float-EXACT, §1-Q3).
"""
from __future__ import annotations

from typing import List, Sequence

import kernel_verdict as KV

from . import _la


def prove_commutativity(A, B) -> bool:
    """Exact ∀-entry test [A,B]=AB−BA=0 over ℚ (the directive's QF_LRA discharge, done by exact arithmetic)."""
    AB = _la.matmul(A, B)
    BA = _la.matmul(B, A)
    return all(AB[i][j] == BA[i][j] for i in range(len(A)) for j in range(len(A[0])))


def lie_product_fold(mats: Sequence[Sequence[Sequence]]) -> KV.Verdict:
    """Fold e^{A_1}…e^{A_k} → e^{ΣA_i} iff all pairwise commutators vanish. EXACT (commuting, integer/rational);
    non-commuting or float ⇒ DECLINE."""
    try:
        M = [_la.fmat(A) for A in mats]
    except _la.NonExact as e:
        return KV.decline(f"bch: {e} ⇒ DECLINE (no float-EXACT)", "bch_commutator")
    if not M:
        return KV.decline("bch: empty product", "bch_commutator")
    n = len(M[0])
    if any(len(A) != n or any(len(r) != n for r in A) for A in M):
        return KV.decline("bch: matrices must be square and same size", "bch_commutator")
    for i in range(len(M)):
        for j in range(i + 1, len(M)):
            if not prove_commutativity(M[i], M[j]):
                return KV.decline(f"bch: [A{i},A{j}]≠0 (non-commuting) ⇒ BCH has higher-order terms ⇒ EXACT collapse "
                                  f"FORBIDDEN ⇒ DECLINE (Trotter would be PROBABILISTIC, never EXACT)", "bch_commutator")
    summed = [[sum(M[t][i][j] for t in range(len(M))) for j in range(n)] for i in range(n)]
    cert = KV.Cert(KV.EXACT, "bch_commuting", passed=True, check_cost=f"O(k²·n³) pairwise [A_i,A_j]=0",
                   detail=f"all {len(M)} generators pairwise commute ([A_i,A_j]=0 entrywise) ⇒ e^{{A_1}}…e^{{A_k}}="
                          f"e^{{ΣA_i}} by BCH (the higher-order terms vanish)")
    return KV.exact({"k": len(M), "collapsed_to": "exp(sum A_i)", "sum_matrix": [[str(x) for x in r] for r in summed]},
                    "bch_commutator", "O(n³) single matrix-exp vs O(k·n³)", cert,
                    reason="Axis-A: exponential-product pattern recognized; Axis-B k matrix-exps → 1")


def adversarial_battery() -> dict:
    """★ EXACT: commuting generators (a matrix and its multiple; diagonal matrices) collapse to a single exp.
    ★★ DECLINE: non-commuting Paulis (X,Z) ⇒ DECLINE (no false-EXACT); float ⇒ DECLINE."""
    com = lie_product_fold([[[1, 0], [0, 2]], [[3, 0], [0, 5]]])               # diagonal ⇒ commute
    com_ok = com.status == KV.EXACT and com.result["k"] == 2
    com2 = lie_product_fold([[[0, 1], [1, 0]], [[0, 2], [2, 0]]])              # A and 2A ⇒ commute
    com2_ok = com2.status == KV.EXACT
    X = [[0, 1], [1, 0]]; Z = [[1, 0], [0, -1]]
    noncom = lie_product_fold([X, Z])                                          # XZ ≠ ZX ⇒ non-commuting
    noncom_declines = noncom.status == KV.DECLINE
    flt = lie_product_fold([[[1.0, 0.0], [0.0, 1.0]]])
    flt_declines = flt.status == KV.DECLINE
    cases = {"diagonal_commute_exact": com_ok, "scalar_multiple_commute_exact": com2_ok,
             "pauli_noncommute_declines": noncom_declines, "float_declines": flt_declines}
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, x in cases.items() if not x]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
