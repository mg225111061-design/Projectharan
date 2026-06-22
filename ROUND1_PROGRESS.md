# ROUND 1 / 10 — the 30 most powerful capabilities (live tracker)

DoD per item: detector/recognizer fires → fix produced → measured whole-program (+f+ceiling, ratio≤ceiling, n
quoted) → graded by ADT → adversarial-wrong→DECLINE test → committed → ticked with commit + test. Honest
UNVERIFIED[reason] where a sandbox limit blocks. Suite green each item.

RESUME POINTER: building Group A/B new recognizers in pillar3/round1.py. Next: item-by-item below.

Legend: ☑ done(new, tested) · ◩ verify-existing (already built+tested elsewhere, cite test) · ☐ pending · ⚠ UNVERIFIED[reason]

## Group A — ceiling-breakers
1. ☐ verified lifting generalized to arbitrary affine loops (widen accepted shape; covers a no-detector hotspot)
2. ◩ egg equality saturation in Pillar 3 — fold_egraph.py + superopt.py [test_foldext3_stage2_superopt]; wire a P3 recognizer
3. ☐ llvmlite/numba native compile of hot numeric region (llvmlite 0.47 + numba 0.65 present → buildable)
4. ◩ STOKE-style stochastic superopt of small fragments — superopt.py [test_foldext3_stage2]; verify adversarial
5. ☐ partial evaluation / specialization on fixed inputs
6. ☐ THE FREE LEAP: wire Pillar-1 fold kernels (cfinite/fold_dispatcher/sparse_fft) into Pillar-3 recognition
## Group B — big-multiplier recognizers
7. ☑ matrix-power linear recurrence O(n)→O(log n) (fast-doubling) ~40×@n=24000 PROBABILISTIC; wrong→DECLINE [test_round1_big_recognizers; round1.py]
8. ◩ naive convolution → FFT/NTT O(n²)→O(n log n) — sparse_fft.py + NTT [test_foldext3_stage3_rust]; wire P3 recognizer
9. ☑ O(2ⁿ)→memoized DP — fib ~10000×@n=29 [test_phaseA] + coin-change ~15700×@amount=26 [test_round1_big_recognizers]
10. ☑ nested-loop join → hash join ~28× [test_phaseA hash_join]
11. ☑ naive substring search → KMP O(n·m)→O(n+m) ~32×@n=24000 PROBABILISTIC; wrong→DECLINE [test_round1_big_recognizers]
12. ☐ segment tree / Fenwick (BIT) repeated range query/update O(n)→O(log n)
13. ◩ sparse-table RMQ O(1)/query — [test_v40_phase4_succinct]
14. ☑ union-find + path compression near-O(1) connectivity ~121×@n=600 PROBABILISTIC; wrong→DECLINE [test_round1_big_recognizers]
15. ◩ blocked/Strassen matmul large n — [test_v40_phase2_structured_matrices]; verify whole-program+wrong
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
