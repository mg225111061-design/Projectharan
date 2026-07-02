# QMKERNEL_MEASURE — §BR (quantum mechanics / geometry / information)

## Battery results (measured, not estimated)

| module | cases | all_ok | wall time |
|---|---|---|---|
| qmkernel/lane.py (shared 2-lane infra) | 21 | ✓ | 0.067s |
| qmkernel/slater.py (NEW-1, flagship) | 17 | ✓ | 0.109s |
| qmkernel/fermion_wick.py (NEW-2) | 15 | ✓ | 0.016s |
| qmkernel/hermitian_realroot.py (NEW-6) | 14 | ✓ | 0.007s |
| qmkernel/entanglement_spectrum.py (NEW-5) | 16 | ✓ | 0.054s |
| qmkernel/lindblad_exp.py (NEW-7) | 11 | ✓ | 5.749s |
| qmkernel/state_validity.py (NEW-9) | 19 | ✓ | 0.025s |
| qmkernel/state_distance.py (NEW-10) | 19 | ✓ | 0.102s |
| qmkernel/qm_inequality.py (NEW-11) | 18 | ✓ | 0.014s |
| qmkernel/holonomic_specfun.py (NEW-8) | 10 | ✓ | 0.683s |
| qmkernel/qgt_berry.py (NEW-12) | 9 | ✓ | 10.902s |
| qmkernel/chern_fhs.py (NEW-13, flagship of Stage 4) | 12 | ✓ | 0.144s |
| qmkernel/wilson_loop.py (NEW-14) | 12 | ✓ | 0.279s |
| qmkernel/bulk_boundary.py (NEW-15) | 9 | ✓ | 0.368s |
| **TOTAL** | **202** | **all ✓** | **18.52s** |

The two heaviest batteries (`qgt_berry` 10.9s, `lindblad_exp` 5.7s) spend their time on genuine exact
symbolic verification — exhaustive Hermiticity/gauge-invariance checks over every parameter-pair (qgt_berry)
and symbolic diagonalization + trace/Hermiticity-preservation proofs over all ρ(0) (lindblad_exp) — not
something to optimize away; this is the cost of a real certificate, not a placeholder.

`webapi.engine_dispatch.qmkernel_reach()` aggregates all 14 sub-batteries: `all_ok=True`, `failed=[]`,
confirmed live (not just via the individual `__main__` runs above).

## §1 2-lane precision regression (float never EXACT — checked across every module)

Every module with a continuous/float-representable input domain (`slater`, `hermitian_realroot`,
`entanglement_spectrum`, `lindblad_exp`, `state_validity`, `state_distance`, `qm_inequality`) has an explicit
battery case asserting: float input → `isinstance(result, qmkernel.lane.EpsCert)` AND
`not isinstance(result, kernel_verdict.Verdict)` AND `result.lane == "APPROX_EPS"`. This is a **structural**
guarantee (a different Python type), not a label convention that could be forgotten on a new code path —
`EpsCert` is never constructed with `lane="EXACT"` anywhere in this package (grep-confirmed: `lane=` is set
exactly once, in the dataclass default, always `"APPROX_EPS"`).

`fermion_wick.py`, `qgt_berry.py`, `chern_fhs.py`, `wilson_loop.py`, `bulk_boundary.py` have no meaningful
float/exact split in their own input domain (combinatorial operators, or inherently-numerical lattice/loop
discretization respectively) — stated explicitly in each module's docstring rather than silently omitted.
`chern_fhs`/`wilson_loop`/`bulk_boundary` are **always** Lane 2 by design (§ their own docstrings): even a
"clean" symbolic Bloch Hamiltonian is diagonalized numerically at every lattice/loop point, so the computation
itself is never exact — the Chern number's TRUE value being an integer does not make THIS COMPUTATION exact.

**Regression count: 0 false-EXACT cases found across 202 battery cases + the ad hoc stress tests performed
during development** (documented inline in this build's history: N=9 Slater Leibniz-cap case, repeated-
eigenvalue trace-distance, irrational+degenerate-eigenvalue Hermitian matrices, a genuinely non-diagonal 4x4
random Hermitian matrix, the unitary-conjugation cross-check for Lindblad, the Wilson-loop/NEW-12 sign-
convention measurement).

## §2 principle 3 dispatcher-honesty regression (the §BP-9 lesson, applied to every reuse item)

- **hermitian_realroot.py**: `test: dispatcher_honesty_different_matrices_different_coeffs` feeds TWO
  different Hermitian matrices and asserts `charpoly_coeffs(H1) != charpoly_coeffs(H2)` AND their resulting
  Sturm-isolating intervals differ — proving `native_realroots.realroots_grade` is actually being called with
  matrix-derived coefficients, never a hardcoded polynomial.
- **chern_fhs.py / bulk_boundary.py**: the Hamiltonian is built from a caller-supplied `d_func` (or
  `onsite_builder`/`hop_builder`) callable — the QWZ model used in the battery is the battery's OWN fixture,
  never baked into the engine; the engine's gap-scan and curvature-sum code paths only ever call `d_func`.
