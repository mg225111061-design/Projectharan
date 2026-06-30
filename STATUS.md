# STATUS — MR.JEFFREY / HARAN  (single source of truth)

*This is the ONE document that states what is true NOW. Autonomous builds update THIS file rather than spawning a
new top-level report. Historical campaign reports live in `reports/archive/`. Every number here is reproduced by
`test_build.py` — if a number drifts, the build is wrong, not this file. Last verified: fresh suite run below.*

## Current state (measured)
| | |
|---|---|
| Repo / branch | `mg225111061-design/Projectharan` · **`claude/charming-brahmagupta-q4wwgh`** |
| Tests | **276 passed / 276** — `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 test_build.py` (+1 §MRJ provider-wiring · +1 §BE browser-offload/isolation · +1 §BF `-O` soundness-gate regression); `test_catalog.py` **238** (+4 §BA caps · +1 §SEC search-gate · +1 §BB R-1 slice-split · +1 §BC CA-1 causal-poset · +1 §BD checker-layer · +1 §BF DECLINE diagnostics) |
| Top-level modes | **CODE** (verified whole-program optimizer, OMEGA) + **MATH** (MATH-Ascent) — UI toggle, `data-top` |
| MATH arsenal | **17 families** + central `fold` + O(1) `broth` (3,772 entries) |
| Served app | Docker → `server:app` serves `mrjeffrey.html` at `/`; `/api/optimize`, `/api/math/solve`, `/api/math/ingest` |
| Now building | **UNIFIED ARSENAL** (a transform system + b ~70 fold families + c physics) — foundational-first: §1 ✅ (G1·G2·G3·G4) → §2 ✅ (Petkovšek·Abramov·Risch·Kovacic·CAD) → §3 physics: P7·P2·P6·P9·P5·P8·P1 ✅ · P3 Petrov ✅ · P4 Cartan–Karlhede ✅ (physics P1–P9 ✅) → §4 transforms: T-symbolic-dynamics·T-spectral-operator·T-number-system·T-structure+randomness ✅ · ROUTER ✅ (6 categories) → **MATH recognition PHASE-1 ✅** (robust parser + fast kernels: modexp/fib/Faulhaber/Lucas-Lehmer/collatz, 3-way DECLINE) → §4 transforms. (NATIVE-CORE done: `NATIVE_CORE_REPORT.md`.) |

## Grades (the ADT, enforced at construction — `kernel_verdict.py`)
- **EXACT** — machine-checked certificate / decision procedure / exhaustive-bounded domain (bound stated).
- **PROBABILISTIC(ε,δ)** — approximation/randomized; δ stated; never EXACT even at δ≤10⁻¹⁸.
- **DECLINE** — irreducible / undecidable / no closed form / unstructured. Dignified, proven, never a fabrication.
- A wrong "EXACT" is a correctness bug; the adversarial battery injects fake-EXACT / rubber-stamp / grade-mismatch and the ADT rejects every one (`test_moat_battery`, `test_*_dogfood`).

## CODE mode (pillar3 / webapi / server)
- OMEGA Rounds 1–3 fully dispositioned (90/90). EXACT-share ≈ **68%** of graded capabilities (`exact_share.py`).
- Recognizers + verified lifting + e-graph + superopt + sound static analyses; fast/normal/extend mode separation
  with **ENFORCED wall-clock budgets** (~1 s / ~30 s / ~8 min) — `pillar3/mode.py` is the contract,
  `mode_budget.run_under_mode_budget` is the runtime. **extend is BOUNDED at ~8 min, NOT unlimited**: at the
  deadline it returns the best CERTIFIED result reached (or an honest partial), never runs past budget, never
  fakes to fill time, never weakens a grade to go faster; fast (MICRO tier) NEVER calls the heavy solver; the hard
  watchdog (`latency_budget.run_with_budget`, daemon thread) means no tier ever hangs. `test_mode_budget_roles`.

## MATH mode (`mathmode/`, 22 modules)
- Center: **`fold`** — recognize structure → closed form + co-generated certificate, or honest DECLINE.
- **`broth`** — O(1) lookup over 3,772 proven entries (Gosper-grown hypergeometric family; ~0.09µs lookup).
- **§AZ CAPABILITY LEDGER** (decision/proof power; ★fold-rate impact 0 — capability ≠ fold-rate; new decision branches
  in EXISTING modules, 14/22 mechanism count UNCHANGED, 0 new files, zero-dep): **CAP-1** Morales-Ramis (PROVE
  Hamiltonian non-integrability via the NVE + reused Kovacic) · **CAP-2** Darboux/Prelle-Singer polynomial first integral ·
  **CAP-4** Sylvester AX+XB=C unique solvability (self-impl resultant) · **CAP-5** Frobenius ℚ-similarity (degree≥5
  eigenvalue-wall bypass) · **CAP-6** exact Jordan/Weyr · **CAP-7** algebraic-GF/transcendence. Highest value = the
  HONEST_DEFER completion — UNKNOWN/timeout DECLINEs become *theorem-backed PROVEN DECLINEs* (precision 1.0 preserved).
  CAP-3 (order≥3 differential-Galois) and CAP-8 (multivariate Chyzak) DEFERRED — soundness-critical, not overclaimed.
