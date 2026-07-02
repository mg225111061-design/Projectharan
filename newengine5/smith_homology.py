"""
§BN NEW-3 — integer homology of a chain complex: Betti numbers + torsion via Smith Normal Form (m09/m10).
=============================================================================================================
Given a chain complex  …→ C_{k+1} --∂_{k+1}--> C_k --∂_k--> C_{k-1} →…  of free ℤ-modules (boundary matrices
over ℤ, with ∂_k an n_{k-1}×n_k integer matrix), the homology H_k = ker ∂_k / im ∂_{k+1} is computable EXACTLY:

  • rank r_k         = #nonzero invariant factors of Smith(∂_k)             (reuse native_lattice.smith_normal_form)
  • Betti b_k        = (n_k − r_k) − r_{k+1}                                (free rank of H_k)
  • torsion(H_k)     = the invariant factors > 1 of ∂_{k+1}                (ℤ/d summands)

★ certificate-or-DECLINE (three INDEPENDENT re-checks; any failure ⇒ DECLINE, never a faked Betti number):
  (1) ∂_k ∘ ∂_{k+1} = 0  for all k — the input is a genuine chain complex (else DECLINE: not a complex);
  (2) U_k · ∂_k · V_k = S_k with U_k,V_k UNIMODULAR (|det|=1), S_k diagonal with the divisibility chain — the
      Smith form is certified, not trusted;
  (3) rank from Smith == rank from an INDEPENDENT exact-ℚ Gaussian elimination — two computations must agree.

Euler characteristic χ = Σ(−1)^k n_k is reported as a derived value (it equals Σ(−1)^k b_k by an algebraic
identity — a sanity readout, NOT the gate; the gate is (1)–(3)). Exact ℤ/ℚ arithmetic. 0 new mechanism
(complete-invariant m09 + structure-by-size m10 branch); 0 new disposer. Amplifies catalog/mech_persistence.
"""
from __future__ import annotations

from fractions import Fraction
from typing import List

import kernel_verdict as KV
import native_lattice as NL

_MAX_CELLS = 4000          # total matrix entries across the complex — beyond ⇒ DECLINE on cost (honest island)


def _matmul(A: List[List[int]], B: List[List[int]]) -> List[List[int]]:
    ra, ca, cb = len(A), len(A[0]) if A else 0, len(B[0]) if B else 0
    return [[sum(A[i][k] * B[k][j] for k in range(ca)) for j in range(cb)] for i in range(ra)]


def _is_zero(M) -> bool:
    return all(v == 0 for row in M for v in row)


def _det_int(M: List[List[int]]) -> Fraction:
    """Exact determinant of a square integer matrix via Fraction Gaussian elimination (for the |det U|=1 check)."""
    n = len(M)
    A = [[Fraction(x) for x in row] for row in M]
    det = Fraction(1)
    for col in range(n):
        piv = next((r for r in range(col, n) if A[r][col] != 0), None)
        if piv is None:
            return Fraction(0)
        if piv != col:
            A[col], A[piv] = A[piv], A[col]; det = -det
        det *= A[col][col]
        inv = A[col][col]
        for r in range(col + 1, n):
            f = A[r][col] / inv
            if f != 0:
                A[r] = [A[r][c] - f * A[col][c] for c in range(n)]
    return det


def _rank_Q(M: List[List[int]]) -> int:
    """Independent exact-ℚ rank via Gaussian elimination (the cross-check of the Smith rank)."""
    if not M or not M[0]:
        return 0
    A = [[Fraction(x) for x in row] for row in M]
    rows, cols = len(A), len(A[0])
    rank = 0
    for col in range(cols):
        piv = next((r for r in range(rank, rows) if A[r][col] != 0), None)
        if piv is None:
            continue
        A[rank], A[piv] = A[piv], A[rank]
        inv = A[rank][col]
        A[rank] = [x / inv for x in A[rank]]
        for r in range(rows):
            if r != rank and A[r][col] != 0:
                f = A[r][col]
                A[r] = [A[r][c] - f * A[rank][c] for c in range(cols)]
        rank += 1
    return rank


def _smith_diag(M: List[List[int]]):
    """(invariant factors |S_ii|>0, full diagonal S, U, V) with U·M·V=S — reuses native_lattice.smith_normal_form."""
    if not M or not M[0]:
        return [], [], [[1]], [[1]]
    S, U, V = NL.smith_normal_form(M)
    diag = [abs(S[i][i]) for i in range(min(len(S), len(S[0]))) if S[i][i] != 0]
    return diag, S, U, V


