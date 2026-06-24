"""§4.4-§4.5 — B-1 (computational geometry · optimization · numerical analysis) and B-2 (graph theory ·
automata/formal languages · program analysis)."""
from catalog.base import Transform as T, reg_many

_EXIST = "UNVERIFIED(existing impl; catalog-gate wiring pending)"
_NEW = "UNVERIFIED(registered; sound apply gated in a later PHASE)"

reg_many([
    # B-1
    T("B1.delaunay_hull", "B-1", "comp-geometry", (9, 2), "finite-invariant", "empty_circumcircle",
      "point set", "CGAL", "EXACT", _NEW),
    T("B1.conic_dual_farkas", "B-1", "optimization", (4,), "obstruction", "farkas_dual",
      "LP/SOCP/SDP infeasibility", "MOSEK/Clarabel [mathmode/optimization]", "EXACT", _NEW),
    T("B1.hodge_helmholtz", "B-1", "comp-geometry", (1,), "finite-invariant", "orthogonal_decomp",
      "vector field on mesh", "PyDEC/libDDG", "EXACT", _NEW),
    T("B1.multigrid_amg", "B-1", "numerics", (6,), "cert-bound", "contraction_bound",
      "elliptic PDE", "hypre/AMGCL", "PROBABILISTIC", _NEW),
    T("B1.matroid_submodular", "B-1", "optimization", (13, 4), "decision", "greedy_optimality",
      "independence system / submodular f", "matroid greedy / SFM", "EXACT", _NEW),
    T("B1.fem_aposteriori", "B-1", "numerics", (4,), "cert-bound", "residual_bound",
      "variational problem", "deal.II/FEniCS", "PROBABILISTIC", _NEW),
    T("B1.sos_positivstellensatz", "B-1", "optimization", (4,), "cert-bound", "sos_decomposition",
      "polynomial inequality / real infeasibility", "SOSTOOLS/SumOfSquares.jl/MOSEK (★ new EXACT tier, §8)",
      "EXACT", _NEW),
    # B-2
    T("B2.robertson_seymour", "B-2", "graph-theory", (10, 14), "obstruction", "forbidden_minors",
      "minor-closed property", "RS minor theory (NON-CONSTRUCTIVE — stated)", "DECISION", _NEW),
    T("B2.modular_decomposition", "B-2", "graph-theory", (9,), "finite-invariant", "modular_tree",
      "graph", "modular decomposition / planarity", "EXACT", _NEW),
    T("B2.courcelle", "B-2", "automata", (2, 3), "decision", "tree_automaton",
      "bounded-treewidth graph + MSO", "[일부: pillar3/complexity]", "DECISION", _EXIST),
    T("B2.syntactic_monoid", "B-2", "formal-languages", (9,), "finite-invariant", "syntactic_monoid",
      "regular language (star-free?)", "Schützenberger", "EXACT", _NEW),
    T("B2.abstract_interpretation", "B-2", "program-analysis", (6, 13), "finite-invariant", "fixpoint_inductive",
      "dataflow", "[이미 있음: pillar3/*, taint_ifds]", "EXACT", _EXIST),
    T("B2.separation_logic", "B-2", "program-analysis", (13,), "decision", "frame_inference",
      "heap program", "[이미 있음: incorrectness, pillar3/effects]", "DECISION", _EXIST),
    T("B2.ranking_termination", "B-2", "program-analysis", (14,), "ordinal-rank", "ranking_function",
      "loop", "[이미 있음: pillar3/termination, measure_synth, ordinal]", "EXACT", _EXIST),
    T("B2.ic3_pdr", "B-2", "model-checking", (3, 13), "finite-invariant", "inductive_invariant",
      "transition system", "[이미 있음: ic3_pdr, pillar3/kinduction]", "EXACT", _EXIST),
    T("B2.polyhedral", "B-2", "compilers", (2,), "normal-form", "affine_normal_form",
      "affine loop nest", "[이미 있음: polyhedral_opt, pillar3/affine]", "EXACT", _EXIST),
])
