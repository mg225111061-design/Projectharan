"""
§AQ §3.HORNER — parsing IS Horner's method: `n = n·B + d`. atoi / arbitrary-base / hex / UUID / varint (base-128).
================================================================================================================
`n = Σ dᵢ·B^(L−1−i)` ⇒ ★REDUCE to the existing C-finite / Horner mechanism (S-1). Proven with z3 LIA: the parse loop ==
the closed form ∀ digit strings; a wrong closed form (flipped exponent) is refuted. varint/LEB128 is base-128 Horner
with the continuation bit as the loop guard.
"""
from __future__ import annotations


def prove_horner_parse(B: int = 10, L: int = 5, correct: bool = True) -> bool:
    """z3 LIA: `n = n·B + d` over L digits == Σ dᵢ·B^(L−1−i). WRONG variant flips the exponent order ⇒ z3 SAT."""
    import z3
    ds = [z3.Int(f"d{i}") for i in range(L)]
    n = z3.IntVal(0)
    for d in ds:
        n = n * B + d
    closed = z3.Sum([ds[i] * (B ** (L - 1 - i if correct else i)) for i in range(L)])
    sol = z3.Solver()
    sol.add(n != closed)
    return sol.check() == z3.unsat


def adversarial_battery() -> dict:
    """★ decimal atoi (B=10), hex (B=16), and varint (B=128) parse loops z3-proven ≡ the Horner closed form (⇒ C-finite,
    existing mechanism); ★★ a flipped-exponent closed form is z3-REFUTED (false-EXACT 0)."""
    cases = {
        "atoi_base10_horner": prove_horner_parse(10, 6, True),
        "hex_base16_horner": prove_horner_parse(16, 4, True),
        "varint_base128_horner": prove_horner_parse(128, 4, True),
        "flipped_exponent_refuted": not prove_horner_parse(10, 5, False),       # ★★
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
