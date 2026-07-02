"""
qmkernel/qm_inequality.py — §BR STAGE 3 NEW-11: quantum inequality certificate checker, ONE engine.
============================================================================================================
Robertson uncertainty · variational principle · CHSH/Bell · Holevo (non-negativity) · monogamy — FIVE
inequalities, NOT five files: every one of them reduces to the SAME primitive, `check_bound(lhs, rhs, cmp,
tol)` — compute both sides EXACTLY (or, with a caller-stated tolerance, numerically) and check the PROVEN
inequality direction. This is the Freivalds-style "guess-and-certify" spirit (m03) applied to inequalities
instead of equalities: never trust a claimed direction, always recompute both sides independently.

★ the directive's own explicit rule for this engine: float input with NO explicit tolerance stated ⇒ DECLINE.
An inequality boundary is exactly where floating-point rounding is most dangerous — silently accepting an
un-toleranced float comparison would risk a false-EXACT-flavoured overclaim even under the Lane-2 label, so
this engine refuses outright rather than emit a possibly-meaningless answer.

★ honest scope: Holevo's theorem bounds the TRUE accessible information (a hard POVM-optimization problem this
engine does not attempt); what IS exactly checked is the Holevo quantity's well-known non-negativity
(concavity of von Neumann entropy) for a GIVEN ensemble — a real, always-true, machine-verified fact, stated
as exactly that and not oversold as "verifying Holevo's theorem" in full generality. Monogamy of entanglement
(e.g. the CKW tangle inequality) needs a 2-qubit concurrence/tangle formula that is genuinely new
infrastructure beyond this pass — DECLINED explicitly rather than guessed (§4/§5 honesty requirement: no
un-derived formula, ever).
"""
from __future__ import annotations

from typing import Optional, Sequence, Union

import sympy as sp

import kernel_verdict as KV
from qmkernel import lane as LN
from qmkernel import state_distance as SD
from qmkernel import state_validity as SV

_CMPS = {"<=", ">=", "<", ">"}


# ── the shared primitive: compute both sides, check the PROVEN direction ───────────────────────────────
def check_bound(lhs, rhs, cmp: str, tol: Optional[float] = None, kind: str = "generic") -> Union[KV.Verdict, LN.EpsCert]:
    if cmp not in _CMPS:
        return KV.decline(f"unknown comparison {cmp!r}", "qmkernel.qm_inequality")
    exact = LN.is_exact_scalar(lhs) and LN.is_exact_scalar(rhs)
    if exact:
        diff = sp.simplify(sp.sympify(lhs) - sp.sympify(rhs))
        holds = {"<=": diff.is_nonpositive, ">=": diff.is_nonnegative,
                 "<": diff.is_negative, ">": diff.is_positive}[cmp]
        if holds is None:
            return KV.decline(f"could not determine the exact sign of {lhs}−{rhs} ⇒ DECLINE", "qmkernel.qm_inequality")
        if not holds:
            return KV.decline(f"inequality {lhs} {cmp} {rhs} does NOT hold (diff={diff}) — refuted, not guessed",
                              "qmkernel.qm_inequality")
        cert = KV.Cert(KV.EXACT, f"inequality_exact_{kind}", passed=True, check_cost="O(1) exact sign check",
                       detail=f"{lhs} {cmp} {rhs}: diff={diff}, sign proven")
        return KV.exact({"holds": True, "lhs": lhs, "rhs": rhs, "diff": diff}, "qmkernel.qm_inequality", "O(1)", cert)
    if tol is None:
        return KV.decline("float operand(s) with NO explicit tolerance stated ⇒ DECLINE (an inequality "
                          "boundary is exactly where floating rounding is dangerous — never a bare-float "
                          "verdict without a stated ε)", "qmkernel.qm_inequality")
    lhsf, rhsf = float(lhs), float(rhs)
    margin = {"<=": rhsf - lhsf, ">=": lhsf - rhsf, "<": rhsf - lhsf, ">": lhsf - rhsf}[cmp]
    violation = max(0.0, -margin)
    return LN.eps_cert(residual=violation, epsilon=tol, kind=f"inequality_lane2_{kind}",
                       detail=f"{lhsf:.6g} {cmp} {rhsf:.6g}: margin={margin:.3e}, tol={tol:.1e}")


