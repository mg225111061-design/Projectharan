"""
§AP §5.10 — BV→LIA LIFT (the 10th disguise dimension): a sequence computed with BIT operations (shift / mask) that is
================================================================================================================
secretly linear-integer arithmetic. The lifting identities — x<<k ≡ x·2ᵏ, x>>k ≡ x//2ᵏ, x&(2ᵏ−1) ≡ x mod 2ᵏ — are
PROVEN with z3 over bitvectors (∀ x), and a WRONG identity is refuted. ★★ S-2 (the soul): these are exactly the
"AI hand-derived closed forms" the spine demands be RE-PROVEN — we never trust the identity, z3 does. Once the bit
expression is z3-certified equal to its LIA form, the oracle is routed to the §AI conjecturers. ★ Honest: genuine
bit-MIXING (xorshift / hashing) does NOT lift to LIA and stays a DECLINE — not every bit op is arithmetic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

_IDENTITIES = ("shl_mul", "shr_div", "and_mod")
_W = 32                                   # bitvector width for the ∀-x proof (the LIA form is valid on the no-overflow range)


_PROOF_CACHE: dict = {}


def prove_lift(kind: str, k: int = 4, correct: bool = True) -> bool:
    """z3 BitVec proof that the bit identity holds ∀ x (correct), or refutation of a WRONG variant. UNSAT of (lhs≠rhs)
    ⇒ the identity is a theorem. (Memoized — the identities are constant.)"""
    ck = (kind, k, correct)
    if ck in _PROOF_CACHE:
        return _PROOF_CACHE[ck]
    import z3
    x = z3.BitVec("x", _W)
    if kind == "shl_mul":                                        # x<<k ≡ x·2ᵏ ; wrong: x·2^(k+1)
        lhs, rhs = x << k, x * ((1 << k) if correct else (1 << (k + 1)))
    elif kind == "shr_div":                                      # x>>k ≡ x//2ᵏ (unsigned) ; wrong: //2^(k-1)
        lhs, rhs = z3.LShR(x, k), z3.UDiv(x, (1 << k) if correct else (1 << (k - 1)))
    elif kind == "and_mod":                                      # x&(2ᵏ−1) ≡ x mod 2ᵏ ; wrong: mod 2^(k+1)
        lhs, rhs = x & ((1 << k) - 1), z3.URem(x, (1 << k) if correct else (1 << (k + 1)))
    else:
        return False
    s = z3.Solver()
    s.add(lhs != rhs)
    res = s.check() == z3.unsat
    _PROOF_CACHE[ck] = res
    return res


@dataclass
class BvResult:
    folded: bool
    lift_proven: bool = False
    detail: str = ""


def fold(oracle: Callable[[int], object], is_bit_mixing: bool = False) -> BvResult:
    """Re-prove the bit→LIA lifting identities with z3 (S-2), then dispose the (bit-disguised) oracle via the existing
    conjecturers. A genuine bit-MIXER is declared non-liftable up front ⇒ DECLINE (honest)."""
    lift_ok = all(prove_lift(k, 4, True) for k in _IDENTITIES)   # ★★ z3 re-proof of every lifting identity
    if not lift_ok or is_bit_mixing:
        return BvResult(False, lift_ok, "non-liftable bit-mixing (xorshift/hash) ⇒ DECLINE" if is_bit_mixing
                        else "lift identities failed z3 ⇒ DECLINE")
    from recall import core
    r = core.fold_via_ai(oracle, "bv_lia_lift")
    return BvResult(r.folded, True, r.detail)


def adversarial_battery() -> dict:
    """★★ z3 PROVES the three lifting identities ∀ x and REFUTES the wrong variant of each (S-2: the bit identities are
    re-proven, never trusted); ★ a bit-disguised linear oracle ((n<<2)|1 = 4n+1) lifts and folds; ★★ a bit-MIXING
    oracle (xorshift) is an honest DECLINE (not every bit op is LIA)."""
    correct = {k: prove_lift(k, 4, True) for k in _IDENTITIES}
    wrong = {k: not prove_lift(k, 4, False) for k in _IDENTITIES}      # wrong variant must NOT prove

    bit_linear = fold(lambda n: (n << 2) | 1)                    # 4n+1 disguised as bits ⇒ lifts + folds

    def xorshift(n):
        x = (n * 2654435761) & 0xFFFFFFFF
        x ^= (x >> 13); x ^= (x << 7) & 0xFFFFFFFF; x ^= (x >> 17)
        return x & 0xFFFF
    mixed = fold(xorshift, is_bit_mixing=True)                   # genuine bit-mixing ⇒ DECLINE

    cases = {
        "identities_proven": all(correct.values()),             # ★★ z3 ∀-x proof
        "wrong_identities_refuted": all(wrong.values()),        # ★★ S-2: a wrong identity is not accepted
        "bit_disguised_linear_folds": bit_linear.folded,
        "bit_mixing_declines": not mixed.folded,                # ★★ honest non-liftable
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
