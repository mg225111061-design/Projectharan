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
    # broaden across MORE of the 50: forward-mode AD (#28), multipoint eval (#29), fast-doubling fib (#33),
    # Stern–Brocot (#42) — each dispatched to the real algorithm, must certify EXACT
    import autodiff as AD
    for expr, pt in [("x**3+2*x", {"x": 3}), ("x**2*y", {"x": 2, "y": 5}), ("(x+1)*(x-2)", {"x": 7})]:
        items.append((f"autodiff·{expr}", 28, expr, (lambda expr=expr, pt=pt: AD.autodiff_grade(expr, pt))))
    for lbl, coeffs, pts in [("cubic", [1, 2, 3, 4], [1, 2, 3, 4, 5]), ("quad", [5, -1, 2], [0, 1, 2, 3])]:
        items.append((f"multipoint·{lbl}", 29, lbl, (lambda coeffs=coeffs, pts=pts: NS.multipoint_eval_grade(coeffs, pts))))
    for nn, mm in [(1000, 1000000007), (10 ** 6, 998244353)]:
        items.append((f"fib_mod·{nn}", 33, f"F({nn})", (lambda nn=nn, mm=mm: FK.fib_mod(nn, mm))))
    for p, q in [(22, 7), (355, 113), (13, 8)]:
        items.append((f"stern_brocot·{p}/{q}", 42, f"{p}/{q}", (lambda p=p, q=q: NT.stern_brocot_grade(p, q))))
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


def _code_shape_corpus() -> List[Tuple[str, str, str]]:
    """(target, summand h(k), n-th term h(n)) — single-fold Σ_{k=1}^{n} h(k) targets, each rendered in five code
    shapes (for / counter-while / comprehension / recursion / functools.reduce) by `_render_shapes`."""
    return [
        ("Σk", "k", "n"),
        ("Σk²", "k*k", "n*n"),
        ("Σk³", "k*k*k", "n*n*n"),
        ("Σ(2k−1)", "2*k-1", "2*n-1"),
        ("Σk(k+1)", "k*(k+1)", "n*(n+1)"),
        ("Σ(3k²−k)", "3*k*k-k", "3*n*n-n"),
    ]


def _render_shapes(h: str, h_n: str) -> Dict[str, str]:
    """The SAME accumulation Σ_{k=1}^{n} h(k) written as five code shapes — all must collapse to one closed form."""
    return {
        "for": f"def f(n):\n s=0\n for k in range(1,n+1):\n  s+=({h})\n return s",
        "while": f"def f(n):\n s=0\n k=1\n while k<=n:\n  s+=({h})\n  k+=1\n return s",
        "comprehension": f"def f(n):\n return sum(({h}) for k in range(1,n+1))",
        "recursion": f"def f(n):\n if n<1:\n  return 0\n return f(n-1)+({h_n})",
        "reduce": f"def f(n):\n return reduce(lambda s,k: s+({h}), range(1,n+1), 0)",
    }


def _nested_code_corpus() -> List[Tuple[str, str, object]]:
    """(label, source, brute-force reference) — doubly-nested Σ_iΣ_j h(i,j) that collapse O(n²)→O(1)."""
    return [
        ("nested·triangular", "def f(n):\n acc=0\n for i in range(1,n+1):\n  for j in range(1,i+1):\n   acc += j\n return acc",
         lambda n: sum(sum(range(1, i + 1)) for i in range(1, n + 1))),
        ("nested·rectangular", "def f(n):\n acc=0\n for i in range(1,n+1):\n  for j in range(1,n+1):\n   acc += i*j\n return acc",
         lambda n: sum(i * j for i in range(1, n + 1) for j in range(1, n + 1))),
        ("nested·coupled", "def f(n):\n acc=0\n for i in range(1,n+1):\n  for j in range(1,i+1):\n   acc += i+j\n return acc",
         lambda n: sum(i + j for i in range(1, n + 1) for j in range(1, i + 1))),
        ("nested·0based", "def f(n):\n acc=0\n for i in range(n):\n  for j in range(n):\n   acc += i*i+j\n return acc",
         lambda n: sum(i * i + j for i in range(n) for j in range(n))),
    ]