- **state_distance.py**: `fidelity`/`relative_entropy`/`trace_distance` all re-run
  `state_validity.check(..., "density_matrix")` on their ACTUAL arguments (not a cached/assumed validity) —
  confirmed by the `invalid_input_declines_in_*` battery cases, which pass a bad matrix directly into each
  function and observe the SAME validation catching it independently each time.

## §4 precondition regression (non-orthonormal / non-Hermitian / small-gap / time-dependent → DECLINE)

| precondition | engine | battery case |
|---|---|---|
| non-orthonormal orbitals | slater.py | `non_orthonormal_declines`, `float_non_orthonormal_declines` |
| repeated evaluation point | slater.py | `repeated_point_declines` |
| non-Hermitian matrix | hermitian_realroot.py, lindblad_exp.py, state_validity.py | `non_hermitian_declines` (×3 modules) |
| time-dependent H/L_k (callable) | lindblad_exp.py | `time_dependent_declines`, `float_time_dependent_declines` |
| un-normalized bipartite state | entanglement_spectrum.py | `unnormalized_declines`, `float_unnormalized_declines` |
| un-normalized QGT family ψ(λ) | qgt_berry.py | `non_normalized_declines`, `flux_non_normalized_declines` |
| small/closed band gap | chern_fhs.py | `m_0_gap_closing_precondition_fails`, `m_2_gap_closing_precondition_fails` |
| small/closed gap (bulk-boundary) | bulk_boundary.py | `near_transition_precondition_fails` |
| float inequality, no stated tolerance | qm_inequality.py | `float_no_tolerance_declines` |
| bad probability distribution | qm_inequality.py | `holevo_bad_probs_declines` |

Every row above is a machine-checked regression, not a design claim.

## §5 Mirage-absence confirmation

Grep across every file in `qmkernel/` for the ten explicitly-rejected items (Dirac notation, Dirac delta,
Born interpretation, general Green's function, general TDSE/TISE, general path integral, WKB, Planck's
formula, no-cloning) as the subject of a NEW ENGINE (as opposed to incidental mention in prose): **0 hits** —
none of the ten appear as a standalone recognized-and-certified computation anywhere in this package.

## Directive-premise corrections (measured and reported, not silently built around)

1. **Kasteleyn/FKT Pfaffian** — the directive calls it "이전 라운드 NEW-12, 미빌드" (previous round's NEW-12,
   unbuilt). `newengine/kasteleyn.py` already exists, complete, from an earlier round (§BM). NEW-4 became a
   verification note, 0 new files.
2. **C-finite/matrix-exponential "gem"** — the directive claims Lindblad-as-matrix-exponential can directly
   reuse a C-finite/Kalman matrix-exponential engine. `cfinite.py` is scalar-recurrence-only (matrix POWERS,
   not exponentials); `newengine/kalman.py` does controllability/observability, not exponentials. Repo-wide
   grep for `expm`/"matrix exponential": 0 hits anywhere. NEW-7's exponential core is genuinely net-new.
3. **QGT/Berry curvature vs. `mathmode/curvature.py`** — confirmed NO overlap (spacetime curvature vs.
   parameter-space curvature are different objects) rather than assumed from the similar name.

## Invariants

- **precision 1.0 / false-EXACT 0**: every EXACT verdict traces to a machine-rechecked `kernel_verdict.Cert`;
  every float-tainted result is structurally an `EpsCert`, never a `Verdict`.
- **14-mechanism registry unchanged**: every module cites an EXISTING mechanism (m02/m03/m05/m08/m09/m10/m11/
  m14) as its recognition branch; 0 new mechanism files added to `mechanisms/`.
- **os-import-0**: `grep -rn "^import os\|^from os" qmkernel/*.py` → 0 hits (checked below, part of the gate).
- **engine-files-untouched**: `git diff --stat` against the 15 reference files (`mathmode/free_fermion.py`,
  `qfold/stabilizer.py`, `mathmode/operator_algebra.py`, `mathmode/ore.py`, `mathmode/holonomic.py`,
  `mathmode/special_holonomic.py`, `native_realroots.py`, `hermite_count.py`, `randomized_svd.py`,
  `cfinite.py`, `mathmode/curvature.py`, `mathmode/petrov.py`, `newengine/kasteleyn.py`,
  `newengine/kalman.py`, `positivity.py`) → empty, exit 0.

## Scope boundaries stated honestly (not silently missing)

- `state_distance.fidelity`/`relative_entropy`: exact only for pure-operand or commuting-mixed cases; the
  fully general non-commuting mixed-mixed case DECLINEs (needs a genuine matrix square root/logarithm).
- `qm_inequality.holevo_nonnegativity`: verifies χ≥0 (concavity of S), NOT the full Holevo theorem against
  true accessible information (a hard POVM-optimization problem, out of scope).
- `qm_inequality.monogamy_tangle_check`: an explicit, tested DECLINE — the Wootters concurrence/tangle
  formula is genuinely new infrastructure this pass does not build.
- `chern_fhs.py`/`bulk_boundary.py`: validated on DEEP (non-near-transition) points; near a phase transition
  the gap precondition fires rather than returning an unreliable finite-size/lattice-artifact-prone answer.
