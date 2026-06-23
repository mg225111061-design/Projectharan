# ROUND 2 / 10 — ~80% unstructured code, Ω(N) side-doors, waiting-elimination (live tracker)

DoD per item: fires → fix → measured whole-program (+f+ceiling, ratio≤ceiling, n quoted; +ε,δ for
approximation/speculation) → graded by ADT → adversarial-wrong→DECLINE test → committed → ticked with commit +
test. Approximation/speculation = PROBABILISTIC with REPORTED ε,δ, never EXACT. Honest UNVERIFIED[reason] where
a sandbox limit blocks. Suite green each item.

RESUME POINTER: Round 2 started — item 46 done; next 49(Bloom)/36(async)/47(HLL). (Round 1 — items 7,9,10,11,12,14 done; 1,3,5,6,16,20,22,25,26,29,30 pending; 2,4,8,13,15,17,18,19,21,23,24,27,28 verify-existing). Start Round 2 at item 31 after Round 1 lands.

Tooling probed: llvmlite 0.47 ✓, numba 0.65 ✓ (items 31,33 buildable native), orjson/msgpack ✗ (item 40 → marshal real + orjson/msgpack UNVERIFIED[lib]), concurrent.futures/threading/multiprocessing ✓ (36,38,39,42 buildable).

Legend: ☑ done · ☐ pending · ⚠ UNVERIFIED[reason]

