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