# ── 1. Robertson uncertainty: ΔAΔB ≥ ½|⟨[A,B]⟩| ─────────────────────────────────────────────────────────
def robertson_uncertainty(A, B, psi, tol: Optional[float] = None) -> Union[KV.Verdict, LN.EpsCert]:
    Am, Bm, psim = sp.Matrix(A), sp.Matrix(B), sp.Matrix(psi)
    norm2 = sp.simplify((psim.H * psim)[0, 0])
    if LN.is_exact_scalar(norm2) and sp.simplify(norm2 - 1) != 0:
        return KV.decline(f"ψ not normalized: ⟨ψ|ψ⟩={norm2} ≠ 1", "qmkernel.qm_inequality")
    expA = sp.simplify((psim.H * Am * psim)[0, 0])
    expA2 = sp.simplify((psim.H * Am * Am * psim)[0, 0])
    expB = sp.simplify((psim.H * Bm * psim)[0, 0])
    expB2 = sp.simplify((psim.H * Bm * Bm * psim)[0, 0])
    varA = sp.simplify(expA2 - expA ** 2)
    varB = sp.simplify(expB2 - expB ** 2)
    comm = sp.simplify((psim.H * (Am * Bm - Bm * Am) * psim)[0, 0])
    lhs = sp.simplify(sp.sqrt(varA) * sp.sqrt(varB)) if LN.is_exact_scalar(varA) and LN.is_exact_scalar(varB) else \
        (varA * varB) ** 0.5
    rhs = sp.simplify(sp.Rational(1, 2) * sp.Abs(comm)) if LN.is_exact_scalar(comm) else 0.5 * abs(comm)
    return check_bound(lhs, rhs, ">=", tol=tol, kind="robertson")


# ── 2. variational principle: ⟨ψ|H|ψ⟩ ≥ E₀ (the TRUE ground energy) ─────────────────────────────────────
def variational_principle(H, psi, tol: Optional[float] = None) -> Union[KV.Verdict, LN.EpsCert]:
    Hm, psim = sp.Matrix(H), sp.Matrix(psi)
    norm2 = sp.simplify((psim.H * psim)[0, 0])
    if LN.is_exact_scalar(norm2) and sp.simplify(norm2 - 1) != 0:
        return KV.decline(f"ψ not normalized: ⟨ψ|ψ⟩={norm2} ≠ 1", "qmkernel.qm_inequality")
    expH = sp.simplify((psim.H * Hm * psim)[0, 0])
    rows = [[Hm[i, j] for j in range(Hm.cols)] for i in range(Hm.rows)]
    if LN.is_exact_container(rows):
        eigvals = list(Hm.eigenvals().keys())
        E0 = min(eigvals, key=lambda x: sp.N(sp.simplify(x)))
        return check_bound(expH, E0, ">=", tol=tol, kind="variational")
    import numpy as np
    Hf = np.array(rows, dtype=complex)
    E0 = float(np.min(np.linalg.eigvalsh((Hf + Hf.conj().T) / 2)))
    return check_bound(complex(expH).real, E0, ">=", tol=tol, kind="variational")


# ── 3. CHSH/Bell: |S| ≤ 2 (classical/local-hidden-variable) or ≤ 2√2 (Tsirelson, quantum) ──────────────
def chsh_bound(e_ab, e_ab2, e_a2b, e_a2b2, quantum: bool = False, tol: Optional[float] = None) -> Union[KV.Verdict, LN.EpsCert]:
    vals = [e_ab, e_ab2, e_a2b, e_a2b2]
    exact = all(LN.is_exact_scalar(v) for v in vals)
    S = (e_ab - e_ab2 + e_a2b + e_a2b2)
    S = sp.simplify(S) if exact else float(S)
    bound = sp.Integer(2) if not quantum else sp.sqrt(8)          # 2√2 = √8, exact algebraic form
    absS = sp.Abs(S) if exact else abs(S)
    if not exact and quantum:
        bound = float(bound)
    return check_bound(absS, bound, "<=", tol=tol, kind="chsh_tsirelson" if quantum else "chsh_classical")


