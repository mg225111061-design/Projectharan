"""
qmkernel/state_validity.py — §BR STAGE 3 NEW-9: quantum-object validity bundle, ONE shape-dispatched engine.
============================================================================================================
Density matrix (trace=1, PSD) · unitary (U†U=I) · projection/POVM (idempotent for a single operator,
completeness for a list) · Kraus (completeness) — FOUR validity notions, NOT four files: `check(obj, kind)`
dispatches by the DECLARED kind, and within "projection_povm" ALSO by the OBJECT'S OWN SHAPE (a single matrix
⇒ idempotency of one projection; a list ⇒ POVM-style positivity + completeness of the whole set).

★ PSD certification (density matrices, POVM elements) is cross-checked via TWO independent sympy code paths:
`Matrix.is_positive_semidefinite` (an internal decomposition-based decision) vs. direct eigenvalue-sign
inspection via `Matrix.eigenvals()` (root-finding) — disagreement between them is a DECLINE, never a coin
flip toward the more convenient answer.
★ m03 guess-and-certify recognition branch: propose "valid" from the structural check, certify it via the
independent second route — no 15th mechanism.
★ 2-lane forced (§1, explicit in this NEW item's brief): exact/symbolic input ⇒ Lane 1 (KV.Verdict, EXACT or
DECLINE). ANY float anywhere ⇒ Lane 2 (qmkernel.lane.EpsCert) — never EXACT, no exceptions.
"""
from __future__ import annotations

from typing import List, Sequence, Union

import sympy as sp

import kernel_verdict as KV
from qmkernel import lane as LN

_KINDS = {"density_matrix", "unitary", "projection_povm", "kraus"}


def _as_matrix(x) -> sp.Matrix:
    return x if isinstance(x, sp.MatrixBase) else sp.Matrix(x)


def _rows_of(x) -> List[List]:
    M = _as_matrix(x)
    return [[M[i, j] for j in range(M.cols)] for i in range(M.rows)]


def _flatten_rows(obj) -> List[List]:
    if isinstance(obj, (list, tuple)) and obj and isinstance(obj[0], (list, tuple)) and \
       obj and isinstance(obj[0][0], (list, tuple)):
        out = []
        for m in obj:
            out += _rows_of(m)
        return out
    if isinstance(obj, (list, tuple)) and obj and isinstance(obj[0], sp.MatrixBase):
        out = []
        for m in obj:
            out += _rows_of(m)
        return out
    return _rows_of(obj)


# ── PSD, cross-checked via two independent sympy routes ────────────────────────────────────────────────
def _is_psd_exact_crosschecked(H: sp.Matrix):
    primary = H.is_positive_semidefinite
    if primary is None:
        return None, False, "sympy's is_positive_semidefinite was indeterminate"
    eigvals = list(H.eigenvals().keys())
    signs = []
    for ev in eigvals:
        ev_s = sp.simplify(ev)
        nn = ev_s.is_nonnegative
        if nn is None:
            nn = sp.N(ev_s, 50) >= sp.Float("-1e-40")
        signs.append(bool(nn))
    independent = all(signs)
    return primary, (primary == independent), f"is_positive_semidefinite={primary}; independent eigenvalue-sign={independent}; eigenvalues={eigvals}"


# ── the four validity notions, exact lane ───────────────────────────────────────────────────────────────
def _check_density_matrix_exact(rho: sp.Matrix) -> KV.Verdict:
    n = rho.rows
    if rho.rows != rho.cols:
        return KV.decline("density matrix must be square", "qmkernel.state_validity")
    tr = sp.simplify(sp.trace(rho))
    if sp.simplify(tr - 1) != 0:
        return KV.decline(f"trace(ρ)={tr} ≠ 1", "qmkernel.state_validity")
    if sp.simplify(rho - rho.conjugate().T) != sp.zeros(n, n):
        return KV.decline("ρ is not Hermitian", "qmkernel.state_validity")
    psd, agree, detail = _is_psd_exact_crosschecked(rho)
    if not agree:
        return KV.decline(f"PSD cross-check DISAGREEMENT: {detail}", "qmkernel.state_validity")
    if not psd:
        return KV.decline(f"ρ is not PSD: {detail}", "qmkernel.state_validity")
    cert = KV.Cert(KV.EXACT, "density_matrix_trace_psd_crosschecked", passed=True,
                   check_cost="trace + Hermiticity + PSD (2 independent sympy routes)", detail=detail)
    return KV.exact({"valid": True, "kind": "density_matrix"}, "qmkernel.state_validity", "O(n^3)", cert)


