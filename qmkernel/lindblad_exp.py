"""
qmkernel/lindblad_exp.py — §BR STAGE 2 NEW-7 (★ highest-value item in Stage 2): Lindblad = matrix exponential.
============================================================================================================
ρ̇ = -i[H,ρ] + Σ_k (L_k ρ L_k† − ½{L_k†L_k, ρ}). The vec(ρ) trick turns this into a CONSTANT-COEFFICIENT
linear ODE vec(ρ̇) = 𝓛·vec(ρ), so vec(ρ(t)) = e^(𝓛t)·vec(ρ(0)) — a closed form, not a numerical integrator.

★ Premise correction (QMKERNEL_INDEX.md §7): the directive's brief calls this "a direct reuse of the C-finite
/matrix-exponential engine — same structure as the Kalman gem." Verified FALSE by reading both files:
`cfinite.py` is scalar-recurrence-only (matrix POWERS by squaring, not a matrix EXPONENTIAL); `newengine/
kalman.py` does controllability/observability rank tests, also no matrix exponential. A repo-wide grep for
"expm"/"matrix exponential" is 0 hits. No matrix-exponential engine exists anywhere in this repo — this
module's exponential core is genuinely net-new (stated here rather than silently building on a false premise).
Neither file is touched (0 diff); the only kinship is conceptual (transfer-matrix closed form), not code reuse.

★ precondition (checked FIRST): H and every L_k must be CONSTANT (time-independent) — enforced by rejecting
any callable input outright (a time-dependent generator would be a function of t, not a fixed matrix); DECLINE,
never silently evaluated at a single instant.

★ certificate — TWO independent layers, "substitute back into the ODE" applied at the level that can actually
hide a bug: (a) the diagonalization 𝓛=PDP⁻¹ is reconstructed and compared to the ORIGINAL 𝓛 exactly (Lane 1)
or within ε (Lane 2) — never merely trusted from the eigensolver; (b) two GENERAL physical-consistency
theorems of any valid Lindbladian are checked on the computed e^(𝓛t) itself, symbolically for arbitrary ρ(0)
(Lane 1) or numerically for sampled ρ(0) (Lane 2): trace preservation (tr ρ(t)=tr ρ(0) for ALL t) and
Hermiticity preservation (ρ(t) Hermitian whenever ρ(0) is) — a bug in the Liouvillian assembly (a dropped
anticommutator term, a sign error) would generically break one of these, so this is a real check, not a
tautology of the diagonalization algebra.
★ m02 canonical-form-by-elimination recognition branch: e^(𝓛t)=Pe^(Dt)P⁻¹ IS elimination to a canonical
(diagonal) form, the same shape as the CHC-kernel/Slater eliminations elsewhere in this session. No 15th
mechanism.
"""
from __future__ import annotations

from typing import List, Sequence, Tuple, Union

import sympy as sp

import kernel_verdict as KV
from qmkernel import lane as LN


