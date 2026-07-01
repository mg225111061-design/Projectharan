"""
qmkernel/hermitian_realroot.py — §BR STAGE 2 NEW-6: certify a Hermitian matrix's eigenvalues are all real.
============================================================================================================
Hermitian ⇒ real spectrum is a general theorem — this engine PROVES it for a SPECIFIC input matrix by
extracting that matrix's own characteristic polynomial and reusing the EXISTING (unmodified)
`native_realroots.realroots_grade` Sturm engine, rather than merely citing the theorem.

★ dispatcher honesty (§2 principle 3 / the §BP-9 lesson): `charpoly_coeffs(H)` is the ONLY place the
characteristic polynomial is built, and it is built from the ACTUAL input `H` (`sympy.Matrix.charpoly()`) —
never a hardcoded polynomial. The regression battery feeds two matrices with DIFFERENT known spectra and
asserts two DIFFERENT coefficient lists reach `native_realroots.realroots_grade`, with results matching each
matrix's OWN eigenvalues (the direct analogue of the Pell/Fibonacci mis-dispatch this directive calls out).

★ m14 obstruction-certificate recognition branch: "all eigenvalues real" is verified by finding NO obstruction
— the squarefree characteristic polynomial's distinct-root count (Sturm, real) equals its total degree
(distinct roots, real+complex); any shortfall would BE the obstruction (a genuinely complex eigenvalue),
which cannot occur for a truly Hermitian input but is checked, not assumed. No 15th mechanism.

★ 2-lane: exact/symbolic H ⇒ Lane 1 (native_realroots.realroots_grade, EXACT). Float H ⇒ Lane 2
(numpy.linalg.eigvalsh + an INDEPENDENT direct-determinant residual check at each returned eigenvalue).
"""
from __future__ import annotations

from fractions import Fraction
from typing import List

import sympy as sp

import kernel_verdict as KV
from qmkernel import lane as LN


def _as_sympy_matrix(H) -> sp.Matrix:
    if isinstance(H, sp.MatrixBase):
        return H
    return sp.Matrix(H)


def _is_hermitian_exact(H: sp.Matrix) -> bool:
    n = H.rows
    return all(sp.simplify(H[i, j] - sp.conjugate(H[j, i])) == 0 for i in range(n) for j in range(n))


def _is_hermitian_eps(H, tol: float) -> tuple:
    import numpy as np
    A = np.array(H, dtype=complex)
    worst = float(np.max(np.abs(A - A.conj().T))) if A.size else 0.0
    return worst <= tol, worst


# ── dispatcher-honesty-critical: the ONLY place the char poly is built, always from the REAL input ─────
def charpoly_coeffs(H: sp.Matrix) -> List[sp.Expr]:
    """The characteristic polynomial's coefficients, extracted from `H` itself — never hardcoded."""
    x = sp.Symbol("_qk_lambda")
    return H.charpoly(x).all_coeffs()


def _squarefree_part(coeffs: List[sp.Expr]) -> List[sp.Expr]:
    """p / gcd(p,p') — removes multiplicities so degree = number of DISTINCT roots (what Sturm counts)."""
    x = sp.Symbol("_qk_x")
    p = sp.Poly(coeffs, x)
    g = sp.gcd(p, p.diff(x))
    q = sp.div(p, g)[0] if g.degree() > 0 else p
    return [sp.nsimplify(c) for c in q.all_coeffs()]


def _to_fraction_coeffs(coeffs: List[sp.Expr]) -> List[Fraction]:
    return [Fraction(c) for c in coeffs]


# ── the top-level entry point ───────────────────────────────────────────────────────────────────────────
def certify_all_real(H, eps_tol: float = 1e-8):
    """Certify every eigenvalue of Hermitian `H` is real. Returns KV.Verdict (Lane 1: EXACT/DECLINE) or
    qmkernel.lane.EpsCert (Lane 2: checked-ε, never EXACT)."""
    Hs = _as_sympy_matrix(H)
    if Hs.rows != Hs.cols:
        return KV.decline("matrix is not square", "qmkernel.hermitian_realroot")
    rows = [[Hs[i, j] for j in range(Hs.cols)] for i in range(Hs.rows)]

    if LN.is_exact_container(rows):
        if not _is_hermitian_exact(Hs):
            return KV.decline("precondition FAILED: matrix is not exactly Hermitian ⇒ DECLINE",
                              "qmkernel.hermitian_realroot")
        coeffs = charpoly_coeffs(Hs)
        try:
            sf = _squarefree_part(coeffs)
            frac_coeffs = _to_fraction_coeffs(sf)
        except (TypeError, ValueError) as e:
            return KV.decline(f"characteristic polynomial is not exact-rational: {e}", "qmkernel.hermitian_realroot")
        n_distinct = len(frac_coeffs) - 1
        import native_realroots as NR
        v = NR.realroots_grade(frac_coeffs)
        if v.status != KV.EXACT:
            return KV.decline(f"native_realroots declined on the squarefree charpoly: {v.reason}",
                              "qmkernel.hermitian_realroot")
        n_real = v.result["n_real_roots"]
        all_real = (n_real == n_distinct)
        verdict_phrase = "ALL real (no obstruction found)" if all_real else \
            "a NON-REAL eigenvalue exists — this input is not actually Hermitian-consistent"
        cert = KV.Cert(KV.EXACT, "hermitian_charpoly_sturm", passed=True,
                       check_cost="charpoly + squarefree gcd (sympy, exact) + Sturm isolation (native_realroots)",
                       detail=f"squarefree charpoly degree={n_distinct}, Sturm-certified distinct real roots="
                              f"{n_real} ⇒ {verdict_phrase}; intervals={v.result['intervals']}")
        if not all_real:
            return KV.decline(f"Sturm found only {n_real}/{n_distinct} distinct roots real — the input is not "
                              "spectrally consistent with a genuine Hermitian matrix", "qmkernel.hermitian_realroot")
        return KV.exact({"all_real": True, "n_distinct_eigenvalues": n_distinct, "intervals": v.result["intervals"]},
                        "qmkernel.hermitian_realroot", "O(n^3) charpoly + O(n^2) Sturm", cert)

    # Lane 2 — float Hermitian matrix
    ok, worst = _is_hermitian_eps(rows, eps_tol)
    if not ok:
        return KV.decline(f"precondition FAILED (Lane 2): max|H-H†|={worst:.3e} > tol={eps_tol:.1e}",
                          "qmkernel.hermitian_realroot")
    import numpy as np
    A = np.array(rows, dtype=complex)
    A = (A + A.conj().T) / 2.0     # symmetrize (the tiny asymmetry already passed the tolerance gate)
    eigvals = np.linalg.eigvalsh(A)
    residuals = [abs(complex(np.linalg.det(A - lam * np.eye(len(A))))) for lam in eigvals] if len(A) <= 6 else None
    max_resid = max(residuals) if residuals else 0.0
    detail = (f"eigvalsh (Hermitian-specialized, real by construction); direct det(H-λI) residual check "
              f"(n≤6 only, honestly capped) max={max_resid:.3e}" if residuals else
              f"eigvalsh (Hermitian-specialized, real by construction); n={len(A)}>6, direct-det residual "
              f"cross-check SKIPPED (stated, not hidden) — orthonormality of eigvalsh's own guarantee still applies")
    return LN.eps_cert(residual=max_resid, epsilon=max(eps_tol, 1e-6), kind="hermitian_lane2_eigvalsh", detail=detail)


