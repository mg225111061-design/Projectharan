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

---

## §H GAP CLOSURE — folding the 14 fake-unstructured gaps (recover the structure the old probes missed)

Fourteen inputs that have REAL structure the detectors/lifters missed — so they were wrongly judged unstructured and
DECLINEd. Each closed by a STRONGER proposer gated by an EXACT disposer. ★ Precision stays measured at exactly 1.0
(zero false EXACT): nothing folds without passing its exact certificate; a wrong proposal is caught and DECLINEs.
The impossible core (secure-CSPRNG / Kolmogorov-random / general-nonlinear-recurrence / non-holonomic) does not move.

**Detection gaps** (`gap_recur.py`, `gap_signal.py`, `gap_matrix.py`; wired into `probe_cascade`):
- P1 nonlinear recurrence — x[n]=P(x[n-1..n-k]) bounded degree, exact ℚ run-forward gate (decidable island; general→DECLINE).
- P2 matrix/coupled recurrence — v[n]=M·v[n-1], exact ℚ M re-substitution; char-poly the certified driver.
- P3 algebraic relation — polynomial relation among windowed terms via exact rational nullspace (Gröbner-cofactor).
- P4 non-Fourier sparse — k-sparse in Walsh–Hadamard / Haar (exact lossless + sparse support).
- P5 block/Kronecker — Kronecker (Van Loan rearrangement rank-1, exact reconstruction) + block-low-rank (all blocks
  rank-deficient, global full-rank); identity/diagonal correctly DECLINE (no over-trigger).
- P6 piecewise — segment + per-segment BM recurrence (partial fold); whole-one-recurrence / all-random → DECLINE.
- P7 modulated — a[n]=ρ·a[n-P] carrier×period-P, exact ℚ re-synthesis.

**Lift gaps** (`gap_lift.py`):
- P9 relational filter-aggregate → comprehension (differential battery, both forms built from the parse); automata/
  graph/general shapes have no sound in-repo certifier without execution → honest DECLINE.
- P10 affine/geometric loop summary — x=a·x+b / p=p·r → closed form, exact ℚ run-forward.
- P11 aliased a[idx[k]] with affine idx[k]=c·k+d → direct a[c·k+d], rewrite z3-certified (UNSAT); non-affine→DECLINE.
- P12 partial lift — a structured Σ inner loop in glue: lift only the inner loop (z3-induction), glue unchanged.

**Certification gaps**:
- P13 full Zeilberger (`gap_telescope.py`) — holonomic recurrence GUESSED from exact S(n) values, then PROVEN by the
  WZ certificate (t=G(k+1)−G(k) re-checked as an exact polynomial identity — guessing is NOT proof). Σ C(n,k)=2ⁿ and
  Σ C(n,k)²=C(2n,n) certified; non-holonomic 2^(k²) → DECLINE.
- P14 PROBABILISTIC tier (`gap_prob.py`) — δ-bounded structure (P8 quasi-periodic: incommensurate tones fit to a
  measured ε on the samples) graded PROBABILISTIC via `lossless_gate`, NEVER folded EXACT; random → DECLINE.

**§H report** (`gaps_report.py`, MEASURED): 13/13 gaps recover their seeded structure; **PRECISION = 1.0** (zero
false EXACT across all new paths on the impossible core); EXACT ledger residual-0-only (12) vs PROBABILISTIC tier
(1), separated; impossible core untouched (6/6 held DECLINE); zero forbidden deps. **test_catalog 60/60; test_build
273/273 (isolated). No new dependency** (z3+stdlib+numpy+sympy; audit `forbidden_present == []`). The denominator
grows; the floor stays exactly where the mathematics puts it. 잘못된 답보다 DECLINE이 항상 옳다.

---

## §I MECHANISM GROWTH — adding M15–M18 (+scope M19–M20), reopening the classification where closure broke

The closure test overturned "fourteen, closed": rigorous case-by-case analysis showed four-to-six candidates do
NOT faithfully reduce — clustering exactly in the predicted blind spots (relational/asymmetric, multiscale-
topological, local-to-global, dynamic). They are added here as constructive, certificate-bearing fold paths under
the same proposer→EXACT-disposer discipline. ★ Precision stays measured at exactly 1.0 (zero false EXACT across
every new mechanism on the impossible core); the symmetric/static/algebraic CORE of the fourteen stays closed; the
impossible core does not move. The set is now OPEN at ≥17 — a further mechanism to be discovered-or-reduced, never declared.

**M15 persistent homology** (`mech_persistence.py`, no gudhi/ripser): Vietoris–Rips + 𝔽₂ boundary reduction → the
barcode (exact); a 1-Lipschitz bottleneck-stability witness (distinguishes M15 from M9's discontinuity). Signal gate
= normalized persistence ≥0.4·diam; random clouds (only noise bars) DECLINE. Multiparameter (no complete invariant)
is the hard core, never EXACT. → mechanism [15].

**M16 causal recovery** (`mech_causal.py`, no causal libs): do-calculus back-door identifiability relative to a
DECLARED DAG (exact d-separation via the moralized ancestral graph) → the do-free estimand. ★ Faithfulness + the
graph are DECLARED axioms EMITTED in the certificate, never certified from observation (Uhler 2013; Verma–Pearl). A
latent bow arc is non-identifiable ⇒ DECLINE (hedge). → mechanism [16].

**M17 sheaf cohomology** (`mech_sheaf.py`): finite cellular sheaf, coboundary δ⁰ over ℚ, H⁰=global sections /
H¹=graded obstruction. Local data that glues → EXACT global section; else DECLINE with [δs]∈H¹. ★ GENERALIZES M14:
the binary "no global section" is the H⁰-empty special case (M14's certs untouched). → mechanism [17].

**M18 geometric flow** (`mech_flow.py`): Laplacian heat flow → canonical decomposition, certified by a strictly-
MONOTONE Dirichlet-energy Lyapunov witness (the dynamical certificate distinguishing it from M6's algebraic
lumping). Connected structureless graph → trivial consensus ⇒ DECLINE. SOC is the stochastic self-tuning sub-case,
not a new mechanism. → mechanism [18].

**M19 knot/Jones** (scope, `mech_knot.py`): Kauffman-bracket state sum → writhe-normalized Jones (verified: trefoil
= −t⁻⁴+t⁻³+t⁻¹). R-II/R-III invariant by the skein δ=−A²−A⁻², R-I by writhe normalization; NOT a normal form
(non-confluent ≠ M8), NOT complete (≠ M9); #P-hard large diagrams DECLINE on cost. → mechanism [19].

**M20 aperiodic order** (scope, `mech_aperiodic.py`): cut-and-project quasicrystal recognition — two tiles + a
BALANCED (Sturmian) order ⇒ pure-point diffraction. Fibonacci chain folds; periodic / random / unbalanced DECLINE.
Deterministic aperiodic order (≠ M7's structure+noise). → mechanism [20].

**PHASE 21 C7 re-map** (`pass_D.py`): the expander/spectral-gap path corrected from M11 (wrong — not state recovery)
to M4 (λ₂ = the SDP/Rayleigh relaxation of conductance) + M7 (expander-mixing quasirandomness) — a spectral
CERTIFICATE of a combinatorial property. Behavior unchanged; labeling fixed.

**§I report** (`mechanisms_report.py`, MEASURED): all new mechanisms recover their seeded structure; **PRECISION =
1.0** (zero false EXACT on the impossible core: random clouds / latent bow / holonomy / connected blob / random
gaps all DECLINE); EXACT ledger residual-0-only; C7 re-map verified (M4+M7, not M11); closure OPEN at ≥17. **test_catalog
66/66; test_build 273/273 (isolated). No new dependency** (z3+stdlib+numpy+sympy; no TDA/causal/knot libraries; audit
`forbidden_present == []`). The classification is honestly reopened; the floor stays where the mathematics puts it.
잘못된 답보다 DECLINE이 항상 옳다.

---

## §J CONVERGENCE — mechanism-set consolidation to 100%, the final admissible mechanism, the conjectural hard-gate

The three-closure-test program is finished. New-admissible yield collapsed an order of magnitude (~33% → ~20% →
~2%) with no new blind-spot axis in the third round: the set has **converged** to ≈21 named mechanisms near a
finite ceiling of 30–33 (counting the 3 primitives + the registered faces). ★ Precision stays measured at exactly
1.0 across the entire grown set + Conley + the faces + the gate; the impossible core does not move.

**PHASE 1 — 100%-completion audit** (`mechanism_audit.py`): all 20 admitted mechanisms (the original 14 + M15–M20)
RUN real gated code (0 deferred), each emits a re-checkable certificate (kind recorded), records its
decidable-island / hard-core boundary, and DECLINEs its impossible core; C7→M4+M7 confirmed.

**PHASE 2 — the one marginal new mechanism: Conley index (M21)** (`mech_conley.py`): the cubical relative homology
H_*(N,L) of an index pair over 𝔽₂. ★ The honest distinct-vs-forced test: a 1D source and sink share the SAME
static neighborhood N (⇒ identical M15 barcode AND M14 obstruction) yet have DIFFERENT Conley indices (t¹ vs 1) —
the exit set L is set by the DYNAMICS, encoding the Morse/unstable dimension neither M14 nor M15 emits ⇒ **GENUINELY
DISTINCT (M21), net-new = 1**, not a forced M14∘M15 composite. Non-isolating input → DECLINE.

**PHASE 3 — reducible candidates registered as FACES** (`mechanism_faces.py`, NO count++): tropical/(min,+) → M13
(Newton lower-hull subdivision), multifractal f(α) → M4 (Legendre), rate–distortion R(D) → M4/M12 (exact binary
closed form), Feigenbaum δ → M6 (validated-numerics ⇒ PROBABILISTIC, never EXACT), Atiyah–Singer → M9/Chern
(χ = V−E+F characteristic-integral), Boolean-Fourier → M11/M9 (Walsh spectrum + junta), cobordism → M9
(Stiefel–Whitney numbers). Parents ⊆ {4,6,9,11,13}; coverage widens, the count does not.

**PHASE 4 — the conjectural hard-gate** (`conjectural_gate.py`): REJECTS any certificate depending on Hodge /
mirror symmetry / standard conjectures / Iwasawa / BSD or an uncomputable core (general circuit lower bounds /
Wang-tile tiling / general word problem / higher K-theory) — explicit conjectural-dependency DECLINE, never EXACT;
PERMITS the constructive islands (Hodge decomposition, étale of explicit varieties, low-degree K-theory, p-adic
L-values, the hyperbolic/free word problem via Dehn / free reduction). Unknown dependency → fail-safe REJECT.

**PHASE 5 — convergence report** (`convergence_report.py`, MEASURED): ≈21 named mechanisms (Conley DISTINCT); the
yield-collapse record; the **admitted-certificate-kinds list** (14 kinds — the closure criterion: a future
candidate reopens the classification ONLY by emitting a certificate of a kind NOT on the list); PRECISION = 1.0
(zero false EXACT across set + Conley + faces + gate); the conjectural cluster permanently quarantined; the
symmetric/static/algebraic core of the original 14 closed. **test_catalog 71/71; test_build 273/273 (isolated). No
new dependency** (z3+stdlib+numpy+sympy; audit `forbidden_present == []`). The denominator has grown as far as
constructive certificates allow; the floor stays exactly where the mathematics puts it; a further mechanism remains
to be discovered or reduced, never declared. 잘못된 답보다 DECLINE이 항상 옳다.

---

## §K — POST-CONSOLIDATION IMPLEMENTATION (every valid zero-dependency result + the fold-coverage meter)

After the three-test convergence (§J: ≈21 named mechanisms, yield ~33%→~20%→~2%), a fresh candidate ledger was
surveyed under **FOUR ADMISSION GATES** — (1) distinct-in-kind, (2) z3-closed (cert inside z3 theories LIA/LRA/NRA/
EUF/…, no external engine), (3) asymptotic (O(N)→O(polylog), not constant-factor), (4) dependency-free — and EVERY
valid zero-dependency result was implemented as real gated code, the rest demoted TRUTHFULLY. Built in-repo,
zero new dependencies (z3+stdlib+numpy+sympy; audit `forbidden_present == []`).

**PHASE 1 — Tier-1 (6 candidates built; ★1 ADMIT, 4 faces, 1 Group-B).**
- ★ **M22 k-REGULAR SEQUENCE FOLD** (`mech_kregular.py`, Allouche–Shallit) — the ONE genuinely-new fold mechanism.
  A base-k DIGIT-INDEXED linear representation a(n)=v·∏A_{digit}·w built from the k-kernel (in-repo greedy automaton
  closure + exact ℚ linear algebra). Folds popcount, Stern, digit-sums, summatory functions (dim 2–4), O(n)→O(log n).
  ★ DISTINCT: popcount(n) is 2-regular and folds here but is PROVABLY NOT C-finite, so M11/M1/M13 DECLINE it — it
  folds a class no existing mechanism folds. Cert = LIA equalities (z3 spot-check + exact ℚ re-substitution disposer).
  Decidable equality island (Krenn–Shallit); undecidable growth boundary (Skolem/Hilbert-10th) DECLINEs. **Count 21→22.**
- **defective-variable linearization** (`mech_defective.py`) → **FACE of M11**: Carleman monomial-closure of a
  nonlinear loop ⇒ M(sₙ)=Aⁿ·M(s₀), C-finite (M11's class). Passes z3-closed/asymptotic/dep-free, FAILS distinct-in-kind.
- **Tensor-Evolution / Chains-of-Recurrences** (`mech_tev.py`) → **FACE of M13**: CR algebra closes polynomial
  (z3 ∀i finite-difference proof) + geometric loop-index forms; the closed form is M13's kind.
- **AARA amortized potential** (`mech_aara.py`) → **GROUP-B VERIFICATION** (new cert kind `amortized_potential`):
  ∀n-SOUND potential method (z3 ∃Φ∀state + ground re-verify); certifies an amortized BOUND, does NOT fold ⇒ fails
  the asymptotic gate ⇒ not a Group-A mechanism. Dynamic-array amortized 3 (Φ=2·size−cap), binary counter 2 (Φ=ones).
- **semiring-Newton fixpoint** (`mech_seminewton.py`) → **FACE of M13**: tropical (min,+) Newton reaches the least
  fixpoint in ≤n steps (1 for linear: the star-solve) vs Kleene's n; SAME lfp object, cross-checked vs Kleene + exact
  re-substitution. A faster solver, not a new kind.
- **SFA symbolic finite automata** (`mech_sfa.py`) → **FACE of M9**: symbolic bisimulation over LIA guards decides
  language equivalence over an infinite alphabet — a canonical complete-invariant decision (M9's kind); nonlinear
  guards (Hilbert-10th) DECLINE.

**PHASE 2 — adjudicated BY BUILDING (both DEMOTE; M23/M24 NOT admitted).**
- **MPST** (`mech_mpst.py`) → **FACE of M17**: global protocol → endpoint projection + synchronous-product
  deadlock-freedom (in-repo BFS, no external automata). Well-formedness is a LOCAL-TO-GLOBAL gluing (un-projectable
  choice = a gluing obstruction = M17's H¹); deadlock-freedom = an M13 safety witness. No new cert kind.
- **edge-cover / AGM** (`mech_edgecover.py`) → **FACE of M10**: fractional edge-cover ρ* (z3.Optimize LP) + the AGM
  join-size bound (triangle ρ*=3/2 ⇒ N^{3/2}). A structure-FORCED size bound (M10's kind, M4 LP-duality lineage).

**PHASE 3 — 8 TIER-2 FACES + Tier-3 constant-factor + Tier-4 exclusions.** `tier2_faces.py`: monoid-hom→M13,
poset-Möbius→M2, CRN-deficiency-zero→M11, discrete-exterior-calculus (d∘d=0)→M18, restricted-chase→M14,
combinatorial-species→M12, trace-monoid-Foata→M15, twin-width→M10 (each folds + DECLINEs its control). `excluded_
candidates.py`: **Tier-3** (polyhedral/affine, MTBDD, deforestation/optics) routed to the **region-3 acceleration
stack, CONSTANT-FACTOR, asymptotics UNCHANGED — never folds**; **Tier-4** 19 exclusions each with the exact reason
(ZX→M8 face, crypto-accumulator impossible-core, Somos→gap_recur, q-holonomic/umbral→M13, forest-algebra→M9,
point-process/markov-cutoff probabilistic, parametricity/nominal-sets/graded-effects not-a-fold, …).
`mechanism_faces.POST_CONSOL_FACES` (14 = 8 Tier-2 + 6 demotions) registered SEPARATELY from the frozen
consolidation `FACES` (7) so the §J snapshot stays a faithful record.

**PHASE 4 — the FOLD-COVERAGE METER** (`fold_coverage.py`, MEASURED). Runs `POST_CONSOL_PROBE_CORPUS_v1` (30 items)
through the real graders, tabulating the disposition into THREE regions the two speeds NEVER mix: **ASYMPTOTIC FOLD**
(EXACT collapse — raw 0.60 / cost-weighted 0.64), **CONSTANT-FACTOR** (region-3, asymptotics unchanged — 0.10), the
**DECLINE FLOOR** (impossible core — 0.30); 15 mechanisms/faces contribute. The meter DOUBLES as a precision gate
(zero false EXACT) and is self-consistent. ★ Loudly CAVEATED: a curated mechanism-probe corpus, NOT a sample of
production code — it measures the engine's per-region behaviour and mechanism coverage, NOT the prevalence of
foldable structure in general code (frontend/gaps reports put that at a small ~1–3%).

**PHASE 5 — the §K report** (`post_consolidation_report.py`, MEASURED): final count **22** named mechanisms (§J 21 +
★M22); the honest disposition table (1 admit / 14 faces / 1 Group-B / 3 constant-factor / 19 excluded); the
certificate-kinds update (admitted-fold-kinds 14→15 via k-regular; the AARA kind is verification, the MPST/edge-cover
kinds reduce to M17/M10); the continued yield collapse (Tiers 2–4 → 0 new mechanisms); the A/B reclassification; and
**PRECISION = 1.0** across the whole post-consolidation set (the impossible core of every new module DECLINEs).
`test_catalog.py` **81/81**, test_build 273 영향 없음. **No new dependency** (audit `forbidden_present == []`).

The post-consolidation pass admitted exactly ONE new mechanism (k-regular), implemented every other valid result as a
face, routed the constant-factor tail to region-3, and excluded the rest with reasons — the floor stays exactly where
the mathematics puts it; a further mechanism remains to be discovered or reduced, never declared.
잘못된 답보다 DECLINE이 항상 옳다.

---

## §L — VERIFIED PRODUCT-ACCELERATION ENGINE (A/B/C/D to the measured limit)

The fold engine collapses the ~1–3% of code with asymptotic structure (measured by the §K coverage meter). THIS
engine goes after the other ~95% — the code whose wall-clock is I/O wait, serialization, data-structure work, and
allocation — through ONE pipeline: PROFILE first (Amdahl), the LLM/detector PROPOSES, z3 or an exact in-repo oracle
PROVES it semantics-preserving, only the PROVED change is APPLIED, and the WHOLE-PROGRAM wall-clock is MEASURED.
Modules live under `accel/`, never imported by test_build. Zero new deps (audit `forbidden_present == []`).

**★ The central invariant (propose–verify–apply).** `accel/pipeline.py`: an `Acceleration` is APPLIED iff `proved`
is True — a proposal is WORTHLESS until the oracle proves it; no proof ⇒ the slow original stands. `precision()` over
a battery = (applied ∩ unsafe) must be ∅. `profile()` ranks hot paths by MEASURED wall-clock share (the Amdahl gate:
no acceleration off a measured hot path). `amdahl_whole_program()` converts a component factor to an HONEST whole-
program factor (5% sped 10× ⇒ ~1.047×, NEVER the component factor). Three clocks separate: A (proposal), B
(verification, one-time), C (achieved runtime, amortized).

**MOVE A — verified I/O elimination** (`accel/verified_io.py`): A1 caching — an AST EFFECT-ANALYSIS proves PURITY
(output is a deterministic function of explicit args; NO clock/RNG/IO read, NO global read/write, NO argument
mutation; every call provably pure; conservative — any unprovable construct ⇒ NOT pure). A2 batching — independence
(no carried dep) + EXACT result-equivalence. A3 dedup/dead-I/O — redundant (same args ⇒ identical result) / dead
(result never consumed) removed, state-changed & live KEPT.

**MOVE B — verified parallelism** (`accel/verified_parallel.py`, the highest proof bar): B1 async overlap — disjoint
read/write conflict sets (true/anti/output dependence). B2 data parallel — no carried dep, no shared-write race,
reductions only if the combine is proved ASSOCIATIVE + COMMUTATIVE (exhaustive). ★ honest measurement: the proof
unlocks SAFETY, the MEASURED factor decides DEPLOYMENT — the sandbox is overhead-bound (~0.15×, GIL+marshalling),
reported and NOT deployed. B3 deadlock — lock-order acyclicity (a cycle is a refuted bug).

**MOVE C — verified algorithm/data-structure correction** (`accel/verified_algo.py`, the highest ceiling per fix):
C1 complexity reduction (linear-search→hashmap dedup) PROVED result-equivalent over an input battery + measured
**~34–36× O(N²)→O(N)** win on N≈3000 (a real fix, not a fold). C2 loop-invariant hoist / CSE. C3 early-exit
(post-condition stability). A result-changing swap / non-invariant hoist / unsafe early-break (breaking a SUM) is
REJECTED.

**MOVE D — verified serde & allocation** (`accel/verified_serde.py`): D1 serialization fast-path — byte-equivalence
+ lossless round-trip (a field-dropping path REJECTED). D2 allocation reuse — no-aliasing-hazard via alias/escape
analysis on an event trace (a `share → mutate → read` trace REJECTED).

**§6 LIMIT PASS + §7 PRODUCT** (`accel/limit_pass.py`): drives A/B/C/D to exhaustion per hot path and composes the
whole-program speedup via Amdahl, terminating with the HONEST LIMIT — on the modeled target a **36.6× compute fix is
Amdahl-bounded to ~1.48× whole-program** by its 0.30 wall-share, with a **50% IRREDUCIBLE physical-I/O floor**;
"10–20× on everything" is NEVER the output. Product: verified LLM-result caching applies A1 to the LLM step (sound
content-hash key — a stale hit is impossible; a hit SKIPS the LLM), measured 3/6 calls avoided on a repeated-request
workload; MR.JEFFREY wired as the A/B/C/D proposer (untrusted, the engine verifies).

**§8 ADVERSARIAL PRECISION BATTERY + §9 REPORT** (`accel/acceleration_report.py`, MEASURED): across 15 cases where the
"fast" version is deliberately WRONG (impure-as-pure, dropping-batch, dependent-async, non-assoc reduction, cyclic
lock, result-changing swap, unsafe early-exit, lossy serde, aliasing-hazard pool), the engine REJECTS 100% — **PRECISION
= 1.0 (zero unsafe accelerations applied)**, recall 1.0 on the safe ones. The honest scope: the fold engine handles
the ~1–3% with collapsible structure; this engine accelerates measured hot paths where PROVABLE, the compute fix real
but Amdahl-bounded, physical I/O the irreducible floor — neither is "all code fast", both are "what is provable,
proved". `test_catalog.py` **86/86**, test_build 273 영향 없음. No new dependency.

잘못된 답보다 DECLINE이 항상 옳다 — 이제 fold가 아니라 가속에서도: the only thing applied is what was proved, the
limit is the measured limit, never infinity.

---

## §M — VERIFIED GPU KERNELS (HARAN→PTX) + HIDDEN-STRUCTURE FOLD + SOUL-DEEP OPTIMIZATION

Three honest moves; the spine is "dependency ≠ imitation" — we write our OWN kernels (PTX, the public ISA),
depending ONLY on the driver, never on the cuBLAS/cuDNN binaries. Modules under `gpu/` + `soul/`, never imported by
test_build. Zero library deps (no cuBLAS/cuDNN/external BLAS; audit `forbidden_present == []`).

**MOVE 1 — self-built cuBLAS/cuDNN-class kernels (`gpu/ptx_codegen.py`, translation-validated).** GEMM emitted as PTX
text along the public-technique ladder: naive → shared-memory **tiled** → **tensor-core** (`wmma.mma.sync`). ★ THE
EDGE cuBLAS CANNOT GIVE: every kernel is TRANSLATION-VALIDATED — its computation proved EQUAL to reference GEMM,
residual=0 for integer (incl. ragged-K, the tiling-remainder case; integer-sum reassociation is exact ⇒ z3
LIA-closed). A buggy tiling that drops the remainder tile is TRANSLATION_DECLINED, never trusted. ★ HONEST DEVICE
STATUS: no GPU/ptxas in this environment ⇒ PTX is the emitted artifact, the proof is over its modeled semantics + a
CPU reference (never depends on a device), and THROUGHPUT is reported **device-pending** (no fabricated GFLOP/s);
on-device the same kernels assemble via ptxas and throughput is measured as an honest fraction of cuBLAS.

**MOVE 2 — hidden-structure fold on top (`gpu/hidden_structure.py`, the second weapon).** For a matrix that LOOKS
dense, detect + EXACTLY-prove latent structure and collapse where cuBLAS computes the full cube blind: **low-rank**
(exact ℚ factorization M=C·R residual=0 → matvec O(N²)→O(Nr), matmul O(N³)→O(N²r); rank-3 N=24 = 5× op reduction);
**circulant/Toeplitz** (exact pattern → FFT O(N log N) asymptotic op-win); **Kronecker** A⊗B (exact block-consistency
→ vec-trick B·X·Aᵀ). ★ HONEST FRAMING: dense input = TIE cuBLAS + a translation-validation proof (fall through to the
MOVE-1 kernel); structured input = WIN on op-count + a proof — we never make dense matmul faster than cuBLAS.
Precision 1.0: a falsely-proposed rank-r/circulant/Kronecker matrix fails residual=0 and falls through to dense.

**MOVE 3 — soul-deep optimization (`soul/systems.py` + `soul/mobile.py`).** The verified A/B/C/D engine driven to each
domain's provable limit. Systems: locks→verified **lock-free** (a single-location commutative RMW is CAS-retry-order-
independent ⇒ linearizable; a multi-location section is kept locked), allocation→pool, syscalls→batch, data-
structures→correct. Mobile: network→cache/dedup (★ cut the call COUNT, never the RTT — network latency is physics),
render→recompute-elimination, serde→fast-path, battery→dead-computation elimination. Each proved safe; the residuals
named honestly (network RTT, kernel-crossing latency are irreducible floors).

**REPORT + BATTERY** (`gpu/gpu_acceleration_report.py`, MEASURED): MOVE-1 validation + no-BLAS-dep + device-pending
throughput; MOVE-2 op-wins + dense-fallthrough framing; MOVE-3 per-domain provable limits. ★ PRECISION = 1.0 over the
GPU-extended adversarial battery — wrong kernels fail validation, false structure falls through to dense, unsafe
optimizations rejected. Honest scope: "We do NOT beat cuBLAS on dense — we built our own that ties it and proves
itself; we win on op-count where structure exists; we optimize systems/mobile real hot paths to the provable limit;
network RTT and kernel-crossing latency are the irreducible floors." `test_catalog.py` **90/90**, test_build 273
영향 없음. No new dependency. 잘못된 답보다 DECLINE이 항상 옳다 — 이제 GPU에서도.

## §N — FINISH-EVERYTHING (QUIET-MACHINE): PRODUCTION FOLD-COVERAGE + REAL-USAGE TEST OF MR.JEFFREY

The "finish everything pending" pass closed the deterministic-verification debts honestly. T1 confirmed the suite on a
quiet machine (273×3 ALL CLEAN — the earlier perf-gate jitter was load, never a regression); T2 was the §M GPU work.
The two NEW deterministic deliverables are below; T5 (honest UI) follows.

**T3 — fold-coverage on a PRODUCTION-representative corpus (`catalog/fold_coverage_production.py`, MEASURED).** The §K
meter's 0.60 was on a CURATED probe — "how the engine behaves on deliberately-structured code", NOT the real-world
number. This meter runs the real fold/lift engine over a NAMED corpus (`PRODUCTION_BACKEND_CORPUS_v1`, 35 functions in
the shapes of real CRUD-backend code: DB access, string/JSON, dict aggregation, validation, control flow, I/O, crypto)
and partitions into three regions without mixing clocks — **asymptotic fold** (EXACT) vs **constant-factor** (region-3,
asymptotics unchanged) vs **DECLINE floor**. ★ THE HONEST RESULT: production asymptotic-fold ≈ **5.7% raw / 7.25%
cost-weighted** — LOW single digits, exactly the ~1–3% the research always estimated, FAR below the 0.60 probe number,
because most backend code is I/O wait, string/data-structure work and control flow with no foldable asymptotic
structure. The corpus is composed to REPRESENT real code, NOT massaged to inflate — a high number here would be the
lie. Precision 1.0: only the genuine arithmetic-accumulation loops fold; the I/O/crypto/control functions correctly do
NOT. The probe-vs-production gap is stated explicitly in the report.

**T4 — REAL-USAGE TEST of MR.JEFFREY + the honest gap report (`mrjeffrey_gap_report.py`, MEASURED).** Not a summary —
the product was actually DRIVEN on real inputs across its deterministic surface, and what broke was written down and
fixed. ★ WHAT IS LIVE-TESTABLE: the propose half (the LLM writing HARAN from a spec) needs a key + egress, absent here
⇒ Clock-A call latency is **[BLOCKED]** and is NEVER faked (reported only as the spec-size proxy). Everything
downstream — parse → **verify (Clock B)** → **fold/lift (Clock C)** → accelerate — is deterministic and IS exercised
live. ★ WHAT REAL-USAGE TESTING FOUND — TWO GENUINE BUGS, BOTH FIXED: **GAP-1** the verified lifter only matched
two-arg `range(lo, hi)`; the SINGLE-arg `range(n)` form (the single most common accumulation loop) silently DECLINED —
fix: the lo-group of the loop regex is now optional (base defaults to 0), and the z3 inductive-sum proof still gates
correctness, so the ATTEMPT widened but the ACCEPT set did not (`for k in range(n): s += k` now folds to n·(n+1)/2).
**GAP-2** a non-polynomial body (`s += 2**k`) raised an UNCAUGHT `ValueError` from the z3 encoder (2**n is outside the
polynomial substrate) instead of DECLINING — an uncaught crash violates sound-or-DECLINE — fix: the encode/prove step
now catches the out-of-substrate case and DECLINEs honestly (a candidate closed form exists but no in-substrate proof).
Both bugs are guarded by live batteries: the VERIFY battery (6 labeled HARAN programs — every wrong implementation
caught, **0 false VERIFIED**, accuracy 1.0 on a quiet run) and the FOLD battery (real loops — polynomials fold, the
geometric body and the no-loop case DECLINE, **0 crashes**). The Clock-C fold win is measured directly (naive O(n) loop
vs the O(1) closed form, correctness-checked before timing — ~2300× at n=20000, a genuine asymptotic collapse, never a
faster-but-wrong answer). The impact-ranked ledger also records the BLOCKED propose step (GAP-3), the inclusive-Σ
boundary convention (GAP-4, by-design, identical for single/two-arg) and the honest low-single-digit fold ceiling
(GAP-5, by-design, = T3). `test_catalog.py` **92/92**, test_build 273 영향 없음 (lift.py 변경 후 재확인). No new
dependency. 잘못된 답보다 DECLINE이 항상 옳다 — 제품을 실제로 굴려 버그 둘을 찾아 고치고, 막힌 시계와 정직한 천장을 덮지 않고 적었다.

**T5 — honest UI/landing (`mrjeffrey_landing.html` + `mrjeffrey.html`, test-enforced).** The PHASE-8 pass already PINNED
every measured landing number (115× hero, 6 demo bars, 1.00× decline) to the engine source and made a drifted number a
test failure; the main UI already renders per-mode CLOCKS, truthful EXACT/PROBABILISTIC/DECLINE badges, the verifier
work (z3 calls / latency / tier), and an honest STATIC-vs-LIVE split (STATIC runs heuristic detection on the user's own
code, ships ONLY the waste types actually detected, falls to 1.0× when none are found, and labels every row as the
engine's canonical measured result — never a fabricated grade). T5 closed the three honesty gaps that remained:
(1) the PEDAGOGICAL examples in the honesty section (a 700× kernel in 40% of runtime → 1.67×; 3×·20×·6.7× ≠ 400×) were
phrased as if factual — now explicitly LABELLED *illustrative* (the Amdahl one carries its arithmetic
1/(0.6+0.4/700)); (2) the hero **115×** MISATTRIBUTED its source — 115.494 is `csv_stats` (archetype "data utility",
grade PROBABILISTIC), NOT the "never-profiled" app (which is 47×) — the label now names the real source and adds "not
typical"; (3) honest COVERAGE framing was added — a new card states big wins are the MINORITY (most production code is
I/O / control flow with no foldable asymptotic structure, only a low-single-digit fraction folds — = T3), and the 115×
is a SELECTED best case, not a uniform promise. `test_post_consol_task5_honest_ui_landing` enforces all three plus the
main-UI honesty markers; PHASE-8 pinning still holds (23 numbers backed). `test_catalog.py` **93/93**; test_build
unaffected (T5 touches only HTML + test_catalog, neither read by test_build). No new dependency.

## §O — A/B/C/D TO THE LIMIT, COMPOSED TO A FIXPOINT, + THE 550-CASE STRESS TEST

The acceleration engine (§L) proved ONE local transform at a time. §O pushes three of the moves to their reachable
limit, COMPOSES proved transforms to a fixpoint with a single end-to-end guarantee, and stress-tests the whole thing
at scale — with PRECISION as the build gate. Modules `accel/maximal.py` + `accel/stress_550.py`; never imported by
test_build; zero new deps (audit `forbidden_present == []`).

**MAXIMAL A/B/C/D (`accel/maximal.py`).** Each extension widens what is ATTEMPTED without widening what is wrongly
ACCEPTED (applied ⇔ proved). **A.transitive_purity** — the base A1 conservatively rejected any call to a non-builtin;
here we take the whole call graph and prove a function PURE iff it is locally clean (no clock/RNG/IO/global/arg-
mutation) AND every callee is transitively pure, via a monotone fixpoint (cycles resolve soundly) — so a function
calling user-defined pure helpers is now cacheable, while an impure leaf keeps the whole graph impure. **A.nested_batch**
— batch across NESTED loops by proving no carried dependency + result-equivalence of the flattened batched call vs the
nested per-item calls in order (a carried/reordering one DECLINEs). **B.prefetch_overlap** — overlap stage i+1's I/O
with stage i's compute, SAFE iff the next I/O neither writes what the current compute touches nor reads what it writes
(a dependent prefetch DECLINEs); the proof unlocks safety, the latency win is the honest max(io,compute)-vs-(io+compute)
overlap model, never a fabricated number. **compose_to_fixpoint** — apply every proposer to the program repeatedly,
applying each PROVED transform whose end-to-end differential against the current program holds, until a full pass adds
nothing new (the FIXPOINT). The end-to-end equivalence is original ≡ final BY TRANSITIVITY of ≡ (each step is proved
equivalent) AND a differential re-check original-vs-final on samples; a step whose differential disagrees with its
claim is REFUSED (precision first). The demo folds a slow pipeline [dedup O(N²) → square-recompute → sum] to
[dedup O(N) → square-map → sum] in 2 proved steps, fixpoint reached, end-to-end ≡ confirmed.

**THE 550-CASE STRESS TEST (`accel/stress_550.py`, MEASURED).** 500 MIXED cases (a balanced spread across all the
moves: pure/impure cache, transitive pure/impure, independent/carried batch & nested-batch, redundant/none dedup,
disjoint/conflicting async, disjoint/dependent prefetch, safe/unsafe parallel, equivalent/result-changing algo swap,
lossless/lossy serde, hazard-free/hazard alloc) + 50 UNSTRUCTURED impossible-core cases (CSPRNG, true RNG, wall-clock,
real I/O, cyclic-lock deadlocks, order-changing "fast" batches, aliasing hazards). ★ THE BINDING GATE IS PRECISION:
every case whose ground truth is "leave it alone" MUST DECLINE, and a single FALSE APPLY fails the build; all 50
impossible-core cases decline. ★ WE NEVER REPORT 550/550 — that would be the lie, since ~half the corpus SHOULD
decline. The measured honest split: **250 accelerated (every one proved) / 300 correctly declined (incl. all 50
impossible-core); precision 1.0 (zero false applies, zero crashes); recall 1.0 on the genuinely-accelerable subset.**
One honest self-correction during the build: the serde "should-apply" cases initially DECLINED because the reference
encoder stringifies values (int inputs round-trip lossily — the verifier was RIGHT to decline); the fix was to make
the test cases genuinely lossless (string values), matching the "apply" label to reality rather than weakening the
verifier. `test_post_consol_task6_accel_maximal_and_stress550` enforces the maximal apply-safe/decline-unsafe pairs,
the fixpoint + end-to-end equivalence, and the full stress gate. `test_catalog.py` **94/94**; test_build unaffected
(accel/ is never imported by test_build). No new dependency. 잘못된 답보다 DECLINE이 항상 옳다 — 550케이스에서도, 정밀도가
빌드 게이트다.

## §P — DETECTOR RECALL: closing the probe-to-production gap (P0–P6), NOT new mechanisms

The mechanism set is converged at 22 (k-regular was the last; six models + three deep sessions independently reached
"zero new *kinds*"). §P does NOT add a 23rd mechanism — it raises the **fold fraction** by making the proposer
recognize disguised instances of the existing 22, each fold still gated by the SAME exact certifier (precision 1.0).
The proposer becomes liberal; the certifier stays exact; false folds stay structurally impossible. New modules under
`catalog/` (blackbox_fallback, lazy_decline, holonomic_sum, bitvector_ring, mobius_fold, distributed_state,
recall_detect, recall_report); none imported by test_build; zero new deps (`forbidden_present == []`).

**P0 — baseline.** The prior 272/1 was definitively classified a load-flake of the `test_native_s3_triage_layer`
wall-clock perf gate (it fails only when test_build runs right after the heavier test_catalog); isolated from the repo
cwd it is **273×3 ALL CLEAN**. Baseline = 273.

**P1 — black-box fallback (`blackbox_fallback.py`).** When white-box lifting is blinded by REPRESENTATIONAL disguise
(recursion / closure / CPS / object-state / …), recover the structure from the OUTPUT sequence — execute the function
as a pure oracle, recover the minimal linear recurrence with Berlekamp–Massey (reusing native_sequence) + Hankel-rank
corroboration → EXISTING `linear_recurrence` kind. PURITY GUARD (transitive; handles self/mutual recursion + nested
CPS helpers) excludes side-effecting/non-deterministic functions (the distributed-state disguise → P6). DISPOSER: the
recovered recurrence must predict a block of HELD-OUT terms the recovery never saw, EXACTLY — catching the
fit-only-on-window adversary (Fibonacci-then-diverge). **P2 — lazy-decline (`lazy_decline.py`).** Periodic-conditional
(`s+=k%2`) and mod-k state (`s+=k%3`) have C-finite partial sums → black-box → `linear_recurrence` (⑩/⑪); telescoping
(`s+=1/(k(k+1))`) → Gosper rational antidifference → `gosper_antidifference` (⑫), proved by the exact symbolic
telescoping identity (harmonic 1/k → non-summable → DECLINE). **P3 — Zeilberger holonomic-sum face of ⑬
(`holonomic_sum.py`).** Nested 2-variable definite sums Σ_k F(n,k) (binomial / DP-fill) routed to the EXISTING
Zeilberger WZ engine (`gap_telescope`) → `zeilberger_telescoping`; O(N²)→O(N) (measured 20301 vs 201 op-count);
non-holonomic 2^(k²) → DECLINE. **P4 — QF_BV bitvector-ring (`bitvector_ring.py`).** Affine Z_{2^w} loops (LCG /
checksum: x←(a·x+b) mod 2^w) — invisible to both the real-valued lifter and the ℝ-based black-box (Z_{2^w} has
zero-divisors) — folded to the O(log N) matrix-power, proved bit-exact by **z3 QF_BV** ∀x → EXISTING
`verified_modular_recurrence_collapse`; nonlinear/cryptographic bit-mix → DECLINE (the Ω(N) wall). **P5 — Möbius face
of ⑬ (`mobius_fold.py`).** Homographic x←(a·x+b)/(c·x+d) lifted to the projective line, folded to M^N, proved by the
cleared-denominator z3 polynomial identity → EXISTING `matrix_recurrence`; degenerate ad−bc=0 and degree-≥2 (Galois)
→ DECLINE. **P6 — distributed/async state (`distributed_state.py`, hardest).** Cross-function taint reassembles an
affine accumulator spread across event handlers, composes along a FIXED schedule into one round map, folds N rounds
via matrix-power, z3-proves equivalence to the sequential handler semantics → EXISTING `matrix_recurrence`. ★ The hard
honest boundary: NONLINEAR handlers, a NONDETERMINISTIC schedule, and unextractable handlers all DECLINE — most real
async state is outside the provable island, and that DECLINE is correct.

**FINAL — recall report (`recall_report.py`, MEASURED).** Two corpora, honestly: the FIXED PRODUCTION_BACKEND_CORPUS_v1
is **8.6% → 8.6%** under the recall fallbacks (Δ0 — it is genuinely mostly non-foldable I/O / control-flow backend
code; the 5.7%→8.6% rise this session was GAP-1's single-arg-range fix, already in the baseline), while the
DISGUISE_STRUCTURE corpus (production-SHAPED disguised/structured code) goes **0.0 → 0.733** (the real recall gain),
every fold via one of 5 EXISTING certificate kinds. ★ **NO 23rd certificate kind** (routed kinds ⊆ the existing set).
★ **Precision = 1.0** across all priorities — every negative control (Kolmogorov-random, harmonic, nonlinear bit-mix,
non-holonomic) DECLINEs under the augmented detector and the P6 nonlinear/nondeterministic handler sets DECLINE; zero
false folds anywhere. `test_catalog.py` **101/101**, test_build **273×3** isolated (recall modules not imported by
test_build). No new dependency. 잘못된 답보다 DECLINE이 항상 옳다 — 새 메커니즘은 없다, 탐지기가 눈을 뜰 뿐이다.

## §Q — PROVEN I/O OPTIMIZATION: six verified ways to shrink the I/O floor (Ideas 1–6)

Physical I/O latency is NOT reducible — a network round-trip or disk seek is bounded by physics. These six ideas do
ONLY two honest things: cut the COUNT of I/Os (1,2,4,5,6) and overlap the WAIT (3). The unique weapon is PROOF, not a
guess: every caching/prefetch/dedup system in existence guesses (and discards on miss); each idea here applies ONLY
when z3 / an exact oracle PROVES it sound, so it can be AGGRESSIVE where heuristics must be timid. Precision = 1.0
extends to I/O — a wrong cache hit / speculation / kept-stale-entry / false merge is a correctness violation that
FAILS the build. New modules under `accel/`; never imported by test_build; zero new deps (`forbidden_present == []`).
The I/O is modeled deterministically in-repo: the I/O-COUNT reduction is exactly measured, while real wall-clock
latency saved is MODELED-pending-real-deployment (exactly as the GPU throughput was device-pending).

**IDEA 1 — semantic cache-equivalence (`semantic_cache.py`).** z3 proves two differently-spelled requests return the
identical result for all inputs (∀x: A⟺B predicate / A==B value) → share one cache entry for the whole equivalence
class. Near-equivalent-but-unequal (`x>5` vs `x>=5`, `a-b` vs `b-a`) proved DISTINCT and kept separate; z3 unknown →
distinct. Measured: a 6-request stream with semantic dups → 4 I/Os (zero false shares). **IDEA 2 — I/O-pattern fold
(`io_pattern_fold.py`).** When the REQUESTS follow an affine recurrence (`for page: fetch(page)`), prove the closed-
form index set (differential, no missing/extra) + independence → N sequential round-trips collapse to 1 batch
(round-trip COUNT, not transfer). Dependent chains and non-affine patterns DECLINE. **IDEA 3 — proven speculation
(`proven_speculation.py`).** Prove work is independent of the I/O result (disjoint read/write) → overlap it with the
wait — NO rollback (proven, not predicted); or execute a proved-identical branch prefix early. Secretly-dependent /
racing work DECLINEs. Overlaps the wait; never claims the I/O got faster. **IDEA 4 — invalidation-minimization
(`proven_invalidation.py`).** Prove a write's target set is disjoint from a cache entry's read set → KEEP the entry
across the write (avoiding the re-fetch conservative invalidation forces); any overlap → invalidate conservatively
(zero stale-keeps). **IDEA 5 — maximal batching (`maximal_batch.py`).** Prove a set of I/Os transitively pairwise-
independent (across loops/call-chains/nesting) → coalesce ALL into one round-trip; any dependent request stays
separate. **IDEA 6 — content-dedup (`proven_dedup.py`).** Prove two requests deterministic AND byte-identical → merge
into one I/O; byte-differing / non-deterministic (nonce/timestamp) kept separate; semantic-only equivalents route to
Idea 1.

**§7–§9 COMPOSE + Amdahl + battery (`proven_io_report.py`, MEASURED).** All six compose on a modeled I/O-heavy
workload with genuinely-reducible structure + irreducible all-distinct I/O: the I/O COUNT drops **87 → 27 (0.69
reduction)**, shrinking the I/O floor **50% → 15.5%** and lifting whole-program to **1.53×** (honestly Amdahl-bounded
by the 2.0× ceiling; the 20 all-distinct required I/Os do NOT move — on a workload of only those the result is ~1.0×).
★ The adversarial precision battery across all six (near-equiv requests, dependent chains, secretly-dependent
speculation, affecting writes, byte-differing / non-deterministic dedup) is **100% REJECTED — precision = 1.0**, zero
unsound I/O optimizations applied. I/O-count reduction = measured; wall-clock latency = modeled-pending-deployment,
never presented as production. `test_catalog.py` **103/103**, test_build **273×3** isolated (accel/ not imported by
test_build). No new dependency. 잘못된 답보다 DECLINE이 항상 옳다 — 물리적 I/O는 못 빠르게 하지만, 증명된 만큼 덜 한다.

## §R — CONDITIONAL VERIFIED SECURITY: the LLM decides the NEED, the verifier proves the FACT (Phases 1–5)

The principle that makes verified security *usable*: apply it where it is needed, and **nowhere else**. The LLM is
the GATE — it judges, with world-knowledge, whether code is security-sensitive (secrets, PII, auth, crypto, or
untrusted input reaching a sensitive sink). The verifier is the JUDGE — only when the gate says SENSITIVE does the
verified layer turn on and PROVE vulnerability-absence, or flag it honestly. **"Safe" is claimed ONLY when proved; a
wrongly-cleared vuln is a correctness violation that FAILS the build.** When the gate says NOT-SENSITIVE the layer
stays entirely OFF and the code is byte-identical — **zero overhead, measured, not asserted** (applying security where
it is not needed is itself the defect). New modules under `security/`; never imported by test_build; zero new deps
(`forbidden_present == []`). Revives `ct_certifier` (anti-KyberSlash lineage) and points it at general LLM-written code.

**PHASE 1 — the LLM sensitivity gate (`llm_gate.py`).** Asks the focused NEED question (not "is it secure" — that is
the verifier's job). SENSITIVE → layer on for the flagged parts; NOT-SENSITIVE → layer fully OFF; uncertain/malformed
→ conservative SENSITIVE (analysis only, never auto-harden). ★ HONEST CLOCK: LLM egress is BLOCKED here, so the gate
falls back to a conservative STATIC HEURISTIC (secret/PII/auth identifiers, crypto APIs, untrusted→sink flows, and
sinks fed by a dynamically-built string) and labels its verdict **"heuristic — NOT the LLM's world-knowledge
judgment"**, never presenting the fallback as the LLM. **PHASE 2 — logical-vuln verification (`logical_vulns.py`).**
Static (zero runtime overhead) — runs even on NOT-SENSITIVE code as analysis. Each class PROVEN_ABSENT (z3/exact) or
FLAGGED-with-location: bounds (guarded `range(len())` / const index proven; else flagged), injection (parameterized /
constant sink proven; concatenated/f-string sink flagged), integer overflow (**reuses the QF_BV / Int-range proof** —
SAT⇒flag, UNSAT⇒proven), memory (use-after-del / None-deref), race (**reuses the B-engine conflict analysis** —
disjoint read/write ⇒ race-free). **PHASE 3 — side-channel verification (`sidechannel.py`, SENSITIVE only).** The part
no LLM can perceive, on two composing axes: **3A thermodynamic** — constant-time taint proves NO secret-dependent
branch / memory-index / variable-time `/`·`%` (the KyberSlash class) / loop-bound ⇒ CT_PROVEN, else a concrete leak;
**3B statistical** — t-probing security over GF(2): secure ⟺ no t-subset of intermediates spans the secret (the
randoms always leave an unobserved cancel). A timing leak is NOT closeable by masking (needs constant-time); honest
level is **source-IR — binary-level NOT covered** (a compiler may introduce leaks: Binsec/Rel). **PHASE 4 —
conditional hardening (`hardening.py`).** Applies ONLY when (gate SENSITIVE) AND (hardened source CT_PROVEN) AND
(differential-equivalent on every battery input): a secret-branch select → branchless `(a&m)|(b&~m)`, with the
Clock-C latency cost **MEASURED and disclosed honestly**. ★ Gate-BINDING: NOT-SENSITIVE code is never hardened (the
overhead defect); a result-CHANGING fix or one that still leaks is REJECTED.

**PHASE 5 + capstone (`overhead_report.py`, `security_report.py`, MEASURED).** Phase 5 proves the other half of the
thesis: NOT-SENSITIVE code is **byte-identical and runs at native speed** (Clock-C ratio ≈1.0, structural zero
overhead — Phases 3–4 never run), while the SAME layer on SENSITIVE+flagged code DOES harden and pays its measured
cost — overhead where needed, **nowhere else**. The capstone proves the whole contract over a labeled adversarial
corpus and the ONE binding number: **PRECISION = 1.0 ⇔ false-safes == 0** — every KNOWN-VULNERABLE case (SQL-concat,
unguarded index, overflow, use-after-del, data race, secret branch, KyberSlash `%`, broken first-order masking) is
FLAGGED, and NO vulnerable snippet is EVER claimed safe (a false "safe" is a build-failing correctness violation);
recall on the provably-safe cases is reported honestly (1.0 here, but a DECLINE would be honest, never a defect).
`test_catalog.py` **108/108** (+5 §R tests), test_build **273×3** isolated (security/ not imported by test_build). No
new dependency. 잘못된 답보다 DECLINE이 항상 옳다 — LLM이 필요를 정하고 검증기가 사실을 증명한다: 증명된 것만 "안전",
필요 없는 곳엔 오버헤드 0.

## §S — UI REBUILD (SECURED · FAST · ACCURATE): keep the design, gut the dashboard

The product UI (`mrjeffrey.html`) is rebuilt around three words — **SECURED · FAST · ACCURATE** — and nothing else.
The polished design system is REUSED verbatim: the color tokens, the 3D `.slab` cards with their layered shadow stack
and `::before` sheen / `::after` contact shadow, the perspective tilt + `floatIn`/`screenIn` animations, the dark-mode
token set + toggle, the typography (sans/mono, clamp-scaled `h1`, mono-caps eyebrow), the sticky blurred topbar with
the glowing brand dot, `:focus-visible` / `.sr-only` accessibility, and the responsive breakpoints. ★The three accent
palettes are REPURPOSED to the three pillars via the kept `[data-mode]` mechanism: **SECURED → violet** (trust),
**FAST → teal** (speed), **ACCURATE → amber** (precision).

★Every engine internal is REMOVED from the surface — the churning build-time numbers that dated the page instantly:
measured ratios (47×/111×/1.48×), Amdahl ceilings + the `.meter`/`.wall`/`.fill` ceiling visualizations, hotspot
fractions, z3 call counts, latency-ms, the `exact`/`probabilistic`/`decline` grade badges + legend, complexity-sweep
flags, the corpus panel-rows with their `differential PASS` notes, the mode-internals tables (detectors / verifier_tier
/ risk_posture / stop_condition), and the waste-class jargon. The DATA blob now carries ONLY the provider list and the
session-only key policy. The result is shown as three HUMAN outcomes — "주입·경계·메모리 안전을 점검… 민감한 경로는
상수 시간으로 보강" / "이미 효율적입니다 — 바꿀 것 없음" / "같은 결과를 내는지 확인" — each pillar a sentence, the honest
negatives surviving as plain words rather than grade badges, never a fabricated measurement (the static artifact labels
its outcomes a DEMO; the live engine renders the real per-run result, translated to human words). The paste-code +
provider flow is preserved (free-no-card badges, get-key links, session-only key handling), and the one honest
disclosure stays: the API key lives in this tab only — never logged, stored, or sent anywhere but the chosen provider.

The CODE⇄MATH toggle and the MATH screens were retired from this artifact (they were grade-badge UIs, which the new
rules forbid; "Nothing else" — the three-pillar code product is the whole surface). The MATH ENGINE remains server-side
(`mathmode/`) and its backend invariants are still test-enforced; only its UI surface is gone. Self-contained single
HTML artifact (vanilla JS + embedded CSS, no toolchain). The old numeric-pinning UI tests are rewritten to STRUCTURAL
assertions (`test_s_ui_three_pillars` + the updated §B1/§B2 backend tests + the updated TASK-5 UI block): three pillars
present, design system reused, all engine internals absent, provider flow + key-safety preserved. `test_catalog.py`
**109/109**, test_build **273×3** (mrjeffrey.html not imported by the engine; §B1/§B2 now assert the MATH backend, not
UI markers). No new dependency. 화면은 측정값의 벽이 아니라 — 안전하게 · 빠르게 · 정확하게, 세 단어다.

## §U — SWE-BENCH SCORE AMPLIFIER: Opus generates, MR.JEFFREY verifies-filters-repairs (formal-beyond-tests)

Opus 4.8's raw patch generation, wrapped in the proposer–verifier machinery: the model proposes N candidate patches
(some wrong); a LAYERED GATE (build → visible tests → regression → ★formal-beyond-tests) filters to the proven ones;
failures are repaired from their precise failure — richest of all a concrete FORMAL COUNTEREXAMPLE naming the exact
input on which the patch is wrong — and the formally-strongest VERIFIED patch is submitted, never an unverified one
gambled on the hidden suite. New package `swebench/` (never imported by test_build; zero new engine deps,
`forbidden_present == []`); reuses `catalog/equiv_check` (`bounded_equiv` / `prove_equiv_z3` + counterexample),
`claude_agent.claude_generate` (api_key=None → mock = honest BLOCKED), clocks, dependency_audit, KV.

★THE DIFFERENTIATOR (the 90→95 gap). The visible tests are a subset; SWE-bench grades on HIDDEN tests too. A patch
passing every visible test can still be wrong on the edge case a hidden test exercises — a plain test-runner cannot see
this. The formal check proves correctness over the input DOMAIN (`bounded_equiv` over a declared domain — sound over
it — or an unbounded z3 ∀ proof where the behaviour is arithmetic-expressible), and a visible-passing-but-formally-
wrong patch is REJECTED with its counterexample (the hidden-test input), converting "passes the tests I can see" into
"is actually correct" — exactly what passing the hidden tests requires.

★HONEST SCOPE. The real SWE-bench Verified/Pro SCORE is MODELED-PENDING-REAL-STACK — it needs the task repos + their
test runners + a live Opus egress, none available here (Clock A BLOCKED, like the GPU was device-pending); a substrate
number is never presented as the real score. What is REAL and MEASURED is the per-mechanism LADDER on a self-contained
EXECUTABLE mini-benchmark (8 Python tasks: buggy fn + issue + visible + HIDDEN tests + reference oracle + recorded
candidate patches), run on real code execution + real z3. **Measured ladder** (each submission graded against the
hidden tests): opus-alone **0.125** → +multi-candidate **0.25** → +regression **0.375** → +localization **0.5** →
+formal **0.75** → +fix-loop **0.875**, every rung a real marginal lift. ★The differentiator prevents **3** hidden-test
failures (off-by-one `in_range`, wrong-at-0 `sign`, `round_half_up` via the formal-counterexample-driven fix loop) that
the strongest TEST-ONLY pipeline (0.5) would have shipped. ★**Precision = 1.0** on submissions: 7 submitted, 0 false
(every submission formally-verified ⟹ correct on hidden), 1 honest **DECLINE** (`collatz` — no candidate passes and the
in-budget repair stays wrong, so we submit nothing rather than gamble). The unbounded z3 ∀ face proves `abs(x)` for all
x and refutes a wrong candidate with a concrete counterexample. `test_catalog.py` **113/113** (+4 §U), test_build
**273×3** (swebench/ not imported). No new dependency. 잘못된 답보다 DECLINE이 항상 옳다 — Opus는 만들고, MR.JEFFREY는
검증·수리한다; 형식 검증이 보이는 테스트 너머의 hidden 실패를 제출 전에 잡는다 — 그것이 90과 95의 차이.

## §V — FOLD THE ENGINE ITSELF: insane engine speed via sound caching everywhere (cold vs warm, measured)

Turn the fold engine INWARD — the weapon that served thousands of pre-proved obligations at O(1) now folds the
engine's OWN repeated work (detection, verification, fold, proof, AST parse, the LLM prompts) so nothing is computed
twice. New package `enginespeed/` (never imported by test_build; zero new deps, `forbidden_present == []`).

★HONEST SPINE. (1) The LLM's per-call latency is NOT reducible — only the call COUNT is (external provider); when an
LLM call is on the critical path no engine-folding moves the total (Amdahl), so cutting calls is the only honest attack
on LLM latency. (2) The engine's own work IS foldable. (3) COLD vs WARM reported SEPARATELY — a cold cache gives ZERO
speedup (the first run computes everything); the wins are on WARM/repeated work; never a warm number as a first-run
number. (4) Precision 1.0 survives caching — a hit is served only on a sound key (content hash, or a proved α-canonical
form), proved by recompute-equivalence with no collision; a wrong/stale hit FAILS the build.

**PHASE 2 cache** (`cache.py`): L1/L2/L3 multilevel + absence-certificate (cache the proven negatives — a known-miss is
never retried) + JIT-artifact, generalized from the offline pre-proving. Sound keys: `content_key` (sha256, complete by
construction) and `canonical_ast_key` (α-normalized AST — α-equivalent code shares a key, different code does not). LRU
eviction is always safe (only forces a recompute); `prove_key_completeness` proves no collision over a battery.
**PHASE 1 profile** (`profile.py`): rank engine ops by cost×repetition; separate the LLM (Clock A, modeled — egress
BLOCKED) from the engine (Clock B/C, measured). On the modeled workload the LLM dominates wall-clock (~0.998) — the
honest expectation that the response cache (call-count) is the big lever, engine-folding accelerates the rest.
**PHASE 3 folded ops** (`folded_ops.py`): parse / z3-verify / fold / proof-obligation / ★LLM-response, each memoized
behind the sound cache; a pre-folded pattern library serves common shapes at O(1). **PHASE 4 brewing** (`brewing.py`):
idle-time pre-compute + critical-path prefetch — sound (real work early, never speculative-wrong). **PHASE 5–6 + report**
(`speed_report.py`, MEASURED): cold-vs-warm per op (z3 verify **~340–390× warm** on this machine, cold ~0.8ms reported
SEPARATELY) and per mode (FAST/NORMAL/EXTEND each measured cold vs warm, EXTEND attempting 160 ops — deepest); the ★LLM
**call-count reduction** (20 prompts → 3 real calls, **0.85** reduction MEASURED; latency saved MODELED-pending-
deployment — count, not latency); precision **1.0** through caching (no collision, recompute-equivalent, α-equivalent
soundly shares a key). `test_catalog.py` **116/116** (+3 §V), test_build **273×3** (enginespeed/ not imported). No new
dependency. 잘못된 답보다 DECLINE이 항상 옳다 — 이미 한 일은 다시 하지 않는다(증명된 채로): cold은 0, warm이 전부,
LLM은 횟수로만 줄이고, 모든 hit는 precision 1.0.

## §W — FRONTEND COMPLETE: accounts, history, files, progress, errors, many providers — all VERIFIED, key never stored

Make MR.JEFFREY a complete product end-to-end, every feature VERIFIED to function (not assumed), built on the existing
`auth.py` (accounts + sessions + per-account history, with NO api_key column anywhere, by design) and the §S
three-pillar UI. New package `frontend/` (never imported by test_build; zero new deps, `forbidden_present == []`) that
verifies + extends.

★ THE ONE HARD INVARIANT — the API key is NEVER stored. Proved structurally: `schema.sql` has no api_key column,
`auth.py` never writes a key, the history rows carry no key field. The key is re-entered each session, held in the tab,
used once, dropped (claude_agent LEVEL-1). The auth/password path is flagged SENSITIVE by the §R gate ⇒ it gets the
real verified-security layer.

**ACCOUNTS + HISTORY** (verify `auth.py`): signup hashes the password (bcrypt→scrypt, salted) + login authenticates +
wrong/weak password rejected; per-account history persists + reloads + is ISOLATED (account A never sees B); key
re-entered each session (old results shown without it). **FILES** (`files.py`): **59** allow-listed types (source/data/
text/config/notebook), ≤5 at once (6th refused), untrusted-input validated (path-traversal / oversized / unsupported
all refused with a reason), fold-assisted ingestion where structured (cached so a repeat is an O(1) hit). **PROVIDERS**
(`providers.py`): widened to **14** — Anthropic/OpenAI/Gemini/Groq/Mistral/Cohere/DeepSeek/xAI/Together/Fireworks/
OpenRouter/Perplexity + the OpenAI/Anthropic-compatible gateways — each wired (transport/auth-env/model/get-key); key
wiring: valid key → live-call **PENDING-REAL-STACK** (egress BLOCKED, never faked), no key → clear message, unknown →
rejected. **ERRORS** (`errors.py`): every failure (network/timeout/invalid-key/rate-limit/provider/file/backend/auth) a
specific, honest, actionable message — no silent failure, no fabricated success. **PROGRESS** (`progress.py`): the real
pipeline stages (generate/build/tests/regression/security/fold/formal/repair/verify), mode-aware (FAST short, EXTEND
deepest) — not a fake spinner.

**UI** (`mrjeffrey.html`, the §S three-pillar product extended): topbar account login/signup + history view + the
key-never-saved disclosure, multi-file upload (≤5), live progress strip, specific error banner, the 14-provider
registry — all WITHOUT reintroducing any engine internal (the §S discipline holds: no grades/ratios/ceilings).
★ HONEST SCOPE: the live stack (real backend process + real provider calls) is PENDING-REAL-STACK (egress BLOCKED + no
server here) — built correctly, never a faked integration; everything verifiable here (logic, wiring, config, security
paths, key-never-stored) is verified (`feature_report.py`). `test_catalog.py` **117/117** (+1 §W), test_build
**273×3** (frontend/ not imported; auth.py unmodified). No new dependency. 검증된 제품 — 전부 동작 확인, 라이브 통합은
pending-real-stack(가짜 없음), 그리고 무엇을 기억하든 키는 절대 저장 안 함.

## §X — THIRD-PATH FOLD PARADIGMS: raise the fold rate without a 23rd mechanism (widen WHERE the 22 apply)

The mechanism set is converged at 22 (14 certificate kinds). These five paradigms add NO 23rd — they widen the
*opportunity to apply* the existing folds to code that currently DECLINEs (a loop blocked by one dynamic parameter, an
unused output, a linear functional, an array write, a stride). Each is z3-gated; precision stays exactly 1.0; every
paradigm routes to an EXISTING mechanism. New package `thirdpath/` (never imported by test_build; zero deps,
`forbidden_present == []`); reuses `catalog/equiv_check.prove_equiv_z3` (with `assumptions=` carrying the guard).

★ THE TWO HONESTIES (this directive's life). (1) **Certificate-issued ≠ fold-applied**: a conditional fold counts
toward the fold rate ONLY when its condition holds at a real callsite — guards implied / projections live / duals used
/ arrays linear / strides periodic. Issued-but-unused is ZERO contribution (the corpus-swap trick by another name,
forbidden). (2) **Fold-rate ≠ speedup**: an applied fold on a tiny/short loop raises the rate but accelerates nothing.
Both measured and reported SEPARATELY.

**P1 axiomatic/guard** (`axiomatic_fold.py`, the strongest): CEGAR-lite synthesizes a guard Φ under which a declining
loop folds; z3 proves `Φ ⟹ folded==original` (issue) then `callsite ⟹ Φ` (apply); the EXACT verdict gains a `guard`
field — no new kind. **P2 projection** (`projection_fold.py`, safest, fully decidable): fold the live output projection
a callsite uses, `π(folded)==π(original)` proved per-callsite. **P3 dual** (`dual_fold.py`): fold `φ∘f` through a linear
functional (`sum∘reverse==sum`), proved over fixed-size symbolic arrays; non-linear functionals DECLINE. **P4 array/
memory** (`array_fold.py`, the new domain): inductive array writes → a quantified closed-form transition
`∀j. arr'[j]==cf(j)`, z3 ∀-proved with a timeout; off-by-one / nonlinear / aliased DECLINE. **P5 stride** (`stride_fold
.py`, weakest): fold `f^k` when affine+periodic (negation, period-2); gated on an affineness check so a general
nonlinear `f` (s²+1) is DECLINED WITHOUT composing (no degree-2^k explosion).

**COMPOSE + measure** (`fold_paradigms_report.py`, MEASURED): on a paradigm-shaped callsite corpus — **issued 8,
applied 6, speedup 4** (the two honesties separated: 2 issued-but-unapplied; 2 applied-but-no-speedup); on the FIXED
backend corpus the added applied fold rate is **0.0** (generic I/O / CRUD / control-flow code lacks the shapes —
honest, not a flattering frequency claim; the research's 20–30% estimates are unverified); the ~15% ceiling is
unrefuted. ★ Precision **1.0** across all five adversarial batteries (every unsound guard / projection / dual / array /
stride REJECTED); ★ NO new certificate kind (routes to linear_recurrence / matrix_recurrence). `test_catalog.py`
**118/118** (+1 §X), test_build **273×3** (thirdpath/ not imported). No new dependency. 잘못된 답보다 DECLINE이 항상
옳다 — 22가 닿는 곳을 넓힐 뿐 접을 수 있는 것을 넓히지 않고, 적용된 fold만 세고, fold율과 가속을 분리한다.

## §Y — ALTERNATIVE-LENS FOLD: tropical semiring · lattice fixpoint · exact Galois quotient (new axes, no 23rd mechanism)

The 22 mechanisms see structure through standard-field linearity. §Y adds three genuinely-new LENSES, each measuring code
on an axis the 22 miss — **algebra**, **order**, **equivalence-class** — and folding code that DECLINEs under them. No
23rd mechanism: every lens issues the EXISTING EXACT verdict and routes to `linear_recurrence`. New package `altlens/`
(never imported by test_build; zero deps, `forbidden_present == []`); z3-gated end to end. ★ The §X two honesties are
INHERITED: (1) **issued ≠ applied** — a lens fold counts toward the rate ONLY when actually applied at a real callsite;
(2) **fold-rate ≠ speedup** — reported separately.

**LENS 1 — TROPICAL / idempotent semiring** (`tropical_fold.py`, the strongest): max/min/+ loops (DP, Bellman-Ford,
shortest-path, scheduling, bottleneck) are NOT linear over a field — so they DECLINE under the 22 — but over the
idempotent semiring (ℝ∪{−∞}, ⊕=max, ⊗=+) they ARE linear, foldable by the max-plus closed form / tropical matrix power.
The scalar recurrence `x←max(x+c,d)` folds to `max(x0+n·c, d+(n−1)·c)`, **z3 ∀-proved by induction** (base + step, c≥0).
Tropical matrix power by repeated squaring equals the n-fold loop, sound by semiring ASSOCIATIVITY (no per-n proof).
★ THE IEEE-754 HONESTY: the closed form is proved over ℝ/ℤ exactly; for float operands a real-valued max-plus form may
diverge from IEEE-754 accumulation — so the sound fold is restricted to **integer/rational (EXACT)** or **DECLINED for
float** (unless an FPSort proof is supplied, out of scope here); the certificate NAMES the arithmetic model. Never emit a
real-only float fold.

**LENS 4 — BOUNDED LATTICE-HEIGHT FIXPOINT** (`lattice_fold.py`, Knaster–Tarski, the order lens): a MONOTONE update over
a finite-height lattice reaches its fixpoint in ≤h steps (h = lattice height), so n≫h folds O(n)→O(h); for a 64-bit
bitset, h=64 → O(1). Over the bitset lattice ({0,1}^k, ⊆), z3 proves (a) f MONOTONE (x⊑y ⟹ f(x)⊑f(y)), (b) the iterate
chain stabilizes (f extensive x⊑f(x) — ascending — or co-extensive — descending), (c) the height bound f^h==f^{h+1}.
★ The trap: monotonicity must be PROVED, not assumed — a single non-monotone op (−, ~, a data-dependent branch) breaks it
and MUST DECLINE.

**LENS 5 — EXACT SEMANTIC QUOTIENT via GALOIS connection** (`galois_fold.py`, the equivalence-class lens): a computation
EXACTLY encoded by a small finite abstract domain D (α: Concrete↠D) cycles within |D| states (pigeonhole), folding
O(n)→O(|D|)≈O(1). Canonical domain ℤ/mℤ under an affine map x←a·x+b. z3 proves the abstraction is **EXACT** — the diagram
commutes, `∀x. α(f(x)) == f#(α(x))`. ★ Only the exact quotient folds; an over-approximation (α(f(x)) ⊒ f#(α(x)) — the
abstract result is a SET not a point, e.g. sign-of-x−1: α(+)∈{+,0}) would be UNSOUND ⇒ DECLINE. ★ A |D|-blowup (large
modulus) ⇒ no speedup ⇒ DECLINE. ★ The power-of-two-modulus overlap with QF_BV (`x mod 2^k == x & (2^k−1)`, already
folded by the existing bitvector machinery) is **SUBTRACTED** — declined here so the lens's added fold rate is not
double-counted.

**COMPOSE + measure** (`altlens_report.py`, MEASURED): on a lens-shaped callsite corpus — **issued 7, applied 6,
speedup 5** (the two honesties separated: 1 issued-but-unapplied = the float tropical callsite honestly NOT applied).
Per-lens attribution: **tropical LARGEST** (3 applied — max/min/+ loops are common), lattice and galois SMALL (the honest
shape). The directive's per-lens estimates (~+1.0 / +0.3 / +0.5 percentage points) are for lens-SHAPED code; on the FIXED
PRODUCTION_BACKEND_CORPUS_v1 (the 5.7% baseline) the added APPLIED fold rate is **~0** — generic backend I/O/CRUD/
control-flow rarely contains a hot exact-arithmetic max-plus recurrence, a monotone finite-lattice loop, or an exact
non-power-of-two modular orbit (honest, not a flattering frequency claim). The pigeonhole wall is absolute — none folds
the truly random; the ~15% ceiling is unrefuted (these lenses widen the reachable structure, they do not break the wall).
★ Precision **1.0** across all three adversarial batteries (every c<0 / float / non-monotone / over-approx / |D|-blowup /
QF_BV-overlap case REJECTED); ★ NO new certificate kind (22 mechanisms / 14 kinds unchanged; routes to
linear_recurrence). `test_catalog.py` **121/121** (+3 §Y, one per lens), test_build **273×3** (altlens/ not imported). No
new dependency. 잘못된 답보다 DECLINE이 항상 옳다 — 세 렌즈는 22가 못 보는 구조를 새 축에서 볼 뿐, 접을 수 없는 것을
접지 않는다; float 열대는 DECLINE, 갈루아↔QF_BV 중복은 차감, 적용된 fold만 세고 가속과 분리한다.

## §Z — THREE NEW FOLD LENSES: generating-function · sliding-window · projective(Möbius) (one is HONESTLY a reuse)

Three more sights the 22 cannot see — a convolution that is secretly a product, a window that need not be re-summed, a
fraction that is secretly a matrix — each z3-gated, precision exactly 1.0, inheriting the §X/§Y honesties (a fold counts
only when APPLIED; fold rate reported SEPARATELY from speedup; the IEEE-754-vs-real caveat stated). New package
`newlens/` (never imported by test_build; zero deps, `forbidden_present == []`).

**LENS A — GENERATING-FUNCTION / formal-power-series** (`genfunc_fold.py`, small but genuinely new): a nonlinear
self-convolution DP (`dp[n]=Σ dp[i]·dp[n-1-i]` Catalan; Motzkin) DECLINEs under the 22 as nonlinear, but as a power
series the convolution is a PRODUCT, so the recurrence becomes an algebraic equation (D=xD²+1) with an exact closed form
(C(2n,n)/(n+1)) folding O(N²)→O(1)/O(log N). z3 (Int theory) proves the closed form == DP ∀n≤bound (the recurrence +
base uniquely determine the array). New algebra (⑬ Faulhaber/Gosper/Zeilberger handles only LINEAR sums); reuses the
existing closed-form evaluator (`fastkernels.catalan`); routes to closed_form. ★ IEEE-754 honesty: exact over
integer/rational; the general FFT product is float and NOT a precision-1.0 fold — exact only under an integer/NTT
discrete model (an O(N²)→O(N log N) complexity SUBSTITUTION, not an O(N)→O(1) fold), float FFT DECLINED.

**LENS B — SLIDING-WINDOW AGGREGATION** (`window_fold.py`, the LARGEST contributor — the most practical): a loop that
re-aggregates a whole window each step is O(N·W); the invariant `acc==aggregate(window)` folds it to O(1)/step. Invertible
sum (integer/exact group) via `acc=acc−oldest+newest` — itself a linear recurrence on the accumulator, routes to ⑩
linear_recurrence, the invariant z3 ∀-proved. min/max via a monotone deque (amortized O(1)/step) — returns an actual
window element, EXACT by construction, float-safe (no subtraction). ★ The float-cancellation trap: float SUM has
`acc−oldest+newest ≠ recomputed` (catastrophic cancellation breaks the invariant) — DECLINED, with a concrete witness
(window [1e16,1,1] slides to incremental 1.0 vs true 3.0). integer product DECLINED (ℤ not a group under ×); mode/median
DECLINED. New incremental-aggregation pattern; issues the existing EXACT verdict (no new algebraic kind).

**LENS C — PROJECTIVE / MÖBIUS** (`mobius_fold.py`, ★ HONESTLY a REUSE — ZERO new): a fractional recurrence
x←(a·x+b)/(c·x+d) folds via the ℙ¹ lift to Mᴺ in O(log N). ★ THE HONEST FINDING: this is the IDENTICAL construction
already shipped as `catalog/mobius_fold.py` (§P P5 — same PGL₂ lift, same Mᴺ fold, same z3 cleared-denominator identity,
same matrix_recurrence kind, same ad−bc=0/pole guards). The directive's no-overlap check named QF_BV/Galois/stride, but
the real overlap is against our OWN prior work. So LENS C is NOT new: we REUSE §P P5 (no duplication) and count its
projective fold as ZERO new fold-rate contribution (`new_contribution` always False) — the no-double-count honesty the
spine demands. The only §Z-added value: an explicit orbit nonzero-denominator guard for a given x₀ (exact-rational;
DECLINE if c·xₙ+d=0 is hit — §P alone marks the pole an island) + the float IEEE-754 caveat (DECLINE float).

**COMPOSE + measure** (`newlens_report.py`, MEASURED): on a lens-shaped corpus — **issued 7, applied 7, applied_NEW 6,
speedup 6**. ★ applied (7) > applied_NEW (6): the Möbius callsite is applied & valid but contributes ZERO new (already
counted in §P P5) — `applied_NEW` excludes it, eliminating the only double-count risk. ★ fold-rate (7) > speedup (6): a
short window is rate-only. Per-lens: **B_window LARGEST** (4 applied-new), A_genfunc small (2), C_mobius ZERO new.
★ No-overlap VERIFIED: genfunc (algebraic GF) and window (incremental aggregation) are DISJOINT from QF_BV (bitvector
ring) / Galois (modular quotient) / stride (group action); Möbius overlaps only our own §P P5 (zeroed). ★ Precision
**1.0** across all three batteries (wrong closed form / float FFT / float-sum cancellation / non-invertible / zero-denom
orbit / float Möbius / degenerate REJECTED); ★ NO new certificate kind (22 mechanisms / 14 kinds unchanged; routes to
closed_form / linear_recurrence / matrix_recurrence + the min/max incremental_pattern EXACT verdict). `test_catalog.py`
**124/124** (+3 §Z), test_build **273×3** (newlens/ not imported). No new dependency. 잘못된 답보다 DECLINE이 항상 옳다 —
합성곱은 곱, 창은 다시 더할 필요 없는 불변식, 분수는 행렬; Möbius는 우리 §P P5라 새 기여 0(이중계산 금지), float은 DECLINE,
적용된 fold만 세고 가속과 분리한다.

## §AA — FIVE FOLD-RATE WEAPONS: not new structure to recognize, but better EXTRACTION of structure already there

Fold rate = (recognizable structure) × (ability to surface it). Every prior directive grew the first factor toward its
~15% ceiling; these five grow the SECOND. ★ All five are LLM-FREE, z3-verified, deterministic — they touch the compiler's
structural machinery, not the proposer's intelligence, so they work identically with a weak LLM (the binding design
constraint, verified structurally via AST in the report: no foldrate module imports an LLM client). New package
`foldrate/` (never imported by test_build; zero deps, `forbidden_present == []`). No new certificate kind.

**WEAPON 1 — CANONICALIZATION** (`canonicalize.py`, the MULTIPLIER, built first): the same foldable structure is written
many ways (`i*2` vs `2*i`, `(x+1)*(x-1)` vs `x*x-1`); a brittle pattern-matcher misses the variants. A semantics-preserving
normal form BEFORE fold lifts EVERY lens/mechanism's hit rate AT ONCE. Proposer–disposer: sympy proposes the normal form
(expand + AC-order), z3 DISPOSES (`prove_equiv_z3` proves ∀ inputs original==canonical); an unprovable rewrite is REJECTED
(original kept). ★ Float non-associativity respected — algebraic reassociation is integer/rational only; float DECLINED.
Measured BEFORE/AFTER on the same corpus: **1→8 hits = 8.0× multiplier** (the float item correctly NOT rewritten, honesty
visible). A multiplier across all detectors, not an addition to one.

**WEAPON 2 — LENS COMPOSITION** (`compose.py`): chain lenses so one transform exposes structure another folds —
canonicalize rewrites a variant summand to the canonical `2*i` that Faulhaber folds, where Faulhaber alone DECLINED the
variant. Each link proved; the FINAL fold z3-proved against the ORIGINAL (canon proved + Faulhaber closed form z3-proved
by induction). ★ Additive-with-overlap, NEVER multiplicative: on a 7-item corpus, **3 single-lens + 4 composition-only =
7 composed** (the lift is composition-only, overlap subtracted; composed_rate ≤ single+lift, a union not a product) — no
"30–50%" overclaim.

**WEAPON 3 — SPECULATIVE/CONDITIONAL FOLD** (`speculative.py`, full §X-P1): guard the one dynamic parameter, emit dual-path
(folded under Φ + original fallback), check Φ at RUNTIME. ★ The fallback invariant (verified): correctness NEVER depends on
the guard — a guard-miss runs the original (correct, slower); only SPEED depends on Φ (dispatch k=4→folded 20, k=9→fallback
45, both correct). ★ Runtime-information, not the LLM (the honest Maxwell's-demon — the runtime is the observer); structured
inputs only — a genuinely input-dependent computation gets NO sound guard ⇒ DECLINE (pigeonhole). issued ≠ applied. Uses
§X-P1's guard field — no new kind.

**WEAPON 4 — MEMOIZATION CACHE** (`foldcache.py`, §V extension): the same fold proved once, served O(1) — fold results,
proof obligations, canonical forms. ★ Sound keys (`canonical_ast_key` α-normalized hash, or `content_key`): a wrong hit is
impossible (different code ⇒ different key); α-equivalent code shares soundly. ★ Cold-vs-warm separated: cold **1 compute**,
warm **0 recomputes** (0.99 hit-rate) — raises VALUE/throughput, NOT the fold rate (the §V honesty, stated).

**WEAPON 5 — DOMAIN-IDIOM LIBRARY** (`domain_idioms.py`): register recurring idioms — prefix-sum (numeric), sum-of-squares
(statistical), running accumulator, power-of-two normalization (ml_preproc) — each mapped to an EXISTING mechanism and
z3-PROVED sound (a syntactic-but-unsound idiom, `x*3==x<<3`, REJECTED). ★ Corpus honesty: a domain idiom lifts the DOMAIN
rate (**0.571** measured) NOT the backend 5.7% (**0.125**, the one rare idiom) — reported SEPARATELY, no corpus-swap.

**COMPOSE + measure** (`foldrate_report.py`, MEASURED): the headline is a DECOMPOSITION, never one inflated number — W1
multiplier (8.0×, before/after), W2 additive lift (4, overlap subtracted), W3 issued≠applied + fallback-invariant + runtime-
not-LLM, W4 cold-vs-warm (value not rate), W5 domain-vs-backend (no corpus-swap); plus a shared baseline→canonicalized→full
decomposition (0.43→1.0→1.0 on the demo corpus — canonicalization the dominant extraction lever). ★ LLM-free VERIFIED
structurally (AST: no LLM import in any weapon). ★ Precision **1.0** across all five adversarial batteries; NO new certificate
kind (22 mechanisms / 14 kinds unchanged); the pigeonhole wall stands (none folds random); float non-associativity respected.
`test_catalog.py` **129/129** (+5 §AA), test_build **273×3** (foldrate/ not imported). No new dependency. 잘못된 답보다
DECLINE이 항상 옳다 — 인식이 아니라 추출을 키운다; 정규화는 곱셈기, 합성은 가산, 추측은 런타임-가드(LLM 아님), 캐시는
value-not-rate, 도메인 관용구는 도메인율, 전부 LLM-free·새 인증서 종류 0.

## §AB — ALL FOLD-RATE AXES: certified-approximate · probabilistic · unit-redefinition · bypass (the grand decomposition)

§AB attacks the two axes never touched: what EARNS the right to be counted as a fold, and what UNIT we measure. The
headline is a DECOMPOSITION — four distinct categories, four numbers, NEVER one inflated total. New package `foldaxes/`
(never imported by test_build; zero deps, `forbidden_present == []`). ★ The shared KV ADT is left UNTOUCHED (the 273 is
safe) — the new grade reuses the EXISTING APPROX_FOLD.

**★ THE LINE THAT KEEPS US NOT AN LLM:** an LLM also approximates. A plain "usually close" would make us the thing we
replace. OURS carries a machine-PROVEN worst-case bound holding on EVERY input, on the first run and the 10¹⁶-th —
`∀ inputs. |folded − original| ≤ ε`, a THEOREM, never a sample. Sampling/averaging/empirical-testing is REJECTED.

**AXIS 1 — CERTIFIED Approximate Fold** (`approx_fold.py`, the largest, identity-critical): float code that DECLINEs under
EXACT folds to a closed form within a UNIVERSALLY-proven ε. ★ REUSES the existing APPROX_FOLD grade (`disposition.py`/
`approx_cert.py`, never-exact R3.5) and ADDS the new interval-certified-ε method: an `ErrorInterval` carries a value range
+ accumulated absolute roundoff (each float op adds ≤ u·|magnitude|, u=2⁻⁵³), propagated over the WHOLE domain ⇒ ε a
rigorous over-approximation (true error ≤ ε on EVERY input). The float loop Σⁿc → n*c with ε=5.57e-8 ∀|c|≤1000. ★ A
SAMPLED ε UNDER-estimates (sampled 0.0 < certified 5.57e-8 — misses unseen inputs) and is REJECTED — the anti-LLM line.

**AXIS 2 — PROBABILISTIC Fold in earnest** (`probabilistic_fold.py`): correct w.p. ≥ 1−2⁻ᵏ via a DERIVED bound. REUSES
`fast_certificates.py` (Freivalds 2⁻ᵏ, Schwartz-Zippel (deg/|S|)^rounds) + KV.PROBABILISTIC. ★ Distinct from AXIS 1 — the
randomness is in the CHECK (over the algorithm's coins), the input can be anything; AXIS 1's ε is over all inputs. The
bound is DERIVED (Freivalds 5.96e-8, SZ 6.5e-55), NEVER empirical; a wrong product DECLINES, random INPUT is not folded,
never presented as certainty.

**AXIS 3 — FOLD-UNIT Redefinition** (`fold_units.py`): structure folds at the EXPRESSION ((x+1)(x-1)−x²≡−1), FUNCTION
(two summation loops → n(n+1)), and call-graph REGION (composed affine accumulators → one transition) units, each
z3-proved. ★ THE DENOMINATOR HONESTY: folds/loop, folds/expr, folds/func, folds/region are DIFFERENT numbers with
DIFFERENT denominators (0.6 / 0.33 / 0.25 / 0.2 measured) — DISTINCT, the unit always stated, NEVER merged.

**AXIS 4 — FOLD BYPASS** (`bypass.py`): for a finite/small/deterministic space, precompute the whole input→output map
once, O(1) lookup. ★ NOT a fold — VALUE/throughput, reported SEPARATELY, never counted in any fold rate; cold (256 fn
calls) vs warm (0) stated; an 8-bit space bypasses, a 32-bit space is DECLINED (> 2⁻¹⁶ cap — caching unbounded is Ω(N)
noise); a wrong lookup is impossible (deterministic table).

**COMPOSE + measure** (`foldaxes_report.py`, MEASURED): the grand decomposition — EXACT (1.0 precision, undiluted) +
APPROX-ε (ε a universal interval theorem) + PROBABILISTIC (derived 2⁻ᵏ), at loop/expr/func/region units, with bypass as a
separate throughput lever — FOUR numbers, never summed. ★ The anti-LLM audit (the section proving we are not an LLM):
every APPROX-ε bound is interval-PROVEN over the whole domain (sampled-ε rejected), every PROBABILISTIC bound is DERIVED
(never empirical). ★ The measured real ceiling: the remainder is the principled-impossible (genuine I/O / randomness /
data-dependent control) — the pigeonhole/physics wall stands. EXACT undiluted; KV ADT untouched; LLM-free (AST-verified);
precision 1.0 / the proven bound across all four batteries. `test_catalog.py` **134/134** (+5 §AB), test_build **273×3**
(foldaxes/ not imported). No new dependency. 잘못된 답보다 DECLINE이 항상 옳다 — LLM도 근사한다; 우리 근사는 정리지 표본이
아니다(∀입력 ε 증명); 네 등급 네 숫자(EXACT·APPROX-ε·PROBABILISTIC·bypass), 단위별 분모 분리, 합산 없음, KV 불변(273 안전).

## §AC — INPUT-AWARE & DEPTH-VARYING FOLDS: profile · spec · partial · asymptotic · recursive (the scoped decomposition)

Every prior directive folded blind to the input. §AC breaks that two ways — we MEASURE the input distribution (profile)
or the user DECLARES it (HARAN `requires`) — and varies the fold's DEPTH three ways (part of a loop; the asymptotic order;
recursively to a fixpoint). All z3-verified where they claim soundness, all LLM-free, all honest about scope. New package
`inputfold/` (never imported by test_build; zero deps, `forbidden_present == []`). No new certificate kind.

**FOLD 1 — PROFILE-GUIDED** (`profile_fold.py`): a measured profile SELECTS which guard lands (turning synthesis into
data-driven selection); REUSES §AA-W3/§X-P1 (the proof Φ⟹folded==original is unchanged — the profile only chooses Φ).
★ THE FALLBACK INVARIANT (binding, verified): correctness NEVER depends on the profile — a guard-miss runs the ORIGINAL
(correct, slower); even a 100%-wrong profile keeps every answer right, only speed drops. Measured: 90 folded / 10 fallback
under a matching workload (hit-rate 0.9, all correct). ★ Scope: "under measured workload W," never universal.

**FOLD 2 — SPEC-DECLARED** (`spec_fold.py`): fold under a user-declared HARAN `requires` precondition P, `P⟹folded==
original` z3-proved (`prove_equiv_z3` assumptions=P) — zero synthesis cost, 100% hit where P holds (abs(x)→x UNDER
`requires x≥0`, not an identity without P). ★ The declaration's truth is RUNTIME-CHECKED (P false ⇒ DECLINE-at-runtime,
run the original — correct) OR the DECLARER'S RESPONSIBILITY (a contract); the mode is STATED, a silent assumption REJECTED.
Perfect HARAN fit (`requires` as an acceleration contract).

**FOLD 3 — PARTIAL** (`partial_fold.py`): fold the foldable SLICE of a whole-loop DECLINE, leave the residual
(`for i: s+=c; io_write` → fold the accumulation, keep the I/O); prove slice==original-slice AND slicing-preserves-
semantics (the slice independent of the residual — a residual that READS the accumulator mid-loop is REJECTED). ★ THE
DENOMINATOR HONESTY: reported at a STATEMENT-LEVEL/fraction rate (1 of 2 = 0.5), DISTINCT from whole-loop, never merged.

**FOLD 4 — ASYMPTOTIC-ONLY** (`asymptotic_fold.py`): reduce the ORDER, not the constant — prefix-sum O(N²)→O(N) z3-proved
EXACT, naive convolution O(N²)→O(N log N) (EXACT under integer/NTT, APPROX-ε for float per §AB, never EXACT), linear scan
O(N)→O(log N) under sortedness (composes with F2). ★ Reported as an ORDER-reduction rate, DISTINCT from closed-form
(O(N)→O(1)), before/after order stated.

**FOLD 5 — RECURSIVE** (`recursive_fold.py`): fold→simplify→re-fold to a FIXPOINT ([5,−5,7,−7] cancels [5,−5] which
EXPOSES [7,−7] → [] in 2 iterations). ★ TERMINATION: a well-founded progress measure (term count) that STRICTLY decreases
each iteration + a cap backstop. Each link proved; final z3-proved against the ORIGINAL (cancellation is value-preserving,
∀x. x+(−x)==0). ★ Additive-not-multiplicative (per §AA-W2): the recursive lift = folds caught ONLY by iterating (fixpoint
2 − single-pass 1 = 1), never a multiplicative claim.

**COMPOSE + measure** (`inputfold_report.py`, MEASURED): the SCOPED decomposition — baseline → +profile-under-W →
+spec-under-`requires` → +partial-statement-level → +asymptotic-order → +recursive-additive, each labeled by its scope and
denominator, NEVER one inflated total. ★ The fallback audit (every profile fold has a sound fallback), the HARAN-fit note
(`requires` as contract, mode stated), the denominator audit (partial statement-level, asymptotic order-reduction —
distinct from closed-form). The measured real ceiling: the remainder under the actual workload is genuine I/O / randomness
/ data-dependent control (the pigeonhole wall stands). LLM-free (AST-verified); precision **1.0** / the stated grade across
all five batteries; no new certificate kind. `test_catalog.py` **139/139** (+5 §AC), test_build **273×3** (inputfold/ not
imported). No new dependency. 잘못된 답보다 DECLINE이 항상 옳다 — 입력을 측정하거나 선언받고, fold 깊이를 부분·차수·고정점으로
변주한다; 프로파일은 정확성 불침범, spec은 P 하에서만, 부분은 문장단위, 점근은 차수, 재귀는 가산; 범위 항상 명시, 합산 없음.

## §AD — EIGHT STRUCTURE-EXISTS-BUT-UNFOLDED GAPS: finish the machine (real structure the detector missed)

Not new structures or new ways to count — eight EXACT HOLES where established-math structure genuinely exists but our
detector/closed-form machinery wasn't built. These are CURRENTLY-unfoldable (a missing detector), NOT principled-impossible
(genuine I/O / randomness / data-dependent control — forever-unfoldable). New package `gapfold/` (never imported by
test_build; zero deps, sympy grandfathered for GAP 5; `forbidden_present == []`). No new certificate kind (22 mech / 14
kinds unchanged); LLM-free (AST-verified).

**GAP 1 — multi-way mutual recursion** (`mutual_recursion.py`): k≥3 entangled linear recurrences → one k×k companion
matrix → matrix power O(N)→O(log N) (we folded 2-way; missed k≥3 from a detection gap). Sound by the companion
homomorphism (associativity) + a differential extraction check; nonlinear rejected. **GAP 2 — divide-and-conquer**
(`divide_conquer.py`): T(n)=a·T(n/b)+f(n) → Master theorem / Akra-Bazzi (merge-sort Θ(n log n), Karatsuba Θ(n^1.585),
binary search Θ(log n)); ASYMPTOTIC-ORDER (per §AC-F4), order-not-value honesty; non-Master rejected. **GAP 3 — deep
nested sums** (`nested_sums.py`): ΣᵢΣⱼ i·j → (Σi)(Σj), triple → (Σi)³ via multivariate Faulhaber (one-var power sums z3
∀-proved, separable product), EXACT O(Nᵏ)→O(1); non-polynomial rejected.

**GAP 4 — structured-data conditions** (`structured_data.py`, the grey zone): classify pure-data-dependent (DECLINE) vs
structured (i%k==0 periodic data-independent; arr[i]>arr[i-1] under declared sortedness); ★ conservative — genuine
data-dependence DECLINED, structure never forced. **GAP 5 — deep algebraic cancellation** (`simplify_fold.py`): simplify
before fold ((x+1)²−x²−2x−1→0, depth 7), z3-proved equivalent (reuse §AA-W1), then fold; non-equivalent rejected, float
declined. **GAP 6 — the float-exact subset** (`float_exact.py`): x·2.0 / power-of-two scaling fold EXACT (z3 IEEE-754
bit-exact via rounding-mode independence); ★ EXACT only when proved — x·3.0 NOT promoted (stays APPROX-ε/DECLINE), no
silent promotion. **GAP 7 — large-but-bounded state** (`large_state.py`): a 32-bit affine LCG folds via QF_BV/matrix-power
STRUCTURE, never enumerating 2^32; ★ nonlinear large state DECLINED (structure never assumed). **GAP 8 — consecutive-loop
fusion** (`loop_fusion.py`): producer-consumer loops (a[i]=f(i); s+=a[i]) fuse → s=Σf(i) → closed form (Faulhaber,
z3-proved); ★ aliasing / intervening write rejected.

**COMPOSE + measure** (`gapfold_report.py`, MEASURED): on a gap-shaped corpus, BEFORE §AD = **0** folds (the
detector/closed-form machinery wasn't built), AFTER = **8/8** (each established-math structure folds, EXACT where it
applies — G2 asymptotic-order, G6's non-bit-exact float stays APPROX-ε/DECLINE). ★ The no-forcing audit (GAP 4/6/7 decline
the genuinely-unstructured). ★ The now-SMALLER real ceiling: the remainder is the principled-impossible (genuine I/O /
randomness / data-dependent control) — the honest payoff of distinguishing currently-unfoldable from forever-unfoldable.
The big three (divide-and-conquer, nested sums, fusion) are the broadest. Precision **1.0** across all eight batteries;
NO new certificate kind. `test_catalog.py` **147/147** (+8 §AD), test_build **273×3** (gapfold/ not imported). No new
dependency. 잘못된 답보다 DECLINE이 항상 옳다 — 기계를 완성한다: 늘 있던 구조를 접고, 8개 구멍을 패치한 뒤 잔여가 물리·정보
이론이 금하는 영원-불가능(진짜 I/O·무작위·데이터의존)임을 측정으로 증명한다.

## §AE — SEVEN HARD-BARRIER DECIDABLE ISLANDS: enter the proven-hard walls, fold the island, never claim the wall

The deepest directive. Seven barriers that are PROVEN hard in general — z3 IEEE-754 bit-blast blow-up, Hilbert's tenth
(Diophantine, undecidable), closed-form equality (general-open), Risch/Zeilberger non-termination, Rice's theorem
(undecidable), the Turing halting problem (undecidable), and Kolmogorov complexity K(x) (uncomputable). We NEVER claim to
solve any of them generally. Inside each we implement the **decidable island** that reduces to a z3-TERMINATING theory.
★ THE UNIFYING INSIGHT: **synthesis is the proposer's job** (FPTaylor / Faulhaber / Gosper-Zeilberger-Karr / Karr-Farkas-
Gröbner / Podelski-Rybalchenko-SCT / Berlekamp-Massey — the hard search); **verification is z3's job, easy under a
TERMINATING theory** (QF_LRA simplex / QF_NRA nlsat-CAD / QF_BV fixed-width — NEVER IEEE-754 bit-blasting). New package
`barrierfold/` (never imported by test_build; zero deps, sympy grandfathered for ISLAND 4; `forbidden_present == []`).
No new certificate kind (22 mech / 14 kinds unchanged); LLM-free (AST-verified).

**ISLAND 1 — FLOAT-ε** (`float_eps.py`): float loops whose REAL semantics is a geometric/linear recurrence fold to the
closed form with a UNIVERSAL ε, proved by affine/interval arithmetic over **QF_NRA** (real-abstraction `A:=aⁿ`, NO
bit-blasting). REUSES `foldaxes.approx_fold.ErrorInterval` + the existing APPROX_FOLD grade (no new grade). ★ |a|≥1
(non-contractive) DECLINES (error grows ~aᴺ); ★ the ε is universal over the whole domain, never sampled (a sampled max
UNDER-estimates it — the §AB anti-LLM line). **ISLAND 2 — NONLINEAR-INTEGER** (`nonlinear_int.py`): five decidable
fragments of Hilbert-10 — additive (Faulhaber, new), modular (REUSE §Y Galois, zero-new), power (modular orbit/Floyd,
new), substitution (REUSE §Z·§P-P5 Möbius, zero-new), finite-state (cycle detector, zero-new); the new piece is the
DECIDABLE-BOUNDARY CLASSIFIER. ★ general nonlinear (x²+c, Collatz, degree-≥2) DECLINED (Hilbert-10). **ISLAND 3 —
EXP-POLY-EQUALITY** (`exppoly_eq.py`): equality of exponential polynomials Σ Pᵢ(n)·λᵢⁿ over distinct algebraic λ is
ALWAYS decidable by BASIS LINEAR-INDEPENDENCE (coefficient comparison), corroborated by a bounded exact-rational identity.
★ the harder Skolem existential-zero (∃n.f(n)=0) is decidable order≤4 (Vereshchagin), order≥5 DECLINED (open).

**ISLAND 4 — HOLONOMIC-SUMMATION** (`holonomic_sum.py`, the largest island): the summation classes with GUARANTEED
termination — polynomial (Faulhaber), geometric, poly-geometric, Gosper-summable hypergeometric, Zeilberger creative
telescoping, Karr ΠΣ, C-finite. REUSES `catalog/holonomic_sum.py` + grandfathered sympy; extends ⑬. ★ verified by the
TELESCOPING identity C(n)−C(n−1)==summand(n) (terminating); ★ non-holonomic (harmonic H_n, digamma, zeta) DECLINED.
**ISLAND 5 — INVARIANT-SYNTHESIS** (`invariant_synth.py`): the COMPLETE synthesis domains — Karr (affine), Farkas/LP
(linear-inequality), Gröbner (fixed-degree polynomial) — each synthesizes the invariant then z3-VERIFIES three VCs
(initiation / consecution / sufficiency) in QF_LRA/QF_NRA. ★ REUSES the §X `synthesize_guard` interface but UPGRADES CEGAR
guessing → complete synthesis; a wrong invariant (slope mismatch) FAILS consecution (the verifier is real). General
invariant synthesis is undecidable (Rice). **ISLAND 6 — TERMINATION** (`termination.py`): the decidable termination
classes — bounded loops, linear ranking functions (Podelski-Rybalchenko, complete via Farkas), Size-Change Termination
(Lee-Jones-Ben-Amram), and HARAN `decreases` contracts (verify, not synthesize). ★★ **THE HALTING OATH** (binding): the
general halting problem is PROVEN undecidable (Turing 1936); every issued proof says "terminates **BECAUSE** <ranking
function / verified decreases clause>", NEVER bare "terminates"; a general `while`/Collatz is DECLINED (neither affirmed
nor denied).

**ISLAND 7 — KOLMOGOROV-ENUMERATION** (`kolmogorov_enum.py`, the deepest wall): "does arbitrary hidden structure exist"
asks for K(x), which is UNCOMPUTABLE. The island: a COMPUTABLE upper bound over a FINITE ENUMERATED registry of decidable
structure classes (constant / periodic / LFSR via REUSED `native_sequence.berlekamp_massey_Q`, + the 22 mechanisms + 8
gaps), selected by MINIMUM DESCRIPTION LENGTH; if nothing compresses below |x|, DECLINE. ★★ **THE KOLMOGOROV OATH**
(binding): K(x) is PROVEN uncomputable (Kolmogorov/Chaitin); this is "best match among a FINITE ENUMERATED list," NEVER
"any structure," NEVER randomness compression. ★ BY DIAGONALIZATION, for any finite registry there exists structured
input it MISSES (Thue-Morse, 2-automatic but non-LFSR/periodic) — honestly DECLINED, never falsely claimed.

**COMPOSE + measure** (`barrierfold_report.py`, MEASURED): all seven island batteries pass — precision **1.0**; LLM-free
(AST: no LLM import in any module); both honesty oaths present and `confirmed_not_solved` ("the halting problem and K(x)
remain UNSOLVED — only their decidable islands folded"); ISLAND 1's ε audited universal-not-sampled. ★ **THE CONVERGED
CEILING**, measured: the DECLINED remainder = {general nonlinear integer (x²+c/Collatz) — **Hilbert-10**; Skolem order ≥ 5
— **open**; non-holonomic H_n/n — **Risch**; general halting — **Turing**; K(x) exact — **Kolmogorov**}. This is the same
boundary three independent research models drew, and we measured it: the remainder is **provably impossible** — Turing /
Hilbert / Kolmogorov — NOT a gap in our machine. NO new certificate kind. `test_catalog.py` **154/154** (+7 §AE),
test_build **273×3** (barrierfold/ not imported). No new dependency. 잘못된 답보다 DECLINE이 항상 옳다 — 증명된 7개 난벽
안의 결정가능 섬만 접는다(합성은 제안자, 검증은 z3의 종료하는 이론); 정지문제와 K(x)는 안 풀었고(섬만), 세 모델이 독립적으로
그은 경계를 측정 — 잔여는 Turing·Hilbert·Kolmogorov가 금한 영원-불가능, 우리 기계의 구멍이 아니다.

## §AG — 30-THEORY REPO-FIRST AUDIT + SyGuS (the one real gap) + optional separation-logic + sound feedback

An external evaluator named 30 theories to "master". ★ MEASURED FACT (grep + per-build import, not guessed): nearly
all are ALREADY built. So the honest answer is an **audit**, not a rebuild — reimplementing 29 would be ~97% duplicate
work and a repo-first violation. New modules `theory_audit.py` (registry), `sygus_propose.py`, `sep_alias.py`,
`theory_audit_report.py`; one backward-compatible edit to `catalog/compose.py` (`combine_grade`). No new certificate
kind (22 mech / 14 kinds unchanged); LLM-free (AST-verified); zero-dep.

**§1 — the audit registry** (`theory_audit.py`, the algo50 mapping pattern): each of 30 named theories → its REAL
module entry point; `test_ag_theory_audit_registry` IMPORTS every CONFIRMED entry point on each build ("we have theory
N"). ★ MEASURED disposition: **26 CONFIRMED / 0 GAP / 1 NOT-A-FOLD / 3 DECLINED-BY-IDENTITY**. CONFIRMED (25
pre-existing, each import-proven): IC3/PDR(`ic3_pdr`), CHC/Spacer(`chc_solve`), Presburger/QE/CAD(`mathmode.real_qe`),
Angluin L*(`lstar`), SFA(`catalog.mech_sfa`), Knuth–Bendix(`native_rewrite`), Gröbner(`groebner`),
Sturm(`native_realroots`), Gosper/Zeilberger(`native_telescope`), Berlekamp–Massey(`native_sequence`),
LLL(`native_lattice`), Sylvester inertia(`sos_cert`), Prony(`prony`), Petrov(`mathmode.petrov`),
Koopman(`mathmode.transforms_symdyn`), E-graph(`equality_saturation`), AARA(`catalog.mech_aara`),
partial-eval/Futamura(`pillar3.parteval`), translation-validation(`catalog.topic_a`),
companion-matrix(`gapfold.mutual_recursion`), sparse-FFT(`catalog.probe_cascade`),
compressed-sensing(`compressed_sensing`), MDL(`catalog.decline_boundary`), Kolmogorov(`barrierfold.kolmogorov_enum`),
widening(`catalog.lift`) — plus **SyGuS** built here (§2a). NOT-A-FOLD: polyhedral (region-3 constant-factor, already
in `excluded_candidates`). DECLINED-BY-IDENTITY: HoTT (z3-termination), GCT (P-vs-NP paradigm), NIA-general
(Hilbert-10 undecidable — decidable islands already in barrierfold ISLAND 2/3). ★ Double-count gate: no theory in two
modules, no module backing two theories. (The evaluator's headline "29 built" depends on splitting the QE family /
IC3-PDR — either way the only genuine gap was SyGuS; reimplementation = 0.)

**§2a — SyGuS** (`sygus_propose.py`, the lone net-new): CFG candidate space + SMT spec → DETERMINISTIC enumerative /
CEGIS synthesis, GATED by the existing `equiv_check.prove_equiv_z3` / `equiv_grade` (no new disposer, no new cert
kind). max2 → `ite(x≥y,x,y)` z3-proven; 2x+1 synthesized; a too-weak grammar (no `*`) canNOT express x·y ⇒ honest
DECLINE. ★★ **honest measurement**: SyGuS is a PROPOSER, NOT a fold-COVERAGE extension — the z3-foldable set is
identical (same gate as §P P1 / §AE ISLAND 5), so **fold-coverage Δ = 0** (measured); the proposer metric is reported
separately, never conflated. LLM-free (deterministic). **§2b — separation-logic** (`sep_alias.py`, optional): promote
an aliasing DECLINE to ACCEPT *by proof* — affine index injectivity / region disjointness reduced to z3 QF_LIA; a
collision/overlap witness keeps DECLINE (precision 1.0). Measured: **4/7 promotions** on the micro-corpus; cert reuses
the existing `invariant` kind.

**§3 — feedback, sound form only.** ① Error explosion: ★ MARTINGALE/Chernoff **REJECTED** — they require an
UNPROVEN independence/martingale structure, and an unproven distributional assumption IS the LLM's approximation =
our forbidden line. Sound fix: a backward-compatible `prob_cap` on `combine_grade` (+ `compose_chain`) — a
PROBABILISTIC chain past the cap DECLINEs honestly (error explosion EXPOSED, never hidden); δ_total ≤ Σδ_i union
bound kept; EXACT-first routing; `prob_cap=None` default ⇒ the 273 are byte-identical. Adversarial: long chain →
DECLINE at the offending stage, false-EXACT = 0. ② NIA-bridge: rejected as duplicate (undecidable; islands already
built) — marked DECLINED-BY-IDENTITY. ③ Data-structure lifting: the named examples are ALREADY built (binary-counter→
amortized = AARA `catalog.mech_aara`; array→algebra = §P `array_fold`); the ~5.7% ceiling is a MEASURED honest
ceiling, NOT inflated — no new structural pattern was found this directive, so NO §AD entry was added (ceiling holds).

**COMPOSE + measure** (`theory_audit_report.py`, MEASURED): the 30-theory disposition table, SyGuS coverage Δ=0
(honest), sep 4 promotions, the ① depth-cap adversarial (false-EXACT 0, martingale rejected). Precision **1.0**
(every SyGuS/sep promotion z3-disposed; false fold / false "solved" = 0); NO new certificate kind (22/14); LLM-free
(AST: no LLM import in any §AG module); zero-dep (`forbidden_present == []`). `test_catalog.py` **158/158** (+4 §AG),
test_build **273×3** (new modules not imported; `combine_grade` change is default-off ⇒ 273 unchanged). 잘못된 답보다
DECLINE이 항상 옳다 — 30개 중 29개는 이미 빌드(재구현 0, 감사로 증명); 유일 빈칸 SyGuS는 z3-게이트 결정적 proposer
(coverage Δ=0); 마틴게일 거부(정체성 사수)·NIA-다리 거부(결정불가·중복)·자료구조 리프팅 이미 AARA/§P·천장 미인플레.

## §AH — MULTILANG INTAKE · VERIFIED CODEGEN · RECALL INTEGRATION · SELF-FOLD · SUPER-SCALING · SECURITY VERIFIERS

Six axes under three binding honesty reframings (a violation FAILS the build): **RF-1** language = *intake*, not
*coverage* (fold acts on the language-agnostic IR; the new work is per-language SEMANTICS that DECLINE unsound folds);
**RF-2** the 22 mechanisms / 14 cert kinds are SATURATED — **no new mechanism** (only recall/composition/
canonicalization + a probabilistic frontier); **RF-3** there is no "perfect security" — only the machine-verified
ABSENCE of a NAMED vuln class + an explicit threat model, else DECLINE/FLAG. precision 1.0 (no false fold / no false
"safe"); new cert kinds 0; LLM-free core; zero-dep core (tree-sitter OPTIONAL, pure-Python fallback kept).

**§1 multilang intake** (`frontend/semantics.py` + `frontend/lang_intake.py`): the precision-1.0 defense line. The
SAME `Σi → n(n+1)/2` fold is decided UNDER each language's integer model — Python (arbitrary) EXACT; Java/C# int32
the NAIVE form OVERFLOWS mid-expression so only the WRAP-AWARE form is accepted (z3 QF_BV refutes naive==wrap-sum);
C/C++ signed overflow = UB ⇒ **DECLINE** in range (never a closed form for UB), EXACT only when no-overflow is
provable; Go/Rust-wrapping wrap-aware; Rust-checked over-range DECLINE. Float reassociation refused (IEEE-754 / FMA);
eval-order preserved. Intake recognizes the structure in 7 languages (language-agnostic) — the foldable subset is
language-independent (same domain-conditional ceiling); only the SOUNDNESS disposition differs (2 languages DECLINE
the same fold). **§2 verified codegen** (`codegen/idiom.py`): deterministic value-range → type-promotion (JS number→
BigInt past 2^53; C int64/__int128 + overflow-guard; Java/C# int→long/BigInteger; Rust checked_*; Go typed) — then
z3 TRANSLATION-VALIDATED against §1 semantics (codegen PROPOSES, z3 DISPOSES; a wrong naive-int32 emission is
REJECTED and falls back). Gain is CONSTANT-factor (type/vectorization), never summed with §1's asymptotic fold.

**§3 recall integration** (`recall_integrate.py`, RF-2 — NO new mechanism): canonicalization collapses ≥3 surface
variants to one form (recall ×3, EXACT ceiling unchanged); lens composition is additive-with-overlap; disguised
C-finite recalled via the REUSED Berlekamp-Massey; the probabilistic frontier grades above-threshold PROBABILISTIC /
below-threshold DECLINE (NEVER EXACT). Reuses §Y/§Z/§AA/§AB/§AC/§AD/§AE/§M (the §AG audit is the double-count gate).
**§4/5 self-fold + super-scaling** (`self_fold.py`): self-fold touches ONLY Clock C (of A=LLM, B=z3, C=fold, I/O) ⇒
end-to-end gain is AMDAHL-LIMITED (1.11× at the modelled budget — A/B/I-O are the non-foldable floor; correctness
never depends on the profile). Super-scaling: the foldable-kernel ratio grows with N (O(N)→O(1)) AND memory drops
O(N)→O(1) (OOM-avoidance) — but the WHOLE-task gain is capped by Amdahl at the MEASURED foldable fraction p; low-p
large work routes to an honest "amdahl-capped" report, high-p to "super-scale". The forbidden "bigger ⇒ absolutely
faster" system claim is NOT made.

**§6 security verifiers** (`security/route.py` + `consttime.py` + `taint.py` + `entropy.py` + `reentrancy.py`, RF-3):
deterministic-first router (the guarantee is router/LLM-INDEPENDENT — the weak-LLM constraint's heart). consttime
(reuse `sidechannel`) proves secret-dep branch/mem/div ABSENCE or FLAG/DECLINE; taint (reuse `taint_ifds`) proves
source→sink non-reachability or FLAG; ★ entropy proves LOW-entropy INSECURITY only — NEVER "secure" (NIST PART1.C:
statistics are necessary-not-sufficient); reentrancy (CFG checks-effects-interactions) FLAGs an external-call-before-
state-write — the DeFi audit angle. ★ Explicit threat model (proves: modelled timing/taint/reentrancy/low-entropy;
does NOT prove: unmodelled side channels, hardware, protocol, crypto-primitive security). Security-side precision
1.0 = ZERO false "safe"; "perfectly safe" is NEVER claimed.

**COMPOSE + measure** (`upgrade_ah_report.py`): all six axes — precision **1.0**; NO new cert kind (22/14); LLM-free
core (AST: no LLM import in any §AH module); zero-dep core (tree-sitter optional, fallback kept); the two honesty
qualifiers preserved (domain-conditional; measured ceiling not inflated); the three forbidden claims ("완벽한 보안",
"클수록 절대 빨라짐", "언어 추가로 fold율 상승") avoided. `test_catalog.py` **164/164** (+6 §AH), test_build **273×3**
(§AH modules not imported — purely additive). 잘못된 답보다 DECLINE이 항상 옳다 — 언어는 intake지 coverage 아님(의미로
unsound fold DECLINE); 새 메커니즘 0(포화); self-fold·super-scaling은 foldable 분율에 Amdahl-제한; 보안은 명시 취약점
부재의 기계검증 + 위협모델, '완벽한 보안' 없음; z3-종결·약한-LLM 비의존·zero-dep 코어·precision 1.0.


## §AI — GROW THE NUMERATOR BY RECALL ONLY (conjecture-then-verify · interproc · spec-declared · canon)

Grow the fold-rate **numerator** (count of folded EXACT cases) by RECALL only — the **denominator** and the 22/14
mechanism / certificate taxonomy are UNCHANGED. Four levers, each **PROPOSES** and z3 **DISPOSES**. ★★ **P-2 (the
line 5 AIs crossed)**: OBSERVATION IS NOT PROOF — a conjecture that matches ten thousand observed points but cannot
pass a z3 ∀-proof + the held-out divergence guard is **DECLINED** (false-EXACT count = 0). Every lever routes to an
EXISTING certificate kind; no new mechanism, no new disposer.

**§1 conjecture-then-verify** (`conjecture/`, the strongest lever): when the white-box matcher can't READ the code
(disguise: recursion / closure / CPS / object-state / dynamic dispatch), run it as a BLACK BOX, observe the I/O,
CONJECTURE a recurrence/closed-form, and let z3 prove it ∀n. Conjecturing is free (a wrong guess is rejected by z3),
so the numerator grows AND the disguise dimension collapses (infinitely many disguises, ONE behavior). Five thin
conjecturers, all REUSE: `bm_linrec` (Berlekamp-Massey C-finite → `native_sequence`), `closedform_guess` (finite-
difference polynomial degree + characteristic (x−1)^{d+1}), `period_guess` (smallest-period table identity),
`matpow_guess` (companion-matrix power O(N)→O(log N) → §AD `mat_pow`), `holonomic_guess` (first-order P-recursive
ratio test — defeats disguised factorial/binomial). Disposition is `harness.conjecture_verify` (REUSE §P P1
`blackbox_recover`) = the **held-out divergence guard** (the conjecture must predict 200 unseen terms past the probe
EXACTLY) **+** the explicit z3 **companion-consecution proof** (`prove_companion_consecution`: z3 QF_LRA proves the
companion matrix advances the recurrence state ∀ window — the ∀n half of the P-2 gate). ★ **under-determination
guard**: an order-d conjecture needs ≥ 2d+2 observations; fewer ⇒ ABANDON (a polynomial of degree k fits ANY k+1
points — a fit is not a proof). ★ **The digit-function trap, honestly handled**: `digitsum`/`popcount` admit a
spurious order-11 linear-recurrence fit on a SHORT window (the structural break is the digit carry at n=100); the
held-out window was bumped 24 → **200** so it crosses multiple carry scales and REFUTES the fit ⇒ DECLINE. This is
exactly the P-2 risk, caught. Honest limit: a finite held-out can't prove ∀n beyond ALL scales — the strongest
guarantee is reserved for the structural z3 proof; the held-out is the divergence *screen*, the z3 consecution is the
*theorem*.

**§2 interprocedural stitching** (`interproc/stitch.py`): most folds today are intra-function, but real accumulators
are scattered ACROSS functions. Stitch per-function affine state updates executed on a fixed schedule into ONE
composed affine recurrence, z3-proven ≡ the sequential application (REUSE §P P6 `distributed_state` — existing
matrix_recurrence kind). A non-affine / aliased / nondeterministic handler ⇒ DECLINE (the contamination guard). ★
Honest boundary: this WIDENS the analysis REACH (cross-function accumulators become visible to the matchers); it does
NOT make most cross-function code foldable (control flow stays control flow) — the fold-rate lift is MODEST.

**§3 spec-declared fold** (`specfold/declared.py`, the cleanest lever — it ADDS information, not a guess): structure
the engine can't INFER, the user/LLM can DECLARE. A HARAN `requires sorted(a)` clause (REUSE `haran_parser`) is
consumed as a fold PRECONDITION — a CONDITIONAL theorem "R ⟹ folded ≡ original", with R **ALWAYS** recorded in the
certificate (hiding the assumption would be a false EXACT; it is transparent). Where R is z3-dischargeable we
discharge it (`requires 0≤s<2^16` ⇒ bounded ⇒ wrap-free integer fold, z3 BV-proven via `frontend.semantics`).
Without a declaration the engine can't prove the structure from bare ground ⇒ DECLINE.

**§4 canonicalization + composition** (REUSE §AA `foldrate/canonicalize.py` + `compose.py`, measure-first, no
reimplementation): surface variants normalize to ONE canonical form (the multiplier — distribution-dependent, 8.0× on
the §AA corpus) and lenses compose (lift 4). The numerator grows by recall; the denominator and 22/14 are unchanged.

**COMPOSE + measure** (`molecule_report.py`): the four levers + an LLM-free AST check + the ★ HONEST per-domain delta
— signal/numeric/stats/crypto fold their DISGUISED structure (real recall: 2/2, 2/2, 2/2, 1/1) but the **general
backend folds 0/2** (digit-sum/popcount have NO recurrence to recall, and the held-out divergence guard refuses the
spurious order-11 fit — the numbers don't lie). precision **1.0** (false fold 0); P-2 enforced (false-EXACT 0);
under-determination guard fires; NO new cert kind (22/14); LLM-free core (AST: no LLM import in any §AI module);
zero-dep. `test_catalog.py` **169/169** (+5 §AI), test_build **273×3** (conjecture/interproc/specfold/molecule_report
not imported — purely additive). 관찰은 증명이 아니다(P-2): 만 개가 맞아도 z3 미증명이면 DECLINE — 분자는 recall로만
키운다(분모·22/14 불변), 거짓 EXACT 0, z3-종결·LLM-free 코어·zero-dep.


## §AJ — FOUR AUXILIARY LAYERS ON §AI (conjecturer routing · residual gate · soundness aux · Viterbi semiring)

Absorbed from four external AI evaluation rounds — taking ONLY the items that pass z3 + precision-1.0 + repo-first —
and wiring each as an AUXILIARY layer on §AI's conjecture-verify that CANNOT weaken the gate. The dominating principle:
a layer may add speed or an extra exact certificate, never a false EXACT.

**§1 residual cutoff gate** (`conjecture/precheck.py`): a fast DECLINE shortcut that skips the conjecture path on the
unmistakable random-oracle signature. ★★ The invariant that makes it safe — **false-skip 0**: it NEVER skips a
foldable. The skip rule requires the joint ABSENCE of every structural tell, and the structural detectors (cheap
Berlekamp-Massey order via the §AI under-determination boundary — REUSE `native_sequence`; polynomial term-ratio —
REUSE `holonomic_guess`; period — REUSE `period_guess`) are SUPERSETS of the conjecturers' own first steps, so a
foldable always trips one ⇒ never skipped, by construction (not by luck). Corroborated by the directive's named
statistical signals — Shannon entropy, rescaled-range Hurst, and MDL incompressibility (REUSE `decline_boundary
.mdl_two_part`, the zlib K-complexity upper bound). ★★ And the honest framing: a skip can only cost RECALL (a wrongly-
skipped foldable would become a DECLINE), it can NEVER cost PRECISION (z3 still disposes everything that PROCEEDS) — so
precision 1.0 does not depend on this gate at all; it's a Clock-C speed filter, with false-skip measured = 0 so recall
is preserved too. A skip is a DECLINE, never a fast EXACT (P-2).

**§2 conjecturer router** (`conjecture/router.py`): cheap signals (autocorrelation ⇒ periodic; finite-difference
collapse ⇒ polynomial; polynomial term-ratio ⇒ holonomic; small Berlekamp-Massey order ⇒ C-finite/matpow; NCD/KS/
mutual-information tie-breakers) predict WHICH conjecturer will fold and try it first. ★★ ORDER only — the full
five-conjecturer portfolio remains the fallback, so the SET that folds is IDENTICAL with or without routing (routed
recall == unrouted recall, measured) and z3 disposes each candidate regardless of order. Routing can neither create a
fold nor a false EXACT; it only saves average conjecture work (the first-try hit rate is the measured win). When the
router guesses wrong (factorial routed non-holonomic first) the fallback still folds it — recall preserved.

**§3 soundness aux** (`conjecture/soundness_aux.py`): (a) **Kraft-McMillan** — a uniquely-decodable / prefix binary
code with lengths {lᵢ} exists IFF Σ2^(-lᵢ) ≤ 1, an EXACT rational realizability certificate (Fraction arithmetic, never
float); >1 ⇒ DECLINE with the exact over-budget. (b) **0-1-law promotion** — ★★ THE P-2 LINE: an observed-always
property P(n) is promoted to "holds ∀n" (EXACT) ONLY when z3 proves the structural dichotomy `(∀n≥0.P(n)) ∨
(∀n≥0.¬P(n))` and the single observation selects the branch; if P is genuinely n-dependent (e.g. "n<100", true on the
probe, false later) z3 finds NO dichotomy and there is NO promotion — observation alone never promotes. Both reuse the
existing `invariant` certificate kind (no new kind).

**§4 Viterbi semiring** (`gapfold/semiring_dp.py`): a Viterbi (max-product) DP is, in the log domain, V[t][j] =
maxᵢ(V[t-1][i] + logT[i][j]) — EXACTLY the max-plus tropical semiring already in the taxonomy. A time-homogeneous
transition folds T steps via the tropical matrix power logT^⊗T, O(T·m²)→O(m³ log T), sound by semiring associativity
(REUSE `altlens.tropical_fold`: `tropical_matpow` + the `verify_matrix_extraction` differential check). ★★ NO new
mechanism — Viterbi is the tropical face; the cert reduces to matrix-power / linear-recurrence (kind `closed_form`).
Honest: max/argmax are exact comparisons (the PATH is exact even in float); the accumulated log-SCORE is exact over
ℤ/ℚ. Per-step-varying emissions are already O(T·m²)-optimal ⇒ the asymptotic fold is DECLINED (no false speedup).

**COMPOSE + measure** (`aj_report.py`): four layers — precision **1.0**; P-2 enforced (skip ⇒ DECLINE; 0-1 promotion
only under a z3 dichotomy); false-skip **0** (measured on the foldable corpus); routing recall **invariant**; NO new
mechanism (22/14); LLM-free core (AST: no LLM import in any §AJ module); zero-dep. `test_catalog.py` **174/174**
(+5 §AJ), test_build **273×3** (precheck/router/soundness_aux/semiring_dp/aj_report not imported — purely additive;
gapfold is never imported by test_build). 보조 레이어는 게이트를 약화할 수 없다 — 잔차 컷오프는 false-skip 0이고 skip은
DECLINE이지 거짓 EXACT가 아니다(recall만 비용, precision 불변); 라우터는 순서만(recall 불변); 0-1 승격은 z3 이분법에서만
(관찰 아님 — P-2); Viterbi는 기존 max-plus face(새 메커니즘 0); precision 1.0·LLM-free 코어·zero-dep.


## §AK — 2000-CODE UNFAKEABLE FOLD-RATE MEASUREMENT + DECLINE-REASON MAP (measurement only — engine unchanged)

A measurement harness (NO engine code added) that runs the EXISTING fold engine over 2000 codes and refuses to let the
number lie. **M-1** the fold rate is reported PER DOMAIN × PER PROVENANCE, never as a lone scalar (filling the corpus
with signal code would read 90%). **M-2** the real product is the DISTRIBUTION of what does NOT fold. **M-3** every
EXACT is independently re-verified — false-EXACT must be 0. **M-4** the corpus is general-backend-majority (the real
world is mostly structureless), with `synthetic` (recall ceiling) and `realworld_style` (the real number) separated.

**§1 corpus** (`corpus/build_corpus.py`): 2000 deterministic (fixed-seed, LLM-free, reproducible) codes — general_backend
600 / numeric 400 / signal 350 / statistical 350 / crypto_preprocessing 300; each tagged `synthetic` vs `realworld_style`;
every bucket carries deliberate NON-foldables (anti-manipulation). **§2 run** (`measure/engine_adapter.py` +
`run_corpus.py`): the unchanged engine — static (`catalog.lift` + `structure_recognizer`) AND the §AI/§AJ black-box path
(precheck → router → 5 conjecturers) — classifies each code EXACT / PROBABILISTIC / DECLINE / ERROR. fold rate =
EXACT / (EXACT + PROBABILISTIC + DECLINE): PROBABILISTIC is NOT in the numerator, ERROR is EXCLUDED; isolated per-item,
harness-level z3 timeout, fixed seed. **§3 taxonomy** (`measure/decline_taxonomy.py`): each DECLINE → a PROVEN_BOUNDARIES
class A–I (REUSE `decline_boundary`); ambiguous ⇒ UNCLASSIFIED (never forced — forcing would hide recall headroom);
R is assigned only by §4. **§4 near-miss** (`measure/near_miss.py`): the recall hunter — aggressively retry DECLINEd
unary oracles (§AI conjecturers at probe=64 + the k-regular mechanism M22, REUSED) under a DOUBLE-WINDOW + far held-out
guard; a fold ⇒ **R** (recall gap) + its disguise type (the ranked recall priority). M-3 held: a near-miss fold is
accepted only through a z3-gated mechanism, never observation.

**MEASURED (n=2000, seed=20260628, reproducible)** — `ak_report.py`:
- fold rate by domain: crypto **0%** (hashes/CSPRNG correctly never fold) · general_backend **10%** (the honest floor —
  structureless backend code has nothing to fold; math, not failure) · numeric **56%** · signal **50%** · statistical **57%**.
- by provenance: **synthetic 90.4%** (recall ceiling — the engine catches what it knows) vs **realworld_style 6.8%**
  (the real number); overall 33% is NOT reported alone (M-1).
- DECLINE map (1340 declines): UNCLASSIFIED 46.6% (data-shaped computation, no proven boundary) · C 17.9% (information
  floor — crypto) · I 17.9% (data-dependent control flow) · F 8.8% (z3 wall — transcendental) · H 4.5% (I/O) · E 4.3%
  (chaos). near-miss R = **44**, all `k-regular(k=2)` ⇒ the #1 recall priority is the k-regular class (popcount).
- ★★ **M-3 precision gate: 660 EXACT folds, false-EXACT 0, precision 1.0** — every EXACT independently re-verified
  (recovered recurrence vs the TRUE oracle on a far window n≈400–420). ERROR 0.

`test_catalog.py` **179/179** (+5 §AK), test_build **273×3** (corpus/measure/ak_report not imported — purely additive).
2000개를 속일 수 없게 측정 — 출처·도메인 분리(M-1)·DECLINE 지도(M-2)·false-EXACT 0(M-3)·general 다수 정직(M-4); 엔진
불변·새 종류 0·z3-종결·LLM-free·zero-dep·재현가능(시드).


## §AL — RECALL TO THE PHYSICAL LIMIT (exhaustive disguise-stripping · conjecture depth · spec-declared max)

Squeeze foldable-but-missed code (the §AK R class) to the limit, across EVERY disguise dimension. **★ S-2 (the soul):
observation is not proof.** The strip modules ONLY normalize — every candidate is disposed by the §AI z3 ∀-proof +
held-out=200 gate, in ONE place (`recall/core.fold_via_ai`); a wrong strip just produces a candidate the gate rejects,
so no strip can ever manufacture a false EXACT. Push recall to the limit, never break precision 1.0. S-1: no new
mechanism; S-3: every DECLINE→ACCEPT promotion is z3-disposed; S-4: general backend stays low (structureless code has
no disguise to strip — math, not failure).

**§1 disguise-strip (`recall/strip/`, 8 dimensions)** — each a deterministic AST/behavioral normalizer that exposes a
foldable oracle, then §AI + z3 dispose: ① `recursion_to_loop` (naive O(2ⁿ) recursion → MEMOIZED feasible oracle —
without it the black-box can't even probe); ② `multivar_collapse` (f(n)→tuple, non-numeric to the black-box → project
the foldable component — the hidden single variable); ③ `interproc_gather` (accumulator scattered across functions →
one recurrence, REUSE §AI §2 `interproc.stitch`); ④ `closure_unwrap` (closure state advanced by repeated calls → unary
oracle); ⑤ `object_state_extract` (object/method state machine → unary oracle); ⑥ `control_flatten` (per-guard
recurrences split by residue class, each z3-gated); ⑦ `strength_reduction_inverse` (repeated-add→linear, repeated-mul→
geometric; honest overlap with the lifter); ⑧ `alg_window_relation` (window over a structured stream → closed form;
overlaps §Z). ★ ①–⑤ are GENUINE new recall (the raw black-box cannot see them); ⑥–⑧ overlap existing coverage but stay
z3-gated. Each module REJECTS its chaos/random/data-dependent adversary (false-EXACT 0).

**§2 conjecture depth + ★★ MULTI-SCALE held-out (`recall/depth.py`)** — escalate the probe (24→48→96→192) so a
higher-order recurrence under-determined at a shallow probe becomes determined (ABANDON if observations are
insufficient — a fit through too few points is never accepted). ★★ The key soundness upgrade: §AK found the
digit-function trap (a recurrence matching a contiguous window but breaking at a digit carry, n=100). A contiguous
held-out crosses ONE carry scale; the multi-scale held-out verifies the recurrence on windows STRADDLING n≈100/1000/
10000, so any carry-class sequence is REFUTED permanently — base-10 digit-sum, which MATCHES a contiguous BM recurrence,
is now a permanent DECLINE. This strengthening can only turn EXACT into DECLINE (precision only goes UP). Honest: depth
shows DIMINISHING RETURNS (`yield_curve` plateaus) — route deep only on §AJ-promising oracles.

**§3 spec-declared max (`recall/declared_max.py`)** — the cleanest recall (information by DECLARATION, no conjecture):
the §AI structures route to specfold (REUSE; bounded_state z3-discharged), widened with monotone/periodic/prime — each
a CONDITIONAL theorem "R ⟹ folded ≡ original" with R ALWAYS in the cert; undeclared ⇒ DECLINE.

**COMPOSE + measure (`al_report.py`)**: §AK R before/after — **8/8 disguise dimensions recovered** (recursion/multivar/
interproc/closure/object/control/strength/window); ★ S-3 precision: every recovered fold went through the §AI z3+held-
out gate ⇒ **false-EXACT 0**; ★★ the digit-function P-2 trap is PERMANENTLY blocked (multi-scale held-out); chaos/random/
structureless DECLINE; S-4 general backend stays low; depth diminishing-returns curve recorded. `test_catalog.py`
**184/184** (+5 §AL incl. the ★ S-2 multi-scale adversarial), test_build **273×3** (recall/al_report not imported —
purely additive). NO new mechanism, NO new certificate kind; LLM-free; zero-dep. 관찰은 증명이 아니다 — recall을 끝까지
밀어도 z3 ∀+다중스케일 held-out이 처분(precision 1.0 불변, 영혼); 변장 8차원 벗김·digit-trap 영구 차단·새 메커니즘 0.


## §AN — CLOSE THE ONE MEASURED RECALL GAP (k-regular k=2, the §AK R=44)

§AK's 2000-code measurement found exactly ONE recall gap: **R=44, all `k-regular(k=2)`**. §AN closes it — measurement-
driven, not guessed. ★ **Honest correction (M-1/S-4)**: inspected, those 44 are `bin(n).count('1')` — POPCOUNT, a
**base-2 AUTOMATIC sequence** (a[n] is a function of n's base-2 digits), recovered by the **k-kernel linear
representation** (the existing M22 `mech_kregular`) — NOT "disguised 2nd-order linear recurrences (a[n] depends on
a[n-2])" as the directive's structural sub-label put it. The directive's CORE is exactly right, though: M22 ALREADY
folds them; the §AK black-box recall path simply never ROUTED to M22 — a **recognition gap, not a capability gap, no
new mechanism (S-1)**.

**`recall/k_regular.py`**: `fold_k_automatic` recognizes a base-k automatic sequence via the EXISTING M22 k-kernel
(k∈{2,3,4}), gated by a DOUBLE-WINDOW held-out (160 AND 280 terms — a spurious fit breaks on the longer window) — this
is the R=44 closer (REUSE `mech_kregular`, no new mechanism). `fold_stride_interleave` builds the directive's
interpretation (k independent recurrences interleaved in one stream → separate the stride-k substreams, BM-fold each
with the §AL multi-scale held-out) — a genuine adjacent pattern (honestly, an interleave of C-finite streams is itself
C-finite, so single-stream BM usually already catches it). §2 quasi: `fold_k_periodic_coeff` (REUSE §AL
`control_flatten` per-residue) + k-mutual (REUSE §AD companion) — preventive, no overfit.

**MEASURED (`an_report.py`, the gate)** — re-run §AK's R=44 the same way it was found: **44/44 popcount DECLINEs
PROMOTED to EXACT** via the existing M22; before each was DECLINEd by the raw §AK engine (the recognition gap), after
each folds. **realworld fold rate 6.84% → 10.04%** (94→138 EXACT of 1374 realworld_style — the only meaningful
denominator, synthetic is already at its 90% ceiling). ★★ **false-EXACT 0**: every promotion re-verified by M22 exact
ℚ re-substitution on 400 terms (independent, far beyond any fit) + the double-window held-out; the §AK 660 EXACT are
untouched (additive recognition). ★ Honest scope: base-10 digit-sum still DECLINEs (the M22 k=10 kernel doesn't close —
a deeper gap, not faked); general backend unaffected (the gap was realworld popcount).

`test_catalog.py` **187/187** (+3 §AN incl. the ★ R=44 regression + the ★ multi-scale held-out), test_build **273×3**
(k_regular/an_report not imported — purely additive). NO new mechanism, NO new certificate kind; LLM-free; zero-dep.
§AK가 직접 측정한 단 하나의 갭(k-regular k=2 = popcount, 44개)을 기존 M22 라우팅으로 닫음(인식 문제지 능력 아님) —
realworld 6.84%→10.04%·false-EXACT 0·새 메커니즘 0·정직한 보정(automatic이지 2차 점화 아님).

---

## §AO — ACCELERATE THE NON-FOLDABLE MAJORITY (verified accel stack, kept SEPARATE from the fold rate)

§AK MEASURED that the realworld majority (≈93%) and the general backend (≈90%) do **not** fold — that is **mathematics,
not failure**. §AO takes the honest next step: *accelerate* a STRUCTURED-numeric subset of that majority with
**z3-EQUIVALENCE-verified** fast kernels, while keeping acceleration **rigorously separate** from the fold rate.

**★ The four honesty axes (the spine of §AO):**
- **A-1 — acceleration ≠ fold.** Speedup is a SEPARATE metric. It is *never* summed with the §AK fold numerator;
  the fold rate is unchanged by §AO (`ao_report.A1_separate_from_fold.acceleration_changes_fold_rate == False`).
- **A-2 — translation validation is THE differentiator.** Every emitted kernel carries a z3 ∀-equivalence proof
  (kernel ≡ its reference on ALL inputs). A kernel that fails validation is **NOT emitted** — this is exactly what a
  "fast library" cannot give you. Measured by rejecting the classic WRONG variant of every transform.
- **A-3 — crypto / hardware-RNG / MCMC EXCLUDED.** Non-deterministic / side-channel cores are refused by policy
  before any transform is attempted (`_crypto_excluded`).
- **A-4 — honest device status.** With no GPU/ptxas present, the artifact is **"PTX-verified-complete (throughput
  device-pending)"** — never a fabricated speedup number.

**§1 — physical/numerical INVARIANTS (`accel/invariant/`) = precision-1.0's PHYSICS version.** An accelerated kernel
must not break the laws it obeys; each law is z3-PROVEN ∀, not assumed:
- `conservation.py` — `circulant_update(stencil)` builds the update matrix; `verify_conservation(M)` z3-proves
  Σ(Mu)==Σu ∀u. The diffusion stencil [1,−2,1] CONSERVES mass; a non-conservative [1,−1,1] is **REJECTED** (false
  "conserved" 0).
- `probability.py` — `verify_probability(P)` z3-proves column-stochastic Σ(Pp)==Σp + nonnegativity; a leaky or
  negative kernel is **REJECTED**.
- `stability.py` — `verify_cfl_diffusion(c)` z3-proves ∀s∈[0,1] |1−4c·s|≤1 (no trig, the amplification factor over
  the symbol range). CFL=½ is stable; **c=0.6 is REJECTED** (|g|>1 ⇒ the scheme blows up).
- `iter_refine.py` — mixed-precision iterative refinement, VALID only when contracting (ρ<1), graded **APPROX_FOLD**
  (ε=ρ^steps, REUSE §AB `approx_fold`, **never EXACT**); a diverging ρ≥1 is REJECTED.

**§2 — verified compiler TRANSFORMS (`accel/xform/`), each z3-equivalence-gated ("CompCert for the accelerator").**
The speedup is real, the math is *proven identical*, and a WRONG variant of every pass is **REJECTED**:
- `fusion.py` — matmul+bias+ReLU fusion proven ≡ the sequential form (REUSE `catalog.topic_a.translation_validate`);
  a wrong fusion (ReLU-before-bias) is rejected.
- `polyhedral.py` — `interchange_legal(deps)` by lex-positivity of the permuted dependence vectors; dep (1,0) legal,
  (1,−1) **rejected** (reverses a dependence); `tiling_equiv`.
- `winograd.py` — F(2,3) Winograd convolution proven ≡ direct conv **over ℚ** (`translation_validate` sort="Real");
  a coefficient error is rejected.
- `scalar_opt.py` — five classic passes (strength-reduction · CSE · LICM · const-fold · DCE), each z3 ∀-proven ≡ the
  original; the classic bug of each is **rejected**.
- `vectorize.py` — lane-equivalence (z3) AND an **aliasing legality gate** (output region disjoint from input via the
  §AG `sep_alias.promote_regions` separation-logic prover); an in-place aliasing map (possible loop-carried
  dependence) is **rejected**.

**§3 — BACKEND emit (`accel/backend/verified_emit.py`) — ride the stack, differentiate by the cert.** We do NOT
reinvent MLIR/LLVM/Triton/XLA. We REUSE `gpu.ptx_codegen` (PTX emission + honest device status) and ATTACH to every
kernel a §2 equivalence certificate and, where physical, a §1 invariant certificate. `emit_verified_gemm` emits a
tiled-GEMM PTX kernel **only if `tv.status == KV.EXACT`** — the buggy tiled GEMM fails translation validation and is
**NOT emitted** (★★ A-2). `emit_verified_dynamics` emits only if BOTH conservation AND CFL stability hold.

**MEASURED (`ao_report.py`, the gate):** all §1+§2+§3 batteries green; A-2 every emitted kernel certified AND every
wrong transform rejected; **class1 invariant-violations accepted = 0** (false "preserved" 0); A-1 acceleration does
NOT change the fold rate; A-3 crypto excluded; A-4 device status honest; precision 1.0; **new certificate kinds 0**
(§AB APPROX-ε + existing equivalence/invariant kinds reused). **Honest scope:** acceleration targets STRUCTURED-numeric
kernels (dynamics/GEMM/conv/filter); the general-backend control-flow majority is **not** accelerable as a verified
kernel either (control flow stays control flow) — honest, exactly like the fold rate.

`test_catalog.py` **191/191** (+4 §AO: §1 invariants incl. ★ CFL/conservation rejection, §2 transforms incl. ★ every
wrong-variant rejection, §3 backend incl. ★★ buggy-GEMM-not-emitted, ao_report A-1/A-2/A-3), test_build **273×3**
(accel.invariant/accel.xform/accel.backend/ao_report **not imported** — purely additive). NO new mechanism, NO new
certificate kind; LLM-free; zero-dep (z3+stdlib).
못 접는 다수(§AK 측정)를 z3-등가검증 커널로 *가속* — A-1 가속≠fold(분자 불변, 분리 지표)·A-2 모든 커널 z3 등가증명
동반(실패 커널 방출 안 됨, 빠른 라이브러리는 못 주는 차별점)·§1 물리 불변식은 precision-1.0의 물리판(비보존/CFL위반
REJECT)·§3 PTX 백본 위 검증 레이어(재발명 안 함)·A-3 crypto 제외·A-4 GPU 없으면 PTX-검증-완료(조작 숫자 0)·새
메커니즘 0·새 증명서 종류 0.

---

## §AP — 4-WAY CROSS-VALIDATED RECALL ×6 (each a normalizer over the existing z3 gate; measured, not estimated)

Six recall mechanisms, each a NORMALIZER that strips a disguise and routes through the EXISTING z3-gated disposer —
**S-1: no new fold mechanism, no new disposer, no new certificate kind.** The spine: **S-2 (soul)** observation is not
proof (z3 ∀-proof + multi-scale held-out disposes; AI hand-derived closed forms are RE-PROVEN, never trusted);
**S-3** every mechanism is MEASURED; **S-4** most AI "fold" examples are Fibonacci/Σk²/EMA = already folded, so these
close DISGUISES (the honest delta on a structureless corpus is small — that honesty is the result).

**§1 `recall/compose/` — CROSS-LENS compositional fold (atomize·fold_each·recombine).** The genuine win is a stream in
NEITHER closed class: **Fibonacci (C-finite, exponential ⇒ not k-regular) + popcount (k-automatic ⇒ not C-finite)** —
no single conjecturer folds the sum, but `atomize` (the decomposition the code exposes) → `fold_each` (each atom in its
OWN lens, z3-gated) → `recombine` (the combine operator re-verified on carry-straddle scales) does. Blind inversion of
an arbitrary sum is under-determined (P-2), so we use the code's exposed decomposition, never a guessed split. A random
atom ⇒ DECLINE; a single atom is refused.

**§2 `recall/libsig/` — scipy/numpy signal recognition (the §AN R=44 GENERALIZED).** A recurrence hidden behind a
library name is invisible to the black-box extractor. `signature_match` names the idiom (cumsum→linear, lfilter/IIR→
ARMA C-finite, EMA→geometric, moving-average→window, **popcount→M22 = the R=44 identity**, cumprod→holonomic);
`extract_recurrence` routes the oracle to that existing lens. Transcendental DFT/FFT is an honest DECLINE; a body NAMED
popcount but computing randomness DECLINEs (the z3 gate disposes, not the name).

**§3 `recall/stride/` — loop-stride recall with HETEROGENEOUS lenses.** Separated by index mod k, each substream may
need a DIFFERENT lens (the addition over §AN's BM-only stride): even→Fibonacci (C-finite via BM+multi-scale), odd→
popcount (k-automatic via M22) — the interleave is in neither class, only the separation folds it. Fast: one BM probe +
the §AL multi-scale carry-straddle held-out per substream; M22 only on logarithmic-growth data (fail-fast). A random
substream ⇒ DECLINE.

**§4 `recall/interproc/` — summarize·unalias·gather (REUSE §AI §2 stitch).** The genuine win over §AI §2 is **§4.2
unalias**: copy-propagating local state-aliases so a laundered-but-affine handler (`t = s; s = 2*t + 1`) folds instead
of false-DECLINING (the free symbol `t` made stitch alone decline). `gather` z3-proves the composition ≡ sequential.
Genuine multi-STATE coupling and non-affine updates stay honest DECLINEs.

**§5 `recall/defunctionalize.py` + `recall/bv_lia_lift.py` — the 9th & 10th disguise dimensions.** defunctionalize
RESOLVES a higher-order dispatch (`ops[select(k)](state)`) to a first-order recurrence — a periodic dispatch is a
per-residue recurrence (REUSE control_flatten), a chaotic dispatch DECLINEs. bv_lia_lift PROVES the bit→LIA identities
with z3 over bitvectors (x<<k ≡ x·2ᵏ, x>>k ≡ x//2ᵏ, x&(2ᵏ−1) ≡ x mod 2ᵏ) ∀x and **REFUTES a wrong variant of each** —
★★ S-2: these are exactly the AI hand-derived closed forms the spine demands be re-proven. Genuine bit-MIXING
(xorshift) does NOT lift and stays a DECLINE.

**§6 `recall/chc_strip/` — array-dependence removal (invariant_find·scalarize).** A self-referential array loop
(`a[i] = expr(a[i−k], i)`, fixed offsets, no external data) is a recurrence in disguise; `invariant_find` proves
scalarizability (AST) **plus a z3 CHC INDUCTIVE invariant** for the affine case (the triangular closed form satisfies
a[i]=a[i−1]+i ∀i — and a wrong closed form is refuted), and `scalarize` collapses the O(n) array loop to the O(1)/
O(log n) closed form (disposed by the existing conjecturers). A loop reading external data (`a[i]=a[i−1]+data[i]`) or a
global offset (`a[n−i]`) is an honest DECLINE.

**MEASURED (`ap_report.py`, S-3):** focused labeled-corpus recall **1.0** (9/9 disguised-foldables recalled) with
**false-EXACT 0** (7/7 adversarial non-foldables DECLINE); a real **§AK 2000-corpus re-run** of the corpus-applicable
TRANSFORMERS (chc_strip + stride) on the sampled DECLINEs → **0 promotions, false-EXACT 0** — the HONEST S-4 result:
the §AK corpus's non-foldables are genuinely non-foldable (data-dependent / transcendental / chaotic), not disguised
(compose/libsig/interproc/defunctionalize/bv_lia need structural inputs the black-box corpus doesn't expose, or don't
transform the oracle, so they are measured on the focused corpus). ★★ the AI hand-derived closed forms (bit→LIA
identities + the CHC inductive invariant) are all **z3-RE-PROVEN and a wrong variant refuted** (S-2).

`test_catalog.py` **198/198** (+7 §AP: one per mechanism + the measured report, each with ★ adversarial declines),
test_build **273×3** (recall.compose/libsig/stride/interproc/chc_strip/defunctionalize/bv_lia_lift/ap_report **not
imported** — purely additive). NO new mechanism, NO new certificate kind; LLM-free; zero-dep (z3+stdlib).
4-교차검증 recall 6종 — 합성(교차렌즈 Fib⊕popcount)·libsig(R=44 일반형)·stride(이종 렌즈)·interproc(alias 해소)·
defunc/bv→lia(9·10번째 변장, z3 비트항등식 재증명)·chc(배열의존 제거, z3 CHC 불변식) — 전부 기존 z3 게이트의
정규화기(S-1 새 메커니즘 0); 측정(S-3) focused recall 1.0·§AK 재실행 false-EXACT 0; AI 닫힌형 전부 z3 재증명(S-2);
S-4 정직(§AK 델타 ~0 = 진짜 안 접히는 것이지 변장 아님).

---

## §AQ — MATH FRAGMENTS IN NON-MATH CODE (classify → extract → reduce to the existing 22; dual-metric, z3-re-verified)

The frontier is the *deterministic math fragments* buried in I/O / parsing / network / control-flow code. ★ Everything
REDUCES to the existing 22 mechanisms — the new code is a **classification / extraction / effect-isolation pipeline**,
not new math (S-1: no new mechanism, no new disposer, no new certificate kind). Only what 4 independent reports
(GLM/Kimi/Claude/PDF) converged on AND that passes the dual-metric / Amdahl / 4-tenet gates was built.

**The governing tenets:** **S-2 (the soul)** — every AI hand-derived closed form is RE-PROVEN by z3 (observation ≠
proof; Kimi's prior hand-calc errors are exactly why); **S-3 (the dual metric, NEVER summed)** — Axis A = coverage +
verification value (we are a VERIFIED fold compiler), Axis B = program speedup (Amdahl, for §AO priority); **S-4** — the
effect system (pure/io/nondet) is the key gate; **S-5** — rebranded honest labels (Q9 upper-bound = SPEED/KoAT re-hash,
EXACT count = new; data-dependent branch → spec-declared).

**§1 `extract/classify/` — the classifier frontend (the multiplier).** `ast_tag` (layer 1, cheap shape tagging) →
`effect_gate` (layer 2, the KEY gate: pure / io / nondet — nondet is a permanent DECLINE, io makes the I/O a residual
frame) → `route` (layer 3, pure atoms → §2..§6). ★ Soundness: routing is for efficiency; a wrong route wastes one
verifier call, never causes a false fold (the z3 gate at each extractor holds precision). It multiplies the coverage of
every downstream §.

**§2 `extract/checksum/` — checksum recognition (Axis A +1, Axis B ≈0).** CRC = a GF(2)-LINEAR register map (z3 BV proves
`step(a⊕b)=step(a)⊕step(b)`) ⇒ matrix-power; Adler/Fletcher = double accumulation `n+Σ(n−i+1)dᵢ` ⇒ telescoping (z3 LIA);
Luhn/ISBN = finite digit lookup — ★★ **S-2 IN ACTION: the convenient `f(d)=2d mod 9` is z3-REFUTED at d=9** (true digit-sum
of 18 is 9, not 0) and the correct `2d−9·[d≥5]` proven; Rabin-Karp/djb2/sdbm = Horner `h=h₀·Bᴸ+Σcᵢ·B^(L−1−i)` ⇒ C-finite.
★★ **FNV resolved by z3, not by prediction**: `(h⊕b)·P` mixes GF(2)-XOR and ℤ/2ⁿ-multiply ⇒ NOT a single-algebra affine map
⇒ honest DECLINE (the 4-report split adjudicated by proof). MurmurHash3/Pearson/crypto = permanent DECLINE.

**§3 `extract/parse_arith/` — Horner (Axis A +1, highest frequency, Axis B ≈0).** Parsing IS `n=n·B+d` ⇒ C-finite Horner
(z3 LIA, atoi/base/UUID/varint); base64/IPv4 = exact disjoint-field BV pack (z3 BV, already O(1)); ★★ the Gregorian
leap-year count `⌊y/4⌋−⌊y/100⌋+⌊y/400⌋` z3-RE-VERIFIED as 400-periodic (97/cycle) and the naive Julian REFUTED (S-2);
float = integer mantissa EXACT (Horner) + ·10^e binary scaling → §AB APPROX-ε (honest split, S-5; never claimed EXACT).

**§4 `extract/periodic_fsm/` — periodic control flow.** `i%k` branch guards ⇒ period P=lcm ⇒ M_P^(N/P) matrix-power
(`stride_fold` reuses control_flatten); `k²<m` guard ⇒ exact ⌊√m⌋ count (z3-verified). ★ A DATA-dependent branch is not
a function of i ⇒ honest DECLINE (→ §5 / spec-declared).

**§5 `extract/io_arith/` — effect-isolation frame (Axis A +1, Axis B ≈0).** The separation-logic frame rule frames the
I/O off as a residual so the surrounding arithmetic folds: the alignment bit-trick `(x+a−1)&~(a−1)` == `a·⌈x/a⌉` (z3 BV);
offset=i·CHUNK (linear); TCP seq (modular BV); exponential backoff `base·(2ⁿ−1)` (geometric); token-bucket (interval-
linear). The textbook "Axis A positive, Axis B 0" case.

**§6 `extract/io_count/` — ★ Q9, the only genuinely-NEW claim.** The I/O DATA never folds, but the call COUNT is
structural: a fixed-step chunk loop does EXACTLY ⌈S/CHUNK⌉ reads (z3 LIA bracketing invariant, `requires fileSize=S`);
pagination ⌈T/P⌉, flush ⌊N/B⌋. ★★ **S-5 separation**: an EXACT count is new; an UPPER BOUND (data-driven loop /
data-driven `break`) is SPEED/KoAT/CoFloCo re-hashed and labelled as such, NOT new. ★ Axis B ≈0 (the I/O still happens —
predicting the count does not remove it); Axis A strongly positive (buffer pre-alloc / cost prediction / SLA cert /
infinite-retry detection) — the purest Axis-A-positive / Axis-B-0 contribution.

**§7 (low-priority/organizing):** Verhoeff/Damm = non-commutative quasigroup ⇒ finite-monoid matrix-power, ★ NO scalar-sum
claim (the honest line), ~0.05% frequency, completeness only. Q12 semiring lens = the organizing view ("any loop = a
semiring path problem, matrix closure"): ℕ/min-plus/Boolean/GF(2) ⇒ EXACT, probability ⇒ PROBABILISTIC (separate).

**MEASURED (`aq_report.py`, S-3):** all eight section batteries green; ★★ **every AI closed form z3-RE-PROVEN AND every
wrong variant refuted** (Luhn 2d-mod-9 @ d=9; Julian; FNV honest DECLINE) ⇒ **false-EXACT 0**; ★★ Axis A (coverage) and
Axis B (Amdahl) reported SEPARATELY and **never summed** (CRC/io/Q9 = Axis-A-positive / Axis-B-≈0; the "20-30%" over-claim
rejected); ★ honest §AK delta ~0 (the numeric corpus lacks I/O/parsing idioms — §AQ's value is on non-math code it does
not represent, M-2). new certificate kinds 0; LLM-free; zero-dep.

`test_catalog.py` **205/205** (+7 §AQ: classify / checksum / parse / periodic-FSM / io-arith / Q9 / report, each with
★ adversarial declines — nondet, MurmurHash, EXACT-vs-bound, the S-2 refutations), test_build **273×3** (extract.* /
aq_report **not imported** — purely additive). NO new mechanism, NO new certificate kind; LLM-free; zero-dep (z3+stdlib).
비수학 코드(I/O·파싱·제어흐름) 속 결정적 수학 조각 — 분류기(효과게이트 pure/io/nondet)→추출→기존 22개 환원(S-1);
체크섬(CRC=GF(2)행렬·Adler=망원·Luhn=유한룩업[2d-mod-9 d=9 반증]·Rabin-Karp=Horner·FNV 정직 DECLINE)·파싱(Horner·
윤년식 재증명)·주기FSM(i%k→행렬거듭)·I/O산술(frame rule)·Q9(EXACT I/O횟수 ⌈S/CHUNK⌉, 유일 신규); AI 닫힌형 전부
z3 재증명(S-2)·이중지표 분리(S-3 Axis B≈0)·false-EXACT 0·새 메커니즘/종류 0.

---

## §AS — ADVERSARIAL HARDENING (criticisms as proposed bugs; measurement-first; fix only what reproduces)

Three external AIs adversarially critiqued the engine's soundness, bottlenecks, and structure. §AS treats each criticism
as a **PROPOSED bug** and disposes it with our own VERIFIER — **the data, not the criticism, decides what is real**.
Discipline: **measurement-first** (a claimed hole is REAL only if a failing adversarial test REPRODUCES it; phantoms are
marked VERIFIED-SAFE with ZERO code change, §0.2 repo-first), **one fix = one regression**, and **no fix changes any
verdict** (precision 1.0 / false-EXACT 0 untouched). This is an *orthogonal hardening track* — not coverage.

**§1 `test_adversarial_soundness.py` — the arbiter (T1-T5).** Each injects an attack into the real EXACT path; SAFE iff
proven exactly under the faithful machine model OR DECLINE. **Result: 5/5 SAFE — no criticism reproduced a false-EXACT.**
- **T1 Int-vs-i64** → VERIFIED-SAFE: `pillar3/bv_validate.py` already proves rewrites over 32-bit two's-complement and
  REFUTES the ℤ-only-true peepholes (`(x+1)>x`, `(x*2)/2==x`); `idealized_vs_machine_contrast()` shows ℤ-PROVEN /
  bv-REFUTED. Python ints are bignums, so the Int-sort equiv path is ALSO faithful for the Python target.
- **T2 Real-vs-IEEE-754** → VERIFIED-SAFE: `gapfold/float_exact.py` uses z3's **IEEE-754 FloatingPoint theory** (EXACT
  only when bit-exact by rounding-mode independence; everything else APPROX-ε/DECLINE). ℝ-equivalence is never shipped as
  float-EXACT; `pillar3/interval.py` bounds overflow.
- **T3 signed/unsigned·shift/mask** → VERIFIED-SAFE: same BV gate + `recall/bv_lia_lift` (bit→LIA proven mod 2^w).
- **T4 taint false-negative** → the taint analyzer (HARAN, reflection-free) is honestly scoped ("no flow in the MODELLED
  graph") and DECLINEs unparseable input; the false-negative class is structurally N/A. ★ **The ONE reproduced gap**:
  the §AQ `effect_gate` silently classified `eval`/`exec`/`setattr` as **pure** (a §2.3 fall-through) ⇒ **FIXED** to a
  new `OPAQUE` effect that routes to DECLINE (precision untouched — the gate only routes; the z3 gate downstream always
  held precision). Regression in `effect_gate.adversarial_battery`.
- **T5 ∀/array unknown** → VERIFIED-SAFE: `equiv_check.prove_equiv_z3` returns proved=True ONLY on z3 UNSAT; sat ⇒
  DECLINE-with-counterexample, **unknown ⇒ DECLINE** (never PROVEN).

**§3 Tier-2 production robustness (precision UNTOUCHED).** ★★ **§3.1 was a REAL reproduced bug**: 24 concurrent z3 solves
**SEGFAULTED the process (rc=139)** — z3's default Context/ASTs are not thread-safe. **FIXED** with `z3_guard.py` (a global
re-entrant lock, `z3_serialized()`/`@guarded`) **wired into `equiv_check.prove_equiv_z3`** (the dominant gate); 24
concurrent solves now agree with no crash. **§3.2** `z3_guard.run_bounded` runs heavy z3/Gröbner in a child process under
`RLIMIT_AS` + a hard timeout — a C-level OOM / hang is contained, the parent survives (graceful degradation, no zombie);
`latency_budget.run_with_budget` already provides the Python-level timeout→DEFER. **§3.3** the e-graph already has a
`node_cap` + iteration bound (`egraph.saturate`) ⇒ VERIFIED-SAFE.

**§4 — 8 REJECTED criticisms (each documented in `as_report.py`, ZERO code change):** the single-file archive mistaken
for the dev tree; the "idle math core" (a measured honest ceiling); over-DECLINE (a coverage issue, not soundness);
PROBABILISTIC mixing (runtime-separated by the Verdict ADT); "k-induction only sound within K" (a misunderstanding —
proper k-induction is unbounded-sound); agent oscillation (proposer-verifier + regression gate); "ABFT duplicates proof"
(ABFT defends HARDWARE faults proofs don't cover); "PTX→adopt MLIR/Triton" (would violate zero-dependency — forbidden).

**MEASURED (`as_report.py`):** Tier-1 5/5 SAFE; 2 reproduced bugs fixed (effect-gate opaque→DECLINE; z3 concurrency) with
FAIL→PASS regressions; 4 phantom criticisms VERIFIED-SAFE (gates already exist); 8 REJECTED documented; **precision 1.0 /
false-EXACT 0 / 660 EXACT invariant** (no verdict changed). `test_catalog.py` **208/208** (+3 §AS), test_build **273**;
zero-dep (z3_guard is stdlib threading/multiprocessing/resource only). NO new mechanism, NO new certificate kind.
적대적 비판 3건을 *제안된 버그*로 보고 우리 VERIFIER로 처분 — 측정으로 재현된 것만 수정. T1-T5 전부 SAFE(게이트
이미 존재); 재현된 2건만 고침: §AQ effect-gate의 eval/exec/setattr→'pure' 폴스루를 opaque→DECLINE로(§2.3), z3 동시성
segfault(rc=139)를 z3_guard 직렬화로(equiv_check에 배선). 헛소리 8건 이유 명시·코드 0. precision 1.0·false-EXACT 0·
660 EXACT 불변(어떤 판정도 안 바뀜)·새 메커니즘/종류 0·zero-dep.

## §AY — QUANTUM LINEAR-STRUCTURE FOLD (12+1 recognition branches; NOT a new mechanism — 14/22 saturation UNCHANGED)

A dossier of "quantum/relativity" fold ideas, disposed by the spine. The GLM insight: **saturation is a PROPOSER
limit, not a z3 limit** — so every item is a NEW PROPOSER ANGLE for the EXISTING verifier (a wider recognition
aperture), reusing repo primitives (`cfinite.companion_nth`/`_matpow`, `native_sequence.berlekamp_massey_Q`/
`gf2_solve`, `gpu.hidden_structure.exact_rank_factorization`, `foldaxes.probabilistic_fold`). No quantum hardware
exists, so what actually crosses over is **classical linear-structure theorems** — the phrase "quantum-origin
speedup" is a permanently banned bigram (self-checked absent from every qfold module + `ay_report.py`).

**§0 VERIFIER TRUTH (the spine of every cert).** `prove_exact.py` admits a z3/array-induction proof of an unbounded
sequence is *out of scope*. So a ∀-n fold here NEVER comes from z3 induction — it comes from (a) a telescoping/step
identity over FINITE variables (decidable: z3 QF_LRA/QF_NRA or exact arithmetic), or (b) a STRUCTURE THEOREM
(minimal-polynomial / companion-matrix / Cayley–Hamilton / projective-linear, ∀-n by construction) gated by **exact
held-out replay**. z3/exact arithmetic only discharges finite-variable identities; no qfold cert claims "z3 proves ∀-n".

**§1.8 EXACT BOUNDARY (the false-EXACT 0 guarantee).** EXACT lives ONLY inside a structure class — commuting /
finite-invariant-subspace / low-rank / Clifford / Gaussian. Every boundary case DECLINEs: **float** (no float-EXACT,
§1-Q3) everywhere; generic dense (full displacement/bond rank); non-commuting (BCH higher-order terms); degree-growth
(Carleman lift does not close — the generic quadratic/logistic map's degree DOUBLES each step); non-Clifford (T-gate
has no symplectic representation); position-dependent transfer kernel.

**Tier-1 (EXACT, top priority).** ★ **QLA-1 Krylov/Lanczos** (`qfold/krylov.py`): a fixed iteration's moments
s_k=wᵀAᵏv fold via Berlekamp–Massey (over ℚ, REUSE native_sequence) → companion form (REUSE cfinite), gated by
held-out replay of TRUE moments beyond the BM window + an operator-level Aᴸv=Σcᵢ·Aⁱv residual-0 check (Cayley–Hamilton
on the Krylov subspace). Fibonacci ✓, random/float DECLINE. ★ **QLA-3 Carleman** (`qfold/carleman.py`): a Riccati /
linear-fractional map x'=(ax+b)/(cx+d) folds via the 2×2 PROJECTIVE lift (net-new: rational maps); a polynomial map
folds iff its monomial lift CLOSES at finite dimension (iterative closure with a degree cap) — the generic quadratic
(x²−1) and logistic (3x−3x²) maps DECLINE (degree doubles ⇒ infinite invariant subspace ⇒ no truncation-EXACT). ★
**QLA-5 displacement-rank** (`qfold/displacement.py`): one recognizer unifies Toeplitz/Hankel/Vandermonde/Cauchy
(★Hankel/Vandermonde/Cauchy net-new — hidden_structure had only Toeplitz/circulant) via exact ℚ defining-property +
displacement rank; a generic dense matrix DECLINEs. ★ **QLA-2 Cayley–Hamilton** (`qfold/cayley_hamilton.py`): a
matrix-power loop folds (χ_A via Faddeev–LeVerrier, χ_A(A)=0 entrywise residual 0, recurrence matches power-by-
squaring). ★ **QFT-1 transfer-matrix** (`qfold/transfer_matrix.py`): a path-sum Z_N=tr(Tᴺ) is C-finite (REUSE QLA-1
on the trace sequence); a position-dependent kernel ⇒ B-axis DECLINE.

**Tier-2 (PROBABILISTIC / independent witness).** ★★ **QLA-7 Hutchinson** (`qfold/hutchinson.py`) and **QLA-6
Chebyshev matrix-function** (`qfold/matfunc.py`) are graded **PROBABILISTIC with a DERIVED δ** (Roosta–Ascher
δ=2·exp(−Mε²/6); Chebyshev truncation 2M/(ρ−1)ρ^(−K)) and can NEVER be EXACT — and DECLINE when the affordable budget
can't reach the required δ (or ρ≤1 / unknown spectrum). ★ **QLA-8 tensor-train** (`qfold/tensor_train.py`): a
low-bond-rank tensor is EXACT (TT-SVD via exact ℚ RREF unfoldings, residual 0, TT storage < full), a generic full-rank
tensor DECLINEs. ★ **QT-1 stabilizer tableau** (`qfold/stabilizer.py`, net-new): a Clifford circuit (H/S/CNOT) folds
to a single 𝔽₂ symplectic matrix (SᵀΩS=Ω), self-implemented over 𝔽₂ (★ `zx_normalize.py` uses pyzx = FORBIDDEN dep,
so this is a zero-dep self-impl), cross-checked by two independent representations (matrix product ∧ tableau rules);
any T-gate (non-Clifford) ⇒ DECLINE (the magic boundary is exact).

**Tier-3 (EXACT, narrow domain).** ★ **QLA-4 BCH** (`qfold/bch.py`): e^{A₁}…e^{A_k}→e^{ΣA} iff all pairwise
commutators vanish (exact [A,B]=0); non-commuting Paulis DECLINE. ★ **REL-1 one-parameter subgroup**
(`qfold/one_param.py`): a rotation/boost power folds (REUSE QLA-2) and collinear elements compose by parameter
addition (REUSE QLA-4 commutativity); a rotation∧boost (non-commuting ⇒ Thomas–Wigner rotation) DECLINEs. ★ **QFT-2
Clifford/geometric-algebra** (`qfold/clifford.py`, self-impl — cadabra/sympy.physics.hep FORBIDDEN): GA/Dirac
equivalence decided by NORMAL FORM (e_ie_j+e_je_i=2η_ij, exact ℚ coefficients); an out-of-metric index (infinite-
dimensional operator algebra) DECLINEs. ★ **REL-2 conservation** (`qfold/conservation.py`): a verified invariant
(Q(step)=Q exactly, linear AND quadratic) folds the loop's Q-query to Q(initial), O(1); a non-invariant DECLINEs.

**§5 REJECTED / honest-DECLINE (0 code change, documented in `ay_report.py`):** Shor/quantum number theory (repackaging
— BM+NTT already exist); superfluid/Gross–Pitaevskii |ψ|²ψ (infinite Carleman lift ⇒ EXACT forbidden); Berry phase
(non-abelian path integral); **quantum chaos / random-matrix (RMT)** (non-deterministic spectrum — Wigner–Dyson level
repulsion forbids a per-eigenvalue closed form; ensemble averages only ⇒ not a ∀-input EXACT target); **Jones
polynomial = CFG semantic equivalence** (a FALSE THEOREM — the Jones polynomial is a KNOT invariant, not a
program-semantics invariant; wiring it would MANUFACTURE false-EXACT = constitutional violation; mech_knot stays
circuit/knot-only); geodesic/GPE schedulers (runtime heuristics, not proofs); SR light-cone race (repackaged
happens-before); unmeasured speedup assertions (Amdahl — every Axis-B claim needs a crossover_n).

**MEASURED (`ay_report.py`):** all 13 mechanism batteries green (EXACT-in-class + DECLINE-boundary each); **Axis A
(recognition, 11 mechanisms) and Axis B (speedup) reported SEPARATELY and NEVER summed** (QLA-6/7 are PROBABILISTIC,
out of the EXACT numerator); **false-EXACT 0**; the **banned bigram is absent** (self-check + source grep of qfold +
ay_report); **8 REJECTED** documented (0 change). `test_catalog.py` **213/213** (+5 §AY), test_build **273** (warm ×3),
**EXACT 660 invariant** (qfold is not imported by the corpus engine or test_build — pure addition). Zero-dep (stdlib
fractions/typing/math + in-repo cfinite/native_sequence/hidden_structure/kernel_verdict only; no pyzx/cadabra/
sympy.physics.hep/external tensor lib). **NO new mechanism (14/22 saturation unchanged), NO new certificate kind.**
양자 선형구조 fold 13종 = 기존 검증기의 새 proposer 인식 분기(GLM통찰: 포화는 proposer 한계지 z3 한계 아님). ∀-n은
companion/최소다항식/Cayley–Hamilton/projective 정리 + held-out replay로(z3 귀납 ✗). EXACT는 가환/유한불변/저rank/
Clifford/가우시안 구조클래스 안에서만 — 경계(부동소수·일반밀집·비가환·차수폭증·비-Clifford·위치의존)는 전부 DECLINE
⇒ false-EXACT 0. Axis A/B 분리(합산 0)·'quantum-origin speedup' 영구 금지어 부재 자가검증·기각 8건(Jones-CFG
거짓정리·RMT 비결정·측지선 휴리스틱) 코드 0.

## §AT — PROOF-CARRYING VERIFICATION (Clock B fast-lane; measurement+routing track, NOT a new mechanism/cert kind)

The §0 verifier truth (shared with §AY/§AI): z3 does NOT prove ∀-n unbounded sequences/sums — `prove_exact` says
array-induction is out of scope, and `catalog/equiv_check.prove_equiv_z3` maps z3 `unknown`/timeout → DECLINE. ∀-n
comes from a STRUCTURE THEOREM: telescoping (S(n)−S(n−1)≡body(n), a finite-variable polynomial identity) or a
companion/minimal-polynomial recurrence (∀-n by construction). §AT makes the **certificate re-checkable cheaply** —
a "proof-carrying" certificate carries the PORTABLE WITNESS (polynomial coefficients / companion (c,init) + held-out
oracle values) so the claim is re-verified WITHOUT re-running z3.

**The three clocks, never conflated** (`clocks.py`): **Clock B** = certificate-verification wall-clock (THIS track —
cheap, decidable); **Clock C** = the EMITTED code's runtime (a fold's speedup); **Axis B** = a speedup RATIO. §AT
measures ONLY Clock B and never sums it with Clock C or Axis B.

**`proof_carrying.py`** — the Clock-B fast-lane. `PCCert(recheck_kind, claim, data)` carries a portable witness;
`verify_exact_fast_lane(cert)` re-checks it (timed as Clock B) and returns EXACT iff the decidable re-check passes.
Two decidable-exact re-checkers: **telescoping_identity** (confirms S(n)−S(n−1)−body(n)≡0 by exact ℚ COEFFICIENT
comparison via the binomial expansion of (n−1)^i — a complete finite check, NOT sampling) and **companion_replay**
(replays `cfinite.companion_nth` on the carried held-out oracle tail — exact ℤ/ℚ, ∀-n by the companion theorem).
`cert_export`/`cert_import`/`recheck_exported` round-trip a cert through a portable dict and re-verify from the dict
ALONE (the proof-carrying guarantee).

**The FLIP (measured value).** `measure_flips` poses ∀-n claims (Faulhaber Σk and Σk², Fibonacci, Tribonacci) where
the pure-z3 route DECLINEs (unbounded induction out of scope) but the certificate re-check confirms EXACT — a FLIP =
z3-DECLINE ∧ cert-EXACT. **flip_count = 4/4**, with NO sampling on the EXACT lane.

**EXACT-lane purity (false-EXACT 0).** Only the two decidable-exact kinds enter the EXACT lane; any SAMPLING kind
(Schwartz–Zippel / Freivalds / Monte-Carlo) is REJECTED here (it is PROBABILISTIC only — §1.1). A TAMPERED certificate
(wrong coefficient / wrong recurrence) FAILS its re-check ⇒ DECLINE, never a false-EXACT.

**MEASURED (`pc_report.py`):** flip_count 4/4 (z3-DECLINE → cert-EXACT); Clock B reported on its own (a few ms total),
never summed with Clock C / Axis B; sampling NOT used on the EXACT lane; tampered cert DECLINEs (false-EXACT 0);
export→import→re-check portability holds. `test_catalog.py` **215/215** (+2 §AT), test_build **273** (warm ×3), corpus
**EXACT 660 invariant** (proof_carrying/pc_report not imported by the corpus engine — pure addition). Zero-dep (stdlib
fractions/math + in-repo cfinite/clocks/kernel_verdict). **NO new mechanism (14/22 unchanged), NO new certificate kind**
(EXACT certs use the existing `exact_replay` kind).
증명서휴대 검증(Clock B 빠른길): 증명서가 휴대 가능한 witness(다항식 계수 / companion c,init + held-out 오라클)를
담아 결정적·정확 재검(텔레스코핑 계수영 / companion replay)으로 z3 없이 재확인 — z3가 못하는 ∀-n(배열귀납
out-of-scope→DECLINE)을 EXACT로 되살림. 측정값 = FLIP 4/4(z3-DECLINE→cert-EXACT). 3 클락 불혼동: Clock B(증명서
검증)≠Clock C(방출코드 런타임)≠Axis B(가속비) — 합산 0. EXACT 레인은 샘플링(SZ/Freivalds) 금지(PROBABILISTIC
전용)·틀린 증명서는 재검 실패 ⇒ false-EXACT 0. `test_catalog 215/215`·test_build 273×3·EXACT 660 불변·새 메커니즘/
증명서 종류 0.

## §AU — THE SECOND CLASSICAL-SIMULATION ISLAND: free-fermion / Gaussian fold (flagship module + 6 hooks)

The structural discovery (doc 14): there are exactly TWO efficiently-classically-simulable islands of quantum-style
computation, closed under DIFFERENT algebras — ① Clifford / stabilizer (Sp(2n,𝔽₂), built in §AY/`qfold.stabilizer`)
and ② free-fermion / Gaussian / matchgate (Pfaffian · covariance · symplectic, built here). Their intersection is
small and their UNION is still NOT universal QC (Gottesman–Knill ∪ Valiant ⊊ BQP) — so EXACT lives only inside one
island, and every boundary DECLINEs with a NAMED THEOREM.

**§0 verifier truth** (shared spine): ∀-(2n)/∀-N is the Wick / covariance / companion THEOREM (NOT z3 induction),
gated by exact arithmetic + held-out replay; z3/exact only discharges FINITE identities (Pf²=det, RᵀR=I / SΩSᵀ=Ω,
C²−C=0, structure constants, H_X H_Zᵀ=0, hook-length). EXACT only for integer/rational data; float ⇒ DECLINE.

**FLAGSHIP `mathmode/free_fermion.py`** (a NEW MODULE — the quadratic-form algebra is genuinely independent of the
𝔽₂ stabilizer and of `hidden_structure`'s matrix-rank, so a separate file is justified; zero external deps, the
Pfaffian is a rational skew-LU self-impl, NOT pyzx). ★ **FF-1 Wick→Pfaffian**: `pfaffian_Q` (Parlett–Reid O(n³),
exact ℚ) — a free 2n-point function = Pf(A); cert = Wick theorem + Pf²=det + small-n combinatorial pairing-sum
replay; `is_wick_consistent` is the free-vs-interacting discriminator (a connected/interacting higher correlator ≠
its Pfaffian reduction ⇒ DECLINE). ★ **FF-3 Bogoliubov** `gaussian_evolve`: Γ→RΓRᵀ with R∈O(2n), N steps fold to
Rᴺ via `cfinite._matpow`; GATE RᵀR=I (non-orthogonal ⇒ non-Gaussian ⇒ DECLINE). ★ **CV-1** `gaussian_cv_evolve`: the
bosonic symplectic version (SΩSᵀ=Ω, Ω=[[0,I],[−I,0]]; non-symplectic ⇒ Hudson ⇒ DECLINE). ★ **FF-4 Jordan–Wigner**
`jw_is_quadratic`: transverse-field Ising / XY-type nearest-neighbour ⇒ free (route to FF-1/3); a ZZ coupling (XXZ
Δ≠0 / Heisenberg) ⇒ quartic ⇒ interacting ⇒ DECLINE. ★ **FF-2 Peschel** `peschel_entropy`: S_A reduces EXACTLY to
the single-particle correlation spectrum when C²=C (pure free state); a mixed C (C²≠C) ⇒ DECLINE; Axis-B only. ★
matchgate ≡ free-fermion ⇒ amplitude = Pfaffian (FF-1) — the island `qfold.stabilizer` cannot capture.

**Hooks (new recognition branches, 14/22 UNCHANGED, each REUSES a primitive).** ★ **KOOP** `island_hooks.koopman_lift`
(reuses the `qfold.carleman` poly engine): a finite Koopman-invariant observable subspace makes a nonlinear map
EXACTLY linear (g_i∘F=Σ A_ij g_j) ⇒ C-finite; an escaping observable (mixing chaos / degree-growth) ⇒ DECLINE. ★
**TW** `extract/tensor_contract.py` (NEW; no treewidth code existed): tensor-contraction = treewidth — a min-fill
variable elimination folds a sum-product when the induced width ≤ cap (VE ≡ naive sum, exact ℚ); high treewidth /
2D-grid (2D PEPS exact = #P-hard, Schuch+ 2007) ⇒ DECLINE. ★ **LIE-1/2** `wei_norman_fold` / `magnus_terminate`: a
finite Lie algebra ([X_i,X_j]∈span{X_k}) ⇒ Wei–Norman closed ODE; a nilpotent algebra ⇒ Magnus Ω terminates;
infinite-dim / non-nilpotent (sl(2)) ⇒ DECLINE. ★ **CODE-1** `css_logical` (reuses `native_sequence.gf2_solve` + 𝔽₂
linear algebra): a valid CSS code (H_X H_Zᵀ=0) ⇒ k=n−rank(H_X)−rank(H_Z) logical qubits; non-commuting ⇒ DECLINE. ★
**SW** `schur_weyl_dim`/`hook_product`: dim S_λ = n!/∏hook (exact integer, cross-checked ≡ #standard Young tableaux);
the 6j×Zeilberger link **REUSES `mathmode.telescoping.zeilberger`** (★ §5.5: NOT reimplemented); U_q deformation ⇒
DECLINE.

**§5 REJECTED walls (each a NAMED THEOREM, 0 code change):** interacting models (Wick/Isserlis is quadratic-only;
JW-ZZ = quartic); volume-law entanglement (Page / area-law); 2D PEPS exact contraction (#P-hard, Schuch+); high
treewidth (Markov–Shi); non-Gaussian CV (Hudson); non-Clifford ∧ non-matchgate (Gottesman–Knill ∪ Valiant ⊊ BQP);
mixing-chaos Koopman (continuous spectrum); Jones-CFG semantic equivalence (FALSE THEOREM — would manufacture
false-EXACT); Shor=BM+NTT, GP=∞-invariant, RMT=non-deterministic spectrum, Berry/geodesic/GPE/light-cone heuristics.
★ Zeilberger/creative-telescoping re-submission FORBIDDEN — `mathmode.telescoping.zeilberger` already exists, reused.

**MEASURED (`au_report.py`):** all 3 batteries green (flagship 10/10 + hooks 11/11 + TW 4/4); two-island boundary
documented (union ⊊ universal QC); Axis A/B separated, never summed; **false-EXACT 0**; banned bigram absent
(self-check + source grep); Zeilberger REUSED not reimplemented; 8 REJECTED walls. `test_catalog.py` **218/218**
(+3 §AU), test_build **273** (warm ×3), corpus **EXACT 660 invariant** (the new modules are not imported by the corpus
engine — pure addition). Zero-dep (rational skew-LU Pfaffian + 𝔽₂ gf2_solve self-impl; no pyzx/cadabra/external tensor
lib). **NO new mechanism (14/22 unchanged), NO new certificate kind.**
두 번째 고전시뮬 섬(자유페르미온/가우시안: Pfaffian·공분산·심플렉틱)을 신규 모듈 `mathmode/free_fermion.py`(FF-1
Pfaffian·FF-3 Bogoliubov·FF-2 Peschel·FF-4 JW·CV-1 심플렉틱) + 6 인식 분기(KOOP·TW·LIE-1/2·CODE-1·SW)로 추가 —
14/22 불변. EXACT는 두 섬(Clifford 𝔽₂ ∧ 자유페르미온/가우시안) 안에서만, 경계는 전부 이름붙은 정리로 DECLINE(상호
작용=Wick·2D PEPS=#P-hard·비가우시안=Hudson·고treewidth=Markov-Shi·mixing=연속스펙트럼). Zeilberger 재사용(재구현 0,
§5.5)·zero-dep self-impl(pyzx/cadabra 부재)·금지 bigram 부재·새 메커니즘/증명서 종류 0.

## §AZ — math-mode CAPABILITY LEDGER expansion (decision/proof power; ★fold-rate impact 0, capability ≠ fold-rate)
**Identity (nailed first):** this widens the class of math structures JEFF can DECIDE / PROVE / normalize — it does NOT
raise the fold rate (the corpus fixes that; the engine is at a measured plateau, unchanged). Every item below has
**fold-rate impact 0**; the deliverable is the capability ledger, not a corpus number. ★ Highest value = the completion
of HONEST_DEFER: turning UNKNOWN/timeout DECLINEs into **theorem-backed PROVEN DECLINEs** (precision 1.0 preserved). All
entries are NEW decision branches in EXISTING math-mode modules (0 new files; **14/22 mechanism count UNCHANGED**;
zero-dep self-impl; repo-first — §B re-submissions NOT rebuilt, confirmed by diff).

BUILT (6/8) — each with a decision-YES test AND a PROVEN-DECLINE/boundary test:
- **CAP-1 Morales-Ramis** (`lagrangian.morales_ramis_nonintegrable`/`_from_nve`) — PROVE Hamiltonian NON-integrability:
  build the normal variational equation along the y=0 invariant line (energy reduction, exact ℚ(x)) → REUSE the existing
  `decision_integration.kovacic_liouvillian` (repo-first, 0 re-impl) → Kovacic case-4 (no Liouvillian sol ⇒ Galois SL₂,
  G⁰ non-abelian) ⇒ ★PROVEN NON-INTEGRABLE. Liouvillian ⇒ UNDECIDED (necessary condition — "integrable" NEVER claimed).
- **CAP-2 Darboux/Prelle-Singer** (`decision_integration.darboux_first_integral`) — DECIDE a polynomial first integral of
  dy/dx=P/Q (X(H)=Q·H_x+P·H_y≡0) up to degree d; EXACT (H found, X(H)≡0 verified) or ★PROVEN bounded DECLINE.
- **CAP-4 Sylvester** (`linear_algebra.sylvester_solvable`) — unique solvability of AX+XB=C via Res(χ_A,χ_{−B}) (self-impl
  resultant = Bareiss-det of the Sylvester matrix; eigenvalues never computed); EXACT (Kronecker solve + AX+XB=C
  re-substitution) or ★PROVEN no-unique-solution (Res=0, spectra overlap).
- **CAP-5 Frobenius ℚ-similarity** (`linear_algebra.similar_decide`) — invariant factors of xI−A via determinantal
  divisors (ℚ[x]); ★bypasses the degree≥5 eigenvalue wall (stays in ℚ[x]); EXACT similar / ★PROVEN A≁B.
- **CAP-6 Jordan/Weyr** (`linear_algebra.jordan_structure`) — exact block sizes at ℚ-rational eigenvalues from the
  nullity sequence of (A−λI)^k; non-ℚ-rational spectrum ⇒ honest extension-needed DECLINE.
- **CAP-7 algebraic GF/transcendence** (`holonomic.algebraic_generating_function`) — DECIDE algebraicity of an OGF by a
  bounded bidegree ansatz P(z,F)=0 (held-out replay certificate); EXACT (e.g. Catalan zC²−C+1=0) or ★bounded
  TRANSCENDENCE certificate (e.g. exp Σz^k/k!).

DEFERRED (2/8) — HONEST, soundness-critical (precision 1.0 forbids shipping an unverified decision; the directive itself
permits UNKNOWN/OUT_OF_SCOPE for CAP-3):
- **CAP-3 order≥3 differential-Galois reducibility** (eigenring) — a sound "PROVEN non-Liouvillian" for order≥3 needs
  full Ore-operator eigenring + irreducibility machinery with real false-EXACT risk; deferred rather than overclaim.
- **CAP-8 Chyzak multivariate creative telescoping** — multivariate Ore-Gröbner telescoper discovery is heavy and
  error-prone; the existing single-index `telescoping.zeilberger` already covers the verified one-index case.

REJECTED (§4, code change 0; confirmed not rebuilt by diff): document-14's 5 re-submissions — Kovacic(order 2),
Petkovšek, q-Zeilberger, Smith(ℤ), Sturm are ALL already implemented; CAP-1 REUSES kovacic_liouvillian, CAP-5 is the
NET-NEW ℚ[x]/similarity generalization (not the ℤ Smith). Verifier truth: every cert is exact ℚ/ℚ[x]/symbolic +
held-out — NO "z3 proves ∀-n". Gates: test_build 273, test_catalog 223→229 (+6 CAP tests), corpus EXACT 660 invariant
(the new branches are NOT imported by the corpus engine — pure capability addition).


## §HANDOFF-ARCHIVE — prior per-campaign onboarding rows (moved verbatim from HANDOFF.md, §BF FIX-4)

These 43 per-campaign essay rows were the bulk of the old HANDOFF.md (the longest was 3,138 chars — an onboarding doc nobody could read). They are the build HISTORY; the live current state stays in `STATUS.md` and the trimmed one-page `HANDOFF.md`. Preserved verbatim here so nothing is lost.

| 항목 | 값 |
|---|---|
| FRONT-END | **프로브 캐스케이드(구조 탐지) + 검증된 리프팅(코드 번역) + Topic A(상수배 가속) — 폴드 가능 분모 확대.** 무의존(z3+stdlib+numpy+sympy; 감사 `forbidden_present==[]`). ★중심 불변식(제안자–검증자): 탐지·리프팅은 *제안자*(liberal), 인증은 *처분자*(EXACT, 위양성 0) — 정확 인증서 통과 없이는 절대 fold 안 됨. 측정(`catalog/frontend_report.py`): **recall 1.0, PRECISION = 1.0(위양성 0), lift-rate 1.0, B-core 10/10 유지**. PHASE A/B 프로브 캐스케이드(`probe_cascade.py`·`detectors_b.py`): 최저비용 우선·hit시 상승, 각 단계 정확산술 게이트 — 단계0 압축성+monobit/runs 스크린(비압축AND무작위→즉시 DECLINE), 1 BM C-finite+유한차분 다항식, 2 FFT→Prony, 3 정수관계(LLL)/Re-Pair SLP, 행렬→정확 rank-revealing; NIST SP800-22를 타입드 디스패처로. PHASE C/D 검증된 리프팅(`equiv_check.py`·`lift.py`): z3 ∀-동치+**귀납적 합 증명(ℝ상)** 기질이 리프팅을 게이트 — 명령형 루프 → 닫힌형 합성 → z3 귀납 증명 → fold(Σk/Σk²/Σk³ 등); 비용게이트가 cold 코드 거부, 비리프팅→DECLINE. PHASE E Topic A(`topic_a.py`): 폴드·리프트 안 되는 코드에 인증된 **상수배** 가속(점근 불변 명시) — equality saturation/translation validation(불건전 x*2→x+1 반증)/superopt. 인증서 tier 기록(z3 강 vs bounded). 위양성 0(보안 CSPRNG/비압축/정지/full-rank/비리프팅 → 전경로 DECLINE). `test_catalog.py` **43/43**, test_build 273 영향 없음. 상세: `BUILD_LOG_catalog.md` §E. ──────── (이전) |
| math-mode 능력 원장 확장 (§AZ) | **★정체성: 능력(capability) 확장이지 fold율 상승 아님 — 모든 항목 fold율 영향 0(코퍼스가 정함·plateau 불변). JEFF가 판정/증명/정규화하는 수학 구조 클래스를 넓힌다. 최고 가치 = HONEST_DEFER 완성(UNKNOWN/타임아웃 DECLINE → *정리로 증명된* PROVEN DECLINE, precision 1.0 보존). 전부 기존 math-mode 모듈의 새 결정분기(신규파일 0·14/22 메커니즘 불변·zero-dep self-impl·repo-first[§B 재제출 0, diff로 확인]). §0 검증기 진실: 전 cert 정확 ℚ/ℚ[x]/symbolic+held-out, 'z3가 ∀-n 증명' 0. **건설 6/8**(각 결정-YES + PROVEN-DECLINE 테스트): ★CAP-1 Morales-Ramis(`lagrangian.morales_ramis_*` — y=0 불변선 NVE를 에너지환원으로 추출→*기존* `decision_integration.kovacic_liouvillian` 재사용→Kovacic case-4[비-Liouville⇒Galois SL₂·G⁰비가환]⇒★해밀토니안 비적분 PROVEN; Liouville⇒UNDECIDED[적분가능 절대 주장 안 함]) · CAP-2 Darboux/Prelle-Singer(`decision_integration.darboux_first_integral` — dy/dx=P/Q 다항 제1적분 X(H)=0, EXACT 또는 ★유계 PROVEN-DECLINE) · CAP-4 Sylvester(`linear_algebra.sylvester_solvable` — AX+XB=C 유일가해 Res(χ_A,χ_{−B})≠0[self-impl resultant=Sylvester행렬 Bareiss det·고유값 안 구함]+Kronecker 재대입 / Res=0⇒★PROVEN 비유일) · CAP-5 Frobenius ℚ-상사(`linear_algebra.similar_decide` — xI−A 불변인자[행렬식약수, ℚ[x]에 머묾⇒★degree≥5 고유값벽 우회]; similar / ★PROVEN A≁B) · CAP-6 Jordan/Weyr(`linear_algebra.jordan_structure` — ℚ-유리고유값 블록크기 nullity 수열; 비유리⇒정직 extension-needed DECLINE) · CAP-7 대수적 GF/초월성(`holonomic.algebraic_generating_function` — 유계 bidegree ansatz+held-out replay; Catalan zC²−C+1=0 EXACT / exp ★유계 초월 certificate). **기각 §B(코드 0, diff 확인)**: 문서14의 Kovacic(order2)·Petkovšek·q-Zeilberger·Smith(ℤ)·Sturm 5종 이미 구현(재구현 0; CAP-1은 kovacic 재사용·CAP-5는 net-new ℚ[x] 일반화). **연기 2/8**(정직·건전성 임계, overclaim 금지): CAP-3 order≥3 미분갈루아(eigenring)·CAP-8 다변수 Chyzak — 둘 다 false-EXACT 위험이라 미출하(directive가 UNKNOWN/OUT_OF_SCOPE 허용). 측정: `test_catalog 223→229`(+6 CAP)·test_build 273(격리 273/0; 동시부하 1건 flake=C6 perf, 격리 재실행 clean)·**EXACT 660 불변**(신규 분기 코퍼스엔진 미import—순수가산). 상세: `BUILD_LOG_catalog.md §AZ`. ──────── (이전) |
| 두 번째 고전시뮬 섬: 자유페르미온/가우시안 (§AU) | **구조적 발견(문서14): 효율적 고전시뮬 섬은 *둘* — ① Clifford/stabilizer(Sp(2n,𝔽₂), §AY `qfold.stabilizer`) ∧ ② 자유페르미온/가우시안/matchgate(Pfaffian·공분산·심플렉틱, 이번 신규). 서로 다른 대수로 닫힘, 교집합 작고, **둘 합쳐도 universal QC 미달**(Gottesman–Knill ∪ Valiant ⊊ BQP) ⇒ EXACT는 한 섬 안에서만, 경계는 *이름붙은 정리*로 DECLINE. **§0 진실**: ∀-(2n)/∀-N은 Wick/공분산/companion 정리(z3 귀납 ✗)+held-out replay; z3는 유한 항등식만(Pf²=det·RᵀR=I·SΩSᵀ=Ω·C²−C=0·구조상수·H_X H_Zᵀ=0·hook-length). 정수/유리만 EXACT·부동소수 DECLINE. **FLAGSHIP `mathmode/free_fermion.py`**(신규 모듈 — 이차형식 대수는 𝔽₂ stabilizer와도 hidden_structure와도 독립이라 정당; zero-dep, Pfaffian은 유리수 skew-LU self-impl, pyzx 아님): ★FF-1 Wick→Pfaffian(`pfaffian_Q` Parlett–Reid O(n³); 자유 2n점=Pf(A), cert=Wick+Pf²=det+조합 쌍짓기합 replay; `is_wick_consistent`가 자유-vs-상호작용 판별 — connected 상관자≠Pf ⇒ DECLINE) ★FF-3 Bogoliubov `gaussian_evolve`(Γ→RΓRᵀ, R∈O(2n), Rᴺ via `cfinite._matpow`; GATE RᵀR=I; 비직교⇒비가우시안 DECLINE) ★CV-1 `gaussian_cv_evolve`(보손 심플렉틱 SΩSᵀ=Ω; 비심플렉틱⇒Hudson DECLINE) ★FF-4 Jordan–Wigner `jw_is_quadratic`(횡Ising/XY=자유→FF-1/3; ZZ[XXZ Δ≠0/Heisenberg]=사차→상호작용 DECLINE) ★FF-2 Peschel `peschel_entropy`(C²=C 순수 자유상태면 S_A가 단입자 스펙트럼으로 정확 환원; 혼합 C²≠C⇒DECLINE; Axis-B만) ★matchgate≡자유페르미온⇒진폭=Pfaffian(stabilizer 섬이 못 잡음). **HOOKS(새 인식 분기·14/22 불변·각 primitive 재사용)**: ★KOOP `island_hooks.koopman_lift`(qfold.carleman poly 엔진 재사용: 유한 Koopman 불변 관측가능 부분공간이면 비선형 F가 정확 선형 g_i∘F=ΣA_ij g_j⇒C-finite; 이탈[mixing/차수폭증]⇒DECLINE) ★TW `extract/tensor_contract.py`(신규: 텐서수축=treewidth, min-fill 변수소거가 sum-product를 induced width≤cap일 때 fold[VE≡소박합]; 고treewidth/2D PEPS #P-hard⇒DECLINE) ★LIE-1/2 `wei_norman_fold`/`magnus_terminate`(유한 리 대수⇒Wei–Norman 닫힌 ODE; 멱영⇒Magnus Ω 종료; 무한차원/비멱영 sl(2)⇒DECLINE) ★CODE-1 `css_logical`(`native_sequence.gf2_solve`+𝔽₂ 재사용: H_X H_Zᵀ=0이면 k=n−rank−rank 논리큐빗; 비가환⇒DECLINE) ★SW `schur_weyl_dim`/`hook_product`(dim S_λ=n!/∏hook 정확 정수, ≡SYT 카운트 교차검증; 6j×Zeilberger 링크는 `mathmode.telescoping.zeilberger` **재사용**[★§5.5: 재구현 0]; U_q⇒DECLINE). **§5 기각 벽(각 이름붙은 정리·코드 0)**: 상호작용(Wick=이차전용)·부피법칙얽힘(Page/area-law)·2D PEPS(#P-hard Schuch+)·고treewidth(Markov–Shi)·비가우시안 CV(Hudson)·비-Clifford∧비-matchgate(G-K∪Valiant⊊BQP)·mixing Koopman(연속스펙트럼)·Jones-CFG(거짓정리). 측정(`au_report.py`): 3 배터리 green(flagship 10+hooks 11+TW 4)·두 섬 경계·Axis A/B 분리·**false-EXACT 0**·금지 bigram 부재·Zeilberger 재사용·8 기각 벽. `test_catalog 218/218`(+3 §AU)·test_build 273×3·**EXACT 660 불변**(신규 모듈 코퍼스엔진 미import—순수가산)·zero-dep(skew-LU Pfaffian+gf2_solve self-impl, pyzx/cadabra 부재)·새 메커니즘/증명서 종류 0. ──────── (이전) |
| 증명서휴대 검증 / Clock B (§AT) | **§0 검증기 진실(§AY/§AI 공유): z3는 ∀-n 무한 수열/합을 증명 못 함 — `prove_exact`가 배열귀납 out-of-scope라 자백, `equiv_check`가 z3 unknown/timeout→DECLINE. ∀-n은 구조 정리(텔레스코핑 S(n)−S(n−1)≡body(n) 유한변수 다항 항등식 / companion·최소다항식 점화, 구성상 ∀-n)로만. §AT는 *증명서를 싸게 재검 가능*하게 만든다 — '증명서휴대' cert가 *휴대 가능한 witness*(다항식 계수 / companion c,init + held-out 오라클 값)를 담아 z3 재실행 없이 재확인. **3 클락 불혼동**(`clocks.py`): **Clock B**=증명서검증 벽시계(이 트랙·싸고 결정적)≠**Clock C**=방출코드 런타임(fold 가속)≠**Axis B**=가속 비율. §AT는 Clock B만 측정, Clock C/Axis B와 절대 합산 안 함. **`proof_carrying.py`**: `PCCert(recheck_kind,claim,data)`+`verify_exact_fast_lane`(Clock B 타이밍, 결정적 재검 통과시만 EXACT); 결정적-정확 재검 2종 — telescoping_identity(S(n)−S(n−1)−body(n)≡0을 (n−1)^i 이항전개로 정확 ℚ *계수* 비교 — 완전한 유한검사, 샘플링 아님)·companion_replay(`cfinite.companion_nth`를 휴대된 held-out 오라클 꼬리에 replay — 정확 ℤ/ℚ, companion 정리로 ∀-n); `cert_export`/`cert_import`/`recheck_exported`가 cert를 portable dict로 왕복+dict만으로 재검(증명서휴대 보증). **FLIP(측정값)**: ∀-n 주장(Faulhaber Σk·Σk², Fibonacci, Tribonacci)에서 순수 z3는 DECLINE(무한 귀납 out-of-scope)인데 cert 재검은 EXACT ⇒ FLIP=z3-DECLINE∧cert-EXACT, **4/4**·EXACT 레인 샘플링 0. **EXACT 레인 순수성(false-EXACT 0)**: 결정적-정확 2종만 EXACT 레인 진입·샘플링류(SZ/Freivalds/Monte-Carlo)는 *기각*(PROBABILISTIC 전용·§1.1)·틀린 증명서(계수/점화 오류)는 재검 *실패*⇒DECLINE. 측정(`pc_report.py`): flip 4/4·Clock B 단독 보고(수 ms, 합산 0)·EXACT 레인 샘플링 미사용·tampered DECLINE·export/import 왕복 OK. `test_catalog 215/215`(+2 §AT)·test_build 273×3·**EXACT 660 불변**(proof_carrying/pc_report 코퍼스엔진 미import — 순수가산)·zero-dep(stdlib+cfinite/clocks/kernel_verdict)·새 메커니즘 0(14/22 불변)·새 증명서 종류 0(기존 `exact_replay` 사용). ──────── (이전) |
| 양자 선형구조 fold 13종 (§AY) | **dossier '양자/상대성' fold 아이디어를 헌법으로 처분 — GLM통찰: 포화는 *proposer* 한계지 z3 한계 아님 ⇒ 12+1 항목 전부 기존 검증기의 *새 인식 분기*(새 메커니즘 0·14/22 불변·새 증명서 종류 0), repo 원시함수 재사용(`cfinite`·`native_sequence` BM/gf2_solve·`hidden_structure` RREF·`probabilistic_fold`). 양자 HW 없음 ⇒ 넘어오는 건 *고전 선형구조 정리뿐*, 'quantum-origin speedup'은 영구 금지 bigram(자가검증). **§0 검증기 진실**(척추): `prove_exact`가 ∀-n z3-array-induction은 out-of-scope라 자백 ⇒ ∀-n은 (a)유한변수 텔레스코핑/step 항등식 또는 (b)구조 정리(최소다항식/companion/Cayley–Hamilton/projective)+**exact held-out replay**로만; z3는 유한 항등식만. **§1.8 EXACT 경계(false-EXACT 0)**: 가환/유한불변/저rank/Clifford/가우시안 안에서만 — 경계 전부 DECLINE(★부동소수·일반밀집·비가환·차수폭증·비-Clifford·위치의존). **T1**: QLA-1 Krylov(`qfold/krylov.py` 모멘트→BM→companion+held-out+잔차0)·QLA-3 Carleman(`carleman.py` Riccati 사영lift[net-new]·일반 2차/로지스틱 차수폭증 DECLINE)·QLA-5 displacement(`displacement.py` Toep/Hank/Vand/Cauchy 통합·★Hank/Vand/Cauchy net-new)·QLA-2 Cayley–Hamilton·QFT-1 transfer-matrix(tr(Tᴺ) C-finite). **T2**: ★★QLA-7 Hutchinson·QLA-6 Chebyshev = PROBABILISTIC 유도δ NEVER EXACT·QLA-8 tensor-train(저 bond rank EXACT)·QT-1 stabilizer(`stabilizer.py` net-new: Clifford→𝔽₂ symplectic self-impl[★zx_normalize=pyzx 금지dep], T게이트 DECLINE). **T3**: QLA-4 BCH·REL-1 1-param subgroup·QFT-2 Clifford/기하대수(`clifford.py` self-impl[cadabra 금지])·REL-2 보존. **§5 기각 8건**(코드 0): Shor·GP·Berry·★RMT(비결정)·★Jones=CFG(거짓정리)·측지선·SR race·무측정 speedup. 측정(`ay_report.py`): 13 배터리 green·Axis A(11)/B 분리 합산금지(QLA-6/7 PROB EXACT 분자 제외)·**false-EXACT 0**·금지 bigram 부재·기각 8건 0변경. `test_catalog 213/213`(+5 §AY)·test_build 273×3·**EXACT 660 불변**(qfold 미import — 순수가산)·zero-dep·새 메커니즘/종류 0. ──────── (이전) |
| 적대적 경화: 비판을 제안된 버그로 (§AS) | **3개 외부 AI의 건전성 적대 비판을 *제안된 버그*로 보고 우리 VERIFIER로 처분 — ★데이터(비판 아님)가 진위를 가른다. 직교 *경화 트랙*(커버리지·검증-tractability와 별개). **measurement-first**(주장한 구멍은 실패 테스트로 *재현*돼야 REAL; phantom은 VERIFIED-SAFE·코드 0)·**repo-first**(게이트 이미 있으면 재구현 0)·**수정 1개=회귀 1개**·**어떤 수정도 판정 불변**(precision 1.0/false-EXACT 0). **§1 `test_adversarial_soundness.py`(중재자, T1-T5)**: 각 공격을 실제 EXACT 경로에 투입 → **5/5 SAFE**(false-EXACT 재현 0). T1 Int-vs-i64·T3 부호/시프트 → VERIFIED-SAFE(`pillar3/bv_validate.py`가 32비트 2의보수로 증명, ℤ-only 재작성[(x+1)>x·(x*2)/2] REFUTE; Python int=bignum이라 ℤ-sort도 충실); T2 Real-vs-IEEE → VERIFIED-SAFE(`gapfold/float_exact.py`가 z3 IEEE-754 FP 이론으로 bit-exact일 때만 EXACT, 아니면 APPROX-ε/DECLINE; ℝ를 float-EXACT로 출하 안 함); T5 ∀/array unknown → VERIFIED-SAFE(`equiv_check` UNSAT일 때만 PROVEN, unknown→DECLINE). ★T4 taint: HARAN은 reflection-free라 false-negative 클래스 N/A·정직 범위('모델 그래프 내 무흐름')지만 — **재현된 단 하나의 §2.3 갭**: §AQ `effect_gate`가 eval/exec/setattr를 *조용히 pure*로(폴스루) → **FIX**: `OPAQUE` 효과 신설→DECLINE-라우트(precision 불변, 게이트는 라우팅만). **§3 Tier-2(precision 미접촉)**: ★★**§3.1 진짜 재현 버그** — 24-스레드 동시 z3가 **segfault(rc=139)**(z3 기본 Context 비-thread-safe) → **FIX** `z3_guard.py`(전역 직렬화 락, `equiv_check`에 배선); 24동시 solve 일치·무크래시. §3.2 `z3_guard.run_bounded`(RLIMIT_AS+하드타임아웃 자식프로세스 → C-OOM/행 격리, 부모 생존); §3.3 e-graph node_cap 이미 존재 → VERIFIED-SAFE. **§4 기각 8건**(`as_report.py`, 코드 0): 단일파일 아카이브 오인·유휴 수학코어(측정된 정직 천장)·over-DECLINE(커버리지지 건전성 아님)·PROBABILISTIC 분리(ADT 런타임 강제)·k-귀납 오해(무계 건전)·에이전트 진동(proposer-verifier+회귀게이트)·ABFT(HW결함 방어, proof와 직교)·PTX→MLIR(zero-dep 위반·금지). 측정: `test_catalog 208/208`(+3 §AS)·test_build 273·**EXACT 660 불변**(seed 20260628, false-EXACT 0)·zero-dep(z3_guard=stdlib). 새 메커니즘/종류 0. 재현된 2건만 수정, 나머진 VERIFIED-SAFE/기각 — *정직한 비판 수용*. ──────── (이전) |
| 비수학 코드 속 수학 조각 추출기 (§AQ) | **비수학(I/O·파싱·네트워크·제어흐름) 코드 속 *결정적 수학 조각*을 추출 — ★전부 기존 22개로 환원(S-1: 새 메커니즘 0·새 disposer 0·새 증명서 종류 0), 새거는 *분류·추출·효과격리 파이프라인*이지 새 수학 아님. 4개 보고서(GLM/Kimi/Claude/PDF) 수렴분 중 *이중지표·Amdahl·4철칙 통과분만*. **S-2(영혼)**: AI 손유도 닫힌형 전부 z3 ∀-재증명(관찰≠증명, Kimi 손계산 오류가 이 게이트가 필요한 이유). **S-3(이중지표·절대 합산금지)**: Axis A=커버리지+검증가치(우린 *검증 fold 컴파일러*) / Axis B=프로그램 speedup(Amdahl, §AO용). **§1 `extract/classify/`**(곱셈기): ast_tag→★effect_gate(pure/io/nondet, 핵심 게이트)→route; nondet 영구 DECLINE, io는 잔차 frame; 라우팅 틀려도 z3가 precision 보장. **§2 체크섬**(Axis A+1, Axis B≈0): CRC=GF(2)-선형(z3 BV)→행렬거듭, Adler=망원합, Luhn=유한룩업 — ★★S-2 발동: 편한 `2d mod 9`를 z3가 d=9에서 *반증*(18의 자릿수합=9≠0), 올바른 `2d−9·[d≥5]` 증명; Rabin-Karp/djb2=Horner C-finite; ★★FNV는 z3가 판정 — (h⊕b)·P는 GF(2)-XOR와 ℤ/2ⁿ-곱 혼합이라 단일대수 아핀 아님 ⇒ 정직 DECLINE(예측 아닌 증명으로 4보고서 분열 해소); MurmurHash/Pearson/암호 영구 DECLINE. **§3 파싱**(Axis A+1, 최고빈도): Horner `n·B+d`→C-finite(atoi/base/varint), base64/IPv4=정확 BV 팩(O(1)), ★★윤년식 ⌊y/4⌋−⌊y/100⌋+⌊y/400⌋ z3 재검증(400주기 97/cycle, Julian 반증), float=정수만티사 EXACT+·10^e §AB APPROX-ε(정직 분리). **§4 주기FSM**: i%k 가드→주기 P=lcm→행렬거듭(control_flatten 재사용), k²<m→정확 ⌊√m⌋; 데이터의존 분기는 정직 DECLINE. **§5 I/O산술**(frame rule): 정렬 (x+a−1)&~(a−1)=a·⌈x/a⌉(z3 BV)·오프셋·TCP seq·백오프 — I/O는 잔차, 주변 산술만 폴드. **§6 ★Q9**(유일 신규): I/O 데이터는 안 접혀도 *호출 횟수*는 구조적 ⇒ EXACT ⌈S/CHUNK⌉(z3 LIA 귀납, requires fileSize=S); ★★S-5: upper-bound는 SPEED/KoAT 재탕(라벨), EXACT count만 신규(데이터의존 break는 bound); Axis B≈0(I/O 여전히 함)·Axis A 강양수(버퍼 사전할당·SLA·무한재시도 탐지). **§7**(저우선): Verhoeff=비가환 finite-monoid 행렬거듭(★스칼라합 주장 없음), Q12 semiring 렌즈(조직 프레임). 측정(`aq_report.py`): 8 배터리 green·AI 닫힌형 전부 z3 재증명+틀린 변형 반증·false-EXACT 0·이중지표 절대 분리·§AK 델타 ~0(정직: 숫자 코퍼스에 I/O/파싱 idiom 없음). `test_catalog 205/205`(+7 §AQ), test_build 273×3(extract.*/aq_report 미import, 순수 가산). 전부 기존 22개 환원·z3가 처분·이중지표 분리·precision 1.0·새 메커니즘/종류 0. ──────── (이전) |
| 4-교차검증 recall 6종: 변장 더 벗기기 (§AP) | **6개 recall 메커니즘 — 전부 기존 z3 게이트의 *정규화기*(S-1 새 fold 메커니즘 0·새 disposer 0·새 증명서 종류 0). 영혼(S-2): 관찰은 증명이 아니다 — z3 ∀-증명+다중스케일 held-out이 처분, AI 손유도 닫힌형은 *재증명*(절대 신뢰 안 함). **§1 `recall/compose/`**: 교차렌즈 합성 폴드(atomize·fold_each·recombine) — Fibonacci(C-finite, 지수 ⇒ k-regular 아님)+popcount(k-automatic ⇒ C-finite 아님)의 합은 *어느 단일 렌즈도* 못 보지만 각 원자는 제 렌즈에서 접히고 recombine 연산자는 carry-straddle에서 재검증; 임의 합 역산은 미결정(P-2)이라 코드가 노출한 분해만 사용. **§2 `recall/libsig/`**: scipy/numpy 신호 idiom 인식 = §AN R=44의 *일반형*(cumsum→선형·lfilter/IIR→ARMA·EMA→기하·moving-avg→window·**popcount→M22[R=44 정체]**·cumprod→holonomic); 초월 DFT/FFT는 정직한 DECLINE, popcount라 *이름붙은* 난수는 게이트가 DECLINE. **§3 `recall/stride/`**: 이종-렌즈 stride 부분스트림(짝=Fibonacci/홀=popcount, 둘 다 아닌 인터리브를 분리해야만 접힘) — §AN의 BM-only stride 위 추가; BM 1프로브+다중스케일, M22는 로그성장만(fail-fast). **§4 `recall/interproc/`**: summarize·unalias·gather(REUSE §AI §2) — 핵심 추가는 §4.2 unalias(지역 alias 복사전파로 `t=s; s=2t+1` 같은 *세탁된* affine을 접음; 없으면 false-DECLINE), 진짜 다중상태 결합은 정직 DECLINE. **§5 9·10번째 변장**: `defunctionalize`(고차 dispatch→1차 점화; 주기→control_flatten, 혼돈→DECLINE) + `bv_lia_lift`(비트→LIA 항등식 x<<k≡x·2ᵏ 등을 z3 BV로 ∀x 증명 *AND 틀린 변형 반증* ★★S-2; xorshift 비트믹싱은 DECLINE). **§6 `recall/chc_strip/`**: 배열의존 제거(invariant_find 스칼라화 가능성 + ★z3 CHC 귀납 불변식[삼각수 닫힌형이 a[i]=a[i-1]+i 만족 ∀i, 틀린 닫힌형 반증] · scalarize O(n)배열→O(1)/O(log n)); 외부 데이터/전역 오프셋 배열루프는 정직 DECLINE. **측정(`ap_report.py`, S-3)**: focused 라벨 코퍼스 recall **1.0**(9/9)·**false-EXACT 0**(7/7 적대 비폴드 DECLINE); 실제 **§AK 2000-코퍼스 재실행**(코퍼스-적용가능 변환기 chc_strip+stride) → **승격 0·false-EXACT 0** = 정직한 S-4 결과(§AK 비폴드는 진짜 안 접힘[데이터/초월/혼돈]이지 변장 아님; 나머지 4종은 구조 입력 필요→focused로 측정); ★★AI 닫힌형(비트→LIA 항등식+CHC 불변식) 전부 z3 재증명+틀린 변형 반증. `test_catalog 198/198`(+7 §AP), test_build 273×3(recall.* / ap_report 미import, 순수 가산). 합성·idiom·stride·alias·고차/비트·배열의존 — 변장을 더 벗기되 precision 1.0 불변. ──────── (이전) |
| 못 접는 다수를 *초가속*: 검증 가속 스택 (§AO) | **§AK가 측정한 비폴드 다수(realworld ≈93%·general backend ≈90%)는 *수학*이지 실패가 아니다 — §AO는 그 STRUCTURED-numeric 부분집합을 z3-등가검증 빠른 커널로 가속하되 fold율과 *엄격히 분리*. ★★A-1: 가속은 *분리된 지표* — §AK fold율 절대 안 바꿈(분자 합산 금지). ★★A-2(차별점): 모든 방출 커널은 z3 ∀-등가 증명 동반 — 검증 실패 커널은 *방출 안 됨*(buggy tiled GEMM 안 나감); 빠른 라이브러리가 못 주는 게 이 증명이다(모든 잘못된 변형 REJECT로 측정). 3 클래스 전부 게이트: **§1 물리/수치 *불변식***(`accel/invariant/`: 보존법칙 Σ(Mu)=Σu·확률공리 Σp=1·CFL 안정성 ∀s∈[0,1]|1−4c·s|≤1·혼합정밀 반복정련 ρ<1=APPROX_FOLD never-EXACT) = precision-1.0의 물리 버전 — 비보존/leak/CFL위반(c=0.6)/발산은 z3로 REJECT(false 'preserved' 0); **§2 검증 컴파일러 *변환***(`accel/xform/`: fusion·polyhedral interchange·Winograd over ℚ·5 scalar pass[SR/CSE/LICM/const-fold/DCE]·vectorize+aliasing 게이트, 각 z3-등가, 잘못된 변형 전부 REJECT); **§3 *백본* emit**(`accel/backend/verified_emit.py`: PTX REUSE `gpu/ptx_codegen`, 커널마다 등가+불변식 증명서 첨부 — MLIR/LLVM/Triton 재발명 안 함, 스택을 *탄다*). ★A-3 crypto/HW-RNG/MCMC 제외. ★A-4 정직: GPU 없으면 "PTX-verified-complete (throughput device-pending)" — 조작 숫자 0. 측정(`ao_report.py`): 전 배터리 green·invariant 위반 수락 0·새 메커니즘 0·새 증명서 종류 0(§AB APPROX-ε 재사용). 정직한 범위: general-backend 제어흐름 다수는 검증 커널로도 가속 불가(제어흐름은 제어흐름) — fold율처럼 정직. `test_catalog 191/191`(+4 §AO), test_build 273×3(accel.* 미import, 순수 가산). 가속≠fold·검증이 차별점·물리 불변식은 precision-1.0의 물리판·정직한 device 상태. ──────── (이전) |
| 측정된 k-regular 맹점 정조준: §AK R=44 닫기 (§AN) | **§AK 2000-측정이 *직접 찾아낸* 단 하나의 recall 갭(R=44, all k-regular k=2)을 닫는다 — 추측 아니라 측정 기반. ★정직 보정(M-1/S-4): 그 44개는 `bin(n).count('1')`=POPCOUNT, *base-2 AUTOMATIC 수열*(n의 2진 자릿수 함수, k-kernel 선형표현=기존 M22 mech_kregular로 복원) — 지시문의 '변장된 2차 선형점화(a[n]이 a[n-2] 의존)' 라벨은 부정확. 단 지시문 *핵심*은 정확: M22가 *이미* 접음 — §AK 블랙박스 recall 경로가 M22로 *라우팅 안 했을* 뿐(인식 갭이지 능력 갭 아님·새 메커니즘 0·S-1). **`recall/k_regular.py`**: `fold_k_automatic`는 base-k automatic을 기존 M22 k-kernel로 인식(k∈{2,3,4})·이중창 held-out(160 AND 280항 — 가짜 적합은 긴 창서 깨짐) ⇒ R=44 closer(REUSE mech_kregular·새 메커니즘 0); `fold_stride_interleave`는 지시문 해석(k개 독립점화 인터리브→stride-k 부분수열 분리·각 BM+다중스케일 held-out) — 진짜 인접패턴이나 인터리브는 그 자체로 C-finite라 단일스트림 BM이 대개 이미 잡음(정직). §2 quasi: `fold_k_periodic_coeff`(REUSE §AL control_flatten)+k-mutual(REUSE §AD companion) — 예방적·과적합 금지. **측정(`an_report.py`·게이트)**: §AK R=44 동일 재실행 — **44/44 popcount DECLINE→EXACT 승격**(기존 M22, before는 raw 엔진이 DECLINE했던 인식갭); **realworld 폴드율 6.84%→10.04%**(94→138 EXACT / 1374 realworld — synthetic은 이미 90% 천장이라 realworld가 유일한 의미있는 분모). ★★**false-EXACT 0**: 모든 승격을 M22 exact ℚ 재치환 400항(독립·적합 너머)+이중창 held-out 재검증; §AK 660 EXACT 불변(가산적 인식). ★정직 범위: base-10 digit-sum 여전히 DECLINE(M22 k=10 kernel 미폐쇄 — 더 깊은 갭, 위조 아님)·일반백엔드 무영향(갭은 realworld popcount였음). `test_catalog.py` **187/187**(+3 §AN incl. ★R=44 회귀 + ★다중스케일 held-out), test_build **273×3**(k_regular/an_report 미임포트 — 순수추가). 새 메커니즘 0·새 종류 0·LLM-free·zero-dep. 상세: `BUILD_LOG_catalog.md` §AN. ──────── (이전) |
| recall 물리한계: 변장 8차원 벗기기·깊이·다중스케일 held-out·spec-declared (§AL) | **§AK R클래스(접히는데 못 봄)를 *물리 한계까지* 짜낸다 — 모든 변장 차원에 대해 exhaustive. ★★S-2(영혼): 관찰은 증명이 아니다 — strip은 *정규화만*, 모든 후보는 §AI z3 ∀-증명 + held-out=200 게이트(`recall/core.fold_via_ai`)가 ONE 지점에서 처분; 잘못 벗기면 게이트가 거부 ⇒ strip은 거짓 EXACT를 *절대* 못 만듦. recall을 끝까지 밀어도 precision 1.0 불변. S-1 새 메커니즘 0·S-3 모든 DECLINE→ACCEPT는 z3 처분·S-4 일반백엔드 여전히 낮음(구조부재는 변장 아님). **§1 변장벗기기**(`recall/strip/`, 8차원): ①`recursion_to_loop`(naive O(2ⁿ) 재귀→MEMO 가능오라클 — 없으면 블랙박스가 probe조차 못함) ②`multivar_collapse`(f→튜플 비수치→foldable 성분 투영 — 숨은단일변수) ③`interproc_gather`(함수횡단 누산기→단일 점화, REUSE §AI §2) ④`closure_unwrap`(클로저 호출열→단항오라클) ⑤`object_state_extract`(객체 상태기계→단항오라클) ⑥`control_flatten`(분기별 점화 residue-class 분리·각 z3) ⑦`strength_reduction_inverse`(덧셈누적→선형·곱누적→기하; lifter와 중복정직) ⑧`alg_window_relation`(구조적스트림 윈도→닫힌형; §Z중복). ★①–⑤ 진짜 신규 recall(raw 블랙박스 못 봄)·⑥–⑧ 기존중복이나 z3게이트 유지·각 모듈은 chaos/random/data-dependent 적대 거부(거짓 EXACT 0). **§2 깊이+★★다중스케일 held-out**(`recall/depth.py`): probe 24→48→96→192 상승(얕은 probe서 under-determined인 고차 점화 포착·관찰부족시 ABANDON). ★★§AK가 잡은 digit-function 함정(연속창 일치하나 자릿수 carry n=100서 깨짐) 영구차단 — held-out을 n≈100/1000/10000 carry경계 횡단으로 검증 ⇒ base-10 digit-sum은 연속 BM 점화에 *일치하지만* carry스케일서 반증 ⇒ 영구 DECLINE; 이 강화는 EXACT→DECLINE만 가능(precision은 오를 뿐). 정직: 깊이 수확체감(yield 곡선 평탄화). **§3 spec-declared 최대**(`recall/declared_max.py`): §AI 구조는 specfold로 라우팅(REUSE·bounded_state z3-discharge)·monotone/periodic/prime 확장 — 조건부 정리 'R⟹folded≡original'·R 항상 cert 명시·미선언 DECLINE. **측정**(`al_report.py`): §AK R before/after — **8/8 변장차원 회복**; ★S-3 precision: 모든 회복 fold이 §AI z3+held-out 게이트 통과 ⇒ **false-EXACT 0**; ★★digit P-2 함정 영구차단·chaos/random/구조부재 DECLINE·S-4 일반백엔드 여전히 낮음·깊이 수확체감곡선. `test_catalog.py` **184/184**(+5 §AL incl. ★S-2 다중스케일 적대), test_build **273×3**(recall/al_report 미임포트 — 순수추가). 새 메커니즘 0·새 종류 0·LLM-free·zero-dep. 상세: `BUILD_LOG_catalog.md` §AL. ──────── (이전) |
| 2000개 무작위 코드 폴드율 정직 측정 + DECLINE 사유 지도 (§AK) | **측정 하네스(엔진 코드 0 추가) — 기존 fold 엔진을 2000개 코드에 *그대로* 돌려 숫자가 거짓말 못 하게. **M-1** 폴드율은 *도메인별×출처별*만 보고(신호코드로 채우면 90% 나옴 — 단일 숫자 금지). **M-2** 진짜 산출물은 *못 접는 것의 분포*. **M-3** EXACT 전부 독립 z3 재검증 — false-EXACT 0. **M-4** 코퍼스는 general_backend 다수(실세계는 대부분 구조 없음)·`synthetic`(recall 상한)/`realworld_style`(진짜 숫자) 분리. **§1 코퍼스**(`corpus/build_corpus.py`): 2000 결정적(시드고정·LLM-free·재현)·general 600/numeric 400/signal 350/stats 350/crypto 300·출처 태깅·각 버킷에 일부러 비폴드(반-조작). **§2 측정**(`measure/engine_adapter.py`+`run_corpus.py`): 엔진 불변 — 정적(`catalog.lift`+`structure_recognizer`)+§AI/§AJ 블랙박스(precheck→router→5추측기) → EXACT/PROB/DECLINE/ERROR 4분류·폴드율=EXACT/(EXACT+PROB+DECLINE)(PROB 분자 제외·ERROR 제외)·고립실행·z3 타임아웃·시드고정. **§3 분류**(`measure/decline_taxonomy.py`): 각 DECLINE→PROVEN_BOUNDARIES A~I(REUSE decline_boundary)·모호하면 UNCLASSIFIED(억지분류 금지 — recall 여지 은폐 방지)·R은 §4만 할당. **§4 near-miss**(`measure/near_miss.py`): recall 사냥 — DECLINE된 단항 oracle을 공격적 재시도(§AI probe=64 + k-regular M22 REUSE)·이중창+far held-out 가드·접히면 **R**(recall 갭)+변장유형(=recall 우선순위). M-3 유지(z3 게이트 통과만, 관찰 아님). **측정값(n=2000·시드 20260628·재현)** `ak_report.py`: 폴드율 — crypto **0%**(해시/CSPRNG 절대 안 접힘 정답)·general_backend **10%**(정직한 바닥 — 구조부재는 수학이지 실패 아님)·numeric **56%**·signal **50%**·stats **57%**; 출처별 — **synthetic 90.4%**(recall 상한) vs **realworld 6.8%**(진짜 숫자)·전체 33%는 단독 보고 안 함(M-1). DECLINE 지도(1340): UNCLASSIFIED 46.6%·C 17.9%(정보바닥-crypto)·I 17.9%(데이터의존 제어흐름)·F 8.8%(z3벽-초월)·H 4.5%(I/O)·E 4.3%(카오스); near-miss R=**44** 전부 k-regular(k=2) ⇒ #1 recall 우선순위는 k-regular류(popcount). ★★**M-3 게이트: 660 EXACT, false-EXACT 0, precision 1.0** — 전부 독립 재검증(복원 점화 vs 참 oracle, far n≈400–420). ERROR 0. `test_catalog.py` **179/179**(+5 §AK), test_build **273×3**(corpus/measure/ak_report 미임포트 — 순수 추가). 상세: `BUILD_LOG_catalog.md` §AK. ──────── (이전) |
| §AI 보조 4레이어: 추측기 라우팅·잔차 게이트·건전성 보조·Viterbi (§AJ) | **4개 외부 평가 라운드에서 *z3+precision-1.0+repo를 통과하는* 항목만 골라 §AI 추측-검증의 *보조 레이어*로 박는다 — 보조는 게이트를 절대 약화 못 함(속도나 추가 exact 증명서만 더할 뿐, 거짓 EXACT는 불가). **§1 잔차 컷오프**(`conjecture/precheck.py`): random-oracle 시그니처면 추측 경로를 빠르게 건너뜀. ★★불변식 **false-skip 0**: foldable은 절대 안 건너뜀 — skip 규칙은 모든 구조적 tell의 동시 부재를 요구하고, 구조 탐지기(싸구려 Berlekamp-Massey order via §AI under-determination 경계 REUSE native_sequence·다항식 비율 REUSE holonomic_guess·주기 REUSE period_guess)는 추측기들의 첫 단계의 *상위집합*이므로 foldable은 항상 하나를 trip ⇒ 건너뛸 수 없음(운이 아니라 구조). 지시문이 명시한 통계 신호(Shannon 엔트로피·R/S Hurst·MDL 비압축성 REUSE decline_boundary.mdl_two_part)가 보강. ★★정직: skip은 RECALL만 비용(잘못 건너뛴 foldable은 DECLINE이 됨)·PRECISION은 절대 불가(PROCEED한 건 z3가 처분) — precision 1.0은 이 게이트에 의존 안 함; Clock-C 속도 필터, false-skip 측정=0. skip은 DECLINE이지 빠른 EXACT 아님(P-2). **§2 추측기 라우터**(`conjecture/router.py`): 싸구려 신호(autocorrelation⇒주기·유한차분 붕괴⇒다항식·다항식 비율⇒holonomic·작은 BM order⇒C-finite/matpow·NCD/KS/상호정보 tie-break)로 어느 추측기가 fold할지 예측해 먼저 시도. ★★순서만 — 5개 추측기 포트폴리오 전체가 fallback이라 fold되는 *집합*은 라우팅 유무와 동일(routed recall == unrouted recall 측정)·z3가 순서 무관하게 처분. 라우팅은 fold도 거짓 EXACT도 못 만듦; 평균 작업만 절약(first-try 적중률이 측정된 이득). 라우터가 틀려도(factorial을 non-holonomic 먼저) fallback이 fold — recall 보존. **§3 건전성 보조**(`conjecture/soundness_aux.py`): (a)Kraft-McMillan — 길이 {lᵢ}의 prefix/uniquely-decodable 이진 코드 존재 ⟺ Σ2^(-lᵢ)≤1, EXACT 유리수 실현가능성 증명서(Fraction, float 절대 아님)·>1⇒정확한 초과분과 DECLINE. (b)0-1 법칙 승격 — ★★P-2 선: 관찰상-항상 성질 P(n)을 'z3가 이분법 (∀n.P)∨(∀n.¬P)을 증명'할 때만 ∀n EXACT로 승격, 관찰 한 점이 분기 선택; n-의존(예 'n<100', probe엔 참·이후 거짓)이면 z3가 이분법 없음 ⇒ 승격 없음 — 관찰만으로는 절대 승격 안 함. 둘 다 기존 'invariant' 종류(새 종류 0). **§4 Viterbi 반환**(`gapfold/semiring_dp.py`): Viterbi(max-product) DP는 로그 영역에서 V[t][j]=maxᵢ(V[t-1][i]+logT[i][j]) — 정확히 기존 taxonomy의 max-plus tropical 반환. 시간-동질 전이는 T스텝을 tropical 행렬거듭제곱 logT^⊗T로 O(T·m²)→O(m³ log T) fold, 반환 결합법칙으로 sound(REUSE altlens.tropical_fold: tropical_matpow + verify_matrix_extraction 차분 검증). ★★새 메커니즘 0 — Viterbi는 tropical face; cert는 matrix-power/linear-recurrence로 환원(kind closed_form). 정직: max/argmax는 정확 비교(경로는 float에서도 정확)·누적 로그-점수는 ℤ/ℚ에서 정확; 스텝별 방출은 이미 O(T·m²)-최적 ⇒ 점근 fold DECLINE(거짓 속도주장 없음). **합성**(`aj_report.py`): precision **1.0**·P-2 강제(skip⇒DECLINE·승격은 z3 이분법만)·false-skip **0**(측정)·라우팅 recall **불변**·새 메커니즘 0(22/14)·LLM-free 코어(AST)·zero-dep. `test_catalog.py` **174/174**(+5 §AJ), test_build **273×3**(precheck/router/soundness_aux/semiring_dp/aj_report 미임포트 — 순수 추가; gapfold는 test_build가 임포트 안 함). 상세: `BUILD_LOG_catalog.md` §AJ. ──────── (이전) |
| 분자 키우기: conjecture-then-verify·인터프로시저럴·spec-declared·canon (§AI) | **분자(fold된 EXACT 수)를 recall로만 키운다 — 분모·22/14 메커니즘/증명서 taxonomy 불변. 4 레버, 각 PROPOSE→z3 DISPOSE. ★★P-2(5개 AI가 넘어진 선): 관찰은 증명이 아니다 — 만 개가 맞아도 z3 ∀-증명 + held-out 발산 가드를 통과 못하면 DECLINE(거짓 EXACT 0). 모든 레버는 기존 증명서 종류로 라우팅 — 새 메커니즘/처분기 0. **§1 conjecture-then-verify**(`conjecture/`, 가장 강한 레버): 화이트박스 매처가 못 읽는 변장(재귀·클로저·CPS·객체상태·동적디스패치)을 블랙박스로 관찰→추측→z3가 ∀n 증명(추측은 공짜 — 틀리면 z3가 기각하므로 분자만 늘고 변장 차원은 붕괴: 변장 무한, 행동 하나). 5 추측기 전부 REUSE — `bm_linrec`(Berlekamp-Massey C-finite→native_sequence)·`closedform_guess`(유한차분 다항식 차수+특성근 (x−1)^{d+1})·`period_guess`(최소주기 표 항등식)·`matpow_guess`(동반행렬 거듭제곱 O(N)→O(log N)→§AD mat_pow)·`holonomic_guess`(1차 P-recursive 비율 — 변장 factorial/binomial 무력화). 처분은 `harness.conjecture_verify`(REUSE §P P1 blackbox_recover)=held-out 발산 가드(probe 너머 **200**항 정확 예측) **+** z3 동반행렬 consecution 증명(`prove_companion_consecution`, QF_LRA가 companion이 ∀-window에서 재귀 상태를 정확히 전진시킴을 증명 — P-2 게이트의 ∀n 절반). ★under-determination 가드: order-d는 ≥2d+2 관찰 필요(차수 k 다항식은 임의의 k+1 점 통과 — 적합은 증명 아님). ★digit-sum/popcount 함정 정직 처리: 짧은 창에서 가짜 order-11 적합이 되지만(구조적 단절은 n=100 자릿수 carry) held-out을 24→**200**으로 올려 다중 carry 스케일을 건너 반증⇒DECLINE(딱 P-2 위험 차단). 정직한 한계: 유한 held-out은 모든 스케일 너머 ∀n을 증명 못함 — 최강 보장은 구조적 z3 증명에 유보, held-out은 발산 *스크린*, z3 consecution이 *정리*. **§2 인터프로시저럴**(`interproc/stitch.py`): 함수들에 흩어진 affine 누산을 ONE 합성 재귀로 재구성, z3가 순차적용과 ≡ 증명(REUSE §P P6 distributed_state, 기존 matrix_recurrence 종류); 비affine/aliased/무결정 핸들러 ⇒ DECLINE(오염 가드). ★정직 경계: 분석 REACH를 넓힘(함수횡단 누산 가시화)이나 대부분 함수횡단 코드를 foldable로 만들지 않음(제어흐름은 제어흐름) — fold-rate 리프트 MODEST. **§3 spec-declared**(`specfold/declared.py`, 가장 깨끗 — 추측이 아니라 정보 추가): HARAN `requires sorted(a)`(REUSE haran_parser)를 fold 전제로 소비 — 조건부 정리 'R ⟹ folded≡original', R은 ALWAYS 증명서에 기록(숨기면 거짓 EXACT — 투명). z3 처분 가능 시 discharge(`0≤s<2^16` ⇒ 유계⇒wrap-free 정수 fold, z3 BV 증명); 선언 없으면 DECLINE. **§4 canon+합성**(REUSE §AA foldrate, 측정-우선·재구현 0): 표면변형→1정규형(multiplier 8.0×, 분포의존)·lens 합성(lift 4). **측정**(`molecule_report.py`): ★정직 per-domain delta — signal/numeric/stats/crypto는 변장구조 fold(실 recall), general backend **0/2**(digit-sum/popcount는 recall할 재귀 없음 + held-out이 가짜 order-11 적합 거부 — 숫자는 거짓말 안 한다). precision **1.0**·P-2 강제(거짓 EXACT 0)·under-determination 가드·새 종류 0(22/14)·LLM-free 코어(AST)·zero-dep. `test_catalog.py` **169/169**(+5 §AI), test_build **273×3**(conjecture/interproc/specfold/molecule_report 미임포트 — 순수 추가). 상세: `BUILD_LOG_catalog.md` §AI. ──────── (이전) |
| 다언어·codegen·recall·self-fold·super-scaling·보안 검증기 (§AH) | **6축, 3개 구속 정직-리프레이밍(위반 시 빌드 실패): RF-1 언어=intake(coverage 아님)·RF-2 22/14 포화(새 메커니즘 0)·RF-3 "완벽한 보안" 없음.** precision 1.0(거짓 fold/거짓 "안전" 0)·새 종류 0·LLM-free 코어·zero-dep 코어(tree-sitter 선택, fallback 유지). **§1 다언어 intake**(`frontend/semantics.py`+`lang_intake.py`, ★precision 방어선): 같은 `Σi→n(n+1)/2` fold을 *언어 정수의미 하에서* 판정 — Python(임의정밀) EXACT; Java/C# int32는 naive가 식중간 overflow ⇒ z3 QF_BV가 naive==wrap-sum 반증 ⇒ wrap-aware형만 ACCEPT; C/C++ signed overflow=UB ⇒ 범위 내 **DECLINE**(UB에 닫힌형 금지), no-overflow 증명 시만 EXACT; Go/Rust-wrapping wrap-aware·Rust-checked 초과 DECLINE; float 재결합 거부·평가순서 보존. intake는 7개 언어 인식(언어무관) — fold 부분집합 언어무관(같은 도메인-조건부 천장), *건전성 disposition*만 다름(2개 언어가 같은 fold DECLINE). **§2 codegen**(`codegen/idiom.py`): 값범위→타입승격(JS number→BigInt·C int64/__int128+guard·Java int→long·Rust checked_*) 결정적 선택 후 z3 **번역검증**(codegen 제안·z3 처분; 틀린 naive-int32 방출은 *거부*·fallback); 게인은 *상수배*(점근 아님, §1과 합산 금지). **§3 recall 통합**(`recall_integrate.py`, RF-2 새 메커니즘 0): canonicalization 3변형→1형(recall ×3, EXACT 천장 불변)·lens 합성 additive-with-overlap·변장 C-finite는 REUSE Berlekamp-Massey로 recall·확률 프론티어는 임계상 PROBABILISTIC/임계하 DECLINE(절대 EXACT 아님); §Y~§AE·§M 재사용(§AG 감사가 중복 게이트). **§4/5 self-fold + super-scaling**(`self_fold.py`): self-fold는 Clock C만 건드림(A=LLM·B=z3·C=fold·I/O 중) ⇒ end-to-end는 Amdahl-제한(모델예산 1.11× — A/B/I-O는 비폴드 바닥; 정확성은 profile 비의존); super-scaling은 foldable 커널 비율 O(N)→O(1)·메모리 O(N)→O(1)(OOM 회피)이나 전체작업은 *측정된* p에 Amdahl-cap — 저-p는 정직 "amdahl-capped", 고-p는 "super-scale"; "클수록 절대 빠름" 시스템 주장 안 함. **§6 보안 검증기**(`security/route.py`+`consttime.py`+`taint.py`+`entropy.py`+`reentrancy.py`, RF-3): 결정적-우선 라우터(보장은 라우터/LLM 비의존 — 약한-LLM 핵심); consttime(reuse sidechannel) 비밀-의존 분기/메모리/나눗셈 부재 증명 or FLAG/DECLINE; taint(reuse taint_ifds) source→sink 비도달 증명 or FLAG; ★entropy는 *저엔트로피 INSECURITY만* 증명(절대 "안전" 아님 — NIST PART1.C 필요-불충분); reentrancy(CFG checks-effects-interactions) external-call-before-write FLAG(DeFi 감사). ★위협모델 명시(증명: 모델된 타이밍/taint/재진입/저엔트로피; 미증명: 미모델 side-channel·하드웨어·프로토콜·암호프리미티브). 보안판 precision 1.0=거짓 "안전" 0; "완벽한 보안" 절대 금지. **합성+측정**(`upgrade_ah_report.py`): 6축 — precision **1.0**·새 종류 0(22/14)·LLM-free 코어(AST)·zero-dep 코어; 두 정직 qualifier 유지·세 금지 카피 회피. `test_catalog.py` **164/164**(+6 §AH), test_build **273×3**(§AH 모듈 미임포트 — 순수 추가). 상세: `BUILD_LOG_catalog.md` §AH. ──────── (이전) |
| 30-이론 repo-first 감사 + SyGuS + 건전 피드백 (§AG) | **외부 평가가 "마스터하라"고 준 30개 이론 — ★측정(grep+매 빌드 import): 거의 다 *이미 빌드됨*. 따라서 답은 *재구현*이 아니라 *감사*(29개 재구현 = ~97% 중복·repo-first 위반).** 새 모듈 `theory_audit.py`(레지스트리)·`sygus_propose.py`·`sep_alias.py`·`theory_audit_report.py` + `catalog/compose.py` 1개 하위호환 수정. 새 인증서 종류 0(22/14), LLM-free(AST), 무의존. **§1 감사 레지스트리**(algo50 매핑 패턴): 30개 이론 → 실제 모듈 entry point, `test_ag_theory_audit_registry`가 매 빌드 전부 IMPORT("이론 N 보유" 증명). ★측정 disposition: **26 CONFIRMED / 0 GAP / 1 NOT-A-FOLD / 3 DECLINED-BY-IDENTITY**. CONFIRMED 25 기존(IC3/PDR·CHC/Spacer·Presburger/QE/CAD·L*·SFA·Knuth-Bendix·Gröbner·Sturm·Gosper/Zeilberger·Berlekamp-Massey·LLL·Sylvester inertia·Prony·Petrov·Koopman·E-graph·AARA·partial-eval/Futamura·번역검증·companion-matrix·sparse-FFT·압축센싱·MDL·Kolmogorov·widening) + SyGuS(여기 빌드). NOT-A-FOLD: polyhedral(region-3 상수배, `excluded_candidates`에 이미 제외). DECLINED-BY-IDENTITY: HoTT(z3-종결 위반)·GCT(P-vs-NP 패러다임)·NIA-일반(Hilbert-10 결정불가 — 결정가능 섬은 barrierfold ISLAND 2/3에 이미). ★이중계산 게이트: 어떤 이론도 두 모듈에 등록 안 함. **§2a SyGuS**(유일 net-new): CFG 후보공간+SMT 명세 → *결정적* enumerative/CEGIS 합성, 기존 `equiv_check.prove_equiv_z3`/`equiv_grade`로 게이트(새 처분자/종류 0). max2→`ite(x≥y,x,y)` z3-증명; 약한 문법(곱 없음)은 x·y 표현 불가 ⇒ 정직 DECLINE. ★★*정직 측정*: SyGuS는 PROPOSER지 coverage 확장 아님 — z3-foldable 집합 불변(§P P1/§AE ISLAND5와 같은 게이트) ⇒ **fold-coverage Δ=0(측정)**; proposer 지표는 별도 보고, 절대 혼동 안 함. **§2b separation-logic**(선택): aliasing DECLINE을 *증명으로* ACCEPT 승격 — affine 단사성/구간 분리를 z3 QF_LIA로 환원; 충돌/겹침 witness면 DECLINE 유지(precision 1.0). 측정: 마이크로코퍼스 **4/7 승격**; cert는 기존 `invariant` 종류 재사용. **§3 피드백, 건전형만:** ①오차폭발: ★마틴게일/Chernoff **거부**(증명 안 된 독립성 가정 = LLM 근사 = 금지선); 건전 수정 = `combine_grade`에 하위호환 `prob_cap`(+`compose_chain`) — PROBABILISTIC 체인이 cap 초과면 정직 DECLINE(오차폭발 *노출*, 은폐 아님); δ_total≤Σδ 유지; `prob_cap=None` 기본 ⇒ 273 바이트동일; 적대 테스트: 긴 체인→해당 단계 DECLINE, false-EXACT 0. ②NIA-다리: 중복·결정불가로 거부(DECLINED-BY-IDENTITY 표기). ③자료구조 리프팅: 명명 예시 *이미 빌드*(이진카운터→amortized = AARA `catalog.mech_aara`; 배열→대수 = §P `array_fold`); ~5.7% 천장은 *측정된 정직 천장*, 인플레 금지 — 새 패턴 미발견 ⇒ §AD 추가 없음(천장 유효). **합성+측정**(`theory_audit_report.py`): 30-이론 표·SyGuS Δ=0·sep 4승격·① depth-cap 적대(false-EXACT 0·마틴게일 거부). precision **1.0**(거짓 fold/거짓 "해결" 0); 새 종류 0(22/14); LLM-free(AST); 무의존. `test_catalog.py` **158/158**(+4 §AG), test_build **273×3**(새 모듈 미임포트; `combine_grade` 기본-off ⇒ 273 불변). 상세: `BUILD_LOG_catalog.md` §AG. ──────── (이전) |
| 일곱 난벽의 결정가능-섬 (§AE, float-ε·비선형정수·exp-poly등식·홀로노믹합·불변식합성·정지·Kolmogorov) | **증명된 7개 *난벽*(z3 IEEE-754 비트블래스트 폭발·Hilbert-10·닫힌형등식 일반-미해결·Risch/Zeilberger 비종료·Rice·Turing 정지문제·Kolmogorov K(x) 비계산) 안으로 들어가, 일반해는 *절대 주장 않고* 각 벽 안의 *결정가능 섬*만 접는다.** ★중심 통찰(제안자–검증자): **합성은 제안자의 일**(FPTaylor/Faulhaber/Gosper-Zeilberger-Karr/Karr-Farkas-Gröbner/Podelski-Rybalchenko-SCT/Berlekamp-Massey — 어려운 탐색), **검증은 z3의 일, 종료하는 이론서 쉬움**(QF_LRA simplex/QF_NRA nlsat-CAD/QF_BV — IEEE-754 비트블래스트 절대 안 함). 새 패키지 `barrierfold/`, test_build 미임포트, 무의존(sympy ISLAND4만 grandfathered), 새 인증서 종류 0(22/14 불변), LLM-free(AST). **ISLAND1 float-ε**(`float_eps.py`): 실수의미가 기하/선형 점화인 float 루프 → 닫힌형 + *보편* ε(affine/interval를 **QF_NRA**서 증명, `A:=aⁿ` 실수추상, 비트블래스트 없음); `foldaxes.ErrorInterval`+기존 APPROX_FOLD 등급 재사용(새 등급 0); ★|a|≥1 DECLINE(오차 ~aᴺ); ★ε는 전역-도메인 보편, 표본 아님(표본 max는 과소추정). **ISLAND2 비선형정수**(`nonlinear_int.py`): Hilbert-10의 5 결정가능 조각 — 가산(Faulhaber, new)·모듈러(§Y Galois 재사용, 0-new)·거듭제곱(modular orbit/Floyd, new)·치환(§Z·§P-P5 Möbius 재사용, 0-new)·유한상태(cycle, 0-new); 새 조각=결정가능-경계 분류기; ★일반 비선형(x²+c·Collatz) DECLINE. **ISLAND3 exp-poly 등식**(`exppoly_eq.py`): 서로 다른 대수적 λ의 지수다항 Σ Pᵢ(n)λᵢⁿ 등식은 **기저 선형독립**으로 *항상* 결정가능(계수비교+유계 정확유리수 확증); ★더 어려운 Skolem 존재-영점은 차수≤4 결정가능(Vereshchagin), 차수≥5 DECLINE(미해결). **ISLAND4 홀로노믹 합**(`holonomic_sum.py`, 최대 섬): 종료보장 합 부류 — 다항(Faulhaber)·기하·다항기하·Gosper 초기하·Zeilberger 창의적 텔레스코핑·Karr ΠΣ·C-finite; `catalog/holonomic_sum.py`+grandfathered sympy 재사용, ⑬ 확장; ★텔레스코핑 항등식 C(n)−C(n−1)==summand(n) 검증(종료); ★비-홀로노믹(조화 H_n·digamma·zeta) DECLINE. **ISLAND5 불변식 합성**(`invariant_synth.py`): *완전* 합성 도메인 — Karr(아핀)·Farkas/LP(선형부등식)·Gröbner(고정차수 다항) 각각 불변식 합성 후 z3가 3 VC(초기화/귀납/충분성)를 QF_LRA/QF_NRA서 검증; ★§X `synthesize_guard` 인터페이스 재사용하되 CEGAR 추측→완전합성 *승격*; 틀린 불변식(기울기 불일치)은 귀납 실패(검증기 진짜); 일반 불변식 합성은 미결정(Rice). **ISLAND6 정지**(`termination.py`): 결정가능 정지 부류 — 유계루프·선형 랭킹함수(Podelski-Rybalchenko, Farkas 완전)·Size-Change Termination(Lee-Jones-Ben-Amram)·HARAN `decreases` 계약(합성 아닌 검증). ★★**정지 맹세**(구속): 일반 정지문제는 *증명된* 미결정(Turing 1936); 발급된 모든 증명은 "랭킹함수/검증된 decreases *때문에* 종료", 절대 맨 "종료" 아님; 일반 `while`/Collatz는 DECLINE(긍정도 부정도 안 함). **ISLAND7 Kolmogorov 열거**(`kolmogorov_enum.py`, 가장 깊은 벽): "임의의 숨은 구조가 있나"는 K(x)를 묻고 그건 *비계산*; 섬 = *유한 열거* 결정가능 구조 부류 레지스트리(상수·주기·LFSR via 재사용 `native_sequence.berlekamp_massey_Q` + 22 메커니즘 + 8 gaps) 위 계산가능 상한, 최소기술길이(MDL) 선택; |x| 아래로 압축 못하면 DECLINE. ★★**Kolmogorov 맹세**(구속): K(x)는 *증명된* 비계산(Kolmogorov/Chaitin); 이건 "유한 열거 목록 중 최선 일치"지 절대 "임의의 구조"·무작위 압축 아님; ★대각화로 어떤 유한 레지스트리든 놓치는 구조적 입력 존재(Thue-Morse, 2-automatic 비-LFSR) — 정직하게 DECLINE, 거짓 주장 안 함. **합성+측정**(`barrierfold_report.py`): 7 섬 배터리 전부 통과 — 정밀도 **1.0**; LLM-free(AST: 어떤 모듈도 LLM 미임포트); 두 맹세 존재+`confirmed_not_solved`("정지문제와 K(x)는 미해결 — 결정가능 섬만 접음"); ISLAND1 ε 보편-비표본 감사. ★**수렴 천장**, 측정: DECLINE 잔여 = {일반 비선형정수(x²+c/Collatz)—**Hilbert-10**; Skolem 차수≥5—**미해결**; 비-홀로노믹 H_n/n—**Risch**; 일반 정지—**Turing**; K(x) 정확—**Kolmogorov**}; 세 독립 연구모델이 그은 *같은* 경계를 측정 — 잔여는 *증명된 불가능*(Turing·Hilbert·Kolmogorov)이지 우리 기계의 구멍이 아님. 새 종류 0(22/14). `test_catalog.py` **154/154**(+7 §AE), test_build **273×3**(barrierfold/ 미임포트). 무의존. 상세: `BUILD_LOG_catalog.md` §AE. ──────── (이전) |
| 여덟 구조-구멍 (§AD, 상호재귀·분할정복·중첩합·구조데이터·소거·float정확·큰상태·루프융합) | **기계를 완성한다 — 새 이론 아님: 늘 있던 *기성수학* 구조를 접고, 잔여가 영원-불가능임을 증명.** 구조는 진짜 있는데 탐지기/닫힌형이 안 만들어진 8개 EXACT 구멍 — *현재*-불가능(탐지기 미비)이지 *원리적*-불가능(진짜 I/O/무작위/데이터의존, 영원-불가능)이 아님. 새 패키지 `gapfold/`, test_build 미임포트, 무의존(sympy GAP5만 grandfathered), 새 인증서 종류 0(22/14 불변), LLM-free(AST). **GAP1 다방향 상호재귀**(`mutual_recursion.py`): k≥3 얽힌 선형점화 → k×k 컴패니언 행렬거듭제곱 O(N)→O(log N)(2-way는 이미·k≥3 탐지격차); 컴패니언 준동형(결합법칙)+차분 추출검증, 비선형 거부. **GAP2 분할정복**(`divide_conquer.py`): T(n)=a·T(n/b)+f(n) → Master/Akra-Bazzi(병합 Θ(n log n)·Karatsuba Θ(n^1.585)·이분 Θ(log n)); 점근-차수(§AC-F4), 차수≠값 정직, 비-Master 거부. **GAP3 중첩합**(`nested_sums.py`): ΣᵢΣⱼ i·j→(Σi)(Σj), 삼중→(Σi)³ 다변수 Faulhaber(1변수 멱합 z3 증명·분리곱), EXACT O(Nᵏ)→O(1); 비다항 거부. **GAP4 구조-데이터 조건**(`structured_data.py`, 그레이존): 순수-데이터의존(DECLINE) vs 구조적(i%k==0 주기·데이터무관; arr[i]>arr[i-1] 선언된 정렬 하)分류; ★보수적 — 진짜 데이터의존 DECLINE, 구조 강제 안 함. **GAP5 깊은 소거**(`simplify_fold.py`): fold 전 단순화((x+1)²−x²−2x−1→0, depth 7) z3 등가증명(§AA-W1 재사용)→fold; 비등가 거부, float DECLINE. **GAP6 float-정확 부분집합**(`float_exact.py`): x·2.0/2의거듭제곱 스케일 → EXACT(z3 IEEE-754 비트정확, 반올림모드 독립); ★증명될 때만 EXACT — x·3.0은 미승격(APPROX-ε/DECLINE), 묵시승격 없음. **GAP7 큰-유계 상태**(`large_state.py`): 32비트 아핀 LCG → QF_BV/행렬거듭제곱 *구조*로 fold, 2^32 열거 안 함; ★비선형 큰상태 DECLINE(구조 가정 안 함). **GAP8 연속루프 융합**(`loop_fusion.py`): 생산자-소비자 루프(a[i]=f(i);s+=a[i])→s=Σf(i) 닫힌형(Faulhaber, z3); ★앨리어싱/중간쓰기 거부. **합성+측정**(`gapfold_report.py`): gap-shaped 코퍼스 BEFORE §AD **0** → AFTER **8/8**(기성수학 구조 fold, EXACT; G2 점근차수·G6 비-정확float은 APPROX-ε/DECLINE); ★무강제 감사(GAP4/6/7 비구조 거부); ★더-작아진 실천장 측정(잔여=원리적 불가능). 빅3(분할정복·중첩합·융합) 최광. 정밀도 **1.0** 8개 배터리·새 종류 0. `test_catalog.py` **147/147**(+8 §AD), test_build **273×3**(gapfold/ 미임포트). 무의존. 상세: `BUILD_LOG_catalog.md` §AD. ──────── (이전) |
| 입력-인지·깊이-변주 fold (§AC, 프로파일·spec·부분·점근·재귀) | **입력이 미지라는 가정과 fold가 전부-아니면-전무라는 가정을 깬다 — 입력을 *측정*(프로파일)하거나 *선언*(HARAN requires)받고, fold 깊이를 부분·차수·고정점으로 변주.** 새 패키지 `inputfold/`, test_build 미임포트, 무의존, 새 인증서 종류 0, 전부 LLM-free. **F1 프로파일-유도**(`profile_fold.py`): 측정된 프로파일이 *실제로 성립하는* 가드를 선택(합성→데이터선택); §AA-W3/§X-P1 재사용(증명 Φ⟹folded==original 불변, 프로파일은 Φ만 선택). ★fallback 불변식(검증): 정확성은 프로파일과 무관 — 미스면 원본(정확, 느림), 100% 틀린 프로파일도 정답 유지·속도만 하락(매칭 워크로드서 90 folded/10 fallback, 적중 0.9, 전부 정확). ★범위 "측정된 워크로드 W 하," 보편 아님. **F2 spec-선언**(`spec_fold.py`): 사용자 선언 HARAN `requires` P 하에서 fold, `P⟹folded==original` z3 증명(합성비용 0, P 성립 시 적중 100%; abs(x)→x UNDER `requires x≥0`, P 없으면 항등식 아님). ★선언의 진실성은 런타임 체크(P 거짓⇒런타임-DECLINE, 원본 실행) 또는 선언자 책임(계약), 모드 명시·묵시가정 거부. HARAN 완벽 적합(requires=가속 계약). **F3 부분**(`partial_fold.py`): 전체-루프 DECLINE의 접을 수 있는 *슬라이스*만 fold, 잔여 유지(`s+=c; io_write`→누산 fold, I/O 유지); slice==원본-slice ∧ 슬라이싱-의미보존 증명(슬라이스가 잔여와 독립 — 잔여가 누산기 중간값 읽으면 REJECT). ★분모 정직: 문장단위/분율(1/2=0.5), 전체-루프와 구별·병합 안 함. **F4 점근-only**(`asymptotic_fold.py`): 상수 아닌 *차수* 감소 — prefix-sum O(N²)→O(N) z3-EXACT, 합성곱 O(N²)→O(N log N)(정수/NTT EXACT, float APPROX-ε per §AB·never EXACT), 선형스캔 O(N)→O(log N) under sorted(F2 합성). ★차수-감소율, 닫힌형(O(N)→O(1))과 구별, before/after 차수 명시. **F5 재귀**(`recursive_fold.py`): fold→단순화→재-fold를 고정점까지([5,-5,7,-7]→[5,-5] 소거가 [7,-7] 노출→[] 2회). ★종료: 정합 진행척도(항 수) 매회 엄격감소 + cap; 각 링크 증명·최종 원본 대비 z3 증명(소거는 값보존 ∀x.x+(-x)==0). ★가산-비곱셈(per §AA-W2): 재귀 lift=반복으로만 잡는 fold(고정점 2 − 단일 1 = 1). **합성+측정**(`inputfold_report.py`): 범위지정 분해 — baseline→+프로파일-under-W→+spec-under-requires→+부분-문장단위→+점근-차수→+재귀-가산, 각 범위·분모 명시, 단일 수 합산 없음; fallback 감사·HARAN-적합·분모 감사·측정된 실천장(잔여=진짜 I/O/무작위/데이터의존). LLM-free(AST)·정밀도 **1.0**/명시 등급·새 종류 0. `test_catalog.py` **139/139**(+5 §AC), test_build **273×3**(inputfold/ 미임포트). 무의존. 상세: `BUILD_LOG_catalog.md` §AC. ──────── (이전) |
| 모든 fold율 축 (§AB, 인증근사·확률·단위재정의·우회) | **무엇이 fold로 셀 자격을 얻는가, 그리고 무엇을 재는가 — 한 번도 안 건드린 두 축. 헤드라인은 *분해*지 단일 수 아님(네 등급 네 숫자).** 새 패키지 `foldaxes/`, test_build 미임포트, 무의존, ★공유 KV ADT 불변(273 안전 — 새 등급은 기존 APPROX_FOLD 재사용). **★LLM 아님의 정체성**: LLM도 근사한다 — 평범한 "대충 맞음"이면 우리가 대체하려는 그것이 됨. 우리 근사는 *모든* 입력에서, 첫 실행도 10¹⁶번째도 성립하는 기계증명 최악경계 — `∀입력. |folded−original| ≤ ε`, *정리*지 표본 아님. 표본/평균/경험검사는 거부. **AXIS 1 인증 근사**(`approx_fold.py`, 최대·정체성핵심): EXACT서 DECLINE하던 float 코드를 *보편증명* ε 내로 fold. ★기존 APPROX_FOLD 등급 재사용(`disposition.py`/`approx_cert.py`, never-exact R3.5) + 신규 interval-certified-ε 방법: `ErrorInterval`가 값범위+누적 반올림(연산당 ≤u·|크기|, u=2⁻⁵³)을 전역 도메인서 전파 ⇒ ε는 엄밀 과근사(모든 입력서 실오차≤ε). float 루프 Σⁿc→n*c, ε=5.57e-8 ∀|c|≤1000. ★표본 ε는 과소추정(표본 0.0 < 인증 5.57e-8)⇒거부 — LLM 아님의 선. **AXIS 2 확률**(`probabilistic_fold.py`): 1−2⁻ᵏ 확률로 정확, *유도된* 경계. `fast_certificates.py`(Freivalds 2⁻ᵏ, Schwartz-Zippel) + KV.PROBABILISTIC 재사용. ★AXIS 1과 구별 — 무작위성은 *체크의 동전*(입력 무관), AXIS 1은 모든 입력 ε. 경계 유도(Freivalds 5.96e-8, SZ 6.5e-55), 경험적 아님; 틀린 곱 DECLINE, 무작위 입력 미fold, 확실성으로 제시 안 함. **AXIS 3 단위 재정의**(`fold_units.py`): 표현식((x+1)(x-1)≡x²-1)·함수(두 합 루프→n(n+1))·영역(합성 아핀 누산기→단일 전이) 단위서 fold, 각 z3 증명. ★분모 정직: fold/loop·fold/expr·fold/func·fold/region은 *다른 분모의 다른 수*(0.6/0.33/0.25/0.2), 단위 명시·절대 병합 안 함. **AXIS 4 우회**(`bypass.py`): 유한·소규모·결정론 공간은 전체 입출력 사전계산·O(1) 조회. ★fold 아님 — value/throughput, 별도 보고; cold(256)/warm(0); 8비트 우회·32비트 DECLINE(2⁻¹⁶ 초과 ⇒ Ω(N) 노이즈); 틀린 조회 불가. **합성+측정**(`foldaxes_report.py`): 대분해 — EXACT(정밀1.0·무희석)+APPROX-ε(구간정리)+PROBABILISTIC(유도 2⁻ᵏ), 단위별, bypass 별도 — 네 숫자 합산 없음. ★LLM 아님 감사(표본-ε 거부·경계 유도), ★측정된 실천장(잔여=원리적 불가능: 진짜 I/O/무작위/데이터의존). EXACT 무희석·KV 불변·LLM-free(AST)·정밀도 1.0/증명경계. `test_catalog.py` **134/134**(+5 §AB), test_build **273×3**(foldaxes/ 미임포트). 무의존. 상세: `BUILD_LOG_catalog.md` §AB. ──────── (이전) |
| 다섯 fold율 무기 (§AA, 정규화·합성·추측·캐시·관용구) | **인식이 아니라 *추출*을 키운다 — 같은 구조를 다른 철자로 써도 놓치지 않게. fold율 = 인식가능 구조 × 표면화 능력; 이전 지시는 첫 인자를 ~15% 천장까지, §AA는 둘째 인자를 키운다.** ★전부 LLM-free·z3-검증·결정론 — 약한 LLM서도 동일(구속 설계 제약; 리포트가 AST로 구조 검증: foldrate 어떤 모듈도 LLM 클라이언트 미임포트). 새 패키지 `foldrate/`, test_build 미임포트, 무의존, 새 인증서 종류 0. **W1 정규화**(`canonicalize.py`, **곱셈기**, 먼저): 같은 구조 여러 철자(`i*2` vs `2*i`)를 brittle 매처가 놓침 → fold 전 정규형으로 모든 렌즈/메커니즘 동시 향상. proposer-disposer: sympy 제안·z3 처분(`prove_equiv_z3`로 ∀입력 original==canonical 증명; 미증명 거부). ★float 비결합성 존중 — 재결합은 정수/유리수만, float DECLINE. before/after 측정 **1→8 = 8.0× 곱셈기**(float 항목 정직히 미재작성). **W2 렌즈 합성**(`compose.py`): 한 변환이 다른 렌즈가 접을 구조 노출(정규화→Faulhaber); 각 링크 증명·최종 fold는 *원본* 대비 z3 증명. ★가산-중복, 곱셈 아님: 7개 코퍼스 **3 단일 + 4 합성전용 = 7 합성**(lift=합성전용, 중복 차감; 합집합이지 곱 아님) — "30–50%" 과장 없음. **W3 추측/조건부**(`speculative.py`, 완전 §X-P1): 동적 파라미터 가드·이중경로(Φ하 folded + 원본 fallback)·런타임 체크. ★fallback 불변식(검증): 정확성은 가드와 무관 — 미스면 원본 실행(정확, 느림), 속도만 Φ 의존(k=4→folded 20, k=9→fallback 45 둘 다 정확). ★런타임 정보지 LLM 아님(정직한 맥스웰 도깨비 — 런타임이 관측자); 구조적 입력만 — 진짜 입력의존은 가드 없음⇒DECLINE(비둘기집). 발급≠적용. §X-P1 guard 필드 — 새 종류 0. **W4 메모이즈 캐시**(`foldcache.py`, §V 확장): fold 결과/증명 의무/정규형 한 번 증명 후 O(1). ★건전 키(`canonical_ast_key`/`content_key`): 틀린 히트 불가(다른 코드⇒다른 키), α-동치는 건전 공유. ★cold-vs-warm 분리: cold **1 계산**·warm **0 재계산**(0.99 히트율) — value/throughput 올림, fold율 아님(§V 정직). **W5 도메인 관용구**(`domain_idioms.py`): prefix-sum(numeric)·sum-of-squares(stats)·running accumulator·pow2 정규화(ml) 등록, 각 기존 메커니즘 매핑·z3 증명(불건전 `x*3==x<<3` 거부). ★코퍼스 정직: 도메인 관용구는 도메인율(**0.571**) 올림, 백엔드 5.7%(**0.125**) 아님 — 분리 보고, 코퍼스-스왑 없음. **합성+측정**(`foldrate_report.py`): 헤드라인은 *분해*지 단일 수 아님 — W1 곱셈기(8.0×)·W2 가산 lift(4, 중복차감)·W3 발급≠적용+fallback불변식·W4 cold-vs-warm·W5 도메인-vs-백엔드 + 공유 baseline→정규화→full 분해(0.43→1.0→1.0). ★LLM-free AST 구조검증. ★정밀도 **1.0** 5개 배터리; 새 인증서 종류 0(22/14 불변); 비둘기집 벽 유지. `test_catalog.py` **129/129**(+5 §AA), test_build **273×3**(foldrate/ 미임포트). 무의존. 상세: `BUILD_LOG_catalog.md` §AA. ──────── (이전) |
| 세 새 fold 렌즈 (§Z, 생성함수·슬라이딩창·사영Möbius) | **합성곱은 곱, 창은 다시 더할 필요 없는 불변식, 분수는 행렬 — 셋 다 새 렌즈, 그러나 하나(Möbius)는 정직하게 *재사용*이다.** 새 패키지 `newlens/`, test_build 미임포트, 무의존(`forbidden_present==[]`), 전구간 z3-게이트, §X/§Y 정직 상속(적용된 fold만 셈·fold율≠가속·IEEE-754 주의). **LENS A 생성함수/형식적 멱급수**(`genfunc_fold.py`, 작지만 진짜 새것): 비선형 자기-합성곱 DP(`dp[n]=Σ dp[i]·dp[n-1-i]` 카탈란/모츠킨)는 22서 비선형이라 DECLINE, 하지만 멱급수로 보면 합성곱이 *곱*이라 점화식이 대수방정식(D=xD²+1)이 되어 닫힌형(C(2n,n)/(n+1))으로 O(N²)→O(1)/O(log N) 접힘. z3(Int)가 닫힌형==DP ∀n≤bound 증명(점화식+기저가 배열을 유일결정). 새 대수(⑬은 *선형* 합만); 기존 닫힌형 평가기(`fastkernels.catalan`) 재사용·closed_form 라우팅. ★IEEE-754 정직: 정수/유리수만 정확; 일반 FFT 곱은 float이라 precision-1.0 fold 아님 — 정수/NTT 이산모델서만 정확(O(N²)→O(N log N) *알고리즘 치환*, O(N)→O(1) fold 아님), float FFT DECLINE. **LENS B 슬라이딩창 집계**(`window_fold.py`, **최대 기여·가장 실용적**): 매 스텝 창 전체 재집계는 O(N·W), 불변식 `acc==aggregate(window)`로 스텝당 O(1) 접힘. 가역 합(정수/정확 군)은 `acc=acc−oldest+newest`(누산기 자체가 선형점화식 ⇒ ⑩ linear_recurrence), 불변식 z3 ∀-증명; min/max는 단조 데크(분할상환 O(1), 실제 창 원소 반환 ⇒ 구성상 EXACT·float 안전). ★float-상쇄 함정: float 합은 `acc−oldest+newest ≠ 재계산`(파국적 상쇄로 불변식 깨짐) ⇒ DECLINE(구체 증인: [1e16,1,1] 창이 증분 1.0 vs 참 3.0). 정수 곱 DECLINE(ℤ는 ×군 아님)·mode/median DECLINE. 새 증분-집계 패턴·기존 EXACT 판정(새 대수 종류 0). **LENS C 사영/Möbius**(`mobius_fold.py`, ★정직하게 *재사용*·새 기여 0): 분수점화식 x←(a·x+b)/(c·x+d)는 ℙ¹ 리프트로 Mᴺ O(log N) 접힘 — ★**정직한 발견**: 이건 이미 `catalog/mobius_fold.py`(§P P5)에 *동일* 구현(같은 PGL₂ 리프트·Mᴺ·z3 분모소거 항등식·matrix_recurrence·ad−bc=0/극 가드). 지시의 무중복 체크는 QF_BV/Galois/stride를 지목했지만 진짜 중복은 *우리 자신의 이전 작업*. 그래서 LENS C는 새것이 아님 — §P P5 **재사용**(중복구현 없음)·사영 fold를 **새 기여 0**(`new_contribution` 항상 False)으로 계산(이중계산 금지). §Z가 더한 유일 가치: 주어진 x₀의 *명시적 궤도 비영-분모 가드*(정확 유리수; c·xₙ+d=0 만나면 DECLINE — §P는 극을 섬으로만 표시) + float 주의(DECLINE). **합성+측정**(`newlens_report.py`): **발급 7·적용 7·적용_NEW 6·가속 6** — ★적용(7)>적용_NEW(6): Möbius 콜사이트는 적용·유효하나 새 기여 0(§P P5)이라 제외(유일 이중계산 위험 제거); ★fold율(7)>가속(6): 짧은 창 율만. 렌즈별 **B_window 최대**(적용-new 4)·A_genfunc 소(2)·C_mobius 0. ★무중복 검증: genfunc(대수 GF)·window(증분집계)는 QF_BV/Galois/stride와 분리; Möbius는 우리 §P P5만 중복(0처리). ★정밀도 **1.0** 3개 적대 배터리(틀린 닫힌형/float FFT/float-합 상쇄/비가역/영분모궤도/float Möbius/퇴화 REJECT); ★새 인증서 종류 0(22 메커니즘/14 종류 불변). `test_catalog.py` **124/124**(+3 §Z), test_build **273×3**(newlens/ 미임포트). 무의존. 상세: `BUILD_LOG_catalog.md` §Z. ──────── (이전) |
| 대안-렌즈 fold (§Y, 열대·격자·갈루아) | **22가 못 보는 구조를 새 축에서 본다 — 대수·순서·동치류, 그래도 23번째 메커니즘은 없다.** 22 메커니즘은 표준체 선형성으로 구조를 본다. §Y는 세 개의 진짜 새 *렌즈*를 더해, 그 셋이 못 보던 코드를 접는다 — 전부 기존 EXACT 판정 발급·`linear_recurrence`로 라우팅(22 메커니즘/14 인증서 종류 불변). 새 패키지 `altlens/`, test_build 미임포트, 무의존(`forbidden_present==[]`), 전구간 z3-게이트. ★§X 두 정직 상속: (1) **발급≠적용** — 실제 콜사이트서 적용될 때만 fold율에 셈; (2) **fold율≠가속** — 분리 보고. **LENS 1 열대/멱등반환**(`tropical_fold.py`, 최강): max/min/+ 루프(DP·Bellman-Ford·최단경로·스케줄링·병목)는 체 위에서 비선형 ⇒ 22서 DECLINE, 하지만 멱등반환 (ℝ∪{−∞}, ⊕=max, ⊗=+)서는 선형 ⇒ max-plus 닫힌형/열대 행렬거듭제곱으로 fold. 스칼라 `x←max(x+c,d)`→`max(x0+n·c, d+(n−1)·c)`, **z3 ∀ 귀납 증명**(base+step, c≥0); 열대 행렬거듭제곱=n-fold 루프(반환 결합법칙, per-n 증명 불요). ★**IEEE-754 정직**: 닫힌형은 ℝ/ℤ서 정확 증명 — float은 실수형 max-plus가 IEEE-754 누산과 갈릴 수 있어 **정수/유리수만 EXACT**·**float은 DECLINE**(FPSort 증명 없으면), 인증서가 산술모델 명시; 실수-only float fold 절대 발급 안 함. **LENS 4 유계-격자-높이 부동점**(`lattice_fold.py`, Knaster–Tarski, 순서 렌즈): 유한높이 격자서 MONOTONE 갱신은 ≤h 스텝에 부동점 도달 ⇒ n≫h면 O(n)→O(h)(64비트 비트셋 h=64→O(1)). 비트셋 격자({0,1}^k,⊆)서 z3가 (a)단조 (b)사슬 안정(extensive 상승 또는 co-extensive 하강) (c)높이바운드 f^h==f^{h+1} 증명. ★함정: 단조성은 *증명*해야지 가정 금지 — 비단조 연산 하나(−,~,데이터분기)면 MUST DECLINE. **LENS 5 갈루아 연결 정확 시맨틱 몫**(`galois_fold.py`, 동치류 렌즈): 작은 유한 추상도메인 D가 *정확히* 인코딩한 계산은 |D| 상태 내 순환(비둘기집) ⇒ O(n)→O(|D|)≈O(1). 표준 도메인 ℤ/mℤ·아핀맵 x←a·x+b; z3가 추상이 **정확**(다이어그램 가환 `∀x. α(f(x))==f#(α(x))`) 증명. ★정확 몫만 fold — 과근사(추상결과가 점 아닌 *집합*, 예 sign-of-x−1: α(+)∈{+,0})는 UNSOUND ⇒ DECLINE; ★|D|-폭발(큰 modulus)⇒가속 없음⇒DECLINE; ★2의거듭제곱 modulus는 QF_BV 중복(`x mod 2^k == x & (2^k−1)`, 기존 비트벡터가 이미 fold)⇒여기선 **차감**(이중계산 방지). **합성+측정**(`altlens_report.py`, 측정): 렌즈-shaped 콜사이트 코퍼스 — **발급 7·적용 6·가속 5**(두 정직 분리: 발급-but-미적용 1 = float 열대 콜사이트 정직히 미적용); 렌즈별 기여 **열대 최대**(적용 3 — max/min/+ 루프 흔함)·격자/갈루아 소(정직한 형태). 지시의 렌즈별 추정(~+1.0/+0.3/+0.5%p)은 렌즈-shaped 코드용 — 고정 백엔드 코퍼스(5.7% 기준)선 추가 적용 fold율 **~0**(일반 I/O/CRUD/제어 코드엔 hot 정확산술 max-plus·단조 격자루프·정확 비2거듭제곱 모듈러 궤도가 드묾, 정직). 비둘기집 벽 절대 — 무작위는 안 접힘; ~15% 천장 미반증. ★정밀도 **1.0** 3개 적대 배터리 전부(c<0/float/비단조/과근사/|D|-폭발/QF_BV-중복 REJECT); ★새 인증서 종류 0. `test_catalog.py` **121/121**(+3 §Y, 렌즈당 1), test_build **273×3**(altlens/ 미임포트). 무의존. 상세: `BUILD_LOG_catalog.md` §Y. ──────── (이전) |
| 제3의 길 fold 패러다임 (§X, P1–P5) | **23번째 메커니즘 없이 fold율을 올린다 — 22가 *닿는 곳*을 넓힐 뿐, 접을 수 있는 것을 넓히지 않는다.** 집합은 22로 수렴(14 인증서 종류). 5개 패러다임은 23번째를 안 더하고, 동적 파라미터/안 쓰는 출력/선형 functional/배열 쓰기/stride에 막혀 DECLINE하던 코드에 기존 fold의 *적용 기회*를 넓힘. 각 z3-게이트·정밀도 정확히 1.0·전부 기존 메커니즘으로 라우팅. 새 패키지 `thirdpath/`, test_build 미임포트, 무의존(`forbidden_present==[]`); `catalog/equiv_check.prove_equiv_z3`(assumptions=가드) 재사용. **★두 정직(이 지시의 생명)**: (1) **발급≠적용** — 조건부 fold는 실제 콜사이트에서 조건이 성립할 때만 fold율에 계산(가드 성립/투영 live/dual 사용/배열 선형/stride 주기); 발급-but-미사용은 기여 0(코퍼스-스왑 트릭, 금지). (2) **fold율≠가속** — 작은/짧은 루프의 적용된 fold는 율만 올리고 가속 0; 둘을 분리 측정·보고. **P1 공리/가드**(`axiomatic_fold.py`, 최강): CEGAR로 가드 Φ 합성, z3가 `Φ⟹folded==original` 증명(발급)→`callsite⟹Φ` 증명(적용); EXACT에 `guard` 필드(새 종류 0). **P2 투영**(`projection_fold.py`, 최안전·완전결정): 콜사이트가 쓰는 live 투영만 fold, `π(folded)==π(original)` 콜사이트별 증명. **P3 dual**(`dual_fold.py`): 선형 functional φ로 `φ∘f` fold(sum∘reverse==sum), 고정크기 기호배열서 증명; 비선형 functional DECLINE. **P4 배열/메모리**(`array_fold.py`, 신규 도메인): 귀납적 배열쓰기→양화 닫힌형 전이 `∀j. arr'[j]==cf(j)`, z3 ∀ 증명(타임아웃); off-by-one/비선형/aliased DECLINE. **P5 stride**(`stride_fold.py`, 최약): affine+주기일 때 `f^k` fold(negation 주기-2); affine 체크 게이트로 일반 비선형 f(s²+1)은 합성 없이 즉시 DECLINE(degree-2^k 폭발 방지). **합성+측정**(`fold_paradigms_report.py`, 측정): 패러다임-shaped 콜사이트 코퍼스 — **발급 8·적용 6·가속 4**(두 정직 분리: 발급-but-미적용 2·적용-but-무가속 2); 고정 백엔드 코퍼스 추가 적용 fold율 **0.0**(일반 I/O/CRUD/제어 코드엔 그 shape이 없음 — 정직, 연구의 20–30% 추정은 미검증); ~15% 천장 미반증. ★정밀도 **1.0** 5개 적대 배터리 전부(불건전 가드/투영/dual/배열/stride REJECT); ★새 인증서 종류 0(linear_recurrence/matrix_recurrence로 라우팅). `test_catalog.py` **118/118**(+1 §X), test_build **273×3**(thirdpath/ 미임포트). 무의존. 상세: `BUILD_LOG_catalog.md` §X. ──────── (이전) |
| 프론트엔드 완성 (§W, Phase 1–7) | **완전한 제품 — 계정·이력·파일·진행·오류·제공자 전부 검증, 그리고 절대 안 넘는 한 줄: API 키는 절대 저장 안 함.** 기존 `auth.py`(계정+세션+계정별 이력, api_key 컬럼 0 — 설계상) + §S 세-기둥 UI 위에. 새 패키지 `frontend/`, test_build 미임포트, 무의존(`forbidden_present==[]`) — 검증+확장. **★유일 하드 불변식: 키 절대 저장 안 함** — 구조적 증명: schema.sql에 api_key 컬럼 없음·auth.py가 키 안 씀·이력 행에 키 필드 없음. 키는 매 세션 재입력·탭에만·1회 사용 후 폐기. auth/비번 경로는 §R 게이트가 SENSITIVE로 표시 ⇒ 실제 검증 레이어 적용. **계정+이력**(auth.py 검증): signup이 비번 해시(bcrypt→scrypt, salt)+login 인증+틀린/약한 비번 거부; 계정별 이력 영속+재로드+격리(A는 B 못 봄); 키는 매 세션 재입력(옛 결과는 키 없이 표시). **파일**(`files.py`): **59** 허용형식(소스/데이터/텍스트/설정/노트북), 한 번에 ≤5(6번째 거부), 비신뢰입력 검증(경로순회/초과크기/미지원 전부 사유와 함께 거부), 구조 있으면 fold-가속 수집(캐시 → 재수집 O(1)). **제공자**(`providers.py`): **14**로 확장 — Anthropic/OpenAI/Gemini/Groq/Mistral/Cohere/DeepSeek/xAI/Together/Fireworks/OpenRouter/Perplexity + OpenAI/Anthropic-호환 게이트웨이 — 각 배선(transport/auth-env/model/get-key); 키 배선: 유효키 → 라이브콜 **PENDING-REAL-STACK**(egress BLOCKED, 가짜 없음), 키 없음 → 명확 메시지, 미지 → 거부. **오류**(`errors.py`): 모든 실패(네트워크/타임아웃/잘못된키/한도/제공자/파일/백엔드/인증)가 구체적·정직·실행가능 메시지 — silent 0, 가짜 성공 0. **진행**(`progress.py`): 실제 파이프라인 단계(생성/빌드/테스트/회귀/보안/fold/형식/수리/검증), 모드별(FAST 짧게, EXTEND 최심) — 가짜 스피너 아님. **UI**(`mrjeffrey.html` §S 확장): 상단 계정 로그인/가입+이력 뷰+키-미저장 고지, 다중파일 업로드(≤5), 라이브 진행 스트립, 구체적 오류 배너, 14-제공자 — 엔진 내부 재도입 0(§S 규율 유지). ★정직 범위: 라이브 스택(실 백엔드+실 제공자 콜)은 PENDING-REAL-STACK(egress BLOCKED+서버 없음) — 올바로 짓되 가짜 통합 없음; 여기서 검증가능한 전부(로직·배선·설정·보안경로·키-미저장) 검증(`feature_report.py`). `test_catalog.py` **117/117**(+1 §W), test_build **273×3**(frontend/ 미임포트; auth.py 무수정). 무의존. 상세: `BUILD_LOG_catalog.md` §W. ──────── (이전) |
| 엔진 자체-fold (§V, Phase 1–6) | **fold 엔진을 안으로 — 엔진 자신의 반복 작업을 접어 아무것도 두 번 계산 안 함(건전 캐싱).** 수천 obligation을 O(1)로 서빙하던 무기를 탐지/검증/fold/증명/AST파싱/LLM프롬프트에 적용. 모듈 `enginespeed/`, test_build 미임포트, 무의존(`forbidden_present==[]`). **★정직 스파인**: (1) LLM 지연은 비가역 — 호출 COUNT만 줆(외부 제공자; 임계경로면 Amdahl로 엔진-fold가 총합 못 움직임 → 호출 줄이기가 유일한 정직한 공격); (2) 엔진 자기 작업은 foldable; (3) **cold vs warm 분리 보고** — cold는 0(첫 실행 전부 계산), 승리는 warm/반복 작업에만, warm 숫자를 첫-실행으로 절대 제시 안 함; (4) **precision 1.0 캐싱 통과** — hit은 건전 키(content hash 또는 증명된 α-canonical form)에만, 재계산-동치로 증명·충돌 0; 틀린/stale hit은 빌드 실패. **Phase 2 cache**(`cache.py`): L1/L2/L3 멀티레벨+absence-인증서(증명된 음성 캐시, known-miss 재시도 안 함)+JIT-아티팩트, 오프라인 pre-proving 일반화. 건전 키 `content_key`(sha256, 구성상 완전)·`canonical_ast_key`(α-정규화 AST — α-동치는 키 공유, 다른 코드는 분리); LRU 축출 항상 안전(재계산만 유발); `prove_key_completeness` 배터리서 충돌 0 증명. **Phase 1 profile**(`profile.py`): cost×repetition 랭크; LLM(Clock A, 모델링 — egress BLOCKED) vs 엔진(Clock B/C, 측정) 분리 — 모델 워크로드서 LLM이 벽시계 지배(~0.998) → 응답 캐시(호출수)가 큰 레버. **Phase 3 folded ops**(`folded_ops.py`): parse/z3-verify/fold/증명-obligation/★LLM-응답 각 건전 캐시 메모이즈; pre-fold 패턴 라이브러리 O(1). **Phase 4 brewing**(`brewing.py`): idle 사전계산+critical-path prefetch — 건전(실작업 미리, speculative-wrong 아님). **Phase 5–6+리포트**(`speed_report.py`, 측정): op별 cold-vs-warm(z3 verify 이 머신 **~340–390× warm**, cold ~0.8ms 분리 보고)+모드별(FAST/NORMAL/EXTEND 각 cold vs warm, EXTEND 160 ops 최심); ★LLM **호출수 절감**(20프롬프트→3실호출, **0.85** 측정; 지연절감 MODELED-pending — 횟수지 지연 아님); precision **1.0** 캐싱 통과(충돌0·재계산동치·α-동치 키공유). `test_catalog.py` **116/116**(+3 §V), test_build **273×3**(enginespeed/ 미임포트). 무의존. 상세: `BUILD_LOG_catalog.md` §V. ──────── (이전) |
| SWE-bench 증폭기 (§U, Phase 1–6) | **Opus는 만들고, MR.JEFFREY는 검증·필터·수리한다 — 형식 검증이 보이는 테스트 너머를 본다(90→95 갭).** Opus 4.8의 raw 패치 생성을 제안자–검증자 기계로 감쌈: N개 후보(일부 틀림) → **층 게이트**(빌드→보이는 테스트→회귀→★형식-테스트-너머) → 증명된 것만 제출, 실패는 정밀 실패(가장 풍부한 건 **형식 반례** — 패치가 틀린 정확한 입력)로 수리, 형식-최강 검증 패치만 제출(hidden에 절대 도박 안 함). 모듈 `swebench/`, test_build 미임포트, 무의존(`forbidden_present==[]`); 재사용 `catalog/equiv_check`(bounded_equiv/prove_equiv_z3+반례)·`claude_agent.claude_generate`(api_key=None→mock=정직 BLOCKED)·clocks·dependency_audit·KV. **★차별점(90→95)**: 보이는 테스트는 부분집합·SWE-bench는 hidden도 채점 — 보이는 테스트 다 통과해도 hidden 엣지에서 틀릴 수 있음, 단순 러너는 못 봄. 형식 검증이 입력 도메인 전체에서 정확성 증명(bounded_equiv 도메인-건전, 또는 산술-표현가능하면 무한 z3 ∀); 보이는-통과-형식-오류 패치는 반례(=hidden 입력)와 함께 REJECT → "보이는 테스트 통과"를 "실제로 정확"으로 전환. **★정직 범위**: 실제 Verified/Pro 점수는 **MODELED-PENDING-REAL-STACK**(task repos+러너+라이브 Opus egress 필요, 여기 없음·Clock A BLOCKED — GPU가 device-pending였듯), 서브스트레이트 숫자를 실제 점수로 절대 제시 안 함. 실제 측정된 건 자체완결 **실행 미니벤치**(8 파이썬 task: 버그fn+이슈+보이는+hidden 테스트+레퍼런스 오라클+녹화 후보)의 **메커니즘 사다리**(실코드 실행+실z3): opus-단독 **0.125**→+다중후보 **0.25**→+회귀 **0.375**→+지역화 **0.5**→+형식 **0.75**→+fix루프 **0.875**, 각 단 실측 한계 상승. ★차별점이 **3건**의 hidden 실패(off-by-one in_range·wrong-at-0 sign·형식-반례-수리 round_half_up) 방지 — 테스트-only 파이프(0.5)가 출하했을 것. ★**정밀도 1.0** 제출: 7 제출·0 거짓(전부 형식 검증⟹hidden 정확)·1 정직 DECLINE(collatz — 후보 통과 0·예산내 수리도 틀림 → 제출 안 함). 무한 z3 ∀가 abs(x) 전체 증명+틀린 것 반례. `test_catalog.py` **113/113**(+4 §U), test_build **273×3**(swebench/ 미임포트). 무의존. 상세: `BUILD_LOG_catalog.md` §U. ──────── (이전) |
| UI 재구성 — 안전·빠름·정확 (§S) | **디자인은 지키고 대시보드는 들어낸다 — 세 단어로: SECURED · FAST · ACCURATE.** 제품 UI(`mrjeffrey.html`)를 세 기둥으로 재구성, 그 외엔 없음. 디자인 시스템 그대로 재사용: 컬러 토큰·3D `.slab`(레이어 그림자+`::before` 광택+`::after` 접지)·perspective 틸트+`floatIn`/`screenIn`·다크모드 토큰+토글·타이포(sans/mono, clamp `h1`)·sticky 블러 topbar+발광 brand dot·`:focus-visible`/`.sr-only`·반응형. ★세 강조 팔레트를 세 기둥에 재배치(`[data-mode]` 유지): **SECURED→보라(신뢰)·FAST→청록(속도)·ACCURATE→앰버(정밀)**. ★표면에서 엔진 내부 전부 제거 — 빌드마다 바뀌어 페이지를 낡게 만들던 숫자들: 측정 배수(47×/111×/1.48×)·Amdahl 천장+`.meter`/`.wall`/`.fill` 천장 시각화·핫스팟 비율·z3 호출수·지연ms·`exact`/`probabilistic`/`decline` 등급 배지+범례·복잡도 스윕·코퍼스 패널행(`differential PASS`)·모드 내부표(detectors/verifier_tier/risk_posture/stop_condition)·낭비유형 은어. DATA 블롭은 이제 제공자 목록+세션전용 키 정책만. 결과는 세 기둥의 사람 문장 — "주입·경계·메모리 점검…민감 경로 상수시간 보강"/"이미 효율적—바꿀 것 없음"/"같은 결과 확인" — 정직한 부정도 배지 아닌 문장으로, 날조 측정 없음(정적은 결과를 DEMO로 명시·라이브는 실제 결과를 사람말로 번역). 붙여넣기+제공자 흐름 보존(무료-무카드 배지·키 발급 링크·세션전용 키), 정직 한 줄 유지(키는 이 탭에만, 로그·저장·타 전송 없음). CODE⇄MATH 토글과 MATH 화면은 이 아티팩트에서 은퇴(등급 배지 UI라 새 규칙 위반; "그 외엔 없음"). MATH 엔진은 서버(`mathmode/`)에 남아 백엔드 불변식 여전히 테스트 강제, UI 표면만 제거. 자체완결 단일 HTML(바닐라 JS+내장 CSS). 옛 숫자-핀 UI 테스트는 구조 단언으로 재작성(`test_s_ui_three_pillars`+갱신된 §B1/§B2 백엔드 테스트+TASK-5 UI 블록). `test_catalog.py` **109/109**, test_build **273×3**(mrjeffrey.html 엔진 미임포트; §B1/§B2는 이제 MATH 백엔드 단언). 무의존. 상세: `BUILD_LOG_catalog.md` §S. ──────── (이전) |
| 조건부 검증 보안 (§R, Phase 1–5) | **LLM이 *필요*를 정하고, 검증기가 *사실*을 증명한다 — 필요한 곳에만, 그 외엔 0.** LLM은 GATE(세계지식으로 보안민감 여부 판단: 비밀/PII/인증/암호/비신뢰입력→민감싱크), 검증기는 JUDGE(민감일 때만 레이어 ON, 취약부재 *증명* 또는 정직히 flag). ★"안전"은 증명됐을 때만 — 잘못 clear한 취약점은 빌드 실패 correctness 위반. NOT-SENSITIVE면 레이어 완전 OFF·코드 바이트동일 = **오버헤드 0, 측정값**(필요없는 곳에 보안 거는 것 자체가 결함). 모듈 `security/`, test_build 미임포트, 무의존(`forbidden_present==[]`). `ct_certifier`(anti-KyberSlash 혈통) 부활시켜 일반 LLM 코드에 조준. **Phase 1 게이트**(`llm_gate.py`): NEED 질문("안전한가"는 검증기 몫). 민감→ON, 비민감→OFF, 불확실/malformed→보수적 SENSITIVE(분석만, auto-harden 금지). ★정직 시계: LLM egress BLOCKED⇒보수적 정적 휴리스틱(비밀/PII/인증 식별자·암호API·비신뢰→싱크·동적문자열 싱크)으로 폴백, 판정을 **"heuristic — LLM 세계지식 판단 아님"**으로 라벨. **Phase 2 논리취약**(`logical_vulns.py`): 정적(런타임 0)⇒비민감코드도 분석. 각 클래스 PROVEN_ABSENT(z3/정확) 또는 FLAGGED-위치: bounds(guarded range(len())·상수인덱스 증명; 그외 flag), injection(파라미터화/상수싱크 증명; 연결/f-string 싱크 flag), overflow(**QF_BV/Int-range 증명 재사용** — SAT⇒flag·UNSAT⇒증명), memory(use-after-del/None-deref), race(**B-엔진 충돌분석 재사용** — disjoint r/w⇒race-free). **Phase 3 사이드채널**(`sidechannel.py`, 민감만): LLM이 못 보는 부분, 2축 합성 — **3A 열역학**: 상수시간 taint가 비밀의존 분기/메모리인덱스/가변시간 `/`·`%`(KyberSlash류)/루프바운드 부재 증명⇒CT_PROVEN 아니면 구체적 leak; **3B 통계**: GF(2) t-probing — 안전⟺어떤 t-부분집합도 비밀을 span 안 함(랜덤이 항상 남아 상쇄). 타이밍 leak은 masking으로 못 닫음(상수시간 필요); 정직 레벨 **source-IR — 바이너리 미포함**(컴파일러가 leak 유입 가능: Binsec/Rel). **Phase 4 조건부 하드닝**(`hardening.py`): (게이트 SENSITIVE)∧(하드닝본 CT_PROVEN)∧(배터리 전입력 차등동치)일 때만 적용 — 비밀분기 select→분기없는 `(a&m)|(b&~m)`, Clock-C 지연비용 **측정·정직 공개**. ★게이트-BINDING: NOT-SENSITIVE는 절대 하드닝 안 함(오버헤드 결함); 결과변경/여전히 leak하는 fix는 REJECT. **Phase 5+캡스톤**(`overhead_report.py`·`security_report.py`, 측정): 비민감코드는 **바이트동일·네이티브 속도**(Clock-C 비율≈1.0, 구조적 오버헤드 0 — Phase 3–4 미실행), 같은 레이어가 민감+flagged엔 하드닝하고 측정비용 지불 — 필요한 곳에만. 라벨된 적대 코퍼스로 단 하나의 수: **정밀도=1.0 ⇔ false-safe==0** — KNOWN-VULNERABLE 전부(SQL-concat·unguarded index·overflow·use-after-del·race·비밀분기·KyberSlash `%`·깨진 1차 masking) FLAGGED, 취약코드 절대 "안전" 주장 안 함(false "safe"=빌드실패 위반); 증명가능-안전 recall은 정직 보고(여기 1.0, DECLINE도 정직). `test_catalog.py` **108/108**(+5 §R), test_build **273×3** 격리. 무의존. 상세: `BUILD_LOG_catalog.md` §R. ──────── (이전) |
| 증명된 I/O 최적화 (§Q, Idea 1–6) | **물리 I/O는 못 빠르게 한다 — 증명된 만큼 *덜* 한다(횟수 절감) + 기다림을 겹친다(오버랩).** 모든 캐싱/프리페치 시스템은 *추측*하지만, 여기 6개는 z3/정확 증명이 통과할 때만 적용 → heuristic이 소심해야 하는 곳에서 공격적. 정밀도 1.0이 I/O로 확장: 틀린 캐시히트/투기/stale-keep/거짓병합 = 정확성 위반 = 빌드 실패. 모듈 `accel/`, test_build 미임포트, 무의존. I/O는 인-레포 결정론 모델 — **I/O 횟수 절감은 정확 측정**, 실 wall-clock 지연은 **modeled-pending-deployment**(GPU throughput가 device-pending였던 것과 동일). **Idea 1 시맨틱 캐시-동치**(`semantic_cache.py`): z3가 다르게 쓰인 두 요청이 모든 입력에서 동일결과임을 증명(∀x A⟺B/A==B)→동치류 전체를 1 I/O로; near-equiv(x>5 vs x>=5, a-b vs b-a)은 distinct 증명·분리(거짓공유 0). **Idea 2 I/O-패턴 fold**(`io_pattern_fold.py`): 요청이 아핀 점화식이면(`for page: fetch(page)`) 닫힌형 인덱스집합(differential)+독립성 증명→N 순차 왕복→1 배치(왕복 횟수, 전송량 아님); 의존체인·비아핀은 DECLINE. **Idea 3 증명된 투기**(`proven_speculation.py`): work가 I/O 결과와 독립(disjoint r/w) 증명→대기와 오버랩(롤백 없음, 추측 아님); 비밀의존·레이스는 DECLINE; I/O를 빠르게 한다고 안 함. **Idea 4 무효화-최소화**(`proven_invalidation.py`): write 타깃집합 ∩ 엔트리 read집합=∅ 증명→write 가로질러 엔트리 유지(재fetch 회피); 겹치면 보수적 무효화(stale-keep 0). **Idea 5 최대 배칭**(`maximal_batch.py`): 추이적 쌍별 독립 증명→흩어진 I/O 전부 1 왕복으로 coalesce; 의존 요청은 분리. **Idea 6 콘텐츠 dedup**(`proven_dedup.py`): 결정론+바이트동일 증명→1 I/O 병합; 바이트다름/비결정(nonce)은 분리, 시맨틱-만은 Idea 1로. **§7–9 합성+Amdahl+배터리**(`proven_io_report.py`, 측정): 6개 합성으로 모델 I/O-heavy 워크로드의 I/O 횟수 **87→27(0.69 절감)**, I/O 바닥 **50%→15.5%**, 전체프로그램 **1.53×**(정직하게 2.0× 천장에 Amdahl 묶임; 전부-distinct 필수 I/O 20개는 안 움직임 — 그것만이면 ~1.0×). ★적대 정밀도 배터리(near-equiv·의존체인·비밀의존투기·영향write·바이트다름/비결정 dedup) **100% REJECT — 정밀도 1.0**. 횟수절감=측정, 지연=modeled. `test_catalog.py` **103/103**, test_build **273×3** 격리. 무의존. 상세: `BUILD_LOG_catalog.md` §Q. ──────── (이전) |
| 탐지기 RECALL (§P, P0–P6) | **확률→프로덕션 갭 좁히기 — 새 메커니즘 0, 탐지기가 눈을 뜰 뿐.** 메커니즘 집합은 22로 수렴(k-regular가 마지막). §P는 23번째 종류를 추가하지 않고, 기존 22의 *변장된 인스턴스*를 제안자가 인식하게 만들어 fold 분율을 올림 — 제안자는 liberal, 인증기는 EXACT 유지, 위양성 구조적 불가능(정밀도 1.0). 새 모듈 `catalog/`(blackbox_fallback·lazy_decline·holonomic_sum·bitvector_ring·mobius_fold·distributed_state·recall_detect·recall_report), test_build 미임포트, 무의존. **P0** 272/1을 부하-flake(`test_native_s3_triage_layer` perf gate)로 확정, 격리 **273×3 CLEAN**. **P1** 블랙박스 폴백: 표현 변장(재귀/클로저/CPS/객체상태)을 출력 시퀀스에서 BM+Hankel로 복원→기존 `linear_recurrence`; 순수성 가드(추이적)가 부작용 함수 제외, held-out 정확예측 disposer가 window-fit(피보나치-후-발산) 적대자 차단. **P2** lazy-decline: 주기조건부(k%2)·mod-k(k%3)는 부분합이 C-finite→블랙박스 `linear_recurrence`(⑩/⑪); 망원합(1/(k(k+1)))→Gosper `gosper_antidifference`(⑫), 정확 망원항등식 증명(조화 1/k→DECLINE). **P3** Zeilberger 홀로노믹-합 ⑬-면: 중첩 2변수 정합 Σ_k F(n,k)(이항/DP)→기존 Zeilberger WZ 엔진 `zeilberger_telescoping`, O(N²)→O(N)(20301 vs 201); 비홀로노믹 2^(k²)→DECLINE. **P4** QF_BV 비트벡터-링: 아핀 Z_2^w 루프(LCG/체크섬, 실수 리프터·ℝ-블랙박스 둘 다 못 봄)→O(log N) 행렬거듭제곱, **z3 QF_BV** ∀x 비트정확 증명→기존 `verified_modular_recurrence_collapse`; 비선형/암호 믹싱→DECLINE(Ω(N) 벽). **P5** Möbius ⑬-면: homographic (a x+b)/(c x+d)→사영선 M^N, 분모소거 z3 다항항등식→기존 `matrix_recurrence`; ad−bc=0·차수≥2(Galois)→DECLINE. **P6**(최난) 분산/async 상태: 핸들러에 흩어진 아핀 누산기를 교차함수 taint로 재조립, 고정 스케줄로 한 라운드 합성, 행렬거듭제곱 fold, z3로 순차 핸들러 의미와 동치 증명→기존 `matrix_recurrence`; ★정직 경계: 비선형·비결정 스케줄·추출불가는 DECLINE(대부분 async 상태는 증명가능 섬 밖, 그 DECLINE이 옳음). **FINAL**(`recall_report.py`, 측정): 고정 PRODUCTION_BACKEND_CORPUS_v1 **8.6%→8.6%**(Δ0 — 진짜 비폴드성 I/O/제어 코드, 정직히 보고; 5.7%→8.6%는 GAP-1 단일인자-range 수정), DISGUISE_STRUCTURE 코퍼스 **0.0→0.733**(진짜 recall 이득), 전부 기존 5종 인증서 종류. ★**23번째 종류 없음**, ★**정밀도 1.0**(전 우선순위 음성통제 DECLINE·위양성 0). `test_catalog.py` **101/101**, test_build **273×3** 격리. 무의존. 상세: `BUILD_LOG_catalog.md` §P. ──────── (이전) |
| A/B/C/D 극한+합성+550 (§O) | **A/B/C/D를 도달가능 한계까지 + fixpoint 합성(엔드투엔드 동치 증명) + 550케이스 스트레스(정밀도=빌드 게이트).** 모듈 `accel/maximal.py`+`accel/stress_550.py`, test_build 미임포트, 무의존(감사 `forbidden_present==[]`). **MAXIMAL**(각 확장은 ATTEMPT만 넓히고 ACCEPT은 안 넓힘, applied⇔proved): **A.transitive_purity**(콜그래프 단조 fixpoint — 함수는 국소적으로 깨끗 AND 모든 피호출자가 추이적으로 순수일 때만 PURE; 사용자정의 순수 헬퍼 호출도 이제 캐시가능, 불순 leaf는 그래프 전체 불순 유지), **A.nested_batch**(중첩 루프 배칭 — carried 없음+평탄화 결과동치 증명, 재배열은 DECLINE), **B.prefetch_overlap**(다음단계 I/O를 현단계 compute와 오버랩 — 다음 I/O가 현 compute의 read/write를 안 건드릴 때만 SAFE, 의존 prefetch는 DECLINE; 증명=안전, 지연이득은 정직한 max(io,compute) 모델). **compose_to_fixpoint**: 증명된 변환을 더 적용할 게 없을 때(FIXPOINT)까지 반복 적용 — 엔드투엔드 동치 = 각 단계 증명 ⇒ 원본≡최종 by ≡의 추이성 + 원본-vs-최종 differential 재확인; 차이나는 단계는 REFUSE(정밀도 우선). 데모: 느린 파이프라인[dedup O(N²)→square-recompute→sum] → [dedup O(N)→square-map→sum] 2증명단계로 fixpoint·엔드투엔드 ≡ 확인. **550 스트레스**(`accel/stress_550.py`, 측정): 500 MIXED(전 무브에 걸친 균형 — pure/impure·indep/carried·disjoint/conflict·equiv/wrong·lossless/lossy·hazard 등) + 50 UNSTRUCTURED 불가능코어(CSPRNG·진짜RNG·벽시계·실제I/O·순환락 교착·순서바꾸는 "빠른"배치·앨리어싱 해저드). ★빌드 게이트=정밀도: "그대로 둬야 하는" 케이스는 전부 DECLINE, 단 하나의 FALSE APPLY도 빌드 실패; 50 불가능코어 전부 DECLINE. ★절대 550/550 보고 안 함(그게 거짓 — 절반은 DECLINE이어야 함). 측정된 정직 분할: **250 가속(전부 증명) / 300 정확히 DECLINE(50 불가능코어 포함); 정밀도 1.0(false apply 0·crash 0); 가속가능 부분집합 recall 1.0**. 빌드 중 정직 자기교정 1건: serde "apply" 케이스가 처음엔 DECLINE(레퍼런스 인코더가 값을 문자열화 → int 입력은 lossy 왕복, 검증기가 옳게 거부) → 케이스를 진짜 lossless(문자열 값)로 고쳐 라벨을 현실에 맞춤(검증기 약화 아님). `test_catalog.py` **94/94**, test_build 영향 없음(accel/ 미임포트). 무의존. 상세: `BUILD_LOG_catalog.md` §O. ──────── (이전) |
| REAL-USAGE + PROD FOLD + 정직 UI (§N, T3·T4·T5) | **제품을 실제로 굴려 — 정직한 갭 리포트(버그 둘 발견·둘 수정) + 프로덕션 폴드-커버리지(진짜 실세계 숫자).** "finish everything" 패스의 결정론 검증 빚을 정직히 청산: T1 조용한 머신에서 273×3 **전부 CLEAN**(앞선 perf-gate 흔들림은 부하였지 회귀 아님), T2는 §M GPU. **T3 — 프로덕션 폴드-커버리지**(`catalog/fold_coverage_production.py`, 측정): §K의 0.60은 큐레이트 프로브("의도적 구조 코드에서 엔진 거동")였지 실세계 숫자가 아님 — 이 미터는 실 fold/lift 엔진을 **named** 코퍼스(`PRODUCTION_BACKEND_CORPUS_v1`, 35함수: DB접근·문자열/JSON·dict집계·검증·제어흐름·I/O·crypto = 실제 CRUD 백엔드 형태)에 돌려 두 속도 안 섞고 3영역 분류 — **점근 폴드**(EXACT) vs **상수배**(region-3) vs **DECLINE 바닥**; ★정직 결과 **점근 폴드 ≈ 5.7% raw / 7.25% cost-weighted** = LOW 한자릿수(연구가 줄곧 추정한 ~1–3%, 프로브 0.60보다 훨씬 낮음 — 대부분 백엔드 코드는 폴드가능 점근 구조 없는 I/O·자료구조·제어흐름). 코퍼스는 실코드 **대표**로 구성(인플레 위해 massage 안 함 — 높은 숫자가 거짓). 정밀도 1.0: 진짜 산술누적 루프만 fold, I/O/crypto/control은 안 fold. **T4 — MR.JEFFREY 실사용 테스트 + 정직 갭 리포트**(`mrjeffrey_gap_report.py`, 측정): 요약이 아니라 제품을 결정론 표면 전체에서 실제 구동하고 깨진 걸 적어 고침. ★live 가능: 제안 절반(LLM이 spec→HARAN 작성)은 키+egress 필요·여기 없음 ⇒ Clock-A 호출지연 **[BLOCKED]**, 절대 날조 안 함(spec-size 프록시만). 다운스트림 parse→**검증(Clock B)**→**fold/lift(Clock C)**→가속은 결정론·live 구동. ★실사용이 찾은 **진짜 버그 둘, 둘 다 수정**: **GAP-1** 검증된 리프터가 two-arg `range(lo,hi)`만 매칭 — 가장 흔한 SINGLE-arg `range(n)`가 조용히 DECLINE → 수정: 루프 regex의 lo-그룹 옵셔널화(base 0 기본), z3 귀납적-합 증명이 여전히 정확성 게이트 ⇒ ATTEMPT는 넓혔으나 ACCEPT은 안 넓힘(`for k in range(n): s+=k`가 이제 n·(n+1)/2로 fold). **GAP-2** 비다항 본문(`s += 2**k`)이 z3 인코더에서 **uncaught ValueError** 발생(2^n은 다항 기질 밖) — uncaught crash는 sound-or-DECLINE 위반 → 수정: encode/prove 단계가 기질-밖 케이스를 잡아 정직히 DECLINE. 둘 다 live 배터리로 가드: VERIFY 배터리(라벨된 6 HARAN — 틀린 구현 전부 잡힘, **false VERIFIED 0**, 조용한 실행 accuracy 1.0)·FOLD 배터리(실 루프 — 다항 fold, 기하본문·무루프 DECLINE, **crash 0**). Clock-C fold 승리는 직접 측정(naive O(n) vs O(1) 닫힌형, 타이밍 전 정확성 검사 — n=20000서 ~2300×, 진짜 점근 붕괴·faster-but-wrong 아님). 임팩트-랭킹 원장에 BLOCKED 제안(GAP-3)·inclusive-Σ 경계 관례(GAP-4, by-design)·정직한 한자릿수 천장(GAP-5, by-design=T3)도 기록. **T5 — 정직 UI/랜딩**(`mrjeffrey_landing.html`+`mrjeffrey.html`, test-enforced): PHASE-8이 이미 측정 숫자(115× 히어로·데모바·1.00× decline)를 소스에 PIN하고 메인 UI가 모드별 CLOCK·정직 EXACT/PROBABILISTIC/DECLINE 배지·STATIC/LIVE 분리(STATIC은 당신 코드 휴리스틱 탐지·탐지된 낭비유형만 ship·없으면 1.0×·각 행 "엔진 표준 측정"으로 라벨)를 함; T5는 남은 정직 갭 셋 종결 — (1) 정직성 섹션의 **교육용** 예시(700%kernel→1.67×, 3·20·6.7≠400)를 *illustrative*로 명시 라벨, (2) 히어로 **115×** 출처 오귀속 수정(115.494는 csv_stats="data utility"·PROBABILISTIC이지 "never-profiled" 앱[47×] 아님 → 실출처 명기+"not typical"), (3) 정직 **커버리지** 프레이밍 추가(큰 승리는 MINORITY — 프로덕션 대부분은 폴드가능 점근구조 없는 I/O/제어흐름, 한자릿수만 fold=T3; 115×는 SELECTED best case). `test_post_consol_task5_honest_ui_landing`가 셋 다+메인UI 마커 강제, PHASE-8 PIN 유지(23숫자 backed). `test_catalog.py` **93/93**, test_build 273 영향 없음(T4는 lift.py 변경 후 273×3 재확인; T5는 HTML+test_catalog만 — test_build 미참조). 무의존. 상세: `BUILD_LOG_catalog.md` §N. ──────── (이전) |
| VERIFIED GPU (§M) | **자체제작 cuBLAS급 커널(HARAN→PTX) + 은닉구조 fold + soul-deep 최적화 — 전부 증명됨.** 의존≠모방: 우리 OWN 커널을 PTX(공개 ISA)로 내림, 드라이버에만 의존, cuBLAS/cuDNN 바이너리 절대 안 씀. 모듈 `gpu/`+`soul/`, test_build 미임포트. 무라이브러리의존(no cuBLAS/cuDNN/외부BLAS; 감사 `forbidden_present==[]`). **MOVE 1 자체 GEMM 커널**(`gpu/ptx_codegen.py`, 번역검증): naive→shared-mem **tiled**→**tensor-core**(`wmma.mma.sync`) PTX 텍스트로 방출. ★cuBLAS가 못 주는 엣지: 모든 커널 TRANSLATION-VALIDATED — 계산이 reference GEMM과 같음 증명, 정수 residual=0(ragged-K 타일잔여 포함; 정수합 재결합 정확⇒z3 LIA-closed); 잔여타일 빠뜨리는 버그 타일링→TRANSLATION_DECLINED. ★정직 디바이스: 환경에 GPU/ptxas 없음⇒PTX는 방출 아티팩트, 증명은 모델 의미+CPU 레퍼런스(디바이스 무관), THROUGHPUT은 **device-pending**(GFLOP/s 날조 0); 온디바이스선 ptxas 어셈블+cuBLAS 분율 측정. **MOVE 2 은닉구조 fold**(`gpu/hidden_structure.py`, 두 번째 무기): dense처럼 보이는 행렬에서 잠재구조 탐지+정확증명 후 붕괴 — **low-rank**(정확 ℚ 분해 M=C·R residual=0→matvec O(N²)→O(Nr), matmul O(N³)→O(N²r); rank-3 N=24=5× 감소), **circulant/Toeplitz**(정확 패턴→FFT O(N log N) 점근), **Kronecker** A⊗B(블록일관성→vec-trick B·X·Aᵀ). ★정직: dense=cuBLAS 타이+증명(MOVE-1 커널로 폴스루), 구조有=op-count 승+증명 — dense matmul을 cuBLAS보다 빠르게 만든다고 절대 주장 안 함. 정밀도 1.0: 거짓 제안 구조는 residual=0 실패→dense 폴스루. **MOVE 3 soul-deep**(`soul/systems.py`+`soul/mobile.py`): 검증된 A/B/C/D를 도메인별 증명가능 한계까지 — 시스템(lock→검증된 lock-free[단일위치 교환RMW=CAS-안전; 다위치는 락 유지], alloc→pool, syscall→batch, 자료구조→교정), 모바일(network→cache/dedup[호출 COUNT 절감, RTT 아님], render→재계산제거, serde→fast-path, battery→dead-elim); 잔여는 정직히 명명(network RTT·커널크로싱 지연=비가역 바닥). **리포트+배터리**(`gpu/gpu_acceleration_report.py`, 측정): ★PRECISION=1.0(틀린 커널 검증실패·거짓구조 폴스루·불안전 최적화 거부); 정직 범위 "dense는 cuBLAS 안 이김—우리껀 타이+증명, 구조에선 op-count 승, 시스템/모바일은 증명한계까지." `test_catalog.py` **90/90**, test_build 273 영향 없음. 상세: `BUILD_LOG_catalog.md` §M. ──────── (이전) |
| VERIFIED ACCEL (A/B/C/D) | **검증된 제품-가속 엔진 — fold가 아니라 가속에서도 정직하게(propose→verify→apply, 측정).** fold 엔진은 점근 구조 있는 ~1–3%(§K 미터)를 접고, 이 엔진은 나머지 ~95%(I/O 대기·직렬화·자료구조·할당) 핫패스를 친다 — 한 파이프라인: PROFILE 먼저(Amdahl 게이트: 측정된 핫패스 밖은 가속 안 함), LLM/탐지기가 PROPOSE, z3/정확 인-레포 오라클이 의미보존을 PROVE, **증명된 것만 APPLY**, 전체프로그램 wall-clock MEASURE. 모듈 `accel/`, test_build 미임포트. 무의존(감사 `forbidden_present==[]`). **★중심 불변식**(`accel/pipeline.py`): `Acceleration.applied ⇔ proved`(증명 없으면 느린 원본 유지); `precision()`=적용∩불안전=∅; `amdahl_whole_program()`는 컴포넌트 배수를 정직한 전체프로그램 배수로(5%를 10× → ~1.047×, 절대 컴포넌트 배수 아님); 세 시계 분리(A 제안/B 검증/C 런타임). **A 검증된 I/O 제거**(`verified_io.py`): A1 캐싱=AST 효과분석으로 순수성 증명(시계/RNG/IO/전역읽기쓰기/인자변이 없음·모든 호출 순수·보수적), A2 배칭=독립성+정확 결과동치, A3 dedup/dead-IO=중복(같은인자⇒같은결과)·죽은(미사용) 제거·live 보존. **B 검증된 병렬성**(`verified_parallel.py`, 최고 증명문턱): B1 비동기=disjoint read/write 충돌집합, B2 데이터병렬=carried-dep/공유쓰기-race 없음·reduction은 결합+교환 증명시만, ★정직측정: 증명은 안전·측정 배수가 배포 결정 — 샌드박스 오버헤드바운드(~0.15×) 정직보고·미배포, B3 교착=lock-order 비순환(사이클=반증된 버그). **C 검증된 알고리즘 교정**(`verified_algo.py`, fix당 최고천장): C1 복잡도감소(linear-search→hashmap)=결과동치 증명+측정 **~34–36× O(N²)→O(N)**(fold 아님, 나쁜코드 교정), C2 루프불변 hoist/CSE, C3 early-exit=후조건안정성. 결과변경 swap·비불변 hoist·안전하지않은 early-break(SUM 끊기)→REJECT. **D 검증된 serde/할당**(`verified_serde.py`): D1 직렬화 fast-path=바이트동치+무손실 왕복(필드누락→REJECT), D2 할당재사용=무앨리어싱-해저드(share→mutate→read→REJECT). **§6 한계패스+§7 제품**(`limit_pass.py`): A/B/C/D를 핫패스마다 소진하고 Amdahl로 전체프로그램 속도 합성·정직한 한계 진술 — 모델타깃에서 **36.6× 컴퓨트 fix가 0.30 wall-share로 Amdahl 묶여 ~1.48× 전체프로그램**, **50% 비가역 물리-I/O 바닥**; "전부 10–20×"는 절대 출력 아님. 제품: 검증된 LLM-결과 캐싱=A1을 LLM 스텝에(건전 content-hash, hit=LLM 건너뜀, stale 불가능), 측정 3/6 호출 회피; MR.JEFFREY=A/B/C/D 제안자(비신뢰, 엔진이 검증). **§8 적대적 정밀도 배터리+§9 리포트**(`acceleration_report.py`, 측정): "빠른" 버전이 일부러 틀린 15케이스(impure-as-pure·dropping-batch·dependent-async·non-assoc reduction·cyclic lock·result-changing swap·unsafe early-exit·lossy serde·aliasing-hazard pool) 전부 100% REJECT — **PRECISION = 1.0**(불안전 적용 0), 안전건 recall 1.0. 정직 범위: fold는 구조있는 ~1–3%, 이 엔진은 증명가능한 핫패스(컴퓨트 fix는 실재하나 Amdahl 묶임, 물리 I/O는 비가역 바닥) — 둘 다 "전부 빠르게"가 아니라 "증명된 것만". `test_catalog.py` **86/86**, test_build 273 영향 없음. 상세: `BUILD_LOG_catalog.md` §L. ──────── (이전) |
| POST-CONSOLIDATION (22) | **수렴 후 구현 — 모든 유효한 무의존 결과 구현 + 폴드-커버리지 미터(측정).** §J 수렴(≈21, 수율 33%→20%→2%) 뒤 새 후보 원장을 **4 입학 게이트**(distinct-in-kind · z3-closed · asymptotic O(N)→O(polylog) · dependency-free)로 심사, 유효한 무의존 결과는 전부 실가동 코드로 구현하고 나머지는 정직히 강등. **★PHASE 1 — Tier-1(6개 건설; 1 입학·4 면·1 Group-B):** ★**M22 k-정규 수열 폴드**(`mech_kregular.py`, Allouche–Shallit) — 유일한 진짜 신규 메커니즘. base-k **자릿수-인덱스 선형표현** a(n)=v·∏A_{digit}·w를 k-커널(인-레포 그리디 오토마톤 폐쇄+정확 ℚ 선형대수)에서 구성; popcount/Stern/자릿수합/누적합 fold(차원 2–4), O(n)→O(log n). ★distinct: popcount는 2-정규이고 여기서 fold되지만 **증명상 C-finite 아님** → M11/M1/M13 전부 DECLINE — 어떤 메커니즘도 못 접는 클래스를 접음. 인증서=LIA 등식(z3 스팟체크+정확 ℚ 재치환 처분자); 동등성 섬 결정가능(Krenn–Shallit)·성장 경계 결정불가(Skolem/Hilbert-10)→DECLINE. **카운트 21→22.** defective-선형화(`mech_defective.py`)→**M11 면**(단항식 폐쇄⇒C-finite); Tensor-Evolution/CR(`mech_tev.py`)→**M13 면**(다항 z3 ∀i 유한차분증명+기하 닫힌형); **AARA**(`mech_aara.py`)→**Group-B 검증**(신규 인증서종 `amortized_potential`; ∀n-건전 z3 ∃Φ∀state 포텐셜법; 폴드 아님—점근 게이트 실패); semiring-Newton(`mech_seminewton.py`)→**M13 면**(트로피컬 (min,+) Newton ≤n步 vs Kleene; 같은 최소부동점, Kleene 교차검증+재치환); SFA(`mech_sfa.py`)→**M9 면**(LIA 가드 기호 bisimulation 언어동등성; 비선형 가드→DECLINE). **PHASE 2 — 건설로 심사(둘 다 강등; M23/M24 미입학):** MPST(`mech_mpst.py`)→**M17 면**(전역프로토콜→엔드포인트 사영+동기곱 교착자유 BFS; well-formedness=국소-대역 접합=M17 H¹); edge-cover/AGM(`mech_edgecover.py`)→**M10 면**(분수 edge-cover ρ* z3.Optimize+AGM 조인크기 한계; 삼각형 ρ*=3/2; 구조-강제 크기한계). **PHASE 3 — 8 Tier-2 면 + Tier-3 상수배 + Tier-4 제외:** `tier2_faces.py`(monoid-hom→M13, poset-Möbius→M2, CRN-δ0→M11, DEC[d∘d=0]→M18, restricted-chase→M14, species→M12, trace-monoid-Foata→M15, twin-width→M10); `excluded_candidates.py`(Tier-3 polyhedral/MTBDD/deforestation→**region-3 가속, 상수배, 점근 불변—폴드 아님**; Tier-4 19개 제외 각 정확 사유: ZX→M8 면, crypto-accumulator 불가능코어, Somos→gap_recur, forest-algebra→M9, point-process/markov-cutoff 확률적, parametricity/nominal-sets 비폴드 …). `mechanism_faces.POST_CONSOL_FACES`(14=8 Tier-2+6 강등)는 동결된 통합 `FACES`(7)와 **분리** 등록(§J 스냅샷 보존). **PHASE 4 — 폴드-커버리지 미터**(`fold_coverage.py`, 측정): `POST_CONSOL_PROBE_CORPUS_v1`(30항목)을 실그레이더로 돌려 두 속도 절대 안 섞고 3영역 분류 — **점근 폴드**(EXACT, raw 0.60/cost-weighted 0.64) vs **상수배**(region-3, 점근불변, 0.10) vs **DECLINE 바닥**(불가능코어, 0.30); 15 메커니즘 기여. 미터가 정밀도 게이트 겸함(위양성 0)·자기일관. ★큰소리 면책: 큐레이트 프로브 코퍼스, 프로덕션 코드 표본 아님 — 엔진의 영역별 거동·메커니즘 커버리지 측정이지 일반 코드의 폴드 가능 구조 빈도(~1–3%) 추정 아님. **PHASE 5 — §K 리포트**(`post_consolidation_report.py`, 측정): 최종 **22** 명명 메커니즘(§J 21+★M22); 정직 disposition 표(1 입학/14 면/1 Group-B/3 상수배/19 제외); 인증서종 갱신(가산-폴드-종 14→15 via k-regular; AARA종은 검증, MPST/edge-cover종은 M17/M10로 환원); 수율붕괴 지속(Tier 2–4→0); A/B 재분류; **PRECISION = 1.0**(전 신규모듈 불가능코어 DECLINE). `test_catalog.py` **81/81**, test_build 273 영향 없음. **무의존**(감사 `forbidden_present == []`). 상세: `BUILD_LOG_catalog.md` §K. ──────── (이전) |
| CONVERGENCE (≈21, 수렴) | **메커니즘 집합 100% 통합 + 마지막 가산 메커니즘 + 추측-하드게이트 + 수렴 리포트.** 3차 폐쇄성 테스트 완료: 신규-가산 수율 ~33%→~20%→~2% 붕괴(3R에 새 사각지대축 없음) ⇒ **수렴**, ≈21 명명 메커니즘(원14+M15–M21), 천장 ~30–33(원시기법3+면 포함). ★정밀도 측정 정확히 1.0(전 집합+Conley+면+게이트 위양성 0), 불가능 코어 불변. **PHASE 1 100% 감사**(`mechanism_audit.py`): 20 메커니즘 전부 실가동(0 defer)+재검증 인증서+결정가능섬 경계+불가능코어 DECLINE; C7→M4+M7 확인. **PHASE 2 Conley 지수(M21)**(`mech_conley.py`): 고립 불변집합의 큐빅 상대호몰로지 H_*(N,L)/𝔽₂. ★정직 distinct-vs-forced: 1D source와 sink은 같은 정적 N(⇒동일 M15 바코드·M14 장애물)인데 Conley 지수가 다름(t¹ vs 1) — exit set L이 *동역학*으로 결정(Morse/불안정차원, M14·M15 둘 다 안 내보냄) ⇒ **진짜 distinct(M21), net-new=1**, M14∘M15 강제합성 아님; 비고립→DECLINE. **PHASE 3 면 등록**(`mechanism_faces.py`, 카운트 증가 없음): tropical→M13, multifractal/rate-distortion→M4, Feigenbaum→M6(검증수치⇒PROBABILISTIC, EXACT 절대 아님), Atiyah–Singer→M9(χ=V−E+F), Boolean-Fourier→M11/M9(Walsh+junta), cobordism→M9; 부모⊆{4,6,9,11,13}, 커버리지만 확장. **PHASE 4 추측 하드게이트**(`conjectural_gate.py`): Hodge/거울대칭/표준추측-모티브/Iwasawa/BSD + 비계산코어(회로하계 natural-proofs·Wang 타일 결정불가·일반 word problem Novikov–Boone·고차 K이론) 의존 인증서 REJECT(명시적 추측-의존 DECLINE, EXACT 절대 안 됨); 구성적 섬(Hodge 분해·명시적 다양체 étale·저차 K이론·p진 L값·Dehn/자유축약 word problem) PERMIT; 미지→fail-safe REJECT. **PHASE 5 수렴 리포트**(`convergence_report.py`): ≈21 명명·수율붕괴 기록·**가산 인증서-종류 14목록**(폐쇄 기준: 미래 후보는 목록에 *없는* 종류 인증서만 재개방)·정밀도 1.0·추측 클러스터 영구 격리·원14 대칭/정적/대수 코어 닫힘. `test_catalog.py` **71/71**, test_build 273 영향 없음. 상세: `BUILD_LOG_catalog.md` §J. ──────── (이전) |
| MECHANISM GROWTH (≥17) | **메커니즘 집합 성장 — 닫힘이 깨진 곳에서 (M15–M18 +스코프 M19–M20).** 폐쇄성 테스트가 "14, 닫힘"을 뒤집음: 4–6개 후보가 충실히 환원되지 않음(관계/비대칭·다중척도위상·국소→대역·동적 사각지대). 제안자→EXACT-처분자 규율로 추가; ★정밀도 측정값 정확히 1.0(전 신규 메커니즘 위양성 0), 14의 대칭/정적/대수 코어는 닫힌 채, 불가능 코어 불변. 집합은 이제 **OPEN at ≥17** — 추가 메커니즘은 발견-또는-환원, 절대 선언 금지. **M15 지속 호몰로지**(`mech_persistence.py`, gudhi/ripser 없이): Vietoris–Rips+𝔽₂ 경계행렬 환원→바코드(정확)+병목-안정성 증인(M9 불연속과 구별); 정규화 지속도≥0.4·diam 게이트, 무작위 구름→DECLINE. → [15]. **M16 인과 복구**(`mech_causal.py`, 인과 라이브러리 없이): 선언된 DAG 상대 do-calculus back-door 식별성(모럴화 조상그래프 d-분리)→do-free estimand; ★faithfulness+그래프는 **선언 공리**(인증서에 명시, 관측에서 인증 불가 — Uhler 2013/Verma–Pearl); 잠재 bow→비식별→DECLINE. → [16]. **M17 층 코호몰로지**(`mech_sheaf.py`): 유한 셀룰러 층 δ⁰/H⁰(대역절단)/H¹(등급 장애물); 접합 성공→EXACT, 실패→[δs] DECLINE; ★M14 일반화(이진 "대역절단 없음"=H⁰-공집합 특수경우). → [17]. **M18 기하 흐름**(`mech_flow.py`): 라플라시안 열흐름→정준형, 단조 Dirichlet-에너지 Lyapunov 증인(M6 대수 lumping과 구별되는 동적 인증서); 연결 무구조→자명 합의 DECLINE; SOC는 부분경우. → [18]. **M19 매듭/Jones**(스코프, `mech_knot.py`): Kauffman 괄호 상태합→writhe-정규화 Jones(검증: trefoil=−t⁻⁴+t⁻³+t⁻¹); 정규형 아님(비합류 ≠M8)·완전 아님(≠M9); #P-난해 대형→DECLINE. → [19]. **M20 비주기 질서**(스코프, `mech_aperiodic.py`): cut-and-project 준결정 — 두 타일+균형(Sturmian) 순서⇒순점 회절; 피보나치 사슬 fold, 주기/무작위/불균형→DECLINE. → [20]. **PHASE 21 C7 재배치**(`pass_D.py`): expander/스펙트럼-갭을 M11(오류—상태복구 아님)→M4(λ₂=전도도 SDP 완화)+M7(expander mixing 준무작위)로 정정. **§I 리포트**(`mechanisms_report.py`, 측정): 전 메커니즘 회복·PRECISION=1.0(불가능 코어 전부 DECLINE)·EXACT 장부 residual-0-only·C7 검증·OPEN≥17·금지의존 `[]`. `test_catalog.py` **66/66**, test_build 273 영향 없음. 상세: `BUILD_LOG_catalog.md` §I. ──────── (이전) |
| GAP CLOSURE (14) | **14개 "가짜-무질서" 갭 폴딩 — 옛 프로브가 놓친 진짜 구조 회복.** 각 갭 = 더 강한 *제안자* + EXACT *처분자*; ★정밀도 측정값 정확히 1.0 유지(위양성 0 — 정확 인증서 없이 절대 fold 안 됨, 틀린 제안은 잡혀서 DECLINE). 불가능 코어(보안CSPRNG/Kolmogorov-random/일반 비선형점화식/비홀로노믹)는 안 움직임. **탐지 갭**(`gap_recur.py`·`gap_signal.py`·`gap_matrix.py`, `probe_cascade` 배선): P1 비선형 점화식(x[n]=P(x[n-1..n-k]) 유계차수, ℚ run-forward) · P2 행렬/결합 점화식(v[n]=M·v[n-1], ℚ 재치환) · P3 대수적 관계(윈도 항들 다항관계, 정확 ℚ 영공간=Gröbner-cofactor) · P4 비-Fourier 희소(Walsh–Hadamard/Haar 무손실+희소) · P5 블록/Kronecker(Van Loan 재배열 rank-1+정확 재구성, block-low-rank; 단위행렬 DECLINE) · P6 조각별(분할+세그먼트별 BM, 부분 fold) · P7 변조(a[n]=ρ·a[n-P], ℚ 재합성). **리프트 갭**(`gap_lift.py`): P9 관계형 filter-aggregate→comprehension(차등 배터리; automata/graph는 정직 DECLINE) · P10 아핀/기하 루프 요약(x=a·x+b→닫힌형, ℚ run-forward) · P11 앨리어스 a[idx[k]] 아핀 idx→직접(z3 UNSAT) · P12 부분 리프트(내부 Σ루프만, z3 귀납, glue 보존). **인증 갭**: P13 완전 Zeilberger(`gap_telescope.py` — 홀로노믹 점화식 추측 후 **WZ 인증서 필수**: t=G(k+1)−G(k) 정확 다항 항등식 재검; ΣC(n,k)=2ⁿ, ΣC(n,k)²=C(2n,n) 인증; 비홀로노믹 2^(k²)→DECLINE) · P14 PROBABILISTIC 티어(`gap_prob.py` — δ-유계 구조[P8 준주기 비공약수 톤]을 `lossless_gate`로 approximation 등급, **절대 EXACT fold 안 함**; random→DECLINE). **§H 리포트**(`gaps_report.py`, 측정): 13/13 갭 회복, **PRECISION=1.0**(전 신규경로 위양성 0), EXACT 장부 residual-0-only(12)/PROBABILISTIC(1) 분리, 불가능 코어 6/6 DECLINE 유지, 금지의존 `[]`. `test_catalog.py` **60/60**, test_build 273 영향 없음. 상세: `BUILD_LOG_catalog.md` §H. ──────── (이전) |
| EXTREME ACCEL (A·B) | **생성코드 속도(A)를 정직한 극한까지 + 제품 지연(B) 별도로 — 측정·인증.** A 가속은 거대한 *상수배*(점근 아님 — 일반 생성코드는 폴드 구조 없음); 각 레이어는 인증서 또는 N-측정 보유, 합성수는 **스택을 실제로 돌려 측정**(레이어 숫자 곱 아님). Clock C(컴퓨트)·Clock A(LLM 지연) 장부 분리 — A의 극한 속도는 LLM-묶인 B를 움직이지 않음. **PHASE 0** `catalog/accel_profile.py`(생성코드 벤치마크 median-of-k 프로파일, wall-share 랭킹, `layout_simd` 의존성분석으로 레이어 태깅, PHASE 1–7 순서를 측정으로 결정·cold<5% 방치). **PHASE 1–5** `catalog/accel.py`(각 인증·측정, Clock C): native(`native_backend` 재사용 — LLVM 컴파일정확성+Rust NTT 차등테스트 ~15–18×) · vectorize(numpy=네이티브C⊕SIMD, 의존성합법성[tier A]∘차등동치 — 초월함수 ~6–7×/BLAS reduction ~100–110×; 불건전→MISMATCH·비병렬→DECLINED) · cores(독립성∘차등 **인증**=안전 기여; 샌드박스 멀티프로세싱은 마샬링 오버헤드로 <1× — **정직히 보고, 가짜 금지**) · cache_layout(AoS→SoA, 앨리어싱/일관성 인증 ~70–80×) · superopt(`superopt` z3/Schwartz–Zippel 정제, 작고 정직). **PHASE 6** `accel.pgo_reorder_dispatch`(프로파일 기반 디스패치 재정렬, 상호배타 first-match 차등동치 인증·비배타→DECLINED ~2.4×). **PHASE 7** GPU=CUDA/ROCm 금지의존 → **헌법적 DECLINE**(out-of-scope 문서화, GPU 런타임 미임포트; numpy가 검증된 병렬 경로). **PHASE 8** `catalog/accel_bpath.py`(B-path Clock A): 2단계 캐시가 LLM 호출 절감 — exact-hash는 검증된 결과 재사용, normalized-key는 **재검증 필수 제안**(실패→실제 생성으로 폴스루, 미검증 절대 배포 안 함); Clock-A 절감=회피 생성 수, 독립 장부. **PHASE 9** `catalog/accel_report.py`(§G: 레이어별 측정+인증, 합성 스택 **end-to-end 측정**[elementwise ~7×/reduction ~110×, 곱 아님], Amdahl 전체프로그램 상한, A/B 장부 분리). 점근 UNCHANGED·uniform-Nx 없음·금지의존 `[]`. `test_catalog.py` **55/55**, test_build 273 영향 없음. 상세: `BUILD_LOG_catalog.md` §G. ──────── (이전) |
| PRODUCT HARDENING | **write→verify→fix 루프를 제품으로 단단히 — 빠르게·정확하게·안전하게·정직하게(PHASE 0–9, 측정).** 세 시계 절대 안 섞음(A=LLM 지연 [live BLOCKED: egress]·B=검증·C=fold/네이티브; 각 승리는 시계+N 명시·uniform-Nx 없음). **PHASE 0** `catalog/product.three_clocks`(median-of-k, Amdahl 병목 지명; A는 정직 BLOCKED). **PHASE 1 = 최대 Clock-A 승리: 건전 캐시** `catalog/prodcache.py`(stdlib만; key=sha256(canonical(입력)+버전) — hit은 cold와 바이트 동일, 변형입력·버전범프는 **항상 miss**[stale hit 불가능, test-enforced]; 반복요청 워크로드의 Clock-A 절감 = 회피한 LLM 호출 수, 정확). **PHASE 2/3** 난이도-프로브 모델 라우팅(easy→small/hard→large, live BLOCKED)·first-pass-wins 병렬검증·증분 재검증(변경없는 부분을 z3 번역검증으로 *증명* 후 생략). **PHASE 4/5** 멀티오라클 합의(독립 오라클 ≥2 만장일치만 EXACT, 아니면 DECLINE)·타깃 피드백 fix 루프(수렴 또는 N 후 정직 DECLINE — 미검증 코드 절대 배포 안 함). **PHASE 6 키 보안 LEVEL-1**(`provider.py`만 env 격리·`claude_agent.py`는 `os` 차단): 레포 전역 grep로 제품 소스 키모양 리터럴 0·`_KEY_STORE` None 유지·명시적 실패모드+키안전 지수백오프(auth/400은 **절대 재시도 안 함**[나쁜 키는 일시적이지 않음], rate-limit/network/5xx만 2·4·8·16s 백오프, 메시지 키 마스킹). **PHASE 7 검증된 네이티브 백엔드(Clock C)** `catalog/native_backend.py`(`egraph_native`+`rust_accel` 재사용): HARAN fold 닫힌형→네이티브 i64 LLVM(**컴파일-정확성 인증서** = z3 인증 추출 ∘ Alive2 번역검증, bit-exact; 어긋나면 TRANSLATION_DECLINED·절대 방출 안 함)·NTT 핫커널→std-only Rust cdylib(차등테스트 N). Amdahl 정직: 네이티브는 컴퓨트 핫패스의 상수배 Clock-C 승리 — Clock-A 묶인 제품을 빠르게 하지 않음(나머지는 shell, 헛된 전면 재작성 안 함). 측정: Σk² bit-exact 인증·Rust NTT ~15× vs 동일알고리즘 Python. 점근 UNCHANGED. Rust/LLVM 의존은 툴체인에만(Python-core import 아님; 감사 `[]`). **PHASE 8 UI 정직 숫자**(`mrjeffrey_landing.html`↔`pillar3_studio_data.json`): 랜딩 숫자가 측정원천에서 조용히 드리프트(히어로 112×→재동기 115×·DECLINE 0.97×→1.00×·데모바 6개 전부) — 측정 JSON으로 재동기 후 테스트로 **PIN**(Amdahl 법칙 ratio≤ceiling 전행 검사·DECLINE은 사유 동반·날조/드리프트 숫자는 이제 테스트 실패). **PHASE 9 통합 리포트** `catalog/product_report.py`(전부 측정 live·시계 분리·금지의존 0). A의 극한 컴퓨트 속도는 B(LLM 묶임)를 움직이지 않음 — 두 장부 분리. `test_catalog.py` **49/49**, test_build 273 영향 없음. 상세: `BUILD_LOG_catalog.md` §F. ──────── (이전) |
| CATALOG ENGINE (캡스톤) | **무질서→구조 엔진 — 14 메커니즘 완성 + 15 번역우회 배선 + 무손실 게이트.** 측정(`catalog/capstone_report.py`): **12/14 메커니즘 apply가 실제 게이트 절차를 돈다**(M6 multigrid·M10 금지마이너[비구성]만 정직 defer). **PHASE 1 공짜 승리**(레포 배선): M2←`groebner`(cofactor), M8←`equality_saturation`(e-graph Z3 인증 정규형), M13←`ic3_pdr`(귀납불변식)+`taint_ifds`(IFDS), M11←`prony`(정확 은닉점화식), M14←`closure_classifier`(Galois/Liouville, 바이너리 부재→정직 defer). **PHASE 2 우회**(각 독립 재검증): `lstar.py`→M9(Angluin L* 최소 DFA, 완전불변량), `string_solver.py`→M2(z3 문자열 QF_S, 모델 재치환; cvc5는 금지 의존이라 z3로), `zx_normalize.py`→M8(pyzx ZX 등가, 텐서 재검), `chc_solve.py`→M13(z3-Spacer 불변식 합성+3 Horn 조건 신선솔버 재검증). **PHASE 3 무손실 게이트**(`catalog/lossless_gate.py`): 우회를 fold로 믿기 전에 완전성/완전추상성/정제 중 하나를 per-instance 인증서로 판별 — PROBABILISTIC은 손실→`approximation` 표시, 절대 EXACT fold 금지(잘못 접기 원천 차단); 합성은 모든 단계 무손실일 때만 무손실. **PHASE 4 무거운 우회**(`catalog/heavy_bypasses.py`): 8개(Metalift·d-DNNF·pynauty·pykoopman·Sepref·SystemDS·MONA·OpenFST) 호출부+정직 defer(정확한 차단사유). 위양성 0(음성통제 전부 DECLINE). Ω(N)/비둘기집/정지 안 깸 — 늘어난 건 구조 도메인으로 라우팅되는 입력집합(도메인 라벨 필수). `test_catalog.py` **32/32 green**(test_build 273 영향 없음 — 순수 가산). 상세: `BUILD_LOG_catalog.md` §10·§11. ────────  (이전) **무질서→구조 카탈로그 엔진 (14 메타메커니즘) — PHASE A–F + 합성 몸통·대가리 완료.** `mechanisms/`(14 메커니즘 1..14 + 2 원시기법, 프레임워크 닫힘·15번째 없음) + `catalog/`(94 변환 = §4 명명 대표, 9패스·14메커니즘 전부 매핑, 38 합성). 카탈로그 커버리지 **94 등록 / 11 VERIFIED / 83 정직-defer**(전부 UNVERIFIED(사유)·kernel=None — 가짜 통과 0). **합성 엔진(`catalog/ir.py` + `catalog/compose.py`)**: `StructForm` IR가 메커니즘 사이를 흐르며 체이닝(kind/data/residual/grade/cert_chain/path) — `apply`는 `Mechanism.step`으로 StructForm→StructForm 시그니처 통일. `combine_grade` = **약한고리 법칙**(EXACT∘EXACT→EXACT; PROBABILISTIC 섞이면 PROBABILISTIC·δ_total≤Σδ 합집합경계·절대 격상금지; DECLINE은 그 지점 short-circuit) — EXACT를 PROBABILISTIC cert 위에 주장하면 **ADT 예외**(거짓 격상 0, test-enforced). `plan`(대가리): probe[0,1]^14 → 합성 트리 SHAPE. `execute`(몸통): 트리 walk·StructForm 스레딩·각 단계 §7 게이트. **실제 도는 합성 체인**: ★**M7 분해**(무질서=구조+의사난수: 깨끗한 k-희소 신호 → 닫힌형[7→1→12] EXACT + 나머지 bound≈machine-ε; 노이즈엔 정직 DECLINE — `sparse_fft`/`prony` 재사용), **M9⟂M14**(완전불변량 OR 장애물: Petrov→EXACT 분류[9,14]·turbulence/E₀→DECLINE+장애물 인증서), **M4|M14**(SOS or 불가능), **M2(∘M3)**(구조화 QE: z3/CAD 소거+유한증인 융합). 배선-defer: M10→M14(금지마이너 비구성)·M6∘M13(multigrid) — 몸통이 호출, 다리 계산만 정직 defer. 측정(`measure_composition`): M7은 **읽는 샘플 O(k)≈88 vs O(N)**가 진짜 우위(Amdahl p=0.96 @N=2048); numpy C-FFT 대비 벽시계는 정직히 "범위 내 교차점 없음"(가짜 가속 0). §6 DECLINE 백본(Rice/비압축성 + 15 경계; turbulence는 M9⟂M14 소유). `test_catalog.py` **27/27 green**(test_build 273 영향 없음 — 순수 가산). 상세·정직 defer 목록: `BUILD_LOG_catalog.md` §C. |
| (이전) 진행 중 | **UNIFIED ARSENAL**(a 변환계 + b ~70 fold 패밀리 + c 물리) — §1 ✅ (G1·G2·G3·G4) → §2 ✅ (Petkovšek·Abramov·Risch·Kovacic·CAD) → §3 물리 P1–P9 ✅ → §4 transforms ✅ · ROUTER ✅ → **MATH recognition PHASE-1 ✅**. (NATIVE-CORE 완료: `NATIVE_CORE_REPORT.md`.) |
