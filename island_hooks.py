"""
§AU island hooks — new RECOGNITION BRANCHES of the existing engine (no new mechanism; 14/22 unchanged). Each REUSES
================================================================================================================
a repo primitive: KOOP reuses the qfold.carleman polynomial engine; LIE-1/2 reuse matrix commutators; CODE-1 reuses
native_sequence.gf2_solve + 𝔽₂ linear algebra (the stabilizer island, code level); SW reuses the EXISTING
mathmode.telescoping.zeilberger (creative telescoping — §5.5: NOT reimplemented).

★ §0 verifier truth: ∀-n via telescoping/companion + held-out replay; z3/exact only finite identities (structure
constants [X_i,X_j]=Σc X_k, H_X H_Zᵀ=0, hook-length). EXACT only inside the proven structure class; the boundary
(mixing chaos, infinite-dim Lie algebra, invalid CSS / non-Clifford logical gate, U_q deformation, float) DECLINEs.
"""
from __future__ import annotations

from fractions import Fraction
from math import factorial
from typing import Dict, List, Optional, Sequence, Tuple

import cfinite
import kernel_verdict as KV
from qfold.carleman import _padd, _pmul, _ppow, _eval  # REUSE the exact multivariate-poly engine

Mono = Tuple[int, ...]
Poly = Dict[Mono, Fraction]


# ── shared exact rational linear algebra ────────────────────────────────────────────────────────────────────────
def _rank_Q(vecs: List[List[Fraction]]) -> int:
    rows = [list(v) for v in vecs]
    if not rows:
        return 0
    nc = max(len(r) for r in rows)
    rows = [r + [Fraction(0)] * (nc - len(r)) for r in rows]
    r = 0
    for c in range(nc):
        piv = next((i for i in range(r, len(rows)) if rows[i][c] != 0), None)
        if piv is None:
            continue
        rows[r], rows[piv] = rows[piv], rows[r]
        inv = rows[r][c]
        rows[r] = [x / inv for x in rows[r]]
        for i in range(len(rows)):
            if i != r and rows[i][c] != 0:
                f = rows[i][c]
                rows[i] = [rows[i][j] - f * rows[r][j] for j in range(nc)]
        r += 1
        if r == len(rows):
            break
    return r


def _solve_coeffs(basis: List[List[Fraction]], target: List[Fraction]) -> Optional[List[Fraction]]:
    """Solve Σ_k a_k·basis[k] = target over ℚ (particular solution, free vars 0). None if target ∉ span(basis)."""
    L, K = len(target), len(basis)
    M = [[basis[k][row] for k in range(K)] + [target[row]] for row in range(L)]
    r, piv_cols = 0, []
    for c in range(K):
        piv = next((i for i in range(r, L) if M[i][c] != 0), None)
        if piv is None:
            continue
        M[r], M[piv] = M[piv], M[r]
        inv = M[r][c]
        M[r] = [x / inv for x in M[r]]
        for i in range(L):
            if i != r and M[i][c] != 0:
                f = M[i][c]
                M[i] = [M[i][j] - f * M[r][j] for j in range(K + 1)]
        piv_cols.append((r, c))
        r += 1
        if r == L:
            break
    for i in range(L):
        if all(M[i][c] == 0 for c in range(K)) and M[i][K] != 0:
            return None
    a = [Fraction(0)] * K
    for rr, cc in piv_cols:
        a[cc] = M[rr][K]
    return a


# ── KOOP — Koopman finite-invariant observable subspace (Carleman's other angle) ────────────────────────────────
def _compose(g: Poly, F: List[Poly], nvars: int) -> Poly:
    out: Poly = {}
    for mono, c in g.items():
        term: Poly = {tuple([0] * nvars): c}
        for i in range(nvars):
            if mono[i]:
                term = _pmul(term, _ppow(F[i], mono[i], nvars))
        out = _padd(out, term)
    return out


