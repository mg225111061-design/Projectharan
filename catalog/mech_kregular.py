"""
POST-CONSOLIDATION PHASE 1f — ★ k-REGULAR SEQUENCE FOLD (M22, the one brand-new mechanism). Allouche–Shallit 1992.
=================================================================================================================
A sequence a(n) is k-REGULAR iff its k-KERNEL  K_k(a) = { (a(kᵉ·n+r))ₙ : e≥0, 0≤r<kᵉ }  generates a FINITELY
GENERATED ℤ-module. Equivalently it has a LINEAR REPRESENTATION indexed by the BASE-k DIGITS of n (NOT by n):
        a(n) = v · A_{d₀} · A_{d₁} · … · A_{dₛ} · w        (d₀d₁…dₛ = base-k digits of n, least-significant first)
with a 1×d row v, d×d digit-matrices A₀…A_{k−1}, and a d×1 column w. This is the structure HIDDEN in digit/bit
loops — popcount, digit-sum, Stern's diatomic, radix conversions, the summatory function of an automatic sequence.

★ WHY DISTINCT (the four-gate admission — it folds a class EVERY existing mechanism DECLINEs):
  • popcount(n) (binary digit-sum) is 2-regular yet is PROVABLY NOT C-finite — a C-finite integer sequence that is
    O(log n) must be eventually periodic, popcount is not — so M11 (Berlekamp–Massey) DECLINEs it, and so do M1/M13.
    A mechanism folding popcount/Stern is DISTINCT IN KIND (gate 1): a digit-indexed linear representation, NOT a
    recurrence in n. ✦ gate 2 (z3-closed): the certificate is a finite conjunction of LINEAR-INTEGER-ARITHMETIC
    equalities a(n)=v·∏A·w — checked exactly over ℚ in-repo and dischargeable in LIA (z3 spot-check, no external
    engine). ✦ gate 3 (asymptotic): O(n)→O(log n) — Stern/summatory eval collapses from an O(n) recurrence walk to
    an O(log_k n) matrix product. ✦ gate 4 (dependency-free): the k-kernel closure + Berstel–Reutenauer-style
    minimal-basis reduction are in-repo (Fraction only); z3 optional.

Decidable ISLAND (admitted): equality / zeroness of two k-regular linear representations is DECIDABLE (Krenn–
Shallit; a weighted-automaton equivalence = linear algebra on the reachable difference vectors). Undecidable
BOUNDARY (DECLINEd): general growth / positivity decisions on linear representations sit at the Skolem–Mahler–Lech
/ Hilbert-10th frontier (not known computable) ⇒ DECLINE, never a guess. The disposer is EXACT over ℚ: a candidate
representation that does not regenerate EVERY supplied term (residual 0) is rejected ⇒ a random sequence (k-kernel
never closes) DECLINEs. Precision stays 1.0.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Dict, List, Optional, Sequence, Tuple

import kernel_verdict as KV

Vec = Tuple[Fraction, ...]


# ── base-k digits, least-significant first (the order the matrices multiply in) ─────────────────────────
def base_k_digits(n: int, k: int) -> List[int]:
    if n == 0:
        return [0]
    out: List[int] = []
    while n > 0:
        out.append(n % k)
        n //= k
    return out


# ── exact ℚ linear algebra: express `target` as a combination of independent `cols` (unique or None) ─────
def _solve_combo(cols: List[Vec], target: Vec) -> Optional[List[Fraction]]:
    """Solve Σ cⱼ·cols[j] = target over ℚ. cols are linearly independent (an echelon basis is maintained by the
    caller), so the solution is unique when it exists; returns the coefficient list, or None if target ∉ span."""
    m = len(target)
    d = len(cols)
    # augmented matrix [cols | target], rows = m coordinates, columns = d basis vectors + 1
    A = [[cols[j][i] for j in range(d)] + [target[i]] for i in range(m)]
    piv_rows: List[Tuple[int, int]] = []
    r = 0
    for c in range(d):
        piv = next((rr for rr in range(r, m) if A[rr][c] != 0), None)
        if piv is None:
            continue
        A[r], A[piv] = A[piv], A[r]
        inv = Fraction(1) / A[r][c]
        A[r] = [x * inv for x in A[r]]
        for rr in range(m):
            if rr != r and A[rr][c] != 0:
                f = A[rr][c]
                A[rr] = [a - f * b for a, b in zip(A[rr], A[r])]
        piv_rows.append((r, c))
        r += 1
    # consistency: any all-zero-in-the-d-block row must have zero RHS
    for rr in range(m):
        if all(A[rr][c] == 0 for c in range(d)) and A[rr][d] != 0:
            return None
    coeffs = [Fraction(0)] * d
    for (rr, cc) in piv_rows:
        coeffs[cc] = A[rr][d]
    return coeffs


def _independent(cols: List[Vec], target: Vec) -> bool:
    return _solve_combo(cols, target) is None


# ── the k-kernel closure: build the minimal linear representation (v, {Aⱼ}, w) from a finite sample ─────
def _sample(a: Sequence[Fraction], e: int, r: int, k: int, L: int) -> Optional[Vec]:
    """The kernel subsequence S_{e,r}(n) = a(kᵉ·n + r) sampled on n=0..L-1; None if the window exceeds the data."""
    ke = k ** e
    hi = ke * (L - 1) + r
    if hi >= len(a):
        return None
    return tuple(a[ke * n + r] for n in range(L))


def build_representation(a: Sequence[Fraction], k: int, L: int, dmax: int
                         ) -> Optional[Tuple[List[List[List[Fraction]]], List[Fraction], List[Fraction], List[Tuple[int, int]]]]:
    """Greedy k-kernel automaton closure (the Berstel–Reutenauer construction). States = kernel subsequences
    S_{e,r}, child(e,r,j) = S_{e+1, kᵉ·j+r}. Returns (A[0..k-1], v, w, basis) or None if it fails to close within
    `dmax` states or the data is insufficient to sample a needed child."""
    basis: List[Tuple[int, int]] = [(0, 0)]                      # state 0 = a itself (S_{0,0})
    vecs: List[Vec] = []
    s0 = _sample(a, 0, 0, k, L)
    if s0 is None:
        return None
    vecs.append(s0)
    A_rows: Dict[int, List[Optional[List[Fraction]]]] = {j: [] for j in range(k)}
    i = 0
    while i < len(basis):
        e, r = basis[i]
        for j in range(k):
            ce, cr = e + 1, (k ** e) * j + r
            child = _sample(a, ce, cr, k, L)
            if child is None:
                return None                                     # insufficient data to certify this transition
            if _independent(vecs, child):                       # a genuinely new kernel state
                if len(basis) >= dmax:
                    return None                                 # kernel did not close within dmax ⇒ not (low-dim) regular
                basis.append((ce, cr))
                vecs.append(child)
            # (re)solve every pending row once the basis may have grown — done after the BFS below
        i += 1
    # now the basis is closed; compute each transition row as a combination in the FINAL basis
    d = len(basis)
    A = [[[Fraction(0)] * d for _ in range(d)] for _ in range(k)]
    for i2, (e, r) in enumerate(basis):
        for j in range(k):
            ce, cr = e + 1, (k ** e) * j + r
            child = _sample(a, ce, cr, k, L)
            coeffs = _solve_combo(vecs, child)
            if coeffs is None:
                return None
            A[j][i2] = coeffs                                   # row i2 of A_j: child(i2,j) = Σ coeffs·basis
    v = [Fraction(1)] + [Fraction(0)] * (d - 1)                 # pick state 0 (= a)
    w = [a[r] for (_, r) in basis]                              # w_i = S_{e_i,r_i}(0) = a[r_i]
    return A, v, w, basis


# ── evaluate the representation: a(n) = v · A_{d0} … A_{ds} · w  (digits LSB-first) ─────────────────────
def eval_representation(A: List[List[List[Fraction]]], v: List[Fraction], w: List[Fraction], n: int, k: int) -> Fraction:
    d = len(v)
    col = list(w)                                               # column vector b(0)
    for dig in reversed(base_k_digits(n, k)):                   # apply most-significant first onto the right
        col = [sum(A[dig][i][l] * col[l] for l in range(d)) for i in range(d)]
    return sum(v[i] * col[i] for i in range(d))


def _is_int_seq(x, lo: int = 16) -> bool:
    return (isinstance(x, (list, tuple)) and len(x) >= lo
            and all(isinstance(t, int) and not isinstance(t, bool) for t in x))


def kregular_grade(seq, k: int = 2, dmax: int = 16) -> KV.Verdict:
    """Fold an integer sequence as k-REGULAR: build the minimal digit-indexed linear representation from its
    k-kernel and DISPOSE by exact ℚ re-substitution — require a(n) = v·∏A_{digit(n)}·w for EVERY supplied term.
    A sequence whose k-kernel never closes within `dmax` states (random / non-automatic) ⇒ DECLINE. The matrices
    are the certificate (LIA, z3-spot-checkable)."""
    if not _is_int_seq(seq):
        return KV.decline("kregular: need an integer sequence of length ≥ 16", "mech_kregular")
    N = len(seq)
    a = [Fraction(t) for t in seq]
    # adaptive fitting window: a child at kernel-depth D needs k^D·(L-1) < N, so try DESCENDING depth budgets and
    # take the LARGEST window whose representation passes the exact disposer (the disposer is the binding gate).
    cand_L = sorted({max(6, min(N // (k ** D), 60)) for D in range(1, 7)}, reverse=True)
    rep = None
    L = cand_L[-1]
    for Ltry in cand_L:
        r = build_representation(a, k, Ltry, dmax)
        if r is None:
            continue
        A, v, w, basis = r
        if all(eval_representation(A, v, w, n, k) == a[n] for n in range(N)):   # ★ EXACT disposer over ℚ ★
            rep, L = r, Ltry
            break
    if rep is None:
        return KV.decline(f"kregular: no k-kernel (k={k}) closed within {dmax} states and regenerated every term "
                          "(non-automatic / random / too high-dimensional) ⇒ DECLINE", "mech_kregular")
    A, v, w, basis = rep
    d = len(basis)
    params = k * d * d + 2 * d
    if params >= N:                                            # the representation must be a genuine COMPRESSION
        return KV.decline(f"kregular: representation has {params} parameters ≥ {N} terms — no compression ⇒ DECLINE",
                          "mech_kregular")
    # the fold-class proof: a low-dimension representation reproduced ALL terms (held-out tail beyond the window)
    z3ok = _z3_spotcheck(A, v, w, seq, k)
    cert = KV.Cert(KV.EXACT, "kregular_linear_representation", passed=True,
                   check_cost=f"exact ℚ re-substitution over all {N} terms (≥{N - L} held out beyond the fit window); "
                              f"LIA equalities z3-{'discharged' if z3ok else 'expressible'}",
                   detail=f"k={k} digit-indexed linear representation, dimension d={d} ({params} params ≪ {N} terms); "
                          f"a(n)=v·∏A_{{digit}}·w regenerates every term, residual=0 — a class M11/M1/M13 DECLINE "
                          "(automatic / non-C-finite, e.g. popcount, Stern)")
    return KV.exact({"k": k, "dimension": d, "params": params, "n_terms": N, "kernel_basis": basis,
                     "matrices": [[[str(x) for x in row] for row in A[j]] for j in range(k)],
                     "v": [str(x) for x in v], "w": [str(x) for x in w]},
                    "mech_kregular", f"k-regular fold (k={k}, dim {d}), O(n)→O(log n)", cert)


# ── z3-closure witness: discharge a sample of the LIA equalities a(n) = v·∏A·w (best-effort; no hard dep) ─
def _z3_spotcheck(A, v, w, seq, k: int, sample: int = 8) -> bool:
    """Demonstrate the certificate lives in LINEAR INTEGER ARITHMETIC: assert v·∏A_{digit}·w == a(n) and check the
    negation is UNSAT in z3 for a sample of n. Best-effort (z3 is a lazy/optional heavy dep); the binding gate is the
    exact ℚ re-substitution above. Returns True iff z3 confirmed the sample (or there is nothing to disprove)."""
    try:
        import z3
    except Exception:  # noqa: BLE001
        return False
    d = len(v)
    pts = list(range(min(sample, len(seq)))) + [len(seq) - 1]
    s = z3.Solver()
    bad = z3.Bool("mismatch")
    clauses = []
    for n in set(pts):
        # build the integer product symbolically over CONCRETE rational entries → an LIA term
        col = [z3.RealVal(int(w[i].numerator)) / z3.RealVal(int(w[i].denominator)) for i in range(d)]
        for dig in reversed(base_k_digits(n, k)):
            col = [z3.Sum([z3.RealVal(int(A[dig][i][l].numerator)) / z3.RealVal(int(A[dig][i][l].denominator)) * col[l]
                           for l in range(d)]) for i in range(d)]
        val = z3.Sum([z3.RealVal(int(v[i].numerator)) / z3.RealVal(int(v[i].denominator)) * col[i] for i in range(d)])
        clauses.append(val != z3.RealVal(int(seq[n])))
    s.add(z3.Or(clauses) == bad)
    s.add(bad)
    return s.check() == z3.unsat


# ── the DECIDABLE ISLAND (admitted): equality / zeroness of two k-regular representations (Krenn–Shallit) ─
def representations_equal(rep1, rep2, k: int, horizon: int = 64) -> bool:
    """Decide a(n) ≡ b(n) for two k-regular linear representations via the reachable-difference-vector basis (a
    weighted-automaton equivalence = exact linear algebra). DECIDABLE island. We grow the basis of reachable
    difference states under the k digit-actions; equality holds iff every reachable state has output 0."""
    A1, v1, w1 = rep1
    A2, v2, w2 = rep2
    d1, d2 = len(v1), len(v2)
    # state = concatenated column (b1(n), b2(n)); start from w (n=0 chain), explore digit-actions; output = v1·c1 − v2·c2
    start = tuple(w1) + tuple(w2)
    seen: List[Vec] = []
    frontier = [start]
    while frontier:
        st = frontier.pop()
        c1, c2 = list(st[:d1]), list(st[d1:])
        out = sum(v1[i] * c1[i] for i in range(d1)) - sum(v2[i] * c2[i] for i in range(d2))
        if out != 0:
            return False                                       # a reachable difference is nonzero ⇒ not equal
        if _independent(seen, st) if seen else True:
            seen.append(st)
            if len(seen) > horizon:
                break                                          # safety; for true k-regular reps this closes quickly
            for j in range(k):
                n1 = tuple(sum(A1[j][i][l] * c1[l] for l in range(d1)) for i in range(d1))
                n2 = tuple(sum(A2[j][i][l] * c2[l] for l in range(d2)) for i in range(d2))
                frontier.append(n1 + n2)
    return True


def growth_query(_rep, _k: int) -> KV.Verdict:
    """The UNDECIDABLE BOUNDARY: a general growth / positivity decision on a linear representation (is a(n)>0 ∀n?
    is a(n)=Ω(n)?) sits at the Skolem–Mahler–Lech / Hilbert-10th frontier — not known computable ⇒ DECLINE."""
    return KV.decline("kregular: general growth/positivity of a linear representation is at the Skolem–Mahler–Lech / "
                      "Hilbert-10th frontier (not known decidable) ⇒ DECLINE (the equality/zeroness island IS "
                      "decided; this boundary is not)", "mech_kregular")


# ── the distinct-vs-existing adjudication (mirrors mech_conley.distinct_vs_forced) ──────────────────────
def distinct_vs_existing() -> dict:
    """Prove M22 is GENUINELY DISTINCT: popcount(n) (2-regular) FOLDS here but the closest existing mechanism
    (M11 Berlekamp–Massey, C-finite/linear-recurrence) DECLINEs it — k-regular folds a class no prior mechanism
    folds. Returns the adjudication record."""
    import native_sequence as NS
    pc = [bin(n).count("1") for n in range(128)]                # popcount: 2-regular, NOT C-finite
    here = kregular_grade(pc, k=2)
    m11 = NS.bm_grade(pc)                                       # M11: must DECLINE (linear complexity ≈ n/2 grows)
    stern = _stern(128)
    stern_here = kregular_grade(stern, k=2)
    distinct = (here.status == KV.EXACT and m11.status == KV.DECLINE)
    return {"popcount_kregular": here.status, "popcount_M11_bm": m11.status,
            "stern_kregular": stern_here.status, "kregular_dim_popcount": here.result["dimension"] if here.status == KV.EXACT else None,
            "verdict": "DISTINCT (M22)" if distinct else "NOT DISTINCT", "net_new": 1 if distinct else 0,
            "reason": "popcount(n) is 2-regular and folds here (digit-indexed linear representation) but is provably "
                      "NOT C-finite (an O(log n) C-finite integer sequence must be eventually periodic; popcount is "
                      "not) ⇒ M11/M1/M13 DECLINE it — M22 folds a class no existing mechanism folds"}


def _stern(N: int) -> List[int]:
    """Stern's diatomic sequence: s(0)=0, s(1)=1, s(2n)=s(n), s(2n+1)=s(n)+s(n+1). The canonical 2-regular,
    non-C-finite sequence whose naive recurrence eval is O(n) and whose k-regular fold is O(log n)."""
    s = [0, 1]
    for n in range(2, N):
        s.append(s[n // 2] if n % 2 == 0 else s[n // 2] + s[n // 2 + 1])
    return s[:N]
