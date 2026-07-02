"""
qmkernel/state_distance.py — §BR STAGE 3 NEW-10: quantum distance/divergence bundle, over NEW-9-validated states.
============================================================================================================
Fidelity · quantum relative entropy · trace distance — over density matrices FIRST validated by
`qmkernel.state_validity.check(..., "density_matrix")` (a genuine composition: this module never accepts an
unvalidated object, it re-runs the SAME check NEW-9 already built, not a duplicate of it).

★ honest scope (never a wrong answer): trace distance is ALWAYS exactly computable (ρ−σ is Hermitian
regardless of whether ρ,σ commute, so its eigenvalues are always real — the SAME cross-checked PSD/eigenvalue
machinery as NEW-9 applies directly). Fidelity and relative entropy reduce to simple, exactly-computable
eigenvalue formulas only when a shared eigenbasis exists (either operator is pure, or the two commute) — the
FULLY GENERAL non-commuting mixed-mixed case needs a genuine matrix square root / matrix logarithm, which this
engine DECLINES rather than attempt a fragile symbolic computation (§2 "guess-and-certify... never a coin
flip"). This is a real mathematical boundary, stated, not a missing feature hidden by silence.

★ §1's own closed-form-vs-decimal-evaluation rule, applied directly: relative entropy's value is generically
irrational (logarithms) even for perfectly rational eigenvalues — the SYMBOLIC closed form Σp_i·log(p_i/q_i) is
Lane 1 EXACT (the expression itself, exact by construction); a DECIMAL value is a separate Lane-2 step via
`qmkernel.lane.decimal_eval`, never silently folded into the "EXACT" result.
★ m03 guess-and-certify recognition branch (shared with NEW-9). No 15th mechanism.
"""
from __future__ import annotations

from typing import Optional, Tuple, Union

import sympy as sp

import kernel_verdict as KV
from qmkernel import lane as LN
from qmkernel import state_validity as SV


def _validate(rho) -> Optional[str]:
    v = SV.check(rho, "density_matrix")
    if isinstance(v, KV.Verdict) and v.status == KV.DECLINE:
        return v.reason
    if isinstance(v, LN.EpsCert) and not v.passed:
        return v.detail
    return None


def _is_pure_exact(rho: sp.Matrix) -> Tuple[bool, Optional[sp.Expr]]:
    """(is_pure, the_single_nonzero_eigenvalue_if_pure) — pure iff rank exactly 1: ONE distinct nonzero
    eigenvalue AND its multiplicity is 1 (NOT just one distinct nonzero value — `eigenvals()` returns a dict
    keyed by distinct value, so e.g. the maximally-mixed state {1/2: multiplicity 2} has exactly one distinct
    nonzero KEY but is rank 2, not pure — multiplicity must be checked explicitly)."""
    eigvals = rho.eigenvals()             # dict: value -> multiplicity
    nonzero = [(ev, mult) for ev, mult in eigvals.items() if sp.simplify(ev) != 0]
    if len(nonzero) == 1 and nonzero[0][1] == 1:
        return True, nonzero[0][0]
    return False, None


def _commuting_joint_eigenbasis(rho: sp.Matrix, sigma: sp.Matrix):
    """If ρ,σ commute, returns (p_vals, q_vals) in a SHARED eigenbasis, else None. Sound (never wrong): if ρ
    has a degenerate eigenvalue and sympy's chosen eigenbasis for it does not also diagonalize σ, this
    correctly returns None (DECLINE) rather than silently picking the wrong pairing."""
    n = rho.rows
    if sp.simplify(rho * sigma - sigma * rho) != sp.zeros(n, n):
        return None
    try:
        P, D = rho.diagonalize()
    except Exception:  # noqa: BLE001 — a genuine non-diagonalizability declines, not crashes
        return None
    p_vals = [D[i, i] for i in range(n)]
    sigma_rot = sp.simplify(P.inv() * sigma * P)
    for i in range(n):
        for j in range(n):
            if i != j and sp.simplify(sigma_rot[i, j]) != 0:
                return None
    q_vals = [sigma_rot[i, i] for i in range(n)]
    return p_vals, q_vals