def _check_unitary_exact(U: sp.Matrix) -> KV.Verdict:
    n = U.rows
    if U.rows != U.cols:
        return KV.decline("unitary check requires a square matrix", "qmkernel.state_validity")
    UdU = sp.simplify(U.conjugate().T * U)
    ok = UdU == sp.eye(n)
    if not ok:
        return KV.decline(f"U†U ≠ I: U†U={UdU}", "qmkernel.state_validity")
    cert = KV.Cert(KV.EXACT, "unitary_udagu_identity", passed=True, check_cost="O(n^3) matrix product",
                   detail="U†U=I verified exactly")
    return KV.exact({"valid": True, "kind": "unitary"}, "qmkernel.state_validity", "O(n^3)", cert)


def _check_projection_single_exact(P: sp.Matrix) -> KV.Verdict:
    n = P.rows
    idem = sp.simplify(P * P - P) == sp.zeros(n, n)
    herm = sp.simplify(P - P.conjugate().T) == sp.zeros(n, n)
    if not idem:
        return KV.decline("P² ≠ P (not idempotent)", "qmkernel.state_validity")
    if not herm:
        return KV.decline("P ≠ P† (not an orthogonal projection)", "qmkernel.state_validity")
    cert = KV.Cert(KV.EXACT, "projection_idempotent_hermitian", passed=True, check_cost="O(n^3)",
                   detail="P²=P and P=P† verified exactly")
    return KV.exact({"valid": True, "kind": "projection"}, "qmkernel.state_validity", "O(n^3)", cert)


def _check_povm_list_exact(Es: Sequence[sp.Matrix]) -> KV.Verdict:
    if not Es:
        return KV.decline("empty POVM list", "qmkernel.state_validity")
    n = Es[0].rows
    total = sp.zeros(n, n)
    for k, E in enumerate(Es):
        if E.rows != n or E.cols != n:
            return KV.decline(f"POVM element {k} has inconsistent dimension", "qmkernel.state_validity")
        psd, agree, detail = _is_psd_exact_crosschecked(E)
        if not agree:
            return KV.decline(f"POVM element {k} PSD cross-check DISAGREEMENT: {detail}", "qmkernel.state_validity")
        if not psd:
            return KV.decline(f"POVM element {k} is not PSD: {detail}", "qmkernel.state_validity")
        total += E
    total = sp.simplify(total)
    if total != sp.eye(n):
        return KV.decline(f"completeness FAILED: ΣE_k={total} ≠ I", "qmkernel.state_validity")
    cert = KV.Cert(KV.EXACT, "povm_positivity_completeness", passed=True,
                   check_cost=f"{len(Es)} PSD cross-checks + ΣE_k=I", detail=f"all {len(Es)} elements PSD; ΣE_k=I exactly")
    return KV.exact({"valid": True, "kind": "povm", "n_elements": len(Es)}, "qmkernel.state_validity", "O(k n^3)", cert)


def _check_kraus_exact(Ks: Sequence[sp.Matrix]) -> KV.Verdict:
    if not Ks:
        return KV.decline("empty Kraus list", "qmkernel.state_validity")
    n = Ks[0].cols
    total = sp.zeros(n, n)
    for K in Ks:
        total += K.conjugate().T * K
    total = sp.simplify(total)
    if total != sp.eye(n):
        return KV.decline(f"Kraus completeness FAILED: ΣK_k†K_k={total} ≠ I", "qmkernel.state_validity")
    cert = KV.Cert(KV.EXACT, "kraus_completeness", passed=True, check_cost=f"{len(Ks)} matrix products + sum",
                   detail=f"ΣK_k†K_k=I exactly over {len(Ks)} operators")
    return KV.exact({"valid": True, "kind": "kraus", "n_operators": len(Ks)}, "qmkernel.state_validity", "O(k n^3)", cert)


