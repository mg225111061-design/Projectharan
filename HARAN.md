# HARAN — one-file master reference

**50 named layer-1 algorithms + cross-algorithm broth + general code-shape collapse**, with an
honest-grade / re-checkable-certificate / decision-procedure discipline. This single file consolidates the whole
system: the algorithm catalog, the broth, the code-shape recognizer, the measured coverage, tier routing, the
soundness story, and the honesty constitution. Every number below is pulled LIVE from the modules (regenerate with
`python3 gen_haran_md.py`) — nothing here is hand-typed.

> **Honesty banner (§X).** Grades are an ADT — `EXACT` / `PROBABILISTIC(ε,δ)` / `DECLINE` — never blurred. A
> "collapse" ships only behind a re-checkable certificate (a differential-equivalence gate against the *real
> executed code*, or a complete decision procedure). Hard limits are NAMED, not hidden: CAD is doubly-exponential,
> Gröbner is EXPSPACE, Lucas–Lehmer is O(p)-iteration, general factorization / CP-rank / ECM are NP-hard or
> subexponential → they **DECLINE** rather than fake an O(1). The broth is **precomputed-lookup-fast, NOT
> execution-O(1)**. Code-shape collapse is **DOMAIN-CONDITIONAL** — unstructured code declines (the honest
> majority); this is not a general-purpose accelerator.

---

## 0 · Status at a glance