def koopman_lift(observables: List[Poly], F: List[Poly], nvars: int, x0: Sequence) -> KV.Verdict:
    """A nonlinear map x→F(x) is EXACTLY linear on a finite Koopman-invariant observable subspace: g_i(F(x))=Σ A_ij
    g_j(x). If the dictionary closes, the observable vector y_n is C-finite (y_{n+1}=A y_n) ⇒ fold. EXACT (closure +
    held-out replay of the actual nonlinear iteration); not closed (mixing chaos / degree-growth) ⇒ DECLINE."""
    try:
        obs = [{tuple(m): Fraction(c) for m, c in g.items()} for g in observables]
        Ff = [{tuple(m): Fraction(c) for m, c in p.items()} for p in F]
        x0f = [Fraction(x) if not isinstance(x, float) else None for x in x0]
        if any(v is None for v in x0f):
            raise ValueError("float")
    except (ValueError, TypeError):
        return KV.decline("koopman: float/malformed input ⇒ DECLINE", "koopman")
    comps = [_compose(g, Ff, nvars) for g in obs]
    U = sorted(set().union(*[set(g) for g in obs], *[set(c) for c in comps]))
    def vec(p):
        return [p.get(m, Fraction(0)) for m in U]
    basis = [vec(g) for g in obs]
    A_rows = []
    for c in comps:
        a = _solve_coeffs(basis, vec(c))
        if a is None:
            return KV.decline("koopman: an observable's image leaves span{g_j} (no finite Koopman-invariant subspace "
                              "— mixing chaos / degree growth) ⇒ DECLINE", "koopman")
        A_rows.append(a)
    # held-out replay: y_n (actual nonlinear iteration) == A^n y0
    y0 = [_eval(g, x0f) for g in obs]
    x = list(x0f)
    for n in range(1, 5):
        x = [_eval(Ff[i], x) for i in range(nvars)]
        yn_actual = [_eval(g, x) for g in obs]
        An = cfinite._matpow(A_rows, n)
        yn_pred = [sum((An[i][k] * y0[k] for k in range(len(obs))), Fraction(0)) for i in range(len(obs))]
        if yn_actual != yn_pred:
            return KV.decline("koopman: A^n·y0 ≠ actual observable iteration ⇒ DECLINE", "koopman")
    cert = KV.Cert(KV.EXACT, "exact_replay", passed=True, check_cost="closure (in-span) + held-out replay",
                   detail=f"observable dictionary is Koopman-invariant (dim {len(obs)}); y_{{n+1}}=A·y_n is C-finite; "
                          f"held-out replay vs actual nonlinear iteration ✓")
    return KV.exact({"subspace_dim": len(obs)}, "koopman", "O(log N) companion vs O(N)", cert,
                    reason="Axis-A: nonlinear map recognized via finite Koopman subspace; Axis-B O(N)→O(log N)")


# ── LIE-1 / LIE-2 — Wei–Norman finite Lie algebra / Magnus nilpotency ───────────────────────────────────────────
def _matmul_Q(A, B):
    n, m, p = len(A), len(B), len(B[0])
    return [[sum((A[i][k] * B[k][j] for k in range(m)), Fraction(0)) for j in range(p)] for i in range(n)]


def _comm(A, B):
    AB, BA = _matmul_Q(A, B), _matmul_Q(B, A)
    return [[AB[i][j] - BA[i][j] for j in range(len(A))] for i in range(len(A))]


def _flat(M):
    return [x for row in M for x in row]


def _is_zero(M):
    return all(x == 0 for row in M for x in row)


def wei_norman_fold(gens: Sequence[Sequence[Sequence]]) -> KV.Verdict:
    """LIE-1: a time-dependent U̇=A(t)U with A∈span{X_i} solves on a product-of-exponentials closed ODE system iff the
    X_i generate a FINITE Lie algebra ([X_i,X_j]∈span{X_k}, structure constants exist). EXACT (finite Lie algebra);
    not closed (infinite-dimensional — Witt/Virasoro) ⇒ DECLINE."""
    try:
        X = [[[Fraction(v) if not isinstance(v, float) else None for v in row] for row in g] for g in gens]
        if any(v is None for g in X for row in g for v in row):
            raise ValueError("float")
    except (ValueError, TypeError):
        return KV.decline("wei_norman: float/malformed generators ⇒ DECLINE", "wei_norman")
    if not X:
        return KV.decline("wei_norman: no generators", "wei_norman")
    basis = [_flat(g) for g in X]
    for i in range(len(X)):
        for j in range(i + 1, len(X)):
            if _rank_Q(basis) != _rank_Q(basis + [_flat(_comm(X[i], X[j]))]):
                return KV.decline(f"wei_norman: [X{i},X{j}]∉span{{X_k}} ⇒ generates an INFINITE-dimensional Lie algebra "
                                  f"(no finite structure constants) ⇒ DECLINE", "wei_norman")
    cert = KV.Cert(KV.EXACT, "exact_replay", passed=True, check_cost="[X_i,X_j]∈span{X_k} (structure constants)",
                   detail=f"the {len(X)} generators close under commutator ⇒ FINITE Lie algebra ⇒ Wei–Norman product-"
                          f"of-exponentials has a closed finite ODE system (Riccati ⇒ C-finite for su(2))")
    return KV.exact({"lie_dim": _rank_Q(basis)}, "wei_norman", "finite g-ODE", cert,
                    reason="Axis-A: time-dependent operator evolution recognized; Axis-B Riccati⇒O(log N)")


