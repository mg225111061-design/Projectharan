"""
UNIFIED ARSENAL §2 — DECISION PROCEDURES (summation side): Petkovšek/van Hoeij + Abramov.
=========================================================================================
"Closed form OR a proof of non-existence" — each with a re-checkable certificate; a proven non-existence is a
dignified, first-class result (the moat), never a fabricated formula.

  • PETKOVŠEK (van Hoeij) — ALL hypergeometric solutions of a linear recurrence Σ p_i(n) y(n+i)=0 (y(n+1)/y(n) ∈
    ℚ(n)), or a proof there are none. A DECISION procedure (complete for hypergeometric solutions). Certificate:
    each returned solution is SUBSTITUTED back and the recurrence reduces to 0 over ℚ(n) — our own check, not a
    library's word; a fabricated solution is rejected.
  • ABRAMOV — rational summability: decide whether Σ r(n), r∈ℚ(n), has a RATIONAL closed form R with
    R(n+1)−R(n)=r(n). A DECISION procedure (Gosper specialised to rational terms). Certificate: the telescoping
    identity R(n+1)−R(n)−r(n) ≡ 0; or a proven NO (e.g. Σ 1/n is the harmonic number — not rationally summable).

We use sympy (rsolve_hyper / gosper_sum) as the SEARCH engine; the substitution / telescoping checks are OUR
certificate. No Lean/Coq. Honest: non-existence relies on the cited algorithm's COMPLETENESS for its class.
"""
from __future__ import annotations

from typing import List

import sympy as sp
from sympy.concrete.gosper import gosper_sum
from sympy.solvers.recurr import rsolve_hyper

import kernel_verdict as KV

_n = sp.Symbol("n", integer=True)


def _verify_recurrence_solution(coeffs: List[sp.Expr], term: sp.Expr, n: sp.Symbol) -> bool:
    """Substitute a hypergeometric solution `term` into Σ_i coeffs[i]·y(n+i)=0 and check it reduces to 0 over
    ℚ(n) — independent of how the term was found. Factor out term(n): Σ_i coeffs[i]·(term(n+i)/term(n)) ≡ 0."""
    if term == 0:
        return False
    ratio_sum = sp.Integer(0)
    for i, c in enumerate(coeffs):
        ratio = sp.simplify(term.subs(n, n + i) / term)
        ratio_sum += sp.sympify(c) * ratio
    return sp.simplify(sp.together(ratio_sum)) == 0


def petkovsek(coeffs: List, n: sp.Symbol = None) -> KV.Verdict:
    """DECIDE the hypergeometric solutions of Σ_i coeffs[i]·y(n+i) = 0 (coeffs[i] ∈ ℚ[n]). EXACT either way:
    a verified basis of hypergeometric solutions, or a proven 'no hypergeometric solution' (Petkovšek decision)."""
    n = n or _n
    coeffs = [sp.sympify(c, locals={"n": n}) for c in coeffs]
    try:
        res = rsolve_hyper(coeffs, sp.Integer(0), n)        # homogeneous: f = 0
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"petkovsek: rsolve_hyper failed ({type(e).__name__}) ⇒ DECLINE", "decision_summation")
    if res is None:
        cert = KV.Cert(KV.EXACT, "petkovsek_decision", passed=True, check_cost="Petkovšek completeness",
                       detail="no hypergeometric solution exists (Petkovšek decision — complete for this class)")
        return KV.exact("NO_HYPERGEOMETRIC_SOLUTION", "decision_summation.petkovsek",
                        "DECISION (no hypergeometric solution)", cert)
    # rsolve_hyper returns the GENERAL solution Σ C_i·(hypergeometric basis term). Pull out the basis terms by
    # the arbitrary constants C0,C1,… (named C# by sympy) and VERIFY each by substitution.
    general = sp.expand(res)
    consts = sorted([s for s in general.free_symbols if str(s).startswith("C")], key=str)
    terms = [sp.simplify(general.coeff(C)) for C in consts]
    terms = [t for t in terms if t != 0]
    if not terms and general != 0:
        terms = [sp.simplify(general)]
    verified = [t for t in terms if _verify_recurrence_solution(coeffs, t, n)]
    if not verified:
        return KV.decline("petkovsek: candidate solutions failed the substitution certificate ⇒ DECLINE", "decision_summation")
    cert = KV.Cert(KV.EXACT, "petkovsek_substitution", passed=True, check_cost="substitution → 0 over ℚ(n)",
                   detail=f"{len(verified)} hypergeometric solution(s) verified by substitution: "
                          f"{', '.join(sp.sstr(t) for t in verified)}")
    return KV.exact(verified, "decision_summation.petkovsek", "DECISION (hypergeometric solutions)", cert)


def abramov_summable(r: sp.Expr, n: sp.Symbol = None) -> KV.Verdict:
    """DECIDE rational summability of r(n) ∈ ℚ(n): a rational R with ΔR = r (EXACT, telescoping-certified), or a
    proven 'not rationally summable' (e.g. 1/n ⇒ harmonic). DECISION via Gosper specialised to rational terms."""
    n = n or _n
    r = sp.sympify(r, locals={"n": n})
    if not r.is_rational_function(n):
        return KV.decline("abramov: input is not a rational function of n ⇒ DECLINE (out of scope)", "decision_summation")
    try:
        R = gosper_sum(r, n)
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"abramov: gosper failed ({type(e).__name__}) ⇒ DECLINE", "decision_summation")
    if R is None:
        cert = KV.Cert(KV.EXACT, "abramov_decision", passed=True, check_cost="Gosper/Abramov completeness",
                       detail="PROVEN not rationally summable (no rational antidifference — e.g. a harmonic number)")
        return KV.exact("NOT_RATIONALLY_SUMMABLE", "decision_summation.abramov",
                        "DECISION (no rational closed form)", cert)
    if sp.simplify(R.subs(n, n + 1) - R - r) != 0:           # our telescoping certificate
        return KV.decline("abramov: candidate antidifference failed the telescoping check ⇒ DECLINE", "decision_summation")
    cert = KV.Cert(KV.EXACT, "abramov_telescoping", passed=True, check_cost="ΔR − r ≡ 0",
                   detail=f"rationally summable: R(n)={sp.sstr(R)}, R(n+1)−R(n) ≡ r(n) ⇒ Σ_(k=a..b) r = R(b+1)−R(a)")
    return KV.exact(R, "decision_summation.abramov", "DECISION (rational summation closed form)", cert)


def solve(problem: dict) -> KV.Verdict:
    """ops: 'petkovsek' (coeffs list), 'abramov' (r expr). DECLINE otherwise."""
    op = problem.get("op")
    if op == "petkovsek":
        return petkovsek(problem["coeffs"])
    if op == "abramov":
        return abramov_summable(problem["r"])
    return KV.decline(f"decision_summation: unknown op {op!r} ⇒ DECLINE", "decision_summation")
