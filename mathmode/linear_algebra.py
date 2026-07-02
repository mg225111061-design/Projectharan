"""
MATH-Ascent §3 (arsenal) — LINEAR ALGEBRA: exact rational solve / inverse / determinant, self-certified.
========================================================================================================
Exact arithmetic over ℚ (fractions.Fraction — never a float), so the answers are EXACT and carry a
SELF-CERTIFYING check: solving Ax=b is O(n³) but the residual  A·x − b = 0  is checkable in O(n²) and proves the
solution with no trust in the solver; the inverse is proven by  A·A⁻¹ = I  exactly. The determinant (fraction-
free Bareiss, O(n³)) is certified by a SECOND independent exact method — cofactor/Laplace expansion (our own)
for small n, sympy's exact det as the cross-check for larger n. Singular systems ⇒ honest DECLINE (no unique
solution / no inverse — never a fabricated answer). This is the §2 fold ethos: compute exactly, then prove the
result against a cheap independent check; offload the grind from the LLM (it must never invert a 6×6 by hand).
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Optional, Sequence

import kernel_verdict as KV

Mat = List[List[Fraction]]


# ── exact matrix helpers (Fraction, never float) ─────────────────────────────────────────────────────────
def _F(M: Sequence[Sequence]) -> Mat:
    return [[Fraction(x) for x in row] for row in M]


def _matmul(A: Mat, B: Mat) -> Mat:
    n, m, p = len(A), len(B), len(B[0])
    return [[sum((A[i][k] * B[k][j] for k in range(m)), Fraction(0)) for j in range(p)] for i in range(n)]


def _matvec(A: Mat, x: Sequence[Fraction]) -> List[Fraction]:
    return [sum((A[i][k] * x[k] for k in range(len(x))), Fraction(0)) for i in range(len(A))]


def _ident(n: int) -> Mat:
    return [[Fraction(1) if i == j else Fraction(0) for j in range(n)] for i in range(n)]


def _is_square(A) -> bool:
    return len(A) > 0 and all(len(r) == len(A) for r in A)


# ── exact Gaussian elimination on the augmented matrix (solve & inverse share it) ────────────────────────
def _rref_solve(A: Mat, rhs: Mat) -> Optional[Mat]:
    """Solve A·X = rhs exactly (rhs has one or more columns). Returns X, or None if A is singular."""
    n = len(A)
    aug = [A[i][:] + rhs[i][:] for i in range(n)]
    w = len(rhs[0])
    for col in range(n):
        piv = next((r for r in range(col, n) if aug[r][col] != 0), None)
        if piv is None:
            return None                                   # singular — no unique solution
        aug[col], aug[piv] = aug[piv], aug[col]
        pv = aug[col][col]
        aug[col] = [v / pv for v in aug[col]]
        for r in range(n):
            if r != col and aug[r][col] != 0:
                f = aug[r][col]
                aug[r] = [a - f * b for a, b in zip(aug[r], aug[col])]
    return [row[n:n + w] for row in aug]


def solve_grade(A, b) -> KV.Verdict:
    """Solve A·x = b exactly. Certificate: the residual A·x − b = 0 (exact). Singular A ⇒ DECLINE."""
    if not _is_square(A) or len(b) != len(A):
        return KV.decline("solve: A must be square and match b ⇒ DECLINE", "linear_algebra.solve")
    Af = _F(A)
    X = _rref_solve(Af, [[Fraction(v)] for v in b])
    if X is None:
        return KV.decline("solve: A is singular ⇒ no unique solution ⇒ DECLINE", "linear_algebra.solve")
    x = [row[0] for row in X]
    if _matvec(Af, x) != [Fraction(v) for v in b]:        # ★ self-certifying residual ★
        return KV.decline("solve: residual A·x ≠ b ⇒ DECLINE", "linear_algebra.solve")
    cert = KV.Cert(KV.EXACT, "exact_residual", passed=True, check_cost="O(n²) residual",
                   detail="A·x = b verified exactly over ℚ (residual = 0)")
    return KV.exact(x, "linear_algebra.solve", "O(n³) exact elimination", cert)


def inverse_grade(A) -> KV.Verdict:
    """Exact inverse A⁻¹. Certificate: A·A⁻¹ = I (exact). Singular A ⇒ DECLINE."""
    if not _is_square(A):
        return KV.decline("inverse: A must be square ⇒ DECLINE", "linear_algebra.inverse")
    n = len(A)
    Af = _F(A)
    inv = _rref_solve(Af, _ident(n))
    if inv is None:
        return KV.decline("inverse: A is singular ⇒ not invertible ⇒ DECLINE", "linear_algebra.inverse")
    if _matmul(Af, inv) != _ident(n):                     # ★ self-certifying A·A⁻¹ = I ★
        return KV.decline("inverse: A·A⁻¹ ≠ I ⇒ DECLINE", "linear_algebra.inverse")
    cert = KV.Cert(KV.EXACT, "inverse_identity", passed=True, check_cost="O(n³) one product",
                   detail="A·A⁻¹ = I verified exactly over ℚ")
    return KV.exact(inv, "linear_algebra.inverse", "O(n³) exact elimination", cert)


# ── determinant: fraction-free Bareiss, certified by a second independent exact method ───────────────────
def _bareiss_det(M: Mat) -> Fraction:
    """Fraction-free Bareiss determinant (exact). O(n³), no growing denominators on integer input."""
    n = len(M)
    A = [row[:] for row in M]
    sign = 1
    prev = Fraction(1)
    for k in range(n - 1):
        if A[k][k] == 0:
            sw = next((r for r in range(k + 1, n) if A[r][k] != 0), None)
            if sw is None:
                return Fraction(0)
            A[k], A[sw] = A[sw], A[k]
            sign = -sign
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                A[i][j] = (A[i][j] * A[k][k] - A[i][k] * A[k][j]) / prev
        prev = A[k][k]
    return sign * A[n - 1][n - 1]


def _cofactor_det(M: Mat) -> Fraction:
    """Independent Laplace/cofactor expansion (exact) — the cross-check for small n."""
    n = len(M)
    if n == 1:
        return M[0][0]
    if n == 2:
        return M[0][0] * M[1][1] - M[0][1] * M[1][0]
    total = Fraction(0)
    for j in range(n):
        if M[0][j] == 0:
            continue
        minor = [[M[i][c] for c in range(n) if c != j] for i in range(1, n)]
        total += ((-1) ** j) * M[0][j] * _cofactor_det(minor)
    return total


def det_grade(A) -> KV.Verdict:
    """Exact determinant via Bareiss, certified by an independent exact method (cofactor for small n, sympy
    exact det otherwise). The two exact computations must agree."""
    if not _is_square(A):
        return KV.decline("det: A must be square ⇒ DECLINE", "linear_algebra.det")
    Af = _F(A)
    d = _bareiss_det(Af)
    n = len(Af)
    if n <= 7:
        d2 = _cofactor_det(Af)
        method = "cofactor expansion (our own)"
    else:
        import sympy as sp
        d2 = Fraction(sp.Matrix(A).det())
        method = "sympy exact det"
    if d != d2:                                            # two independent EXACT methods must agree
        return KV.decline(f"det: Bareiss {d} ≠ {method} {d2} ⇒ DECLINE", "linear_algebra.det")
    cert = KV.Cert(KV.EXACT, "det_cross_method", passed=True, check_cost=f"second exact method ({method})",
                   detail=f"det = {d}; fraction-free Bareiss ≡ {method} (exact agreement)")
    return KV.exact(d, "linear_algebra.det", "O(n³) fraction-free", cert)


# ── exact eigenpairs, self-certified by A·v = λ·v ───────────────────────────────────────────────────────
def eigen_grade(A) -> KV.Verdict:
    """Exact eigenvalues/eigenvectors. Certificate: A·v − λ·v = 0 for every returned pair (verified symbolically).
    Eigenvalues with no closed form (an unsolvable characteristic polynomial, degree ≥ 5) ⇒ honest DECLINE."""
    import sympy as sp
    if not _is_square(A):
        return KV.decline("eigen: A must be square ⇒ DECLINE", "linear_algebra.eigen")
    M = sp.Matrix([[sp.nsimplify(x) for x in row] for row in A])
    try:
        eigs = M.eigenvects()
    except Exception as e:                                    # noqa: BLE001
        return KV.decline(f"eigen: eigen-decomposition failed ({type(e).__name__}) ⇒ DECLINE", "linear_algebra.eigen")
    pairs = []
    for val, mult, vecs in eigs:
        if val.has(sp.CRootOf) or val.has(sp.RootOf):        # no explicit closed form ⇒ honest DECLINE
            return KV.decline("eigen: eigenvalues only as implicit RootOf (degree ≥5) ⇒ DECLINE",
                              "linear_algebra.eigen")
        for v in vecs:
            if sp.simplify(M * v - val * v) != sp.zeros(M.rows, 1):   # ★ A·v = λ·v, exact ★
                return KV.decline(f"eigen: A·v ≠ λ·v for λ={sp.sstr(val)} ⇒ DECLINE", "linear_algebra.eigen")
            pairs.append((val, list(v)))
    cert = KV.Cert(KV.EXACT, "eigenpair_verified", passed=True, check_cost=f"{len(pairs)} exact A·v−λ·v checks",
                   detail=f"{len(pairs)} eigenpair(s); each satisfies A·v = λ·v exactly (eigenvalues: "
                          f"{', '.join(sp.sstr(val) for val, _ in pairs)})")
    return KV.exact(pairs, "linear_algebra.eigen", "exact eigenpairs (sympy + verified)", cert)


# ══ §AZ CAPABILITY LEDGER (fold-rate impact: 0) — new decision branches; exact ℚ, self-impl, repo-first ══════════
def _charpoly(A: Mat) -> List[Fraction]:
    """Characteristic polynomial of A as monic descending coeffs [1, c₁, …, cₙ] (det(sI−A)=sⁿ+c₁sⁿ⁻¹+⋯+cₙ), via
    Faddeev–LeVerrier — exact over ℚ, reuses _matmul/_ident (self-impl, no z3, no sympy)."""
    n = len(A)
    M = [[Fraction(0)] * n for _ in range(n)]
    coeffs = [Fraction(1)]
    for k in range(1, n + 1):
        Mk = [[M[i][j] + (coeffs[-1] if i == j else Fraction(0)) for j in range(n)] for i in range(n)]
        M = _matmul(A, Mk)
        tr = sum((M[i][i] for i in range(n)), Fraction(0))
        coeffs.append(-tr / k)
    return coeffs


def _resultant(p: List[Fraction], q: List[Fraction]) -> Fraction:
    """Resultant Res(p,q) = det of the Sylvester matrix (p,q monic-or-not descending coeffs) — fraction-free Bareiss
    (self-impl). Res ≠ 0 ⟺ p,q share NO common root (no common factor over an algebraically closed field)."""
    n, m = len(p) - 1, len(q) - 1
    if n < 0 or m < 0:
        return Fraction(0)
    size = n + m
    if size == 0:
        return Fraction(1)
    S = [[Fraction(0)] * size for _ in range(size)]
    for i in range(m):                                         # m shifted rows of p
        for j, c in enumerate(p):
            S[i][i + j] = c
    for i in range(n):                                         # n shifted rows of q
        for j, c in enumerate(q):
            S[m + i][i + j] = c
    return _bareiss_det(S)


def _rank(M: Mat) -> int:
    """Exact rank over ℚ by Gaussian elimination (pivot count)."""
    A = [row[:] for row in M]
    rows, cols = len(A), len(A[0]) if A else 0
    r = 0
    for c in range(cols):
        piv = next((i for i in range(r, rows) if A[i][c] != 0), None)
        if piv is None:
            continue
        A[r], A[piv] = A[piv], A[r]
        pv = A[r][c]
        A[r] = [v / pv for v in A[r]]
        for i in range(rows):
            if i != r and A[i][c] != 0:
                f = A[i][c]
                A[i] = [a - f * b for a, b in zip(A[i], A[r])]
        r += 1
        if r == rows:
            break
    return r


# ── CAP-4: Sylvester AX+XB=C unique solvability (spectral separation) ────────────────────────────────────────
def sylvester_solvable(A, B, C=None) -> KV.Verdict:
    """DECIDE unique solvability of AX+XB=C: unique ⟺ spec(A)∩spec(−B)=∅ ⟺ Res(χ_A, χ_{−B})≠0 (eigenvalues NEVER
    computed). EXACT (Res≠0: solve via Kronecker (I⊗A+Bᵀ⊗I)vec(X)=vec(C), re-substitute AX+XB=C) or ★PROVEN DECLINE
    (Res=0: spectra share a value ⇒ NO unique solution). fold-rate impact: 0 (capability ledger)."""
    if not _is_square(A) or not _is_square(B):
        return KV.decline("sylvester: A,B must be square ⇒ DECLINE", "linear_algebra.sylvester")
    Af, Bf = _F(A), _F(B)
    nB = len(Bf)
    negB = [[-Bf[i][j] for j in range(nB)] for i in range(nB)]
    res = _resultant(_charpoly(Af), _charpoly(negB))
    if res == 0:
        return KV.decline("sylvester: ★PROVEN no unique solution — Res(χ_A,χ_{−B})=0 ⇒ A and −B share an eigenvalue "
                          "(spectra overlap, Sylvester/Roth); AX+XB=C is NOT uniquely solvable (existence is "
                          "special-RHS dependent).", "linear_algebra.sylvester")
    n, m = len(Af), nB
    if C is None:                                              # decision-only (no RHS): unique solvability established
        cert = KV.Cert(KV.EXACT, "sylvester_resultant_nonzero", passed=True, check_cost="Res(χ_A,χ_{−B})≠0 (Bareiss)",
                       detail=f"Res(χ_A,χ_{{−B}}) = {res} ≠ 0 ⇒ spec(A)∩spec(−B)=∅ ⇒ unique solution for every C")
        return KV.exact({"unique": True, "resultant": str(res)}, "linear_algebra.sylvester",
                        "DECISION (Sylvester unique solvability)", cert)
    Cf = _F(C)
    # Kronecker: column-stacked vec(X); M[j*n+i][l*n+k] = δ_{jl}A[i][k] + B[l][j]δ_{ik}
    N = n * m
    Mk = [[Fraction(0)] * N for _ in range(N)]
    for j in range(m):
        for i in range(n):
            for l in range(m):
                for k in range(n):
                    val = (Af[i][k] if j == l else Fraction(0)) + (Bf[l][j] if i == k else Fraction(0))
                    if val != 0:
                        Mk[j * n + i][l * n + k] = val
    vecC = [[Cf[i][j]] for j in range(m) for i in range(n)]
    sol = _rref_solve(Mk, vecC)
    if sol is None:
        return KV.decline("sylvester: Kronecker system singular despite Res≠0 (unexpected) ⇒ DECLINE", "linear_algebra.sylvester")
    X = [[sol[j * n + i][0] for j in range(m)] for i in range(n)]
    AX = _matmul(Af, X)
    XB = _matmul(X, Bf)
    if [[AX[i][j] + XB[i][j] for j in range(m)] for i in range(n)] != Cf:   # ★ re-substitution certificate
        return KV.decline("sylvester: AX+XB ≠ C ⇒ DECLINE (rejected)", "linear_algebra.sylvester")
    cert = KV.Cert(KV.EXACT, "sylvester_resubstitution", passed=True, check_cost="AX+XB−C ≡ 0 (exact)",
                   detail=f"Res≠0 ⇒ unique; X recovered by Kronecker solve and AX+XB=C verified exactly over ℚ")
    return KV.exact(X, "linear_algebra.sylvester", "DECISION (Sylvester unique solve)", cert)


# ── CAP-5: Frobenius rational canonical form — ℚ-similarity (bypasses the degree≥5 eigenvalue wall) ──────────────
def _invariant_factors_xI_minus(A) -> List:
    """Invariant factors of xI−A as monic sympy polynomials in x, via determinantal divisors d_k = gcd of all k×k
    minors (i_k = d_k/d_{k−1}). A complete ℚ-similarity invariant (structure theorem) — stays in ℚ[x], so it never
    needs the eigenvalues (the degree≥5 bypass)."""
    import sympy as sp
    x = sp.Symbol("x")
    n = len(A)
    M = sp.Matrix(n, n, lambda i, j: (x if i == j else 0) - sp.Rational(Fraction(A[i][j])))
    from itertools import combinations
    dprev = sp.Integer(1)
    inv = []
    for k in range(1, n + 1):
        g = sp.Integer(0)
        for rows in combinations(range(n), k):
            for cols in combinations(range(n), k):
                minor = M.extract(list(rows), list(cols)).det()
                g = sp.gcd(g, sp.expand(minor))
        dk = sp.simplify(g)
        if dk == 0:
            return None                                        # should not happen for xI−A (det ≠ 0)
        ik = sp.simplify(sp.cancel(dk / dprev))
        inv.append(sp.Poly(ik, x).monic().as_expr())
        dprev = dk
    return [f for f in inv if sp.Poly(f, x).degree() > 0]       # drop the trivial 1's


def similar_decide(A, B) -> KV.Verdict:
    """DECIDE A∼B over ℚ via Frobenius invariant factors of xI−A, xI−B (same factors ⟺ similar). EXACT decision;
    ★PROVEN A≁B (negative inference) when the invariant factors differ. Works for degree≥5 spectra (stays in ℚ[x]).
    fold-rate impact: 0 (capability ledger)."""
    if not _is_square(A) or not _is_square(B) or len(A) != len(B):
        return KV.decline("similar: A,B must be square and same size ⇒ DECLINE", "linear_algebra.similar")
    import sympy as sp
    x = sp.Symbol("x")
    try:
        fa = _invariant_factors_xI_minus(A)
        fb = _invariant_factors_xI_minus(B)
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"similar: invariant-factor computation failed ({type(e).__name__}) ⇒ DECLINE", "linear_algebra.similar")
    same = len(fa) == len(fb) and all(sp.expand(p - q) == 0 for p, q in zip(fa, fb))
    fa_s = [sp.sstr(p) for p in fa]
    if same:
        cert = KV.Cert(KV.EXACT, "frobenius_invariant_factors", passed=True, check_cost="ℚ[x] determinantal divisors",
                       detail=f"xI−A and xI−B share invariant factors {fa_s} ⇒ A∼B over ℚ (Frobenius; complete invariant)")
        return KV.exact({"similar": True, "invariant_factors": fa_s}, "linear_algebra.similar",
                        "DECISION (ℚ-similarity, Frobenius)", cert)
    return KV.decline(f"similar: ★PROVEN A≁B over ℚ — invariant factors differ ({fa_s} vs {[sp.sstr(q) for q in fb]}); "
                      "by Frobenius (a complete similarity invariant) the matrices are NOT similar.", "linear_algebra.similar")


# ── CAP-6: exact Jordan/Weyr block structure at the ℚ-rational eigenvalues (nullity sequence) ────────────────────
def jordan_structure(A) -> KV.Verdict:
    """Exact Jordan block sizes per ℚ-RATIONAL eigenvalue from the nullity sequence of (A−λI)^k (#blocks of size ≥k
    = rank(A−λI)^{k−1} − rank(A−λI)^k). EXACT over ℚ. Non-ℚ-rational eigenvalues are reported as 'extension needed'
    (honest partial). fold-rate impact: 0 (capability ledger)."""
    if not _is_square(A):
        return KV.decline("jordan: A must be square ⇒ DECLINE", "linear_algebra.jordan")
    import sympy as sp
    x = sp.Symbol("x")
    Af = _F(A)
    n = len(Af)
    cp = sum(c * x ** (n - i) for i, c in enumerate(_charpoly(Af)))
    roots = sp.roots(sp.Poly(cp, x))                            # {root: algebraic multiplicity}
    rational = {r: m for r, m in roots.items() if r.is_rational}
    non_rational_mult = sum(m for r, m in roots.items() if not r.is_rational)
    structure = {}
    for lam, alg_mult in rational.items():
        lamF = Fraction(int(sp.numer(lam)), int(sp.denom(lam)))
        AmL = [[Af[i][j] - (lamF if i == j else Fraction(0)) for j in range(n)] for i in range(n)]
        nul = [0]                                              # nullity of (A−λI)^0 = 0
        P = _ident(n)
        for k in range(1, alg_mult + 1):
            P = _matmul(AmL, P)
            nul.append(n - _rank(P))
        blocks_ge = [nul[k] - nul[k - 1] for k in range(1, len(nul))]    # #blocks of size ≥ k
        sizes = []
        for k in range(1, len(blocks_ge)):
            cnt = blocks_ge[k - 1] - blocks_ge[k]
            sizes += [k] * cnt
        sizes += [len(blocks_ge)] * blocks_ge[-1] if blocks_ge else []
        if sum(sizes) != alg_mult:                             # consistency: Σ block sizes = algebraic multiplicity
            return KV.decline(f"jordan: block sizes {sizes} ≠ algebraic multiplicity {alg_mult} for λ={lam} ⇒ DECLINE",
                              "linear_algebra.jordan")
        structure[sp.sstr(lam)] = sorted(sizes, reverse=True)
    if non_rational_mult > 0 and not structure:
        return KV.decline(f"jordan: all eigenvalues are non-ℚ-rational (irreducible factors, degree≥2) ⇒ field "
                          f"extension needed ⇒ DECLINE (honest; ℚ-rational part empty)", "linear_algebra.jordan")
    cert = KV.Cert(KV.EXACT, "jordan_nullity_sequence", passed=True, check_cost="exact ℚ rank of (A−λI)^k",
                   detail=f"per-λ block sizes from nullity jumps; Σ sizes = alg. mult. (exact). {structure}"
                          + (f" [non-ℚ-rational multiplicity {non_rational_mult} needs extension]" if non_rational_mult else ""))
    return KV.exact({"jordan_blocks": structure, "non_rational_multiplicity": non_rational_mult},
                    "linear_algebra.jordan", "DECISION (exact Jordan/Weyr at ℚ-eigenvalues)", cert)


def solve(problem: dict) -> KV.Verdict:
    """problem = {"op": "solve"|"inverse"|"det"|"eigen"|"sylvester"|"similar"|"jordan", ...}. Unknown op ⇒ DECLINE."""
    op = problem.get("op")
    if op == "solve":
        return solve_grade(problem["A"], problem["b"])
    if op == "inverse":
        return inverse_grade(problem["A"])
    if op == "det":
        return det_grade(problem["A"])
    if op == "eigen":
        return eigen_grade(problem["A"])
    if op == "sylvester":
        return sylvester_solvable(problem["A"], problem["B"], problem.get("C"))
    if op == "similar":
        return similar_decide(problem["A"], problem["B"])
    if op == "jordan":
        return jordan_structure(problem["A"])
    return KV.decline(f"linear_algebra: unknown op {op!r} ⇒ DECLINE", "linear_algebra")
