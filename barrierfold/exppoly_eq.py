"""
§AE ISLAND 3 — EXP-POLY-EQUALITY (barrier: closed-form equality partially decidable, general case open).
================================================================================================================
Deciding whether two closed forms are equal is partially decidable. The island: exponential polynomials f = Σ P_i(n)·λ_iⁿ
with algebraic λ_i, decided by BASIS LINEAR-INDEPENDENCE — distinct algebraic λ give linearly-independent {nʲ·λⁿ}, so
f ≡ g reduces to COEFFICIENT COMPARISON (same λ's, same polynomial coefficients). Plus the decidable Skolem sub-cases:
order ≤ 4 (Vereshchagin), roots-of-unity / fixed-k-periodic, finite-field/modular (pigeonhole-periodic).

★ Repo-first: this is the EQUALITY-CHECK our C-finite folds already need — the new piece is the exp-poly canonical-form
equality decider. Grade: EXACT; verification = coefficient comparison + a bounded exp-poly identity (terminating).
★ DECLINE boundary: Skolem order ≥ 5 (open — the existential-zero question), unbounded k-periodic, transcendental base
(e^n, π^n — z3 can't decide), general special functions. Equality of exp-polys over distinct algebraic λ is ALWAYS
decidable (basis); the order-≤4 limit is for the harder Skolem existential-zero problem, stated honestly.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, List, Optional, Tuple


@dataclass
class ExpPolyEq:
    decidable: bool
    equal: Optional[bool] = None
    method: str = ""
    detail: str = ""


# an exp-poly term = (polynomial coeffs c0+c1·n+…, base λ as a Fraction). f = list of terms.
Term = Tuple[Tuple[Fraction, ...], Fraction]


def _normalize(terms: List[Term]) -> Dict[Fraction, List[Fraction]]:
    """Merge terms sharing a base λ (sum their polynomial coefficient vectors). The canonical form: {λ → coeff vector}.
    By basis linear-independence (distinct algebraic λ ⇒ {nʲλⁿ} independent), two exp-polys are equal IFF these match."""
    out: Dict[Fraction, List[Fraction]] = {}
    for coeffs, lam in terms:
        lam = Fraction(lam)
        vec = out.setdefault(lam, [])
        for j, c in enumerate(coeffs):
            if j >= len(vec):
                vec.extend([Fraction(0)] * (j + 1 - len(vec)))
            vec[j] += Fraction(c)
    return {lam: [c for c in vec] for lam, vec in out.items()}


def _eval(terms: List[Term], n: int) -> Fraction:
    return sum(sum(Fraction(c) * Fraction(n) ** j for j, c in enumerate(coeffs)) * Fraction(lam) ** n
               for coeffs, lam in terms)


def _strip(vec: List[Fraction]) -> List[Fraction]:
    v = list(vec)
    while v and v[-1] == 0:
        v.pop()
    return v


def exppoly_equal(f: List[Term], g: List[Term], bound: int = 12) -> ExpPolyEq:
    """Decide f ≡ g over distinct algebraic (here rational) bases by BASIS INDEPENDENCE: equal IFF the normalized
    {λ→coeff} forms match. Corroborated by a bounded exp-poly identity (∀ n ≤ bound, exact rational). ALWAYS decidable."""
    nf, ng = _normalize(f), _normalize(g)
    bases = set(nf) | set(ng)
    by_basis = all(_strip(nf.get(lam, [])) == _strip(ng.get(lam, [])) for lam in bases)
    by_eval = all(_eval(f, n) == _eval(g, n) for n in range(bound + 1))       # corroborating bounded identity
    equal = by_basis and by_eval
    # if the structural and the bounded checks disagree, basis-independence has been violated (a bug) — be conservative
    if by_basis != by_eval:
        return ExpPolyEq(False, None, "basis-vs-eval", "basis comparison disagreed with bounded eval ⇒ DECLINE (conservative)")
    return ExpPolyEq(True, equal, "basis-linear-independence",
                     f"distinct-base exp-polys: equal ⟺ coeff vectors match (basis independence) = {equal}; "
                     f"corroborated ∀n≤{bound} (EXACT, terminating)")


def skolem_decidable(order: int) -> bool:
    """The Skolem existential-zero problem (∃n. f(n)=0) is DECIDABLE for order ≤ 4 (Vereshchagin) and roots-of-unity;
    order ≥ 5 is OPEN. (Equality itself is always decidable via basis; this gates the harder existential question.)"""
    return order <= 4


def adversarial_battery() -> dict:
    """(n+1)² ≡ n²+2n+1 [polynomial, basis λ=1]; 2·2ⁿ ≢ 3·2ⁿ [same base, different coeff]; 2ⁿ + 3ⁿ ≢ 2·2ⁿ [distinct
    bases, basis-independent]; ★ Skolem order ≤ 4 decidable, order ≥ 5 DECLINED (open)."""
    # (n+1)^2 = n^2+2n+1 ; LHS coeffs [1,2,1] base 1; RHS as three base-1 terms n²+2n+1 that NORMALIZE to [1,2,1]
    eq_poly = exppoly_equal([((1, 2, 1), Fraction(1))],
                            [((0, 0, 1), Fraction(1)), ((0, 2), Fraction(1)), ((1,), Fraction(1))])
    # 2*2^n vs 3*2^n (same base, diff coeff) ⇒ NOT equal
    neq_same_base = exppoly_equal([((2,), Fraction(2))], [((3,), Fraction(2))])
    # 2^n + 3^n vs 2*2^n (distinct bases) ⇒ NOT equal (basis independence)
    neq_distinct = exppoly_equal([((1,), Fraction(2)), ((1,), Fraction(3))], [((2,), Fraction(2))])
    cases = {
        "polynomial_equal_by_basis": eq_poly.decidable and eq_poly.equal,
        "same_base_diff_coeff_unequal": neq_same_base.decidable and (not neq_same_base.equal),
        "distinct_base_unequal": neq_distinct.decidable and (not neq_distinct.equal),
        "equality_always_decidable": eq_poly.method == "basis-linear-independence",
        "skolem_order4_decidable": skolem_decidable(4),
        "skolem_order5_declined": not skolem_decidable(5),                    # ★ open problem ⇒ DECLINE
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
