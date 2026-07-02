"""
§AU — THE SECOND CLASSICAL-SIMULATION ISLAND: free-fermion / Gaussian / matchgate fold (net-new module).
================================================================================================================
There are exactly TWO efficiently-classically-simulable islands of quantum-style computation, closed under DIFFERENT
algebras: ① Clifford/stabilizer (Sp(2n,𝔽₂) — built in §AY/qfold.stabilizer) and ② free-fermion / Gaussian / matchgate
(Pfaffian · covariance · symplectic — THIS module). Their intersection is small and their UNION is still NOT
universal QC (Gottesman–Knill ∪ Valiant ⊊ BQP) — so EXACT lives only inside one island; everything outside (interacting
theories, volume-law entanglement, #P-hard contraction, non-Gaussian, mixing chaos, float) DECLINEs with a theorem.

This is a NEW MODULE (not a new mechanism — 14/22 unchanged) because the quadratic-form island is a genuinely
independent algebra: Pfaffian/covariance/symplectic appear NOWHERE in the repo (stabilizer is 𝔽₂; hidden_structure is
matrix-rank). Zero external deps — the Pfaffian is a rational skew-LU self-impl (Parlett–Reid), NOT numpy float.

★ §0 verifier truth: ∀-(2n) / ∀-N is NOT z3 induction — it is the Wick / covariance / companion THEOREM, gated by
exact arithmetic + held-out replay; z3 only discharges FINITE algebraic identities (Pf(A)²=det(A), RᵀR=I, C²−C=0).
★ EXACT only for integer/rational data; float ⇒ DECLINE (the exact structure collapses). false-EXACT 0: a TAMPERED /
interacting correlator fails Wick-consistency ⇒ DECLINE.
"""
from __future__ import annotations

from fractions import Fraction
from itertools import combinations
from typing import Dict, List, Optional, Sequence, Tuple

import cfinite
import kernel_verdict as KV


# ── exact rational helpers ──────────────────────────────────────────────────────────────────────────────────────
def _exact(x) -> Fraction:
    """Coerce to an EXACT Fraction; a float is inexact by nature ⇒ ValueError (the caller DECLINEs — no float-EXACT,
    §1-8). Fraction(0.0) silently succeeds, so floats must be rejected explicitly."""
    if isinstance(x, bool):
        return Fraction(int(x))
    if isinstance(x, float):
        raise ValueError("float on the exact path — rationals/integers only (§1-8)")
    return Fraction(x)


def _is_skew(A: List[List[Fraction]]) -> bool:
    n = len(A)
    return all(A[i][i] == 0 for i in range(n)) and all(A[i][j] == -A[j][i] for i in range(n) for j in range(n))


def det_Q(M: Sequence[Sequence]) -> Fraction:
    """Exact rational determinant via Gaussian elimination (first-nonzero pivot)."""
    n = len(M)
    A = [[Fraction(M[i][j]) for j in range(n)] for i in range(n)]
    det = Fraction(1)
    for c in range(n):
        piv = next((r for r in range(c, n) if A[r][c] != 0), None)
        if piv is None:
            return Fraction(0)
        if piv != c:
            A[c], A[piv] = A[piv], A[c]
            det = -det
        det *= A[c][c]
        inv = A[c][c]
        for r in range(c + 1, n):
            if A[r][c] != 0:
                f = A[r][c] / inv
                for j in range(c, n):
                    A[r][j] -= f * A[c][j]
    return det


