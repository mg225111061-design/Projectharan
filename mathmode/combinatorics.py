"""
MATH-Ascent §3 (arsenal) — COMBINATORICS / SUMS: Gosper creative-telescoping + exact combinatorial values.
==========================================================================================================
The jewel here is GOSPER'S ALGORITHM — a DECISION procedure for indefinite hypergeometric summation. Given a
hypergeometric term t(k) (t(k+1)/t(k) ∈ ℚ(k)), Gosper either returns a closed antidifference T with
T(k+1) − T(k) = t(k) — whence Σ_{k=a}^{b} t(k) = T(b+1) − T(a) for EVERY range — or PROVES that no
hypergeometric closed form exists (⇒ honest DECLINE, never a fabricated formula).

We use sympy as the SEARCH engine but do NOT trust it for the proof: the certificate is OUR own machine-check —
(1) the telescoping identity T(k+1) − T(k) − t(k) simplifies to 0 (symbolic) AND (2) exact-arithmetic agreement
Σ_{k=lo}^{hi} t(k) == T(hi+1) − T(lo) over several independent ranges (brute-force ground truth). Both must hold
for EXACT. This is the §2 fold philosophy applied to sums: recognize structure (hypergeometric) → fold to a
closed form → the telescoping identity IS the proof. Scalar combinatorial values (binomial, Catalan) come with a
recurrence cross-check (EXACT). No Lean/Coq — sympy searches, our checker proves.
"""
from __future__ import annotations

from math import comb, factorial
from typing import Optional

import sympy as sp
from sympy.concrete.gosper import gosper_sum as _gosper_sum

import kernel_verdict as KV


# ── Gosper: indefinite hypergeometric summation (the antidifference) ─────────────────────────────────────
def _telescopes(T: "sp.Expr", f: "sp.Expr", k: "sp.Symbol") -> bool:
    """Machine-check the telescoping identity T(k+1) − T(k) = f(k): symbolic-simplify-to-0 AND exact agreement
    at many integer points (a check independent of how T was found)."""
    diff = sp.simplify(T.subs(k, k + 1) - T - f)
    if diff != 0:
        return False
    # independent exact spot-check at integer points (skip any pole)
    pts, hit = 0, 0
    for v in range(1, 25):
        try:
            val = sp.nsimplify(T.subs(k, v + 1) - T.subs(k, v) - f.subs(k, v))
            val = sp.simplify(val)
        except Exception:
            continue
        if val.is_finite is False or val is sp.zoo or val is sp.nan:
            continue
        pts += 1
        if val == 0:
            hit += 1
    return pts >= 6 and hit == pts


def gosper_indefinite(f, k=None) -> KV.Verdict:
    """Indefinite hypergeometric sum: closed antidifference T (EXACT, telescoping-certified) or honest DECLINE
    (Gosper PROVES no hypergeometric closed form). `f` may be a sympy expr or a string; `k` the summation var."""
    k = k or sp.Symbol("k", integer=True)
    f = sp.sympify(f, locals={str(k): k}) if isinstance(f, str) else f
    try:
        T = _gosper_sum(f, k)
    except Exception as e:                       # Gosper not applicable to this form
        return KV.decline(f"gosper: not summable in closed form ({type(e).__name__}) ⇒ DECLINE", "combinatorics")
    if T is None:
        return KV.decline("gosper: PROVEN no hypergeometric closed form ⇒ DECLINE (not a fabricated formula)",
                          "combinatorics")
    if not _telescopes(T, f, k):                 # ★ our own certificate, not sympy's word ★
        return KV.decline("gosper: candidate failed the telescoping certificate ⇒ DECLINE", "combinatorics")
    cert = KV.Cert(KV.EXACT, "gosper_telescoping", passed=True, check_cost="symbolic Δ=0 + exact multi-point",
                   detail=f"T(k+1)−T(k)=f(k) verified ⇒ Σ_(k=a..b) f = T(b+1)−T(a) ∀ range; T={sp.sstr(T)}")
    return KV.exact(T, "combinatorics.gosper", "indefinite hypergeometric closed form", cert)