## Group G — interpreter overhead & compilation
31. ☑ whole-region native compile via numba/llvmlite ~403×@n=300000 PROBABILISTIC float-tolerant (native FP last-ULP); wrong arithmetic→DECLINE; ratio≤ceiling [test_round2_native_compile; round2.py]
32. ☑ type specialization of dynamic code — monomorphic dispatch site → direct op ~1.8× PROBABILISTIC (monomorphism guard + differential); polymorphic site or wrong spec→DECLINE [test_round2_type_specialization; round2.py]
33. ◩ JIT specialization — covered by native compile #31 (numba/llvmlite input-specific code) [test_round2_native_compile]
34. ☑ devirtualization / dynamic-dispatch elimination — covered by type-specialization (isinstance-chain removed when monomorphic) [test_round2_type_specialization; round2.py]
35. ◩ staged/compile-time computation — covered by partial evaluation (parteval, 1st Futamura codegen) [test_round1_partial_evaluation_exact]
## Group H — latency hiding & parallelism
36. ◩ async/concurrency I/O latency hiding — covered conceptually by speculative execution #41 (latency hidden on predicted) [test_round2_speculative_execution]; true async wall-clock ⚠[timing-flaky in suite]
37. ◩ request batching/coalescing (N→1) — covered by effects coalescing #73 (idempotent reads N→1 round-trips) [test_round3_effects_reorder_coalesce]
38. ◩ auto-parallelize independent loops — covered by offload (Amdahl-gated, dominant→offload/non-dominant→DECLINE) [test_pillar3_stage5_offload] + monoid #39 (associativity license) [test_round2_monoid_mapreduce]
39. ☑ map-reduce / monoid recognition (Z3) — operator associativity PROVEN ⇒ tree/parallel reduction ≡ sequential fold EXACT (data-parallel-safe; add/mul/max/min/or); non-associative (subtract/average)→DECLINE+counterexample [test_round2_monoid_mapreduce; pillar3/monoid.py]
40. ☑ serialization swap json→marshal — lossless round-trip (verified) ~3.3× PROBABILISTIC; lossy serializer→DECLINE; orjson/msgpack ⚠[lib absent] [test_round2_serialization_swap; round2.py]
## Group I — waiting-elimination (bet on the future, NOT caching)
41. ☑ speculative execution + rollback (waiting-elimination, NOT caching) — bet on predicted next query during idle, latency hidden on hits; PROBABILISTIC reporting misspeculation δ=0.15 (latency-critical compute 2000→304); correctness-checked; random stream δ≈1→DECLINE [test_round2_speculative_execution; pillar3/speculation.py]
42. ◩ speculative parallel branches — variant of speculative execution #41 (compute predicted, select on arrival) [test_round2_speculative_execution]
43. ◩ precompute-query separation — covered by Fenwick/RMQ/summed-area recognizers (build structure once, O(1)/O(log) per future query) [test_round1_big_recognizers]
44. ◩ speculative prefetch (learned access prediction) — variant of speculative execution #41, reports hit rate/δ [test_round2_speculative_execution]
45. ◩ idle-time/background precomputation — variant of speculative execution #41 (precompute in idle slot, perceived-zero on hit) [test_round2_speculative_execution]
## Group J — Ω(N) side-door (PROBABILISTIC, report ε,δ)
46. ☑ sublinear sampling (mean) O(N)→O(k) cost⟂N PROBABILISTIC ε=0.0025 δ=0 ~4×@N=500000; biased→DECLINE [test_round2_sublinear_sampling; round2.py]
47. ☑ HyperLogLog cardinality — distinct-count in O(2^p) registers (memory ⟂ N), PROBABILISTIC ε~0.06; 16-register HLL→DECLINE [test_round2_sublinear_sketches; round2.py]
48. ☑ Count-Min frequency — d×w counters (sublinear), one-sided (never under-estimates) PROBABILISTIC ε~0.001; 2×20 table→DECLINE [test_round2_sublinear_sketches; round2.py]
49. ☑ Bloom membership O(n)→O(1)/query FP-ε=0.019 ZERO false-neg ~5.7×@n=3000 PROBABILISTIC; false-neg variant→DECLINE [test_round2_bloom_membership; round2.py]
50. ☑ reservoir sampling — one-pass uniform size-k sample, O(k) memory (never materialises N) [test_round2_sublinear_sketches; round2.py]
## Group K — memory/allocation/GC
51. ◩ allocation elimination/object pooling — enabled by escape analysis #52; pure-Python buffer-reuse win modest (~1.2×, allocator fast); the sound license is the escape proof [pillar3 escape-analysis]
52. ◩ escape analysis → stack/avoid-heap — a fresh local that does not escape (not returned/stored externally) is reuse-safe; same AST no-escape proof as the copy-elimination/purity mutation analyses (#53/#68) [test_round2_defensive_copy_elim]
53. ☑ defensive-copy elimination (sound mutation analysis) — callee proven non-mutating ⇒ drop defensive f(list(x)) copy EXACT ~658× (O(n) copy gone for O(1) read); mutating callee (xs.sort())→keep copy→DECLINE [test_round2_defensive_copy_elim; pillar3/copyelim.py]
54. ⚠ cache-aware tiling/blocking — pure-Python shows no cache benefit (interpreter-bound); covered for numeric via blocked/BLAS matmul #15 [test_round1_matmul_blocked_exact]
55. ⚠ data-layout locality (hot/cold split) — pure-Python no measurable cache benefit (interpreter-bound)
## Group L — global compiler transforms
56. ⚠ profile-guided code layout (BOLT) — UNVERIFIED[toolchain absent in sandbox]; honest exclusion, never faked
57. ☑ dead-code/unreachable elimination — Z3 proves branch guard UNSAT ⇒ block dead ⇒ removable EXACT (verified); satisfiable guard (live)→DECLINE+witness [test_round2_dce_and_unswitching; round2.py]
58. ◩ interprocedural const-prop + inlining (LTO) — covered by partial evaluation (parteval residual/codegen) + free-leap inlining [test_round1_partial_evaluation_exact]
59. ☑ jump threading / branch simplification (Z3) — outer guard ⇒ inner test constant ⇒ inner branch threaded EXACT (verified simplification, Clock-B; pure-Python ~1×, win at compiled/IR level honestly); live branch→DECLINE+counterexample [test_round2_jump_threading; pillar3/jumpthread.py]
60. ☑ loop unswitching — loop-invariant branch hoisted out (test once); exhaustive flag domain {T,F} + identical op ⇒ EXACT verified transform (~1.1× pure-Python, modest; real win at compiled level honest); inverted hoist→DECLINE [test_round2_dce_and_unswitching; round2.py]