- Arsenal families: number_theory (egcd/modinv/CRT/modexp/Diophantine/primality/factorize/φ/discrete-log/√/Pell) ·
  combinatorics (Gosper, binomial, Catalan) · linear_algebra (solve/inverse/det/eigen) ·
  algebra (factor/gcd/roots/interpolate/partial-fractions/systems) · geometry · certified_numeric (Sturm/IVT/√/Monte-Carlo) ·
  optimization (LP duality) · science_engineering (dimensional) · probability (Markov/Chebyshev) ·
  inequalities (nonneg/SOS) · differential (ODE) · graph (shortest-path/bipartite) · special_functions (Γ/ζ) ·
  calculus (∫/d/dx/Taylor) · logic (Z3 SAT/tautology/equiv).
- Entry point `solver.py`: free-text/JSON → `solve_in_mode(mode)`; `MathSolution.trace()` shows grade-tagged reasoning.
- Measured coverage (`benchmark.py`): **62 problems / 22 domains — EXACT 50, PROBABILISTIC 1, DECLINE 11**, all
  matching expected grade (62/62), 34 cross-checked vs ground truth. Spans the unified arsenal: G1–G4 foundations
  (telescoping/ΠΣ*), §2 decision procedures (Petkovšek/Abramov/Risch/Kovacic/CAD), §3 physics P1–P9
  (Buckingham/Petrov/Wigner/operator-algebra), §4 transforms (symdyn/number/randomness/spectral), and the PHASE-1
  fast kernels (modexp/fib O(log) · Lucas–Lehmer with honest infeasibility ceiling). Demo: `reports/archive/MATH_SHOWCASE.md`.

## §B UI (served single-file `mrjeffrey.html`)
- CODE ⇄ MATH toggle (re-themes + re-routes); fast/normal/extend preserved inside each.
- Universal file attachment (drag-drop + picker) → `/api/math/ingest`; fold-accelerated analysis.
- Safe archive extraction (`archive.py`): zip/tar/gz, in-memory, zip-slip + decompression-bomb defenses.

## Module families (C4 — analyzed; not the trivial dups the review assumed)
A dependency-mapped review (importers per module) found these are **layered, distinct-consumer modules, not
literal copies** — so a behaviour-preserving merge is a real refactor, not a delete:
- **e-graph (4):** `egraph` (core engine) · `equality_saturation` (e-graph + Z3-extraction — the MATH `fold`'s
  critical path) · `fold_egraph` (fold-rules **already reusing `egraph`**, i.e. an adapter) · `egraph_native`
  (extracted-term → LLVM emit). Four pipeline STAGES, not four engines. The two cores (`egraph` /
  `equality_saturation`) genuinely overlap → **unification folds INTO §1** (the native term core becomes the one
  canonical engine; merging Python now then rewriting in Rust would be wasted work).
- **spec_* (6):** a LAYERED toolkit, not dups — `spec_strengthen`→`spec_strength_gate`, `spec_infer`→`spec_fragment`,
  `spec_gate`←prove_exact/measure, `spec_propagation`←proof_dag; `spec_strengthen`/`spec_propagation` are
  **tested** (not dead). Kept; the layering is intentional and documented.
- **frontends (6):** distinct LANGUAGES (c/go/java/js/native…), not copies. tree-sitter convergence deferred
  (availability + a large rewrite); honest UNVERIFIED, not faked.
Conclusion: no risky merge performed (the suite stays green); the real e-graph unification is sequenced into
§1, the spec_* layering is kept, frontend→tree-sitter is deferred. Entropy reduced by MAPPING + the C1/C2 doc fixes.

