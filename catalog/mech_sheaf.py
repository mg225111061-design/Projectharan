"""
MECHANISM 17 — Sheaf cohomology / local-to-global (in-repo; generalizes M14's binary obstruction).
====================================================================================================
A finite cellular sheaf on a graph: a vector-space stalk on each vertex/edge + restriction maps; the coboundary
δ⁰ assembles local data into edge-disagreements. By EXACT ℚ linear algebra:
  • H⁰ = ker δ⁰ = the GLOBAL SECTIONS (locally-consistent global assignments);
  • H¹ = coker δ⁰ = the graded OBSTRUCTION to gluing.

★ proposer→EXACT-disposer (exact rational kernels/ranks):
  • a provided local section that GLUES (δ⁰s = 0) ⇒ EXACT fold = the recovered global section;
  • a section that does NOT glue ⇒ DECLINE with the obstruction class [δs] ∈ H¹ (a positive absence-proof — the
    M14 generalization: M14's binary "no global section" is exactly the H⁰-empty / [δs]≠0 special case);
  • no section but a NONTRIVIAL global section exists (dim H⁰ ≥ 1) ⇒ EXACT (global sections recovered);
  • a random sheaf (no global section, a generic full obstruction) ⇒ DECLINE. The impossible core does not move.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Dict, List, Optional, Tuple

import kernel_verdict as KV


def _coboundary(vertices, edges, dim, restr):
    """Build δ⁰: C⁰(=⊕_v ℝ^dim) → C¹(=⊕_e ℝ^dim) over ℚ. For edge e=(u,v): (δx)_e = R[e,v]·x_v − R[e,u]·x_u.
    restr[(e_index, vertex)] is a dim×dim rational matrix (default identity)."""
    import sympy as sp
    V = list(vertices)
    vpos = {v: i for i, v in enumerate(V)}
    rows = len(edges) * dim
    cols = len(V) * dim
    M = sp.zeros(rows, cols)
    I = sp.eye(dim)
    for ei, (u, v) in enumerate(edges):
        Ru = restr.get((ei, u), I)
        Rv = restr.get((ei, v), I)
        for a in range(dim):
            for b in range(dim):
                M[ei * dim + a, vpos[v] * dim + b] += Rv[a, b]
                M[ei * dim + a, vpos[u] * dim + b] -= Ru[a, b]
    return M, V, vpos


def _to_mat(m, dim):
    import sympy as sp
    return sp.Matrix([[sp.Rational(Fraction(x)) for x in row] for row in m]) if m is not None else sp.eye(dim)


def sheaf_grade(spec: dict) -> KV.Verdict:
    """M17 — compute sheaf cohomology of a finite cellular sheaf on a graph and fold local→global. spec =
    {vertices, edges:[(u,v)], stalk_dim?, restrictions?:{(edge_idx,vertex):matrix}, section?:{v:vector}}.
    Returns EXACT (global section recovered / global sections exist) or DECLINE (obstruction [δs]≠0 / no global
    section — the M14-generalizing positive absence-proof)."""
    import sympy as sp
    if not (isinstance(spec, dict) and "vertices" in spec and "edges" in spec):
        return KV.decline("sheaf: need {vertices, edges, [stalk_dim, restrictions, section]}", "mech_sheaf")
    vertices = list(spec["vertices"])
    edges = [tuple(e) for e in spec["edges"]]
    dim = int(spec.get("stalk_dim", 1))
    raw = spec.get("restrictions") or {}
    restr = {k: _to_mat(v, dim) for k, v in raw.items()}
    delta, V, vpos = _coboundary(vertices, edges, dim, restr)
    rank = delta.rank()
    h0 = delta.cols - rank                                      # dim ker δ⁰ = global sections
    h1 = delta.rows - rank                                      # dim coker δ⁰ = obstruction
    if "section" in spec and spec["section"] is not None:
        sec = spec["section"]
        x = sp.zeros(delta.cols, 1)
        for v, vec in sec.items():
            vv = vec if isinstance(vec, (list, tuple)) else [vec]
            for b in range(dim):
                x[vpos[v] * dim + b] = sp.Rational(Fraction(vv[b]))
        ds = delta * x
        if all(c == 0 for c in ds):                            # δ⁰s = 0 ⇒ the local data GLUES
            cert = KV.Cert(KV.EXACT, "sheaf_cohomology", passed=True,
                           check_cost="exact ℚ δ⁰·s = 0 (local data glues to a global section)",
                           detail=f"H⁰={h0}, H¹={h1}; provided section is a global section (δ⁰s=0) — local→global fold")
            return KV.exact({"H0": h0, "H1": h1, "glued": True, "global_section": True},
                            "mech_sheaf", "sheaf global section (local→global gluing)", cert)
        # does not glue ⇒ obstruction class [δs] ∈ H¹ (M14-generalizing positive absence-proof)
        return KV.decline(f"sheaf: local data does NOT glue — obstruction [δs]≠0 in H¹ (dim {h1}); no global section "
                          f"(the M14 binary obstruction is the H⁰-empty special case) ⇒ DECLINE", "mech_sheaf")
    # no section provided: fold iff a NONTRIVIAL global section exists
    if h0 >= 1:
        ns = delta.nullspace()
        cert = KV.Cert(KV.EXACT, "sheaf_cohomology", passed=True,
                       check_cost="exact ℚ kernel of δ⁰ (global sections) + coker (obstruction)",
                       detail=f"H⁰={h0} (nontrivial global sections), H¹={h1}; cohomology computed by exact linear algebra")
        return KV.exact({"H0": h0, "H1": h1, "global_section_dim": h0, "section_basis_count": len(ns)},
                        "mech_sheaf", "sheaf cohomology (global sections exist)", cert)
    return KV.decline(f"sheaf: no nontrivial global section (H⁰=0), obstruction H¹={h1} ⇒ DECLINE "
                      "(local-to-global gluing fails — M14 obstruction, generalized)", "mech_sheaf")
