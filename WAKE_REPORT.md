# WAKE_REPORT.md — autonomous research-build engine (§4 living report)

> **STATUS: LIVING DRAFT, updated every cycle.** The 10-hour engine has no completion condition; this report accretes
> the honest findings so it is current whenever the run ends (10h mark / usage reset / compaction). The headline is
> deliberately unglamorous and that is the point: **the engine is at a measured, honest PLATEAU — recall is saturated,
> precision is intact (false-EXACT 0), and the cycles' value is hardening the safety net + honest measurement, NOT
> manufactured fold-rate.** Inventing recall here would breach the HONESTY SPINE; the engine refused to.

## §-1 Capstone invariant snapshot @ HEAD 628f09a (cycle 6) — ALL GREEN
- `test_build`: **273 passed / 0 failed**. `test_catalog`: **223 passed / 0 failed**. corpus (seed 20260628): **EXACT
  660 / PROB 0 / DECLINE 1340 / ERROR 0**. Loop-C red-team: **820 probes / 0 false-EXACT**. Every §0 invariant holds.

## §0 The single number that matters: false-EXACT == 0 (INV-1)
- **0 false-EXACT across every probe this run.** Triple-independent confirmation:
  1. corpus live re-measure (seed 20260628, n=2000): EXACT 660 / PROB 0 / DECLINE 1340 / ERROR 0 — unchanged.
  2. Loop-C red-team: **820** randomized deterministic adversarial probes, 0 false-EXACT.
  3. Loop-A digs: 88 UNCLASSIFIED unary oracles (Krylov) + 536 non-unary (extract/) — 0 false-EXACT, every boundary DECLINEs.
- INV-1 is the only total-freeze trigger; it never tripped.

## §1 Fold-rate: before → after (provenance-split, NEVER a lone scalar — M-1)
- **No change, and that is the honest finding.** asymptotic corpus fold rate = EXACT 660 / (660+0+1340) = **0.33**,
  identical before and after this run. 0 new EXACT obligations were issued (Loop A recovered 0; Loop B accepted 0).
- WHY (proven, not asserted): the biggest DECLINE cluster, UNCLASSIFIED (624 = 46.6% of 1340), yields **0** additional
  folds from every available recognizer — the honest ceiling, triple-confirmed:
  - **Krylov 32→128 probe-length headroom** on the 88 UNCLASSIFIED unary oracles → 0 recoveries (the conjecturers
    already ran BM; `near_miss` already retries at probe 64; the corpus has no order-16–31 monotone C-finite oracles).
  - **extract/ effect-system frontend** on the 536 non-unary UNCLASSIFIED → router sends 44→parse_arith + 110→io_frame,
    but the extractor z3 gates DECLINE all 154 ⇒ 0 folds (separate ledger, own denominator, never summed into 0.33).
  - the historical `near_miss` R=44 was a *distinct* k-regular subset, already recovered (§AN).
- The remaining DECLINE clusters are the PROVEN mathematics floor: C/crypto-info ~17.9%, I/data-branch ~17.9%,
  F/transcendental ~8.8%, H/IO ~4.5%, E/chaos ~4.3% — none foldable to a ∀-input closed form.

## §2 New EXACT obligations this run
- **0.** No new mechanism (INV-5: 14/22 saturated). No engine code change (INV-3). The engine modules built this run are
  measurement + self-censor + adversarial + hygiene artifacts — they issue no folds.

## §3 Autonomous candidate list (Loop B) — pass / discard with reasons
- Proposed 5, **accepted 0** (the self-censor working at saturation). Each rejection names the mechanism it duplicates:
  | id | candidate | verdict | duplicates / reason |
  |----|-----------|---------|---------------------|
  | B1 | Hankel-determinant rank fold | REJECT (INV-5) | ≡ Berlekamp-Massey/C-finite (M13) — PROVEN: BM order == Hankel rank on 2 seqs |
  | B2 | Padé / rational-GF fold | REJECT (INV-5) | rational GF ⟺ C-finite recurrence (§Z genfunc + M13) |
  | B3 | roots-of-unity-filter fold | REJECT (INV-5) | periodic_fsm + nested_sums + exp-poly machinery |
  | B4 | P-recursive holonomic fold | REJECT (INV-5) | §AE holonomic island + §P Zeilberger (re-submission forbidden) |
  | B5 | Toeplitz-solve iteration fold | REJECT (F4+INV-5) | crosses Axis A (=M13) with Axis B (speedup) + double-count |

## §4 Safety net broadened (Loop C) + drift guard (Loop D)
- Loop C now red-teams the **engine CORE** (not just this-session folds) across THREE foldable classes that stress
  distinct conjecturers: C-finite/BM 60/60 + polynomial/closedform 40/40 + eventually-periodic/period 40/40 all fold
  EXACT-and-CORRECT (re-verified vs the true oracle on a far window n≈400-420 via the existing reverify_exact); 40/40
  random hash oracles DECLINE. Perfect recall + perfect precision (false-EXACT 0) under randomized adversarial generation.
- Loop D `hygiene.py` audits the engine/ package the loop authors itself: H1 zero-dep, H2 banned-bigram absent, H3 no
  agent-model-id leak (the product's own backend-model config is pre-existing/legitimate/out-of-scope), H4 no
  float-EXACT — each with a negative control proving the detector fires. Engine package CLEAN.

## §5 Permanent gates added this run (test_catalog 218 → 223)
- 219 `test_engine_redteam_loop_c` (Loop C, later extended with the core-conjecturer escalation)
- 220 `test_engine_loop_a_probe_headroom` (Loop A soundness witness)
- 221 `test_engine_loop_b_self_censor` (Loop B self-censor + Hankel≡BM proof)
- 222 `test_engine_loop_a_extract_ledger` (Loop A extract/ separate-ledger soundness)
- 223 `test_engine_loop_d_hygiene` (Loop D engine/ drift guard)
- test_build 273 unchanged; corpus 660 EXACT unchanged.

## §6 Reverts / BLOCKED / compaction
- Reverts: 0 (no boundary-loosening attempted; INV-3 held).
- BLOCKED: none.
- Compactions: 1 (resumed cleanly from ENGINE_STATE.md). Restarts: 0.

## §7 Amdahl / axis honesty
- Axis A (recognition/coverage) and Axis B (speedup) kept strictly separate; never summed. No "quantum"+"speedup" claim
  (the banned bigram is absent from all source; the detector assembles it by concatenation).
- The extract/ ledger is a DISTINCT fold unit (own denominator) and is never added to the asymptotic 0.33 (§AB fold_units).

## §8 Next-cycle direction
- The recall frontier is exhausted and both the islands and the core are red-teamed. Honest remaining work is maintenance
  + reporting: re-confirm invariants, optionally extend the core red-team to polynomial/periodic generated oracles
  (same false-EXACT-0 discipline), and keep this report current. The engine will NOT manufacture recall to look busy.
