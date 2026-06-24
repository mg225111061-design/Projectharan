"""§4.6-§4.7 — C-1 (QFT · general relativity · condensed matter) and C-2 (quantum chemistry · neuroscience ·
economics/finance · climate/geophysics)."""
from catalog.base import Transform as T, reg_many

_EXIST = "UNVERIFIED(existing impl; catalog-gate wiring pending)"
_NEW = "UNVERIFIED(registered; sound apply gated in a later PHASE)"

reg_many([
    # C-1
    T("C1.petrov", "C-1", "general-relativity", (9,), "finite-invariant", "weyl_classification",
      "spacetime Weyl tensor", "[이미 있음: mathmode/petrov]", "EXACT", _EXIST),
    T("C1.tensor_canon", "C-1", "physics", (2, 9), "normal-form", "canonical_tensor",
      "tensor expression (symmetry/Bianchi)", "[이미 있음: mathmode/tensor_canon]", "EXACT", _EXIST),
    T("C1.wigner_repr", "C-1", "physics", (1, -1), "finite-invariant", "irrep_decomposition",
      "symmetry-group action", "[이미 있음: mathmode/wigner]", "EXACT", _EXIST),
    T("C1.topological_insulator", "C-1", "condensed-matter", (1, 9), "finite-invariant", "chern_z2",
      "band structure", "Chern/Z₂ invariant", "EXACT", _NEW),
    T("C1.lax_integrable", "C-1", "physics", (5,), "closed-form", "lax_commutator",
      "1+1 integrable system", "Lax pair", "EXACT", _NEW),
    T("C1.entanglement_arealaw", "C-1", "qft", (14,), "cert-bound", "arealaw_compressibility",
      "quantum state (area-law; volume-law=DECLINE)", "boundary-only", "DECISION", _NEW),
    # C-2
    T("C2.coupled_cluster", "C-2", "quantum-chemistry", (13, 2), "cert-bound", "size_extensive",
      "electron correlation", "PySCF/ORCA CCSD(T)", "PROBABILISTIC", _NEW),
    T("C2.hohenberg_kohn", "C-2", "quantum-chemistry", (9,), "finite-invariant", "density_functional",
      "electron system", "PySCF (exact functional unknown — limit stated)", "DECISION", _NEW),
    T("C2.transition_state_hessian", "C-2", "quantum-chemistry", (9, 3), "finite-invariant", "saddle_index",
      "potential energy surface", "Hessian-index certification", "EXACT", _NEW),
    T("C2.neural_manifold", "C-2", "neuroscience", (11,), "latent-state", "latent_residual",
      "neural population activity", "LFADS/CEBRA", "PROBABILISTIC", _NEW),
    T("C2.grid_cells", "C-2", "neuroscience", (9,), "finite-invariant", "representation_geometry",
      "neural code", "efficient-coding geometry", "PROBABILISTIC", _NEW),
    T("C2.ftap_noarbitrage", "C-2", "finance", (14, 4), "decision", "martingale_measure",
      "market", "QuantLib (no-arbitrage ⟺ martingale measure)", "DECISION", _NEW),
    T("C2.bellman_hjb", "C-2", "control", (13,), "closed-form", "value_function",
      "optimal control / MDP", "Bellman/HJB", "EXACT", _NEW),
    T("C2.arrow_debreu_ppad", "C-2", "economics", (14,), "obstruction", "ppad_boundary",
      "market / game equilibrium", "Arrow–Debreu existence (non-constructive) / PPAD-hard", "DECLINE", _NEW),
    T("C2.cointegration_johansen", "C-2", "econometrics", (9, 11), "finite-invariant", "cointegration_rank",
      "multivariate time series", "statsmodels Johansen", "PROBABILISTIC", _NEW),
    T("C2.enkf_assimilation", "C-2", "geophysics", (11,), "latent-state", "covariance_estimate",
      "dynamics + observations", "DART EnKF", "PROBABILISTIC", _NEW),
    T("C2.tipping_early_warning", "C-2", "climate", (11,), "cert-bound", "critical_slowing_down",
      "time series approaching bifurcation", "lag-1 autocorrelation / variance", "PROBABILISTIC", _NEW),
    T("C2.lorenz_lyapunov", "C-2", "chaos", (14,), "obstruction", "lyapunov_horizon",
      "chaotic system", "Lyapunov-time predictability bound", "DECLINE", _NEW),
])
