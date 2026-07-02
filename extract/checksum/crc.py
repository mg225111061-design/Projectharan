"""
§AQ §2.CRC — CRC(8/16/32/64) = GF(2)[x] polynomial division = a GF(2)-LINEAR map on the register, z3-PROVEN.
================================================================================================================
The bit-serial reflected CRC step `c ↦ (c >> 1) ^ (POLY if c&1 else 0)` is GF(2)-LINEAR in c — we PROVE it with z3 over
bitvectors: ∀ a,b: step(a⊕b) == step(a) ⊕ step(b). A linear map composes to Mⁿ ⇒ n bits/bytes ★REDUCE to the existing
matrix-power / additive-CA mechanism (S-1, no new mechanism). The byte injection `c ^ byte` is the affine constant. ★ A
WRONG step (any nonlinear op — a carry add, a multiply) FAILS linearity ⇒ z3 SAT ⇒ DECLINE (false-EXACT 0).
"""
from __future__ import annotations

# CRC-32 (IEEE 802.3, reflected) polynomial; the proof is parametric in width/poly.
_POLY32 = 0xEDB88320


def crc_step_bit(c: int, poly: int = _POLY32, width: int = 32) -> int:
    mask = (1 << width) - 1
    return ((c >> 1) ^ (poly if (c & 1) else 0)) & mask


def prove_crc_linear(width: int = 32, poly: int = _POLY32, correct: bool = True) -> bool:
    """z3 BV: the CRC bit-step is GF(2)-linear ∀ a,b (UNSAT of step(a⊕b) ≠ step(a)⊕step(b)). The WRONG variant injects a
    nonlinear carry (+1) ⇒ linearity breaks ⇒ SAT ⇒ not proven."""
    import z3
    a, b = z3.BitVec("a", width), z3.BitVec("b", width)

    def step(c):
        sh = z3.LShR(c, 1)
        red = z3.If(c & 1 == 1, z3.BitVecVal(poly, width), z3.BitVecVal(0, width))
        s = sh ^ red
        return s if correct else s + 1                            # ★ wrong: a carry-add breaks GF(2)-linearity
    sol = z3.Solver()
    sol.add(step(a ^ b) != (step(a) ^ step(b)))
    return sol.check() == z3.unsat


def prove_affine_with_byte(width: int = 32, poly: int = _POLY32) -> bool:
    """z3 BV: injecting a data byte makes the per-byte update AFFINE in c — the c-homogeneous part is linear and the byte
    is the constant: step(c⊕d) ⊕ step(0) == step(c) ⊕ step(d) ∀ c,d (affine superposition)."""
    import z3
    c, d = z3.BitVec("c", width), z3.BitVec("d", width)

    def step(x):
        return z3.LShR(x, 1) ^ z3.If(x & 1 == 1, z3.BitVecVal(poly, width), z3.BitVecVal(0, width))
    sol = z3.Solver()
    sol.add(step(c ^ d) ^ step(z3.BitVecVal(0, width)) != step(c) ^ step(d))
    return sol.check() == z3.unsat


def adversarial_battery() -> dict:
    """★ the CRC-32 bit-step is z3-proven GF(2)-LINEAR (⇒ reduces to matrix-power, existing mechanism); ★ CRC-16/CRC-8
    widths also linear; ★ the affine superposition with a data byte holds; ★★ a WRONG step with a nonlinear carry is
    z3-REFUTED (not linear ⇒ DECLINE, false-EXACT 0)."""
    cases = {
        "crc32_step_linear": prove_crc_linear(32, _POLY32, True),
        "crc16_step_linear": prove_crc_linear(16, 0xA001, True),
        "crc8_step_linear": prove_crc_linear(8, 0x8C, True),
        "byte_injection_affine": prove_affine_with_byte(),
        "nonlinear_step_refuted": not prove_crc_linear(32, _POLY32, False),     # ★★ S-2
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