| Metric | Value |
|--------|-------|
| Named algorithms | **50** — A=20 · B=10 · C=15 · D=5 |
| Status | **50 CONFIRMED · 0 PARTIAL · 0 GAP** (all 50 entry points import + resolve) |
| Grades | **47 EXACT · 3 PROBABILISTIC** |
| Tiers | fast=10 · normal=31 · extend=9 |
| Broth | **1,367 pre-proven instantiations** across **13 of the 50**; O(1) lookup ≈ **0.102 µs** (all-hit, size-independent) |
| Measured coverage (MATH) | **53 cases / 25 algorithms** certified; **6/6** adversarial DECLINE |
| Measured coverage (CODE) | **39 execution-verified collapses** (30 single-fold + 4 nested + 4 filtered + 1 strided); **6/6** adversarial REJECT |
| Tier-routing invariant | fast hosts **0** heavy solvers (40/50 TIER_UP in fast); extend runs all 50 |
| Tests | **273 passed / 273** — deterministic runner (command below) |

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 test_build.py
```

---

## 1 · The 50 named algorithms

Each is a GENERAL, certificate-bearing decision procedure or kernel with an HONEST grade and HONEST complexity.
"Broth ✓" = common instantiations are pre-proven offline for O(1) lookup. Entry point = the module + callable that
`test_algo50_registry` imports and re-checks every commit.

### Group A — Foundational symbolic / summation / algebraic (20)

| # | Algorithm | Grade | Tier | Broth | Honest complexity / decision | Entry point |
|---|-----------|-------|------|-------|------------------------------|-------------|
| 1 | Gosper | EXACT | normal | ✓ | decision; closed-form-or-proven-none | `mathmode.telescoping.gosper_indefinite` |
| 2 | Zeilberger (creative telescoping) | EXACT | normal | ✓ | decision; O(order·deg) ansatz | `mathmode.telescoping.zeilberger` |
| 3 | q-Zeilberger | EXACT | normal | ✓ | bounded q-ansatz | `q_fold.q_fold` |
| 4 | Petkovsek (Hyper) | EXACT | extend | · | decision; solutions-or-proven-none | `mathmode.decision_summation.petkovsek` |
| 5 | Abramov (rational summation) | EXACT | normal | · | decision; rationally-summable-or-not | `mathmode.decision_summation.abramov_summable` |
| 6 | Karr/Schneider PiSigma* | EXACT | extend | · | decision; nested sum/product | `mathmode.pisigma.telescope` |
| 7 | Holonomic / D-finite closure | EXACT | normal | ✓ | closure (sum/product/substitution) | `mathmode.holonomic.grade_sum` |
| 8 | Ore-algebra / skew-polynomial core | EXACT | normal | · | decision; normal form | `mathmode.ore.OreAlgebra` |
| 9 | Faulhaber / Bernoulli power sums | EXACT | fast | ✓ | O(n)→O(1) closed form | `pillar3.polysum.polysum_grade` |
| 10 | C-finite + fast-doubling | EXACT | normal | ✓ | O(n)→O(log n) | `cfinite.companion_nth` |
| 11 | Matrix power (binary exp + Cayley–Hamilton) | EXACT | fast | ✓ | O(log n); A^n mod m bounded | `cfinite.companion_nth_mod` |
| 12 | NTT / FFT convolution | EXACT | normal | · | O(n²)→O(n log n) | `pillar3.convolution.conv_ntt` |
| 13 | Bostan–Mori (GF coefficient extraction) | EXACT | normal | ✓ | O(M(d) log n) | `newton_series.bostan_mori_grade` |
| 14 | Newton iteration on power series | EXACT | normal | · | quadratic convergence, O(M(n)) | `newton_series.newton_series_grade` |
| 15 | Berlekamp–Massey | EXACT | normal | · | O(n²); structure-or-no-short-rec | `benortiwari.berlekamp_massey` |
| 16 | Risch (elementary integration) | EXACT | extend | · | decision (transcendental case) — _algebraic case PARTIAL — honest (transcendental case complete)_ | `mathmode.decision_integration.risch_elementary` |
| 17 | Hermite reduction (rational integration) | EXACT | normal | · | O(poly) linear solve — _standalone Hermite/Horowitz reduction (rational part) + the Risch decision both present_ | `hermite.hermite_reduce_grade` |
| 18 | CAD (cylindrical algebraic decomposition) | EXACT | extend | · | DOUBLY-EXPONENTIAL — NEVER O(1) — _doubly-exponential; univariate/low-dim within the extend budget, else DECLINE_ | `mathmode.real_qe.decide` |
| 19 | Gröbner basis (Buchberger / F4) | EXACT | extend | · | EXPSPACE worst case — extend-budgeted (DECLINE past the step cap) — _Buchberger with cofactor tracking; F4 (matrix acceleration) not added — same ideal, faster_ | `groebner.ideal_member_grade` |
| 20 | Kovacic (Liouvillian 2nd-order ODE) | EXACT | extend | · | decision; Liouvillian-or-not | `mathmode.decision_integration.kovacic_liouvillian` |

### Group B — Frontier sublinear / sparse / streaming (10)

| # | Algorithm | Grade | Tier | Broth | Honest complexity / decision | Entry point |
|---|-----------|-------|------|-------|------------------------------|-------------|
| 21 | Sparse FFT | EXACT | normal | · | sublinear where k≪n | `sparse_fft.recover` |
| 22 | Compressed sensing / ℓ1 (with certificate) | EXACT | normal | · | EXACT w/ cert, else PROBABILISTIC — _EXACT only when the dual certificate holds; otherwise PROBABILISTIC_ | `compressed_sensing.recover` |
| 23 | Prony / ESPRIT / matrix-pencil | EXACT | normal | · | generalized eigenproblem | `prony.recover` |
| 24 | Matrix completion (low-rank) | PROBABILISTIC | normal | · | PROBABILISTIC(ε,δ) — never EXACT — _EXACT only with an exact-completion certificate; default grade PROBABILISTIC_ | `matrix_completion.complete` |
| 25 | Tensor decomposition (CP/Tucker exact cases) | EXACT | normal | · | rank-1 exact; higher CP rank NP-hard → DECLINE — _exact CP (rank ≤ 1) decomposition + mono-term canonicalization present; general CP/Tucker is NP-hard ⇒ certified-numeric/DECLINE beyond rank-1_ | `cp_decompose.cp_decompose_grade` |
| 26 | Spiked / planted-signal detection | PROBABILISTIC | normal | · | PROBABILISTIC(δ) — _random-matrix universality used (not invented); detection is PROBABILISTIC_ | `planted_detect.detect` |
| 27 | Streaming sketches (Count-Min / AMS / HLL) | PROBABILISTIC | fast | · | sublinear space; PROBABILISTIC — _PROBABILISTIC(ε,δ) BY CONSTRUCTION — never EXACT even at tiny δ_ | `sketching.heavy_hitters` |
| 28 | Automatic differentiation (exact dual) | EXACT | normal | · | O(nodes·vars) forward | `autodiff.autodiff_grade` |
| 29 | Fast multipoint eval + interpolation | EXACT | normal | · | O(M(n) log n) eval — _fast multipoint EVALUATION (subproduct tree) + sparse interpolation present; a fast O(n log²n) dense interpolation not yet_ | `newton_series.multipoint_eval_grade` |
| 30 | Walsh–Hadamard / NTT (general) | EXACT | normal | · | O(n²)→O(n log n) | `kernels_symbolic.measure_wht` |

### Group C — Number theory (15)

| # | Algorithm | Grade | Tier | Broth | Honest complexity / decision | Entry point |
|---|-----------|-------|------|-------|------------------------------|-------------|
| 31 | Fast modular exponentiation | EXACT | fast | ✓ | O(log b) | `mathmode.number_theory.modexp_grade` |
| 32 | Power towers via Carmichael-λ | EXACT | fast | ✓ | O(log) modexp + λ(m) factorization | `mathmode.number_theory.power_tower_grade` |
| 33 | Fast-doubling Fibonacci / Lucas mod m | EXACT | fast | ✓ | O(log n) | `mathmode.fastkernels.fib_mod` |
| 34 | Lucas' theorem + Granville lifting | EXACT | fast | ✓ | O(log_p n · p^e) for astronomical n | `mathmode.number_theory.binom_mod_pe_grade` |
| 35 | Extended Euclid / Bézout + CRT (Garner) | EXACT | fast | · | egcd O(log min); CRT O(k²) | `mathmode.number_theory.crt_grade` |
| 36 | Miller–Rabin (deterministic, bounded) + BPSW | EXACT | normal | ✓ | EXACT < 3.317e24, PROBABILISTIC above — _deterministic MR + BPSW (strong MR-2 ∧ strong Lucas) present; disjoint-liar property tested_ | `mathmode.number_theory.bpsw_grade` |
| 37 | Lucas–Lehmer (Mersenne) | EXACT | extend | · | O(p)-ITERATION — real ceiling (p≲20000 here); astronomical p → DECLINE, never O(1), never a hang — _honest O(p)-iteration; NOT a collapse_ | `mathmode.fastkernels.lucas_lehmer` |
| 38 | Pollard rho / p−1 / ECM factorization | EXACT | extend | · | subexponential, NOT guaranteed — _trial + Pollard rho + Pollard p−1 present; ECM (elliptic-curve method) not yet_ | `mathmode.number_theory.factorize_grade` |
| 39 | Tonelli–Shanks / Cipolla (modular sqrt) | EXACT | normal | ✓ | O(log² p) — _Tonelli–Shanks AND Cipolla present; each cross-checks the other_ | `mathmode.number_theory.cipolla_sqrt_grade` |
| 40 | Baby-step giant-step / rho (discrete log) | EXACT | extend | · | O(√n) time, O(1) space (rho) / O(√m) (BSGS) — _BSGS AND Pollard-rho (O(1) space) present; each cross-checks the other_ | `mathmode.number_theory.pollard_rho_dlog_grade` |
| 41 | Continued fractions + Pell | EXACT | normal | · | O(period)≈O(√D); n-th via matrix power O(log n) | `mathmode.number_theory.pell_grade` |
| 42 | Stern–Brocot / rational reconstruction | EXACT | fast | · | O(log m) — _Stern–Brocot tree (exact path + best rational approximation) AND modular reconstruction present_ | `mathmode.number_theory.stern_brocot_grade` |
| 43 | Sieve of Eratosthenes (segmented + wheel) | EXACT | normal | · | O(n log log n) ENUMERATION — not a collapse — _classic boolean sieve; segmented/wheel are constant-factor/memory optimizations, not yet added_ | `mathmode.number_theory.sieve_primes_grade` |
| 44 | Euler φ / Möbius / multiplicative functions | EXACT | normal | ✓ | factorization-bound — _Euler φ AND Möbius μ present; an arbitrary-multiplicative-function framework not yet abstracted_ | `mathmode.number_theory.mobius_grade` |
| 45 | Quadratic reciprocity / Jacobi symbol | EXACT | fast | ✓ | O(log a · log n) | `mathmode.number_theory.jacobi_grade` |

### Group D — Quantum / relativity (exact-algebraic only) (5)

| # | Algorithm | Grade | Tier | Broth | Honest complexity / decision | Entry point |
|---|-----------|-------|------|-------|------------------------------|-------------|
| 46 | Butler–Portugal tensor canonicalization | EXACT | normal | ✓ | Schreier–Sims; mono-term DECISION — _mono-term symmetries; multi-term/Bianchi → Young projectors, flagged_ | `mathmode.tensor_canon.canonicalize` |
| 47 | Curvature-from-metric + Einstein check | EXACT | normal | ✓ | closed-form metrics only — _EXACT for closed-form metrics; numerical relativity is certified-numeric/DECLINE_ | `mathmode.curvature.schwarzschild_grade` |
| 48 | Wick / normal ordering | EXACT | normal | ✓ | decision; Heisenberg algebra — _bosonic Heisenberg algebra; fermionic/grand-canonical flagged_ | `mathmode.operator_algebra.normal_order` |
| 49 | Wigner 3j/6j/9j + Clebsch–Gordan | EXACT | normal | ✓ | exact algebraic only — _exact rational×√rational; numerical j/m never claimed_ | `mathmode.wigner.wigner3j` |
| 50 | Dimensional analysis + Buckingham-Pi | EXACT | normal | ✓ | exact null-space — _integer null-space only; basis non-unique (canonical choice flagged)_ | `mathmode.buckingham.buckingham_pi` |

---

## 2 · The cross-algorithm BROTH (`haran_broth.py`)

The "instant" mechanism: COMMON instantiations are computed + certified ONCE offline (the brew); at runtime a
normalized key hits an **O(1) hash** and the pre-proven result + certificate returns instantly, size-independent.
The certificate discipline is the strongest possible — **every stored entry RE-VERIFIES by RE-RUNNING the real
algorithm** (`reverify`), so a corrupted/tampered cache is caught, never silently served.

- **1,367 entries across 13 of the 50**, by algorithm: #9×12, #10×7, #31×30, #32×36, #33×8, #34×4, #38×199, #39×109, #40×106, #41×33, #44×200, #45×174, #49×449
- O(1) lookup measured at **≈ 0.102 µs**, all-hit = `True`
- Families: #9 Faulhaber Σkᵖ · #10 named C-finite · #31 modexp · #32 power-towers · #33 fast-doubling Fibonacci ·
  #34 binomial mod p (Lucas, incl. astronomical n) · #38 factorization · #39 Cipolla √ mod p · #40 discrete log ·
  #41 Pell · #44 Möbius μ · #45 Jacobi · #49 Wigner 3j
- **§0-B honesty:** broth makes RECURRING cases instant ONLY because they were pre-proven offline — it does NOT
  make the algorithm's EXECUTION O(1). A MISS runs the algorithm at its true complexity (or honestly declines).

A second broth exists for the recognizer (§3): the pure fold solver `FK.fold_certificate` is memoized
(`_FOLD_BROTH`), so a recurring code-shape re-looks-up its solved closure in O(1) (~9× faster on repeat) — the
per-source differential gate still runs, so the cache speeds the SOLVER, never the safety check.

---

## 3 · General code-shape collapse (`structure_recognizer.py`)

"General code" is locally structured: under a piece there is often an algebraic object (monoid/semiring/…) and a
SHAPE. When recognized, a loop is OFFLOADED to a closed form — but only behind a **differential-equivalence gate
against the real executed code** (a wrong closed form is never emitted; a misread can only DECLINE).

**Code-shape invariance — 7 shapes → one collapse.** The SAME accumulation written as a `for`-loop, a counter-
`while`, a `sum`/`prod` comprehension, a linear self-recursion, or a `functools.reduce` fold all normalize to ONE
byte-identical structural key (`_acc_loop_any_shape`) and the SAME verified O(1) closed form (e.g. Σk² →
n(n+1)(2n+1)/6 for all five). Beyond single folds:

- **Nested** `Σ_i Σ_j h(i,j)` → O(1) (close inner fold → substitute → close outer); inner bounds may depend on the
  outer var (triangular). Degree-2 bounds → O(n³); honest per-case complexity.
- **Filtered** `Σ_{k%M==R} h(k)` → O(1) via the exact reindex k = M·t + r₀ (for-loop ≡ comprehension).
- **Strided / exponential** `for j in range(2ⁿ)` → O(1) closed form (the power is one bigint op, never the loop).

**Bounded gates (no-hang, sound).** Every gate that EXECUTES the user's loop is bounded by an iteration budget /
polynomial-bound guard, so no input (e.g. `range(2**i)`) can run an unbounded loop. Recognized-nested-but-declined
never falls through to the loop-sampling recurrence detector.

**Wired LIVE + stream-consistent.** `engine_bridge._loop_collapse` surfaces every shape at its OPTIMAL complexity
(dispatch before the recurrence detector → a polynomial sum is O(1), not O(log n); a genuine state-update loop like
Fibonacci still → O(log n)); `code_stream` streams the same verdict (stream ≡ result).

**Measured CODE reach (NO padding — each counts only if dispatch→OFFLOADED AND the closed form matches a
brute-force run on fresh inputs):** 30/30 (target × shape)
single-fold, all 6 targets shape-invariant; 4/4
nested; 4/4 filtered; 1/1
strided = **39 total**; **6/6**
adversarial shapes correctly REJECTED.

---

## 3b · Measured collapse coverage of the 50 (`algo50_coverage.py`)

The 50 are GENERAL (one covers many cases); this MEASURES that breadth on a curated corpus, DOMAIN-CONDITIONAL.

- **53 covered cases across 25 distinct algorithms**, all certified
  `EXACT` (53) — algorithms: #1, #5, #9, #10, #13, #14, #17, #19, #25, #28, #29, #31, #32, #33, #34, #36, #38, #39, #40, #41, #42, #43, #44, #45, #49
- A deliberately ADVERSARIAL block (transcendental Σ1/k, undefined recurrence, even-modulus Jacobi, out-of-range
  sieve, transcendental autodiff, non-prime binomial) **DECLINES 6/6**
  — the proof that coverage is domain-conditional, not a general accelerator, not "100%".

---

## 4 · Tier routing (`algo50_router.py`)

Operational glue tying §1 (each algorithm's tier) + §2 (broth) + the `pillar3/mode.py` fast/normal/extend contract:

- A **BROTH HIT short-circuits in ANY mode** — instant O(1) EXACT even in fast, regardless of how heavy the
  underlying algorithm is (e.g. #38 factorization is extend-tier, yet a broth hit returns instantly in fast).
- On a MISS, the algorithm runs ONLY if its tier ≤ the requested mode. **fast (~1 s) NEVER hosts an extend-tier
  heavy solver** (40/50 TIER_UP in fast, 0 heavy hosted) → it returns TIER_UP.
- normal (~30 s) runs fast+normal; **extend (~8 min, BOUNDED) runs all 50** = `True`.

---

## 5 · Soundness story

The recognizer is sound static analysis; the collapse ACTIONS are gated by execution, so a misclassification can
only DECLINE — never emit a wrong answer. Adversarial probing of the full pipeline found and fixed **three real
hang bugs** (all of the same class — an unbounded loop executed inside an equivalence gate):

1. **Nested gate** executed the real loop up to N=64 → an exponential inner bound `range(2**i)` ran ~2⁶⁴ iterations
   and hung → fixed with a polynomial-bound guard + small bounded samples.
2. **Recurrence fall-through** — a recognized nested loop that declined fell through to the loop-sampling recurrence
   detector → fixed by returning honest NONE without fall-through.
3. **Single-fold gate** had the same exposure on `range(2**n)` → fixed with a per-sample iteration budget (and now
   the exponential case OFFLOADS via affordable small samples — an O(2ⁿ) → O(1) win).

A consolidated adversarial battery (`test_haran_dispatch_adversarial_soundness`) asserts the whole pipeline is
sound on tricky near-misses (break/continue/side-effects/non-constant bounds/nested-lambda-reduce/global-in-
recursion → DECLINE; loop-var-shadow/true-div/n⁵-bound → correct OFFLOAD; infinite recursion → statically rejected,
no hang). The **gate, not any cache, is the soundness authority** — a forced-wrong closed form still DECLINEs.

---

## 6 · §X — what we must NOT claim (honesty constitution)

- Grades stay an ADT: never report PROBABILISTIC as EXACT; always state (ε, δ); DECLINE when outside the class.
- Doubly-exp / EXPSPACE / O(p)-iteration / NP-hard / subexponential limits are NAMED and routed to `extend` or
  DECLINE — never dressed as O(1).
- The 50 are GENERAL named algorithms (~15 fundamental ideas + specializations), NOT 50 fundamentally-distinct
  structures; the measured counts are SAMPLES of general capability, not the capability itself.
- Broth = precomputed-lookup-fast, NOT execution-O(1). Code-shape collapse = domain-conditional, NOT a general
  accelerator. Speedups are whole-program-for-this-function (f=1), grow as n/log n, and are ≤ the Amdahl ceiling
  embedded in a larger program.

---

## 7 · File map

| File | Role |
|------|------|
| `algo50.py` | The spine: the 50-algorithm registry (grade/complexity/tier/broth/decision) + `counts`/`verify_entrypoints`/`summary`. |
| `haran_broth.py` | §2 cross-algorithm broth: offline brew + O(1) lookup + `reverify` (re-runs the real algorithm). |
| `structure_recognizer.py` | §3 code-shape recognizer + dispatcher: for/while/comprehension/recursion/reduce/nested/filtered/strided → gated O(1) collapse; `_FOLD_BROTH` memo. |
| `algo50_coverage.py` | §3 MEASURED coverage: `measure()` (MATH, the 50) + `measure_code_shapes()` (CODE reach) + adversarial DECLINE blocks. |
| `algo50_router.py` | §4 tier routing: `route` / `routing_matrix` (broth short-circuit, fast-never-heavy invariant). |
| `webapi/engine_bridge.py` | Live engine: `_loop_collapse` surfaces every code-shape at optimal complexity (Gosper for-loops · nested · dispatch folds · recurrence state-updates). |
| `code_stream.py` | §3 live UI trace (ANALYZE→RECOGNIZE→APPLY→CERTIFY→VERIFY→RESULT), stream ≡ result. |
| number-theory & series | `mathmode/number_theory.py`, `newton_series.py`, `autodiff.py`, `groebner.py`, `hermite.py`, `cp_decompose.py`, `cfinite.py` — the algorithm implementations. |
| `test_build.py` | The deterministic suite (273 tests; run alone with the thread-cap command above). |
| `STATUS.md` / `HANDOFF.md` / `CODE_UPGRADE_REPORT.md` | Status board · onboarding · detailed change log (this file consolidates them). |

---

_Generated from live module data. Regenerate: `PYTHONPATH=. python3 gen_haran_md.py`._
