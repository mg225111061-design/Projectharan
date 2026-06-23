# STATUS — MR.JEFFREY / HARAN  (single source of truth)

*This is the ONE document that states what is true NOW. Autonomous builds update THIS file rather than spawning a
new top-level report. Historical campaign reports live in `reports/archive/`. Every number here is reproduced by
`test_build.py` — if a number drifts, the build is wrong, not this file. Last verified: fresh suite run below.*

## Current state (measured)
| | |
|---|---|
| Repo / branch | `mg225111061-design/Projectharan` · **`claude/charming-brahmagupta-q4wwgh`** |
| Tests | **205 passed / 205** — `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 test_build.py` |
| Top-level modes | **CODE** (verified whole-program optimizer, OMEGA) + **MATH** (MATH-Ascent) — UI toggle, `data-top` |
| MATH arsenal | **17 families** + central `fold` + O(1) `broth` (3,772 entries) |
| Served app | Docker → `server:app` serves `mrjeffrey.html` at `/`; `/api/optimize`, `/api/math/solve`, `/api/math/ingest` |
| Now building | NATIVE-CORE directive (§0.5 cleanup → §1 Rust core → §2 zero-dep SMT → §3 triage → §4 routing → §5 deps→0) |

## Grades (the ADT, enforced at construction — `kernel_verdict.py`)
- **EXACT** — machine-checked certificate / decision procedure / exhaustive-bounded domain (bound stated).
- **PROBABILISTIC(ε,δ)** — approximation/randomized; δ stated; never EXACT even at δ≤10⁻¹⁸.
- **DECLINE** — irreducible / undecidable / no closed form / unstructured. Dignified, proven, never a fabrication.
- A wrong "EXACT" is a correctness bug; the adversarial battery injects fake-EXACT / rubber-stamp / grade-mismatch and the ADT rejects every one (`test_moat_battery`, `test_*_dogfood`).

## CODE mode (pillar3 / webapi / server)
- OMEGA Rounds 1–3 fully dispositioned (90/90). EXACT-share ≈ **68%** of graded capabilities (`exact_share.py`).
- Recognizers + verified lifting + e-graph + superopt + sound static analyses; fast/normal/extend mode separation.

## MATH mode (`mathmode/`, 22 modules)
- Center: **`fold`** — recognize structure → closed form + co-generated certificate, or honest DECLINE.
- **`broth`** — O(1) lookup over 3,772 proven entries (Gosper-grown hypergeometric family; ~0.09µs lookup).
- Arsenal families: number_theory (egcd/modinv/CRT/modexp/Diophantine/primality/factorize/φ/discrete-log/√/Pell) ·
  combinatorics (Gosper, binomial, Catalan) · linear_algebra (solve/inverse/det/eigen) ·
  algebra (factor/gcd/roots/interpolate/partial-fractions/systems) · geometry · certified_numeric (Sturm/IVT/√/Monte-Carlo) ·
  optimization (LP duality) · science_engineering (dimensional) · probability (Markov/Chebyshev) ·
  inequalities (nonneg/SOS) · differential (ODE) · graph (shortest-path/bipartite) · special_functions (Γ/ζ) ·
  calculus (∫/d/dx/Taylor) · logic (Z3 SAT/tautology/equiv).
- Entry point `solver.py`: free-text/JSON → `solve_in_mode(mode)`; `MathSolution.trace()` shows grade-tagged reasoning.
- Measured coverage (`benchmark.py`): **41 problems / 16 domains — EXACT 32, PROBABILISTIC 1, DECLINE 8**, all
  matching expected grade, 26 cross-checked vs ground truth. Demonstration: `reports/archive/MATH_SHOWCASE.md`.

## §B UI (served single-file `mrjeffrey.html`)
- CODE ⇄ MATH toggle (re-themes + re-routes); fast/normal/extend preserved inside each.
- Universal file attachment (drag-drop + picker) → `/api/math/ingest`; fold-accelerated analysis.
- Safe archive extraction (`archive.py`): zip/tar/gz, in-memory, zip-slip + decompression-bomb defenses.

## In progress / planned (NATIVE-CORE directive)
- §0.5 cleanup: **C1 HANDOFF ✅ · C2 STATUS.md (this) + archive ✅ · C3 key wording · C4 dedupe · C5 versioning · C6 perf↔correctness gates**.
- §3 AST-depth fast-triage before the proof cache · §1 Rust core (arena AST, deterministic fixed-precision ring,
  deterministic SIMD) · §2 zero-dependency bit-blasting SMT (CDCL SAT + certificate checker) · §4 multi-LLM
  abstraction + mock · §5 dependency elimination. Native build / live egress marked **UNVERIFIED** where the
  sandbox blocks, with the Python path as the verified fallback — never faked.

## Known flakes (load-induced, NOT regressions — pass in isolation)
`test_round2_sublinear_sketches` (HLL ε near boundary), `test_pillar3_stage2_compounding_loop` (timing),
absolute-threshold perf gates (`test_v40_phase2_structured_matrices`, `test_foldext2_stage*`). C6 splits these
perf assertions out of the correctness suite so "0 regression" holds on any hardware.

## Version scheme (C5 — one monotonic timeline; legacy labels mapped)
Build numbering is the git history on this branch. Legacy labels map onto one timeline:
`v4–v40` (early kernels) → `MEGA`/`PILLAR3 stage0–5` (CODE engine) → `OMEGA Rounds 1–3` (CODE breadth) →
`MATH-Ascent §1–§8 + §B1–B4` (MATH mode) → **NATIVE-CORE** (current). Going forward: one scheme — this file's
"Now building" line + git history. No new v-numbers / campaign names.

## Deploy (one user action)
Render (Docker): set **Branch = `claude/charming-brahmagupta-q4wwgh`**, Root `.`, Dockerfile `./Dockerfile`,
Manual Deploy → Clear build cache & deploy. Routes/CMD/`/api/math/*` verified locally; rebuild is the user's action.
Details: `DEPLOY_NOTES.md`.

## Document map
Root keeps only: `README.md`, `HANDOFF.md` (onboarding), **`STATUS.md`** (this), `DEPLOY_NOTES.md`, and
`NATIVE_CORE_REPORT.md` (when the native work lands). All historical campaign reports → `reports/archive/`.
