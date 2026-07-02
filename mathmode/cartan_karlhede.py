"""
UNIFIED ARSENAL §3 · P4 — Cartan–Karlhede equivalence: the SPI discriminator (rigorous NO-certificate).
======================================================================================================
Two spacetimes are LOCALLY EQUIVALENT iff their Cartan scalars (the canonicalised Riemann tensor + its covariant
derivatives, with the isotropy group, to ≤7 orders in 4D) match. The full algorithm is heavy; its cheap, RIGOROUS
half is the SCALAR POLYNOMIAL INVARIANT (SPI) pre-filter: a scalar curvature invariant is coordinate-INDEPENDENT,
so if any SPI differs in CHARACTER between two metrics, they are PROVABLY INEQUIVALENT — no frame search needed.

Here the SPIs are the Ricci scalar R and the Kretschmann scalar K = R_{abcd}R^{abcd} (from P2's curvature chain).
Compared in a coordinate-independent way: is the invariant identically zero? is it constant (no coordinate
dependence)? — both are geometric facts. A mismatch ⇒ INEQUIVALENT with the differing invariant as the witness.

CERTIFICATE: the differing SPI (NO-certificate, rigorous). HONEST SCOPE (§X): SPIs are NECESSARY not SUFFICIENT —
matching SPIs ⇒ "NOT DISTINGUISHED by these invariants", NOT proven equivalent; the full Cartan–Karlhede frame
canonicalisation (≤7 derivatives, isotropy) is flagged future. Fixture: Schwarzschild (K=48M²/r⁶, non-constant) vs
Minkowski (K=0) ⇒ INEQUIVALENT — the invariant the engine SEES.
"""
from __future__ import annotations

from typing import List

import sympy as sp

import kernel_verdict as KV
from mathmode import curvature as CV


def spi(metric: sp.Matrix, coords: List[sp.Symbol]) -> dict:
    """The scalar polynomial invariants used as the pre-filter: Ricci scalar R and Kretschmann K."""
    res = CV.analyze(metric, coords)
    return {"R": sp.simplify(res["ricci_scalar"]), "K": sp.simplify(res["kretschmann"]), "coords": set(coords)}


def _character(inv: sp.Expr, coords: set) -> str:
    """Coordinate-independent character of a scalar invariant: 'zero' / 'nonzero-constant' / 'non-constant'."""
    if sp.simplify(inv) == 0:
        return "zero"
    return "nonzero-constant" if not (inv.free_symbols & coords) else "non-constant"


def discriminate(spiA: dict, spiB: dict) -> KV.Verdict:
    """Compare two SPI sets. INEQUIVALENT (EXACT, with the witness invariant) if any invariant's coordinate-
    independent character differs; else 'NOT DISTINGUISHED' (honest — SPIs are necessary, not sufficient)."""
    witnesses = []
    for name in ("R", "K"):
        cA = _character(spiA[name], spiA["coords"])
        cB = _character(spiB[name], spiB["coords"])
        if cA != cB:
            witnesses.append((name, cA, cB))
    if witnesses:
        w = "; ".join(f"{n}: A is {a}, B is {b}" for n, a, b in witnesses)
        cert = KV.Cert(KV.EXACT, "spi_inequivalence", passed=True, check_cost="coordinate-independent SPI character",
                       detail=f"INEQUIVALENT — scalar invariant(s) differ in a coordinate-independent way: {w}")
        return KV.exact({"equivalent": False, "witnesses": witnesses}, "cartan_karlhede.discriminate",
                        "DECISION (SPI inequivalence — rigorous NO)", cert)
    cert = KV.Cert(KV.EXACT, "spi_not_distinguished", passed=True, check_cost="SPI character match",
                   detail="NOT DISTINGUISHED by {R, K}: the SPIs match in character — SPIs are NECESSARY not "
                          "SUFFICIENT; the full Cartan–Karlhede frame algorithm (≤7 derivatives, isotropy) is "
                          "needed to PROVE equivalence (flagged future) — no false 'equivalent' claimed")
    return KV.exact({"equivalent": None, "note": "not distinguished by SPIs (necessary-not-sufficient)"},
                    "cartan_karlhede.discriminate", "SPI pre-filter (inconclusive — honest)", cert)


def solve(problem: dict) -> KV.Verdict:
    """problem = {'op':'equivalence', 'A':{'metric':[[..]],'coords':[..]}, 'B':{...}}."""
    if problem.get("op") != "equivalence":
        return KV.decline(f"cartan_karlhede: unknown op {problem.get('op')!r} ⇒ DECLINE", "cartan_karlhede")
    A, B = problem["A"], problem["B"]
    sA = spi(sp.Matrix(A["metric"]), [sp.Symbol(c) for c in A["coords"]])
    sB = spi(sp.Matrix(B["metric"]), [sp.Symbol(c) for c in B["coords"]])
    return discriminate(sA, sB)