# ── Lane 2 (float) versions — same structure, tolerance-checked, never EXACT ────────────────────────────
def _check_lane2(obj, kind: str, eps_tol: float) -> LN.EpsCert:
    import numpy as np
    if kind == "density_matrix":
        rho = np.array(_rows_of(obj), dtype=complex)
        tr_resid = abs(complex(np.trace(rho)) - 1.0)
        herm_resid = float(np.max(np.abs(rho - rho.conj().T)))
        eigvals = np.linalg.eigvalsh((rho + rho.conj().T) / 2)
        min_eig = float(np.min(eigvals))
        worst = max(tr_resid, herm_resid, max(0.0, -min_eig))
        return LN.eps_cert(residual=worst, epsilon=eps_tol, kind="density_matrix_lane2",
                           detail=f"|tr-1|={tr_resid:.2e}, Hermiticity resid={herm_resid:.2e}, min_eig={min_eig:.2e}")
    if kind == "unitary":
        U = np.array(_rows_of(obj), dtype=complex)
        resid = float(np.max(np.abs(U.conj().T @ U - np.eye(U.shape[0]))))
        return LN.eps_cert(residual=resid, epsilon=eps_tol, kind="unitary_lane2", detail=f"‖U†U−I‖_max={resid:.2e}")
    if kind == "projection_povm":
        if isinstance(obj, (list, tuple)):
            n = np.array(_rows_of(obj[0]), dtype=complex).shape[0]
            total = np.zeros((n, n), dtype=complex)
            worst_psd = 0.0
            for E in obj:
                Em = np.array(_rows_of(E), dtype=complex)
                eig = np.linalg.eigvalsh((Em + Em.conj().T) / 2)
                worst_psd = max(worst_psd, max(0.0, -float(np.min(eig))))
                total += Em
            resid = max(worst_psd, float(np.max(np.abs(total - np.eye(n)))))
            return LN.eps_cert(residual=resid, epsilon=eps_tol, kind="povm_lane2",
                               detail=f"max PSD violation + ‖ΣE_k−I‖_max={resid:.2e}")
        P = np.array(_rows_of(obj), dtype=complex)
        idem = float(np.max(np.abs(P @ P - P)))
        herm = float(np.max(np.abs(P - P.conj().T)))
        return LN.eps_cert(residual=max(idem, herm), epsilon=eps_tol, kind="projection_lane2",
                           detail=f"‖P²−P‖_max={idem:.2e}, ‖P−P†‖_max={herm:.2e}")
    if kind == "kraus":
        n = np.array(_rows_of(obj[0]), dtype=complex).shape[1]
        total = np.zeros((n, n), dtype=complex)
        for K in obj:
            Km = np.array(_rows_of(K), dtype=complex)
            total += Km.conj().T @ Km
        resid = float(np.max(np.abs(total - np.eye(n))))
        return LN.eps_cert(residual=resid, epsilon=eps_tol, kind="kraus_lane2", detail=f"‖ΣK†K−I‖_max={resid:.2e}")
    raise ValueError(kind)


# ── the top-level entry point ───────────────────────────────────────────────────────────────────────────
def check(obj, kind: str, eps_tol: float = 1e-8) -> Union[KV.Verdict, LN.EpsCert]:
    if kind not in _KINDS:
        return KV.decline(f"unknown kind {kind!r}, expected one of {_KINDS}", "qmkernel.state_validity")
    try:
        rows = _flatten_rows(obj)
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"could not interpret object shape for kind={kind}: {type(e).__name__}: {e}",
                          "qmkernel.state_validity")

    if LN.is_exact_container(rows):
        if kind == "density_matrix":
            return _check_density_matrix_exact(_as_matrix(obj))
        if kind == "unitary":
            return _check_unitary_exact(_as_matrix(obj))
        if kind == "projection_povm":
            if isinstance(obj, (list, tuple)):
                return _check_povm_list_exact([_as_matrix(e) for e in obj])
            return _check_projection_single_exact(_as_matrix(obj))
        if kind == "kraus":
            if not isinstance(obj, (list, tuple)):
                return KV.decline("kraus requires a LIST of operators", "qmkernel.state_validity")
            return _check_kraus_exact([_as_matrix(k) for k in obj])

    return _check_lane2(obj, kind, eps_tol)


