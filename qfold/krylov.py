"""
§AY QLA-1 — Krylov / Lanczos minimal-polynomial → C-finite (the top-priority recognition branch).
================================================================================================================
A fixed linear iteration v_{k+1}=A·v_k (or any moment s_k=wᵀAᵏv) is governed by the MINIMAL POLYNOMIAL of A on
the Krylov space: μ_{A,v}(A)v=0 ⟹ Aᵐv = Σ_{i<m} c_i Aⁱv, so the moment sequence obeys an order-m linear
recurrence. Recognize it by Berlekamp–Massey over ℚ (REUSE native_sequence) → companion form (REUSE cfinite).

★ ∀-k = the minimal-polynomial / companion-matrix THEOREM (§0-b), NOT z3 induction. The gate is exact held-out
replay: the recovered recurrence must predict TRUE moments BEYOND the BM training window (catches a spurious low
fit). EXACT only for integer/rational A (float ⇒ BM breaks ⇒ DECLINE — never a float-EXACT, §1-Q3).
★ Axis A: matrix-iteration / quadratic-form accumulation recognized as C-finite. Axis B (NEVER summed): the loop
O(N·matvec) collapses to O(m³·log N) via companion power-by-squaring — a real speedup ONLY when m ≪ N.
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Optional, Sequence

import cfinite
import kernel_verdict as KV
import native_sequence as NS

from . import _la


def _moment_seq(A, v, w, count: int) -> List[Fraction]:
    """s_k = wᵀ Aᵏ v for k=0..count-1 (exact rational)."""
    u = v[:]
    out = []
    for _ in range(count):
        out.append(_la.dot(w, u))
        u = _la.matvec(A, u)
    return out


def _fold_seq(seq: Sequence[Fraction], held_out: int = 6):
    """BM-fold a scalar sequence with an EXACT held-out replay gate. Returns (c, init, L) or None.
    Soundness: BM on the training prefix, then companion_nth must reproduce the held-out TRUE tail exactly — a
    spurious low-order fit fails this. Convention bridge: BM gives C with s[i]=−Σ C[j]s[i−j] ⇒ cfinite c[j−1]=−C[j]."""
    s = [Fraction(x) for x in seq]
    n = len(s)
    if n < 8 or held_out < 3 or n - held_out < 4:
        return None
    train = s[: n - held_out]
    C, L = NS.berlekamp_massey_Q(train)
    if L == 0:
        return None
    if 2 * L > len(train) - 2:                                   # L ≈ n/2 — no short recurrence ⇒ random signature
        return None
    if not NS._verify_recurrence(train, C, L):                  # candidate must fit the whole training window
        return None
    c = [-C[j] for j in range(1, L + 1)]                        # cfinite convention: f(n)=Σ c[j]·f(n-1-j)
    init = s[:L]
    for k in range(n - held_out, n):                           # ★ held-out replay on TRUE tail (the sound gate)
        if cfinite.companion_nth(c, init, k) != s[k]:
            return None
    return c, init, L


def detect_krylov_cfinite(A: Sequence[Sequence], v: Sequence, w: Optional[Sequence] = None) -> KV.Verdict:
    """Recognize a fixed linear iteration / moment stream as C-finite via its minimal polynomial. EXACT (integer/
    rational A) gated by held-out replay, or DECLINE (float / no short recurrence / fails replay)."""
    try:
        Af, vf = _la.fmat(A), _la.fvec(v)
        wf = _la.fvec(w) if w is not None else [Fraction(1)] * len(vf)
    except _la.NonExact as e:
        return KV.decline(f"krylov: {e} — float matrix breaks exact BM ⇒ DECLINE (no float-EXACT)", "krylov_minpoly")
    n = len(Af)
    if n == 0 or len(vf) != n or len(wf) != n:
        return KV.decline("krylov: empty/mismatched dimensions", "krylov_minpoly")
    held = 8
    seq = _moment_seq(Af, vf, wf, 2 * n + 4 + held)
    folded = _fold_seq(seq, held_out=held)
    if folded is None:
        return KV.decline(f"krylov: moment sequence has no short recurrence (linear complexity ≈ n/2) or fails "
                          f"held-out replay ⇒ no finite invariant subspace seen ⇒ DECLINE", "krylov_minpoly")
    c, init, L = folded
    # ★ structural strengthener: does the recurrence lift to the OPERATOR level (Aᴸv = Σ cᵢ A^{L-1-i} v, residual 0)?
    operator_level = _operator_dependence(Af, vf, c, L)
    coeffs = [str(x) for x in c]
    detail = (f"minimal-polynomial recurrence order L={L} on the Krylov space; moments s_k=wᵀAᵏv satisfy "
              f"s_k=Σcⱼ·s_{{k-1-j}}, c={coeffs}; companion held-out replay ✓ on TRUE moments beyond the BM window"
              + ("; operator-level Aᴸv=Σcᵢ·Aⁱv residual=0 (Cayley–Hamilton on Krylov)" if operator_level else ""))
    cert = KV.Cert(KV.EXACT, "krylov_companion_replay", passed=True,
                   check_cost=f"O(L²) BM + exact held-out replay on {held} true moments", detail=detail)
    return KV.exact({"order": L, "coeffs": coeffs, "operator_level": operator_level,
                     "predict": lambda N, _c=c, _i=init: cfinite.companion_nth(_c, _i, N)},
                    "krylov_minpoly_cfinite", f"O(L³·log N) companion power (L={L})", cert,
                    reason="Axis-B speedup O(N·matvec)→O(L³·log N) holds only when L≪N (crossover); Axis-A = "
                           "matrix-iteration recognized as C-finite")


def _operator_dependence(A, v, c, L) -> bool:
    """Exact check Aᴸ v == Σ_{i=0}^{L-1} c_i · A^{L-1-i} v (vector residual 0 over ℚ) — the operator-level minimal
    polynomial witness (stronger than moment replay; ∀-k by Cayley–Hamilton on the Krylov subspace)."""
    u = [v[:]]
    for _ in range(L):
        u.append(_la.matvec(A, u[-1]))
    rhs = [Fraction(0)] * len(v)
    for i in range(L):
        ui = u[L - 1 - i]
        rhs = [rhs[t] + c[i] * ui[t] for t in range(len(v))]
    return all(u[L][t] == rhs[t] for t in range(len(v)))


def fold_moment_sequence(seq: Sequence) -> KV.Verdict:
    """Fold a raw scalar moment stream (e.g. wᵀAᵏv already materialised) — EXACT iff a short recurrence held-out
    replays, else DECLINE. The black-box face of QLA-1 (a random stream ⇒ L≈n/2 ⇒ honest DECLINE)."""
    try:
        s = [Fraction(x) for x in seq]
    except (ValueError, TypeError):
        return KV.decline("krylov: non-exact moment stream ⇒ DECLINE", "krylov_minpoly")
    folded = _fold_seq(s, held_out=max(4, len(s) // 4))
    if folded is None:
        return KV.decline("krylov: moment stream has no short recurrence / fails held-out replay ⇒ DECLINE",
                          "krylov_minpoly")
    c, init, L = folded
    cert = KV.Cert(KV.EXACT, "krylov_companion_replay", passed=True, check_cost="BM + held-out replay",
                   detail=f"order-{L} linear recurrence, held-out replay ✓")
    return KV.exact({"order": L, "coeffs": [str(x) for x in c]}, "krylov_minpoly_cfinite",
                    f"O(L³·log N) (L={L})", cert)


def adversarial_battery() -> dict:
    """★ EXACT: Fibonacci companion + a 3×3 integer iteration fold to their minimal-poly recurrences (held-out
    replay ✓, operator-level ✓). ★★ DECLINE boundary: a FLOAT matrix (no float-EXACT) and a genuinely random
    moment stream (linear complexity ≈ n/2) both DECLINE — no false-EXACT."""
    # EXACT — Fibonacci companion [[1,1],[1,0]], v=e0 ⇒ moments are Fibonacci-like, order-2 recurrence c=[1,1]
    fib = detect_krylov_cfinite([[1, 1], [1, 0]], [1, 0], [1, 0])
    fib_ok = fib.status == KV.EXACT and fib.result["order"] == 2 and fib.result["coeffs"] == ["1", "1"]
    true_s15 = _moment_seq(_la.fmat([[1, 1], [1, 0]]), _la.fvec([1, 0]), _la.fvec([1, 0]), 16)[15]  # brute-force moment
    fib_predict = fib.status == KV.EXACT and fib.result["predict"](15) == true_s15                 # ∀-N closed form ✓
    # EXACT — a 3×3 integer matrix with a cyclic vector (min poly degree 3), moments fold
    A3 = [[2, 1, 0], [0, 2, 1], [0, 0, 3]]
    m3 = detect_krylov_cfinite(A3, [1, 1, 1], [1, 0, 0])
    m3_ok = m3.status == KV.EXACT and m3.result["operator_level"]
    # DECLINE — float matrix (no float-EXACT)
    flt = detect_krylov_cfinite([[1.5, 0.0], [0.0, 0.5]], [1.0, 1.0])
    flt_declines = flt.status == KV.DECLINE
    # DECLINE — a genuinely random moment stream (high linear complexity ⇒ L≈n/2)
    import hashlib
    rnd = [int.from_bytes(hashlib.sha256(str(k).encode()).digest()[:4], "big") for k in range(40)]
    rnd_declines = fold_moment_sequence(rnd).status == KV.DECLINE
    cases = {"fibonacci_exact": fib_ok, "fibonacci_predict_matches": fib_predict, "matrix3_exact_operator": m3_ok,
             "float_declines": flt_declines, "random_moment_declines": rnd_declines}
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, x in cases.items() if not x]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
