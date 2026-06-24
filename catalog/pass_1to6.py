"""§4.1 — passes 1-6: the broad terrain (analysis/algebra/topology/physics/engineering/learning/combinatorics/
information). [이미 있음: module] = already in the repo — reinforce + register only, never reimplement (§1.2)."""
from catalog.base import Transform as T, reg_many

_EXIST = "UNVERIFIED(existing impl; catalog-gate wiring pending)"
_NEW = "UNVERIFIED(registered; sound apply gated in a later PHASE)"

reg_many([
    T("16.faulhaber", "1-6", "analysis", (13, 2), "closed-form", "coeff_zero",
      "Σ k^p with polynomial summand", "[이미 있음: closure_classifier, mathmode/telescoping]", "EXACT", _EXIST),
    T("16.gosper", "1-6", "analysis", (2, 14), "decision", "telescoping_cert",
      "hypergeometric term ratio rational", "[이미 있음: closure_classifier, mathmode/ore]", "DECISION", _EXIST),
    T("16.zeilberger", "1-6", "analysis", (2, 13), "closed-form", "creative_telescoping",
      "parametric sum", "[이미 있음: mathmode/holonomic, mathmode/ore]", "EXACT", _EXIST),
    T("16.cfinite", "1-6", "analysis", (1, 13), "closed-form", "companion_replay",
      "linear recurrence", "[이미 있음: cfinite, mathmode/holonomic]", "EXACT", _EXIST),
    T("16.bostan_mori", "1-6", "analysis", (2, 13), "closed-form", "coeff_extract",
      "rational/algebraic generating function", "[이미 있음: newton_series]", "EXACT", _EXIST),
    T("16.chain_of_recurrences", "1-6", "compilers", (13,), "closed-form", "cr_normal_form",
      "polynomial/exponential loop", "[이미 있음: loop_recurrence]", "EXACT", _EXIST),
    T("16.spectral_svd_pca", "1-6", "linear-algebra", (1,), "finite-invariant", "eigendecomp_residual",
      "symmetric/normal matrix", "mathmode/linear_algebra", "EXACT", _NEW),
    T("16.galois_solvability", "1-6", "algebra", (14,), "obstruction", "galois_radical",
      "polynomial equation degree≥5", "[이미 있음: closure_classifier galois-radical]", "DECLINE", _EXIST),
    T("16.liouville_integration", "1-6", "analysis", (14,), "obstruction", "liouville_elementary",
      "indefinite integral (erf-like)", "[이미 있음: closure_classifier liouville-elementary]", "DECLINE", _EXIST),
    T("16.buckingham_pi", "1-6", "physics", (9, -1), "finite-invariant", "nullspace_basis",
      "physical quantities with dimensions", "[이미 있음: mathmode/buckingham]", "EXACT", _EXIST),
    T("16.noether", "1-6", "physics", (5,), "closed-form", "noether_dIdt",
      "Lagrangian with continuous symmetry", "[이미 있음: mathmode/lagrangian]", "EXACT", _EXIST),
    T("16.legendre_transform", "1-6", "physics", (0,), "normal-form", "biconjugate_identity",
      "convex potential (mechanics/thermo)", "mathmode/transforms", "EXACT", _NEW),
    T("16.rg_fixpoint", "1-6", "physics", (6,), "finite-invariant", "fixpoint_inductive",
      "scale-invariant flow", "mathmode/transforms_symdyn", "EXACT", _NEW),
    T("16.vc_pac_bound", "1-6", "learning", (10, 12), "cert-bound", "vc_sample_complexity",
      "hypothesis class", "PAC/VC", "PROBABILISTIC", _NEW),
    T("16.szemeredi_regularity", "1-6", "combinatorics", (7,), "normal-form", "regularity_partition",
      "large dense graph", "Szemerédi regularity", "DECISION", _NEW),
    T("16.shannon_huffman_arith", "1-6", "information", (12,), "code-length", "mdl_two_part",
      "symbol distribution", "[이미 있음: kernels_io]", "EXACT", _EXIST),
])
