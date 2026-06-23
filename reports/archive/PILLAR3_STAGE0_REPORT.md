# Pillar 3 · Stage 0 (v48) — profiler + neutral-baseline measure + complexity fitter + recorder

The foundation; everything gates on it. All four modules tested.

## Delivered
- `pillar3/measure.py` — **the single source of truth.** `SpeedupReport` REFUSES to exist without `n` AND
  `hotspot_fraction` (raises) and computes `amdahl_ceiling = 1/(1-f)`. `measure_whole_program` = warmup-aware
  median wall-clock ratio of the WHOLE program (Clock C), neutral baseline. Kernel ratios are never produced here.
- `pillar3/profiler.py` — cProfile-backed ground truth: cost centers ranked by cumulative time, each with its
  exclusive-time fraction of the run (the Amdahl input). `rank_by_self_time` for true fix targets.
- `pillar3/complexity.py` — the flagship: Goldsmith-Aiken-Wilkerson (ESEC-FSE 2007) trend-prof. Log-log
  least-squares power-law fit `y=a·n^b` (pure numpy) + R²; classifies O(1)/O(log n)/O(n)/O(n log n)/O(n^b);
  flags super-linearity.
- `pillar3/record.py` — the gold oracle: record (args,output) of the trusted original; `differential_test`
  catches any divergence; carries the rule-of-three δ=3/n for the PROBABILISTIC grade.

## Measured / verified (the Stage-0 test)
- complexity fitter recovers **O(n), O(n log n), O(n²), O(n³)** (b within ±0.15, R²>0.95); super-linear flagged.
- profiler ranks a planted O(n²) hotspot #1 at **>50% self-time**.
- measure **raises** without n+hotspot_fraction; a real run reports the ratio with **Amdahl ceiling 10×** at
  hotspot 90%.
- differential oracle: a correct candidate passes, a wrong candidate is **caught** (→ DECLINE path).

## §0 self-check
1. whole-program measured ratio? yes (measure.py is the only ratio source). 2. carries hotspot+ceiling? yes
   (SpeedupReport enforces it). 3. graded + ADT raise? grade ADT (Pillar 1 kernel_verdict) reused in Stage 1.
4. differential at each step? record.py is the oracle Stage 1+ run every step. 5. UNVERIFIED tagging? the
   no-LLM proposer is stated honestly (deterministic detectors); toolchain-blocked transforms tag UNVERIFIED.

## Honest scope
No live LLM in the sandbox ⇒ the "LLM classifier/proposer" is realized as deterministic structural detectors +
pattern fixers (Rule 5: the LLM was never the arbiter — the profiler is ground truth, the verifier decides).
112 tests pass, 0 regression.
