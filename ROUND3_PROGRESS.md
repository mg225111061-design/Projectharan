# ROUND 3 / 10 — Tier-2 EXACT-share: verification techniques that PROMOTE to EXACT (live tracker)

DoD per item: capability built/wired → graded by ADT (EXACT = machine-checked equivalence; sound static
analysis where a wrong "safe" is a correctness bug) → adversarial/unsafe case → DECLINE (with a witness where
applicable) → committed → ticked with commit + test. Verification verdicts are Clock-B (correctness), reported
separately from any Clock-A/C speedup. Honest UNVERIFIED[reason] where a sandbox limit blocks.

RESUME POINTER: #67 (machine-faithful translation validation) done. Next: #68 purity → EXACT memoization,
#71 termination (ranking function), #70 range/interval analysis, then #61 BMC / #65 k-induction for unbounded
loops, #63 SMT portfolio (Clock-B speed).

Legend: ☑ done(new, tested) · ◩ verify-existing (cite test) · ☐ pending · ⚠ UNVERIFIED[reason]

## Group P — equivalence & refinement
61. ☑ bounded model checking — unroll two stateful transitions k steps, Z3-check equivalence over ALL input sequences ≤k; equivalent opt → EXACT bounded-depth (∀inputs); divergence → DECLINE with SHALLOWEST counterexample trace (off-by-one@depth1 x=11; clamp bug@depth2); pairs with #65 k-induction [test_round3_bmc_bounded_equiv; pillar3/bmc.py]
62. ◩ symbolic execution oracle — symbolic_oracle.py [exists]; wire a P3 equivalence gate
63. ☑ cheap-first verification tiering (Clock-B: decide more WITHOUT the solver) — syntactic→interval→Z3; Z3 calls 9→2 (4.5× fewer) on the battery, every cheap-tier decision cross-checked SOUND vs Z3; a disagreeing fast path → DECLINE. (SMT-tactic portfolio substituted §A2: Z3 decides even nonlinear via preprocessing, so "fewer-unknown" didn't demo; tiering is the robust Clock-B win) [test_round3_verification_tiering; pillar3/verify_tiering.py]
64. ☐ CEGAR (counterexample-guided abstraction refinement) for loop invariants
65. ☑ k-induction — prove closed form/loop invariant for UNBOUNDED n (Z3 base+step); promotes bounded-domain identity → EXACT for ALL n; Σi, Faulhaber Σi², Σodd, x%2==0, x≥0 proven; non-inductive (n(n+1)/2, n²) fail step → DECLINE [test_round3_kinduction_unbounded; pillar3/kinduction.py]
66. ◩ refinement (output refines input wherever defined) — translation_validate [exists]
67. ☑ translation validation under REAL machine semantics (bitvector/overflow-aware) — 5 sound peepholes EXACT (bv-proven), 3 overflow-unsafe REFUTED→DECLINE+cex; (x+1)>x PROVEN over ℤ but REFUTED over bv32 @ INT_MAX (catches the miscompile idealized reasoning misses) [test_round3_bitvector_translation_validation; pillar3/bv_validate.py]
## Group Q — sound static analyses (a wrong "safe" is a correctness bug)
68. ☑ purity / determinism analysis → EXACT memoization — conservative AST proof (no impure calls/global·arg mutation/yield); pure→memoize EXACT ~74×@repeated args; nondeterministic (random) AND global-mutating fns both classified impure→DECLINE (soundness regression-guarded — caught+fixed a global-mutation false-pure) [test_round3_purity_memoization_exact; pillar3/purity.py]
69. ☑ alias / loop-carried dependence analysis (Z3, sound) — ∀i≠j w(i)≠r(j)∧w(i)≠w(j) over affine indices ⇒ EXACT parallel-safe (a[2i]=g(a[2i+1]) etc.); real dependence (a[i]=g(a[i+1])) → DECLINE+witness (never a false independent) [test_round3_aliasing_dependence; pillar3/aliasing.py]
70. ☑ interval/range analysis → EXACT no-overflow machine-int fast path (sound abstract interpretation over [lo,hi]); unifies the NTT/matmul no-wrap bound; conv |v|≤2e8⊂int64 EXACT, >2^63 OR int32 ⇒ DECLINE; over-approximation brute-checked [test_round3_interval_range_analysis; pillar3/interval.py]
71. ☑ termination via ranking functions (Z3, sound) — r bounded-below ∧ strictly-decreasing under guard ⇒ EXACT termination certificate (4 loops proven); increasing / steps-over-zero loops → DECLINE+witness (never assume termination) [test_round3_termination_ranking; pillar3/termination.py]
72. ☑ complexity certificate — measure naive&fast at several n, fit log-log growth exponent, certify fast is a STRICTLY LOWER class (Δexp≥margin, R²-gated); O(n²)→O(n) certified (exp 2.05→0.96), PROBABILISTIC (empirical, δ=1−R²); same-class O(n)/O(n) pair→DECLINE (no false asymptotic claim) [test_round3_complexity_certificate; pillar3/complexity_cert.py]

DETERMINISTIC SUITE RUN: `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 test_build.py` ⇒ 163/163. Thread caps remove numpy/numba/BLAS worker-pool inter-test CONTENTION (the load-induced flake source: offload, partial_eval, phaseM2, foldext2, pillar3_stage2) while PRESERVING the SIMD/JIT wins (vectorization/compilation, not parallelism). Each flake also passes in isolation uncapped.
73. ☑ effects analysis → safe reordering & batching/coalescing — effect-set commute (no W-W/R-W/W-R, not both ordered I/O); independent ops reorderable; idempotent reads coalesced N→1 round-trips EXACT ~85× (4000→40); intervening write/RAW/ordered-I/O → DECLINE (never stale/reordered) [test_round3_effects_reorder_coalesce; pillar3/effects.py]
74. ☑ interprocedural summaries (purity across the call graph) → EXACT memoization — monotone fixpoint (fn pure iff callees proven pure); proves compute_pure that single-fn #68 REJECTS (calls helpers) → memoize EXACT ~76×; caller reaching I/O helper → DECLINE (sound, extends #68) [test_round3_interprocedural_purity; pillar3/interproc.py]