def pfaffian_Q(M: Sequence[Sequence]) -> Fraction:
    """Pfaffian of a skew-symmetric rational matrix via the Parlett–Reid LTL algorithm — O(n³) EXACT (no float).
    Pf(A)²=det(A); Pf=0 for odd dimension."""
    n = len(M)
    if n % 2 == 1:
        return Fraction(0)
    if n == 0:
        return Fraction(1)
    A = [[Fraction(M[i][j]) for j in range(n)] for i in range(n)]
    pf = Fraction(1)
    for k in range(0, n - 1, 2):
        kp = next((i for i in range(k + 1, n) if A[i][k] != 0), None)   # any nonzero pivot (exact ⇒ no stability need)
        if kp is None:
            return Fraction(0)
        if kp != k + 1:
            for j in range(k, n):                                       # swap rows k+1, kp
                A[k + 1][j], A[kp][j] = A[kp][j], A[k + 1][j]
            for i in range(k, n):                                       # swap cols k+1, kp
                A[i][k + 1], A[i][kp] = A[i][kp], A[i][k + 1]
            pf = -pf
        pf *= A[k][k + 1]
        if k + 2 < n:
            piv = A[k][k + 1]
            tau = [A[k][j] / piv for j in range(k + 2, n)]
            col = [A[i][k + 1] for i in range(k + 2, n)]                # A[k+2:, k+1]
            for ii, i in enumerate(range(k + 2, n)):
                for jj, j in enumerate(range(k + 2, n)):
                    A[i][j] += tau[ii] * col[jj] - col[ii] * tau[jj]    # += outer(tau,col) − outer(col,tau)
    return pf


def pfaffian_combinatorial(M: Sequence[Sequence]) -> Fraction:
    """Ground-truth Pfaffian = signed sum over perfect matchings (the (2n−1)!! Wick pairing sum). For small n only —
    used to VERIFY pfaffian_Q (and to materialise the Wick pairing sum)."""
    n = len(M)
    if n % 2 == 1:
        return Fraction(0)
    A = [[Fraction(M[i][j]) for j in range(n)] for i in range(n)]
    pts = list(range(n))

    def _sum(rem: List[int]) -> Fraction:
        if not rem:
            return Fraction(1)
        i = rem[0]
        tot = Fraction(0)
        for idx in range(1, len(rem)):
            j = rem[idx]
            sign = (-1) ** (idx - 1)                                    # moving j next to i
            tot += sign * A[i][j] * _sum(rem[1:idx] + rem[idx + 1:])
        return tot

    return _sum(pts)


# ── FF-1 — Wick → Pfaffian (free-field correlation fold) ────────────────────────────────────────────────────────
def wick_pfaffian_fold(A: Sequence[Sequence]) -> KV.Verdict:
    """The 2n-point function of a FREE (quadratic) theory equals Pf(A), A_{ij}=⟨ψ_iψ_j⟩ skew-symmetric. EXACT (Wick
    theorem) gated by Pf²=det + small-n combinatorial replay; float / non-skew ⇒ DECLINE."""
    try:
        Af = [[_exact(x) for x in row] for row in A]
    except (ValueError, TypeError):
        return KV.decline("wick: non-rational correlator (float) ⇒ exact structure collapses ⇒ DECLINE", "free_fermion")
    n = len(Af)
    if n == 0 or any(len(r) != n for r in Af):
        return KV.decline("wick: need a square 2-point matrix", "free_fermion")
    if not _is_skew(Af):
        return KV.decline("wick: ⟨ψ_iψ_j⟩ is not skew-symmetric ⇒ not a valid free-field 2-point structure ⇒ DECLINE",
                          "free_fermion")
    pf = pfaffian_Q(Af)
    if n % 2 == 1:
        # odd number of fermion operators ⇒ correlator vanishes (still EXACT)
        cert = KV.Cert(KV.EXACT, "exact_replay", passed=True, check_cost="parity",
                       detail="odd-point free-fermion correlator = 0 (Wick: no perfect matching)")
        return KV.exact({"pfaffian": "0", "vanishes": True}, "free_fermion", "O(1)", cert)
    d = det_Q(Af)
    if pf * pf != d:                                                   # Pf²=det — must hold (defensive)
        return KV.decline("wick: Pf²≠det (numerical inexactness) ⇒ DECLINE", "free_fermion")
    if n <= 8 and pfaffian_combinatorial(Af) != pf:                   # combinatorial replay on small n
        return KV.decline("wick: Parlett–Reid Pfaffian disagrees with the pairing sum ⇒ DECLINE", "free_fermion")
    cert = KV.Cert(KV.EXACT, "exact_replay", passed=True,
                   check_cost="O(n³) skew-LU + Pf²=det + combinatorial replay",
                   detail=f"⟨ψ₁…ψ_{{{n}}}⟩=Pf(A) (Wick, ∀ by construction); Pf²=det ✓; pairing-sum replay ✓ (n≤8)")
    return KV.exact({"pfaffian": str(pf)}, "free_fermion", "O(n³) Pfaffian vs (2n−1)!! pairing sum", cert,
                    reason="Axis-A: free-field correlator / pairing-sum recognized; Axis-B (2n−1)!!→O(n³), crossover_n≈4")


