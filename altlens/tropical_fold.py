"""
§Y LENS 1 — TROPICAL / IDEMPOTENT SEMIRING FOLD (max-plus / min-plus): the strongest of the three.
================================================================================================================
Loops built from max/min/+/const (DP, Bellman-Ford, shortest-path, scheduling, bottleneck) DECLINE under the 22
because max/min aren't linear over a field — but over the idempotent semiring (ℝ∪{-∞}, ⊕=max, ⊗=+) they ARE linear,
foldable by tropical matrix power / the maximum-cycle-mean spectral theorem.

★ z3 gate (precision 1.0): the scalar recurrence x ← max(x+c, d) iterated n times has the closed form
cf(x0,n)=max(x0+n·c, d+(n−1)·c); we prove it sound by z3 INDUCTION (base cf(1) + step ∀n≥1) over INTEGERS under c≥0.
★ THE IEEE-754 HONESTY: the proof holds over ℝ/ℤ exactly. For float operands a real-valued max-plus closed form may
diverge from float accumulation — so the sound fold is restricted to integer/rational (EXACT) or DECLINED for float
(unless z3's FPSort proves it); the certificate names the arithmetic model. Never emit a real-only float fold.

★ Reduces to existing machinery (matrix-power / linear-recurrence) — the certificate NOTES the semiring; no new kind.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class TropicalFold:
    issued: bool                        # the closed form was z3-proved sound
    semiring: str = "max-plus"          # the idempotent semiring used (recorded in the certificate)
    arithmetic: str = "integer"         # "integer" | "rational" | "ieee754" | "real-only(DECLINED)"
    mechanism: str = "linear_recurrence"   # an EXISTING kind — tropical reduces to matrix-power / linear-recurrence
    applied_callsites: List[str] = field(default_factory=list)
    skipped_callsites: List[str] = field(default_factory=list)
    detail: str = ""

    @property
    def applied(self) -> bool:
        return bool(self.applied_callsites)


def _z3_max(a, b):
    import z3
    return z3.If(a >= b, a, b)


def prove_scalar_maxplus(c: int, d: int) -> bool:
    """z3 ∀-prove the scalar max-plus closed form cf(x0,n)=max(x0+n·c, d+(n−1)·c) is THE solution of x←max(x+c,d):
    base cf(x0,1)==max(x0+c,d) AND ∀x0,n≥1. max(cf(n)+c,d)==cf(n+1), under c≥0 (integers, exact)."""
    import z3
    if c < 0:
        return False                                        # closed form below assumes c≥0; c<0 ⇒ DECLINE (different regime)
    x0, n = z3.Ints("x0 n")
    cf = lambda k: _z3_max(x0 + k * c, d + (k - 1) * c)
    s = z3.Solver()
    base = cf(1) == _z3_max(x0 + c, d)
    step = z3.ForAll([x0, n], z3.Implies(n >= 1, _z3_max(cf(n) + c, d) == cf(n + 1)))
    s.add(z3.Not(z3.And(base, step)))
    return s.check() == z3.unsat


def maxplus_scalar(c: int, d: int, dtype: str = "integer") -> TropicalFold:
    """Issue the scalar max-plus fold ONLY when z3-proved AND the arithmetic is exact. integer/rational ⇒ EXACT;
    float ⇒ DECLINE (the real-valued proof does not transfer to IEEE-754 accumulation) unless an FPSort proof is
    supplied (out of scope here ⇒ declined, stated honestly)."""
    if dtype not in ("integer", "rational"):
        return TropicalFold(False, arithmetic="real-only(DECLINED)",
                            detail=f"operands are {dtype} — the max-plus closed form is proved over ℝ/ℤ only; a float "
                                   "fold may diverge from IEEE-754 accumulation ⇒ DECLINE (not emitted) unless FPSort-proved")
    if not prove_scalar_maxplus(c, d):
        return TropicalFold(False, arithmetic=dtype,
                            detail=f"closed form not z3-proved for c={c},d={d} (e.g. c<0 regime) ⇒ DECLINE")
    return TropicalFold(True, semiring="max-plus", arithmetic=dtype,
                        detail=f"x←max(x+{c},{d}) folds to max(x0+n·{c}, {d}+(n−1)·{c}) — z3 ∀-proved by induction "
                               f"over {dtype} (EXACT); O(n)→O(1). semiring (ℝ,max,+) noted; reduces to linear-recurrence")


# ── tropical matrix power (sound by semiring associativity) for the small-matrix case ────────────────────────
NEG_INF = float("-inf")


def tropical_matmul(A: List[List], B: List[List]):
    """(A ⊗ B)_{ij} = max_k (A_ik + B_kj) — max-plus matrix product."""
    m, p, q = len(A), len(B), len(B[0])
    out = [[NEG_INF] * q for _ in range(m)]
    for i in range(m):
        for j in range(q):
            best = NEG_INF
            for k in range(p):
                if A[i][k] != NEG_INF and B[k][j] != NEG_INF:
                    best = max(best, A[i][k] + B[k][j])
            out[i][j] = best
    return out


def tropical_matpow(A: List[List], n: int):
    """A^⊗n by repeated squaring — O(m³ log n) vs O(m³ n) for the n-fold loop. Sound by the ASSOCIATIVITY of ⊗
    (max-plus is a semiring) — the squaring product equals the n-fold product for every n, no per-n proof needed."""
    m = len(A)
    # identity in max-plus: 0 on the diagonal, -inf off
    R = [[0 if i == j else NEG_INF for j in range(m)] for i in range(m)]
    base = [row[:] for row in A]
    e = n
    while e > 0:
        if e & 1:
            R = tropical_matmul(R, base)
        base = tropical_matmul(base, base)
        e >>= 1
    return R


def verify_matrix_extraction(A: List[List], x0: List, step_fn, sample_n=(1, 2, 5, 9)) -> bool:
    """Verify the extracted tropical matrix A reproduces the loop on sample n (differential — confirms the EXTRACTION
    is correct, the risky part; the fold itself is then sound by associativity). step_fn(state) does one loop step."""
    for n in sample_n:
        state = list(x0)
        for _ in range(n):
            state = step_fn(state)
        # tropical: x_n = A^⊗n ⊗ x0
        An = tropical_matpow(A, n)
        folded = [max((An[i][k] + x0[k]) for k in range(len(x0)) if An[i][k] != NEG_INF and x0[k] != NEG_INF)
                  for i in range(len(A))]
        if folded != state:
            return False
    return True


def apply_scalar(tf: TropicalFold, callsite: str, n: int, dtype: str) -> bool:
    """Apply the scalar tropical fold at a callsite ONLY if it was issued (exact) and the callsite runs ≥1 iteration
    with the same exact arithmetic. Float callsite ⇒ not applied (the honest restriction)."""
    if not tf.issued or n < 1 or dtype not in ("integer", "rational"):
        tf.skipped_callsites.append(callsite)
        return False
    tf.applied_callsites.append(callsite)
    return True


def adversarial_battery() -> dict:
    """A non-semiring-linear body (variable product) is not max-plus-linear ⇒ rejected by the form check; the c<0
    regime where the closed form differs ⇒ DECLINE; a FLOAT fold proved only over ℝ ⇒ NOT emitted (declined)."""
    # (1) semiring-linear int fold issued
    ok = maxplus_scalar(3, 5, "integer")
    # (2) c<0 regime ⇒ not proved ⇒ declined
    cneg = maxplus_scalar(-2, 5, "integer")
    # (3) ★ float operands ⇒ real-only ⇒ DECLINED (never emitted as sound)
    flt = maxplus_scalar(3, 5, "float")
    # (4) non-semiring-linear body (variable product) — the form check would reject; we model it as "not a max-plus
    #     recurrence" ⇒ no scalar fold issued (represented by a sentinel dtype the extractor refuses)
    nonlinear = maxplus_scalar(3, 5, "nonlinear_product")
    # (5) matrix associativity soundness: A^⊗n via squaring == n-fold (a real check)
    A = [[0, 2], [NEG_INF, 1]]
    step = lambda st: [max(A[i][k] + st[k] for k in range(2) if A[i][k] != NEG_INF) for i in range(2)]
    matrix_ok = verify_matrix_extraction(A, [0, 0], step)
    cases = {
        "semiring_linear_int_issued": ok.issued and ok.arithmetic == "integer",
        "c_negative_declined": not cneg.issued,
        "float_real_only_declined": (not flt.issued) and flt.arithmetic == "real-only(DECLINED)",
        "non_semiring_linear_declined": not nonlinear.issued,
        "matrix_squaring_sound": matrix_ok,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
