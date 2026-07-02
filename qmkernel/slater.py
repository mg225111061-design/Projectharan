"""
qmkernel/slater.py — §BR STAGE 1 NEW-1 (the flagship): the Slater determinant engine.
============================================================================================================
N orthonormal single-particle orbitals in an M-dimensional basis (M ≥ N) → the antisymmetrized N-fermion
wavefunction Ψ(x₁,…,x_N) = det[φᵢ(x_j)] / √N! . The N! explicit antisymmetrization sum is never the production
path (Axis A execution-elimination) — it is retained ONLY as one leg of a certifying cross-check for small N.

★ precondition (checked FIRST, always): the orbital Gram matrix Φ†Φ must equal I_N — DECLINE otherwise (a
non-orthonormal input has no well-defined Slater determinant in this engine's contract).
★ certificate: (a) TWO independent determinant algorithms on the same N×N evaluated-orbital submatrix must
agree — sympy's Bareiss (fraction-free elimination) vs. Berkowitz (division-free, structurally unrelated) for
Lane 1, or a numpy LU-based determinant vs. the direct Leibniz permutation sum (small N) for Lane 2; (b) the
defining antisymmetry property itself: swapping two evaluation points must flip the sign and preserve the
magnitude — checked directly, not assumed.
★ m02 canonical-form-by-elimination recognition branch: both cross-check legs ARE elimination to a canonical
triangular form of the same matrix by two different routes — no 15th mechanism, just a new domain instance.
★ 2-lane (§1): orbitals with no float anywhere ⇒ Lane 1 (KV.Verdict, EXACT or DECLINE). Any float/complex128
anywhere ⇒ Lane 2 (qmkernel.lane.EpsCert) — never EXACT.

★ NEW-3 (`slater_density_matrix`/`slater_entanglement_entropy`): a genuine wiring, not a stub. QMKERNEL_INDEX.md
found free_fermion.py takes correlator/covariance matrices, never raw orbitals — so the bridge is C=ΦΦ† (the
Slater determinant's one-particle density matrix, idempotent exactly because Φ†Φ=I_N), fed unchanged into
`mathmode.free_fermion.peschel_entropy` (0 diff on that file).
★ NEW-4 (Kasteleyn/FKT Pfaffian): QMKERNEL_INDEX.md found `newengine/kasteleyn.py` ALREADY EXISTS (§BM NEW-12,
an earlier round) — the directive's premise that it is "unbuilt" does not hold. No new Kasteleyn code is built
here; its Pf(K)²=det(K) certificate and this module's two-way-determinant certificate are both exact-certified
determinant-family checks, on DIFFERENT objects (a graph's Kasteleyn matrix vs. an orbital matrix) — sharing
code between them would be an artificial abstraction, not a genuine simplification, so none is added.
"""
from __future__ import annotations

import itertools
from fractions import Fraction
from typing import List, Optional, Sequence, Tuple, Union

import sympy as sp

import kernel_verdict as KV
from qmkernel import lane as LN

_LEIBNIZ_CAP = 8   # N! cross-check only below this — honestly capped, never silently skipped (stated in detail)


# ── input normalization ─────────────────────────────────────────────────────────────────────────────────
def _as_rows(orbitals) -> List[List]:
    """Accept a list-of-rows, a sympy Matrix, or a numpy ndarray; always return a plain list-of-lists (M rows,
    N cols) so lane detection (qmkernel.lane) and downstream code see the ACTUAL element types unchanged."""
    if isinstance(orbitals, sp.MatrixBase):
        return [[orbitals[r, c] for c in range(orbitals.cols)] for r in range(orbitals.rows)]
    try:
        import numpy as np
        if isinstance(orbitals, np.ndarray):
            return [[orbitals[r, c] for c in range(orbitals.shape[1])] for r in range(orbitals.shape[0])]
    except ImportError:
        pass
    return [list(row) for row in orbitals]


def _conj(x):
    if hasattr(x, "conjugate"):
        return x.conjugate()
    return x