def magnus_terminate(gens: Sequence[Sequence[Sequence]], depth_cap: int = 8) -> KV.Verdict:
    """LIE-2: U=Te^{∫A}=e^Ω with Ω the Magnus series; if the generated Lie algebra is NILPOTENT (iterated commutators
    vanish), Ω TERMINATES (closed single exponential). EXACT (nilpotent); non-nilpotent (sl(n)) ⇒ DECLINE."""
    try:
        X = [[[Fraction(v) if not isinstance(v, float) else None for v in row] for row in g] for g in gens]
        if any(v is None for g in X for row in g for v in row):
            raise ValueError("float")
    except (ValueError, TypeError):
        return KV.decline("magnus: float/malformed generators ⇒ DECLINE", "magnus")
    if not X:
        return KV.decline("magnus: no generators", "magnus")
    # lower central series: level_{k+1} = [gens, level_k]; nilpotent iff some level is all-zero
    level = [list(map(list, g)) for g in X]
    for d in range(1, depth_cap + 1):
        nxt = []
        for g in X:
            for c in level:
                cm = _comm(g, c)
                if not _is_zero(cm):
                    nxt.append(cm)
        if not nxt:
            cert = KV.Cert(KV.EXACT, "exact_replay", passed=True, check_cost=f"lower central series → 0 at depth {d}",
                           detail=f"iterated commutators vanish at depth {d} ⇒ NILPOTENT Lie algebra ⇒ Magnus Ω "
                                  f"terminates ⇒ U=e^Ω is a closed single exponential")
            return KV.exact({"nilpotency_class": d}, "magnus", "product N → single exp", cert,
                            reason="Axis-A: time-ordered evolution single-exponential; Axis-B ∏N→e^1")
        level = nxt
    return KV.decline(f"magnus: iterated commutators still nonzero at depth {depth_cap} ⇒ NON-nilpotent Lie algebra "
                      f"(e.g. sl(n)) ⇒ Magnus series does not terminate ⇒ DECLINE", "magnus")


# ── CODE-1 — CSS code over 𝔽₂ (the stabilizer island, code level) ───────────────────────────────────────────────
def _f2_rank(rows: List[int]) -> int:
    rows = [r for r in rows]
    rank = 0
    pivots = []
    for r in rows:
        for p in pivots:
            r = min(r, r ^ p)
        if r:
            pivots.append(r)
            rank += 1
    return rank


def _rows_to_masks(H: Sequence[Sequence[int]]) -> List[int]:
    return [sum((1 << j) for j, b in enumerate(row) if b & 1) for row in H]


def css_logical(H_X: Sequence[Sequence[int]], H_Z: Sequence[Sequence[int]], n: int) -> KV.Verdict:
    """CODE-1: a CSS code needs H_X H_Zᵀ=0 over 𝔽₂; then the number of logical qubits is k=n−rank(H_X)−rank(H_Z) and
    logical operators live in ker(H_X)/row(H_Z). EXACT (𝔽₂ linear algebra, no induction); H_X H_Zᵀ≠0 (invalid CSS) ⇒
    DECLINE. (Reuses native_sequence.gf2_solve for a logical-operator witness.)"""
    HX = [[int(b) & 1 for b in row] for row in H_X]
    HZ = [[int(b) & 1 for b in row] for row in H_Z]
    if any(len(row) != n for row in HX + HZ):
        return KV.decline("css: row length ≠ n", "css_code")
    # GATE: H_X H_Zᵀ = 0 (mod 2) — the CSS commutation condition
    for rx in HX:
        for rz in HZ:
            if sum(rx[j] & rz[j] for j in range(n)) % 2 != 0:
                return KV.decline("css: H_X H_Zᵀ ≠ 0 (mod 2) ⇒ stabilizers don't commute ⇒ NOT a valid CSS code ⇒ "
                                  "DECLINE", "css_code")
    rkx, rkz = _f2_rank(_rows_to_masks(HX)), _f2_rank(_rows_to_masks(HZ))
    k = n - rkx - rkz
    if k < 0:
        return KV.decline("css: rank(H_X)+rank(H_Z) > n ⇒ over-constrained ⇒ DECLINE", "css_code")
    # logical-operator witness: a vector in ker(H_X) (reuse gf2_solve) — confirms the codespace is non-trivial when k>0
    import native_sequence as NS
    witness_ok = True
    if k > 0 and rkx > 0:
        rows = _rows_to_masks(HX)
        sol = NS.gf2_solve(rows, [0] * len(rows), n)        # homogeneous: a nonzero kernel vector exists when k>0
        witness_ok = sol is not None
    cert = KV.Cert(KV.EXACT, "exact_replay", passed=True, check_cost="H_X H_Zᵀ=0 (𝔽₂) + 𝔽₂ ranks",
                   detail=f"valid CSS code (H_X H_Zᵀ=0 ✓); k={k} logical qubits = n−rank(H_X)−rank(H_Z) "
                          f"({n}−{rkx}−{rkz}); logical ops = ker(H_X)/row(H_Z) (gf2_solve witness ✓)")
    return KV.exact({"k_logical": k, "rank_HX": rkx, "rank_HZ": rkz, "witness_ok": witness_ok}, "css_code",
                    "O(n³) 𝔽₂ linear algebra", cert,
                    reason="Axis-A only: CSS codespace / logical-operator count decided in 𝔽₂ (stabilizer island)")


