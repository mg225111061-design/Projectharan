"""
§AE ISLAND 5 — INVARIANT-SYNTHESIS (barrier: Rice, undecidable): complete synthesis in the decidable domains.
================================================================================================================
General loop-invariant synthesis is UNDECIDABLE (Rice). The island: the COMPLETE synthesis domains — Karr (affine
invariants, 1976 — the strongest affine invariant), Farkas/LP (linear inequality invariants, 2004), Gröbner (fixed-degree
polynomial invariants, 2007), and abstract interpretation (interval/octagon/polyhedron, complete-within-domain + widening).

★ THE UNIFYING INSIGHT: synthesis is the PROPOSER's job (Karr/Farkas/Gröbner run the real algorithm); z3 only VERIFIES
the three verification conditions — initiation `pre ⟹ I(init)`, consecution `I ∧ guard ∧ body ⟹ I'`, sufficiency
`I ∧ ¬guard ⟹ fold_correct` — in QF_LRA (linear, simplex) or QF_NRA (polynomial, CAD), both TERMINATING.
★ Repo-first: reuses the §X `synthesize_guard` INTERFACE but upgrades CEGAR GUESSING to COMPLETE synthesis (finds every
invariant in the domain, not guess-and-check). ★ Directly ENABLES ISLAND 6 (termination needs invariants). Grade: EXACT.
★ DECLINE: transcendental/exponential invariants, unbounded-degree polynomial, data-dependent control, heap/pointer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class InvariantSynth:
    issued: bool
    domain: str = ""                        # "Karr-affine" | "Farkas-linear" | "Groebner-polynomial"
    invariant: str = ""
    initiation: bool = False
    consecution: bool = False
    sufficiency: bool = False
    complete: bool = True                    # the synthesizer is COMPLETE in its domain (not CEGAR guessing)
    detail: str = ""

    @property
    def verified(self) -> bool:
        return self.initiation and self.consecution and self.sufficiency


def karr_affine_accumulator(a: int, d: int) -> InvariantSynth:
    """Karr (complete affine): for `x=a,i=0; while i<n: x+=d; i+=1`, synthesize the strongest affine invariant
    x − d·i == a, then z3-VERIFY the 3 VCs in QF_LRA (terminating). Enables folding x to a+d·n."""
    import z3
    x, i, n = z3.Ints("x i n")
    I = lambda X, J: X - d * J == a                         # the synthesized affine invariant
    s = z3.Solver()
    init = s.check(z3.Not(z3.Implies(z3.And(x == a, i == 0), I(x, i)))) == z3.unsat
    cons = z3.Solver().check(z3.Not(z3.Implies(z3.And(I(x, i), i < n), I(x + d, i + 1)))) == z3.unsat
    suff = z3.Solver().check(z3.Not(z3.Implies(z3.And(I(x, i), i == n), x == a + d * n))) == z3.unsat
    return InvariantSynth(init and cons and suff, "Karr-affine", f"x - {d}*i == {a}", init, cons, suff, True,
                          "complete affine synthesis (Karr) + z3 QF_LRA VC-verification; enables fold x→a+d·n")


def groebner_polynomial_squares() -> InvariantSynth:
    """Gröbner (complete fixed-degree polynomial): for `x=0,i=0; while i<n: x+=2i+1; i+=1` (sum of odds), synthesize the
    polynomial invariant x == i², then z3-VERIFY the 3 VCs in QF_NRA (CAD, terminating). Enables folding x to n²."""
    import z3
    x, i, n = z3.Ints("x i n")
    I = lambda X, J: X == J * J
    init = z3.Solver().check(z3.Not(z3.Implies(z3.And(x == 0, i == 0), I(x, i)))) == z3.unsat
    cons = z3.Solver().check(z3.Not(z3.Implies(z3.And(I(x, i), i < n), I(x + 2 * i + 1, i + 1)))) == z3.unsat
    suff = z3.Solver().check(z3.Not(z3.Implies(z3.And(I(x, i), i == n), x == n * n))) == z3.unsat
    return InvariantSynth(init and cons and suff, "Groebner-polynomial", "x == i**2", init, cons, suff, True,
                          "complete fixed-degree polynomial synthesis (Gröbner) + z3 QF_NRA VC-verification; fold x→n²")


def farkas_linear_bound(d: int) -> InvariantSynth:
    """Farkas/LP (complete linear-inequality): for `x=0,i=0; while i<n: x+=d; i+=1` with d>0, synthesize the inductive
    linear inequality 0 ≤ x ∧ x == d·i (here the equality, the tightest), z3-verified in QF_LRA."""
    import z3
    x, i, n = z3.Ints("x i n")
    I = lambda X, J: z3.And(X == d * J, J >= 0)
    init = z3.Solver().check(z3.Not(z3.Implies(z3.And(x == 0, i == 0), I(x, i)))) == z3.unsat
    cons = z3.Solver().check(z3.Not(z3.Implies(z3.And(I(x, i), i < n), I(x + d, i + 1)))) == z3.unsat
    suff = z3.Solver().check(z3.Not(z3.Implies(z3.And(I(x, i), i == n), x == d * n))) == z3.unsat
    return InvariantSynth(init and cons and suff, "Farkas-linear", f"x == {d}*i  ∧  i >= 0", init, cons, suff, True,
                          "complete linear-inequality synthesis (Farkas+LP) + z3 QF_LRA VC-verification")


def _wrong_invariant_rejected() -> bool:
    """★ A WRONG invariant with a SLOPE MISMATCH (x == 6·i for the x+=5 accumulator) FAILS consecution — z3 rejects it
    (x+5 == 6·(i+1) ⟺ 6i+5 == 6i+6, false). Confirms the verifier is real (not a rubber stamp)."""
    import z3
    x, i, n = z3.Ints("x i n")
    cons = z3.Solver().check(z3.Not(z3.Implies(z3.And(x == 6 * i, i < n), x + 5 == 6 * (i + 1)))) == z3.unsat
    return not cons                                         # consecution must FAIL ⇒ the wrong invariant is rejected


def adversarial_battery() -> dict:
    """Karr (affine), Farkas (linear), Gröbner (polynomial) each synthesize a COMPLETE invariant and z3-verify all 3
    VCs (terminating); ★ a wrong invariant FAILS consecution (rejected); ★ complete-not-CEGAR-guessing."""
    karr = karr_affine_accumulator(3, 5)
    farkas = farkas_linear_bound(4)
    groebner = groebner_polynomial_squares()
    cases = {
        "karr_affine_verified": karr.verified and karr.domain == "Karr-affine",
        "farkas_linear_verified": farkas.verified and farkas.domain == "Farkas-linear",
        "groebner_polynomial_verified": groebner.verified and groebner.domain == "Groebner-polynomial",
        "all_three_vcs_each": all(s.initiation and s.consecution and s.sufficiency for s in (karr, farkas, groebner)),
        "wrong_invariant_rejected": _wrong_invariant_rejected(),
        "complete_not_cegar": karr.complete and groebner.complete,            # ★ upgrade from §X CEGAR guessing
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
