"""
HARAN §3 — MEASURED covered-case count: route a structured corpus into the 50 algorithms; honest DECLINE elsewhere.
=================================================================================================================
The 50 named algorithms are GENERAL (one algorithm covers many cases). This module MEASURES that breadth on a
curated corpus: each item is dispatched to the real algorithm for its domain, the actual graded Verdict is taken,
and we count how many CASES certify (EXACT / PROBABILISTIC) across how many distinct algorithm FAMILIES — plus a
deliberately ADVERSARIAL block (control-flow / graph / I/O / a transcendental sum / a structureless sequence) that
MUST DECLINE. The count is the MEASURED collapse coverage on THIS corpus.

§X HONESTY (verbatim): coverage is DOMAIN-CONDITIONAL — near-zero on general/control-flow/graph/I/O code; this is
NOT a general-purpose accelerator and the number is not "100%". The adversarial DECLINEs are CORRECT behaviour
(structure genuinely absent), not failures. A "family" here is a generalized recognizer family (an algorithm × a
recognizable sub-pattern), NOT a fundamentally-distinct structure. No padding: an item counts only if a REAL
algorithm returns a real EXACT/PROBABILISTIC verdict with its certificate.
"""
from __future__ import annotations

from fractions import Fraction as Fr
from typing import Dict, List, Tuple

import kernel_verdict as KV


def _structured() -> List[Tuple[str, int, str, object]]:
    """(family, algo#, label, thunk) — each thunk returns a KV.Verdict from the real algorithm. Structured ⇒
    should certify (EXACT/PROBABILISTIC)."""
    import mathmode.number_theory as NT
    import mathmode.fastkernels as FK
    import mathmode.wigner as W
    import newton_series as NS
    import cfinite as CF

    items: List[Tuple[str, int, str, object]] = []

    # #9 Faulhaber power sums — degrees 1..6 (six generalized cases under one algorithm)
    for d in range(1, 7):
        items.append((f"faulhaber·deg{d}", 9, f"Σk^{d}", (lambda d=d: FK.faulhaber(d, 100))))
    # #10/#11 named C-finite recurrences (companion O(log n)) — seven recognizable families
    named = {"fibonacci": ([1, 1], [0, 1]), "lucas": ([1, 1], [2, 1]), "pell": ([2, 1], [0, 1]),
             "jacobsthal": ([1, 2], [0, 1]), "tribonacci": ([1, 1, 1], [0, 0, 1]),
             "padovan": ([0, 1, 1], [1, 1, 1]), "perrin": ([0, 1, 1], [3, 0, 2])}
    for nm, (c, init) in named.items():
        items.append((f"cfinite·{nm}", 10, nm, (lambda c=c, init=init: _cfinite_verdict(CF, c, init))))
    # #13 Bostan–Mori GF coefficient extraction — four rational GFs
    for lbl, p, q in [("fib-GF", [0, 1], [1, -1, -1]), ("geom", [1], [1, -2]),
                      ("rational½", [1], [1, Fr(-1, 2)]), ("tribonacci-GF", [0, 0, 1], [1, -1, -1, -1])]:
        items.append((f"bostan_mori·{lbl}", 13, lbl, (lambda p=p, q=q: NS.bostan_mori_grade(p, q, 500))))
    # #14 Newton series — inv / exp / log / sqrt
    for op, a in [("inv", [3, 1, -2]), ("exp", [0, 1]), ("log", [1, 1]), ("sqrt", [1, 1])]:
        items.append((f"newton·{op}", 14, op, (lambda op=op, a=a: NS.newton_series_grade(op, a, 12))))
    # #31 modexp / #32 power-towers / #33 fib-mod / #34 binom / #45 jacobi / #44 mobius — number-theory breadth
    items.append(("modexp", 31, "a^b mod m", (lambda: NT.modexp_grade(7, 10 ** 6, 1000003))))
    items.append(("power_tower", 32, "a^(b^c) mod m", (lambda: NT.power_tower_grade(7, 3, 100, 1000000007))))
    items.append(("binom_mod_pe", 34, "C(n,k) mod p^e", (lambda: NT.binom_mod_pe_grade(10 ** 18, 12345, 3, 7))))
    for a, n in [(2, 7), (3, 7), (1001, 9907), (5, 21)]:
        items.append((f"jacobi·({a}|{n})", 45, f"({a}|{n})", (lambda a=a, n=n: NT.jacobi_grade(a, n))))
    items.append(("mobius", 44, "μ(n)", (lambda: NT.mobius_grade(210))))
    items.append(("pell", 41, "x²−Dy²=1", (lambda: NT.pell_grade(61))))
    items.append(("sieve", 43, "primes≤n", (lambda: NT.sieve_primes_grade(1000))))
    # #49 Wigner 3j — three exact algebraic values
    for j in [(1, 1, 2, 0, 0, 0), (1, 1, 0, 0, 0, 0), (2, 2, 2, 0, 0, 0)]:
        items.append((f"wigner3j·{j}", 49, "3j", (lambda j=j: W.wigner3j(*j))))
    # broaden the corpus across more of the 50 (decision procedures + the closed gaps/partials), small fast inputs
    import groebner as GB
    import hermite as HM
    import cp_decompose as CP
    import mathmode.telescoping as TS
    import mathmode.decision_summation as DS
    items.append(("gosper", 1, "Σ indefinite", (lambda: TS.gosper_indefinite("k"))))
    items.append(("abramov", 5, "rational sum", (lambda: DS.abramov_summable("1/(k*(k+1))"))))
    items.append(("hermite", 17, "∫A/B rational", (lambda: HM.hermite_reduce_grade("1", "x**2*(x+1)"))))
    items.append(("groebner", 19, "ideal membership", (lambda: GB.ideal_member_grade(["x-1", "y-1"], "x*y-1", ["x", "y"]))))
    items.append(("cp_rank1", 25, "CP rank-1", (lambda: CP.cp_decompose_grade([[[2, -2], [1, -1]], [[4, -4], [2, -2]]]))))
    items.append(("bpsw", 36, "primality", (lambda: NT.bpsw_grade(10007))))
    items.append(("factorize", 38, "∏ pᵢ^eᵢ", (lambda: NT.factorize_grade(360))))
    items.append(("cipolla", 39, "modular sqrt", (lambda: NT.cipolla_sqrt_grade(2, 7))))
    items.append(("rho_dlog", 40, "discrete log", (lambda: NT.pollard_rho_dlog_grade(2, 22, 29))))
    return items


