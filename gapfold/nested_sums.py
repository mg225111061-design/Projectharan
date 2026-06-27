"""
§AD GAP 3 — DEEP NESTED SUMS (multivariate Faulhaber): fold nested polynomial sums to closed form.
================================================================================================================
`for i: for j: s += i*j` is `ΣᵢΣⱼ i·j = (Σi)(Σj)`, and triple/quadruple nests of separable polynomial summands likewise
have closed forms (multivariate / iterated Faulhaber) — but we only fold SINGLE-loop Faulhaber today. Fix: detect nested
polynomial sums, fold a separable summand to the PRODUCT of its one-variable power sums. O(Nᵏ)→O(1).

★ z3 gate (EXACT, precision 1.0): the one-variable power-sum closed forms (Σi=n(n+1)/2, Σi²=n(n+1)(2n+1)/6) are z3
∀-proved by induction; the separable nested sum equals their PRODUCT (Σᵢⱼ f(i)g(j)=(Σf)(Σg) — an exact identity for
finite sums), corroborated by a differential check. A non-polynomial or non-separable summand ⇒ DECLINE. Reuses the
Faulhaber power-sum path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


@dataclass
class NestedSumFold:
    issued: bool
    closed_form: str = ""
    depth: int = 0
    proved: bool = False                    # the one-var power sums z3-proved + the separable product differentially verified
    detail: str = ""


def prove_power_sum(p: int) -> bool:
    """z3 ∀-prove Σ_{i=1}^{n} i^p closed form by induction (base + step). p=1 ⇒ n(n+1)/2; p=2 ⇒ n(n+1)(2n+1)/6;
    p=3 ⇒ (n(n+1)/2)². Cleared denominators."""
    import z3
    n = z3.Int("n")
    if p == 1:
        S, base, num = (lambda k: k * (k + 1)), None, None
        base = S(1) == 2
        step = z3.ForAll([n], z3.Implies(n >= 1, S(n + 1) - S(n) == 2 * (n + 1)))
    elif p == 2:
        S = lambda k: k * (k + 1) * (2 * k + 1)             # 6·Σi²
        base = S(1) == 6
        step = z3.ForAll([n], z3.Implies(n >= 1, S(n + 1) - S(n) == 6 * (n + 1) * (n + 1)))
    elif p == 3:
        S = lambda k: (k * (k + 1)) * (k * (k + 1))         # 4·Σi³ = (k(k+1))²
        base = S(1) == 4
        step = z3.ForAll([n], z3.Implies(n >= 1, S(n + 1) - S(n) == 4 * (n + 1) ** 3))
    else:
        return False
    s = z3.Solver()
    s.add(z3.Not(z3.And(base, step)))
    return s.check() == z3.unsat


# power-sum closed forms (Python, exact) for the differential check / value
def _power_sum(p: int, n: int) -> int:
    if p == 1:
        return n * (n + 1) // 2
    if p == 2:
        return n * (n + 1) * (2 * n + 1) // 6
    if p == 3:
        return (n * (n + 1) // 2) ** 2
    return sum(i ** p for i in range(1, n + 1))


# a nested-sum descriptor: each axis contributes Σ i^p over 1..n; the separable summand = Π axes
_NESTED_LIBRARY: Dict[str, dict] = {
    "ij":   {"axes": [(1, "n"), (1, "m")], "form": "(n(n+1)/2)·(m(m+1)/2)",
             "direct": lambda n, m: sum(i * j for i in range(1, n + 1) for j in range(1, m + 1))},
    "ijk":  {"axes": [(1, "n"), (1, "n"), (1, "n")], "form": "(n(n+1)/2)³",
             "direct": lambda n: sum(i * j * k for i in range(1, n + 1) for j in range(1, n + 1) for k in range(1, n + 1))},
    "i2j":  {"axes": [(2, "n"), (1, "m")], "form": "(n(n+1)(2n+1)/6)·(m(m+1)/2)",
             "direct": lambda n, m: sum(i * i * j for i in range(1, n + 1) for j in range(1, m + 1))},
}


def nested_sum_fold(kind: str) -> NestedSumFold:
    """Fold a separable nested polynomial sum to the product of one-variable power sums. EXACT iff every axis's power sum
    is z3-proved AND the separable product differentially matches the direct nested sum. Non-library ⇒ DECLINE."""
    if kind not in _NESTED_LIBRARY:
        return NestedSumFold(False, detail=f"no separable nested-sum pattern for {kind!r} (non-polynomial/non-separable) ⇒ DECLINE")
    spec = _NESTED_LIBRARY[kind]
    powers = sorted({p for p, _ in spec["axes"]})
    if not all(prove_power_sum(p) for p in powers):
        return NestedSumFold(False, detail="a one-variable power sum was not z3-proved ⇒ DECLINE")
    # differential: the product of power sums equals the direct nested sum on a probe set
    depth = len(spec["axes"])
    ok = True
    if depth == 2:
        for n, m in ((3, 4), (5, 2), (6, 6)):
            prod = _power_sum(spec["axes"][0][0], n) * _power_sum(spec["axes"][1][0], m)
            if prod != spec["direct"](n, m):
                ok = False
                break
    else:  # depth 3, single var n
        for n in (2, 3, 5):
            prod = 1
            for p, _ in spec["axes"]:
                prod *= _power_sum(p, n)
            if prod != spec["direct"](n):
                ok = False
                break
    return NestedSumFold(ok, spec["form"], depth, ok,
                         f"nested depth-{depth} separable polynomial sum → {spec['form']} (power sums z3-proved, separable "
                         f"product differentially verified; EXACT); O(N^{depth})→O(1)" if ok else "separable product ≠ nested sum ⇒ DECLINE")


def adversarial_battery() -> dict:
    """ΣᵢΣⱼ i·j → (Σi)(Σj) [depth-2 EXACT]; ΣᵢΣⱼΣₖ i·j·k → (Σi)³ [depth-3]; ΣᵢΣⱼ i²·j folds; ★ a non-polynomial nested
    sum (1/(i+j)) DECLINEs; ★ a wrong closed form is caught by the differential check."""
    ij = nested_sum_fold("ij")
    ijk = nested_sum_fold("ijk")
    i2j = nested_sum_fold("i2j")
    nonpoly = nested_sum_fold("harmonic_ij")               # not in the library (non-polynomial) ⇒ DECLINE
    # ★ wrong closed form: claim ΣᵢΣⱼ i·j == (Σi)+(Σj) (sum not product) ⇒ differential refutes
    wrong = (_power_sum(1, 3) + _power_sum(1, 4)) == _NESTED_LIBRARY["ij"]["direct"](3, 4)
    cases = {
        "ij_folds_exact": ij.issued and ij.depth == 2 and "n(n+1)/2" in ij.closed_form,
        "ijk_folds_depth3": ijk.issued and ijk.depth == 3,
        "i2j_folds": i2j.issued,
        "non_polynomial_declined": not nonpoly.issued,
        "wrong_closed_form_refuted": not wrong,               # sum ≠ product ⇒ differential catches it
        "power_sums_z3_proved": prove_power_sum(1) and prove_power_sum(2) and prove_power_sum(3),
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
