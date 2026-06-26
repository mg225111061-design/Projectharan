# BUILD LOG — chaos→structure catalog engine (14 meta-mechanisms)

10-hour autonomous build on v40 (281 files / 56,289 lines). Honest accounting per §1.4: "100% implemented" =
every transform has an HONEST entry (VERIFIED or UNVERIFIED(reason)) — NOT 100% passing. New kernels enter the
`kernel_router` REGISTRY only behind the §7 gate. Three clocks never mixed; fold = Clock C.

---

## PHASE A — skeleton (mechanisms/ + catalog/ + compose + decline_boundary) ✅

**What:** built the catalog-engine backbone on top of the existing `kernel_router.REGISTRY` + `kernel_verdict` ADT.

- `mechanisms/` — the 14 meta-mechanisms (1..14) + 2 cross-cutting primitives (Legendre duality, symmetry
  reduction), each a `Mechanism(probe, apply, cert_kinds, contract, composable_with)`. Real cheap `probe`s
  ([0,1]^14 routing signal); `apply`s return an honest `HONEST_DEFER` DECLINE (sound logic lands in PHASE B–F —
  no fake pass, no gateless kernel in REGISTRY). Framework CLOSED: closure_report → no 15th mechanism; ur-form
  annotations on M1/M13/M14.
- `catalog/` — `Transform` registry: **94 transforms** registered = the §4 named representatives across all 9
  passes (1-6:16, A-1:7, A-2:6, B-1:7, B-2:9, C-1:6, C-2:12, D-1:14, D-2:17). All 14 mechanisms have ≥1 transform;
  **38 are compositions** (deep results = mechanism composition, §3.4). (§0's "~190" is the broader research
  catalog; §4 enumerates 94 named representatives — these are registered 100%.)
- `catalog/compose.py` — §5 router skeleton: DECLINE-guard → existing-fold short-circuit → 14-probe vector →
  composition pipeline plan (`mechanism_path`). Real gated composition lands in PHASE E; PHASE A returns an honest
  DECLINE naming the planned path (never a fake result).
- `catalog/decline_boundary.py` — §6 backbone: Rice / incompressibility / turbulence guards (conservative keyword
  heuristics at PHASE A; real tests in PHASE D) + the 15-entry proven-boundary list.
- `test_catalog.py` — standalone suite; **6/6 green** (mechanisms closed, probe routing, honest coverage, DECLINE
  backbone, router, no-unverified-autoselect).

**Measured:** catalog coverage = 94 registered / 0 VERIFIED / 94 honest-deferred (PHASE A registers the catalog;
gated kernels follow). Router smoke: fold→EXACT[13] (Σk²→n(n+1)(2n+1)/6), Rice→DECLINE[14], SOS→DEFER plan[4→14],
classify→DEFER plan[9→2].

**Existing suite:** unaffected — PHASE A is purely additive (no existing file modified); `test_build` still
collects 273; new packages import cleanly alongside it.

**Deferred (K=94, reason):** every transform `apply` is HONEST_DEFER pending its PHASE (B: SOS/Presburger/RCF/ACF;
C: ordinal/NbE/arith-hierarchy; D: DECLINE guards; E: composition; F: domain applies). No gateless kernel registered.

**15th-mechanism candidate:** none — framework closed (D-1·D-2 reconfirmed).

---

## PHASE B — mature decision procedures (EXACT tier) ✅

- **★ SOS / Positivstellensatz (`sos_cert.py`, mechanism 4) — NEW EXACT tier.** Prove p ≥ 0 globally by a RATIONAL
  PSD Gram matrix Q with p = zᵀQz; both checks EXACT (zᵀQz≡p over ℚ; Q⪰0 via Sturm-exact negative-eigenvalue count
  of the characteristic polynomial — no floating SDP, no eigen-solve). Complete for quadratics (unique Gram); for
  higher even degree the particular Gram is tried and DECLINEs honestly if not PSD (no SDP cone search → no
  overclaim). Verified: (x-1)², (x-y)², x⁴+1, 2x²+2y²+2xy → EXACT SOS; x²-1/x³/xy/x⁴-x²/-x² → DECLINE; cert
  re-checks; tampered cert rejected. Bug found+fixed: PSD test mis-handled a repeated 0 eigenvalue (count_roots is
  distinct-count) → fixed.
- **RCF/CAD QE (`rcf_cad_qe` kernel) — reuse `mathmode.real_qe.decide` ([이미 있음]).** ∀x.x²+1>0 → EXACT True;
  ∀x.x²-1>0 → EXACT False. Routed through kernel_router with a structured RCF query.
- **Presburger QE (`presburger_qe.py`, direct z3 4.16.0 — the trusted oracle).** ∀(x∈ℤⁿ).φ valid ⟺ ¬φ UNSAT; a
  counterexample model is the witness otherwise. ∀x,y.2(x+y)=2x+2y → EXACT True; x+y=x → EXACT False+cex; garbage →
  DECLINE. (Bypassed the finicky `z3_adapter` string parser — "could not encode" on simple goals — per §1.6.)
