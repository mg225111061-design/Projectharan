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

---

# §BC — Axis Y (runtime ACCELERATION), measurement-first. ★ A DIFFERENT AXIS from the fold-recovery above.

★ This is **Axis Y (runtime acceleration), NOT fold (Axis X)** — *never summed* with the fold-rate above or the
Clocks. A (unstructured, the vast majority) has no structure to close ⇒ fold 0 is the right answer; here we make
*execution* faster, gated for **bit-identical** results.

## §0 confirmed: the acceleration machine + correctness gates are ALREADY built (skip — no rebuild)
| concern | already-built | used by §BC |
|---|---|---|
| correctness = bit-identical | `pillar3/equiv.py` (Z3 ∀-input output-identity moat) | the legality oracle |
| purity | `pillar3/purity.py` / `effects.py` (`prove_pure`) | independence input |
| independence | `sep_alias.py`, `verified_parallel._conflicts` (read/write conflict) | ★ the poset edges |
| **IO-1 async overlap** | **`accel/verified_parallel.verified_async_overlap`** | ALREADY BUILT ⇒ skip |
| **IO-2 batching / IO-3 dedup** | **`accel/verified_io.verified_batch` / `verified_dedup`**, `accel/maximal_batch`, `accel/proven_dedup` | ALREADY BUILT ⇒ skip |
| PAR-1 assoc reduction / PAR-2 data-parallel | `verified_parallel.prove_assoc_comm` / `verified_data_parallel` | ALREADY BUILT ⇒ skip |
| RC-2 memoize / native | `accel/verified_io.verified_cache`, `backend_llvm.py` (bit-exact + `[BLOCKED: llvmlite]`) | ALREADY BUILT ⇒ skip |

## Per-round honest expectation (the directive's own map; measured baseline ≈0)
| round | methods | §AK expectation | this round |
|---|---|---|---|
| 1 recompute | LICM / content-dedup / incremental | ≈0 (memoize+CSE already built) | not built (narrow) |
| 2 execute | numpy vectorize / AST clean / monomorphize / native | ≈0 | not built (narrow) |
| 3 parallel | assoc reduction / data-parallel map | ≈0 (A-2/A-1 dominate) | already built (skip) |
| **4 I/O** | async overlap / batch / coalesce / prefetch | the real value in GENERAL code, but **already built**; the **numeric §AK corpus has ~0 network/DB I/O loops** ⇒ measured ≈0 here | already built (skip); honest ≈0 in §AK |
| **5 causal** | **CA-1 poset + Dilworth** | "no new speedup — exact-Amdahl strengthening" | ★ **BUILT** (`accel/causal_poset.py`) |

## What was built (CA-1 only — the genuine net-new, a tighter BOUND not a new speedup)
`accel/causal_poset.py` lifts the pairwise independence the existing gates prove into a **partial order**, then:
- **Dilworth max-antichain (width)** = provably-MAXIMUM concurrency (no schedule runs more at once).
- **Longest chain** = the **EXACT Amdahl critical path** (the serial floor — a theorem, replacing the estimate).
Reuses `verified_parallel._conflicts` (the independence oracle) + `accel.pipeline` proved/rejected; pure stdlib
(Kuhn matching for Dilworth, DAG longest path). ★ A proven dependence is ALWAYS comparable ⇒ kept sequential
(never overlapped). Verified: sequential chain ⇒ width 1 / 1× (no speedup, honest); independent ⇒ width n;
two parallel chains ⇒ width 2 / ceiling 2×. test `test_bc_ca1_causal_poset`.

## Invariants (§5 gates)
- ★ **Axis Y ≠ fold-rate ≠ Clock — never summed.** CA-1 reports concurrency width + Amdahl critical path only.
- ★ **IEEE754 sacred** — CA-1 doesn't reassociate FP; the existing reduction gates (`prove_assoc_comm`) already
  reject non-associative float reductions. CA-1 only reorders *independent* ops (no value change).
- correctness is the existing `pillar3/equiv` bit-identical moat — CA-1 adds no new correctness logic.
- "relativistic acceleration" / light-cone-race / geodesic-scheduler / Lorentz **not present** (banned; CA-1 is
  Dilworth/Lamport-happens-before combinatorics — a bound, not a faster clock).
- zero-dep (stdlib); `test_build` 274/0; `test_catalog` + `test_bc_ca1_causal_poset`; fold-rate / false-EXACT
  invariant untouched (CA-1 in `accel/`, not imported by the corpus-count or fold engines).
