# QMKERNEL_INDEX — §BR §3 index (overlap confirmed BEFORE build; duplicate work = 0)

Every claim below was checked by reading the actual source (not assumed from the directive's own framing —
one claim in the directive's motivating text turned out to be wrong on inspection; see §7). Net-new work is
listed only where overlap is confirmed absent.

## 1. `mathmode/free_fermion.py` (free-fermion / matchgate)

Public API: `wick_pfaffian_fold(A)`, `is_wick_consistent(A, higher)`, `gaussian_evolve(Gamma,R,N)`,
`jw_is_quadratic(terms)`, `peschel_entropy(C, subsystem)`, `gaussian_cv_evolve(sigma,S,N)`, `matchgate_note()`,
`adversarial_battery()`. Internal exact-Fraction `det_Q`/`pfaffian_Q`/`pfaffian_combinatorial` helpers exist
but are scoped to **2-point correlator matrices**, not orbital matrices.

★ **No function accepts a Slater determinant (N orthonormal orbitals) as input.** Every entry point takes a
correlator matrix, a covariance matrix, or spin-Hamiltonian terms — never orbital vectors/indices. Repo-wide
`grep -i slater` across every `.py` file: **0 hits**. Confirmed genuinely net-new, not a duplicate.

**Wiring decision (NEW-3)**: qmkernel/slater.py will NOT import free_fermion's internal `det_Q` (that helper
is correlator-matrix-shaped, a different object than an orbital matrix — reusing it would conflate two
distinct mathematical objects that happen to both be "a determinant"). Instead NEW-3 wires at the *public API*
boundary: a Slater state's occupation/correlator data, once computed, is handed to `wick_pfaffian_fold`/
`peschel_entropy` unchanged — free_fermion.py itself is not touched, 0 diff.

## 2. `qfold/stabilizer.py` (Gottesman-Knill)

Public API is pure Clifford/Pauli/𝔽₂-symplectic. Grep for `jordan|wigner|fermion|majorana|anticommut`
(case-insensitive): **0 hits**. The directive's premise ("Jordan-Wigner 교집합 케이스 존재") describes a
*mathematical fact* (JW-transformed quadratic fermion Hamiltonians with the right structure ARE Clifford
circuits), not something this file implements. No JW-stabilizer bridge exists. This is **not** one of the
16 NEW items — noted here for honesty, not queued as a gap.

## 3. `mathmode/operator_algebra.py` (bosonic operator algebra)

Full read. `comm(A,B) = A·B−B·A` only. Grep for `anticommut|fermion|grassmann`: **0 hits**. `normal_order()`
implements Wick normal ordering (via the Ore-algebra canonical form) for the **bosonic** Heisenberg algebra —
no anticommutators, no sign-tracking on operator reorder, no fermionic type system anywhere in the file.
★ **Confirmed bosonic-only → NEW-2 (fermionic Wick/anticommutator extension) is genuinely net-new**, per the
directive's own conditional ("§3에서 bosonic만 확인되면 확장"). operator_algebra.py is not touched (0 diff);
NEW-2 is a new module, not an edit to this file.

## 4. `mathmode/ore.py` + `mathmode/holonomic.py` + `mathmode/special_holonomic.py` (holonomic/D-finite)

- `ore.py` (G1): abstract Ore-algebra ring, completely name-agnostic (no special-function lookup at all).
- `holonomic.py` (G2): generic D-finite closure (sum/product) via module-reduction + linear-dependence
  discovery. Also name-agnostic — discovers annihilators algorithmically, no lookup table.
- `special_holonomic.py` (P9): a **lookup-table registry** — `REGISTRY = {"legendre","hermite","laguerre",
  "chebyshev_t","bessel"}`, each a hardcoded annihilator (coeffs dict + sympy witness) with a genuine
  substitution certificate (`L(f) ≡ 0` verified symbolically, tested in `test_build.py:8517-8542`).