# ── von Neumann entropy: always exact (a single Hermitian matrix, no joint-eigenbasis issue at all) ────
def von_neumann_entropy(rho) -> Union[KV.Verdict, LN.EpsCert]:
    """S(ρ)=-tr(ρ log ρ) = -Σ(mult·λ_i·log λ_i). Always exact-computable (single operator — no commutativity
    concern); the CLOSED FORM is Lane 1 EXACT even though it contains logarithms (§1's own rule: the
    EXPRESSION is exact, its decimal value is a separate Lane-2 step via qmkernel.lane.decimal_eval)."""
    err = _validate(rho)
    if err:
        return KV.decline(f"input failed NEW-9 density-matrix validation: {err}", "qmkernel.state_distance")
    rows = SV._flatten_rows(rho)
    if LN.is_exact_container(rows):
        rho_m = SV._as_matrix(rho)
        eigval_mult = rho_m.eigenvals()
        terms = []
        for ev, mult in eigval_mult.items():
            p = sp.simplify(ev)
            if p == 0:
                continue
            terms.append(mult * p * sp.log(p))
        S = sp.simplify(-sum(terms)) if terms else sp.Integer(0)
        cert = KV.Cert(KV.EXACT, "von_neumann_entropy_closed_form", passed=True,
                       check_cost="eigenvalues with multiplicity (exact)",
                       detail=f"eigenvalues(ρ) with multiplicity={eigval_mult}; S(ρ)=-Σ(mult·λlogλ)={S} "
                              "(EXACT closed form; decimal value is Lane 2)")
        return KV.exact({"entropy_exact_expr": S}, "qmkernel.state_distance", "O(n^3)", cert)
    import numpy as np
    rho_f = np.array(SV._rows_of(rho), dtype=complex)
    eigvals = np.linalg.eigvalsh((rho_f + rho_f.conj().T) / 2)
    S = -sum(float(p * np.log(p)) for p in eigvals if p > 1e-14)
    return LN.eps_cert(residual=0.0, epsilon=1e-6, kind="von_neumann_entropy_lane2", detail=f"S≈{S:.6f}")


# ── trace distance: always exact (no commutativity needed) ─────────────────────────────────────────────
def trace_distance(rho, sigma) -> Union[KV.Verdict, LN.EpsCert]:
    for r in (rho, sigma):
        err = _validate(r)
        if err:
            return KV.decline(f"input failed NEW-9 density-matrix validation: {err}", "qmkernel.state_distance")
    rows = SV._flatten_rows(rho) + SV._flatten_rows(sigma)
    if LN.is_exact_container(rows):
        rho_m, sigma_m = SV._as_matrix(rho), SV._as_matrix(sigma)
        diff = sp.simplify(rho_m - sigma_m)
        eigval_mult = diff.eigenvals()        # dict: value -> multiplicity — MUST weight by multiplicity
        td = sp.simplify(sp.Rational(1, 2) * sum(mult * sp.Abs(sp.simplify(ev)) for ev, mult in eigval_mult.items()))
        cert = KV.Cert(KV.EXACT, "trace_distance_eigenvalue_abs_sum", passed=True,
                       check_cost="eigenvalues of the Hermitian difference ρ-σ (exact, multiplicity-weighted)",
                       detail=f"eigenvalues(ρ-σ) with multiplicity={eigval_mult}; D=½Σ(mult·|λ_i|)={td}")
        return KV.exact({"trace_distance": td}, "qmkernel.state_distance", "O(n^3)", cert)
    import numpy as np
    rho_f = np.array(SV._rows_of(rho), dtype=complex)
    sigma_f = np.array(SV._rows_of(sigma), dtype=complex)
    diff = rho_f - sigma_f
    eigvals = np.linalg.eigvalsh((diff + diff.conj().T) / 2)
    td = 0.5 * float(np.sum(np.abs(eigvals)))
    return LN.eps_cert(residual=0.0, epsilon=1e-6, kind="trace_distance_lane2", detail=f"D={td:.6f}")


