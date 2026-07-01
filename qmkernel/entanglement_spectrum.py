"""
qmkernel/entanglement_spectrum.py — §BR STAGE 2 NEW-5: Schmidt decomposition = SVD.
============================================================================================================
A bipartite pure state |ψ⟩=Σ_ij C_ij|i⟩_A|j⟩_B has Schmidt decomposition |ψ⟩=Σ_k σ_k|u_k⟩_A|v_k⟩_B where
C=UΣV† is the SVD of the coefficient matrix and σ_k are the Schmidt coefficients (λ_k=σ_k² are the reduced
density matrix's eigenvalues — the entanglement spectrum).

★ Confirmed net-new (QMKERNEL_INDEX.md §6): `randomized_svd.py` is float-only (numpy), no exact/rational path,
and is designed for LARGE matrices where a full SVD is too expensive — not the regime this engine targets
(bipartition dimensions here are the kind a direct, deterministic linear-algebra approach handles cleanly).
`randomized_svd.py` itself is NOT touched (0 diff); its already-existing `approximate()` remains available,
unconnected, as a separate tool for genuinely large matrices — forcing a link here would be an artificial
composition with no benefit (the same judgment call as the Kasteleyn note in slater.py).

★ m11 hidden-state-space-recovery recognition branch: the Schmidt basis IS the hidden low-rank state-space of
the bipartite coefficient matrix — recovering it via SVD is exactly this mechanism's shape. No 15th mechanism.

★ certificate: reconstruction UΣV†=C (exact algebra, Lane 1) or residual ‖UΣV†−C‖≤ε (Lane 2), PLUS column
orthonormality of U and V, checked directly — never assumed from the algorithm's own correctness.
★ 2-lane: exact/symbolic C ⇒ Lane 1 (exact SVD via eigendecomposition of C†C, sympy exact arithmetic — a
NEW exact small-matrix path, since none existed). Float C ⇒ Lane 2 (numpy.linalg.svd, deterministic full SVD;
never routed through a RANDOMIZED algorithm for a bipartition-sized problem — see note above).
"""
from __future__ import annotations

from typing import List, Sequence, Tuple, Union

import sympy as sp

import kernel_verdict as KV
from qmkernel import lane as LN


def _as_matrix(C) -> sp.Matrix:
    return C if isinstance(C, sp.MatrixBase) else sp.Matrix(C)


def _rows(C) -> List[List]:
    M = _as_matrix(C) if not isinstance(C, (list, tuple)) else None
    if M is not None:
        return [[M[i, j] for j in range(M.cols)] for i in range(M.rows)]
    return [list(r) for r in C]


def _is_normalized_exact(rows: List[List]) -> Tuple[bool, object]:
    total = sum(sp.conjugate(x) * x for row in rows for x in row)
    total = sp.simplify(total)
    return sp.simplify(total - 1) == 0, total


def _is_normalized_eps(rows: List[List], tol: float) -> Tuple[bool, float]:
    total = sum(abs(complex(x)) ** 2 for row in rows for x in row)
    return abs(total - 1.0) <= tol, total


# ── exact small-matrix SVD (net-new — no such path exists anywhere in the repo) ─────────────────────────
def exact_svd(C: sp.Matrix) -> Tuple[sp.Matrix, List[sp.Expr], sp.Matrix]:
    """Exact (thin) SVD via eigendecomposition of the Gram matrix C†C — sympy exact arithmetic throughout.
    Returns (U, singular_values, V) with U (d_A×r), V (d_B×r), r=rank (zero singular values dropped: a valid
    THIN/compact SVD that still reconstructs C exactly, since the dropped directions contribute nothing)."""
    G = sp.conjugate(C.T) * C                             # d_B × d_B, Hermitian PSD
    eig_data = G.eigenvects()                              # [(eigenvalue, multiplicity, [eigenvectors]), ...]
    groups = []
    for val, _mult, vecs in eig_data:
        val = sp.nsimplify(sp.simplify(val))
        ortho = sp.GramSchmidt(list(vecs), orthonormal=True)   # ★ guarantees true orthonormality WITHIN the eigenspace
        for v in ortho:
            groups.append((val, v))
    groups.sort(key=lambda p: sp.N(p[0]), reverse=True)     # descending singular value order (numeric compare only for ORDER)

    v_cols, s_vals, u_cols = [], [], []
    for val, v in groups:
        if sp.simplify(val) == 0:
            continue                                        # thin SVD: drop the zero-singular-value directions
        sigma = sp.sqrt(val)
        u = (C * v) / sigma
        u = sp.simplify(u)
        v_cols.append(v)
        s_vals.append(sp.simplify(sigma))
        u_cols.append(u)
    if not v_cols:
        return sp.zeros(C.rows, 0), [], sp.zeros(C.cols, 0)
    U = sp.Matrix.hstack(*u_cols)
    V = sp.Matrix.hstack(*v_cols)
    return U, s_vals, V