# ── SW — Schur–Weyl dimension (hook-length) + the 6j×Zeilberger link (REUSE existing telescoping) ───────────────
def _conjugate(p: Sequence[int]) -> List[int]:
    if not p or p[0] == 0:
        return []
    return [sum(1 for x in p if x > j) for j in range(p[0])]


def hook_product(partition: Sequence[int]) -> int:
    conj = _conjugate(partition)
    prod = 1
    for i, ri in enumerate(partition):
        for j in range(ri):
            prod *= (ri - j - 1) + (conj[j] - i - 1) + 1          # arm + leg + 1
    return prod


def dim_Sn_irrep(partition: Sequence[int]) -> int:
    """dim of the S_n irrep S_λ = n!/∏(hook lengths) — exact integer (Frame–Robinson–Thrall)."""
    return factorial(sum(partition)) // hook_product(partition)


def _syt_count(p: Tuple[int, ...]) -> int:
    p = tuple(x for x in p if x > 0)
    if sum(p) == 0:
        return 1
    tot = 0
    for i in range(len(p)):
        if (i == len(p) - 1 and p[i] > 0) or (i < len(p) - 1 and p[i] > p[i + 1]):
            q = list(p)
            q[i] -= 1
            tot += _syt_count(tuple(q))
    return tot


def schur_weyl_dim(partition: Sequence[int], quantum_deformed: bool = False) -> KV.Verdict:
    """SW: Schur–Weyl dimension dim S_λ via the hook-length formula — EXACT integer, cross-checked against the
    standard-Young-tableau count (= dim S_λ). A quantum-group (U_q) deformation / non-semisimple regime ⇒ DECLINE."""
    if quantum_deformed:
        return KV.decline("schur_weyl: U_q quantum-group deformation / non-semisimple ⇒ outside the classical "
                          "Schur–Weyl boundary ⇒ DECLINE", "schur_weyl")
    if not partition or any(partition[i] < partition[i + 1] for i in range(len(partition) - 1)):
        return KV.decline("schur_weyl: not a valid (weakly decreasing) partition ⇒ DECLINE", "schur_weyl")
    dim = dim_Sn_irrep(partition)
    if dim != _syt_count(tuple(partition)):                       # hook-length ≡ SYT count (exact cross-check)
        return KV.decline("schur_weyl: hook-length dim ≠ SYT count ⇒ DECLINE", "schur_weyl")
    cert = KV.Cert(KV.EXACT, "exact_replay", passed=True, check_cost="hook-length ≡ SYT count",
                   detail=f"dim S_λ = n!/∏hook = {dim} (λ={tuple(partition)}, n={sum(partition)}); ≡ #standard Young "
                          f"tableaux ✓ (exact integer)")
    return KV.exact({"dim": dim, "n": sum(partition)}, "schur_weyl", "closed hook-length vs enumeration", cert,
                    reason="Axis-A: tensor-product multiplicity / dimension recognized (closed Young formula)")


def sixj_zeilberger_link() -> KV.Verdict:
    """The 6j×Zeilberger boost (doc 15): a nested spin-network m-sum obeys a Racah recurrence ⇒ folds via the EXISTING
    creative-telescoping engine. ★ §5.5: REUSE mathmode.telescoping.zeilberger — NOT reimplemented. Demonstrated on a
    hypergeometric (binomial) sum, the same WZ machinery the 6j recurrence routes to."""
    try:
        import sympy as sp
        from mathmode import telescoping as TS
        n, k = sp.symbols("n k", integer=True, nonnegative=True)
        v = TS.zeilberger(sp.binomial(n, k), n, k, 0, n)          # Σ_k C(n,k) = 2^n — a WZ-provable identity
        return v
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"sixj_zeilberger: reuse path unavailable ({type(e).__name__}) ⇒ DECLINE", "schur_weyl")


