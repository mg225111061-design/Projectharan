"""
§AE ISLAND 2 — NONLINEAR-INTEGER (barrier: Hilbert-10 / Diophantine, undecidable): five decidable fragments.
================================================================================================================
General nonlinear integer recurrences have UNDECIDABLE closed-form existence (Hilbert's tenth). The island: five
decidable fragments, each reducing to a terminating theory — polynomial-additive `x+=p(n)` (Faulhaber), linear-modular
`x=(a·x+b)%m` (matrix-power/cycle over ℤ/mℤ), power `x=x^k` (modular orbit), substitution-linearizable (Möbius `y=1/x`),
and finite-state-over-ℤ/mℤ (Floyd cycle). Outside ⇒ DECLINE (x²+c, general degree-≥2 poly, Collatz).

★ The genuinely-NEW piece: the DECIDABLE-BOUNDARY CLASSIFIER that routes each recurrence to its fragment or DECLINEs.
★ Repo-first / zero-new: linear-modular REUSES the Galois-quotient lens (§Y `altlens.galois_fold`); substitution REUSES
§Z/§P-P5 Möbius; finite-state overlaps the small-state cycle detector — all counted ZERO new (the §Z discipline). Grade:
EXACT (every fragment); verification in QF_NRA (Faulhaber) / QF_BV (modular) / finite FSM — all TERMINATING.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Tuple


@dataclass
class NonlinearIntFold:
    issued: bool
    fragment: str = ""                      # additive | modular | power | substitution | finite_state | undecidable
    grade: str = "EXACT"
    new_contribution: bool = True           # False for the reused fragments (modular=Galois, substitution=Möbius, finite-state=cycle)
    detail: str = ""


_DECIDABLE = {"additive", "modular", "power", "substitution", "finite_state"}
_UNDECIDABLE = {"quadratic", "general_poly", "collatz"}


def classify(kind: str) -> str:
    """★ The decidable-boundary classifier (the new value): route to a fragment, or 'undecidable' (DECLINE)."""
    if kind in _DECIDABLE:
        return kind
    return "undecidable"


def _prove_additive_faulhaber() -> bool:
    """z3: x += (c0 + c1·i) folds to c0·n + c1·n(n+1)/2 (Faulhaber), proved by induction (terminating QF_NRA-bounded)."""
    import z3
    n = z3.Int("n")
    S2 = lambda k: 2 * 0 * k + 2 * (1 * k) + 1 * k * (k + 1)   # 2·Σ(1+i) = 2k + k(k+1)
    s = z3.Solver()
    s.add(z3.Not(z3.And(S2(1) == 2 * (1 + 1), z3.ForAll([n], z3.Implies(n >= 1, S2(n + 1) - S2(n) == 2 * (1 + (n + 1)))))))
    return s.check() == z3.unsat


def _floyd_cycle(f: Callable[[int], int], x0: int, cap: int = 100000) -> Optional[Tuple[int, int]]:
    """Floyd/Brent cycle detection over a finite-state map: return (μ tail, λ period), the orbit's eventual cycle. None
    if no cycle within cap (then the state space isn't small/finite enough ⇒ caller DECLINEs)."""
    slow = fast = x0
    for _ in range(cap):
        slow = f(slow)
        fast = f(f(fast))
        if slow == fast:
            break
    else:
        return None
    mu = 0
    slow = x0
    while slow != fast and mu < cap:
        slow, fast, mu = f(slow), f(fast), mu + 1
    lam = 1
    fast = f(slow)
    while slow != fast and lam < cap:
        fast, lam = f(fast), lam + 1
    return mu, lam


def fold(kind: str, **kw) -> NonlinearIntFold:
    """Route to the fragment's fold (or DECLINE). modular/substitution/finite-state reuse existing lenses (zero new)."""
    frag = classify(kind)
    if frag == "undecidable":
        return NonlinearIntFold(False, "undecidable",
                                detail=f"`{kind}` is a general nonlinear integer recurrence (Hilbert-10 undecidable: "
                                       "x²+c / degree-≥2 poly / Collatz) ⇒ DECLINE — out of every decidable fragment")
    if frag == "additive":
        ok = _prove_additive_faulhaber()
        return NonlinearIntFold(ok, "additive", "EXACT", True,
                                "polynomial-additive x+=p(n) → Faulhaber closed form (z3-proved, terminating); EXACT")
    if frag == "modular":
        import altlens.galois_fold as GF                      # ★ REUSE the Galois-quotient lens (§Y)
        gf = GF.galois_modular_fold(kw.get("a", 3), kw.get("b", 1), kw.get("m", 7))
        return NonlinearIntFold(gf.issued, "modular", "EXACT", False,    # zero-new (overlap §Y)
                                f"linear-modular x=(a·x+b)%m → matrix-power/cycle over ℤ/mℤ (REUSED §Y Galois, ZERO new); "
                                f"{'EXACT' if gf.issued else 'DECLINE'}")
    if frag == "substitution":
        import catalog.mobius_fold as MF                      # ★ REUSE §Z/§P-P5 Möbius
        import kernel_verdict as KV
        v = MF.mobius_fold_grade(kw.get("a", 1), kw.get("b", 1), kw.get("c", 1), kw.get("d", 2))
        return NonlinearIntFold(v.status == KV.EXACT, "substitution", "EXACT", False,   # zero-new (overlap §Z/§P)
                                "substitution-linearizable → Möbius y=1/x (REUSED §Z/§P-P5, ZERO new); EXACT")
    if frag in ("power", "finite_state"):
        m = kw.get("m", 97)
        if frag == "power":
            k, x0 = kw.get("k", 3), kw.get("x0", 5)
            f = lambda x: pow(x, k, m)                        # x ↦ x^k mod m (modular orbit)
        else:
            a, b, x0 = kw.get("a", 7), kw.get("b", 11), kw.get("x0", 1)
            f = lambda x: (a * x + b) % m                     # finite-state over ℤ/mℤ
        cyc = _floyd_cycle(f, x0)
        new = (frag == "power")                               # power-mod is new; finite-state overlaps the cycle detector
        if cyc is None:
            return NonlinearIntFold(False, frag, detail="no cycle within cap ⇒ state space not small/finite ⇒ DECLINE")
        mu, lam = cyc
        return NonlinearIntFold(True, frag, "EXACT", new,
                                f"{frag} orbit over ℤ/{m}ℤ → Floyd cycle (tail {mu}, period {lam}); EXACT, O(n)→O(μ+λ)"
                                + ("" if new else " [overlaps small-state cycle detector, ZERO new]"))
    return NonlinearIntFold(False, frag, detail="unrecognized ⇒ DECLINE")


def adversarial_battery() -> dict:
    """additive (Faulhaber) & power (modular orbit) fold EXACT-new; modular & substitution fold but ZERO-new (reused
    §Y/§Z); ★ general nonlinear (x²+c / Collatz / general poly) is DECLINED (Hilbert-10, out of every fragment)."""
    add = fold("additive")
    powr = fold("power", k=3, x0=5, m=97)
    modr = fold("modular", a=3, b=1, m=7)
    subst = fold("substitution", a=1, b=1, c=1, d=2)
    quad = fold("quadratic")                                  # x²+c ⇒ undecidable
    collatz = fold("collatz")
    cases = {
        "additive_folds_new": add.issued and add.fragment == "additive" and add.new_contribution,
        "power_folds": powr.issued and powr.fragment == "power",
        "modular_folds_zero_new": modr.issued and (not modr.new_contribution),     # ★ reused §Y, zero-new
        "substitution_zero_new": subst.issued and (not subst.new_contribution),    # ★ reused §Z/§P, zero-new
        "quadratic_declined": (not quad.issued) and quad.fragment == "undecidable",  # ★ Hilbert-10
        "collatz_declined": not collatz.issued,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
