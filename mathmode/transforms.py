"""
UNIFIED ARSENAL §4 — the TRANSFORM SYSTEM router (the outer layer that ties §1–§3 together).
=============================================================================================
Given any object, RECOGNIZE the structure already present, choose a TRANSFORM that re-expresses it into a form
§1 (foundations) / §2 (decision procedures) / §3 (physics) can close, dispatch, check the certificate → EXACT;
else a PROVEN DECLINE naming the obstruction. The router is DETERMINISTIC — it changes only the PATH, never a grade.

Transform categories wired here (each reuses a verified closer + co-generated certificate):
  • T-algebraic-differential  integral → Risch decision (elementary or proven non-elementary); sum → Gosper fold.
  • T-symbolic-dynamics       chaos → subshift integer matrix → entropy/ζ (EXACT).
  • T-number-system           modular→rational; real→algebraic (PSLQ, verified); series→rational GF (BM).
  • T-structure+randomness    fold the C-finite part; PROVE the rest has no short linear recurrence (no prediction).
  • T-physics                 tensor→Butler–Portugal; Weyl scalars→Petrov; metric-pair→Cartan–Karlhede SPI;
                              quantities→Buckingham-Pi; Weyl quartic → §3.

We report a MEASURED coverage rate on a structured corpus — NEVER a fake 100%; objects with provably no closed
form / no structure get a proven DECLINE (the moat). §X honesty applies throughout (rigorous spectral variants
only; PSLQ EXACT only if symbolically verified; randomness ⇒ exact stats + proven irreducibility, no rule).
"""
from __future__ import annotations

from typing import Tuple

import sympy as sp

import kernel_verdict as KV


def route(obj: dict) -> Tuple[str, KV.Verdict]:
    """Classify `obj` → (transform_name, verdict). A proven DECLINE names the obstruction when nothing closes it."""
    typ = obj.get("type")
    if typ == "integral":
        from mathmode import decision_integration as DI
        x = sp.Symbol(obj.get("var", "x"))
        return "T-algebraic-differential", DI.risch_elementary(obj["f"], x)
    if typ == "sum":
        from mathmode import combinatorics as CB
        return "T-algebraic-differential", CB.gosper_indefinite(obj["summand"])
    if typ == "subshift":
        from mathmode import transforms_symdyn as SD
        return "T-symbolic-dynamics", SD.subshift(obj["A"])
    if typ == "modular":
        from mathmode import transforms_number as TN
        return "T-number-system", TN.modular_to_rational(obj["r"], obj["m"])
    if typ == "constant":
        from mathmode import transforms_number as TN
        return "T-number-system", TN.recognize_algebraic(obj["value"])
    if typ == "series":
        from mathmode import transforms_number as TN
        return "T-number-system", TN.series_to_rational(obj["terms"])
    if typ == "sequence":
        from mathmode import transforms_random as TR
        return "T-structure+randomness", TR.decompose(obj["terms"])
    if typ == "petrov":
        from mathmode import petrov as PV
        return "T-physics", PV.classify(obj["psi"])
    if typ == "buckingham":
        from mathmode import buckingham as BP
        return "T-physics", BP.buckingham_pi(obj["quantities"])
    if typ == "tensor":
        from mathmode import tensor_canon as TC
        return "T-physics", TC.canonicalize(tuple(obj["indices"]), obj["gens"], obj.get("dummies", []))
    return "none", KV.decline(f"transform-router: no transform matches type {typ!r} ⇒ DECLINE "
                              f"(obstruction: unrecognized object class — not a fabricated route)", "transforms")


# ── a STRUCTURED corpus (objects that DO have structure) + adversarial DECLINE cases ─────────────────────────
def corpus() -> list:
    return [
        ("golden-mean shift", {"type": "subshift", "A": [[1, 1], [1, 0]]}, KV.EXACT),
        ("full 2-shift", {"type": "subshift", "A": [[1, 1], [1, 1]]}, KV.EXACT),
        ("modular 3/7", {"type": "modular", "r": (3 * pow(7, -1, 10 ** 9 + 7)) % (10 ** 9 + 7), "m": 10 ** 9 + 7}, KV.EXACT),
        ("golden ratio", {"type": "constant", "value": (1 + sp.sqrt(5)) / 2}, KV.EXACT),
        ("√2", {"type": "constant", "value": sp.sqrt(2)}, KV.EXACT),
        ("Fibonacci GF", {"type": "series", "terms": [1, 1, 2, 3, 5, 8, 13, 21]}, KV.EXACT),
        ("Fibonacci seq", {"type": "sequence", "terms": [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]}, KV.EXACT),
        ("primes (incompressible)", {"type": "sequence", "terms": [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]}, KV.EXACT),
        ("∫2x·e^{x²} (elementary)", {"type": "integral", "f": "2*x*exp(x**2)"}, KV.EXACT),
        ("Σ k (Gosper)", {"type": "sum", "summand": "k"}, KV.EXACT),
        ("Schwarzschild Petrov", {"type": "petrov", "psi": [0, 0, -sp.Symbol("M") / sp.Symbol("r") ** 3, 0, 0]}, KV.EXACT),
        ("pipe-flow Buckingham", {"type": "buckingham", "quantities": {
            "rho": {"M": 1, "L": -3}, "V": {"L": 1, "T": -1}, "D": {"L": 1},
            "mu": {"M": 1, "L": -1, "T": -1}, "dp": {"M": 1, "L": -1, "T": -2}}}, KV.EXACT),
        ("Riemann tensor canon", {"type": "tensor", "indices": ["d", "c", "b", "a"],
                                  "gens": [([1, 0, 2, 3], -1), ([0, 1, 3, 2], -1), ([2, 3, 0, 1], 1)]}, KV.EXACT),
        # honest DECLINEs (proven non-elementary / unrecognized) — these SHOULD NOT close
        ("∫e^{x²} (non-elementary)", {"type": "integral", "f": "exp(x**2)"}, KV.DECLINE),
        ("unrecognized object", {"type": "mystery_blob"}, KV.DECLINE),
    ]


def measure_coverage() -> dict:
    """Run the router over the structured corpus and report the MEASURED outcome distribution (no fake 100%)."""
    rows = []
    exact = prob = decline = matched = 0
    for name, obj, expected in corpus():
        tname, v = route(obj)
        ok = (v.status == expected)
        rows.append({"name": name, "transform": tname, "status": v.status, "expected": expected, "as_expected": ok})
        matched += int(ok)
        exact += int(v.status == KV.EXACT)
        prob += int(v.status == KV.PROBABILISTIC)
        decline += int(v.status == KV.DECLINE)
    n = len(rows)
    structured = [r for r in rows if r["expected"] != KV.DECLINE]
    closed = sum(1 for r in structured if r["status"] in (KV.EXACT, KV.PROBABILISTIC))
    return {"n": n, "exact": exact, "probabilistic": prob, "decline": decline, "as_expected": matched,
            "structured_corpus": len(structured), "structured_closed": closed,
            "structured_coverage_pct": round(100 * closed / len(structured), 1) if structured else 0.0,
            "rows": rows}


def solve(problem: dict) -> KV.Verdict:
    """problem = the object dict (with 'type'); returns the routed verdict."""
    _, v = route(problem)
    return v
