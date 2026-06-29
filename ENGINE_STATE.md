# ENGINE_STATE.md — autonomous research-build engine checkpoint (the lifeline)

> **RESUME PROTOCOL (read first on every restart/compaction):** read this file top-to-bottom, then resume at
> "CURRENT LOOP POSITION". Never stop with an excuse; if a task blocks, log BLOCKED + reason and move to the next
> loop. The engine has no completion condition — it runs until the 10h mark, then §4 final report (WAKE_REPORT.md).

## 🟢 INVARIANT STATUS (auto-checked each commit; false-EXACT==0 is the ONLY total-freeze trigger)
- **INV-1 false-EXACT == 0** — ✅ HOLDING. Triple-confirmed cycle 2: (a) corpus live re-measure seed 20260628 = EXACT
  660 / PROB 0 / DECLINE 1340 / ERROR 0; (b) Loop-C red-team 640 probes 0 false-EXACT; (c) Loop-A corpus dig on the
  88 UNCLASSIFIED unary oracles = 0 false-EXACT (independent ground-truth far-window re-check).
- **INV-2 660 EXACT lossless + test_build 273 + test_catalog 221** — ✅ HOLDING (catalog 218→219 red-team→220 Loop-A
  →221 Loop-B; Loop-D regression confirmed **219 passed/0 failed** on cycle-1 commit; 221 to be reconfirmed this cycle).
- **INV-3 no boundary-loosening (z3 gate / DECLINE / precision)** — ✅ none attempted (engine code UNCHANGED; loop_a/
  loop_b are measurement+self-censor artifacts, issue 0 new EXACT obligations).
- **INV-4 progress = obligations + flip counts (provenance-split), NOT a single scalar.** Cycle-2 obligations added: 0
  (Loop A recovered 0; Loop B accepted 0). Gates added: +2 (loop_a soundness, loop_b self-censor). HONEST: 0 new folds.
- **INV-5 no new mechanism (14/22 saturated)** — ✅ PROVEN this cycle: Loop B accepted 0/5 candidates, each a named
  face/axis-cross; Hankel-rank≡Berlekamp-Massey demonstrated with running code (BM order == Hankel rank on 2 seqs).
- **Verifier truth**: z3 = finite identities only; ∀-n = telescoping / companion / Pfaffian / symplectic + held-out.

## REPO
- repo `mg225111061-design/Projectharan`, branch `claude/charming-brahmagupta-q4wwgh`, HEAD = engine cycle 1 (03ba721),
  cycle 2 about to commit.
- Gates command: `OMP_NUM_THREADS=1 python3 test_build.py` (273) · `python3 test_catalog.py` (222) ·
  `python3 -c "from measure import run_corpus as RC; print(RC.run(seed=20260628).summary['overall'])"` (EXACT 660).

## PART 1 (8-phase initial fuel) — ✅ COMPLETE (built+pushed this session)
- P5 recall/strip disguise-strip = §AL · P6 recall/compose = §AP · P7 extract/classify on corpus = §AQ ·
  P8 proof-carrying flip = §AT (proof_carrying.py, Clock B) · P1 free-fermion island = §AU (mathmode/free_fermion.py) ·
  P2 Krylov/Carleman/displacement = §AY (qfold/) · P3 Koopman/treewidth = §AU (island_hooks.py + extract/tensor_contract.py).
- **PHASES COMPLETE → ENGINE MODE.**

## MEASURED BASELINE (corpus seed 20260628, n=2000)
- overall: EXACT 660 / PROB 0 / DECLINE 1340 / ERROR 0; fold_rate 0.33 (NEVER reported as a lone scalar — §M-1).
- provenance: synthetic 90.4% / realworld 6.8% (+§AN k-regular recoveries on realworld popcount).
- DECLINE clusters (the dig-map): UNCLASSIFIED ~46.6% · C/crypto-info-floor ~17.9% · I/data-branch ~17.9% ·
  F/transcendental-z3-wall ~8.8% · H/IO ~4.5% · E/chaos ~4.3%. Most are the PROVEN honest ceiling (not foldable).
- near_miss R class historically = 44 (all k-regular, recovered §AN). New §AY/§AU recognizers (Krylov/Pfaffian/…)
  are niche vs this corpus mix ⇒ expected Loop-A yield is small; honest to measure and log either way.

## CURRENT LOOP POSITION
- **ENGINE MODE, cycle 3 DONE (Loop A extract-ledger) → committing → Loop D regression (catalog 222).** catalog now
  **222** (+ extract-ledger soundness gate). cycle-2 Loop-D regression confirmed catalog **221 green** on commit 1518cf3.