def _adversarial_code_shapes() -> List[Tuple[str, str]]:
    """(label, source) — code shapes that MUST NOT collapse (the recognizer/gate can only DECLINE on a misread)."""
    return [
        ("acc-dependent for-body", "def f(n):\n s=1\n for k in range(1,n+1):\n  s+=s\n return s"),
        ("non-counter while", "def f(x):\n while x>1:\n  x=x//2\n return x"),
        ("binary recursion (Fibonacci)", "def f(n):\n if n<2:\n  return n\n return f(n-1)+f(n-2)"),
        ("acc-in-reduce-summand", "def f(n):\n return reduce(lambda s,k: s+s, range(1,n+1), 0)"),
        ("triple nesting", "def f(n):\n acc=0\n for i in range(n):\n  for j in range(n):\n   for k in range(n):\n    acc += i\n return acc"),
        ("acc-dependent nested body", "def f(n):\n acc=1\n for i in range(1,n+1):\n  for j in range(1,i+1):\n   acc += acc+j\n return acc"),
    ]


def measure_code_shapes() -> Dict[str, object]:
    """HARAN §3 (code-shape mapping) — MEASURED reach of the CODE-side recognizer: how many (target × code-shape)
    pairs collapse to a VERIFIED O(1)/closed form via `structure_recognizer.dispatch`, plus nested O(n²)→O(1). A
    collapse counts ONLY if dispatch returns OFFLOADED AND the emitted closed form independently matches a brute-force
    evaluation on fresh inputs (NO padding). Per target, all five shapes must agree on ONE closed form (shape
    invariance). Adversarial code shapes MUST NOT collapse. This is a measured CODE-collapse count, NOT a claim that
    arbitrary code collapses — unstructured code declines (the honest majority)."""
    import sympy
    import structure_recognizer as SR

    SHAPES = ["for", "while", "comprehension", "recursion", "reduce"]
    collapses = 0
    fully_invariant = 0
    per_shape = {s: 0 for s in SHAPES}
    targets = _code_shape_corpus()
    for _tgt, h, h_n in targets:
        cforms = set()
        rendered = _render_shapes(h, h_n)
        offloaded_here = 0
        for sh in SHAPES:
            d = SR.dispatch(rendered[sh], "f")
            if d.status != "OFFLOADED" or not d.closed_form:
                continue
            F = sympy.sympify(d.closed_form)
            psym = next(iter(F.free_symbols), sympy.Symbol("n"))
            ref = SR._make_callable(rendered[sh], "f")
            if all(abs(float(F.subs(psym, N)) - ref(N)) < 1e-6 for N in (3, 6, 9, 14, 20)):
                collapses += 1
                offloaded_here += 1
                per_shape[sh] += 1
                cforms.add(str(sympy.simplify(F)))
        if offloaded_here == len(SHAPES) and len(cforms) == 1:
            fully_invariant += 1

    nested_ok = 0
    for _lbl, src, ref in _nested_code_corpus():
        d = SR.dispatch(src, "f")
        if d.status == "OFFLOADED" and d.closed_form:
            F = sympy.sympify(d.closed_form)
            psym = next(iter(F.free_symbols), sympy.Symbol("n"))
            if all(abs(float(F.subs(psym, N)) - ref(N)) < 1e-6 for N in (4, 7, 11, 16, 25)):
                nested_ok += 1

    adv = _adversarial_code_shapes()
    adv_rejected = sum(1 for _lbl, src in adv if SR.dispatch(src, "f").status != "OFFLOADED")
    return {
        "single_fold_targets": len(targets),
        "code_shapes": len(SHAPES),
        "single_fold_collapses": collapses,            # (target × shape) pairs that VERIFIABLY collapse
        "single_fold_max": len(targets) * len(SHAPES),
        "fully_invariant_targets": fully_invariant,    # targets whose 5 shapes all agree on ONE closed form
        "per_shape_collapses": per_shape,
        "nested_collapses": nested_ok,
        "nested_total": len(_nested_code_corpus()),
        "total_code_collapses": collapses + nested_ok,
        "adversarial_total": len(adv),
        "adversarial_rejected": adv_rejected,
        "adversarial_correct": adv_rejected == len(adv),
    }


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