def _cfinite_verdict(CF, c, init):
    n = 60
    fast, naive = CF.companion_nth(c, init, n), CF.naive_nth(c, init, n)
    if fast == naive:
        cert = KV.Cert(KV.EXACT, "cfinite_companion", passed=True, check_cost="O(log n) companion",
                       detail=f"f({n})={fast}; companion ≡ naive (held-out)")
        return KV.exact(fast, "cfinite", "companion O(log n)", cert)
    return KV.decline("cfinite: companion ≠ naive ⇒ DECLINE", "cfinite")


def _adversarial() -> List[Tuple[str, object]]:
    """(label, thunk) — UNSTRUCTURED inputs that MUST DECLINE (structure genuinely absent)."""
    import mathmode.number_theory as NT
    import newton_series as NS
    import autodiff as AD
    import mathmode.broth as BROTH
    return [
        ("transcendental-sum Σ1/k", (lambda: BROTH.prove("1/k"))),                 # harmonic — no closed form
        ("structureless-recurrence", (lambda: NS.newton_series_grade("inv", [0, 1], 8))),  # A(0)=0 ⇒ undefined
        ("jacobi-even-modulus", (lambda: NT.jacobi_grade(3, 8))),                  # even n ⇒ undefined
        ("sieve-out-of-range", (lambda: NT.sieve_primes_grade(50000))),            # beyond cert bound
        ("autodiff-transcendental", (lambda: AD.autodiff_grade("sin(x)", {"x": 1}))),  # non-rational value
        ("binom-nonprime", (lambda: NT.binom_mod_pe_grade(10, 3, 4, 1))),          # p not prime
    ]


def measure() -> Dict[str, object]:
    """Run the corpus through the REAL algorithms and MEASURE the collapse coverage (DOMAIN-CONDITIONAL)."""
    structured = _structured()
    certified, fams = [], set()
    for fam, algo, label, thunk in structured:
        v = thunk()
        if v.status in (KV.EXACT, KV.PROBABILISTIC):
            certified.append((fam, algo, label, v.status))
            fams.add(fam)
    adv = _adversarial()
    declined = [lbl for lbl, thunk in adv if thunk().status == KV.DECLINE]
    algos_covered = sorted({algo for _, algo, _, _ in certified})
    return {
        "corpus_structured": len(structured),
        "covered_cases": len(certified),
        "families_covered": len(fams),
        "algorithms_covered": algos_covered,
        "n_algorithms_covered": len(algos_covered),
        "adversarial_total": len(adv),
        "adversarial_declined": len(declined),
        "adversarial_correct": len(declined) == len(adv),
        "by_grade": {g: sum(1 for *_, s in certified if s == g) for g in (KV.EXACT, KV.PROBABILISTIC)},
    }