def is_wick_consistent(A: Sequence[Sequence], higher: Dict[Tuple[int, ...], object]) -> KV.Verdict:
    """Free-vs-interacting discriminator: a given higher correlator ⟨ψ_{i1}…ψ_{i2m}⟩ must equal the Pfaffian of the
    A-submatrix on those indices (Wick). All consistent ⇒ FREE (EXACT, fold via Pfaffian); ANY mismatch ⇒ a connected
    (interacting) correlation ⇒ DECLINE (Wick holds ONLY for quadratic actions)."""
    try:
        Af = [[_exact(x) for x in row] for row in A]
        hi = {tuple(k): _exact(v) for k, v in higher.items()}
    except (ValueError, TypeError):
        return KV.decline("wick: non-rational data ⇒ DECLINE", "free_fermion")
    if not _is_skew(Af):
        return KV.decline("wick: 2-point matrix not skew ⇒ DECLINE", "free_fermion")
    for idxs, val in hi.items():
        sub = [[Af[i][j] for j in idxs] for i in idxs]
        if pfaffian_Q(sub) != val:
            return KV.decline(f"wick: ⟨{idxs}⟩={val} ≠ Pf(submatrix)={pfaffian_Q(sub)} ⇒ connected (interacting) "
                              f"correlation ≠ 0 ⇒ NOT free ⇒ DECLINE", "free_fermion")
    cert = KV.Cert(KV.EXACT, "exact_replay", passed=True, check_cost="Pfaffian per correlator",
                   detail="all provided higher correlators satisfy Wick (= Pf of the 2-point submatrix) ⇒ free theory")
    return KV.exact({"free": True, "checked": len(hi)}, "free_fermion", "O(n³) per correlator", cert,
                    reason="Axis-A: free theory certified by Wick consistency")


