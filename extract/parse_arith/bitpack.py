"""
§AQ §3.BITPACK — base64 / hex decode and IPv4 packing = fixed bitvector shift-OR, z3 BV-proven (already O(1)).
================================================================================================================
base64: 4 sextets → 3 bytes `(a<<18)|(b<<12)|(c<<6)|d` ⇒ a fixed BV shift-OR (the disjoint fields make `|` = `+`).
IPv4: `(a<<24)|(b<<16)|(c<<8)|d` ⇒ a fixed BV pack. ★ z3 BV proves the OR-of-disjoint-fields equals the arithmetic
sum (so the packing is an exact linear combination — already O(1), no loop). A WRONG pack (overlapping shift) is refuted.
"""
from __future__ import annotations


def prove_ipv4_pack(correct: bool = True) -> bool:
    """z3 BV(32): (a<<24)|(b<<16)|(c<<8)|d == a·2²⁴ + b·2¹⁶ + c·2⁸ + d  ∀ bytes a,b,c,d∈[0,255]. WRONG: a<<24 → a<<23
    (overlap) ⇒ z3 SAT."""
    import z3
    a, b, c, d = (z3.BitVec(x, 32) for x in "abcd")
    bytes_ok = z3.And(*[z3.ULE(v, 255) for v in (a, b, c, d)])
    sh_a = 23 if not correct else 24
    packed = (a << sh_a) | (b << 16) | (c << 8) | d
    arith = a * (1 << 24) + b * (1 << 16) + c * (1 << 8) + d
    sol = z3.Solver()
    sol.add(bytes_ok, packed != arith)
    return sol.check() == z3.unsat


def prove_base64_quad(correct: bool = True) -> bool:
    """z3 BV(24): 4 sextets (each ≤63) pack `(a<<18)|(b<<12)|(c<<6)|d == a·2¹⁸+b·2¹²+c·2⁶+d` (disjoint ⇒ | == +).
    WRONG: c<<6 → c<<7 (overlap) ⇒ SAT."""
    import z3
    a, b, c, d = (z3.BitVec(x, 24) for x in "abcd")
    ok = z3.And(*[z3.ULE(v, 63) for v in (a, b, c, d)])
    sh_c = 7 if not correct else 6
    packed = (a << 18) | (b << 12) | (c << sh_c) | d
    arith = a * (1 << 18) + b * (1 << 12) + c * (1 << 6) + d
    sol = z3.Solver()
    sol.add(ok, packed != arith)
    return sol.check() == z3.unsat


def adversarial_battery() -> dict:
    """★ IPv4 and base64 packing are z3-proven exact linear field-combinations (OR-of-disjoint == sum, already O(1));
    ★★ an overlapping (wrong) shift is z3-REFUTED."""
    cases = {
        "ipv4_pack_exact": prove_ipv4_pack(True),
        "base64_quad_exact": prove_base64_quad(True),
        "ipv4_overlap_refuted": not prove_ipv4_pack(False),         # ★★
        "base64_overlap_refuted": not prove_base64_quad(False),     # ★★
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