# ── adversarial battery ─────────────────────────────────────────────────────────────────────────────────
def adversarial_battery() -> dict:
    cases = {}

    # density matrix: valid pure state |0><0|
    rho_valid = sp.Matrix([[1, 0], [0, 0]])
    v1 = check(rho_valid, "density_matrix")
    cases["valid_density_matrix_exact"] = v1.status == KV.EXACT
    rho_bad_trace = sp.Matrix([[1, 0], [0, 1]])          # trace=2
    cases["bad_trace_declines"] = check(rho_bad_trace, "density_matrix").status == KV.DECLINE
    rho_not_psd = sp.Matrix([[2, 3], [3, -1]])            # trace=1, Hermitian, but not PSD (has a negative eigenvalue)
    cases["not_psd_declines"] = check(rho_not_psd, "density_matrix").status == KV.DECLINE
    rho_mixed = sp.Matrix([[sp.Rational(1, 2), 0], [0, sp.Rational(1, 2)]])   # maximally mixed, valid
    cases["mixed_state_exact"] = check(rho_mixed, "density_matrix").status == KV.EXACT

    # unitary
    Hgate = sp.Matrix([[1, 1], [1, -1]]) / sp.sqrt(2)     # Hadamard, unitary
    cases["hadamard_unitary_exact"] = check(Hgate, "unitary").status == KV.EXACT
    not_unitary = sp.Matrix([[1, 1], [0, 1]])
    cases["non_unitary_declines"] = check(not_unitary, "unitary").status == KV.DECLINE

    # projection (single)
    Pgood = sp.Matrix([[1, 0], [0, 0]])
    cases["valid_projection_exact"] = check(Pgood, "projection_povm").status == KV.EXACT
    Pbad = sp.Matrix([[1, 1], [0, 0]])                    # idempotent (P^2=P) but NOT Hermitian
    cases["nonhermitian_projection_declines"] = check(Pbad, "projection_povm").status == KV.DECLINE
    Pnotidem = sp.Matrix([[1, 0], [0, sp.Rational(1, 2)]])   # Hermitian but not idempotent
    cases["nonidempotent_projection_declines"] = check(Pnotidem, "projection_povm").status == KV.DECLINE

    # POVM (list) -- projective measurement {|0><0|, |1><1|} is a valid POVM (and a PVM)
    povm_valid = [sp.Matrix([[1, 0], [0, 0]]), sp.Matrix([[0, 0], [0, 1]])]
    cases["valid_povm_exact"] = check(povm_valid, "projection_povm").status == KV.EXACT
    povm_bad = [sp.Matrix([[1, 0], [0, 0]]), sp.Matrix([[0, 0], [0, sp.Rational(1, 2)]])]   # doesn't sum to I
    cases["incomplete_povm_declines"] = check(povm_bad, "projection_povm").status == KV.DECLINE
    povm_nonpsd = [sp.Matrix([[2, 0], [0, -1]]), sp.Matrix([[-1, 0], [0, 2]])]              # sums to I but not PSD
    cases["nonpsd_povm_declines"] = check(povm_nonpsd, "projection_povm").status == KV.DECLINE

    # Kraus (amplitude damping channel, gamma=1/2 -- textbook 2-Kraus-operator channel)
    g = sp.Rational(1, 2)
    K0 = sp.Matrix([[1, 0], [0, sp.sqrt(1 - g)]])
    K1 = sp.Matrix([[0, sp.sqrt(g)], [0, 0]])
    cases["valid_kraus_exact"] = check([K0, K1], "kraus").status == KV.EXACT
    cases["incomplete_kraus_declines"] = check([K0], "kraus").status == KV.DECLINE   # missing K1, doesn't sum to I

    # 2-lane forced: float density matrix
    import numpy as np
    rho_f = np.array([[0.6, 0.0], [0.0, 0.4]])
    vf = check(rho_f, "density_matrix")
    cases["float_density_is_eps_cert_not_kv_verdict"] = isinstance(vf, LN.EpsCert) and not isinstance(vf, KV.Verdict)
    cases["float_density_never_exact_tag"] = getattr(vf, "lane", None) == "APPROX_EPS"
    cases["float_density_passes"] = isinstance(vf, LN.EpsCert) and vf.passed

    # 2-lane forced: float unitary
    Uf = np.array([[1.0, 1.0], [1.0, -1.0]]) / (2 ** 0.5)
    vfu = check(Uf, "unitary")
    cases["float_unitary_is_eps_cert"] = isinstance(vfu, LN.EpsCert) and not isinstance(vfu, KV.Verdict)

    # 2-lane forced: a bad float density matrix -> EpsCert with passed=False (still Lane 2, never a fake EXACT)
    rho_f_bad = np.array([[2.0, 3.0], [3.0, -1.0]])
    vfb = check(rho_f_bad, "density_matrix")
    cases["float_bad_density_eps_cert_not_passed"] = isinstance(vfb, LN.EpsCert) and not vfb.passed

    all_ok = all(cases.values())
    failed = [k for k, v_ in cases.items() if not v_]
    return {"cases": cases, "all_ok": all_ok, "failed": failed}


if __name__ == "__main__":
    import json
    b = adversarial_battery()
    print(json.dumps({"all_ok": b["all_ok"], "failed": b["failed"], "n_cases": len(b["cases"])}, indent=2))