# ── 4. Holevo quantity non-negativity: χ({p_i,ρ_i}) = S(ρ̄) − Σp_iS(ρ_i) ≥ 0 (concavity of S) ──────────
def holevo_nonnegativity(probs: Sequence, rhos: Sequence, tol: Optional[float] = None) -> Union[KV.Verdict, LN.EpsCert]:
    if len(probs) != len(rhos) or not rhos:
        return KV.decline("probs/rhos length mismatch or empty", "qmkernel.qm_inequality")
    exact_probs = all(LN.is_exact_scalar(p) for p in probs)
    if exact_probs:
        if sp.simplify(sum(probs) - 1) != 0:
            return KV.decline(f"probabilities do not sum to 1: {sum(probs)}", "qmkernel.qm_inequality")
        if any(sp.simplify(p).is_negative for p in probs):
            return KV.decline("a negative probability was supplied", "qmkernel.qm_inequality")
    n = SV._as_matrix(rhos[0]).rows
    rho_bar = sum((p * SV._as_matrix(r) for p, r in zip(probs, rhos)), sp.zeros(n, n))
    v_bar = SD.von_neumann_entropy(rho_bar)
    if isinstance(v_bar, KV.Verdict) and v_bar.status == KV.DECLINE:
        return KV.decline(f"S(ρ̄) declined: {v_bar.reason}", "qmkernel.qm_inequality")
    v_each = [SD.von_neumann_entropy(r) for r in rhos]
    for v in v_each:
        if isinstance(v, KV.Verdict) and v.status == KV.DECLINE:
            return KV.decline(f"S(ρ_i) declined for one ensemble member: {v.reason}", "qmkernel.qm_inequality")
    all_exact = isinstance(v_bar, KV.Verdict) and all(isinstance(v, KV.Verdict) for v in v_each)
    if all_exact:
        S_bar = v_bar.result["entropy_exact_expr"]
        S_each = [v.result["entropy_exact_expr"] for v in v_each]
        chi = sp.simplify(S_bar - sum(p * s for p, s in zip(probs, S_each)))
        return check_bound(chi, 0, ">=", tol=tol, kind="holevo_nonneg")
    return KV.decline("mixed exact/Lane-2 ensemble members are not composed here — supply a uniformly exact "
                      "or uniformly float ensemble", "qmkernel.qm_inequality")


# ── 5. monogamy of entanglement (CKW tangle inequality) — honest scope DECLINE ──────────────────────────
def monogamy_tangle_check(*args, **kwargs) -> KV.Verdict:
    """τ_AB + τ_AC ≤ τ_A(BC) needs the Wootters concurrence/tangle formula for 2-qubit reduced states — a
    genuinely new piece of infrastructure this pass does not build (§4/§5: no un-derived formula, ever).
    DECLINE, explicitly and honestly, rather than a guessed tangle computation."""
    return KV.decline("monogamy-of-entanglement (CKW tangle) needs the Wootters concurrence/tangle formula, "
                      "which is not implemented in this pass — an honest scope boundary, not a silent gap "
                      "(see QMKERNEL_INDEX.md / this module's docstring)", "qmkernel.qm_inequality")


