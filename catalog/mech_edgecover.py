"""
POST-CONSOLIDATION PHASE 2b — EDGE-COVER JOIN DECOMPOSITION (the AGM / fractional-edge-cover bound).
================================================================================================================
A natural-join query is a HYPERGRAPH: attributes = vertices, relations = hyperedges. A FRACTIONAL EDGE COVER assigns
x_e ≥ 0 to each relation so that every attribute is covered (Σ_{e∋v} x_e ≥ 1); ρ* = min Σ x_e is the fractional
edge-cover number. The AGM bound (Atserias–Grohe–Marx) is then |⋈| ≤ ∏_e |R_e|^{x_e} — a PROVABLE upper bound on the
join output size (the triangle query gives ρ*=3/2 ⇒ |⋈| ≤ N^{3/2}). The fold: query → ρ* + the AGM size bound,
certified by the LP-optimal cover.

★ THE HONEST ADJUDICATION (admit M24 only if z3-closed AND not plain AGM/M10 — adjudicated BY BUILDING):
  gate 2 (z3-closed): ✓ — ρ* is a z3 LRA / LP-optimum; the cover's feasibility (Σ_{e∋v} x_e ≥ 1) is re-checked over ℚ.
  gate 4 (dependency-free): ✓ — z3.Optimize (heavy, lazy); no external DB/optimizer.
  gate 1 (DISTINCT IN KIND): ✗ — this is EXACTLY plain AGM, and the AGM bound is a SIZE BOUND FORCED BY THE
      STRUCTURE (the join cannot exceed it) — M10's kind ("guaranteed-by-size": Erdős–Szekeres / Ramsey / pigeonhole
      forcing). Its derivation is LP duality on the fractional cover — the convex-duality lineage of M4 (the Legendre/
      rate-distortion faces). It emits NO new certificate kind. ⇒ DEMOTE: a FACE of M10 (parent mechanism 10), M4
      LP-duality lineage. NOT a new mechanism (no count++); M24 is NOT admitted.

A query with an UNCOVERABLE attribute (in no relation) ⇒ the join is unbounded ⇒ the LP is infeasible ⇒ DECLINE
(never a false finite bound). Precision 1.0.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Dict, List, Optional, Tuple

import kernel_verdict as KV

PARENT_MECHANISM = 10   # a structure-forced size bound — M10's kind (M4 LP-duality lineage)


def fractional_edge_cover(vertices: List[str], edges: Dict[str, set]
                          ) -> Optional[Tuple[Fraction, Dict[str, Fraction]]]:
    """Solve the LP: minimize Σ x_e s.t. Σ_{e∋v} x_e ≥ 1 ∀v, x_e ≥ 0, via z3.Optimize (LRA). Returns (ρ*, cover) or
    None (infeasible — an uncoverable attribute / z3 absent)."""
    try:
        import z3
    except Exception:  # noqa: BLE001
        return None
    opt = z3.Optimize()
    xe = {e: z3.Real(f"x_{e}") for e in edges}
    for e in edges:
        opt.add(xe[e] >= 0)
    for v in vertices:
        covering = [xe[e] for e in edges if v in edges[e]]
        if not covering:
            return None                                          # an attribute in no relation ⇒ infeasible
        opt.add(z3.Sum(covering) >= 1)
    h = opt.minimize(z3.Sum(list(xe.values())))
    if opt.check() != z3.sat:
        return None
    m = opt.model()

    def frac(rv):
        v = m[rv]
        return Fraction(int(v.numerator_as_long()), int(v.denominator_as_long())) if v is not None else Fraction(0)
    cover = {e: frac(xe[e]) for e in edges}
    rho = sum(cover.values())
    return rho, cover


def edgecover_grade(spec: dict) -> KV.Verdict:
    """Compute the fractional edge-cover number ρ* and the AGM join-size bound for a join query. spec = {vertices,
    edges:{rel: [attrs]}, sizes?:{rel: N}}. EXACT iff a feasible fractional cover exists (re-checked over ℚ); an
    uncoverable attribute (unbounded join) ⇒ DECLINE. DEMOTES to a FACE of M10 (forced size bound, M4 LP-duality)."""
    if not (isinstance(spec, dict) and "vertices" in spec and "edges" in spec):
        return KV.decline("edgecover: need {vertices, edges:{rel:[attrs]}[, sizes]}", "mech_edgecover")
    vertices = list(spec["vertices"])
    edges = {e: set(attrs) for e, attrs in spec["edges"].items()}
    sizes = {e: int(spec.get("sizes", {}).get(e, 0)) for e in edges}
    res = fractional_edge_cover(vertices, edges)
    if res is None:
        return KV.decline("edgecover: no fractional edge cover (an attribute lies in NO relation ⇒ the join is "
                          "UNBOUNDED) ⇒ DECLINE (never a false finite bound)", "mech_edgecover")
    rho, cover = res
    # ★ EXACT disposer over ℚ: the cover is feasible — every attribute is covered to ≥ 1 ★
    for v in vertices:
        if sum(cover[e] for e in edges if v in edges[e]) < 1:
            return KV.decline("edgecover: cover re-check failed (an attribute under-covered) ⇒ DECLINE", "mech_edgecover")
    agm = None
    if all(sizes[e] > 0 for e in edges):
        agm = 1.0
        for e in edges:
            agm *= float(sizes[e]) ** float(cover[e])
    uniform_bound = f"N^{rho}" if rho.denominator != 1 else f"N^{rho.numerator}"
    cert = KV.Cert(KV.EXACT, "fractional_edge_cover", passed=True,
                   check_cost=f"z3 LRA LP-optimum ρ*={rho} + ℚ feasibility re-check (every attribute covered ≥ 1)",
                   detail=f"fractional edge-cover number ρ*={rho}; AGM bound |⋈| ≤ ∏|R_e|^{{x_e}}"
                          + (f" = {agm:.4g}" if agm is not None else f" (≤ {uniform_bound} for equal sizes N)")
                          + " — a structure-FORCED size bound (FACE of M10; LP-duality lineage of M4)")
    return KV.exact({"parent_mechanism": PARENT_MECHANISM, "face": "edge_cover", "rho_star": str(rho),
                     "cover": {e: str(c) for e, c in cover.items()}, "agm_bound": agm,
                     "uniform_bound": uniform_bound}, "mech_edgecover",
                    f"AGM edge-cover bound (ρ*={rho}) → M10 face", cert)


def adjudication() -> dict:
    """Honest gate-by-gate: z3-closed ✓, dependency-free ✓, but it IS plain AGM and the AGM bound is a structure-
    forced size bound (M10's kind, M4 LP-duality lineage) ⇒ DEMOTE to a FACE of M10; M24 NOT admitted."""
    return {"candidate": "edge-cover join decomposition (AGM)", "z3_closed": True, "dependency_free": True,
            "not_plain_agm": False, "distinct_in_kind": False, "verdict": "DEMOTE → FACE of M10 (M24 not admitted)",
            "reason": "this is plain AGM; the bound is a SIZE BOUND FORCED BY STRUCTURE (the join cannot exceed ∏|R_e|"
                      "^{x_e}) — M10's 'guaranteed-by-size' kind, derived by LP duality (M4's convex-duality lineage); "
                      "no new certificate kind ⇒ a FACE of M10, not a new mechanism"}