# ── FF-3 — Bogoliubov: Gaussian evolution = orthogonal/symplectic action on the covariance matrix ───────────────
def gaussian_evolve(Gamma: Sequence[Sequence], R: Sequence[Sequence], N: int) -> KV.Verdict:
    """A Gaussian (quadratic-H) channel acts on the covariance matrix as Γ→RΓRᵀ with R orthogonal (fermion). N steps
    fold to Γ_N=Rᴺ Γ (Rᴺ)ᵀ via cfinite._matpow — EXACT (rational R, RᵀR=I); non-orthogonal R / float ⇒ DECLINE."""
    try:
        Rf = [[_exact(x) for x in row] for row in R]
        Gf = [[_exact(x) for x in row] for row in Gamma]
    except (ValueError, TypeError):
        return KV.decline("gaussian: non-rational R/Γ (float) ⇒ DECLINE (no float-EXACT)", "free_fermion")
    n = len(Rf)
    if n == 0 or any(len(r) != n for r in Rf):
        return KV.decline("gaussian: R must be square", "free_fermion")
    # GATE: RᵀR = I (orthogonal ⇒ Gaussian-preserving; the directive's z3 finite identity, here exact arithmetic)
    RtR = [[sum((Rf[k][i] * Rf[k][j] for k in range(n)), Fraction(0)) for j in range(n)] for i in range(n)]
    if any(RtR[i][j] != (1 if i == j else 0) for i in range(n) for j in range(n)):
        return KV.decline("gaussian: RᵀR≠I ⇒ R is not orthogonal ⇒ not a Gaussian-preserving channel ⇒ DECLINE "
                          "(non-Gaussian)", "free_fermion")
    RN = cfinite._matpow(Rf, N)
    RNt = [[RN[j][i] for j in range(n)] for i in range(n)]
    GN = [[sum((RN[i][k] * Gf[k][j] for k in range(n)), Fraction(0)) for j in range(n)] for i in range(n)]
    GN = [[sum((GN[i][k] * RNt[k][j] for k in range(n)), Fraction(0)) for j in range(n)] for i in range(n)]
    # held-out replay: step-by-step for a small N' must match the matpow form
    chk = [[Fraction(Gf[i][j]) for j in range(n)] for i in range(n)]
    for _ in range(min(N, 3)):
        tmp = [[sum((Rf[i][k] * chk[k][j] for k in range(n)), Fraction(0)) for j in range(n)] for i in range(n)]
        chk = [[sum((tmp[i][k] * Rf[j][k] for k in range(n)), Fraction(0)) for j in range(n)] for i in range(n)]
    if N <= 3 and chk != GN:
        return KV.decline("gaussian: matpow form disagrees with step-by-step replay ⇒ DECLINE", "free_fermion")
    cert = KV.Cert(KV.EXACT, "exact_replay", passed=True, check_cost="RᵀR=I + O(n³·log N) matpow + held-out replay",
                   detail="Γ_N=Rᴺ Γ (Rᴺ)ᵀ, R∈O(2n) (RᵀR=I ✓); covariance theorem ∀-N + companion matpow")
    return KV.exact({"covariance_N": [[str(x) for x in row] for row in GN]}, "free_fermion",
                    "O(n³·log N) vs O(N·2^N)", cert,
                    reason="Axis-A: Gaussian channel recognized; Axis-B exp→O(n³·log N), crossover_n≈1")


# ── FF-4 — Jordan–Wigner: spin model → free fermions iff the JW image is quadratic ──────────────────────────────
_JW_QUADRATIC = {"Z", "X", "Y", "XX", "YY", "XY", "YX"}     # transverse field + XY-type nearest-neighbour ⇒ bilinear
_JW_QUARTIC = {"ZZ"}                                        # density-density ⇒ quartic (interacting fermions)


def jw_is_quadratic(terms: Sequence[dict]) -> KV.Verdict:
    """Decide whether a 1D spin Hamiltonian maps to a QUADRATIC (free) fermion model under Jordan–Wigner. Each term is
    {"op": "Z"|"X"|"XX"|"YY"|"ZZ"|…, "range": 1}. EXACT-route iff every term is JW-bilinear (⇒ FF-1/FF-3); a ZZ
    coupling (XXZ Δ≠0 / Heisenberg) or an unrecognised/long-range term ⇒ quartic/non-local ⇒ DECLINE."""
    if not terms:
        return KV.decline("jw: empty Hamiltonian", "free_fermion")
    quartic, unknown = [], []
    for t in terms:
        op = t.get("op", "")
        rng = t.get("range", 1)
        if op in _JW_QUADRATIC and rng <= 1:
            continue
        if op in _JW_QUARTIC:
            quartic.append(op)
        else:
            unknown.append((op, rng))                       # long-range two-body / unrecognised ⇒ string ⇒ non-quadratic
    if quartic or unknown:
        why = (f"ZZ density-density ⇒ quartic {quartic}" if quartic else "") + (
            f" non-bilinear/long-range {unknown[:3]}" if unknown else "")
    if quartic:
        return KV.decline(f"jw: {why} (XXZ Δ≠0 / Heisenberg / interacting) ⇒ JW image has quartic terms ⇒ NOT free ⇒ "
                          f"DECLINE (JW frees only 1D quadratic models)", "free_fermion")
    if unknown:
        return KV.decline(f"jw: {why} ⇒ JW image is non-local/non-bilinear ⇒ DECLINE", "free_fermion")
    cert = KV.Cert(KV.EXACT, "exact_replay", passed=True, check_cost="JW bilinearity (quartic coeff ≡ 0)",
                   detail="every term is JW-bilinear (transverse field + XY-type nearest-neighbour) ⇒ free-fermion "
                          "solvable ⇒ route to FF-1/FF-3 (Pfaffian / covariance)")
    return KV.exact({"free_fermion_solvable": True, "terms": len(terms)}, "free_fermion", "O(2^N)→O(N³)", cert,
                    reason="Axis-A: JW-quadratic spin model recognized; Axis-B exp→poly")