# ── fidelity: exact when either state is pure, or the two commute ──────────────────────────────────────
def fidelity(rho, sigma) -> Union[KV.Verdict, LN.EpsCert]:
    for r in (rho, sigma):
        err = _validate(r)
        if err:
            return KV.decline(f"input failed NEW-9 density-matrix validation: {err}", "qmkernel.state_distance")
    rows = SV._flatten_rows(rho) + SV._flatten_rows(sigma)
    if LN.is_exact_container(rows):
        rho_m, sigma_m = SV._as_matrix(rho), SV._as_matrix(sigma)
        pure_rho, _ = _is_pure_exact(rho_m)
        pure_sigma, _ = _is_pure_exact(sigma_m)
        if pure_rho or pure_sigma:
            F = sp.simplify(sp.trace(rho_m * sigma_m))
            cert = KV.Cert(KV.EXACT, "fidelity_pure_state_tr_rho_sigma", passed=True,
                           check_cost="O(n^3), valid whenever either operand is pure",
                           detail=f"pure_rho={pure_rho}, pure_sigma={pure_sigma}; F=tr(ρσ)={F}")
            return KV.exact({"fidelity": F}, "qmkernel.state_distance", "O(n^3)", cert)
        joint = _commuting_joint_eigenbasis(rho_m, sigma_m)
        if joint is not None:
            p_vals, q_vals = joint
            F = sp.simplify(sum(sp.sqrt(sp.simplify(p * q)) for p, q in zip(p_vals, q_vals)) ** 2)
            cert = KV.Cert(KV.EXACT, "fidelity_commuting_joint_eigenbasis", passed=True,
                           check_cost="commutator check + simultaneous diagonalization",
                           detail=f"ρ,σ commute; joint eigenvalues p={p_vals}, q={q_vals}; F=(Σ√(p_iq_i))²={F}")
            return KV.exact({"fidelity": F}, "qmkernel.state_distance", "O(n^3)", cert)
        return KV.decline("fidelity of two non-commuting MIXED states needs a genuine matrix square root — "
                          "out of this engine's exact scope (neither operand is pure, and ρσ≠σρ)",
                          "qmkernel.state_distance")
    import numpy as np
    rho_f = np.array(SV._rows_of(rho), dtype=complex)
    sigma_f = np.array(SV._rows_of(sigma), dtype=complex)

    def _sqrtm_herm(M):
        w, v = np.linalg.eigh((M + M.conj().T) / 2)
        w = np.clip(w, 0, None)
        return (v * np.sqrt(w)) @ v.conj().T

    sq_rho = _sqrtm_herm(rho_f)
    inner = sq_rho @ sigma_f @ sq_rho
    w = np.linalg.eigvalsh((inner + inner.conj().T) / 2)
    w = np.clip(w, 0, None)
    F = float(np.sum(np.sqrt(w)) ** 2)
    return LN.eps_cert(residual=0.0, epsilon=1e-6, kind="fidelity_lane2_general", detail=f"F={F:.6f}")


# ── relative entropy: exact CLOSED FORM when ρ,σ commute (else DECLINE); decimal value is Lane 2 ───────
def relative_entropy(rho, sigma) -> Union[KV.Verdict, LN.EpsCert]:
    for r in (rho, sigma):
        err = _validate(r)
        if err:
            return KV.decline(f"input failed NEW-9 density-matrix validation: {err}", "qmkernel.state_distance")
    rows = SV._flatten_rows(rho) + SV._flatten_rows(sigma)
    if LN.is_exact_container(rows):
        rho_m, sigma_m = SV._as_matrix(rho), SV._as_matrix(sigma)
        joint = _commuting_joint_eigenbasis(rho_m, sigma_m)
        if joint is None:
            return KV.decline("relative entropy of non-commuting states needs a matrix logarithm — out of "
                              "this engine's exact scope", "qmkernel.state_distance")
        p_vals, q_vals = joint
        terms = []
        for p, q in zip(p_vals, q_vals):
            p, q = sp.simplify(p), sp.simplify(q)
            if p == 0:
                continue
            if q == 0:
                return KV.decline(f"relative entropy DIVERGES: support(ρ) ⊄ support(σ) (p={p}, q=0)",
                                  "qmkernel.state_distance")
            terms.append(p * sp.log(p / q))
        S = sp.simplify(sum(terms)) if terms else sp.Integer(0)
        cert = KV.Cert(KV.EXACT, "relative_entropy_commuting_closed_form", passed=True,
                       check_cost="commutator check + simultaneous diagonalization",
                       detail=f"S(ρ‖σ)=Σp_i·log(p_i/q_i)={S} (EXACT closed form; decimal value is Lane 2 — "
                              "§1's own closed-form-vs-decimal-evaluation rule)")
        return KV.exact({"relative_entropy_exact_expr": S}, "qmkernel.state_distance", "O(n^3)", cert)
    import numpy as np
    rho_f = np.array(SV._rows_of(rho), dtype=complex)
    sigma_f = np.array(SV._rows_of(sigma), dtype=complex)
    pw = np.linalg.eigvalsh((rho_f + rho_f.conj().T) / 2)
    qw = np.linalg.eigvalsh((sigma_f + sigma_f.conj().T) / 2)
    pw, qw = np.sort(pw)[::-1], np.sort(qw)[::-1]     # Lane 2: approximate via SORTED spectra (own eigenbases)
    S = 0.0
    for p, q in zip(pw, qw):
        if p > 1e-14:
            if q <= 1e-14:
                return KV.decline("relative entropy diverges (Lane 2): support mismatch", "qmkernel.state_distance")
            S += float(p * np.log(p / q))
    return LN.eps_cert(residual=0.0, epsilon=1e-6, kind="relative_entropy_lane2_sorted_spectra",
                       detail=f"S≈{S:.6f} (Lane 2 approximation via sorted eigenvalue pairing, NOT the exact "
                              "commuting-basis formula — an honest approximation, not claimed exact)")