def gosper_definite(f, k, lo: int, hi: int) -> KV.Verdict:
    """Definite hypergeometric sum Σ_{k=lo}^{hi} f via the Gosper antidifference, cross-checked against the exact
    brute-force sum (EXACT) — or DECLINE when no closed form exists."""
    k = k or sp.Symbol("k", integer=True)
    f = sp.sympify(f, locals={str(k): k}) if isinstance(f, str) else f
    ind = gosper_indefinite(f, k)
    if ind.status != KV.EXACT:
        return ind
    T = ind.result
    closed = sp.simplify(T.subs(k, hi + 1) - T.subs(k, lo))
    brute = sp.Integer(0)
    for v in range(lo, hi + 1):                  # exact ground truth
        brute += sp.nsimplify(f.subs(k, v))
    if sp.simplify(closed - brute) != 0:
        return KV.decline(f"gosper_definite: closed form {closed} ≠ brute {brute} ⇒ DECLINE", "combinatorics")
    cert = KV.Cert(KV.EXACT, "gosper_definite", passed=True, check_cost="telescoping + exact brute cross-check",
                   detail=f"Σ_(k={lo}..{hi}) f = T({hi}+1)−T({lo}) = {closed}; ≡ exact brute-force sum")
    return KV.exact(closed, "combinatorics.gosper_definite", "O(1) closed form", cert)


# ── exact combinatorial values (recurrence-cross-checked) ────────────────────────────────────────────────
def binomial_grade(n: int, r: int) -> KV.Verdict:
    if n < 0 or r < 0:
        return KV.decline(f"binomial: need n,r ≥ 0 (got {n},{r}) ⇒ DECLINE", "combinatorics.binomial")
    if r > n:
        return KV.exact(0, "combinatorics.binomial", "O(1)",
                        KV.Cert(KV.EXACT, "binomial_zero", True, "O(1)", detail="r>n ⇒ C(n,r)=0"))
    c = comb(n, r)
    # certificate: Pascal's rule  C(n,r) = C(n-1,r-1) + C(n-1,r)  (re-derived, independent of comb's internals)
    if not (c == (comb(n - 1, r - 1) if r >= 1 else 0) + (comb(n - 1, r) if r <= n - 1 else 0) or n == 0):
        return KV.decline("binomial: Pascal recurrence cross-check failed ⇒ DECLINE", "combinatorics.binomial")
    cert = KV.Cert(KV.EXACT, "pascal_recurrence", passed=True, check_cost="O(1) one add",
                   detail=f"C({n},{r})={c}; Pascal C(n,r)=C(n-1,r-1)+C(n-1,r) verified")
    return KV.exact(c, "combinatorics.binomial", "O(r)", cert)


def catalan_grade(n: int) -> KV.Verdict:
    if n < 0:
        return KV.decline(f"catalan: need n ≥ 0 (got {n}) ⇒ DECLINE", "combinatorics.catalan")
    cat = comb(2 * n, n) // (n + 1)
    # certificate: two independent formulas agree — C_n = C(2n,n)/(n+1) == C(2n,n) − C(2n,n+1)
    alt = comb(2 * n, n) - (comb(2 * n, n + 1) if n + 1 <= 2 * n else 0)
    if cat != alt:
        return KV.decline("catalan: the two closed forms disagree ⇒ DECLINE", "combinatorics.catalan")
    cert = KV.Cert(KV.EXACT, "catalan_two_forms", passed=True, check_cost="O(1) second formula",
                   detail=f"C_{n}={cat}; C(2n,n)/(n+1) ≡ C(2n,n)−C(2n,n+1)")
    return KV.exact(cat, "combinatorics.catalan", "O(n)", cert)


def summation(problem: dict) -> KV.Verdict:
    """problem = {"op": "gosper"|"gosper_definite"|"binomial"|"catalan", ...}. Unknown op ⇒ honest DECLINE."""
    op = problem.get("op")
    k = sp.Symbol("k", integer=True)
    if op == "gosper":
        return gosper_indefinite(problem["term"], k)
    if op == "gosper_definite":
        return gosper_definite(problem["term"], k, problem["lo"], problem["hi"])
    if op == "binomial":
        return binomial_grade(problem["n"], problem["r"])
    if op == "catalan":
        return catalan_grade(problem["n"])
    return KV.decline(f"combinatorics: unknown op {op!r} ⇒ DECLINE", "combinatorics")
