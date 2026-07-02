"""
§AQ §5.ALIGN — the alignment bit-trick `(x + a − 1) & ~(a − 1)` == `a·⌈x/a⌉` for a = 2ᵏ, z3 BV-PROVEN.
================================================================================================================
The ubiquitous power-of-two alignment idiom equals ceiling-to-multiple — a clean BV↔arithmetic identity. ★ z3 BV proves
`(x + a − 1) & ~(a − 1) == ((x + a − 1) // a) · a` (= a·⌈x/a⌉) ∀ x; a WRONG mask (`& ~a`) is refuted. EXACT (already O(1);
the value is the verified equivalence, not a speedup).
"""
from __future__ import annotations


def prove_align_up(k: int = 6, width: int = 32, correct: bool = True) -> bool:
    """z3 BV: (x + a−1) & ~(a−1) == ((x+a−1) udiv a)·a  for a=2ᵏ, ∀ x with no overflow. WRONG mask ~a ⇒ SAT."""
    import z3
    a = 1 << k
    x = z3.BitVec("x", width)
    aw = z3.BitVecVal(a, width)
    no_ovf = z3.ULT(x, z3.BitVecVal((1 << width) - a, width))     # x + a-1 must not wrap
    mask = ~(aw - 1) if correct else ~aw                          # ★ wrong: ~a instead of ~(a-1)
    lhs = (x + (aw - 1)) & mask
    rhs = z3.UDiv(x + (aw - 1), aw) * aw                          # a·⌈x/a⌉
    sol = z3.Solver()
    sol.add(no_ovf, lhs != rhs)
    return sol.check() == z3.unsat


def adversarial_battery() -> dict:
    """★ the align-up bit-trick == a·⌈x/a⌉ is z3-proven for a∈{8,64,4096} (page sizes); ★★ a wrong mask (~a) is
    z3-REFUTED (false-EXACT 0)."""
    cases = {
        "align8_proven": prove_align_up(3, 32, True),
        "align64_proven": prove_align_up(6, 32, True),
        "page4096_proven": prove_align_up(12, 32, True),
        "wrong_mask_refuted": not prove_align_up(6, 32, False),    # ★★
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
