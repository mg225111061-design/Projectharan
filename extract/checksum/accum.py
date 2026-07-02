"""
§AQ §2.ACCUM — Adler-32 / Fletcher (double accumulation = TELESCOPING sum) and Luhn / ISBN (weighted digit sum), z3.
================================================================================================================
Adler/Fletcher: `a = 1 + Σdᵢ`, `b = Σ aᵢ = n + Σ(n−i+1)·dᵢ` — a discrete double-integral ⇒ ★REDUCE to the existing
TELESCOPING-sum mechanism (Σk). Proven with z3 LIA: the iterative double-accumulation == the closed form ∀ inputs.

Luhn / ISBN-10 / EAN-13: the doubling `f(d)` is a finite 0..9 lookup. ★★ S-2 IN ACTION — the convenient AI closed form
`f(d) = 2d mod 9` is WRONG at d=9 (gives 0, the true digit-sum of 18 is 9); z3 REFUTES it and PROVES the correct
`f(d) = 2d − 9·[d≥5]`. This is exactly the hand-calc error class the spine guards against — observation ≠ proof.
"""
from __future__ import annotations


def _adler_iter_b(ds):
    """Reference double-accumulation (no mod): a starts at 1, b accumulates a after each digit."""
    a, b = 1, 0
    for d in ds:
        a = a + d
        b = b + a
    return b


def prove_adler_telescoping(n: int = 4, correct: bool = True) -> bool:
    """z3 LIA: iterative b == n + Σ(n−i+1)·dᵢ  ∀ d₀..d_{n−1}. WRONG variant uses (n−i) (off-by-one) ⇒ z3 SAT."""
    import z3
    ds = [z3.Int(f"d{i}") for i in range(n)]
    a = z3.IntVal(1)
    b = z3.IntVal(0)
    for d in ds:
        a = a + d
        b = b + a
    closed = z3.IntVal(n) + z3.Sum([(n - i if correct else n - i - 1) * ds[i] for i in range(n)])
    # closed uses weight (n-i) for i=0..n-1 i.e. (n-i+1)·d with 1-based i ⇒ here weight (n-i) for 0-based, +n constant
    sol = z3.Solver()
    sol.add(b != closed)
    return sol.check() == z3.unsat


def luhn_double_ref(d: int) -> int:
    """The true Luhn doubling: double, and if the result exceeds 9 subtract 9 (= digit-sum of 2d)."""
    return 2 * d if 2 * d < 10 else 2 * d - 9


def prove_luhn_lookup() -> dict:
    """★★ z3 over d∈[0,9]: the correct closed form 2d−9·[d≥5] is PROVEN ≡ the reference; the convenient `2d mod 9` is
    REFUTED (counterexample d=9). The S-2 catch."""
    import z3
    d = z3.Int("d")
    dom = z3.And(d >= 0, d <= 9)
    ref = z3.If(2 * d < 10, 2 * d, 2 * d - 9)
    correct = z3.If(d >= 5, 2 * d - 9, 2 * d)
    naive = (2 * d) % 9
    s1 = z3.Solver(); s1.add(dom, correct != ref)
    correct_proven = s1.check() == z3.unsat
    s2 = z3.Solver(); s2.add(dom, naive != ref)
    naive_refuted = s2.check() == z3.sat                          # ★★ z3 finds d=9
    cex = None
    if naive_refuted:
        m = s2.model()
        cex = m[d].as_long()
    return {"correct_proven": correct_proven, "naive_2d_mod_9_refuted": naive_refuted, "counterexample_d": cex}


def adversarial_battery() -> dict:
    """★ Adler/Fletcher double-accumulation z3-proven ≡ the telescoping closed form (⇒ reduces to Σk, existing); ★★ a
    wrong (off-by-one) telescoping weight is z3-REFUTED; ★★ Luhn: the correct lookup is PROVEN and the convenient
    `2d mod 9` is REFUTED at d=9 (S-2 — the AI hand-calc error caught by z3)."""
    luhn = prove_luhn_lookup()
    # sanity: the reference iterative b matches a concrete closed-form value
    sample_ok = _adler_iter_b([3, 1, 4, 1]) == 4 + sum((4 - i) * v for i, v in enumerate([3, 1, 4, 1]))
    cases = {
        "adler_telescoping_proven": prove_adler_telescoping(4, True),
        "adler_offbyone_refuted": not prove_adler_telescoping(4, False),        # ★★
        "adler_reference_consistent": sample_ok,
        "luhn_correct_proven": luhn["correct_proven"],
        "luhn_2d_mod_9_refuted": luhn["naive_2d_mod_9_refuted"] and luhn["counterexample_d"] == 9,  # ★★ S-2
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