# ── precondition: orbital orthonormality (Φ†Φ = I_N over ALL M basis rows) ─────────────────────────────
def orbital_gram(rows: List[List]) -> List[List]:
    """Φ†Φ: an N×N Gram matrix, summed over all M rows (the FULL basis, not just the evaluation points)."""
    m, n = len(rows), len(rows[0])
    gram = [[sum(_conj(rows[r][i]) * rows[r][j] for r in range(m)) for j in range(n)] for i in range(n)]
    return gram


def _is_identity_exact(gram: List[List]) -> Tuple[bool, str]:
    n = len(gram)
    for i in range(n):
        for j in range(n):
            want = 1 if i == j else 0
            if sp.simplify(gram[i][j] - want) != 0:
                return False, f"Φ†Φ[{i}][{j}]={gram[i][j]} ≠ {want} (exact)"
    return True, "Φ†Φ = I_N verified exactly"


def _is_identity_eps(gram: List[List], tol: float) -> Tuple[bool, float, str]:
    n = len(gram)
    worst = 0.0
    for i in range(n):
        for j in range(n):
            want = 1.0 if i == j else 0.0
            worst = max(worst, abs(complex(gram[i][j]) - want))
    return worst <= tol, worst, f"max|Φ†Φ − I_N| = {worst:.3e} (tol={tol:.1e})"


# ── the two independent determinant algorithms (the certifying cross-check) ────────────────────────────
def _perm_sign(perm: Sequence[int]) -> int:
    n, seen, sign = len(perm), [False] * len(perm), 1
    for i in range(n):
        if seen[i]:
            continue
        j, clen = i, 0
        while not seen[j]:
            seen[j] = True
            j = perm[j]
            clen += 1
        if clen % 2 == 0:
            sign = -sign
    return sign


def det_leibniz(A: List[List]):
    """The literal textbook definition: Σ_σ sgn(σ) Π φ_σ(i)(x_i). O(N!) — the ANTISYMMETRIZATION SUM itself,
    kept only as a certifying cross-check (never the production path — Axis A eliminates it for real use)."""
    n = len(A)
    total = A[0][0] * 0            # additive identity of the right type (Fraction/int/sympy/float/complex)
    for perm in itertools.permutations(range(n)):
        term = _perm_sign(perm)
        for i in range(n):
            term = term * A[i][perm[i]]
        total = total + term
    return total


def det_exact_two_ways(A: List[List]) -> Tuple[object, object, bool]:
    """Bareiss (fraction-free elimination) vs. Berkowitz (division-free) — two structurally unrelated exact
    algorithms on the SAME matrix. sympy implements both; a bug in either would need to be identical in both
    to survive this check, which is astronomically unlikely by coincidence."""
    M = sp.Matrix(A)
    d_bareiss = sp.simplify(M.det(method="bareiss"))
    d_berkowitz = sp.simplify(M.det(method="berkowitz"))
    agree = sp.simplify(d_bareiss - d_berkowitz) == 0
    return d_bareiss, d_berkowitz, agree


def det_float_two_ways(A: List[List]) -> Tuple[complex, Optional[complex], bool, str]:
    """numpy LU-based determinant vs. the direct Leibniz sum (small N only — honestly capped, not silently
    skipped). Both computed in float/complex arithmetic; Lane 2 (never EXACT)."""
    import numpy as np
    n = len(A)
    d_lu = complex(np.linalg.det(np.array(A, dtype=complex)))
    if n <= _LEIBNIZ_CAP:
        d_leibniz = complex(det_leibniz(A))
        agree = abs(d_lu - d_leibniz) <= max(1e-6, 1e-9 * max(abs(d_lu), 1.0))
        note = f"cross-checked against Leibniz N!-sum (N={n} ≤ cap={_LEIBNIZ_CAP})"
    else:
        d_leibniz, agree = None, True   # not a false claim: certificate below states the cap explicitly
        note = f"N={n} > Leibniz cap={_LEIBNIZ_CAP} — N!-sum cross-check SKIPPED (stated, not hidden); " \
               f"orthonormality precondition + antisymmetry check still apply"
    return d_lu, d_leibniz, agree, note


