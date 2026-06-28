"""
§AJ §3 — SOUNDNESS AUX: Kraft-McMillan realizability (exact) + 0-1-law promotion (z3-gated, NEVER observation).
================================================================================================================
Two auxiliary soundness layers that can only ever ADD a z3/exact certificate — never weaken the gate.

(A) KRAFT-McMILLAN. A binary code with codeword lengths {lᵢ} is uniquely decodable (equivalently: a prefix code with
those lengths exists) IFF Σ 2^(-lᵢ) ≤ 1 (Kraft for prefix codes; McMillan proves the same bound is necessary even for
the wider uniquely-decodable class). This is an EXACT rational certificate (Fraction arithmetic — no float), a
realizability witness for any recovered encoding/Huffman-like structure. > 1 ⇒ no such code ⇒ DECLINE with the exact
over-budget amount.

(B) 0-1-LAW PROMOTION. ★★ THE P-2 LINE. A property P(n) observed to hold on the probe is promoted to "holds ∀n"
(EXACT) ONLY when z3 proves a STRUCTURAL DICHOTOMY — `(∀n≥0. P(n)) ∨ (∀n≥0. ¬P(n))` — and the single observation
selects the surviving branch. If z3 cannot prove the dichotomy (P is genuinely n-dependent — e.g. "P(n) ≡ n<100",
true on the probe, false later), there is NO promotion: observation alone NEVER promotes (a match is not a proof).
This is the auxiliary that turns "always observed" into "proven" exactly where — and only where — a 0-1 law actually
holds. REUSE z3 (existing disposer); reuse the existing 'invariant' certificate kind (no new kind).
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, List, Optional


@dataclass
class KraftResult:
    realizable: bool
    kraft_sum: Fraction               # exact Σ 2^(-lᵢ) (rational)
    verdict: object = None
    detail: str = ""


def kraft_mcmillan(lengths: List[int]) -> KraftResult:
    """EXACT Kraft-McMillan: a uniquely-decodable / prefix binary code with these lengths exists IFF Σ 2^(-lᵢ) ≤ 1.
    Fraction arithmetic ⇒ exact (never float). ≤ 1 ⇒ EXACT realizability cert; > 1 ⇒ DECLINE with the over-budget."""
    import kernel_verdict as KV
    if not lengths or any((not isinstance(l, int)) or l < 0 for l in lengths):
        return KraftResult(False, Fraction(0), KV.decline("kraft: lengths must be non-negative integers", "kraft"),
                           "invalid code-length multiset")
    s = sum((Fraction(1, 2 ** l) for l in lengths), Fraction(0))
    if s <= 1:
        cert = KV.Cert(KV.EXACT, "invariant", passed=True, check_cost="O(k) exact rational sum",
                       detail=f"Kraft-McMillan Σ2^(-lᵢ)={s} ≤ 1 ⇒ a uniquely-decodable/prefix code with lengths "
                              f"{sorted(lengths)} EXISTS (exact rational realizability certificate)")
        return KraftResult(True, s, KV.exact({"kraft_sum": str(s), "lengths": sorted(lengths)}, "kraft",
                           "prefix-code realizability", cert), f"realizable: Σ2^(-lᵢ)={s} ≤ 1")
    return KraftResult(False, s, KV.decline(f"kraft: Σ2^(-lᵢ)={s} > 1 ⇒ no uniquely-decodable code (over budget by "
                       f"{s - 1}) ⇒ DECLINE", "kraft"), f"NOT realizable: Σ2^(-lᵢ)={s} > 1 (over by {s - 1})")


@dataclass
class PromoteResult:
    promoted: bool
    branch: str = ""                  # "all" | "none" | "" (no dichotomy ⇒ no promotion)
    verdict: object = None
    detail: str = ""


def prove_zero_one_dichotomy(phi: Callable[[object], object]) -> Optional[str]:
    """z3: does the 0-1 dichotomy `(∀n≥0. φ(n)) ∨ (∀n≥0. ¬φ(n))` hold? Returns "all" (φ proven ∀n), "none" (¬φ proven
    ∀n), or None (φ is genuinely n-dependent ⇒ NO dichotomy). φ takes a z3 Int and returns a z3 Bool."""
    import z3
    n = z3.Int("n")
    s_all = z3.Solver(); s_all.add(n >= 0, z3.Not(phi(n)))          # a counterexample to ∀n φ ?
    if s_all.check() == z3.unsat:
        return "all"
    s_none = z3.Solver(); s_none.add(n >= 0, phi(n))               # a witness that φ ever holds ?
    if s_none.check() == z3.unsat:
        return "none"
    return None                                                     # neither ⇒ n-dependent ⇒ no 0-1 law


def zero_one_promote(phi: Callable[[object], object], observed_holds: bool) -> PromoteResult:
    """★ Promote an observed-always property to EXACT ∀n ONLY under a z3-proved 0-1 dichotomy; the single observation
    selects the branch. No dichotomy ⇒ DECLINE (observation alone NEVER promotes — P-2)."""
    import kernel_verdict as KV
    d = prove_zero_one_dichotomy(phi)
    if d == "all" and observed_holds:
        cert = KV.Cert(KV.EXACT, "invariant", passed=True, check_cost="z3 0-1 dichotomy proof",
                       detail="z3 proved (∀n≥0. P(n)) ∨ (∀n≥0. ¬P(n)); the observation P holds ⇒ ∀n≥0 P(n) (EXACT)")
        return PromoteResult(True, "all", KV.exact({"branch": "all"}, "zero_one", "∀n invariant", cert),
                             "★ z3 dichotomy = all + observed-holds ⇒ promoted to EXACT ∀n")
    if d == "none" and not observed_holds:
        cert = KV.Cert(KV.EXACT, "invariant", passed=True, check_cost="z3 0-1 dichotomy proof",
                       detail="z3 proved (∀n≥0. ¬P(n)); the observation ¬P ⇒ ∀n≥0 ¬P(n) (EXACT)")
        return PromoteResult(True, "none", KV.exact({"branch": "none"}, "zero_one", "∀n invariant", cert),
                             "z3 dichotomy = none + observed-not-holds ⇒ proven identically false (EXACT)")
    if d is None:
        return PromoteResult(False, "", KV.decline("no z3 0-1 dichotomy (property is n-dependent) ⇒ observation does "
                             "NOT promote ⇒ DECLINE", "zero_one"),
                             "★ P-2: observed-always but z3 found the property n-dependent ⇒ NO promotion (DECLINE)")
    return PromoteResult(False, d, KV.decline("z3 dichotomy contradicts the observation ⇒ DECLINE", "zero_one"),
                         f"z3 dichotomy={d} contradicts observation ⇒ DECLINE")


def adversarial_battery() -> dict:
    """Kraft: {1,2,3,3} is realizable (Σ=1), {1,1,2} is NOT (Σ=5/4>1, exact); ★ 0-1 promotion: a z3-INVARIANT property
    (n+1>n, true ∀n) is PROMOTED to EXACT, but ★★ an observed-always-but-n-dependent property (n<100 — true on the
    probe, false later) is NOT promoted (z3 finds no dichotomy ⇒ DECLINE — the P-2 line); ¬-invariant (n<0) promotes
    to 'none'."""
    import z3
    realizable = kraft_mcmillan([1, 2, 3, 3])          # Σ = 1/2+1/4+1/8+1/8 = 1 ⇒ realizable
    over = kraft_mcmillan([1, 1, 2])                    # Σ = 1/2+1/2+1/4 = 5/4 > 1 ⇒ NOT realizable
    invariant = zero_one_promote(lambda n: n + 1 > n, observed_holds=True)            # ∀n true ⇒ promote (all)
    ndep = zero_one_promote(lambda n: n < 100, observed_holds=True)                   # ★ P-2: n-dependent ⇒ NO promote
    never = zero_one_promote(lambda n: n < 0, observed_holds=False)                   # ∀n≥0 false ⇒ promote (none)
    cases = {
        "kraft_equality_realizable": realizable.realizable and realizable.kraft_sum == Fraction(1),
        "kraft_over_budget_declined": (not over.realizable) and over.kraft_sum == Fraction(5, 4),  # ★ exact rational
        "invariant_promoted_all": invariant.promoted and invariant.branch == "all",
        "ndependent_not_promoted_P2": not ndep.promoted,           # ★★ observation-only NEVER promotes
        "false_invariant_promoted_none": never.promoted and never.branch == "none",
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