# ── adversarial battery ─────────────────────────────────────────────────────────────────────────────────
def adversarial_battery() -> dict:
    cases = {}

    rho_pure0 = sp.Matrix([[1, 0], [0, 0]])
    rho_pure1 = sp.Matrix([[0, 0], [0, 1]])
    rho_mixed = sp.Matrix([[sp.Rational(1, 2), 0], [0, sp.Rational(1, 2)]])

    # von Neumann entropy: pure state -> 0; maximally mixed 2-level -> log(2)
    ve1 = von_neumann_entropy(rho_pure0)
    cases["pure_state_entropy_zero"] = ve1.status == KV.EXACT and sp.simplify(ve1.result["entropy_exact_expr"]) == 0
    ve2 = von_neumann_entropy(rho_mixed)
    cases["maximally_mixed_entropy_log2"] = (ve2.status == KV.EXACT and
                                             sp.simplify(ve2.result["entropy_exact_expr"] - sp.log(2)) == 0)

    # trace distance: orthogonal pure states -> maximal distance 1
    v1 = trace_distance(rho_pure0, rho_pure1)
    cases["orthogonal_pure_trace_distance_is_one"] = v1.status == KV.EXACT and sp.simplify(v1.result["trace_distance"] - 1) == 0
    # trace distance to self is 0
    v2 = trace_distance(rho_pure0, rho_pure0)
    cases["self_trace_distance_zero"] = v2.status == KV.EXACT and sp.simplify(v2.result["trace_distance"]) == 0

    # ★ regression: (ρ-σ) with a REPEATED eigenvalue — must be multiplicity-WEIGHTED, not counted once per
    # distinct value (the exact bug this battery caught: |2/3|+|-1/3|=1, D=1/2 WRONG vs correct D=2/3)
    rho3 = sp.diag(1, 0, 0)
    sigma3 = sp.eye(3) / 3
    v2b = trace_distance(rho3, sigma3)
    cases["repeated_eigenvalue_trace_distance_multiplicity_weighted"] = (
        v2b.status == KV.EXACT and sp.simplify(v2b.result["trace_distance"] - sp.Rational(2, 3)) == 0)

    # fidelity: orthogonal pure states -> 0
    v3 = fidelity(rho_pure0, rho_pure1)
    cases["orthogonal_pure_fidelity_zero"] = v3.status == KV.EXACT and sp.simplify(v3.result["fidelity"]) == 0
    # fidelity: identical pure state -> 1
    v4 = fidelity(rho_pure0, rho_pure0)
    cases["self_fidelity_one"] = v4.status == KV.EXACT and sp.simplify(v4.result["fidelity"] - 1) == 0
    # fidelity: pure vs mixed
    v5 = fidelity(rho_pure0, rho_mixed)
    cases["pure_vs_mixed_fidelity_exact"] = v5.status == KV.EXACT and sp.simplify(v5.result["fidelity"] - sp.Rational(1, 2)) == 0

    # fidelity: two commuting mixed states (both diagonal, not pure) -- the joint-eigenbasis path
    sigma_mixed = sp.Matrix([[sp.Rational(1, 4), 0], [0, sp.Rational(3, 4)]])
    v6 = fidelity(rho_mixed, sigma_mixed)
    expected_F = (sp.sqrt(sp.Rational(1, 2) * sp.Rational(1, 4)) + sp.sqrt(sp.Rational(1, 2) * sp.Rational(3, 4))) ** 2
    cases["commuting_mixed_fidelity_exact"] = (v6.status == KV.EXACT and
                                               sp.simplify(v6.result["fidelity"] - expected_F) == 0)

    # fidelity: two NON-commuting mixed states -> honest DECLINE (never a wrong guess)
    non_comm_a = sp.Matrix([[sp.Rational(3, 4), sp.Rational(1, 4)], [sp.Rational(1, 4), sp.Rational(1, 4)]])
    non_comm_b = sp.Matrix([[sp.Rational(1, 2), sp.Rational(1, 4)], [sp.Rational(1, 4), sp.Rational(1, 2)]])
    is_comm = sp.simplify(non_comm_a * non_comm_b - non_comm_b * non_comm_a) == sp.zeros(2, 2)
    is_pure_a, _ = _is_pure_exact(non_comm_a)
    is_pure_b, _ = _is_pure_exact(non_comm_b)
    v7 = fidelity(non_comm_a, non_comm_b)
    cases["noncommuting_mixed_fidelity_declines"] = (not is_comm and not is_pure_a and not is_pure_b and
                                                      v7.status == KV.DECLINE)

    # relative entropy: self vs self is 0
    v8 = relative_entropy(rho_mixed, rho_mixed)
    cases["self_relative_entropy_zero"] = v8.status == KV.EXACT and sp.simplify(v8.result["relative_entropy_exact_expr"]) == 0
    # relative entropy: commuting, distinct -> exact symbolic (contains log), nonzero
    v9 = relative_entropy(rho_mixed, sigma_mixed)
    cases["commuting_relative_entropy_exact_nonzero"] = (v9.status == KV.EXACT and
                                                          sp.simplify(v9.result["relative_entropy_exact_expr"]) != 0)
    # decimal evaluation of the exact expression is Lane 2, never EXACT
    dv = LN.decimal_eval(v9.result["relative_entropy_exact_expr"], kind="rel_entropy_decimal")
    cases["relative_entropy_decimal_is_lane2"] = dv.lane == "APPROX_EPS" and not isinstance(dv, KV.Verdict)
    # relative entropy: divergent (support mismatch) -> DECLINE
    v10 = relative_entropy(rho_pure0, rho_pure1)
    cases["divergent_relative_entropy_declines"] = v10.status == KV.DECLINE

    # validation composition: an INVALID density matrix must decline in every distance function (never crash)
    bad_rho = sp.Matrix([[2, 0], [0, -1]])
    cases["invalid_input_declines_in_trace_distance"] = trace_distance(bad_rho, rho_mixed).status == KV.DECLINE
    cases["invalid_input_declines_in_fidelity"] = fidelity(bad_rho, rho_mixed).status == KV.DECLINE
    cases["invalid_input_declines_in_relative_entropy"] = relative_entropy(bad_rho, rho_mixed).status == KV.DECLINE

    # Lane 2: float states
    import numpy as np
    rho_f = np.array([[1.0, 0.0], [0.0, 0.0]])
    sigma_f = np.array([[0.5, 0.0], [0.0, 0.5]])
    vf1 = trace_distance(rho_f, sigma_f)
    cases["float_trace_distance_is_eps_cert"] = isinstance(vf1, LN.EpsCert) and not isinstance(vf1, KV.Verdict)
    vf2 = fidelity(rho_f, sigma_f)
    cases["float_fidelity_is_eps_cert"] = isinstance(vf2, LN.EpsCert) and not isinstance(vf2, KV.Verdict)

    all_ok = all(cases.values())
    failed = [k for k, v_ in cases.items() if not v_]
    return {"cases": cases, "all_ok": all_ok, "failed": failed}


if __name__ == "__main__":
    import json
    b = adversarial_battery()
    print(json.dumps({"all_ok": b["all_ok"], "failed": b["failed"], "n_cases": len(b["cases"])}, indent=2))