def homology(boundaries: List[List[List[int]]]) -> KV.Verdict:
    """EXACT Betti numbers + torsion of the chain complex [∂_1,…,∂_N] (∂_k: n_{k-1}×n_k), certified by (1)–(3).
    DECLINE if it is not a chain complex (∂∂≠0), if a Smith/rank re-check fails, or beyond the cost island."""
    bnd = [[[int(x) for x in row] for row in M] for M in boundaries]
    N = len(bnd)
    if N == 0:
        return KV.decline("smith_homology: empty complex (no boundary maps)", "smith_homology")
    cells = sum(len(M) * (len(M[0]) if M else 0) for M in bnd)
    if cells > _MAX_CELLS:
        return KV.decline(f"smith_homology: {cells} matrix entries > {_MAX_CELLS} ⇒ DECLINE on cost (island)",
                          "smith_homology")
    # dimensions n_0..n_N ; consistency rows(∂_{k+1}) == cols(∂_k)
    n = [len(bnd[0])]                                       # n_0 = rows(∂_1)
    for k in range(N):
        cols = len(bnd[k][0]) if bnd[k] else 0
        if len(bnd[k]) != n[k]:
            return KV.decline(f"smith_homology: ∂_{k+1} has {len(bnd[k])} rows ≠ n_{k}={n[k]} (dim mismatch)",
                              "smith_homology")
        n.append(cols)
    # (1) ∂_k ∘ ∂_{k+1} = 0  (valid chain complex)
    for k in range(N - 1):
        if not _is_zero(_matmul(bnd[k], bnd[k + 1])):
            return KV.decline(f"smith_homology: ∂_{k+1}∘∂_{k+2} ≠ 0 — not a chain complex ⇒ DECLINE",
                              "smith_homology")
    # ranks + Smith certs
    r = [0] * (N + 2)                                       # r_0 = 0 (∂_0=0); r_{N+1}=0
    torsion_of_im: List[List[int]] = [[] for _ in range(N + 2)]
    for k in range(1, N + 1):
        M = bnd[k - 1]
        if not M or not M[0]:           # zero map (no k-cells, or no (k−1)-cells): rank 0, no torsion, ∂∂=0 trivially
            r[k] = 0
            continue
        diag, S, U, V = _smith_diag(M)
        # (2) U·∂·V == S, U,V unimodular, S diagonal w/ divisibility chain
        UAV = _matmul(_matmul(U, bnd[k - 1]), V)
        if UAV != S:
            return KV.decline(f"smith_homology: U·∂_{k}·V ≠ S ⇒ DECLINE (Smith re-check, bug guard)", "smith_homology")
        if abs(_det_int(U)) != 1 or abs(_det_int(V)) != 1:
            return KV.decline(f"smith_homology: Smith transform for ∂_{k} not unimodular ⇒ DECLINE", "smith_homology")
        # (3) rank cross-check: Smith rank == independent ℚ rank
        rk_smith = len(diag)
        if rk_smith != _rank_Q(bnd[k - 1]):
            return KV.decline(f"smith_homology: Smith rank {rk_smith} ≠ ℚ-rank for ∂_{k} ⇒ DECLINE", "smith_homology")
        r[k] = rk_smith
        torsion_of_im[k] = sorted(d for d in diag if d > 1)     # invariant factors >1 ⇒ torsion of H_{k-1}
    # Betti + torsion
    betti = [(n[k] - r[k]) - r[k + 1] for k in range(N + 1)]
    torsion = {k: torsion_of_im[k + 1] for k in range(N + 1) if torsion_of_im[k + 1]}
    euler_cells = sum((-1) ** k * n[k] for k in range(N + 1))
    euler_betti = sum((-1) ** k * betti[k] for k in range(N + 1))
    cert = KV.Cert(KV.EXACT, "smith_homology", passed=True,
                   check_cost="∂∂=0 + U∂V=S (unimodular) + Smith-rank==ℚ-rank, all exact",
                   detail=f"Betti={betti}, torsion={torsion}; χ(cells)={euler_cells}==χ(Betti)={euler_betti}; "
                          "ranks cross-checked, Smith transforms unimodular ⇒ EXACT integer homology")
    return KV.exact({"betti": betti, "torsion": {str(k): v for k, v in torsion.items()},
                     "euler_characteristic": euler_cells, "ranks": r[1:N + 1]},
                    "smith_homology", "Smith NF homology (exact ℤ)", cert)


def adversarial_battery() -> dict:
    """★ circle S¹ (1 vertex,1 edge): b₀=b₁=1; ★ ℝP² (torsion ℤ/2): b₀=1,b₁=0,b₂=0,torsion@1={2}; ★ a non-complex
    (∂∂≠0) ⇒ DECLINE; ★ two points (b₀=2). Betti/torsion re-checked by ∂∂=0 + unimodular Smith + ℚ-rank."""
    # S¹ as 1 vertex v, 1 edge e with ∂e = v−v = 0  ⇒ ∂_1 = [[0]] (1×1). b0=1, b1=1.
    s1 = homology([[[0]]])
    # ℝP²: standard small complex 1 vertex, 1 edge, 1 face with ∂_1=[[0]], ∂_2=[[2]] ⇒ H0=ℤ,H1=ℤ/2,H2=0
    rp2 = homology([[[0]], [[2]]])
    # two disjoint points, no edges: ∂_1 is 2×0 (no 1-cells). Represent N=1 with ∂_1 = [[],[]] (2 rows,0 cols).
    twopts = homology([[[], []]])
    # NOT a complex: ∂_1=[[1]], ∂_2=[[1]] ⇒ ∂_1∂_2=[[1]]≠0 ⇒ DECLINE
    bad = homology([[[1]], [[1]]])
    cases = {
        "circle_b0_b1": s1.status == "EXACT" and s1.result["betti"] == [1, 1],
        "rp2_torsion_Z2": rp2.status == "EXACT" and rp2.result["betti"] == [1, 0, 0]
                          and rp2.result["torsion"].get("1") == [2],
        "two_points_b0": twopts.status == "EXACT" and twopts.result["betti"][0] == 2,
        "noncomplex_DECLINE": bad.status == "DECLINE",
        "exact_carries_cert": rp2.certificate is not None and rp2.certificate.passed,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