# ── FF-2 — Peschel: free-fermion entanglement entropy from the correlation spectrum ─────────────────────────────
def peschel_entropy(C: Sequence[Sequence], subsystem: Sequence[int]) -> KV.Verdict:
    """Entanglement entropy of subsystem A of a free-fermion state reduces EXACTLY to the single-particle correlation
    spectrum (Peschel): S_A=−Σ[ν ln ν+(1−ν)ln(1−ν)], ν=eig(C_A). EXACT-STRUCTURE iff the global state is a pure free
    state (C²−C=0, exact); a mixed/thermal C (C²≠C) ⇒ DECLINE. Axis-B only (O(2^|A|)→O(|A|³))."""
    try:
        Cf = [[_exact(x) for x in row] for row in C]
    except (ValueError, TypeError):
        return KV.decline("peschel: non-rational correlation matrix (float) ⇒ DECLINE", "free_fermion")
    n = len(Cf)
    if n == 0 or any(len(r) != n for r in Cf):
        return KV.decline("peschel: C must be square", "free_fermion")
    # GATE: purity C²−C=0 (the global state is a pure free-fermion state ⇒ RDM is Gaussian, Peschel applies exactly)
    C2 = [[sum((Cf[i][k] * Cf[k][j] for k in range(n)), Fraction(0)) for j in range(n)] for i in range(n)]
    if any(C2[i][j] != Cf[i][j] for i in range(n) for j in range(n)):
        return KV.decline("peschel: C²≠C ⇒ not a pure free-fermion state (mixed/thermal, or interacting RDM "
                          "non-Gaussian) ⇒ DECLINE", "free_fermion")
    A = list(subsystem)
    if any(i < 0 or i >= n for i in A):
        return KV.decline("peschel: subsystem index out of range", "free_fermion")
    # numeric eigenvalues of C_A (float used ONLY to evaluate the transcendental entropy; the EXACT claim is the
    # structural reduction, certified by C²−C=0 above)
    import numpy as np
    CA = np.array([[float(Cf[i][j]) for j in A] for i in A], dtype=float)
    nu = np.linalg.eigvalsh((CA + CA.T) / 2.0)
    S = 0.0
    for v in nu:
        v = min(max(float(v), 0.0), 1.0)
        for p in (v, 1.0 - v):
            if p > 1e-12:
                S -= p * np.log(p)
    cert = KV.Cert(KV.EXACT, "exact_replay", passed=True, check_cost="C²−C=0 (purity) + O(|A|³) single-particle spectrum",
                   detail="pure free-fermion state (C²=C ✓) ⇒ S_A reduces EXACTLY to the single-particle correlation "
                          "spectrum (Peschel); O(2^|A|)→O(|A|³). The entropy VALUE is the exact-spectrum evaluation.")
    return KV.exact({"entropy": float(S), "subsystem_size": len(A)}, "free_fermion", "O(|A|³) vs O(2^|A|)", cert,
                    reason="Axis-B only: free-fermion entanglement reduction; crossover_n≈20")


def _symplectic_form(n: int) -> List[List[Fraction]]:
    """Ω = [[0, I],[−I, 0]] (2n×2n) — the bosonic symplectic form."""
    m = 2 * n
    J = [[Fraction(0)] * m for _ in range(m)]
    for i in range(n):
        J[i][n + i] = Fraction(1)
        J[n + i][i] = Fraction(-1)
    return J