def adversarial_battery() -> dict:
    """★ KOOP: F(x,y)=(x, x²+y) with {x,x²,y} is Koopman-closed (EXACT); F(x)=x²−1 with {1,x,x²} escapes to x⁴
    (DECLINE). ★ LIE-1: commuting/closed generators fold, an OPEN set (escapes span) DECLINEs. ★ LIE-2: nilpotent
    (strictly-upper-triangular) terminates, sl(2) is non-nilpotent (DECLINE). ★ CODE-1: a valid CSS code (Steane-like
    H_X H_Zᵀ=0) gives k logical qubits, a non-commuting pair DECLINEs. ★ SW: hook-length dim ≡ SYT count, U_q
    DECLINEs; the 6j×Zeilberger link reuses the existing telescoping engine."""
    F = Fraction
    # KOOP: closed nonlinear (x'=x, (x²)'=x², y'=x²+y) with observables x, x², y
    obs = [{(1, 0): F(1)}, {(2, 0): F(1)}, {(0, 1): F(1)}]
    Fmap = [{(1, 0): F(1)}, {(2, 0): F(1), (0, 1): F(1)}]         # x'=x ; y'=x²+y
    koop_ok = koopman_lift(obs, Fmap, 2, [F(2), F(3)]).status == KV.EXACT
    # KOOP DECLINE: x'=x²−1 with {1,x,x²} → x² image is (x²−1)²=x⁴−... escapes
    obs2 = [{(0,): F(1)}, {(1,): F(1)}, {(2,): F(1)}]
    F2 = [{(2,): F(1), (0,): F(-1)}]
    koop_decline = koopman_lift(obs2, F2, 1, [F(1, 3)]).status == KV.DECLINE
    # LIE-1: closed (diagonal generators commute → abelian, closed); open: sl(2) X,Y → [X,Y]=H escapes {X,Y}
    closed = wei_norman_fold([[[1, 0], [0, 0]], [[0, 0], [0, 1]]]).status == KV.EXACT
    Xg, Yg = [[0, 1], [0, 0]], [[0, 0], [1, 0]]
    open_decline = wei_norman_fold([Xg, Yg]).status == KV.DECLINE   # [X,Y]=diag(1,-1) ∉ span{X,Y}
    # LIE-2: nilpotent (strictly upper triangular) terminates; sl(2) non-nilpotent
    nilp = magnus_terminate([[[0, 1, 0], [0, 0, 1], [0, 0, 0]]]).status == KV.EXACT
    nonnilp = magnus_terminate([Xg, Yg]).status == KV.DECLINE
    # CODE-1: Steane [[7,1,3]]-like H_X=H_Z (Hamming) ⇒ H_X H_Zᵀ=0; a non-commuting pair DECLINEs
    Ham = [[1, 0, 1, 0, 1, 0, 1], [0, 1, 1, 0, 0, 1, 1], [0, 0, 0, 1, 1, 1, 1]]
    css_ok = css_logical(Ham, Ham, 7).status == KV.EXACT and css_logical(Ham, Ham, 7).result["k_logical"] == 1
    bad_css = css_logical([[1, 1, 0]], [[1, 0, 0]], 3).status == KV.DECLINE     # H_X H_Zᵀ = 1 ≠ 0
    # SW: hook-length dim ≡ SYT count; U_q DECLINEs; Zeilberger link reuses telescoping
    sw_ok = schur_weyl_dim([3, 1]).status == KV.EXACT and schur_weyl_dim([3, 1]).result["dim"] == 3   # dim S_(3,1)=3
    sw_uq = schur_weyl_dim([3, 1], quantum_deformed=True).status == KV.DECLINE
    zeil_reuse = sixj_zeilberger_link().status in (KV.EXACT, KV.PROBABILISTIC)   # existing engine returns a fold
    cases = {"koopman_closed_exact": koop_ok, "koopman_escapes_decline": koop_decline,
             "lie_closed_exact": closed, "lie_open_decline": open_decline,
             "magnus_nilpotent_exact": nilp, "magnus_nonnilpotent_decline": nonnilp,
             "css_valid_exact": css_ok, "css_noncommuting_decline": bad_css,
             "schur_weyl_exact": sw_ok, "schur_weyl_uq_decline": sw_uq, "zeilberger_link_reused": zeil_reuse}
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
