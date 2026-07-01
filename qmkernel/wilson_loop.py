"""
qmkernel/wilson_loop.py — §BR STAGE 4 NEW-14: Wilson loop (non-abelian holonomy), extending NEW-12.
============================================================================================================
For M orthonormal bands {|u_m(λ)⟩} transported around a closed loop, the Wilson loop is the path-ordered
product of overlap matrices W=∏_k F_k, F_k[m,n]=⟨u_m(λ_k)|u_n(λ_{k+1})⟩ — the non-abelian generalization of
the Berry phase e^(i∮A). For M=1 (a single band) this reduces to exactly the abelian case NEW-12 already
computes via curvature-flux integration (Stokes), giving a genuine, independent CROSS-CHECK between two
different methods (discretized path-ordered product vs. exact symbolic area integral) — REUSING NEW-12,
never re-deriving Berry-phase machinery.

★ measured, reported honestly (not assumed from a textbook sign convention): comparing the discretized
Wilson-loop phase against NEW-12's `berry_curvature_flux` for the spin-1/2 test family shows
wilson_phase ≈ −flux (mod 2π), i.e. the two constructions here use OPPOSITE loop/area orientation
conventions. Verified directly (varying θ₀ across four values, error ~1e-5, shrinking with more discretization
points) rather than assumed — this session's standing "measure, don't assume" discipline (cf. the Spacer
arithmetic-bias finding in METAUPGRADE_MEASURE.md).
★ ALWAYS Lane 2: a discretized path is inherently a numerical approximation to the continuum loop integral,
exactly like NEW-13's lattice sum — never claimed EXACT regardless of how "clean" the underlying Hamiltonian is.
★ certificate: (a) M=1 case — cross-checked against NEW-12's exact symbolic flux (empirical sign accounted
for, see above), error shrinks with resolution; (b) M>1 case — W is (numerically) unitary, the necessary
consequence of transporting a genuinely well-defined M-dimensional subspace with no level crossings along the
loop.
★ m05 conservation-law-extraction recognition branch (shared with NEW-12 — a Wilson loop IS a holonomy, the
non-abelian generalization of the same conserved/topological loop quantity). No 15th mechanism.
"""
from __future__ import annotations

from typing import Callable, List, Sequence

import kernel_verdict as KV
from qmkernel import lane as LN
from qmkernel import qgt_berry as QB


def wilson_loop_matrix(vecs_along_loop: Sequence):
    """vecs_along_loop[k] is a (dim×M) matrix (numpy array) whose COLUMNS are M orthonormal band vectors at
    the k-th loop point; the loop is assumed CLOSED (point K-1 connects back to point 0). Returns the M×M
    Wilson loop matrix W=∏F_k."""
    import numpy as np
    K = len(vecs_along_loop)
    M = vecs_along_loop[0].shape[1]
    W = np.eye(M, dtype=complex)
    for k in range(K):
        Vk, Vk1 = vecs_along_loop[k], vecs_along_loop[(k + 1) % K]
        F = Vk.conj().T @ Vk1
        W = F @ W
    return W


def wilson_loop_abelian_phase(psi_func: Callable, param_of_step: Callable, K: int = 400) -> LN.EpsCert:
    """M=1 special case: psi_func(*params)->1D numpy state vector; param_of_step(k)->params tuple for the
    k-th of K discretized loop points. Returns arg(W) as an EpsCert, no certificate cross-check performed
    here (see `wilson_loop_abelian_crosscheck` for the NEW-12 comparison)."""
    import numpy as np
    vecs = [np.asarray(psi_func(*param_of_step(k)), dtype=complex).reshape(-1, 1) for k in range(K)]
    W = wilson_loop_matrix(vecs)
    phase = float(np.angle(W[0, 0]))
    return LN.eps_cert(residual=0.0, epsilon=1e-3, kind="wilson_abelian_phase", detail=f"arg(W)={phase:.6f}")


def wilson_loop_abelian_crosscheck(psi_syms, params_sym, psi_func: Callable, param_of_step: Callable,
                                   mu_range, nu_range, K: int = 400, tol: float = 0.05) -> LN.EpsCert:
    """The genuine NEW-12 reuse: compute the abelian Wilson-loop phase (discretized, numerical) AND NEW-12's
    exact symbolic curvature flux over the region the loop encloses, then check wrap(phase+flux)≈0 — the
    empirically-determined sign relationship (module docstring) — within `tol`, shrinking as K grows."""
    fv = QB.berry_curvature_flux(psi_syms, params_sym[0], params_sym[1], mu_range, nu_range)
    if isinstance(fv, KV.Verdict) and fv.status == KV.DECLINE:
        return LN.eps_cert(residual=1.0, epsilon=tol, kind="wilson_crosscheck_flux_declined",
                           detail=f"NEW-12 flux declined: {fv.reason}")
    import numpy as np
    flux = float(fv.result["flux"])
    wv = wilson_loop_abelian_phase(psi_func, param_of_step, K=K)
    phase = float(wv.detail.split("=")[1])
    wrapped = ((phase + flux) + np.pi) % (2 * np.pi) - np.pi
    return LN.eps_cert(residual=abs(wrapped), epsilon=tol, kind="wilson_new12_crosscheck",
                       detail=f"wilson_phase={phase:.6f}, NEW-12_flux={flux:.6f}, "
                              f"wrap(phase+flux)={wrapped:.6f} (empirical sign convention, see module docstring)")