## In progress / planned (NATIVE-CORE directive)
- §0.5 cleanup: **C1 HANDOFF ✅ · C2 STATUS.md (this) + archive ✅ · C3 key wording ✅ · C4 mapped (e-graph→§1) ✅ · C5 versioning ✅ · C6 perf↔correctness gates ✅ · C-process stale-doc test ✅**.
- **HARAN-50 ✅ COMPLETE** `algo50.py` — the honest CATALOG of the 50 NAMED layer-1 algorithms (20 foundational ·
  10 frontier · 15 number-theory · 5 quantum/relativity), each POINTING into the real implementation (no
  re-implementation). MEASURED status: **50 CONFIRMED + 0 PARTIAL + 0 GAP** — every named algorithm is fully built,
  certificate-bearing, and adversarially tested (Groups A/B/C/D all confirmed). The 8 original gaps (#45 Jacobi,
  #43 sieve, #32 power-towers, #34 Lucas/Granville, #14 Newton-series, #13 Bostan–Mori, #28 autodiff, #19 Gröbner)
  and all 9 partials (#44 Möbius, #42 Stern–Brocot, #29 multipoint-eval, #36 BPSW, #39 Cipolla, #40 Pollard-rho-dlog,
  #38 Pollard p−1, #17 Hermite, #25 exact-CP-rank1) were built/closed one-per-commit. A per-commit test
  (`test_algo50_registry`) IMPORTS every entry point so "we have algorithm N" is re-checked. §2 BROTH widened
  (`haran_broth.py`, 1,367 cross-algorithm instantiations across 13 of the 50 @ ~0.07 µs O(1), each re-verified by
  re-execution); §3 measured coverage (`algo50_coverage.py`: MATH 53 cases / 25 algorithms certified + CODE-side
  code-shape reach 39 execution-verified collapses [6 Σ-targets × 5 shapes + 4 nested + 4 filtered + 1 strided],
  6/6 adversarial DECLINE, domain-conditional); §4 tier routing (`algo50_router.py`: broth-hit short-circuits any
  mode, fast never hosts the heavy
  solver). §X honest caveats RECORDED + test-enforced: CAD doubly-exp, Lucas–Lehmer O(p)-iter, general CP/Tucker
  & ECM NP-hard ⇒ DECLINE; PROBABILISTIC never EXACT; 50 NAMED GENERAL algorithms ≈15 fundamental + specializations,
  NOT 50 distinct structures; broth = precomputed-lookup-fast, NOT execution-O(1).
- **§3 ✅** AST-depth fast-triage before the proof cache (`proof_triage.py`; deterministic route, lossless verdict;
  regression demonstrated + fixed in `proof_cache.measure_triage`; `test_native_s3_triage_layer`).
- **§2 ✅** ZERO-DEPENDENCY bit-blasting SMT (`bitblast_smt.py`: in-house DPLL SAT + bit-blaster + independent
  certificate checker — no coqc/cvc5/Bitwuzla/Lean/Z3). Decides QF-bitvector (add/sub/neg/mul-by-const/general-mul/
  udiv/and/or/xor/not/shl/lshr/ashr/shl_var/lshr_var/eq/ult/slt/sgt/ite-mux), EXACT *within the stated width* (bound = 2^w), deterministic
  (same result **and** certificate), every SAT model re-checked by a tiny TCB. Wired into
  `pillar3/bv_validate.bv_equiv_inhouse` and cross-checked against Z3 on the sound peepholes
  (`cross_check_inhouse_vs_z3` → all agree). The expanded theory decides a STRENGTH-REDUCTION catalog VALID in-house
  (`prove_strength_reductions`: mul↔shift, branchless sign-mask `ashr(x,w-1)=neg(lshr(x,w-1))`, bit round-trips,
  ×-ring commute/assoc/distrib, and **branchless conditional tricks verified ≡ their if-then-else spec** — e.g.
  branchless abs `(x^ashr)−ashr ≡ x<0?−x:x` via ite-mux) — so CODE can ACCEPT those speedups with zero external
  solver, EXACT within width; `test_native_s2_bitblast_smt`. **Honest scope (§X):** NOT cvc5/Z3 parity — no
  arrays/reals/unbounded ints; the overflow-unsafe peepholes stay out of the SOUND cross-check because they're
  UNSOUND (the in-house solver can now DECIDE all three — the conditional ones via ite-mux, `mul2_div2_id` via
  sdiv — but the cross-check asserts PROVEN≡PROVEN, so only SOUND peepholes participate). Signed compare, general
  multiply, right-shift, ite-mux, UNSIGNED+SIGNED division (udiv/sdiv — incl. div→shift `x//2^k ≡ x>>k` and the
  signed div→shift WITH round-toward-zero BIAS), and VARIABLE-amount shift (barrel shifter — incl. mul-by-power-of-
  two `x·2^k ≡ x<<k`) ARE in-house. Small TCB, zero deps — that's the point.
  **★ Scope (§BF FIX-2 — honest framing):** this is a *small-width, from-scratch DPLL demonstrator* that
  independently validates bitvector identities — its SAT core is naive (lowest-index / positive-first; no
  CDCL/watched-literals/VSIDS), so it is **not** a z3 replacement at scale. **z3-solver≥4.12 remains a hard
  dependency** (`requirements.txt`) on the MAIN verification path; "zero-dependency SMT" means *this checker* needs
  no external solver, NOT that the system dropped z3.
- **§1 ✅** dependency-0 Rust core (`rust_core/` std-only cdylib via ctypes — no PyO3/maturin/cffi/flint/faer;
  `rust_core.py` bridge). Delivers the v34-deferred pieces: flat **arena AST** (one deterministic pass);
  **deterministic fixed-precision multimodular CRT ring** — Garner-combines residues over a fixed 4-prime basis
  into the EXACT integer (native big-uint), replacing Python bignum, EXACT while |v| ≤ MAX_ABS = (∏p−1)/2 (123-bit;
  beyond it the basis must widen or DECLINE — the wrap is exactly at the bound, stated honestly); bounded
  **rational reconstruction**; **deterministic fixed-reduction-order** modular dot (the "SIMD" demonstrator: pure
  integer + fixed order ⇒ bit-identical regardless of vectorization/threads). Verified: Rust≡Python differential +
  a FORMAL exhaustive-bounded equivalence (12,789 enumerated arena×assignment checks, 0 mismatches) + exhaustive
  CRT round-trip. `test_native_s1_rust_core`. **Measured honestly:** no speed crossover at this granularity (ctypes
  overhead vs C-fast CPython int) ⇒ speed **UNVERIFIED**, correctness is the deliverable (mirrors the v40-phase7 RNS
  honesty). Native rewrite changes RUNTIME not GRADES; `target/` is environment-built (gitignored), Python ring is
  the verified fallback — never faked.
  **★ Scope (§BF FIX-3 — honest framing):** this is *future-native scaffolding*, NOT a working accelerator.
  At the current granularity the ctypes boundary overhead exceeds CPython's C-fast bignum, so it is a **performance
  no-op today** (speed UNVERIFIED) — **correctness is the deliverable**. Calling it "native acceleration" describes
  the *path being built*, not a measured speedup.
- **§4 ✅** multi-LLM routing abstraction + high-fidelity OFFLINE mock (`llm_router.py` over `provider.py` /
  `claude_agent.py`). One router selects the wire transport (Anthropic Messages / OpenAI chat.completions / Gemini
  generateContent), shapes the request EXACTLY as the live path, runs a mock returning PROVIDER-SHAPED raw
  responses, and parses back — so routing+serialization+parsing for every gateway (anthropic, openai-compat incl.
  OpenRouter / Z.ai / DeepSeek, gemini, groq) runs with ZERO network, deterministically. `test_native_s4_llm_routing`.
  **Honest (§X):** a mock is always `live=False` / `source=mock-sim:*` (never dressed as live); the real-egress LIVE
  path is **UNVERIFIED** [egress-blocked] and NEVER fabricates a response; keys are per-call args, redacted, never
  logged. LLM proposes, the verifier grades.
- **§5 ✅** dependency elimination, MEASURED + ENFORCED (`dependency_audit.py`, `test_native_s5_dependency_audit`).
  FORBIDDEN big provers / native binders (coqc/cvc5/Bitwuzla/Lean/PyO3/maturin/cffi) = **0 imports**; the grade
  ADT + the whole NATIVE-CORE (7 modules) are **STDLIB-ONLY** — empty third-party closure, proven statically AND
  at runtime (a subprocess imports them with numpy/sympy/z3/anthropic/openai/numba/llvmlite all hidden, every one
  loads); **numpy is OPTIONAL-not-required for the core** (a heavy dep of specific CODE/MATH numeric kernels only);
  17 optional packages are lazy/graceful-degrade. Final hard top-level set: `fastapi, numpy, pydantic, sympy, z3`.
- **NATIVE-CORE is COMPLETE** — full report in `NATIVE_CORE_REPORT.md` (with the §X "what we must not claim"
  constraints kept verbatim). Native build / live egress stay **UNVERIFIED** where the sandbox blocks, Python path
  the verified fallback — never faked.

## Known flakes (load-induced, NOT regressions — pass in isolation)
`test_round2_sublinear_sketches` (HLL ε near boundary), `test_pillar3_stage2_compounding_loop` (timing),
absolute-threshold perf gates (`test_v40_phase2_structured_matrices`, `test_foldext2_stage*`),
`test_native_s3_triage_layer` (cache-regression margin ~0.1s), `test_s12_structure_offload` (JOIN hash-rewrite timing), `test_phaseInfinity_D5_detectors` (45× timing), `test_phaseD2_structural_detectors` (razor-thin SoA ~1.3× perf ratio), noisy under load, and
`test_phaseV_equivalence_coverage` (couples a measured win-floor to the EXACT grade ⇒ noisy under parallel load;
PROVEN-equivalence itself is stable — pass in isolation). C6 splits perf assertions out of the correctness suite so
"0 regression" holds on any hardware; these remaining win-floor/threshold couplings are the next C6 candidates.

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
**`NATIVE_CORE_REPORT.md`** (the native campaign — landed). All historical campaign reports → `reports/archive/`.
