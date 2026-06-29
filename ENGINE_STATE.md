# ENGINE_STATE.md — autonomous research-build engine checkpoint (the lifeline)

> **RESUME PROTOCOL (read first on every restart/compaction):** read this file top-to-bottom, then resume at
> "CURRENT LOOP POSITION". Never stop with an excuse; if a task blocks, log BLOCKED + reason and move to the next
> loop. The engine has no completion condition — it runs until the 10h mark, then §4 final report (WAKE_REPORT.md).

## 🟢 INVARIANT STATUS (auto-checked each commit; false-EXACT==0 is the ONLY total-freeze trigger)
- **INV-1 false-EXACT == 0** — ✅ HOLDING (corpus seed 20260628: EXACT 660 / PROB 0 / DECLINE 1340 / ERROR 0).
- **INV-2 660 EXACT lossless + test_build 273 + test_catalog 218** — ✅ HOLDING (catalog now 218 incl. §AS/§AY/§AT/§AU).
- **INV-3 no boundary-loosening (z3 gate / DECLINE / precision)** — ✅ none attempted.
- **INV-4 progress = obligations + flip counts (provenance-split), NOT a single scalar.**
- **INV-5 no new mechanism (14/22 saturated)** — ✅ all new work = recognition branches / independent-algebra module.
- **Verifier truth**: z3 = finite identities only; ∀-n = telescoping / companion / Pfaffian / symplectic + held-out.

## REPO
- repo `mg225111061-design/Projectharan`, branch `claude/charming-brahmagupta-q4wwgh`, HEAD = §AU (b507525).
- Gates command: `OMP_NUM_THREADS=1 python3 test_build.py` (273) · `python3 test_catalog.py` (218) ·
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
- **ENGINE MODE, cycle 1 DONE (Loop C) → cycle 2 NEXT (Loop A corpus dig).** catalog now **219** (+ red-team gate).
- Cycle-1 Loop C result: `engine/red_team.py` — **640 randomized adversarial probes, 0 false-EXACT, INV-1 holds**;
  every boundary (random stream / sampling cert / injected T-gate) DECLINEs. Wired as a PERMANENT regression gate
  (test_catalog `test_engine_redteam_loop_c`). Pushed.
- NEXT (cycle 2, Loop A): re-measure corpus; analyse the UNCLASSIFIED (~46.6%) DECLINE cluster; attempt the new
  §AY/§AU recognizers on a sample; measure fold-rate delta (honest — likely small vs this corpus mix; log either way).
  Then Loop D regression (273/219/660), then repeat A→B→C→D.

## AUTONOMOUS DECISION LOG (morning audit)
- (cycle 0) PART 1 judged complete (all 8 phases already built+pushed across §AL/§AP/§AQ/§AT/§AY/§AU); → ENGINE MODE.
- (cycle 1, Loop C) Built the red-team FIRST (before fold-rate hunting) because INV-1 (false-EXACT 0) is the only
  total-freeze trigger — the active safety device must exist before the engine proposes/builds more folds. Result:
  0 false-EXACT across 640 probes; wired as a permanent gate. Logged.

## RESTART/COMPACTION COUNTER
- compactions: (tracked by harness) · restarts: 0 so far this engine run.
