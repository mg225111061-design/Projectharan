# IMPL_FULL_MEASURE — §BH two-axes-one-weapon, measured (honest)

★ Rule (unchanged): every speed claim carries a **measured wall-clock crossover** — never the exponent alone
(the galactic trap). Numbers below are reproduced by `python3` on this build's CPU; absolute ms vary by machine,
the *ratio* and the *O()* are the point. The bridge claim is a **logical equivalence**, demonstrated on concrete
loops (a table, not a wall-clock ratio). "quantum/relativistic/ultra-speed" banned.

## ★ THE SPINE — fold ⟺ prove on the SAME object (the headline finding)
The loop axis-1 *folds* to a closed form is **exactly** the loop axis-2 *proves* terminating. Same companion
matrix `C=[[1+a,−a],[1,0]]`, same per-step expression `Δ(x)=(a−1)x+b` — which is simultaneously the fold's first
difference `x_{k+1}−x_k` and `−1×` the ranking function's decrease. Demonstrated on four concrete loops:

| loop | companion C (eig) | Δ(x0) | axis-1 fold | axis-2 terminates | bridge consistent |
|---|---|---|---|---|---|
| `while x<100: x+=7` | `[[2,−1],[1,0]]` {1,1} | 7 | **EXACT** O(log n) | **EXACT** (z3 ranking) | ✓ (Δ>0 ⟺ proves) |
| `while x<1000: x+=1` | `[[2,−1],[1,0]]` {1,1} | 1 | **EXACT** O(log n) | **EXACT** (z3 ranking) | ✓ (Δ>0 ⟺ proves) |
| `while x<100: x=x` (degenerate) | `[[2,−1],[1,0]]` {1,1} | **0** | **EXACT** → *constant* | **DECLINE** (non-term) | ✓ (Δ=0 ⟺ no rank) |
| `while x<10⁶: x=2x+1` | `[[3,−2],[1,0]]` {2,1} | 2 | **EXACT** O(log n) | **EXACT** (z3, x≥x0 inv.) | ✓ (Δ>0 ⟺ proves) |

★ **Reading it.** The fold makes progress toward the bound (Δ>0) **iff** z3 proves termination with `r=N−x`; the
loop folds to a *constant* (Δ=0) **iff** it cannot terminate. The geometric `x=2x+1` folds unconditionally, while
its termination is start-dependent — z3 proves it under the reachable invariant `x≥x0≥0`, which is *exactly the
closed form's positivity*. One object, both axes: build the fold engine stronger and the verifier gets stronger.
(`bridge.bridge_battery()` → all 12 cases green; reuses `cfinite` + `pillar3.termination` + `z3`, re-build 0.)

## axis-1 — fold = execution removal (past-native), measured
`while x<N: x=2·x+1` homogenizes to the order-2 C-finite recurrence (companion `[[3,−2],[1,0]]`); `cfinite`
evaluates `x_n` by matrix power-by-squaring in O(log n) vs the naïve O(n) loop. **Lossless** (companion ≡ naïve,
exact integers — re-checked over a window before grading EXACT):

| shape | n | naïve O(n) | fold O(log n) | measured crossover | equal? |
|---|---|---|---|---|---|
| `x=2x+1` companion power | 50,000 | 195.5 ms | 6.39 ms | **≈31×** | ✓ exact |
| `x=2x+1` companion power | 200,000 | 2,614.8 ms | 57.39 ms | **≈46×** | ✓ exact |

★ The ratio **grows with n** (O(n)/O(log n)); both sides pay bignum cost (the values are huge integers), so this is
the honest *complexity* win, not an unbounded one. Native (C/Rust) would still loop O(n); we removed the loop.

## STAGE 0 — universal cheap-verifier (Freivalds k=128), measured + HONESTLY framed
Verify `A·B=C` in O(k·n²) by `k` random projections (one-sided: a correct C *always* passes; a wrong C ⇒ DECLINE).
k=128 ⇒ **δ = 2⁻¹²⁸ ≈ 2.9e-39** — astronomically certain, graded **PROBABILISTIC, never EXACT** (the ADT forbids
EXACT+δ; this is correct, not a limitation). GVFA (Gaussian projection) ⇒ **δ=0** (measure-zero false-positive set).

| N | recompute (numpy BLAS) | Freivalds verify (k=128) | ratio vs BLAS |
|---|---|---|---|
| 400 | 0.68 ms | 1.77 ms | **0.38×** (verify is *slower*) |
| 900 | 6.15 ms | 5.73 ms | **1.07×** (≈ break-even) |

★ **The honest read (do NOT oversell).** Against numpy's already-optimized BLAS matmul, k=128 Freivalds is
*slower* at N=400 and only break-even by N=900 (it crosses over and wins at larger N, but slowly). **Freivalds is
not a way to beat BLAS.** Its value is the **proposer-verifier shape**: verify a result you did *not* compute with
BLAS — an O(N³) naïve implementation, a GPU/browser-offloaded matmul (§BE), an untrusted proposer, or a galactic
algorithm's output — in O(k·n²) with δ you choose. The two knobs are *certainty* (k=128 ⇒ 2⁻¹²⁸) and *trust-free
checking*, not raw speed. Schwartz–Zippel extends the same engine to polynomial identity (random point mod a large
prime; disagree ⇒ a witness/refutation, agree ⇒ δ≤(d/p)ᵏ). (`verify_universal.adversarial_battery()` → all green.)

## Honesty (§4) — same constitution
- **two axes = one weapon** (the bridge): build once, both gain. axis-1 ceiling = remove/reduce/verify-cheaply
  (Landauer/Margolus–Levitin) — no "same computation, free speedup." axis-2 ceiling = Rice ⇒ **PROVE / CHECK /
  HONEST_DEFER** (our three grades). "quantum/relativistic/ultra-speed" absent from every §BH artifact (tested).
- **false-EXACT 0:** the fold is EXACT only after companion ≡ naïve re-check; termination is EXACT only when z3
  *proves* it (else DECLINE — never assume termination); Freivalds/GVFA/SZ are graded PROBABILISTIC with a stated
  δ, never EXACT. Every fold + PROVE rides the single disposer (`recall/core`).
- **measurement-premise:** every speed row above is a measured wall-clock crossover; the bridge row is a logical
  equivalence shown on concrete loops; no galactic switch (CW/HvdH stay doc-only); approximations state bounds.
- **zero-dep:** `cfinite` + `pillar3.termination` + `z3` (Spacer built-in) + `numpy` + stdlib. No new mechanism, no
  new disposer — STAGE 0 + the spine are recognition/dispatch on existing engines (see IMPL_FULL_INDEX).
- ★ **Sandbox note:** these CPU numbers are reproducible here; the *live browser* path (Pyodide/WASM CDN, COOP/COEP)
  + per-language numbers remain **author-validated on Render** (the sandbox blocks the CDN + open web) — code +
  push only here, no false "verified" claim for the browser lane.
