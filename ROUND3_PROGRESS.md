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
71. ☐ termination (ranking function) → safe loop transforms
72. ☐ complexity certificate (prove the asymptotic class actually improved)
73. ☐ effects analysis (I/O / mutation) → safe reordering & batching
74. ☐ interprocedural summaries (purity/range/effects across calls)
