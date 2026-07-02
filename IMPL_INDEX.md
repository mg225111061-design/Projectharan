# IMPL_INDEX — §BG implementation phase, pre-build reuse index (§2)

★ The honest frame (research-proven): "beating native" has **exactly 4 physically-honest routes** — (1) *remove*
computation (fold/precompute/memoize), (2) *lower* complexity (better big-O), (3) cheaply-verifiable *approximation*
(Freivalds), (4) swap the hardware substrate (analog/optical — **needs-hw, out of scope**). "Same computation, same
hardware, free speedup" is a perpetual-motion mirage that Landauer (k_B·T·ln2 / bit) and Margolus–Levitin
(~6×10³³ ops/s/J) forbid. So:
- **WASM SIMD/threads/caching → *near-native*** (real, but a structural 1.5–2× ceiling).
- ★ **fold = not running → *past-native*** (native still loops O(n); we jump to a closed form O(1), so we beat native
  *regardless* of the WASM penalty — we removed the computation). True only on STRUCTURED code; unstructured ⇒
  near-native WASM + HONEST_DEFER.
- ★ "quantum / relativistic / ultra-speed" are BANNED (a classical CPU can't be quantum; a quantum sim is 2ⁿ
  *slower*; Landauer/Margolus–Levitin cap everything).

## Already built — gem ledger rank 1–6 (reuse; re-build 0)
| gem | route | already-built location | grade |
|---|---|---|---|
| **1 closed-form sum** (Faulhaber/Gosper/Zeilberger/Petkovšek) | remove (O(1)⟵O(n)) | `loop_decision.decide_sum_collapse`, `structure_recognizer`, `mathmode/telescoping` (Zeilberger cert) | EXACT-cert |
| **2 C-finite → matrix power** | remove (O(log n)⟵O(n)) | `loop_recurrence.decide_recurrence_collapse`, `cfinite.py` (companion `_matpow`) | EXACT-cert |
| **3 lookup / precompute / perfect-hash** | remove (O(1)) | `foldaxes/bypass.py` (§AB total-precompute), `haran_broth.py` (3,772-entry O(1)) | EXACT |
| **4 Freivalds / Schwartz–Zippel** | verify cheaply (O(kN²)⟵matmul) | `freivalds.py::verify_matmul` (**default k=24** — see net-new) | PROBABILISTIC δ≤2⁻ᵏ (GVFA Gaussian → δ=0) |
| **5 e-graph / superopt** | rewrite (z3-gated) | `pillar3/equiv.py`, `egraph.py`, `pillar3/superopt.py` | EXACT-cert |
| **6 FFT/NTT/Karatsuba/Strassen** | lower complexity | `gapfold/divide_conquer.py`, `rust_accel.py` (NTT), `kernels_structured.py` | EXACT (measured crossover only) |
| disposer (false-EXACT 0) | single gate | `recall/core.fold_via_ai` (z3 ∀-proof + held-out=200) | — |
| §BD check | language-agnostic patterns + fold O(1) | `checker/*` | EXACT/CHECKED/FLAGGED/DEFER |
| §BE isolation | browser exec, net-sever / key-0 / terminate / sanitize | `static/runner.worker.js`, `static/sandbox_guard.js` | — |
| §BF diagnosis | DECLINE *why* + hint | `diagnostics.py` | — |

★ The research **externally validates** this architecture ("the only physically-honest past-native is exactly what
you already do"). So net-new is *recognition / dispatch / productization*, NOT a new mechanism or disposer.

## net-new this build (§3 only)
- **Workstream C (productize, FIRST):** per-snippet grade badge (EXACT/CHECKED/FLAGGED/DEFER) + write→check→RUN→fix
  flow + ★DEFER-only highlight in `mrjeffrey.html` — reuses §BD grade + §BF why + §BE run. (The Run button + server
  fold-check already exist from §BE; this makes the grade per-snippet and folds away the EXACT/CHECKED parts so the
  user only inspects DEFER.)
- **Workstream B (past-native):** rank 1/2/3/5/6 already built ⇒ **re-build DECLINED** (documented, not duplicated).
  Net-new = **FOLD-4 Freivalds *past-native lane* at k≥60** (δ≤2⁻⁶⁰ ≈ 8.7e-19, false-EXACT 0; still PROBABILISTIC —
  never EXACT, the ADT forbids EXACT+δ) + a **measured crossover** (`IMPL_MEASURE.md`). A thin recognition lane over
  `freivalds.verify_matmul`, not a new mechanism.
- **Workstream A (near-native):** `static/runtimes/registry.js` (language→WASM runtime map, **honest labels** +
  download sizes) + `static/runtimes/wasm_cache.js` (IndexedDB compiled-Module cache, 2nd-load instant) — genuinely
  net-new browser JS; both run §BE-isolated. ACCEL-5 = fold-before-run (reuse `/api/check`).

## Honesty (§4)
- past-native = removing computation (fold), not magic; WASM has a 1.5–2× ceiling (near-native), stated.
- ★ galactic trap: Coppersmith–Winograd (ω≈2.371) / Harvey–van der Hoeven (O(n log n)) have astronomical constants —
  **never switch on the exponent alone; only on a measured wall-clock crossover.** We do NOT use CW/HvdH.
- approximations (randomized SVD / sketch / sparse-FFT / Freivalds) always state an error/probability bound.
- false-EXACT 0: every fold rides `recall/core`; Freivalds uses k≥60 and is graded PROBABILISTIC, never EXACT.
- ★ Sandbox blocks the WASM CDN + COOP/COEP headers ⇒ the live multi-language browser path is **author-validated on
  Render**; code + push only here, no false "verified" claim. zero-dep (language runtimes are browser-side).