★ **Hermite is already registered** (`special_holonomic.py:36-37`) — needed for the QHO wavefunction family.
★ **Airy and confluent-hypergeometric/Kummer/Whittaker are NOT registered anywhere.** They appear ONLY as
negative markers (`kovacic.py`, `mathmode/decision_integration.py`'s `_NONLIOUVILLE` tuple) used to *reject*
false Liouvillian solutions — a completely different, negative use, not holonomic recognition.

**Wiring decision (NEW-8)**: for Hermite, `qmkernel/holonomic_specfun.py` is pure label-routing to
`mathmode.special_holonomic.register("hermite", n)` (0 new logic, per the directive's own instruction). For
Airy (tunneling) and confluent-hypergeometric (hydrogen radial), qmkernel builds its **own** small annihilator
registry inside `qmkernel/holonomic_specfun.py`, using the *same certificate pattern* (coeffs dict +
substitution check) — but does **not** edit `mathmode/special_holonomic.py`'s `REGISTRY` (keeps that
already-tested production file at 0 diff, same protective posture as §BQ's metakernel work). Reusing the
*pattern*, not the *file*, is the honest description.

## 5. Real-root separation (Sturm/Descartes) — `native_realroots.py`, `hermite_count.py`

`native_realroots.realroots_grade(coeffs)` takes **any** rational polynomial coefficient sequence (no
restriction to a particular matrix form) and returns a `KV.Verdict(EXACT)` with Sturm-isolated real-root
intervals as its certificate. Fully reusable as-is, zero adaptation needed.

**Wiring decision (NEW-6)**: `qmkernel/hermitian_realroot.py` will extract the characteristic polynomial of
the **actual input matrix** (via `sympy`'s exact `.charpoly()`, never a hardcoded polynomial — this is the
directive's §2 principle 3 "dispatcher honesty" check, verified by a regression test that feeds two different
matrices and asserts two different coefficient lists reach `realroots_grade`), then calls
`native_realroots.realroots_grade` unmodified.

## 6. `randomized_svd.py`

`randomized_svd()`/`approximate()` are **float-only** (numpy), graded via a *different* ADT
(`sublinear_layer.SublinearVerdict`, PROBABILISTIC with a concentration-bound δ) — there is no exact/rational
path. Confirmed by grep (`exact|Fraction|sympy|rational`: 0 hits).

**Wiring decision (NEW-5)**: rather than editing the already-wired production file `randomized_svd.py` (it is
a direct `_WIRED_ENTRIES` dispatcher target — editing it risks the existing wiring), the exact small-matrix
SVD path is a **new** function in `qmkernel/entanglement_spectrum.py` (via sympy exact eigendecomposition of
the Gram matrix, singular values = √eigenvalues when they land in exact rational/algebraic form). It composes
alongside (does not replace) `randomized_svd.approximate()`, which remains the Lane-2/float fallback.
`randomized_svd.py` stays at 0 diff.

## 7. `cfinite.py` + `newengine/kalman.py` — ★ directive premise checked and corrected

The directive's motivating text asserts Lindblad-as-matrix-exponential can "directly reuse the C-finite
engine — same structure as the Kalman/matrix-exponential gem." Verified by reading both files in full:
`cfinite.py` provides **scalar** C-finite recurrence evaluation (`companion_nth`: integer matrix powers by
repeated squaring) — no matrix exponential, no ODE solver. `newengine/kalman.py` provides controllability/
observability rank tests (`controllable`, `observable`) — also no matrix exponential. A repo-wide grep for
`expm|matrix_exp|scipy.linalg.expm|"matrix exponential"` returns **0 hits** anywhere in the repository.

★ **Correction, stated honestly rather than silently building on a false premise**: no matrix-exponential
engine exists anywhere in this repo today. NEW-7's matrix-exponential core is genuinely net-new. It borrows
only the *conceptual* kinship with `cfinite.py` (both turn a linear recurrence/ODE into a closed form via a
transfer matrix) — no code or file is reused, and this is stated as a design note in `qmkernel/lindblad_exp.py`
rather than an inflated reuse claim.

## 8. `mathmode/curvature.py` + `mathmode/petrov.py`

`curvature.py`: spacetime differential geometry only (metric → Christoffel → Riemann → Ricci → Kretschmann,
exact via sympy re-substitution). `petrov.py`: classifies the Weyl tensor's algebraic type from the 5
Newman-Penrose scalars (exact, via squarefree quartic-root partition). Grep for
`berry|parameter.*manifold|connection.*bundle`: **0 hits** in either file — neither has any notion of
curvature over an *abstract parameter space* (a connection on a vector bundle over a parameter manifold, as
opposed to curvature of physical spacetime).

★ **Confirmed no overlap → NEW-12 (QGT/Berry) is fully net-new.** The two modules share only the generic
"connection → curvature-2-form → invariant" *pattern*, which is standard differential geometry, not
repo-specific code — no file is touched, no code is imported from either.

## 9. `newengine/kasteleyn.py` — ★ a SECOND directive premise checked and corrected

NEW-4's brief calls Kasteleyn/FKT Pfaffian "이전 라운드 NEW-12(Kasteleyn, 미빌드)" (previous round's NEW-12,
*unbuilt*). Verified false by reading the file: `newengine/kasteleyn.py` is a complete, already-built,
already-tested engine (§BM NEW-12, an earlier round — task history confirms it), with its own precondition
(planarity/antisymmetry), certificate (`Pf(K)²=det(K)`, exact integers), and `adversarial_battery()`.

★ **Correction**: no new Kasteleyn build is needed. NEW-4 is a verification note, not a build item: this
module's two-way-determinant certificate (slater.py) and Kasteleyn's `Pf(K)²=det(K)` certificate are both
exact-certified determinant-family checks, but on genuinely different objects (an N×N orbital-value matrix vs.
a graph's Kasteleyn-oriented adjacency matrix) — forcing shared code between them would be an artificial
abstraction the task doesn't need, not a real simplification. 0 new files for NEW-4.

## Net-new table (what STAGE 1-4 actually builds)

| item | verdict | what it does |
|---|---|---|
| NEW-1 slater.py | **net-new** | orthonormality precondition + determinant/overlap cross-check certificate |
| NEW-2 fermion_wick.py | **net-new** (confirmed §3) | anticommutator + sign-tracked Wick contraction |
| NEW-3 free-fermion wiring | **routing only** | Slater→correlator handoff into free_fermion's public API |
| NEW-4 Kasteleyn shared infra | **premise corrected (§9)** | `newengine/kasteleyn.py` already exists and is complete (§BM NEW-12) — 0 new files; documented, not rebuilt |
| NEW-5 entanglement_spectrum.py | **net-new** exact path + **routing** to randomized_svd for float | Schmidt=SVD, reconstruction+orthonormality certificate |
| NEW-6 hermitian_realroot.py | **routing only** | extract real charpoly → `native_realroots.realroots_grade` |
| NEW-7 lindblad_exp.py | **net-new** (premise corrected §7) | vec(ρ) trick + matrix exponential, substitute-back certificate |
| NEW-8 holonomic_specfun.py | **hybrid**: routing (Hermite) + net-new (Airy, confluent-hypergeometric) | |
| NEW-9 state_validity.py | **net-new** | density-matrix/unitary/POVM/Kraus, one shape-dispatched engine |
| NEW-10 state_distance.py | **net-new**, consumes NEW-9 | fidelity/relative-entropy/trace-distance |
| NEW-11 qm_inequality.py | **net-new** | Robertson/variational/CHSH/Holevo/monogamy, one engine |
| NEW-12 qgt_berry.py | **net-new** (confirmed §8) | Berry connection/phase/curvature + Fubini-Study + QGT, one object |
| NEW-13 chern_fhs.py | **net-new** | FHS lattice Chern number, gap precondition, 2× resolution stability |
| NEW-14 Wilson loop | **net-new**, extends NEW-12 | path-ordered non-abelian holonomy |
| NEW-15 bulk_boundary.py | **net-new** | independent cross-check, not a new fold |
| NEW-16 dispatcher wiring | infra | `webapi/engine_dispatch.py` + `engine_inventory.py` |

## Shared infra decision: the 2-lane discipline (§1 of the directive)

The existing 3-grade ADT (`kernel_verdict.KV`: EXACT/PROBABILISTIC/DECLINE) is a **closed, structurally
enforced** set (`Verdict.__post_init__` raises `GradeViolation` on anything else) — every engine in the repo
that returns a `KV.Verdict` relies on that closure. The repo's own established practice for "checked-to-ε,
never sampled, never exact" results is to use a **separate, KV-adjacent type**, not to force a 4th grade into
KV: `disposition.Disposition(kind="APPROX_FOLD", ...)` (accel/foldaxes) and `sublinear_layer.SublinearVerdict`
(randomized_svd) are both existing precedents of exactly this pattern — "KV untouched" is stated explicitly in
`foldaxes/approx_fold.py:109`.

`qmkernel/lane.py` (new, shared by every Stage) follows the same precedent: Lane 1 (input carries no float
anywhere) returns a real `KV.Verdict(EXACT)`; Lane 2 (any float in the input) returns `EpsCert` — a distinct
dataclass that is **never** a `KV.Verdict`, so it cannot structurally be mistaken for EXACT or PROBABILISTIC
by any downstream consumer (stronger than a labeling convention: a type-level guarantee). DECLINE (precondition
failures) uses `KV.decline(...)` from either lane, since DECLINE carries no grade-specific payload either way.