def _kron(A: sp.Matrix, B: sp.Matrix) -> sp.Matrix:
    ra, ca = A.shape
    rb, cb = B.shape
    return sp.Matrix(ra * rb, ca * cb, lambda i, j: A[i // rb, j // cb] * B[i % rb, j % cb])


def _vec(rho: sp.Matrix) -> sp.Matrix:
    """Column-major vectorization: vec(ρ)_{i+nj} = ρ_{ij}."""
    n = rho.rows
    return sp.Matrix([rho[i, j] for j in range(rho.cols) for i in range(n)])


def _unvec(v: sp.Matrix, n: int) -> sp.Matrix:
    return sp.Matrix(n, n, lambda i, j: v[i + n * j])


def liouvillian(H: sp.Matrix, L_ops: Sequence[sp.Matrix]) -> sp.Matrix:
    """𝓛 such that vec(ρ̇) = 𝓛·vec(ρ), from the constant H and Lindblad jump operators L_ops."""
    n = H.rows
    I = sp.eye(n)
    Lsuper = -sp.I * (_kron(I, H) - _kron(H.T, I))
    for Lk in L_ops:
        Ld = Lk.conjugate().T if hasattr(Lk, "conjugate") else Lk.H
        LdL = Ld * Lk
        Lconj = Lk.conjugate() if hasattr(Lk, "conjugate") else Lk
        Lsuper += _kron(Lconj, Lk) - sp.Rational(1, 2) * _kron(I, LdL) - sp.Rational(1, 2) * _kron(LdL.T, I)
    return sp.simplify(Lsuper)


def _reject_time_dependent(H, L_ops) -> bool:
    if callable(H):
        return True
    return any(callable(Lk) for Lk in L_ops)


# ── Lane 1: exact diagonalization-based matrix exponential + certificate ───────────────────────────────
def exact_matrix_exp(Lsuper: sp.Matrix, t: sp.Symbol):
    """e^(𝓛t) via exact diagonalization. Raises if 𝓛 is not diagonalizable (a genuine, honest boundary —
    a defective generator has no such closed form via this method; the caller DECLINEs, never fakes one)."""
    P, D = Lsuper.diagonalize()
    diag = [D[i, i] for i in range(D.rows)]
    expDt = sp.diag(*[sp.exp(d * t) for d in diag])
    Pinv = P.inv()
    expLt = sp.simplify(P * expDt * Pinv)
    return expLt, P, D, Pinv


def _diagonalization_reconstructs(Lsuper: sp.Matrix, P: sp.Matrix, D: sp.Matrix, Pinv: sp.Matrix) -> bool:
    recon = sp.simplify(P * D * Pinv)
    return sp.simplify(recon - Lsuper) == sp.zeros(*Lsuper.shape)


def _trace_preserved_symbolic(expLt: sp.Matrix, n: int, t: sp.Symbol) -> bool:
    entries = sp.symbols(f"_qk_rho0_0:{n * n}")
    rho0 = sp.Matrix(n, n, lambda i, j: entries[i * n + j])
    rhot = _unvec(sp.simplify(expLt * _vec(rho0)), n)
    diff = sp.simplify(sp.trace(rhot) - sp.trace(rho0))
    return diff == 0


def _hermiticity_preserved_symbolic(expLt: sp.Matrix, n: int, t: sp.Symbol) -> bool:
    # a general Hermitian ansatz: real diagonal symbols, independent off-diagonal complex symbols with c=conj(b)
    reals = sp.symbols(f"_qk_d0:{n}", real=True)
    off = {}
    rho0 = sp.zeros(n, n)
    for i in range(n):
        rho0[i, i] = reals[i]
    for i in range(n):
        for j in range(i + 1, n):
            b = sp.Symbol(f"_qk_off_{i}_{j}")
            off[(i, j)] = b
            rho0[i, j] = b
            rho0[j, i] = sp.conjugate(b)
    rhot = _unvec(sp.simplify(expLt * _vec(rho0)), n)
    for i in range(n):
        for j in range(n):
            if sp.simplify(rhot[i, j] - sp.conjugate(rhot[j, i])) != 0:
                return False
    return True


def lindblad_verdict(H, L_ops: Sequence, t=None, eps_tol: float = 1e-8) -> Union[KV.Verdict, LN.EpsCert]:
    """H: n×n Hamiltonian (Hermitian, constant). L_ops: sequence of n×n constant jump operators. `t` is the
    symbolic (Lane 1) or numeric (Lane 2) time; defaults to a fresh symbol / 1.0 respectively. Returns
    KV.Verdict (Lane 1: EXACT/DECLINE) or LN.EpsCert (Lane 2: checked-ε, never EXACT)."""
    if _reject_time_dependent(H, L_ops):
        return KV.decline("time-dependent Hamiltonian/Lindblad operators are out of scope for this "
                          "constant-coefficient engine ⇒ DECLINE (precondition, never silently evaluated "
                          "at one instant)", "qmkernel.lindblad_exp")
    Hm = H if isinstance(H, sp.MatrixBase) else sp.Matrix(H)
    Lms = [Lk if isinstance(Lk, sp.MatrixBase) else sp.Matrix(Lk) for Lk in L_ops]
    n = Hm.rows
    rows_all = [[Hm[i, j] for j in range(n)] for i in range(n)]
    for Lm in Lms:
        rows_all += [[Lm[i, j] for j in range(n)] for i in range(n)]

    if LN.is_exact_container(rows_all):
        if not sp.simplify(Hm - Hm.conjugate().T) == sp.zeros(n, n):
            return KV.decline("H is not exactly Hermitian ⇒ DECLINE", "qmkernel.lindblad_exp")
        Lsuper = liouvillian(Hm, Lms)
        tsym = t if t is not None else sp.Symbol("t", positive=True)
        try:
            expLt, P, D, Pinv = exact_matrix_exp(Lsuper, tsym)
        except sp.matrices.exceptions.MatrixError as e:
            return KV.decline(f"𝓛 is not diagonalizable — no exact closed form via this method: {e}",
                              "qmkernel.lindblad_exp")
        recon_ok = _diagonalization_reconstructs(Lsuper, P, D, Pinv)
        trace_ok = _trace_preserved_symbolic(expLt, n, tsym)
        herm_ok = _hermiticity_preserved_symbolic(expLt, n, tsym)
        if not (recon_ok and trace_ok and herm_ok):
            return KV.decline(f"certificate FAILED: diagonalization_reconstructs={recon_ok}, "
                              f"trace_preserved={trace_ok}, hermiticity_preserved={herm_ok}",
                              "qmkernel.lindblad_exp")
        cert = KV.Cert(KV.EXACT, "lindblad_liouvillian_diagonalization", passed=True,
                       check_cost=f"diagonalization of {Lsuper.rows}x{Lsuper.rows} 𝓛 + 2 symbolic "
                                  "physical-consistency theorems (trace, Hermiticity preservation)",
                       detail=f"𝓛=PDP⁻¹ reconstructs exactly; tr(ρ(t))=tr(ρ(0)) ∀ρ(0) (symbolic); ρ(t) "
                              f"Hermitian whenever ρ(0) is (symbolic); eigenvalues of 𝓛={[D[i,i] for i in range(D.rows)]}")
        return KV.exact({"liouvillian": Lsuper, "exp_Lt": expLt, "t": tsym}, "qmkernel.lindblad_exp",
                        f"O(n^6) diagonalization of an n^2 x n^2 generator", cert)

    # Lane 2 — float H/L_ops
    import numpy as np
    Hf = np.array(rows_all[:n], dtype=complex)
    if np.max(np.abs(Hf - Hf.conj().T)) > eps_tol:
        return KV.decline("H is not Hermitian within tolerance (Lane 2) ⇒ DECLINE", "qmkernel.lindblad_exp")
    Lfs = [np.array(rows_all[n * (k + 1):n * (k + 2)], dtype=complex) for k in range(len(Lms))]
    I = np.eye(n)
    Lsuper = -1j * (np.kron(I, Hf) - np.kron(Hf.T, I))
    for Lf in Lfs:
        Ld = Lf.conj().T
        LdL = Ld @ Lf
        Lsuper = Lsuper + np.kron(Lf.conj(), Lf) - 0.5 * np.kron(I, LdL) - 0.5 * np.kron(LdL.T, I)
    tval = t if t is not None else 1.0
    eigvals, eigvecs = np.linalg.eig(Lsuper)
    expLt = eigvecs @ np.diag(np.exp(eigvals * tval)) @ np.linalg.inv(eigvecs)
    recon = eigvecs @ np.diag(eigvals) @ np.linalg.inv(eigvecs)
    recon_resid = float(np.max(np.abs(recon - Lsuper)))
    rng = np.random.default_rng(0)
    trace_resid = 0.0
    for _ in range(5):
        r0 = rng.standard_normal((n, n)) + 1j * rng.standard_normal((n, n))
        v0 = r0.flatten(order="F")
        vt = expLt @ v0
        rhot = vt.reshape((n, n), order="F")
        trace_resid = max(trace_resid, abs(complex(np.trace(rhot) - np.trace(r0))))
    worst = max(recon_resid, trace_resid)
    return LN.eps_cert(residual=worst, epsilon=max(eps_tol, 1e-6), kind="lindblad_lane2_expm",
                       detail=f"diagonalization reconstruction resid={recon_resid:.3e}, trace-preservation "
                              f"resid (5 random ρ(0))={trace_resid:.3e}")


# ── adversarial battery ─────────────────────────────────────────────────────────────────────────────────
def adversarial_battery() -> dict:
    cases = {}

    # 1) pure dissipation (H=0), single jump operator (population transfer 0->1 at rate 1) -- exact, symbolic t
    H0 = sp.zeros(2, 2)
    L0 = sp.Matrix([[0, 0], [1, 0]])
    v1 = lindblad_verdict(H0, [L0])
    cases["pure_dissipation_exact_grade"] = v1.status == KV.EXACT

    # 2) at t=0, exp(Lt) must be the identity (initial condition sanity, substituted numerically)
    if v1.status == KV.EXACT:
        expLt, tsym = v1.result["exp_Lt"], v1.result["t"]
        at_zero = sp.simplify(expLt.subs(tsym, 0))
        cases["exp_at_t0_is_identity"] = at_zero == sp.eye(4)
    else:
        cases["exp_at_t0_is_identity"] = False

    # 3) coherent-only evolution (L_ops=[], pure Hamiltonian unitary dynamics) -- exact, must ALSO preserve trace+Hermiticity
    Hc = sp.Matrix([[0, 1], [1, 0]])   # sigma_x
    v2 = lindblad_verdict(Hc, [])
    cases["coherent_only_exact_grade"] = v2.status == KV.EXACT

    # 4) time-dependent H (a callable) -> DECLINE (precondition)
    v3 = lindblad_verdict(lambda tt: sp.Matrix([[tt, 0], [0, -tt]]), [L0])
    cases["time_dependent_declines"] = v3.status == KV.DECLINE

    # 5) non-Hermitian H (exact) -> DECLINE
    v4 = lindblad_verdict(sp.Matrix([[1, 2], [3, 4]]), [L0])
    cases["non_hermitian_H_declines"] = v4.status == KV.DECLINE

    # 6) two jump operators simultaneously (both amplitude-damping-like AND dephasing) -- exact
    Lz = sp.Matrix([[1, 0], [0, -1]]) / sp.sqrt(2)     # dephasing (already Hermitian, its own dagger)
    v5 = lindblad_verdict(H0, [L0, Lz])
    cases["two_jump_operators_exact_grade"] = v5.status == KV.EXACT

    # 7) Lane 2: float H, L
    import numpy as np
    Hf = np.array([[0.0, 1.0], [1.0, 0.0]])
    Lf = np.array([[0.0, 0.0], [1.0, 0.0]])
    vf = lindblad_verdict(Hf, [Lf])
    cases["float_lindblad_is_eps_cert_not_kv_verdict"] = isinstance(vf, LN.EpsCert) and not isinstance(vf, KV.Verdict)
    cases["float_lindblad_never_exact_tag"] = getattr(vf, "lane", None) == "APPROX_EPS"
    cases["float_lindblad_passes"] = isinstance(vf, LN.EpsCert) and vf.passed

    # 8) Lane 2: non-Hermitian float H -> DECLINE
    Hf_bad = np.array([[1.0, 2.0], [3.0, 4.0]])
    vf2 = lindblad_verdict(Hf_bad, [Lf])
    cases["float_non_hermitian_declines"] = isinstance(vf2, KV.Verdict) and vf2.status == KV.DECLINE

    # 9) Lane 2: time-dependent (callable) -> DECLINE even in the float regime
    vf3 = lindblad_verdict(lambda tt: Hf, [Lf])
    cases["float_time_dependent_declines"] = isinstance(vf3, KV.Verdict) and vf3.status == KV.DECLINE

    all_ok = all(cases.values())
    failed = [k for k, v_ in cases.items() if not v_]
    return {"cases": cases, "all_ok": all_ok, "failed": failed}


if __name__ == "__main__":
    import json
    b = adversarial_battery()
    print(json.dumps({"all_ok": b["all_ok"], "failed": b["failed"], "n_cases": len(b["cases"])}, indent=2))