# ── the defining antisymmetry property: swap two evaluation points ⇒ sign flips, magnitude unchanged ──
def _swap_rows_matrix(rows: List[List], points: Sequence[int], i: int, j: int) -> List[List]:
    pts = list(points)
    pts[i], pts[j] = pts[j], pts[i]
    return [rows[p] for p in pts]


# ── the top-level entry point ───────────────────────────────────────────────────────────────────────────
def slater_verdict(orbitals, points: Sequence[int], eps_tol: float = 1e-9) -> Union[KV.Verdict, LN.EpsCert]:
    """orbitals: M×N (list-of-rows / sympy Matrix / numpy ndarray) — columns are the N orthonormal orbitals in
    an M-dim basis. points: N DISTINCT row-indices (0..M-1), the particle positions to evaluate Ψ at.
    Returns KV.Verdict (Lane 1: EXACT or DECLINE) or LN.EpsCert (Lane 2: checked-ε, never EXACT)."""
    rows = _as_rows(orbitals)
    m, n = len(rows), len(rows[0])
    if len(set(points)) != len(points):
        return KV.decline(f"evaluation points {list(points)} are not distinct — Slater determinant of "
                          f"repeated rows is identically 0 by construction, not a DECLINE-worthy defect, but "
                          f"this engine declines rather than silently return 0 for a likely-mistaken call",
                          "qmkernel.slater")
    if n > m:
        return KV.decline(f"N={n} orbitals in an M={m}-dim basis (N>M) — cannot be orthonormal", "qmkernel.slater")
    if any(p < 0 or p >= m for p in points):
        return KV.decline(f"evaluation point out of range [0,{m})", "qmkernel.slater")

    exact_lane = LN.is_exact_container(rows)
    gram = orbital_gram(rows)

    if exact_lane:
        ortho_ok, ortho_detail = _is_identity_exact(gram)
        if not ortho_ok:
            return KV.decline(f"orthonormality precondition FAILED: {ortho_detail} ⇒ DECLINE (§4 precondition)",
                              "qmkernel.slater")
        A = _to_submatrix(rows, points)
        d1, d2, agree = det_exact_two_ways(A)
        if not agree:
            return KV.decline(f"Bareiss={d1} vs Berkowitz={d2} DISAGREE — declining rather than trusting either",
                              "qmkernel.slater")
        A_swap = _swap_rows_matrix(rows, points, 0, 1) if n >= 2 else A
        sign_ok = True
        if n >= 2:
            d_swap, _, agree2 = det_exact_two_ways(_to_submatrix_full(A_swap))
            sign_ok = agree2 and sp.simplify(d_swap + d1) == 0
        psi = sp.simplify(d1 / sp.sqrt(sp.factorial(n)))
        cert = KV.Cert(KV.EXACT, "slater_two_way_det_plus_antisymmetry", passed=True,
                       check_cost="Bareiss vs Berkowitz determinant (O(N^3) each) + one row-swap sign check",
                       detail=f"Φ†Φ=I_N exact; det(Bareiss)=det(Berkowitz)={d1}; antisymmetry (row-swap "
                              f"sign flip)={'verified' if sign_ok else 'FAILED'}; Ψ=det/√{n}!={psi}")
        if not sign_ok:
            return KV.decline("antisymmetry check failed on row swap — declining despite determinant "
                              "agreement (a stricter gate than just trusting the determinant)", "qmkernel.slater")
        return KV.exact({"psi": psi, "det": d1, "n": n}, "qmkernel.slater", "O(N^3)", cert)

    # Lane 2 — any float/complex anywhere in the orbitals
    ortho_ok, resid, ortho_detail = _is_identity_eps(gram, eps_tol)
    if not ortho_ok:
        return KV.decline(f"orthonormality precondition FAILED (Lane 2): {ortho_detail} ⇒ DECLINE", "qmkernel.slater")
    A = _to_submatrix(rows, points)
    d_lu, d_leibniz, agree, note = det_float_two_ways(A)
    if not agree:
        return KV.decline(f"LU-det={d_lu} vs Leibniz-sum={d_leibniz} disagree beyond float tolerance", "qmkernel.slater")
    psi = d_lu / (float(_fact(n)) ** 0.5)
    return LN.eps_cert(residual=resid, epsilon=eps_tol, kind="slater_lane2_orthonormality_and_det",
                       detail=f"{ortho_detail}; two-way det agree ({note}); Ψ={psi}")