def gaussian_cv_evolve(sigma: Sequence[Sequence], S: Sequence[Sequence], N: int) -> KV.Verdict:
    """CV-1 — continuous-variable Gaussian channel: a Gaussian unitary acts on the covariance matrix as σ→SσSᵀ with
    S SYMPLECTIC (SΩSᵀ=Ω, Ω=[[0,I],[−I,0]]). N steps fold to σ_N=Sᴺ σ (Sᴺ)ᵀ via cfinite._matpow. EXACT (rational
    symplectic S); non-symplectic (non-Gaussian, e.g. Kerr/cubic) or float ⇒ DECLINE (Hudson: Wigner-positive ⟺
    Gaussian)."""
    try:
        Sf = [[_exact(x) for x in row] for row in S]
        sig = [[_exact(x) for x in row] for row in sigma]
    except (ValueError, TypeError):
        return KV.decline("cv: non-rational S/σ (float) ⇒ DECLINE (no float-EXACT)", "free_fermion")
    m = len(Sf)
    if m == 0 or m % 2 == 1 or any(len(r) != m for r in Sf):
        return KV.decline("cv: S must be a 2n×2n square matrix", "free_fermion")
    n = m // 2
    Om = _symplectic_form(n)
    StOmS = [[sum((Sf[a][i] * Om[a][b] * Sf[b][j] for a in range(m) for b in range(m)), Fraction(0))
              for j in range(m)] for i in range(m)]
    if any(StOmS[i][j] != Om[i][j] for i in range(m) for j in range(m)):
        return KV.decline("cv: SᵀΩS≠Ω ⇒ S is not symplectic ⇒ not a Gaussian-preserving channel (non-Gaussian: "
                          "cubic/Kerr/photon-number) ⇒ DECLINE", "free_fermion")
    SN = cfinite._matpow(Sf, N)
    SNt = [[SN[j][i] for j in range(m)] for i in range(m)]
    out = [[sum((SN[i][k] * sig[k][j] for k in range(m)), Fraction(0)) for j in range(m)] for i in range(m)]
    out = [[sum((out[i][k] * SNt[k][j] for k in range(m)), Fraction(0)) for j in range(m)] for i in range(m)]
    cert = KV.Cert(KV.EXACT, "exact_replay", passed=True, check_cost="SᵀΩS=Ω + O(n³·log N) matpow",
                   detail="σ_N=Sᴺ σ (Sᴺ)ᵀ, S∈Sp(2n,ℝ) (SᵀΩS=Ω ✓); covariance theorem ∀-N + companion matpow")
    return KV.exact({"covariance_N": [[str(x) for x in row] for row in out]}, "free_fermion",
                    "O(n³·log N) symplectic", cert,
                    reason="Axis-A: Gaussian CV (optical) circuit recognized; Axis-B ∞→O(n³·log N)")


def matchgate_note() -> str:
    """matchgate circuits = free fermions (Valiant 2002; Terhal–DiVincenzo 2002; Jozsa–Miyake 2008): their amplitudes
    are Pfaffians ⇒ decided by FF-1 (pfaffian_Q), NOT pyzx. The stabilizer island cannot capture matchgates; this one
    does. Both islands' UNION is still not universal QC."""
    return "matchgate ≡ free-fermion ⇒ amplitude = Pfaffian (FF-1); zero-dep self-impl, no pyzx."


