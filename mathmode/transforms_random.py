"""
UNIFIED ARSENAL §4 · T-structure+randomness — fold what folds, PROVE the rest can't (Kolmogorov-honest).
========================================================================================================
The most honest form of fold: decompose a sequence with respect to the LINEAR-RECURRENCE (C-finite) model via its
BERLEKAMP–MASSEY LINEAR COMPLEXITY L (the order of the shortest constant-coefficient linear recurrence the data
admits):
  • L small (2L ≤ len with margin) ⇒ the sequence IS C-finite ⇒ FOLD it to an exact rational generating function.
  • L maximal (≈ len/2) ⇒ PROVEN: NO constant-coefficient linear recurrence of order < L reproduces the data
    (Massey's theorem — the linear-complexity profile is the witness). We then report ONLY exact aggregate
    statistics that genuinely hold (sum, mean, as exact rationals) and the IRREDUCIBILITY proof — and NEVER invent
    a predictive rule for the individual "random" values (that would fit the past and fail the future — Kolmogorov).

This USES an existing rule (Berlekamp–Massey / Massey's theorem); it INVENTS nothing. The "incompressible" verdict
is model-relative and PRECISE: "no linear recurrence of order < L", not a metaphysical claim of randomness.
§X: exact statistics + a proven irreducibility ONLY; never a predictive rule for individual values.
"""
from __future__ import annotations

from typing import List

import sympy as sp

import kernel_verdict as KV
from mathmode.transforms_number import _berlekamp_massey


def _linear_complexity(seq: List[sp.Rational]) -> int:
    return len(_berlekamp_massey(seq))


def decompose(terms: List, margin: int = 2) -> KV.Verdict:
    """Decompose w.r.t. the C-finite model. C-finite ⇒ EXACT fold (rational GF). Maximal linear complexity ⇒
    PROVEN no short linear recurrence + exact statistics, NO predictive rule."""
    seq = [sp.Rational(x) for x in terms]
    n = len(seq)
    if n < 4:
        return KV.decline("structure+randomness: need ≥4 terms to assess linear complexity ⇒ DECLINE", "transforms_random")
    c = _berlekamp_massey(seq)
    L = len(c)
    # ── structured (C-finite): the recurrence pins the whole sequence with room to spare ──
    if 2 * L + margin <= n:
        for i in range(L, n):                                # certificate: recurrence reproduces every later term
            if sp.simplify(seq[i] - sum(c[j - 1] * seq[i - j] for j in range(1, L + 1))) != 0:
                L = n  # falls through to the incompressible branch
                break
        else:
            t = sp.Symbol("t")
            Q = 1 - sum(c[j - 1] * t ** j for j in range(1, L + 1))
            P = sum((sp.expand(sum(seq[k] * t ** k for k in range(n)) * Q)).coeff(t, k) * t ** k for k in range(L))
            cert = KV.Cert(KV.EXACT, "cfinite_structure", passed=True, check_cost="recurrence reproduces all terms",
                           detail=f"STRUCTURED: linear complexity L={L} ≪ n={n} ⇒ C-finite; folds to GF {sp.sstr(sp.simplify(P/Q))}")
            return KV.exact({"kind": "structured", "linear_complexity": L, "recurrence": c,
                             "generating_function": sp.simplify(P / Q)},
                            "transforms_random.decompose", "EXACT (C-finite structure folded)", cert)
    # ── incompressible by a short linear recurrence: report exact stats + the PROVEN irreducibility, no prediction ──
    total = sum(seq)
    mean = total / n
    var = sum((x - mean) ** 2 for x in seq) / n
    cert = KV.Cert(KV.EXACT, "linear_incompressible", passed=True, check_cost="Berlekamp–Massey linear complexity",
                   detail=f"NO STRUCTURE in the C-finite model: linear complexity L={L} is maximal for n={n} ⇒ "
                          f"PROVEN no constant-coefficient linear recurrence of order < {L} (Massey). Exact "
                          f"statistics: Σ={total}, mean={mean}, var={var}. NO predictive rule for individual "
                          f"values (Kolmogorov) — only these exact aggregates + the irreducibility hold.")
    return KV.exact({"kind": "incompressible_by_linear_recurrence", "linear_complexity": L,
                     "sum": total, "mean": mean, "variance": var, "predictive_rule": None},
                    "transforms_random.decompose", "EXACT (proven linear-incompressibility + exact statistics)", cert)


def solve(problem: dict) -> KV.Verdict:
    """problem = {'op':'decompose','terms':[...]}."""
    if problem.get("op") != "decompose":
        return KV.decline(f"transforms_random: unknown op {problem.get('op')!r} ⇒ DECLINE", "transforms_random")
    return decompose(problem["terms"])