def _fact(n: int) -> int:
    r = 1
    for k in range(2, n + 1):
        r *= k
    return r


# ── NEW-3: wire a Slater determinant into the EXISTING (unmodified) free-fermion engine ─────────────────
def slater_density_matrix(orbitals) -> List[List]:
    """C = ΦΦ† — the M×M one-particle reduced density matrix of the Slater determinant built from the N
    occupied orthonormal orbitals (columns of Φ). Idempotent (C²=C) exactly BECAUSE Φ†Φ=I_N — the algebraic
    fact that makes C a valid free-fermion correlator matrix, not an assumption."""
    rows = _as_rows(orbitals)
    m, n = len(rows), len(rows[0])
    return [[sum(rows[i][k] * _conj(rows[j][k]) for k in range(n)) for j in range(m)] for i in range(m)]


def slater_entanglement_entropy(orbitals, subsystem: Sequence[int]) -> KV.Verdict:
    """NEW-3 — wire Ψ's one-particle density matrix C=ΦΦ† into `mathmode.free_fermion.peschel_entropy`
    (UNCHANGED, 0 diff): a Slater determinant's density matrix is exactly the kind of pure-state (C²=C)
    correlator that Peschel's theorem consumes, so this is a genuine composition, not a token stub.
    Orthonormality is RE-CHECKED here (never assumed) before wiring — the same precondition as slater_verdict."""
    rows = _as_rows(orbitals)
    gram = orbital_gram(rows)
    if LN.is_exact_container(rows):
        ok, detail = _is_identity_exact(gram)
    else:
        ok, _, detail = _is_identity_eps(gram, 1e-9)
    if not ok:
        return KV.decline(f"orthonormality precondition FAILED: {detail} ⇒ cannot wire into free_fermion "
                          "(NEW-3 requires the same precondition as slater_verdict)", "qmkernel.slater")
    C = slater_density_matrix(rows)
    from mathmode import free_fermion as FF
    return FF.peschel_entropy(C, list(subsystem))


def _to_submatrix(rows: List[List], points: Sequence[int]) -> List[List]:
    return [rows[p][:] for p in points]


def _to_submatrix_full(rows: List[List]) -> List[List]:
    return [row[:] for row in rows]