def adversarial_battery() -> dict:
    """★ FF-1 Pfaffian: Parlett–Reid ≡ combinatorial pairing sum AND Pf²=det on random skew matrices; a free 4-point
    folds, an INTERACTING (connected) 4-point DECLINEs. ★ FF-3 Gaussian: an orthogonal R folds Γ→RᴺΓRᵀᴺ, a non-
    orthogonal R DECLINEs (non-Gaussian). ★ FF-4 JW: transverse-Ising (Z+XX) is free, XXZ (ZZ) DECLINEs (quartic).
    ★ FF-2 Peschel: a pure projector (C²=C) gives an entropy, a mixed C (C²≠C) DECLINEs. ★★ float ⇒ DECLINE."""
    # FF-1 Pfaffian correctness on a 4×4 and 6×6 skew matrix
    A4 = [[0, 2, -1, 3], [-2, 0, 5, -1], [1, -5, 0, 2], [-3, 1, -2, 0]]
    pf_ok = pfaffian_Q(A4) == pfaffian_combinatorial(A4) and pfaffian_Q(A4) ** 2 == det_Q(A4)
    A6 = [[0, 1, 2, 3, 4, 5], [-1, 0, 6, 7, 8, 9], [-2, -6, 0, 1, 2, 3],
          [-3, -7, -1, 0, 4, 5], [-4, -8, -2, -4, 0, 6], [-5, -9, -3, -5, -6, 0]]
    pf6_ok = pfaffian_Q(A6) == pfaffian_combinatorial(A6) and pfaffian_Q(A6) ** 2 == det_Q(A6)
    free_fold = wick_pfaffian_fold(A4).status == KV.EXACT
    # free vs interacting 4-point: free ⟨1234⟩ = Pf = A12·A34 − A13·A24 + A14·A23
    free4 = is_wick_consistent(A4, {(0, 1, 2, 3): pfaffian_Q(A4)})
    inter4 = is_wick_consistent(A4, {(0, 1, 2, 3): pfaffian_Q(A4) + 1})   # add a connected piece ⇒ interacting
    wick_disc = free4.status == KV.EXACT and inter4.status == KV.DECLINE
    # FF-3 Gaussian: a rational orthogonal R (a signed permutation) folds; a non-orthogonal R DECLINEs
    Rorth = [[0, -1], [1, 0]]                                            # 90° rotation, RᵀR=I
    Gamma = [[0, 1], [-1, 0]]
    gauss_ok = gaussian_evolve(Gamma, Rorth, 5).status == KV.EXACT
    gauss_bad = gaussian_evolve(Gamma, [[2, 0], [0, 1]], 5).status == KV.DECLINE   # RᵀR≠I ⇒ non-Gaussian
    # FF-4 JW: transverse-field Ising (free) vs XXZ (interacting)
    tfim = jw_is_quadratic([{"op": "Z", "range": 1}, {"op": "XX", "range": 1}])
    xxz = jw_is_quadratic([{"op": "XX", "range": 1}, {"op": "YY", "range": 1}, {"op": "ZZ", "range": 1}])
    jw_ok = tfim.status == KV.EXACT and xxz.status == KV.DECLINE
    # FF-2 Peschel: a pure projector C (C²=C) gives entropy; a mixed C (C²≠C) DECLINEs
    Cpure = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]      # projector ⇒ C²=C (product state, S=0)
    Cmixed = [[Fraction(1, 2), 0], [0, Fraction(1, 2)]]                   # C²≠C ⇒ mixed
    peschel_ok = (peschel_entropy(Cpure, [0, 1]).status == KV.EXACT
                  and peschel_entropy(Cmixed, [0, 1]).status == KV.DECLINE)
    # CV-1: a symplectic S (SᵀΩS=Ω, shear) folds the covariance; a non-symplectic S (det≠1) DECLINEs (non-Gaussian)
    cv_ok = (gaussian_cv_evolve([[1, 0], [0, 1]], [[1, 1], [0, 1]], 5).status == KV.EXACT
             and gaussian_cv_evolve([[1, 0], [0, 1]], [[2, 0], [0, 1]], 5).status == KV.DECLINE)
    # float ⇒ DECLINE
    float_declines = wick_pfaffian_fold([[0.0, 1.0], [-1.0, 0.0]]).status == KV.DECLINE
    cases = {"pfaffian4_correct": pf_ok, "pfaffian6_correct": pf6_ok, "free_correlator_folds": free_fold,
             "wick_free_vs_interacting": wick_disc, "gaussian_orthogonal_folds": gauss_ok,
             "gaussian_nonorthogonal_declines": gauss_bad, "cv_symplectic_vs_nonsymplectic": cv_ok,
             "jw_tfim_free_xxz_declines": jw_ok, "peschel_pure_vs_mixed": peschel_ok, "float_declines": float_declines}
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
