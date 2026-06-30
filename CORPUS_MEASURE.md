# CORPUS_MEASURE — §BB B/C fold-recovery, measurement-first (the directive's own honesty)

The §BB directive is **explicit** that recovery is expected to be **≈ 0** and the value is **coverage completion**
("fold it if the structure *comes*"), not a fold-rate gain. This file records the measurement honestly — and a
recovery of 0 is **reported as a fact, not a failure**.

## §0 confirmed: precision 1.0 is already structural (single disposer)
`recall/core.fold_via_ai(fn, disguise, probe)` is the **one** place a candidate is disposed — z3 ∀-proof +
**held-out = 200**. The strip/split modules only NORMALIZE. So every recovery branch that routes through
`recall/core` inherits **false-EXACT-impossible** for free — no per-method anti-false-EXACT re-proof, no new
disposer. Verified end-to-end this round: a clean polynomial atom folds EXACT; a pseudo-random (hash) atom does
**not** fold (test `test_bb_r1_slice_split`).

## Prior measured baseline (established, not re-run here — honest)
The previous directive measured the analogous aggressive probes against the §AK 2000-code corpus and got **0
recovery**: Krylov probe 128 (order-16–31 C-finite) → 0; `extract` (structural quantity) → 0; `near_miss` retry
→ 0. That measured-0 is the basis for the ≈0 expectation below. ★ This round did **not** re-run a fresh full §AK
sweep (cost); the per-method expectations are the directive's own, cross-checked against that prior measured-0 and
the corpus's nature (synthetic numeric/data loops, not disguised multi-accumulator code).

## Per-method corpus expectation (R-1…R-5)
| # | Method | §AK structure sought | Expectation | Status this round |
|---|---|---|---|---|
| **R-1** | backward-slice accumulator split | a loop body with ≥2 accumulators sharing a per-iteration temp (`t=g(i); acc1+=t; acc2+=t*(-1)**i`) | ★ **non-zero possibility** (rare but plausible) | **BUILT** — `atomize.backward_slice_split`; verified on a synthetic interleaved case (split ≡ original on held-out n=200); routes to the existing gate. Partial fold honest (each atom that DECLINEs is a residual). |
| R-2 | strip-pipeline fixpoint | ≥2-layer nested disguise (closure∘recursion∘control-flatten) | ≈0 (≥2-layer co-occurrence is very rare) | not built (recognizer-only deferred; would reuse existing strip/* + recall/core) |
| R-3 | adaptive probe delta | order 16–31 C-finite (beyond near_miss-64) | ≈0 (prior Krylov-128 → 0) | not built (prior measure says absent) |
| R-4 | polyhedral unrolled lin-alg | manual nested matrix-vector loops (not numpy `@`) | ≈0 (general Python uses numpy; manual MAC loops rare) | not built (prior quantum/matrix probe → 0) |
| R-5 | structural-quantity extract | index-determined trip/branch/IO counts over a payload loop | ≈0 (prior `extract` → 0) | not built (prior measure says absent) |

## What was built and why (coverage, not fold-rate)
**R-1 only.** It is the single method the directive rates as having a non-zero corpus possibility, and it is the
cleanest sound extension of the existing `atomize` machinery: the split is exact *by construction* (the shared
temp takes only the index, so it structurally cannot observe an accumulator — Weiser slicing), re-verified
combine ≡ original on held-out, and disposal is the existing `recall/core` gate. **No fold-rate is claimed** — the
recognizer exists so that *if* an interleaved-accumulator loop arrives, it folds; the synthetic test proves the
machinery, not a corpus yield.

## Invariants held (§5 gates)
- **A (structureless 362) / B-3 (principle-impossible)** untouched — no recovery branch targets them.
- **hash/random still DECLINE** — verified end-to-end (the gate, before any recovery, rejects pseudo-random).
- **partial-fold residual honest** — R-1 reports per-atom fold/DECLINE; no Amdahl/ratio inflation.
- zero-dep (stdlib only); `test_build` 274/0; `test_catalog` + `test_bb_r1_slice_split`; false-EXACT 0 / 660 EXACT
  invariant (R-1 lives in `recall/compose`, not imported by the corpus-count engine — additive by construction).
- R-2…R-5 honestly **deferred** (prior measured-0 ⇒ recognizer-only would be coverage with no measurable yield;
  documented rather than silently built).