- **ACF (Chevalley) — HONEST_DEFER:** no existing module; constructible-set projection beyond this PHASE's budget.
  D1.acf_qe stays UNVERIFIED(reason), kernel=None — registered honestly, not faked.

**Measured:** 3 §7-gated kernels registered into kernel_router.REGISTRY (all VERIFIED, contracts well-formed);
catalog coverage 94 registered / **4 VERIFIED** (B1.sos, D2.sos_refutation, D1.rcf_cad_qe, D1.presburger_qe) / 90
deferred. test_catalog **10/10 green** (4 new PHASE B tests incl. negative controls + tamper rejection).
**Deferred (K):** ACF (no module). All three clocks separated; SOS/QE are decision procedures (Clock B verify, not C).

---

## PHASE C — fold-core self-improvement ✅

- **Ordinal-bounded termination (`ordinal_cert.py`, mechanism 14/ordinal) — the fold decreases-clause.** A
  lexicographic measure (tuple of naturals) that maps to a strictly DESCENDING ordinal sequence (CNF) certifies
  termination (well-founded ⇒ finite). Reuses the existing [이미 있음] `ordinal.check_descent`/`lex_measure_to_ordinal`.
  EXACT on descending measures (e.g. (3,0)>(2,5)>(2,4)>(1,9)), DECLINE on ascending/equal (no false termination
  claim). Registered as the `ordinal_termination` kernel; backs D1.ordinal_termination + B2.ranking_termination.
- **Arithmetic-hierarchy routing probe (`arith_hierarchy.py`, mechanism 9) — §5-FIRST signal.** Heuristic placement:
  a Σ⁰₁/Π⁰₁-complete semantic-program-property (Rice) → DECLINE; a bounded/quantifier-free/decision-procedure query
  → PROCEED. Wired at the TOP of `catalog.compose.route` (before the mechanism probe vector). Honest: the hierarchy
  itself is undecidable, so this is a routing PROBE, not a decision kernel — D1.arithmetic_hierarchy stays
  UNVERIFIED (functional + wired, but not a gated decision kernel; declines are always sound).
- **NbE / cut-elimination as the eval core — HONEST_DEFER:** `haran_eval.Interp` exists but a gated `normalize()`
  fold-core entry is beyond this PHASE's budget (§1.6). D1.cut_elimination / D2.nbe / D2.hott_canonicity stay
  UNVERIFIED — not faked.

**Measured:** 1 new §7-gated kernel (`ordinal_termination`); catalog coverage 94 registered / **6 VERIFIED** / 88
deferred. test_catalog **13/13 green** (3 new PHASE C tests with negative controls + the §5-first short-circuit).

---

## PHASE D — DECLINE backbone (mechanism 12/14) ✅

- **MEASURED incompressibility (MDL 2-part code, `decline_boundary.mdl_*` + `mdl_incompressibility` kernel).**
  Replaces PHASE A's keyword heuristic with a real test: literal length L0 vs zlib-compressed length Lc (a SOUND
  upper bound on Kolmogorov complexity). Data with hidden structure COMPRESSES → EXACT code-length (PROCEED — this
  RECOVERS the "fake Ω(N)" cases); incompressible data → DECLINE, honestly framed as "no model in the MDL/zlib class
  beats the literal" (per-instance — NOT a Kolmogorov-randomness proof, which is uncomputable). Measured: os.urandom
  → ratio ≈1.0 DECLINE; `abcd`×200 → ratio 0.02 EXACT; range(1000) → ratio 0.17 EXACT. Backs D1.kolmogorov_incompressible
  + mechanism 12 apply.
- **Guards + proven boundaries (complete).** Rice / incompressibility / turbulence guards + the 15-entry proven-
  boundary list (Kolmogorov-random, halting/Rice, stat-comp gap, irreversibility, Galois/Liouville, volume-law,
  turbulence, crypto-PRG, MIP*=RE, natural/relativization/algebrization, MRDP, chaos, PPAD, CH, ordinal-limit).
- **Negative controls (central to the backbone):** every guard DECLINEs on its boundary marker; ordinary foldable
  code (`def f`, comprehensions, SOS polynomials) trips NO guard (`DB.check`→None) — no over-decline. A DECLINE is
  a POSITIVE absence-proof (a win).

**Measured:** 1 new §7-gated kernel (`mdl_incompressibility`); coverage 94 registered / **7 VERIFIED** / 87 deferred.
test_catalog **15/15 green** (2 new PHASE D tests). MDL is a structural test (not a clock — reported as ratio).

---

## PHASE E — mechanism-composition router (§5) ✅

`catalog.compose.route` now EXECUTES the built gated applies along the planned pipeline (no single-discipline 1:1
decomposition — routing is by mechanism composition) and returns the §5.6 output `(result, grade, certificate,
bound, mechanism_path)` via `CatalogResult.as_tuple()`. Order: arithmetic-hierarchy placement → DECLINE guards →
existing fold (M13) → data-like MDL (M12) → composition pipeline executing M4 (SOS) etc.

