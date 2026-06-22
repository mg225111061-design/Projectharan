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
61. ☐ bounded model checking (unroll k + Z3 equivalence on the bounded domain)
62. ◩ symbolic execution oracle — symbolic_oracle.py [exists]; wire a P3 equivalence gate
63. ☐ SMT portfolio (parallel tactics, first-to-close) — Clock-B verification speed
64. ☐ CEGAR (counterexample-guided abstraction refinement) for loop invariants
65. ☐ k-induction (prove a loop invariant for unbounded n)
66. ◩ refinement (output refines input wherever defined) — translation_validate [exists]
67. ☑ translation validation under REAL machine semantics (bitvector/overflow-aware) — 5 sound peepholes EXACT (bv-proven), 3 overflow-unsafe REFUTED→DECLINE+cex; (x+1)>x PROVEN over ℤ but REFUTED over bv32 @ INT_MAX (catches the miscompile idealized reasoning misses) [test_round3_bitvector_translation_validation; pillar3/bv_validate.py]
## Group Q — sound static analyses (a wrong "safe" is a correctness bug)
68. ☑ purity / determinism analysis → EXACT memoization — conservative AST proof (no impure calls/global·arg mutation/yield); pure→memoize EXACT ~74×@repeated args; nondeterministic (random) AND global-mutating fns both classified impure→DECLINE (soundness regression-guarded — caught+fixed a global-mutation false-pure) [test_round3_purity_memoization_exact; pillar3/purity.py]
69. ☐ alias / non-aliasing proof → safe reordering/vectorization
70. ☐ range / interval analysis (prove no overflow / in-range → EXACT fast path)
71. ☑ termination via ranking functions (Z3, sound) — r bounded-below ∧ strictly-decreasing under guard ⇒ EXACT termination certificate (4 loops proven); increasing / steps-over-zero loops → DECLINE+witness (never assume termination) [test_round3_termination_ranking; pillar3/termination.py]
72. ☑ complexity certificate — measure naive&fast at several n, fit log-log growth exponent, certify fast is a STRICTLY LOWER class (Δexp≥margin, R²-gated); O(n²)→O(n) certified (exp 2.05→0.96), PROBABILISTIC (empirical, δ=1−R²); same-class O(n)/O(n) pair→DECLINE (no false asymptotic claim) [test_round3_complexity_certificate; pillar3/complexity_cert.py]

DETERMINISTIC SUITE RUN: `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 test_build.py` ⇒ 156/156. Thread caps remove numpy/numba/BLAS worker-pool inter-test CONTENTION (the load-induced flake source: offload, partial_eval, phaseM2, foldext2, pillar3_stage2) while PRESERVING the SIMD/JIT wins (vectorization/compilation, not parallelism). Each flake also passes in isolation uncapped.
73. ☐ effects analysis (I/O / mutation) → safe reordering & batching
74. ☐ interprocedural summaries (purity/range/effects across calls)