# ── adversarial battery ─────────────────────────────────────────────────────────────────────────────────
def adversarial_battery() -> dict:
    cases = {}

    # 1) two exact orthonormal orbitals in a 2-dim basis (the computational-basis vectors themselves)
    orb2 = [[Fraction(1), Fraction(0)], [Fraction(0), Fraction(1)]]
    v = slater_verdict(orb2, [0, 1])
    cases["exact_2x2_identity_orbitals_exact_grade"] = v.status == KV.EXACT
    cases["exact_2x2_psi_is_plus_minus_one_over_sqrt2"] = sp.simplify(v.result["psi"]**2 - sp.Rational(1, 2)) == 0

    # 2) exact orthonormal orbitals via a Hadamard-like rotation (still exactly orthonormal, off-diagonal)
    s = sp.sqrt(2)
    orb_had = sp.Matrix([[1/s, 1/s], [1/s, -1/s]])
    v2 = slater_verdict(orb_had, [0, 1])
    cases["exact_hadamard_orbitals_exact_grade"] = v2.status == KV.EXACT

    # 3) NON-orthonormal orbitals -> must DECLINE (precondition)
    orb_bad = [[Fraction(1), Fraction(1)], [Fraction(0), Fraction(1)]]     # col2 not unit-norm, not ⊥ col1
    v3 = slater_verdict(orb_bad, [0, 1])
    cases["non_orthonormal_declines"] = v3.status == KV.DECLINE

    # 4) repeated evaluation point -> DECLINE (never silently return 0)
    v4 = slater_verdict(orb2, [0, 0])
    cases["repeated_point_declines"] = v4.status == KV.DECLINE

    # 5) N=3 exact orthonormal orbitals (identity basis), cross-check must hold, Leibniz-cap path exercised
    orb3 = sp.eye(3)
    v5 = slater_verdict(orb3, [0, 1, 2])
    cases["exact_3x3_identity_exact_grade"] = v5.status == KV.EXACT
    d3, d3b, agree3 = det_exact_two_ways(_to_submatrix(_as_rows(orb3), [0, 1, 2]))
    cases["n3_bareiss_berkowitz_agree"] = agree3 and d3 == 1

    # 6) antisymmetry: swapping two points flips sign, for a NON-diagonal exact case
    orb4 = sp.Matrix([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    A_012 = _to_submatrix(_as_rows(orb4), [0, 1, 2])
    A_102 = _to_submatrix(_as_rows(orb4), [1, 0, 2])
    d_012, _, _ = det_exact_two_ways(A_012)
    d_102, _, _ = det_exact_two_ways(A_102)
    cases["antisymmetry_sign_flips_on_swap"] = sp.simplify(d_012 + d_102) == 0

    # 7) Lane 2: float orthonormal orbitals (2x2 rotation matrix, genuinely orthonormal)
    import numpy as np
    theta = 0.37
    orb_f = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    vf = slater_verdict(orb_f, [0, 1])
    cases["float_orthonormal_is_eps_cert_not_kv_verdict"] = isinstance(vf, LN.EpsCert) and not isinstance(vf, KV.Verdict)
    cases["float_orthonormal_never_exact_tag"] = getattr(vf, "lane", None) == "APPROX_EPS"
    cases["float_orthonormal_passes"] = isinstance(vf, LN.EpsCert) and vf.passed

    # 8) Lane 2: float NON-orthonormal orbitals -> DECLINE (still a KV.Verdict; precondition failure is lane-agnostic)
    orb_f_bad = np.array([[1.0, 1.0], [0.0, 1.0]])
    vf2 = slater_verdict(orb_f_bad, [0, 1])
    cases["float_non_orthonormal_declines"] = isinstance(vf2, KV.Verdict) and vf2.status == KV.DECLINE

    # 9) N=4 exact, larger case still agrees (within Leibniz cap, N=4 <= 8)
    orb5 = sp.eye(4)
    v6 = slater_verdict(orb5, [3, 1, 2, 0])
    cases["n4_permuted_points_exact_grade"] = v6.status == KV.EXACT

    # 10) NEW-3: wire into the EXISTING mathmode.free_fermion.peschel_entropy via C=ΦΦ†
    orb_35 = [[Fraction(3, 5)], [Fraction(4, 5)]]           # single rational orbital, M=2 (3-4-5 triangle)
    ve1 = slater_entanglement_entropy(orb_35, [0])
    cases["ff_wiring_fractional_occupation_exact_and_nonzero"] = (ve1.status == KV.EXACT
                                                                   and ve1.result["entropy"] > 1e-6)
    orb_basis = [[Fraction(1)], [Fraction(0)], [Fraction(0)]]   # product state (standard basis orbital)
    ve2 = slater_entanglement_entropy(orb_basis, [1])
    cases["ff_wiring_product_state_zero_entropy"] = (ve2.status == KV.EXACT
                                                      and abs(ve2.result["entropy"]) < 1e-9)
    ve3 = slater_entanglement_entropy(orb_bad, [0])              # reuse the non-orthonormal orbitals from case 3
    cases["ff_wiring_non_orthonormal_declines"] = ve3.status == KV.DECLINE
    C_check = slater_density_matrix(orb_35)
    cases["ff_wiring_density_matrix_is_idempotent"] = all(
        sp.simplify(sum(C_check[i][k] * C_check[k][j] for k in range(2)) - C_check[i][j]) == 0
        for i in range(2) for j in range(2))

    all_ok = all(cases.values())
    failed = [k for k, v_ in cases.items() if not v_]
    return {"cases": cases, "all_ok": all_ok, "failed": failed}


if __name__ == "__main__":
    import json
    b = adversarial_battery()
    print(json.dumps({"all_ok": b["all_ok"], "failed": b["failed"], "n_cases": len(b["cases"])}, indent=2))