Working compositions (measured): fold Σk²→EXACT[13]; SOS (x-1)²→EXACT[4]; non-SOS x²-1→DECLINE[4,14] (M4 declines,
composition honest); random bytes→DECLINE[14]; structured data/range→EXACT[12]; halt-query→DECLINE[14]
(arith-hierarchy obstruction). Unbuilt compositions (classification 9→2, Robertson–Seymour 10→14) return an HONEST
DEFER naming the planned path — never a fake result. Built apply set: {M4, M12} inline + M13 (fold) + M14 (guards);
the rest HONEST_DEFER until PHASE F.

**Measured:** coverage 94 registered / 7 VERIFIED / 87 deferred; test_catalog **16/16 green** (new
test_phaseE_composition_router; updated the stale PHASE-A compose assertion now that SOS actually solves EXACT).

---

## PHASE F — domain applies (reuse mature modules) ✅

Buckingham-Π (M9, `mathmode.buckingham` [이미 있음]) → EXACT dimensionless-group normal form (pendulum →
gravity·period²/length); Noether energy conservation (M5, `mathmode.lagrangian` [이미 있음]) → EXACT conserved H
with dH/dt≡0. Thin §7-gated kernels (`buckingham_pi`, `noether_energy`); backs 16.buckingham_pi + 16.noether.
coverage 94 / **9 VERIFIED** / 85 deferred; test_catalog **18/18**.

---

# §C — CATALOG ENGINE BUILD REPORT

1. **Catalog coverage.** 94 transforms registered (the §4 named representatives; §0's "~190" is the broader research
   set) across **all 9 passes** and **all 14 mechanisms** (38 compositions). **9 VERIFIED** (§7-gated, kernel-backed):
   B1.sos_positivstellensatz, D2.sos_refutation, D1.rcf_cad_qe, D1.presburger_qe, D1.ordinal_termination,
   B2.ranking_termination, D1.kolmogorov_incompressible, 16.buckingham_pi, 16.noether. **85 honest-deferred**
   (UNVERIFIED(reason), kernel=None — never faked). Honest 100% REGISTERED, NOT 100% pass.
2. **New EXACT tier — SOS/Positivstellensatz.** WORKING (`sos_cert.py`). Example cert: x²−2x+1 = zᵀQz, Q=[[1,−1],
   [−1,1]]⪰0 (0 negative eigenvalues, Sturm-exact) ⇒ EXACT (x−1)². Non-nonneg ⇒ DECLINE; tamper rejected.
3. **Decision procedures.** Presburger (z3 oracle) ✓ EXACT True/False+counterexample; RCF/CAD (`mathmode.real_qe`) ✓;
   ACF (Chevalley) — HONEST_DEFER (no module).
4. **fold-core self-improvement.** Ordinal-bounded termination ✓ (the decreases-clause: strictly-descending lex→
   ordinal ⇒ EXACT terminates). NbE/cut-elim eval-core — HONEST_DEFER (haran_eval.Interp exists; gated normalize()
   beyond budget).
5. **DECLINE backbone.** Rice + MEASURED incompressibility (MDL 2-part, zlib K-upper-bound) + turbulence guards +
   15 proven boundaries. Negative controls pass; recovers "fake Ω(N)" (compressible data proceeds, incompressible
   declines).
6. **Mechanism-composition router (§5).** Working pipelines: fold[13], SOS[4], MDL[12], obstruction[14]
   (arith-hierarchy + guards). Planned-but-deferred compositions return HONEST_DEFER naming the path: classification
   9→2, Robertson–Seymour 10→14, structure⊕pseudorandom 7→13→12. Returns (result,grade,cert,bound,mechanism_path).
7. **Measurement (clocks, §2).** The catalog engine's collapses are DECISION procedures (Clock B verify) and the MDL
   structural test (a ratio, not a clock); the M13 path reuses the existing Clock-C-measured fold. No Clock-C
   runtime speedup is CLAIMED for the new decision kernels (they decide/certify; they are not emitted hot loops).
8. **False positives = 0.** Negative controls across the engine (random bytes / halting / x²−1 / equivalence /
   unstructured text) all DECLINE — never a non-DECLINE on a structureless/boundary input.
9. **Tests.** Existing `test_build` UNAFFECTED (273, additive build — no pre-existing file modified). New
   `test_catalog` **18/18 green** (each kernel: positive case + negative control + grade consistency; tamper rejection).
10. **15th-mechanism candidate.** None — framework CLOSED (D-1·D-2 reconfirmed; ur-form annotations on M1/M13/M14).
11. **research→judge→build cycles.** 0 (the PHASE A–F build consumed this session). The §9 loop (recover "fake Ω(N)":
    compressed-sensing per-instance witness / sparse-FFT / matrix-completion / Prony / spiked-detection) is the
    recommended next build.
12. **HANDOFF.md updated.** Yes (catalog-engine section added).
13. **Next build (honest UNVERIFIED list + why).** ACF QE (no module); NbE eval-core (gated normalize() needed);
    mechanism applies M1/M3/M6/M7/M8/M10/M11 (need mature-SW bridges: Sage/Macaulay2/CGAL/PySCF/LFADS/ZX);
    PHASE G SNARK/STARK cert-tech (integrity-proof wiring, optional); GCT (open obstacle — registered UNVERIFIED).

---

