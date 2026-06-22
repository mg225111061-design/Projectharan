# ROUND 2 / 10 — ~80% unstructured code, Ω(N) side-doors, waiting-elimination (live tracker)

DoD per item: fires → fix → measured whole-program (+f+ceiling, ratio≤ceiling, n quoted; +ε,δ for
approximation/speculation) → graded by ADT → adversarial-wrong→DECLINE test → committed → ticked with commit +
test. Approximation/speculation = PROBABILISTIC with REPORTED ε,δ, never EXACT. Honest UNVERIFIED[reason] where
a sandbox limit blocks. Suite green each item.

RESUME POINTER: Round 2 started — item 46 done; next 49(Bloom)/36(async)/47(HLL). (Round 1 — items 7,9,10,11,12,14 done; 1,3,5,6,16,20,22,25,26,29,30 pending; 2,4,8,13,15,17,18,19,21,23,24,27,28 verify-existing). Start Round 2 at item 31 after Round 1 lands.

Tooling probed: llvmlite 0.47 ✓, numba 0.65 ✓ (items 31,33 buildable native), orjson/msgpack ✗ (item 40 → marshal real + orjson/msgpack UNVERIFIED[lib]), concurrent.futures/threading/multiprocessing ✓ (36,38,39,42 buildable).

Legend: ☑ done · ☐ pending · ⚠ UNVERIFIED[reason]

## Group G — interpreter overhead & compilation
31. ☐ whole-region native compile via llvmlite/numba (numba ✓ → buildable; larger regions)
32. ☐ type specialization of dynamic code
33. ☐ JIT specialization — input-specific code (numba/closure ✓)
34. ☐ devirtualization / dynamic-dispatch elimination
35. ☐ staged/compile-time computation (partial-eval deepen)
## Group H — latency hiding & parallelism
36. ☐ async/concurrency to hide I/O latency (simulated I/O; concurrent.futures)
37. ☐ request batching/coalescing (N calls→1)
38. ☐ auto-parallelize independent loops (ProcessPool; Amdahl-gated)
39. ☐ map-reduce / data-parallel recognition
40. ☐ serialization swap (marshal real; orjson/msgpack ⚠[lib])
## Group I — waiting-elimination (bet on the future, NOT caching)
41. ☐ speculative execution + rollback (report misspeculation δ)
42. ☐ speculative parallel branches (compute both, select)
43. ☐ precompute-query separation (build structure for not-yet-asked queries)
44. ☐ speculative prefetch via learned access prediction (report hit rate)
45. ☐ idle-time / background precomputation (perceived vs actual)
## Group J — Ω(N) side-door (PROBABILISTIC, report ε,δ)
46. ☑ sublinear sampling (mean) O(N)→O(k) cost⟂N PROBABILISTIC ε=0.0025 δ=0 ~4×@N=500000; biased→DECLINE [test_round2_sublinear_sampling; round2.py]
47. ☐ cardinality sketch (HyperLogLog; ε)
48. ☐ frequency sketch (Count-Min; ε)
49. ☐ membership filter (Bloom; no false negatives; ε)
50. ☐ streaming/one-pass bounded memory (reservoir sampling)
## Group K — memory/allocation/GC
51. ☐ allocation elimination / object pooling
52. ☐ escape analysis → stack/avoid-heap
53. ☐ defensive-copy elimination
54. ☐ cache-aware tiling/blocking
55. ☐ data-layout locality (hot/cold field split)
## Group L — global compiler transforms
56. ☐ profile-guided code layout (BOLT-style) ⚠ likely [toolchain]
57. ☐ global dead-code/unreachable elimination (interprocedural)
58. ☐ interprocedural constant propagation + inlining (LTO-style)
59. ☐ jump threading / branch simplification (Z3 where tractable)
60. ☐ loop unswitching / unrolling (profile-gated)