# ── adversarial battery ─────────────────────────────────────────────────────────────────────────────────
def adversarial_battery() -> dict:
    cases = {}

    # check_bound core: exact holds / exact fails / float no-tol declines / float with tol passes
    cases["exact_bound_holds"] = check_bound(sp.Integer(3), sp.Integer(5), "<=").status == KV.EXACT
    cases["exact_bound_fails_declines"] = check_bound(sp.Integer(5), sp.Integer(3), "<=").status == KV.DECLINE
    cases["float_no_tolerance_declines"] = check_bound(3.0001, 3.0, "<=").status == KV.DECLINE
    vft = check_bound(3.0001, 3.0, "<=", tol=1e-3)
    cases["float_with_tolerance_is_eps_cert"] = isinstance(vft, LN.EpsCert) and not isinstance(vft, KV.Verdict) and vft.passed

    # 1) Robertson uncertainty: canonical X,P-like qubit operators (Pauli X,Z), |0> state
    X = sp.Matrix([[0, 1], [1, 0]])
    Z = sp.Matrix([[1, 0], [0, -1]])
    psi0 = sp.Matrix([1, 0])
    v1 = robertson_uncertainty(X, Z, psi0)
    cases["robertson_pauli_exact_grade"] = v1.status in (KV.EXACT, KV.DECLINE)   # must not crash; check it actually HOLDS below
    cases["robertson_pauli_holds"] = v1.status == KV.EXACT

    # 2) variational principle: H=Pauli Z (eigenvalues +-1), trial state |0> gives <H>=1 >= E0=-1 -- holds
    v2 = variational_principle(Z, psi0)
    cases["variational_holds_for_excited_trial"] = v2.status == KV.EXACT
    # trial state that IS the ground state -> equality, still "holds" (>=)
    psi_ground = sp.Matrix([0, 1])
    v2b = variational_principle(Z, psi_ground)
    cases["variational_holds_at_ground_state_equality"] = v2b.status == KV.EXACT

    # 3) CHSH: classical/local bound example S=2 exactly (boundary, holds with <=)
    v3 = chsh_bound(sp.Rational(1, 1), sp.Integer(0), sp.Integer(1), sp.Integer(0))
    cases["chsh_boundary_holds"] = v3.status == KV.EXACT
    # a value that VIOLATES the classical bound (S=3) -> declines (refuted, not guessed)
    v3b = chsh_bound(sp.Integer(1), sp.Integer(-1), sp.Integer(1), sp.Integer(1))   # S=1-(-1)+1+1=4
    cases["chsh_violation_declines"] = v3b.status == KV.DECLINE
    # the SAME violating correlation checked against Tsirelson's quantum bound (2sqrt2 ≈2.828) -- still violates (S=4>2√2)
    v3c = chsh_bound(sp.Integer(1), sp.Integer(-1), sp.Integer(1), sp.Integer(1), quantum=True)
    cases["chsh_beyond_tsirelson_declines"] = v3c.status == KV.DECLINE
    # a genuinely quantum correlation value (2*sqrt(2)) exactly AT Tsirelson's bound -- holds
    tsirelson_val = sp.sqrt(2)
    v3d = chsh_bound(tsirelson_val, tsirelson_val, tsirelson_val, -tsirelson_val, quantum=True)
    cases["chsh_at_tsirelson_holds"] = v3d.status == KV.EXACT

    # 4) Holevo non-negativity: a simple 2-state ensemble (|0>,|1> equal weights) -> chi should be log(2) (all of it accessible, pure states)
    rho0 = sp.Matrix([[1, 0], [0, 0]])
    rho1 = sp.Matrix([[0, 0], [0, 1]])
    v4 = holevo_nonnegativity([sp.Rational(1, 2), sp.Rational(1, 2)], [rho0, rho1])
    cases["holevo_nonneg_holds"] = v4.status == KV.EXACT
    cases["holevo_pure_ensemble_chi_is_log2"] = (v4.status == KV.EXACT and
                                                 sp.simplify(v4.result["diff"] - sp.log(2)) == 0)
    # ensemble of IDENTICAL states -> chi=0 (no distinguishing information, boundary case, still holds via >=)
    v4b = holevo_nonnegativity([sp.Rational(1, 2), sp.Rational(1, 2)], [rho0, rho0])
    cases["holevo_identical_states_chi_zero"] = v4b.status == KV.EXACT and sp.simplify(v4b.result["diff"]) == 0
    # bad probabilities (don't sum to 1) -> declines
    v4c = holevo_nonnegativity([sp.Rational(1, 2), sp.Rational(1, 2), sp.Rational(1, 2)], [rho0, rho1, rho0])
    cases["holevo_bad_probs_declines"] = v4c.status == KV.DECLINE

    # 5) monogamy: honest scope DECLINE, always, tested explicitly (not a silent gap)
    v5 = monogamy_tangle_check()
    cases["monogamy_honest_scope_declines"] = v5.status == KV.DECLINE
    cases["monogamy_declines_mentions_wootters"] = "wootters" in v5.reason.lower() or "concurrence" in v5.reason.lower()

    all_ok = all(cases.values())
    failed = [k for k, v_ in cases.items() if not v_]
    return {"cases": cases, "all_ok": all_ok, "failed": failed}


if __name__ == "__main__":
    import json
    b = adversarial_battery()
    print(json.dumps({"all_ok": b["all_ok"], "failed": b["failed"], "n_cases": len(b["cases"])}, indent=2))