def _reconstruction_residual_exact(C: sp.Matrix, U: sp.Matrix, S: List[sp.Expr], V: sp.Matrix) -> sp.Expr:
    Sigma = sp.diag(*S) if S else sp.zeros(0, 0)
    recon = U * Sigma * sp.conjugate(V.T) if S else sp.zeros(C.rows, C.cols)
    return sp.simplify(recon - C)


def _is_col_orthonormal_exact(M: sp.Matrix) -> bool:
    if M.cols == 0:
        return True
    G = sp.simplify(sp.conjugate(M.T) * M)
    I = sp.eye(M.cols)
    return sp.simplify(G - I) == sp.zeros(M.cols, M.cols)


# ── the top-level entry point ───────────────────────────────────────────────────────────────────────────
def schmidt_verdict(coeff_matrix, norm_tol: float = 1e-9) -> Union[KV.Verdict, LN.EpsCert]:
    """coeff_matrix: the d_A×d_B bipartite coefficient matrix C_ij of |ψ⟩=Σ C_ij|i⟩|j⟩. Precondition: |ψ⟩ is
    normalized (Σ|C_ij|²=1) — DECLINE otherwise. Returns KV.Verdict (Lane 1) or LN.EpsCert (Lane 2)."""
    rows = _rows(coeff_matrix)
    exact_lane = LN.is_exact_container(rows)

    if exact_lane:
        ok, total = _is_normalized_exact(rows)
        if not ok:
            return KV.decline(f"normalization precondition FAILED: Σ|C|²={total} ≠ 1 ⇒ DECLINE",
                              "qmkernel.entanglement_spectrum")
        C = sp.Matrix(rows)
        try:
            U, S, V = exact_svd(C)
        except Exception as e:  # noqa: BLE001 — a genuine algebraic failure declines, never crashes the caller
            return KV.decline(f"exact SVD failed: {type(e).__name__}: {e}", "qmkernel.entanglement_spectrum")
        resid = _reconstruction_residual_exact(C, U, S, V)
        recon_ok = resid == sp.zeros(C.rows, C.cols)
        u_ortho = _is_col_orthonormal_exact(U)
        v_ortho = _is_col_orthonormal_exact(V)
        if not (recon_ok and u_ortho and v_ortho):
            return KV.decline(f"SVD certificate FAILED: reconstruction_ok={recon_ok}, U_orthonormal={u_ortho}, "
                              f"V_orthonormal={v_ortho}", "qmkernel.entanglement_spectrum")
        schmidt_probs = [sp.simplify(s * s) for s in S]
        cert = KV.Cert(KV.EXACT, "schmidt_svd_reconstruction", passed=True,
                       check_cost=f"eigendecomposition of C†C (rank {len(S)}) + reconstruction + orthonormality",
                       detail=f"UΣV†=C exact; U,V column-orthonormal; Schmidt coefficients (σ)={S}; "
                              f"Schmidt probabilities (σ²)={schmidt_probs}")
        return KV.exact({"schmidt_values": S, "schmidt_probabilities": schmidt_probs, "rank": len(S),
                         "U": U, "V": V}, "qmkernel.entanglement_spectrum", "O(d^3) exact eigendecomposition", cert)

    # Lane 2 — float coefficient matrix: a full DETERMINISTIC numpy SVD (never randomized — see module docstring)
    ok, total = _is_normalized_eps(rows, norm_tol)
    if not ok:
        return KV.decline(f"normalization precondition FAILED (Lane 2): Σ|C|²={total:.6f} ≠ 1", "qmkernel.entanglement_spectrum")
    import numpy as np
    C = np.array(rows, dtype=complex)
    U, s, Vh = np.linalg.svd(C, full_matrices=False)
    recon = U @ np.diag(s) @ Vh
    resid = float(np.max(np.abs(recon - C))) if C.size else 0.0
    u_orth = float(np.max(np.abs(U.conj().T @ U - np.eye(U.shape[1])))) if U.shape[1] else 0.0
    v_orth = float(np.max(np.abs(Vh @ Vh.conj().T - np.eye(Vh.shape[0])))) if Vh.shape[0] else 0.0
    worst = max(resid, u_orth, v_orth)
    return LN.eps_cert(residual=worst, epsilon=max(norm_tol, 1e-6), kind="schmidt_lane2_svd_reconstruction",
                       detail=f"reconstruction resid={resid:.3e}, U-orthonormality resid={u_orth:.3e}, "
                              f"V-orthonormality resid={v_orth:.3e}; Schmidt probabilities={list(s**2)}")