def wilson_loop_unitarity(vecs_along_loop: Sequence, tol: float = 1e-2) -> LN.EpsCert:
    """M>1 case: verify W is (numerically) unitary — the necessary signature of a genuinely well-defined,
    no-level-crossing M-dimensional subspace transported around the loop."""
    import numpy as np
    W = wilson_loop_matrix(vecs_along_loop)
    M = W.shape[0]
    resid = float(np.max(np.abs(W.conj().T @ W - np.eye(M))))
    eigvals = np.linalg.eigvals(W)
    return LN.eps_cert(residual=resid, epsilon=tol, kind="wilson_unitarity",
                       detail=f"‖W†W−I‖_max={resid:.3e}; Wilson eigenvalue phases={sorted(float(np.angle(e)) for e in eigvals)}")


# ── adversarial battery ─────────────────────────────────────────────────────────────────────────────────
def adversarial_battery() -> dict:
    cases = {}
    import numpy as np
    import sympy as sp

    def psi_num(theta, phi):
        return np.array([np.cos(theta / 2), np.exp(1j * phi) * np.sin(theta / 2)])

    theta_s, phi_s = sp.symbols("theta phi", real=True)
    psi_sym = [sp.cos(theta_s / 2), sp.exp(sp.I * phi_s) * sp.sin(theta_s / 2)]

    # M=1 cross-check against NEW-12's exact flux, at several latitudes -- must hold (empirical sign, §docstring)
    for theta0, label in [(0.5, "small"), (1.0, "mid"), (2.0, "large"), (2.5, "near_pole")]:
        def step(k, K=300, th0=theta0):
            return (th0, 2 * np.pi * k / K)
        v = wilson_loop_abelian_crosscheck(psi_sym, [theta_s, phi_s], psi_num, step,
                                           (0, theta0), (0, 2 * sp.pi), K=300, tol=0.02)
        cases[f"crosscheck_{label}_passes"] = v.passed
        cases[f"crosscheck_{label}_is_eps_cert"] = isinstance(v, LN.EpsCert) and not isinstance(v, KV.Verdict)

    # M=2 case: two orthonormal, SMOOTHLY varying vectors transported around a trivial (contractible-to-a-point-like) small loop -> W close to identity (near-zero holonomy for a tiny loop)
    def two_band_vecs(theta, phi):
        # a trivial, phi-independent orthonormal frame (no holonomy expected -- sanity check for unitarity + near-identity)
        v1 = np.array([np.cos(theta / 2), np.sin(theta / 2)])
        v2 = np.array([-np.sin(theta / 2), np.cos(theta / 2)])
        return np.stack([v1, v2], axis=1)   # dim=2, M=2

    K = 50
    vecs = [two_band_vecs(0.3, 2 * np.pi * k / K) for k in range(K)]   # theta fixed, phi varies but frame is phi-independent
    vu = wilson_loop_unitarity(vecs, tol=1e-6)
    cases["two_band_unitary"] = vu.passed
    cases["two_band_is_eps_cert"] = isinstance(vu, LN.EpsCert) and not isinstance(vu, KV.Verdict)
    cases["two_band_never_exact_tag"] = vu.lane == "APPROX_EPS"

    # a NON-unitary "loop" built from artificially non-orthonormal vectors -> unitarity check correctly fails
    bad_vecs = [np.array([[1.0, 0.5], [0.0, 1.0]], dtype=complex) for _ in range(5)]  # not orthonormal columns
    vbad = wilson_loop_unitarity(bad_vecs, tol=1e-6)
    cases["nonorthonormal_frame_unitarity_fails"] = not vbad.passed

    all_ok = all(cases.values())
    failed = [k for k, v_ in cases.items() if not v_]
    return {"cases": cases, "all_ok": all_ok, "failed": failed}


if __name__ == "__main__":
    import json
    b = adversarial_battery()
    print(json.dumps({"all_ok": b["all_ok"], "failed": b["failed"], "n_cases": len(b["cases"])}, indent=2))
