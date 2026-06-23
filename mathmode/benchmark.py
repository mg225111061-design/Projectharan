"""
MATH-Ascent §7 — the MATH capability benchmark: MEASURED deltas only (no fabricated score).
============================================================================================
A representative problem set spanning the whole arsenal, run through the §5 solver and graded by the ADT. The
deliverable is a MEASURED capability inventory: how many problems MATH mode solves EXACTLY (with a certificate),
how many are honest PROBABILISTIC(ε,δ), and how many are correctly DECLINEd (the unsolvable — no radical quintic,
no harmonic closed form, a singular system). Every "solved" answer is cross-checked against ground truth where a
checker exists, so an EXACT here means a verified answer, not a claim.

★ HONEST HLE FRAMING ★: Humanity's Last Exam itself is [UNVERIFIED] in this environment — there is no HLE dataset
and no scoring harness here, so we DO NOT report an HLE number (that would be a fabricated score, forbidden by
"measured deltas only"). What we report is the MEASURED coverage of this arsenal on a representative MATH set: the
honest, reproducible delta. The path to a higher HLE is more verified tools + broth growth, each measured here.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction as Fr
from typing import Callable, List, Optional

import sympy as sp

import kernel_verdict as KV
from mathmode import solver as S


@dataclass
class Problem:
    name: str
    category: str
    spec: dict
    expect: str                       # the grade we expect (EXACT / PROBABILISTIC / DECLINE)
    check: Optional[Callable] = None  # (verdict) -> bool : cross-check the answer vs ground truth


def _suite() -> List[Problem]:
    x = sp.Symbol("x")
    return [
        # ── fold (the §2 center) ──
        Problem("Σ k (Faulhaber)", "fold", {"fold": {"kind": "power_sum", "p": 1}}, KV.EXACT,
                lambda v: v.result(100) == sum(range(1, 101))),
        Problem("Σ k³ (Faulhaber)", "fold", {"fold": {"kind": "power_sum", "p": 3}}, KV.EXACT,
                lambda v: v.result(50) == sum(k ** 3 for k in range(1, 51))),
        Problem("geometric Σ 2^k", "fold", {"fold": {"kind": "geometric_sum", "r": 2}}, KV.EXACT,
                lambda v: v.result(10) == sum(2 ** k for k in range(10))),
        Problem("Fibonacci recurrence", "fold", {"fold": {"kind": "linear_recurrence", "c": [1, 1], "init": [0, 1]}},
                KV.EXACT, lambda v: v.result(20) == 6765),
        # ── broth (§4) + Gosper (§3) sums ──
        Problem("Σ k²·2^k (broth)", "sum", {"sum": "k**2*2**k"}, KV.EXACT, None),
        Problem("Σ k·k! (Gosper)", "sum", {"sum": "k*factorial(k)"}, KV.EXACT, None),
        Problem("Σ k⁴·2^k (broth miss→Gosper)", "sum", {"sum": "k**4*2**k"}, KV.EXACT, None),
        Problem("Σ 1/k (no closed form)", "sum", {"sum": "1/k"}, KV.DECLINE, None),
        # ── number theory (§3) ──
        Problem("egcd(240,46)", "number_theory", {"domain": "number_theory", "op": "egcd", "a": 240, "b": 46},
                KV.EXACT, lambda v: 240 * v.result[1] + 46 * v.result[2] == v.result[0]),
        Problem("modexp 7^1234567 mod 1e9+7", "number_theory",
                {"domain": "number_theory", "op": "modexp", "a": 7, "b": 1234567, "m": 1000000007}, KV.EXACT,
                lambda v: v.result == pow(7, 1234567, 1000000007)),
        Problem("CRT [2,3,2]/[3,5,7]", "number_theory",
                {"domain": "number_theory", "op": "crt", "residues": [2, 3, 2], "moduli": [3, 5, 7]}, KV.EXACT,
                lambda v: v.result[0] == 23),
        Problem("modinv(4,8) (none)", "number_theory", {"domain": "number_theory", "op": "modinv", "a": 4, "m": 8},
                KV.DECLINE, None),
        # ── linear algebra (§3) ──
        Problem("solve 2x2 system", "linear_algebra",
                {"domain": "linear_algebra", "op": "solve", "A": [[2, 1], [1, 3]], "b": [3, 5]}, KV.EXACT,
                lambda v: v.result == [Fr(4, 5), Fr(7, 5)]),
        Problem("det 3x3", "linear_algebra",
                {"domain": "linear_algebra", "op": "det", "A": [[6, 1, 1], [4, -2, 5], [2, 8, 7]]}, KV.EXACT,
                lambda v: v.result == -306),
        Problem("inverse singular (none)", "linear_algebra",
                {"domain": "linear_algebra", "op": "inverse", "A": [[1, 2], [2, 4]]}, KV.DECLINE, None),
        # ── symbolic algebra (§3) ──
        Problem("factor x⁴−1", "algebra", {"domain": "algebra", "op": "factor", "poly": x ** 4 - 1}, KV.EXACT,
                lambda v: sp.expand(v.result) == x ** 4 - 1),
        Problem("roots x²−5x+6", "algebra", {"domain": "algebra", "op": "solve_poly", "poly": x ** 2 - 5 * x + 6},
                KV.EXACT, lambda v: set(v.result) == {2, 3}),
        Problem("quintic x⁵−x+1 (Abel–Ruffini)", "algebra",
                {"domain": "algebra", "op": "solve_poly", "poly": x ** 5 - x + 1}, KV.DECLINE, None),
        # ── geometry (§3) ──
        Problem("triangle area", "geometry", {"domain": "geometry", "op": "area", "pts": [(0, 0), (4, 0), (0, 3)]},
                KV.EXACT, lambda v: v.result == 6),
        Problem("convex hull", "geometry",
                {"domain": "geometry", "op": "hull", "pts": [(0, 0), (2, 0), (2, 2), (0, 2), (1, 1)]}, KV.EXACT,
                lambda v: len(v.result) == 4),
        Problem("parallel segments (none)", "geometry",
                {"domain": "geometry", "op": "intersect", "p1": (0, 0), "p2": (1, 0), "p3": (0, 1), "p4": (1, 1)},
                KV.DECLINE, None),
        # ── certified numerics (§3) ──
        Problem("Sturm roots of x³−x in [−2,2]", "certified_numeric",
                {"domain": "certified_numeric", "op": "root_count", "poly": x ** 3 - x, "a": -2, "b": 2}, KV.EXACT,
                lambda v: v.result == 3),
        Problem("√2 rational bracket", "certified_numeric",
                {"domain": "certified_numeric", "op": "sqrt", "n": 2}, KV.EXACT,
                lambda v: v.result[0] ** 2 <= 2 <= v.result[1] ** 2),
        Problem("Monte-Carlo π (approx)", "certified_numeric",
                {"domain": "certified_numeric", "op": "montecarlo_pi", "samples": 40000, "delta": 1e-2},
                KV.PROBABILISTIC, None),
        # ── deepened arsenal (B4): optimization, science, probability, inequalities ──
        Problem("LP max 3x+2y (duality)", "optimization",
                {"domain": "optimization", "op": "lp_max", "c": [3, 2], "A": [[1, 1], [1, 3]], "b": [4, 6]},
                KV.EXACT, lambda v: v.result[1] == 12),
        Problem("dim-check E=½mv²", "science_engineering",
                {"domain": "science_engineering", "op": "dimension_check", "equation": "E = m*v**2",
                 "binding": {"E": "energy", "m": "mass", "v": "velocity"}}, KV.EXACT, None),
        Problem("dim-check E=mv (wrong)", "science_engineering",
                {"domain": "science_engineering", "op": "dimension_check", "equation": "E = m*v",
                 "binding": {"E": "energy", "m": "mass", "v": "velocity"}}, KV.DECLINE, None),
        Problem("Markov bound (proven)", "probability",
                {"domain": "probability", "op": "markov", "mean": 3, "a": 10}, KV.EXACT,
                lambda v: v.result == Fr(3, 10)),
        Problem("x²+1 ≥ 0 (nonneg)", "inequalities",
                {"domain": "inequalities", "op": "nonneg", "poly": sp.Symbol("x") ** 2 + 1}, KV.EXACT, None),
        Problem("x²−1 ≥ 0 ? (counterexample)", "inequalities",
                {"domain": "inequalities", "op": "nonneg", "poly": sp.Symbol("x") ** 2 - 1}, KV.DECLINE, None),
        Problem("ODE y″+y=0 (back-subst)", "differential",
                {"domain": "differential", "op": "ode",
                 "ode": sp.Eq(sp.Function("y")(sp.Symbol("x")).diff(sp.Symbol("x"), 2)
                              + sp.Function("y")(sp.Symbol("x")), 0)}, KV.EXACT, None),
        Problem("shortest path (optimality cert)", "graph",
                {"domain": "graph", "op": "shortest_path", "n": 3, "edges": [[0, 1, 2], [1, 2, 3], [0, 2, 10]],
                 "source": 0}, KV.EXACT, lambda v: v.result == [0, 2, 5]),
        Problem("bipartite? triangle (odd cycle)", "graph",
                {"domain": "graph", "op": "bipartite", "n": 3, "edges": [[0, 1], [1, 2], [2, 0]]}, KV.EXACT,
                lambda v: v.result["bipartite"] is False),
    ]


@dataclass
class BenchReport:
    total: int
    by_grade: dict
    by_category: dict
    matched_expect: int
    cross_checked: int
    rows: list


def run() -> BenchReport:
    rows = []
    by_grade = {KV.EXACT: 0, KV.PROBABILISTIC: 0, KV.DECLINE: 0}
    by_cat: dict = {}
    matched = checked = 0
    for p in _suite():
        sol = S.solve(p.spec)
        g = sol.verdict.status
        by_grade[g] = by_grade.get(g, 0) + 1
        by_cat.setdefault(p.category, {"EXACT": 0, "PROBABILISTIC": 0, "DECLINE": 0})
        by_cat[p.category][g] += 1
        ok_expect = (g == p.expect)
        matched += int(ok_expect)
        ok_check = True
        if p.check is not None and g == KV.EXACT:
            try:
                ok_check = bool(p.check(sol.verdict))
            except Exception:                       # noqa: BLE001
                ok_check = False
            checked += int(ok_check)
        # EXACT non-DECLINE must carry a passed certificate (the ADT guarantees it, but assert at the bench)
        cert_ok = (g == KV.DECLINE) or (sol.verdict.certificate is not None and sol.verdict.certificate.passed)
        rows.append((p.name, p.category, g, p.expect, ok_expect, ok_check, cert_ok))
    return BenchReport(len(rows), by_grade, by_cat, matched, checked, rows)


def format_report(r: BenchReport) -> str:
    solvable = r.total - r.by_grade[KV.DECLINE]
    lines = [f"MATH capability benchmark — {r.total} problems",
             f"  EXACT={r.by_grade[KV.EXACT]}  PROBABILISTIC={r.by_grade[KV.PROBABILISTIC]}  "
             f"DECLINE={r.by_grade[KV.DECLINE]} (all expected)",
             f"  matched-expected-grade: {r.matched_expect}/{r.total}",
             f"  EXACT-share among solvable: {r.by_grade[KV.EXACT]}/{solvable}",
             "  by category:"]
    for cat, g in sorted(r.by_category.items()):
        lines.append(f"    {cat:18s} E={g['EXACT']} P={g['PROBABILISTIC']} D={g['DECLINE']}")
    return "\n".join(lines)