- Cycle-3 Loop A (`engine/loop_a.py::dig_extract_ledger`): measured the §AQ `extract/` effect-system frontend (a real
  product path via server.py/intent.py, but NOT measured by engine_adapter) on the **536 non-unary UNCLASSIFIED** as a
  SEPARATE fold-unit ledger (own denominator, NEVER summed into 0.33 — M-1/§AB fold_units; additive not double-count
  since the conjecturers can't run on non-unary code). Result: router sends 44→parse_arith + 110→io_frame, but the
  extractor z3 gates **DECLINE all 154 ⇒ 0 folds**, rate 0.0. ★★ HONEST CEILING NOW TRIPLE-CONFIRMED: Krylov 0 (88
  unary) + extract/ 0 (536 non-unary) + the distinct near_miss R=44 (k-regular) — the UNCLASSIFIED 624 cluster yields
  ZERO additional folds from every available recognizer. Fold rate does not rise; PROVEN by measurement, not asserted.
- (prior) cycle 2 catalog now **221** (+ loop_a probe-headroom gate, + loop_b self-censor gate).
- Cycle-2 Loop A (`engine/loop_a.py`): corpus live re-measure = **EXACT 660 / DECLINE 1340** (invariant held). Dug the
  UNCLASSIFIED cluster (**624** = 46.6%: 88 unary oracles, 536 non-unary [212 data-loop, 362 structureless]). The only
  non-double-counting probe (Krylov 32→128 samples, since `near_miss` already covers 64) recovered **0** of 88 with
  **0 false-EXACT** — the new §AY/§AU islands add 0 corpus recall (matrices/circuits absent by construction). Synthetic
  soundness PROVEN (order-18 declined@32 / recovered@128 / far-reverified; hash declines@128). HONEST CEILING CONFIRMED.
- Cycle-2 Loop B (`engine/loop_b.py`): F1–F4 + INV-5 self-censor over 5 proposed candidates (Hankel-rank, Padé/rat-GF,
  roots-of-unity filter, P-recursive holonomic, Toeplitz-solve) → **0 accepted, 5 rejected**, each a named face/axis-
  cross. Flagship double-count PROVEN: Berlekamp-Massey order == Hankel stabilized rank on Fibonacci(2) & custom(3).
- Cycle-2 Loop C (re-run): red-team 640 probes, **0 false-EXACT**, INV-1 holds.
- NEXT (after Loop D 273/222/660 green + push): cycle 4 — the UNCLASSIFIED-recall path is now PROVEN exhausted (triple-
  confirmed 0), so STOP chasing it. Pivot Loop A to the honest complementary question: "where the §AY/§AU islands DO
  apply, do they fire correctly and SOUNDLY?" Build a small ISLAND-SHAPED micro-corpus (matrix-iteration / Clifford
  circuits / skew-symmetric free-fermion inputs) and measure island recall as a SEPARATE DOMAIN ledger (own denominator,
  never summed into 0.33; false-EXACT 0 by independent ground-truth re-check). This validates the islands aren't useless
  — they're domain-specific — without inflating the general rate (honest, not goalpost-moving). Then Loop B/C/D.
  Alternative if that saturates: escalate Loop C to adversarially re-verify the CORE 660 EXACT corpus folds (broaden
  INV-1 from this-session folds to the whole engine). Checkpoint each cycle.

## AUTONOMOUS DECISION LOG (morning audit)
- (cycle 0) PART 1 judged complete (all 8 phases already built+pushed across §AL/§AP/§AQ/§AT/§AY/§AU); → ENGINE MODE.
- (cycle 1, Loop C) Built the red-team FIRST (before fold-rate hunting) because INV-1 (false-EXACT 0) is the only
  total-freeze trigger — the active safety device must exist before the engine proposes/builds more folds. Result:
  0 false-EXACT across 640 probes; wired as a permanent gate. Logged.
- (cycle 2, Loop A) Discovered the new §AY/§AU islands' corpus recall is provably ~0: (1) the conjecturers already run
  BM on proceed=True oracles, (2) `near_miss` already retries at probe=64, so the only honest non-double-counting probe
  is 32→128. Measured it on all 88 UNCLASSIFIED unary oracles: 0 recovery, 0 false-EXACT. Did NOT force a recovery —
  logged the honest ceiling. The new islands' value is for matrix/circuit INPUTS not present in this code corpus.
- (cycle 2, Loop B) Refused to invent a fake "new fold": ran 5 candidates through F1–F4 + INV-5 and let the self-censor
  kill all 5 as faces of existing mechanisms. Proved the flagship (Hankel≡BM) with running code rather than asserting
  it. A clean "0 accepted, every rejection named" is the discipline working at saturation, not a failure.

## RESTART/COMPACTION COUNTER
- compactions: 1 so far (resumed from this file post-compaction; cycle 2 done clean) · restarts: 0.
