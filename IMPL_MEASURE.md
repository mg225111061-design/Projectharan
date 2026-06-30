# IMPL_MEASURE — §BG measured crossovers (the "past-native" claim, honest)

★ Rule: every speed claim carries a **measured wall-clock crossover** (never the exponent alone — the galactic
trap). All numbers below are reproduced by `python3` on this build's CPU; absolute ms vary by machine, the *ratio*
and the *O()* are the point. "past-native" = we **removed the computation** (fold), not magic — native still loops
O(n); we jump to a closed form.

## Workstream B — fold / execution-removal (past-native), measured
| gem | shape | naive (native-style loop) | fold | measured crossover | grade |
|---|---|---|---|---|---|
| **1 Faulhaber** Σk, n=5,000,000 | O(n) → O(1) | 53.3 ms | 0.0038 ms (n(n+1)/2) | **≈14,000×** | EXACT-cert |
| **2 Fibonacci**, n=200,000 | O(n) → O(log n) | 348 ms | 32.2 ms (companion matrix-power) | **≈11×** | EXACT-cert |
| **4 Freivalds** A·B=C, N=700 | O(N³) → O(kN²) verify | 3.8 ms (numpy BLAS matmul) | 2.07 ms (k=64 verify) | ≈1.8× *vs BLAS* | PROBABILISTIC |

★ **Honest reading of each:**
- **gem-1 (≈14,000×)** is the cleanest past-native: the loop is *gone*, replaced by one arithmetic expression. A
  native (C/Rust) loop would still pay O(n); we pay O(1). This is where WASM's 1.5–2× penalty is irrelevant — there
  is no loop left to be slow.
- **gem-2 (≈11×)** is O(log n) matrix-power; the ratio is *bignum-bounded* at large n (the Fibonacci values are
  themselves huge integers, so neither side is free) — still a genuine complexity win, growing with n.
- **gem-4 (1.8× vs BLAS)** is the honest one to NOT oversell: against numpy's already-optimized BLAS matmul the
  verify is only ~1.8× cheaper. Freivalds' real value is verifying an **expensive or untrusted** matmul — a naive
  O(N³) implementation, a GPU/browser-offloaded result, or a galactic-algorithm output — in O(kN²). The gem is the
  *proposer-verifier* shape (compute however you like, verify cheaply), not a win over BLAS.

★ **false-EXACT 0 (gem-4):** k=64 ⇒ δ = 2⁻⁶⁴ ≈ **5.4e-20**, far below any tolerance; a wrong C is **DECLINE**d
(one-sided: a correct C *always* passes). Adversarial battery (50k trials, N=6, k=20): false_reject=0 (guaranteed,
one-sided), false_accept=0 (consistent with ≤ trials·2⁻ᵏ). It is graded **PROBABILISTIC, never EXACT** — the grade
ADT forbids EXACT+δ; this is correct, not a limitation.

★ **rank 1/2/3/5/6 already built** (`loop_decision`, `loop_recurrence`/`cfinite`, `foldaxes/bypass`+`haran_broth`,
`pillar3/equiv`+`egraph`, `gapfold/divide_conquer`+`rust_accel`) ⇒ re-build DECLINED (see IMPL_INDEX). Net-new this
build = the **measured demonstration** above + the k≥60 false-EXACT-0 Freivalds lane (reuse, not a new mechanism).

## Workstream A — multi-language WASM (near-native), NOT measured here (honest)
★ The WASM CDNs (Pyodide, ruby.wasm, …) and the COOP/COEP headers are **blocked in this sandbox**, so per-language
load/exec times and the IndexedDB cache hit-rate **cannot be measured here** — they are author-validated on Render.
What is asserted structurally (and in `test_bg_pastnative_and_runtimes`): the registry exists with honest tier
labels + approx download sizes, the IndexedDB cache module exists, and both are servable via `/static/runtimes/`.

Expected on Render (to be filled by the author from real runs):
- Pyodide first load ~6.5 MB (seconds) → IndexedDB cache hit → **near-instant 2nd load** (ACCEL-3, the biggest felt win).
- SIMD (`-msimd128`) on numeric hot-loops: ~4–8× *within WASM* (ACCEL-1) — near-native, **not** past-native.
- ★ ACCEL-5 fold-before-run: a foldable loop (Σk, Fibonacci) is recognized by `/api/check` and the **execution is
  skipped** — gem-1/2 above show why that beats running it in any runtime (the loop is removed, not sped up).

## Invariants
- WASM ceiling stated (near-native 1.5–2×); fold is past-native only on structured code; unstructured ⇒ near-native
  WASM + HONEST_DEFER.
- no galactic switch (CW/HvdH unused); approximations carry bounds; false-EXACT 0 (Freivalds k≥60, graded PROBABILISTIC).
- "quantum / relativistic / ultra-speed" absent (Landauer / Margolus–Levitin bound everything).
- zero-dep (language runtimes are browser-side); `test_build` 276 / `test_catalog` +1; os-import-0; 14 mechanisms.
