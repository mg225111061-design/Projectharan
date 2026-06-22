# ROUND 1 / 10 — the 30 most powerful capabilities (live tracker)

DoD per item: detector/recognizer fires → fix produced → measured whole-program (+f+ceiling, ratio≤ceiling, n
quoted) → graded by ADT → adversarial-wrong→DECLINE test → committed → ticked with commit + test. Honest
UNVERIFIED[reason] where a sandbox limit blocks. Suite green each item.

RESUME POINTER: building Group A/B new recognizers in pillar3/round1.py. Next: item-by-item below.

Legend: ☑ done(new, tested) · ◩ verify-existing (already built+tested elsewhere, cite test) · ☐ pending · ⚠ UNVERIFIED[reason]

## Group A — ceiling-breakers
1. ☑ verified lifting generalized to arbitrary affine loops — family s+=A·a[i]+B·i+C, identity Z3-proven ONCE over symbolic A,B,C+array (len≤6) licenses all instances; index-only(A=0) O(n)→O(1) ~560× ceiling-breaker, array-affine ~9×, EXACT; triangular off-by-one→Z3-refuted DECLINE [test_round1_affine_lift_generalized_exact; pillar3/affine.py]
2. ☑ egg equality saturation wired into Pillar-3 — wasteful expr (27 nodes) saturated→cheapest equiv (x·K, 3 nodes) Z3-certified (∀vars term≡rewrite), compiled+measured ~10×@n=40000, EXACT δ=None; non-Z3-equivalent rewrite (x·999)→DECLINE; bounded iters (correctness independent of saturation depth) [test_round1_egraph_simplify_exact; pillar3/egraph_simplify.py]
3. ☐ llvmlite/numba native compile of hot numeric region (llvmlite 0.47 + numba 0.65 present → buildable)
4. ☑ STOKE-style stochastic superopt wired into Pillar-3 — superopt search (12→4 cost, 6x+8), Schwartz–Zippel-verified (randomized ⇒ PROBABILISTIC δ≤1e-300, NEVER EXACT), measured ~2.4×; build-time search→O(1) runtime cache hit; wrong rewrite (7x) S-Z-refuted→DECLINE [test_round1_stoke_superopt_probabilistic; pillar3/stoke.py]
5. ☑ partial evaluation / specialization on fixed inputs — EXACT (Z3 residual≡generic): 1st Futamura projection (interp specialized on a fixed program → straight-line, ~1.7×) + sparse linear-map (dot w/ fixed weights drops zeros+loop, ~2.2×); wrong residual (mul→add / dropped live term) differential-caught AND Z3-refuted→DECLINE [test_round1_partial_evaluation_exact; pillar3/parteval.py]
6. ☑ THE FREE LEAP: wire Pillar-1 cfinite EXACT kernel into Pillar-3 recognition — recurrence hotspot routed to companion-matrix closed form, graded EXACT (was PROBABILISTIC item 7), O(n)→O(log n) ~30×@n=24000 fib (Pell/Tribonacci/Lucas too); recognition gate (companion≡loop probe) → mis-recognized recurrence DECLINEs [test_round1_freeleap_cfinite_exact; pillar3/freeleap.py]
## Group B — big-multiplier recognizers
7. ☑ matrix-power linear recurrence O(n)→O(log n) (fast-doubling) ~40×@n=24000 PROBABILISTIC; wrong→DECLINE [test_round1_big_recognizers; round1.py]
8. ☑ naive convolution → NTT O(n²)→O(n log n) wired into Pillar-3 — EXACT under PROVEN no-wraparound bound (|c[k]|<P/2 ⇒ exact integers), ~119×@n=2000 (rust NTT; pure-Python fallback ~10×), bit-exact vs naive δ=None; bound-exceeded→DECLINE (no wrap), corrupted NTT→DECLINE [test_round1_convolution_ntt_exact; pillar3/convolution.py]
9. ☑ O(2ⁿ)→memoized DP — fib ~10000×@n=29 [test_phaseA] + coin-change ~15700×@amount=26 [test_round1_big_recognizers]
10. ☑ nested-loop join → hash join ~28× [test_phaseA hash_join]
11. ☑ naive substring search → KMP O(n·m)→O(n+m) ~32×@n=24000 PROBABILISTIC; wrong→DECLINE [test_round1_big_recognizers]
12. ☑ Fenwick/BIT repeated point-update + range-query O((U+Q)·n)→O((U+Q)·log n) ~9×@n=2000 PROBABILISTIC; wrong→DECLINE [test_round1_big_recognizers; round1.py]
13. ☑ sparse-table RMQ O(q·n)→O(n log n build + O(1)/query) ~10×@n=4000 PROBABILISTIC; inclusive-split off-by-one wrong→DECLINE [test_round1_big_recognizers; round1.py]
14. ☑ union-find + path compression near-O(1) connectivity ~121×@n=600 PROBABILISTIC; wrong→DECLINE [test_round1_big_recognizers]
15. ☑ naive O(n³) matmul → blocked/BLAS (numpy int64) ~65×@n=160 EXACT under PROVEN no-overflow bound (|C_ij|<2^63 ⇒ exact integers), bit-exact vs naive δ=None; bound-exceeded→DECLINE (no wrap), wrong-axis→DECLINE; UNVERIFIED[no numpy] [test_round1_matmul_blocked_exact; pillar3/matmul.py]
## Group C — redundancy elimination
16. ☐ incremental / self-adjusting computation (recompute affected sub-DAG only)
17. ◩ interprocedural memoization of pure functions — superopt fib memo [test_phaseS_extend_depth]
18. ◩ interprocedural CSE — equiv_transforms CSE [test_phaseV]
19. ◩ loop-invariant code motion (deep) — equiv_transforms hoist [test_phaseV]
20. ☐ dead-code + reachability elimination
## Group D — compiler transforms
21. ◩ polyhedral optimization of affine loop nests — polyhedral_opt.py [exists]; wire/verify
22. ☐ bounds-check elimination (Z3 in-range proof → EXACT)
23. ◩ strength reduction (deep) — equiv_transforms [test_phaseV]
24. ◩ algebraic simplification + constant folding (e-graph) — fold_egraph [test_foldext3_stage2]
25. ☐ function specialization + inlining of hot small calls
## Group E — data structure & representation
26. ☐ AoS → SoA layout transform
27. ◩ list-as-set/dict membership O(n)→O(1) — detectors2 (membership_to_set, count_in_loop) [tests]
28. ◩ compressed/succinct structure with direct query (SLP) — [test_v40_phase5_generators]
## Group F — accuracy + verification speed
29. ☐ promote PROBABILISTIC→EXACT where provable; widen Z3; report EXACT-share rise
30. ☐ verification speed (Clock B): proof caching + cheap-first tiering; measure throughput

Build-new this round: 1,3,5,6,7,11,12,14,16,20,22,25,26,29,30 (+ DP/LCS for 9, P3 wires for 2,8,15,21).
Verify-existing + cite: 2,4,8,13,15,17,18,19,21,23,24,27,28.
