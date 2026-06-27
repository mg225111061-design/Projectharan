"""
§AD GAP 7 — LARGE-BUT-BOUNDED STATE (fold the structure, never enumerate).
================================================================================================================
An 8-bit state (256 values) folds via cycle detection, but a 32-bit state (4 billion) is abandoned as "too large" — yet
if the transition has STRUCTURE (linear/affine/bitwise-linear), the fold doesn't need to enumerate 4 billion states; it
folds the structure directly (matrix power over the ring ℤ/2^w). Fix: for large-but-bounded state with provable structure
`x ← (a·x + b) mod 2^w`, fold via the affine matrix power — O(N)→O(log N), no enumeration.

★ z3 gate (EXACT, precision 1.0): QF_BV proves (a) the transition is AFFINE (∀x. f(x) == a·x+b over BitVec w), then (b)
the closed form (matrix [[a,b],[0,1]]ⁿ mod 2^w applied to [x,1]) equals the n-fold transition (bitvector-exact, sample n;
sound for all n by the ring homomorphism). ★ A genuinely-unstructured large state (nonlinear mixing) is DECLINED — the
affineness check FAILS; structure is never assumed because the small-state version worked. Reuses the QF_BV / matrix-power
machinery (§P-P4 / §Y).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class LargeStateFold:
    issued: bool
    width: int = 0
    a: Optional[int] = None
    b: Optional[int] = None
    affine: bool = False
    fold_verified: bool = False
    detail: str = ""


def is_affine(f: Callable, w: int) -> bool:
    """z3 QF_BV: is f affine over BitVec w? Let a=f(1)−f(0), b=f(0); prove ∀x. f(x) == a·x+b (mod 2^w). unsat of the
    negation ⇒ affine. A nonlinear f (x·x+…) fails ⇒ not affine."""
    import z3
    x = z3.BitVec("x", w)
    a = f(z3.BitVecVal(1, w)) - f(z3.BitVecVal(0, w))
    b = f(z3.BitVecVal(0, w))
    s = z3.Solver()
    s.add(f(x) != a * x + b)
    return s.check() == z3.unsat


def _coeffs(f: Callable, w: int):
    a = (f(1) - f(0)) % (1 << w)
    b = f(0) % (1 << w)
    return a, b


def _mat2_pow_mod(a: int, b: int, n: int, m: int):
    """[[a,b],[0,1]]ⁿ mod m by repeated squaring (the affine map's matrix). Returns (A, B) with the n-fold map
    x ↦ (A·x + B) mod m — folds the structure WITHOUT enumerating the 2^w states."""
    RA, RB = 1, 0                                            # identity affine map
    ba, bb = a, b
    e = n
    while e > 0:
        if e & 1:
            RA, RB = (RA * ba) % m, (RA * bb + RB) % m
        ba, bb = (ba * ba) % m, (ba * bb + bb) % m
        e >>= 1
    return RA, RB


def prove_fold_matches(f: Callable, a: int, b: int, w: int, sample_n=(1, 2, 3, 5, 8)) -> bool:
    """z3 QF_BV: for sample n, ∀x. (the n-fold transition) == (the closed affine map A·x+B from the matrix power), mod
    2^w — bitvector-exact. Sound for all n by the affine ring homomorphism."""
    import z3
    m = 1 << w
    for n in sample_n:
        x = z3.BitVec("x", w)
        it = x
        for _ in range(n):
            it = f(it)
        A, B = _mat2_pow_mod(a, b, n, m)
        s = z3.Solver()
        s.add(it != z3.BitVecVal(A, w) * x + z3.BitVecVal(B, w))
        if s.check() != z3.unsat:
            return False
    return True


def large_state_fold(f: Callable, w: int = 32) -> LargeStateFold:
    """Fold a large-but-bounded (2^w) state transition via its affine structure (matrix power, NO enumeration), iff f is
    z3-proved affine AND the closed form is QF_BV-verified. A nonlinear/unstructured transition ⇒ DECLINE."""
    if not is_affine(f, w):
        return LargeStateFold(False, w, affine=False,
                              detail=f"transition over 2^{w} states is NOT affine (nonlinear/unstructured mixing) ⇒ "
                                     "DECLINE (structure never assumed; enumeration is not the alternative — it stays unfolded)")
    a, b = _coeffs(f, w)
    ok = prove_fold_matches(f, a, b, w)
    return LargeStateFold(ok, w, a, b, True, ok,
                          detail=(f"affine x←({a}·x+{b}) mod 2^{w} folds via matrix power O(N)→O(log N), QF_BV-verified, "
                                  f"WITHOUT enumerating 2^{w} states" if ok else "affine but closed form unverified ⇒ DECLINE"))


def adversarial_battery() -> dict:
    """A 32-bit affine LCG-style transition folds via its structure (no enumeration, QF_BV-verified); ★ a 32-bit
    NONLINEAR transition (x·x+1) is DECLINED (structure not forced just because the space is bounded); the matrix-power
    closed form matches the iteration."""
    import z3
    affine = lambda x: (1103515245 * x + 12345)             # a classic LCG (affine mod 2^w)
    fa = large_state_fold(affine, 32)
    nonlinear = lambda x: x * x + 1                          # nonlinear mixing ⇒ not affine ⇒ DECLINE
    fn = large_state_fold(nonlinear, 32)
    # smaller affine for a quick closed-form sanity
    small = large_state_fold(lambda x: 5 * x + 3, 16)
    cases = {
        "affine_large_state_folds": fa.issued and fa.affine and fa.fold_verified,
        "no_enumeration": "WITHOUT enumerating" in fa.detail and fa.width == 32,
        "nonlinear_large_state_declined": (not fn.issued) and (not fn.affine),   # ★ structure not forced
        "small_affine_folds": small.issued and small.a == 5 and small.b == 3,
        "matrix_power_correct": _mat2_pow_mod(5, 3, 2, 1 << 16) == ((25) % (1 << 16), (5 * 3 + 3) % (1 << 16)),
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
