"""§4.2-§4.3 — A-1 (diff/Riemann geometry · algebraic geometry · analytic number theory · harmonic analysis)
and A-2 (probability · operator algebras · combinatorics depth)."""
from catalog.base import Transform as T, reg_many

_EXIST = "UNVERIFIED(existing impl; catalog-gate wiring pending)"
_NEW = "UNVERIFIED(registered; sound apply gated in a later PHASE)"

reg_many([
    # A-1
    T("A1.hecke_eigenform", "A-1", "automorphic-forms", (1,), "finite-invariant", "sturm_bound",
      "modular-form space", "Sage/Pari/Magma modular symbols", "EXACT", _NEW),
    T("A1.cartan_karlhede", "A-1", "riemann-geometry", (9,), "finite-invariant", "complete_invariant",
      "Riemannian curvature", "[이미 있음: mathmode/cartan_karlhede, mathmode/curvature]", "EXACT", _EXIST),
    T("A1.sheaf_cohomology_bgg", "A-1", "algebraic-geometry", (2, 9), "finite-invariant", "free_resolution",
      "projective variety", "Macaulay2", "EXACT", _NEW),
    T("A1.riemann_roch", "A-1", "algebraic-geometry", (2,), "finite-invariant", "function_space_dim",
      "algebraic curve", "Magma/Singular", "EXACT", _NEW),
    T("A1.elliptic_descent", "A-1", "number-theory", (3, 14), "finite-invariant", "descent_conditional",
      "elliptic curve rank", "Sage/Magma (conditional GRH/BSD — cert propagates the hypothesis)", "DECISION", _NEW),
    T("A1.circle_method", "A-1", "analytic-number-theory", (7,), "cert-bound", "arc_bound",
      "arithmetic sum / prime counting", "explicit-formula / major-minor arcs (bound-only)", "PROBABILISTIC", _NEW),
    T("A1.zeta_zero_verification", "A-1", "analytic-number-theory", (3,), "cert-bound", "interval_enclosure",
      "ζ(s) zeros", "Arb [이미 있음: mathmode/certified_numeric]", "EXACT", _EXIST),
    # A-2
    T("A2.large_deviations", "A-2", "probability", (0, 12), "closed-form", "convex_conjugate",
      "sum / empirical distribution", "Cramér/Sanov [mathmode/probability]", "EXACT", _NEW),
    T("A2.concentration", "A-2", "probability", (10,), "cert-bound", "mcdiarmid_talagrand",
      "Lipschitz function of independents", "[mathmode/inequalities]", "PROBABILISTIC", _NEW),
    T("A2.free_probability_r", "A-2", "operator-algebras", (1, 0), "closed-form", "r_transform",
      "large random matrix spectrum", "[mathmode/operator_algebra]", "EXACT", _NEW),
    T("A2.von_neumann_type", "A-2", "operator-algebras", (9,), "finite-invariant", "type_classification",
      "operator algebra type I/II/III", "[이미 있음: mathmode/operator_algebra]", "EXACT", _EXIST),
    T("A2.markov_basis", "A-2", "algebraic-statistics", (2,), "normal-form", "move_set",
      "contingency table", "4ti2", "EXACT", _NEW),
    T("A2.species_exponential", "A-2", "combinatorics", (13,), "closed-form", "exponential_formula",
      "combinatorial species", "[mathmode/combinatorics]", "EXACT", _NEW),
])