# ── adversarial battery ─────────────────────────────────────────────────────────────────────────────────
def adversarial_battery() -> dict:
    cases = {}

    # 1) a maximally-entangled 2x2 Bell-like state: C = [[1/sqrt2,0],[0,1/sqrt2]] -- two equal Schmidt coeffs
    s = sp.Rational(1, 1) / sp.sqrt(2)
    C1 = [[s, 0], [0, s]]
    v1 = schmidt_verdict(C1)
    cases["bell_state_exact_grade"] = v1.status == KV.EXACT
    cases["bell_state_rank_2"] = v1.status == KV.EXACT and v1.result["rank"] == 2
    cases["bell_state_equal_schmidt_probs"] = (v1.status == KV.EXACT and
                                               all(sp.simplify(p - sp.Rational(1, 2)) == 0 for p in v1.result["schmidt_probabilities"]))

    # 2) a PRODUCT state (rank 1): C = [[1,0],[0,0]] -- zero entanglement, only one nonzero Schmidt coefficient
    C2 = [[1, 0], [0, 0]]
    v2 = schmidt_verdict(C2)
    cases["product_state_exact_grade"] = v2.status == KV.EXACT
    cases["product_state_rank_1"] = v2.status == KV.EXACT and v2.result["rank"] == 1

    # 3) an UN-normalized state -> DECLINE
    C3 = [[1, 0], [0, 1]]     # Σ|C|²=2 ≠ 1
    v3 = schmidt_verdict(C3)
    cases["unnormalized_declines"] = v3.status == KV.DECLINE

    # 4) a rational, PARTIALLY-entangled 2x2 state with unequal Schmidt weights (3-4-5 shape)
    C4 = [[sp.Rational(3, 5), 0], [0, sp.Rational(4, 5)]]
    v4 = schmidt_verdict(C4)
    cases["partial_entanglement_exact_grade"] = v4.status == KV.EXACT
    probs4 = sorted(v4.result["schmidt_probabilities"]) if v4.status == KV.EXACT else []
    cases["partial_entanglement_correct_probs"] = (v4.status == KV.EXACT and
                                                    probs4 == [sp.Rational(9, 25), sp.Rational(16, 25)])

    # 5) a NON-diagonal 2x2 exact case (genuine off-diagonal mixing, tests eigenvects()+GramSchmidt path)
    C5 = sp.Matrix([[sp.Rational(1, 2), sp.Rational(1, 2)], [sp.Rational(1, 2), sp.Rational(-1, 2)]])  # already orthogonal rows/cols, Σ|C|²=1
    v5 = schmidt_verdict(C5)
    cases["nondiagonal_exact_grade"] = v5.status == KV.EXACT
    cases["nondiagonal_reconstructs"] = v5.status == KV.EXACT   # reconstruction is asserted INSIDE schmidt_verdict already

    # 6) a 3x2 rectangular exact case (d_A != d_B)
    C6 = [[sp.Rational(1, 2), 0], [0, sp.Rational(1, 2)], [0, sp.sqrt(2) / 2]]
    v6 = schmidt_verdict(C6)
    cases["rectangular_case_handled"] = v6.status in (KV.EXACT, KV.DECLINE)   # must not crash either way
    if v6.status == KV.EXACT:
        cases["rectangular_case_exact_and_normalized_check"] = True
    else:
        cases["rectangular_case_exact_and_normalized_check"] = "normalization" in v6.reason

    # 7) Lane 2: float normalized bipartite state
    import numpy as np
    v = 1.0 / (2 ** 0.5)
    Cf = np.array([[v, 0.0], [0.0, v]])
    vf = schmidt_verdict(Cf)
    cases["float_bell_is_eps_cert_not_kv_verdict"] = isinstance(vf, LN.EpsCert) and not isinstance(vf, KV.Verdict)
    cases["float_bell_never_exact_tag"] = getattr(vf, "lane", None) == "APPROX_EPS"
    cases["float_bell_passes"] = isinstance(vf, LN.EpsCert) and vf.passed

    # 8) Lane 2: un-normalized float -> DECLINE
    Cf_bad = np.array([[1.0, 0.0], [0.0, 1.0]])
    vf2 = schmidt_verdict(Cf_bad)
    cases["float_unnormalized_declines"] = isinstance(vf2, KV.Verdict) and vf2.status == KV.DECLINE

    all_ok = all(cases.values())
    failed = [k for k, v_ in cases.items() if not v_]
    return {"cases": cases, "all_ok": all_ok, "failed": failed}


if __name__ == "__main__":
    import json
    b = adversarial_battery()
    print(json.dumps({"all_ok": b["all_ok"], "failed": b["failed"], "n_cases": len(b["cases"])}, indent=2))