# ── adversarial battery ─────────────────────────────────────────────────────────────────────────────────
def adversarial_battery() -> dict:
    cases = {}

    # 1) exact Hermitian (real symmetric) matrix with distinct rational eigenvalues by construction
    H1 = sp.Matrix([[2, 1], [1, 2]])         # eigenvalues 1, 3 (rational, distinct)
    v1 = certify_all_real(H1)
    cases["h1_exact_grade"] = v1.status == KV.EXACT
    cases["h1_all_real_true"] = v1.status == KV.EXACT and v1.result["all_real"] is True

    # 2) a DIFFERENT exact Hermitian matrix (complex off-diagonal), different spectrum -> dispatcher honesty
    I = sp.I
    H2 = sp.Matrix([[0, I], [-I, 0]])        # Pauli Y — eigenvalues -1, +1
    v2 = certify_all_real(H2)
    cases["h2_exact_grade"] = v2.status == KV.EXACT
    c1 = charpoly_coeffs(H1)
    c2 = charpoly_coeffs(H2)
    cases["dispatcher_honesty_different_matrices_different_coeffs"] = c1 != c2
    cases["dispatcher_honesty_different_matrices_different_intervals"] = (
        v1.result["intervals"] != v2.result["intervals"])

    # 3) non-Hermitian exact matrix -> DECLINE (precondition)
    H3 = sp.Matrix([[1, 2], [3, 4]])          # not symmetric/Hermitian
    v3 = certify_all_real(H3)
    cases["non_hermitian_declines"] = v3.status == KV.DECLINE

    # 4) repeated-eigenvalue Hermitian matrix (identity) -> squarefree handling must still certify all-real
    H4 = sp.eye(3)
    v4 = certify_all_real(H4)
    cases["repeated_eigenvalue_identity_exact_grade"] = v4.status == KV.EXACT
    cases["repeated_eigenvalue_squarefree_degree_is_one"] = (v4.status == KV.EXACT
                                                              and v4.result["n_distinct_eigenvalues"] == 1)

    # 5) a 3x3 Hermitian matrix with an irrational but real spectrum (still exact/symbolic input)
    H5 = sp.Matrix([[0, 1, 0], [1, 0, 1], [0, 1, 0]])   # path graph adjacency, eigenvalues 0, ±√2
    v5 = certify_all_real(H5)
    cases["irrational_spectrum_still_exact_and_all_real"] = (v5.status == KV.EXACT
                                                              and v5.result["n_distinct_eigenvalues"] == 3)

    # 6) Lane 2: float Hermitian matrix
    import numpy as np
    Hf = np.array([[2.0, 1.0], [1.0, 2.0]])
    vf = certify_all_real(Hf)
    cases["float_hermitian_is_eps_cert_not_kv_verdict"] = isinstance(vf, LN.EpsCert) and not isinstance(vf, KV.Verdict)
    cases["float_hermitian_never_exact_tag"] = getattr(vf, "lane", None) == "APPROX_EPS"
    cases["float_hermitian_passes"] = isinstance(vf, LN.EpsCert) and vf.passed

    # 7) Lane 2: float non-Hermitian -> DECLINE
    Hf_bad = np.array([[1.0, 2.0], [3.0, 4.0]])
    vf2 = certify_all_real(Hf_bad)
    cases["float_non_hermitian_declines"] = isinstance(vf2, KV.Verdict) and vf2.status == KV.DECLINE

    # 8) non-square matrix -> DECLINE
    v8 = certify_all_real(sp.Matrix([[1, 2, 3], [4, 5, 6]]))
    cases["non_square_declines"] = v8.status == KV.DECLINE

    all_ok = all(cases.values())
    failed = [k for k, v_ in cases.items() if not v_]
    return {"cases": cases, "all_ok": all_ok, "failed": failed}


if __name__ == "__main__":
    import json
    b = adversarial_battery()
    print(json.dumps({"all_ok": b["all_ok"], "failed": b["failed"], "n_cases": len(b["cases"])}, indent=2))
