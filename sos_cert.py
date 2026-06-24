"""
SOS / POSITIVSTELLENSATZ — a new EXACT certificate tier (Constitution §4.4/§8, mechanism 4).
============================================================================================
Prove a polynomial p(x) ≥ 0 (globally, over ℝⁿ) by an EXACT sum-of-squares certificate: a RATIONAL Gram matrix Q
with p = zᵀ Q z (z = the monomial basis up to degree d) and Q ⪰ 0. Both checks are EXACT, no floating SDP:
  • zᵀ Q z ≡ p           — exact polynomial identity over ℚ;
  • Q ⪰ 0               — zero negative eigenvalues, counted EXACTLY via the characteristic polynomial (Sturm),
                          never an eigen-solve / floating decomposition.
SOUND-OR-DECLINE (§2): the Gram is UNIQUE for quadratics (degree 2) ⇒ a COMPLETE EXACT decision. For higher even
degree the Gram is under-determined (an SDP cone); we try the PARTICULAR solution (free params 0) and, if it is
PSD + matches, emit EXACT — otherwise DECLINE honestly (we do NOT have an SDP solver to search the cone, so we
never overclaim). Odd degree / negative leading behaviour ⇒ not globally nonneg ⇒ DECLINE.

The dual cert is the Positivstellensatz refutation backbone (mechanism 4 → 14): an SOS proof of p ≥ 0 is also a
refutation of p < 0 satisfiability.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import sympy as sp

import kernel_verdict as KV

_LAM = sp.Symbol("_lam_sos")


def _neg_eig_count(Q: sp.Matrix) -> int:
    """EXACT count of strictly-negative eigenvalues of a symmetric rational Q (no eigen-solve): negative real roots
    of the characteristic polynomial via Sturm root-counting. (Q symmetric ⇒ all eigenvalues real.)"""
    c = Q.charpoly(_LAM)
    neg_closed = int(c.count_roots(sp.S.NegativeInfinity, 0))      # DISTINCT real roots in (-∞, 0]
    zero_is_root = sp.simplify(c.as_expr().subs(_LAM, 0)) == 0     # subtract the root at 0 (a repeated 0 eig is PSD)
    return neg_closed - (1 if zero_is_root else 0)


def is_psd(Q: sp.Matrix) -> bool:
    """EXACT PSD test for a symmetric rational matrix."""
    if not Q.is_symmetric():
        return False
    return _neg_eig_count(Q) == 0


def _monomials(gens: Tuple[sp.Symbol, ...], d: int) -> List[sp.Expr]:
    """All monomials in `gens` of total degree ≤ d (the SOS basis z)."""
    from itertools import combinations_with_replacement
    mons = [sp.Integer(1)]
    for deg in range(1, d + 1):
        for combo in combinations_with_replacement(gens, deg):
            m = sp.Integer(1)
            for g in combo:
                m *= g
            mons.append(m)
    # dedup keep order
    seen, out = set(), []
    for m in mons:
        k = sp.srepr(m)
        if k not in seen:
            seen.add(k)
            out.append(m)
    return out


def sos_gram(expr, gens: Optional[Tuple[sp.Symbol, ...]] = None):
    """Build a rational Gram matrix Q with zᵀQz ≡ p (particular solution; unique for quadratics). Returns
    (Q, basis) or None (odd/zero degree, or no consistent Gram)."""
    expr = sp.expand(sp.sympify(expr))
    if gens is None:
        gens = tuple(sorted(expr.free_symbols, key=lambda s: s.name)) or (sp.Symbol("x"),)
    p = sp.Poly(expr, *gens)
    deg = p.total_degree()
    if deg == 0:
        # constant: nonneg iff the constant ≥ 0; Gram is the 1×1 [c]
        c = expr
        return (sp.Matrix([[c]]), [sp.Integer(1)])
    if deg % 2 == 1:
        return None                                               # odd degree ⇒ not globally nonneg
    d = deg // 2
    basis = _monomials(gens, d)
    n = len(basis)
    # symbolic symmetric Q
    qsyms = {}
    Q = sp.zeros(n, n)
    for i in range(n):
        for j in range(i, n):
            s = sp.Symbol(f"_q_{i}_{j}")
            qsyms[(i, j)] = s
            Q[i, j] = s
            Q[j, i] = s
    # zᵀ Q z  matched to p
    z = sp.Matrix(basis)
    form = sp.expand((z.T * Q * z)[0, 0])
    diff = sp.Poly(sp.expand(form - expr), *gens)
    eqs = [sp.Eq(co, 0) for co in diff.coeffs()] if diff.total_degree() >= 0 else []
    # also force every monomial coefficient of (form - expr) to zero (robust): collect on all monomials
    allmons = set(sp.Poly(form, *gens).monoms()) | set(p.monoms())
    fpoly = sp.Poly(form, *gens)
    eqs = []
    for mon in allmons:
        eqs.append(sp.Eq(fpoly.coeff_monomial(mon) - p.coeff_monomial(mon), 0))
    sol = sp.solve(eqs, list(qsyms.values()), dict=True)
    if not sol:
        return None
    sub = sol[0]
    # particular solution: free params (symbols not pinned) → 0
    Qp = Q.subs(sub)
    Qp = Qp.subs({s: 0 for s in Qp.free_symbols})
    try:
        Qp = sp.Matrix(n, n, lambda i, j: sp.nsimplify(Qp[i, j]))
    except Exception:  # noqa: BLE001
        pass
    return (Qp, basis)


def verify_sos(expr, Q: sp.Matrix, basis: List[sp.Expr]) -> bool:
    """EXACT re-check of an SOS certificate: zᵀQz ≡ p AND Q ⪰ 0 (both over ℚ)."""
    z = sp.Matrix(basis)
    identity_ok = sp.expand((z.T * Q * z)[0, 0] - sp.expand(sp.sympify(expr))) == 0
    return bool(identity_ok and is_psd(Q))


def squares_from_gram(Q: sp.Matrix, basis: List[sp.Expr]) -> List[sp.Expr]:
    """Explicit SOS terms p = Σ d_k (ℓ_kᵀ z)² from an LDLᵀ of the PSD Gram (best-effort; cert is (Q,basis))."""
    try:
        L, D = Q.LDLdecomposition(hermitian=False)
        z = sp.Matrix(basis)
        out = []
        Lz = L.T * z
        for k in range(Q.rows):
            dk = D[k, k]
            if dk != 0:
                out.append(sp.simplify(dk * Lz[k] ** 2))
        return out
    except Exception:  # noqa: BLE001
        return []


def inertia(Q: sp.Matrix):
    """Sylvester INERTIA (n₊, n₀, n₋) of a symmetric rational matrix — a complete invariant of its congruence class
    (mechanism 1/9). EXACT via eigenvalue signs (symmetric ⇒ real eigenvalues; sympy decides the sign of each
    algebraic eigenvalue). Returns None if not symmetric or a sign is undecidable."""
    Q = sp.Matrix(Q)
    if not Q.is_symmetric():
        return None
    try:
        ev = Q.eigenvals()
    except Exception:  # noqa: BLE001
        return None
    pos = zero = neg = 0
    for v, m in ev.items():
        vs = sp.simplify(v)
        if vs == 0:
            zero += m
        elif vs.is_positive:
            pos += m
        elif vs.is_negative:
            neg += m
        else:
            return None
    return (int(pos), int(zero), int(neg))


def inertia_grade(Q) -> KV.Verdict:
    """EXACT spectral signature (Sylvester inertia) of a symmetric rational matrix — a complete congruence invariant.
    Definiteness falls out: (n,0,0)=PD, (·,·,0)=PSD, (0,·,·)≤0, mixed=indefinite. Non-symmetric → DECLINE."""
    try:
        M = sp.Matrix(Q)
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"inertia: not a matrix ({type(e).__name__})", "spectral_inertia")
    if not M.is_symmetric():
        return KV.decline("inertia: matrix not symmetric — congruence inertia needs a symmetric matrix", "spectral_inertia")
    inr = inertia(M)
    if inr is None:
        return KV.decline("inertia: an eigenvalue sign was undecidable (exact spectrum unavailable)", "spectral_inertia")
    pos, zero, neg = inr
    kind = ("positive-definite" if (zero == 0 and neg == 0) else "positive-semidefinite" if neg == 0
            else "negative-definite" if (zero == 0 and pos == 0) else "negative-semidefinite" if pos == 0
            else "indefinite")
    cert = KV.Cert(KV.EXACT, "sylvester_inertia", passed=True, check_cost="exact eigenvalue signs (charpoly)",
                   detail=f"inertia (n₊,n₀,n₋) = {inr} — {kind}; complete congruence invariant (Sylvester's law)")
    return KV.exact({"inertia": inr, "definiteness": kind}, "spectral_inertia",
                    "Sylvester inertia (EXACT complete invariant)", cert)


def sos_grade(expr, gens: Optional[Tuple[sp.Symbol, ...]] = None) -> KV.Verdict:
    """EXACT SOS verdict for p ≥ 0 globally. EXACT (Gram PSD + identity verified) else honest DECLINE."""
    try:
        expr = sp.expand(sp.sympify(expr))
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"sos: unparseable polynomial ({type(e).__name__})", "sos")
    if gens is None:
        gens = tuple(sorted(expr.free_symbols, key=lambda s: s.name))
    if not gens:
        # constant
        c = sp.nsimplify(expr)
        if c >= 0:
            cert = KV.Cert(KV.EXACT, "sos_constant", passed=True, check_cost="O(1)", detail=f"{c} ≥ 0")
            return KV.exact(f"{c} = ({sp.sqrt(c)})²" if c != 0 else "0", "sos", "O(1)", cert)
        return KV.decline(f"sos: constant {c} < 0 — not nonneg (no SOS)", "sos")
    g = sos_gram(expr, gens)
    if g is None:
        return KV.decline("sos: odd total degree / no consistent Gram — not a global SOS (DECLINE, no overclaim)", "sos")
    Q, basis = g
    if not verify_sos(expr, Q, basis):
        return KV.decline("sos: particular Gram is not PSD (would need an SDP cone search — no solver here) → "
                          "honest DECLINE (sound: never overclaims nonnegativity)", "sos")
    squares = squares_from_gram(Q, basis)
    detail = f"p = zᵀQz, z={basis}, Q⪰0 (0 negative eigenvalues, Sturm-exact)" + (
        f"; SOS = {' + '.join(str(s) for s in squares)}" if squares else "")
    cert = KV.Cert(KV.EXACT, "sos_gram", passed=True, check_cost="O(n³) charpoly+Sturm + exact identity",
                   detail=detail)
    return KV.exact({"gram": Q, "basis": basis, "squares": squares}, "sos", "SOS/Positivstellensatz (EXACT)", cert)