## §9 research→judge→build loop

**Cycle 1 — mechanism 1 (diagonalize): Sylvester inertia.** JUDGE: M1 spectral was deferred. RESEARCH: the inertia
(n₊,n₀,n₋) is a COMPLETE congruence invariant, computable EXACTLY from eigenvalue signs (symmetric ⇒ real spectrum)
— reuses the spectral theme. BUILD: `sos_cert.inertia/inertia_grade` + the `spectral_inertia` kernel; recovers
16.spectral_svd_pca (deferred→VERIFIED). EXACT on PD/indefinite/zero-diagonal/PSD incl. [[0,1],[1,0]]→(1,0,1);
non-symmetric → DECLINE. coverage 94 / **10 VERIFIED** / 84 deferred; test_catalog **19/19**.

**Cycle 2 — mechanism 9 (complete invariant): Petrov.** Weyl scalars [Ψ0..Ψ4] → EXACT Petrov type (complete
invariant of the Weyl tensor's algebraic type), reusing `mathmode.petrov`. Recovers C1.petrov. coverage 94 /
**11 VERIFIED** / 83 deferred; test_catalog **20/20**. (Cartan–Karlhede SPI format pending — next cycle.)

---

## §10 합성 엔진 — 몸통·대가리 (composition body+head)

The catalog stopped being "a skeleton with 3 arms" (M4/M12/M13 only) and became a **composition engine** where
mechanisms CHAIN: one mechanism's output is the next's input, each stage §7-gated, the grade composed by the
weakest-link law. No single-discipline 1:1 decomposition — inputs decompose into mechanism pipelines/trees.

**1. IR — `catalog/ir.py` `StructForm`** (the connective tissue flowing between mechanisms):
`kind | data | residual | grade | cert_chain | path`. `StructForm.raw(x)` starts a composition; `.accumulate(m, v)`
folds a mechanism's Verdict in by the weakest-link law; `.note_step(m, g, k)` records a derived/branch step without
touching the grade; `.to_verdict()` collapses to the §5.6 `(result, grade, cert, bound, mechanism_path)` output and
re-checks the weakest-link invariant. **Signature unification**: `Mechanism.step(StructForm)→StructForm` (in
`mechanisms/base.py`) — every mechanism is now callable in the chain; the per-mechanism `apply` stays the gated,
Verdict-returning core.

**2. `combine_grade` (weakest-link law, `catalog/compose.py`).** Grade lattice DECLINE < PROBABILISTIC < EXACT; a
composition's grade is the MIN (the weakest link). EXACT∘EXACT→EXACT (both certs retained, all re-checked passed);
any PROBABILISTIC→PROBABILISTIC (δ_total ≤ Σδ_i union bound, ε per-op, **never upgraded to EXACT**); a DECLINE
short-circuits (stop=True, downstream NOT run). **No false upgrade**: claiming EXACT over a non-EXACT cert chain
raises an ADT exception at `to_verdict` (test-enforced). Partial success (M_a EXACT + M_b DECLINE) → honest
"structured up to M_a, stuck at M_b" DECLINE, never whole-EXACT.

**3. `plan` (head).** probe[0,1]^14 → a composition-tree SHAPE (not a single max-point): numeric signal → `m7_split`;
classification → `m9_perp_m14`; polynomial inequality → `sos`; bytes → `mdl`; structured QE dict → fused `[2]`; else
the research-grammar `chain` (M10→M14, M6∘M13, M1→M9, …).

**4. `execute` (body).** Walks the plan, threads the `StructForm`, §7-gates every stage (grade ADT enforced at
Verdict construction + cert.passed re-asserted; mechanisms with an oracle do their differential-equivalence recheck
inside `apply`). Returns a `CatalogResult` with the full `(m, grade, cert_kind)` trace.

**Real mechanism chains that RUN:**
- ★ **M7 decomposition** ("무질서 = 구조 + 의사난수", the master principle, executed). `sparse_fft`/`prony` (reused,
  repo-first) split a signal into a k-sparse structure + a remainder. CLEAN k-sparse → EXACT closed form
  `[7→1→12]` (M1 reads the spectrum off M7's certified split; M12 bounds the remainder ≈ machine-ε). Noisy/low-rank
  → HONEST_DEFER (no overclaim). Structureless → DECLINE (no false structure). The remainder, when incompressible,
  hits the Ω(N) floor on THAT part only.
- **M9⟂M14** ("정규형으로 접거나, 장애물을 내놓거나"). M14 (turbulence/E₀) checked in parallel with the M9 complete
  invariant: obstruction fires → DECLINE + obstruction certificate (absence-of-invariant proof); Petrov/Buckingham
  → EXACT classification `[9,14]`; neither → honest DECLINE. (turbulence ownership moved here from the generic
  top-level boundary — it is a classification-specific obstruction.)
- **M4|M14** (SOS or impossibility), **M2(∘M3)** (z3/CAD fuses elimination + finite-witness certification).
- **Wired-but-deferred** (body CALLS the leg, only the heavy compute defers): M10→M14 (forbidden-minor set is
  non-constructive), M6∘M13 (multigrid/RG external). Signatures matched so plugging the leg in just works.

**Measurement (`measure_composition`, NO_UNMEASURED).** M7's genuine advantage is **samples read** — O(k)≈88 prefix
vs O(N) (Amdahl p=0.96 @N=2048): real, complexity-faithful, measured. The Clock-B wall-clock vs numpy's C-FFT is
reported TRUTHFULLY (constant-dominated → no crossover in range = honest "no measured wall-clock win", never a faked
speedup). Build-time is NOT a clock.

**Honesty / passing condition.** Composition grade NEVER falsely upgrades (weakest-link ADT + `combine_grade` only
takes the MIN). Negative controls (random bytes / random signal / unstructured prose) → DECLINE on every path
(false-positive 0). New composition tests in `test_catalog.py`: M7 split correctness, M9⟂M14 obstruction DECLINE,
weakest-link grade enforcement, DECLINE short-circuit path recording, negative controls, IR signature-unification,
measurement. **`test_catalog` 27/27 green; `test_build` 273/273 (purely additive).** 잘못된 답보다 DECLINE이 항상 옳다.

---

## §11 CAPSTONE — 14-mechanism completion + 15-bypass wiring + lossless gate

The empty mechanism applies were completed by WIRING existing repo modules (free wins) and adding bypass
strategies, each §7-gated with a per-instance certificate. **Measured (catalog/capstone_report.py): 12/14 mechanism
applies now run a real gated procedure** — only M6 (renormalize/multigrid, external engine) and M10 (forbidden-minor,
non-constructive Robertson–Seymour) remain honestly deferred.

**PHASE 1 — free wins (repo modules, no external deps):**
- M2 ← `groebner.ideal_member_grade` — Buchberger ideal membership + a re-checkable cofactor witness (q=ΣHᵢfᵢ).
- M8 ← `equality_saturation.optimize` — e-graph confluent normal form, Z3-equivalence-certified (full abstraction).
- M13 ← `ic3_pdr.prove_safety` (k-induction inductive invariant) + `taint_ifds.prove_injection_free` (IFDS fixpoint).
- M11 ← `prony.recover` — exact hidden-recurrence state space (held-out residual ≈ machine-ε ⇒ EXACT, else DECLINE).
- M14 ← `closure_classifier` (Galois insolvability / Liouville non-elementary) — call-site wired; `galois_absence`
  binary absent ⇒ honest DEFER (never a fabricated impossibility).

**PHASE 2 — bypass strategies (pip / pure-python), each independently re-checked:**
- `lstar.py` → M9 — Angluin L* learns the minimal DFA of a regular black-box (complete invariant); EXACT+complete
  when the exhaustive bounded-equivalence depth covers the Myhill–Nerode bound; non-regular ⇒ DECLINE.
- `string_solver.py` → M2 — straight-line/QF_S string constraints via z3's string theory (z3 is an allowed core dep;
  cvc5 was rejected — constitutionally FORBIDDEN big-prover binder). SAT model re-substituted independently.
- `zx_normalize.py` → M8 — ZX-calculus circuit equivalence/normal form via pyzx, re-checked by an exact tensor
  comparison; over-budget / pyzx-absent ⇒ DECLINE.
- `chc_solve.py` → M13 — z3-Spacer SYNTHESIZES an inductive invariant where k-induction returns UNKNOWN; the
  invariant is EXTRACTED and its three Horn conditions are RE-VERIFIED with a fresh solver (EXACT only if that passes).

**PHASE 3 — the ★ lossless judgment gate (`catalog/lossless_gate.py`):** before trusting a translation as a FOLD,
judge it LOSSLESS by one of three per-instance conditions — completeness (ρ∘f==f^♯∘ρ), full abstraction (preserves+
reflects equivalence), machine-verified refinement (re-verified inductive invariant). A PROBABILISTIC (δ-bounded)
result is LOSSY → flagged `approximation`, NEVER folded EXACT (the source-block that makes "fold almost everything"
safe). A composition is lossless iff EVERY stage is (weakest-link for losslessness too). Every `route` result now
carries a `lossless` condition label (M7→completeness, Petrov/L*→full_abstraction, CHC→refinement, …).

**PHASE 4 — heavy bypass call-sites (`catalog/heavy_bypasses.py`):** 8 external bypasses (Metalift verified-lifting,
d-DNNF/c2d, pynauty symmetry, pykoopman, Sepref/CoqEAL data-refinement, SystemDS compressed-domain, MONA/MSO,
OpenFST) wired as call sites with their PRECISE blockers; the body calls them (M11←koopman, M1←nauty) and they
light up the moment the engine is installed — until then an HONEST_DEFER, never a fabricated result.

**Honesty boundary (measured, §10):** false-positive = 0 (random bytes / random signal / unstructured prose →
DECLINE on every path). Still-DECLINE domains are honest: genuinely non-constructive (M10 forbidden-minor), no
runtime engine (M6 multigrid; the 8 heavy bypasses), or a forbidden runtime dep (cvc5/Coq/Lean — only a [BLOCKED]
subprocess). NO uniform-property (RIP) verification; per-instance witnesses only. This does NOT break Ω(N) /
pigeonhole / Skolem≥5 / halting; what grows is the set of inputs routable into a wall-less structure domain, with
a domain label on every coverage number. **test_catalog 32/32; test_build 273/273 (purely additive).**

---

## §D NATIVE ARSENAL — zero-dependency in-repo implementation of all 14 mechanisms + the research tools

ZERO new external dependencies (only z3 + stdlib + numpy + the grandfathered sympy already in source; dependency
audit `forbidden_present == []`). Every fold carries a per-instance, independently re-checked certificate; routed
through `lossless_gate`; false-positive = 0 on the impossible core. **Measured (`catalog/arsenal_report.py`): 14/14
mechanisms run, 19 native cores NATIVE-LIVE, 8 giants fallback+defer.**

**PHASE 0 — completed the 14** (`renormalize.py` M6, `guaranteed_structure.py` M10): exact Markov lumping +
multigrid residual enclosure; Erdős–Szekeres / pigeonhole-cycle / Ramsey R(3,3) constructive extractors. 14/14.

**PHASE 1 — numeric / lattice / sequence cores** (in-repo, exact):
- `native_lattice.py`: LLL (δ=3/4, exact ℚ, unimodular transform verified), integer-relation via LLL (full-precision
  re-check — spurious below precision ⇒ DECLINE), Smith Normal Form + linear Diophantine (substituted back).
- `native_sequence.py`: Berlekamp–Massey over ℚ and GF(2) — **the fake-random vs genuine-random gate** (L≪n/2 fold,
  L≈n/2 DECLINE); GF(2) Gaussian solver; Re-Pair grammar (lossless SLP, incompressible ⇒ DECLINE).
- `native_realroots.py`: Sturm sequence + Descartes/bisection real-root isolation (count-certified intervals).

**PHASE 2 — automata / logic cores** (in-repo; z3 only as an allowed oracle):
- `native_rewrite.py`: Knuth–Bendix completion (shortlex) for the monoid word problem (confluent system re-verified).
- `native_modelcount.py`: exact #SAT via DPLL, cross-checked under two variable orderings + brute force (≤20 vars).
- `native_unify.py`: first-order syntactic unification (occurs-checked MGU, apply-to-both-sides re-check).
- (Presburger is decided via z3, an allowed core dep; Courcelle bounded-treewidth DP — see §C heavy list.)

**PHASE 3 — symbolic** (`native_telescope.py`): Gosper's algorithm for indefinite hypergeometric summation
(antidifference re-verified S(n+1)−S(n)=t(n); non-summable ⇒ DECLINE). The genuinely-enormous symbolic engines
(full Kovacic, full Risch) remain honest-deferred — a wrong symbolic answer is the worst soundness bug, so where
correctness can't be guaranteed the constitutional choice is DECLINE; the existing `closure_classifier` (Liouville)
covers the non-elementary obstruction cases.

**PHASE 4 — decidable islands** (`native_prng.py`, WALL 2): LCG recovery (difference/gcd) + LFSR/xorshift (GF(2)
Berlekamp–Massey), each REPLAY-certified (predict a held-out output exactly). ★ A secure CSPRNG / SHA-256 keystream
has near-maximal linear complexity ⇒ DECLINE on every path — the impossible core does not move. (Linear-loop
termination / Karp–Miller / Pell are covered by the existing ic3_pdr / ordinal / mathmode modules.)

**PHASE 5 — the residual giants** (`catalog/heavy_bypasses.py`, in-repo fallback + honest-defer): Gröbner (native
Buchberger fallback, galactic systems defer), full CAD (native Sturm + z3 nlsat fallback), CAPD-scale rigorous
integration, Walnut Ostrowski-automatic, QCMod quadratic-Chabauty — call sites wired, the residual hard case
honest-deferred with a precise blocker, never a fake pass.

**Honesty (measured §10):** false-positive = 0 (secure CSPRNG / Kolmogorov-random / halting / non-SOS → DECLINE on
every path). A/B DECLINE split separates A-open (movable) from B-core (impossible). Reproducibility: `pillar3/round2`
sketch streams seeded (the int-tuple sketch hashing is already process-stable). **test_catalog 38/38; test_build
273/273 stable. No new dependency.** 잘못된 답보다 DECLINE이 항상 옳다.

---

## §E FRONT-END — probe-cascade detection + verified-lifting translation + Topic A speedups

Two front-ends WIDEN the foldable denominator on top of the complete native engine, plus a constant-factor speedup
path for the remainder — all gated by an EXACT zero-false-positive certifier (proposer→disposer). Zero new
dependencies (z3+stdlib+numpy+sympy; audit `forbidden_present==[]`). **Measured (`catalog/frontend_report.py`):
recall 1.0, ★ PRECISION = 1.0 (zero false positives), lift-rate 1.0, B-core held 10/10.**

**★ Central invariant (proposer–verifier).** Detection (`probe_cascade.py`) and lifting (`lift.py`) are PROPOSERS —
liberal, heuristic. Certification (each native core's exact re-check; `equiv_check.py`'s z3 proof) is the DISPOSER —
EXACT, zero false positives. No transform reaches the fold engine without passing its exact certificate; a wrong
proposal is caught and the input falls through to DECLINE. This is what makes aggressive detection/lifting sound.

**PHASE A/B — probe cascade** (`catalog/probe_cascade.py`, `catalog/detectors_b.py`): cheapest-first detectors,
escalate-on-hit, each gated by an EXACT check in exact arithmetic. Stage 0 compressibility+monobit/runs SCREEN
(incompressible AND random ⇒ immediate DECLINE); 1 Berlekamp–Massey C-finite (ℚ re-substitution) + finite-difference
polynomial law; 2 FFT/autocorrelation → Prony exponential sum (residual gate); 3 integer-relation (LLL) / Re-Pair SLP
(lossless); matrix branch = exact rank-revealing (ℚ dependence certificate). NIST SP800-22 tests double as a
typed structure dispatcher. Reuses the native-arsenal cores. precision = 1.0 on the impossible-core battery.

**PHASE C/D — verified lifting** (`catalog/equiv_check.py`, `catalog/lift.py`): the z3 equivalence substrate
(∀-equivalence UNSAT; inductive sum proof over ℝ so integer division can't block a true polynomial identity; bounded
exhaustive) gates the lifting front-end. An imperative accumulation loop is parsed → its closed form synthesized →
PROVED equivalent by z3 INDUCTION → folded (Σk/Σk²/Σk³/Σ(2k+1)/Σk(k+1) all lifted). A cost gate rejects cold/run-once
code; non-liftable code → honest DECLINE. The lift never folds without a passing equivalence certificate.

**PHASE E — Topic A** (`catalog/topic_a.py`): for code that neither folds nor lifts, a certified CONSTANT-FACTOR
speedup (asymptotics recorded UNCHANGED) — equality saturation (Z3-certified node reduction), translation validation
(an unsound x*2→x+1 is REFUTED with a counterexample), Souper-style superopt — each carrying its equivalence
certificate; none claims an asymptotic improvement.

**Certificate tiers recorded:** z3_forall / z3_induction (strong, re-checkable) vs bounded (domain-limited, labelled).
**Honesty (§10):** false-positive = 0 — secure CSPRNG / Kolmogorov-random / incompressible / halting / full-rank /
non-liftable / unsound-opt → DECLINE on every path. The impossible core does not move. **test_catalog 43/43;
test_build 273/273 (isolated). No new dependency.** 잘못된 답보다 DECLINE이 항상 옳다.

---

## §F PRODUCT-WIDE HARDENING — fast · correct · secure · honest (PHASE 0–9, MEASURED)

The write→verify→fix loop hardened as a product. Three clocks NEVER mixed (A=LLM latency [live BLOCKED: egress],
B=verification, C=fold/native compute); every win states its clock + N; no uniform-Nx; build-time is not a clock.

**PHASE 0 — measure first** (`catalog/product.three_clocks`): A/B/C measured separately (median-of-k), the Amdahl
bottleneck named; Clock-A live latency is honestly BLOCKED (mock used only for attribution, never a fabricated number).

**PHASE 1 — the biggest Clock-A win: a SOUND cache** (`catalog/prodcache.py`, stdlib only): key =
sha256(canonical(exact inputs) + version). A hit is byte-for-byte the cold result (the LLM call / re-verification is
skipped); a mutated input OR a version bump ALWAYS misses — a stale/wrong hit is impossible (test-enforced). The
measured Clock-A reduction on a repeated-request workload is exact (LLM calls avoided), never extrapolated.

**PHASE 2/3 — fewer/cheaper calls** (`catalog/product.py`): difficulty-probe model routing (easy→small / hard→large,
live BLOCKED); first-pass-wins parallel verify; incremental re-verify that PROVES the unchanged part equivalent (z3
translation validation) before skipping it — never a skipped check without its proof.

**PHASE 4/5 — correctness deepened** (`catalog/product.py`): multi-oracle consensus (EXACT only if ≥2 INDEPENDENT
oracles unanimously agree — one oracle's bug can't manufacture a pass; else DECLINE); fix loop with TARGETED feedback
(the concrete failure artifact targets the next attempt) that converges or DECLINEs honestly after N (never ships
unverified code).

**PHASE 6 — API-key security, LEVEL-1** (`provider.py` isolates env; `claude_agent.py` fences `os`): repo-wide grep
proves zero key-shaped literals in product source; `_KEY_STORE` stays None across calls; explicit failure modes +
key-safe exponential backoff — a terminal (auth/bad-request) failure is NEVER retried (a bad key is not transient), a
transient one (rate-limit/network/5xx) backs off 2s,4s,8s,16s; every classified message is key-redacted first.

**PHASE 7 — verified-native backend (Clock C)** (`catalog/native_backend.py`, reuses `egraph_native`+`rust_accel`):
HARAN fold closed form → native i64 LLVM gated by a COMPILATION-CORRECTNESS certificate (z3-certified extraction ∘
Alive2-style translation validation, bit-exact battery — a diverging native output is TRANSLATION_DECLINED, never
emitted); the NTT hot kernel → std-only Rust cdylib gated by a DIFFERENTIAL TEST with N. Amdahl-honest: native is a
constant-factor Clock-C win on the COMPUTE hot-paths — it does NOT speed the Clock-A-bound product, so the rest stays
in the shell (no vanity rewrite). Measured: Σk² emission certified bit-exact; Rust NTT ~15× vs same-algo Python.
asymptotics UNCHANGED. Rust/LLVM deps live in the toolchain, not Python-core imports (zero-dep audit stays []).

**PHASE 8 — UI honest numbers** (`mrjeffrey_landing.html` ↔ `pillar3_studio_data.json`): the landing-page numbers had
silently drifted from the regenerated measured source (hero 112×→re-synced 115×, decline 0.97×→1.00×, all six demo
bars). Re-synced to the committed measured JSON and PINNED by a test — the Amdahl law (ratio ≤ ceiling) is checked on
every row, declines must carry a reason, and a fabricated/drifted UI number is now a test failure.

**PHASE 9 — integrated report** (`catalog/product_report.py`): all of the above MEASURED live, clocks separate,
zero forbidden deps. **test_catalog 49/49; test_build 273/273 (isolated). No new dependency.** A's extreme compute
speed does not move B (LLM-bound) — the two ledgers stay separate. 잘못된 답보다 DECLINE이 항상 옳다.

---

## §G EXTREME ACCELERATION — generated-code speed (A) to its honest limit + product latency (B), MEASURED

A's acceleration is a large **CONSTANT FACTOR**, never asymptotic — general generated code has no foldable
structure (or the fold engine would already collapse it). Each layer carries a CORRECTNESS CERTIFICATE or a
measured benchmark with N; a layer that changes results is reverted; the compounded number is **MEASURED by
running the stacked version**, never the product of per-layer numbers. Clock C (compute) and Clock A (LLM latency)
stay in SEPARATE ledgers — A's extreme compute speed does NOT move the LLM-bound product (B).

**PHASE 0** (`catalog/accel_profile.py`): a generated-code benchmark (readable pure-Python kernels — elementwise
map, associative reduction, AXPY, Horner, AoS field-sum) profiled by median-of-k wall-clock (Clock C), ranked by
wall-share, each tagged with its applicable layer (via `layout_simd` dependence analysis). The PHASE 1–7 ordering
is set by measured addressable share (Amdahl); cold paths (<5%) are documented and left.

**PHASE 1–5** (`catalog/accel.py`) — the certified constant-factor stack, each gated + measured (Clock C):
- **native** (reuse `native_backend`): LLVM closed-form (compilation-correctness / translation-validation) + Rust
  NTT kernel (differential-test N) — measured ~15–18× on the real kernel, ~1× on a trivial closed form (honest).
- **vectorize** (numpy = native-C ⊕ SIMD): dependence-legality (tier A) ∘ differential-equivalence — measured
  kernel-dependent (~6–7× transcendental, ~100–110× BLAS reduction). Unsound vectorization → MISMATCH (rejected);
  non-parallelizable → DECLINED.
- **cores**: independence ∘ differential CERTIFIED (the transferable safety contribution); in-sandbox
  multiprocessing is OVERHEAD-BOUND for marshalled Python data (measured <1×) — reported HONESTLY, never faked.
- **cache_layout**: AoS→SoA, aliasing/consistency certified — measured contiguous-vs-strided ~70–80×.
- **superopt** (reuse `superopt.certified_extract`): z3 / Schwartz–Zippel refinement — modest, honest (op-count).

**PHASE 6** (`accel.pgo_reorder_dispatch`): profile-guided dispatch reordering (measured-common case first);
certificate = differential-equivalence on a mutually-exclusive first-match chain (layout-only). Non-exclusive →
DECLINED. Measured ~2.4×.

**PHASE 7** (`accel_report.gpu_decision`): GPU needs CUDA/ROCm — a forbidden heavy dependency. The constitutional
choice is to DECLINE, not silently import: documented out-of-scope, no GPU runtime imported; numpy is the verified
in-environment data-parallel path.

**PHASE 8** (`catalog/accel_bpath.py`) — the B-path (Clock A): a two-tier cache cuts LLM calls SOUNDLY. Tier 1
exact-hash reuses a VERIFIED result; tier 2 normalized-key offers a SUGGESTION that MUST RE-PASS VERIFICATION
before use (fails ⇒ falls through to a real generation — never ships unverified). Measured Clock-A reduction =
generations avoided, in its OWN ledger.

**PHASE 9** (`catalog/accel_report.py`): the §G report — per-layer measured factors (each certificate-gated), the
compounded stack MEASURED end-to-end (elementwise ~7×, reduction ~110× — explicitly NOT multiplied; numpy fuses
native-C⊕SIMD, multicore excluded as overhead-bound), the Amdahl whole-program bound (a kernel factor is never a
whole-program factor), and the strict A/B ledger separation. **test_catalog 55/55; test_build 273/273 (isolated).
No new dependency** (Rust/LLVM in the toolchain; Python-core audit `forbidden_present == []`). asymptotics
UNCHANGED on every layer — a large measured constant, never asymptotic, never uniform-Nx. 잘못된 답보다 DECLINE이 항상 옳다.
