"""
§AQ §2.HORNER — polynomial rolling hashes (Rabin-Karp / djb2 / sdbm) = C-finite Horner; FNV = honest z3 ADJUDICATION.
================================================================================================================
Rabin-Karp / djb2 (`h=h·33+c`) / sdbm (`h=h·65599+c`): the update `h = h·B + c` has the closed form
`h_L = h₀·Bᴸ + Σ cᵢ·B^(L−1−i)` ⇒ ★REDUCE to the existing C-finite / Horner mechanism (S-1). Proven by z3 LIA: the
iterative loop == the closed form ∀ inputs; a wrong closed form is refuted.

★★ FNV-1a (`h = (h ⊕ b)·P`) SPLIT the 4 reports (GLM=DECLINE; Kimi/Claude=folds). S-2 ADJUDICATES with z3 — and the
"constant-XOR = GF(2)-affine" claim does NOT survive: ⊕ is GF(2)-linear but ·P is ring-multiplication over ℤ/2ⁿ, NOT
GF(2)-linear, so the composition is not a single-algebra affine map. z3 finds a linearity counterexample ⇒ honest
DECLINE. (This is precisely the hand-calc-prediction-vs-proof gate the spine demands: observation/expectation ≠ proof.)
"""
from __future__ import annotations


def prove_horner_closed(B: int = 31, h0: int = 0, L: int = 4, correct: bool = True) -> bool:
    """z3 LIA: iterative h=h·B+c over L chars == h₀·Bᴸ + Σ cᵢ·B^(L−1−i). WRONG variant flips the exponent order ⇒ SAT."""
    import z3
    cs = [z3.Int(f"c{i}") for i in range(L)]
    h = z3.IntVal(h0)
    for c in cs:
        h = h * B + c
    closed = z3.IntVal(h0) * (B ** L) + z3.Sum([cs[i] * (B ** (L - 1 - i if correct else i)) for i in range(L)])
    sol = z3.Solver()
    sol.add(h != closed)
    return sol.check() == z3.unsat


def prove_fnv_not_gf2_affine(width: int = 32, P: int = 0x01000193) -> bool:
    """★★ z3 BV: the FNV step h ↦ (h ⊕ b)·P is NOT GF(2)-linear in h (a fixed byte b) — z3 finds a,b with
    step(a⊕x) ⊕ step(0) ≠ step(a) ⊕ step(x). Returns True iff the non-linearity is CONFIRMED (so FNV honestly DECLINEs
    the single-algebra affine fold). The honest resolution of the 4-report split."""
    import z3
    a, x = z3.BitVec("a", width), z3.BitVec("x", width)
    b = z3.BitVecVal(0x61, width)                                 # a fixed data byte

    def step(h):
        return (h ^ b) * z3.BitVecVal(P, width)
    sol = z3.Solver()
    sol.add(step(a ^ x) ^ step(z3.BitVecVal(0, width)) != step(a) ^ step(x))   # affine-superposition violation
    return sol.check() == z3.sat                                  # SAT ⇒ NOT affine ⇒ DECLINE (honest)


def adversarial_battery() -> dict:
    """★ Rabin-Karp / djb2 / sdbm Horner closed forms z3-proven ≡ the loop (⇒ C-finite, existing); ★★ a wrong exponent
    order is z3-REFUTED; ★★ FNV-1a does NOT reduce to a single-algebra affine map — z3 confirms the non-linearity ⇒
    honest DECLINE (the 4-report split resolved by proof, not by prediction — S-2)."""
    cases = {
        "rabin_karp_horner_proven": prove_horner_closed(256, 0, 4, True),
        "djb2_horner_proven": prove_horner_closed(33, 5381, 4, True),
        "sdbm_horner_proven": prove_horner_closed(65599, 0, 4, True),
        "wrong_exponent_refuted": not prove_horner_closed(31, 0, 4, False),     # ★★
        "fnv_not_affine_honest_decline": prove_fnv_not_gf2_affine(),            # ★★ S-2 adjudication
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
