# PHASE ENGINE REPORT — Track P depth (this campaign)

All numbers below are **measured whole-program** by the real engine, carry their hotspot fraction `f` and
Amdahl ceiling `1/(1−f)`, and satisfy **ratio ≤ ceiling by construction** (coherent floor-pipeline
measurement). Grades come from the real ADT (`kernel_verdict`). Asymptotic ratios are quoted **with n**
because they grow with input size. Numbers vary run-to-run with machine load; representative values shown.

## PHASE L — verified lifting (Z3 two-step, EXACT) — `pillar3/lifting.py`
Lift a hot region to a spec, re-synthesize the optimal, EXACT iff Z3 proves **both** spec≡original and
optimized≡spec (bounded translation validation over symbolic integer arrays; no Lean/Coq).

| lift | transform | grade | measured (rep.) | ceiling | note |
|---|---|---|---|---|---|
| running_sum | hand-rolled O(n²) running sum → O(n) scan | EXACT | ~4.9× | ~5.0× | **no fixed detector recognizes it** (generalization) |
| weighted_running_sum | O(n²) → O(n) | EXACT | ~7.8× | ~8.3× | |
| range_sum_query | K queries O(K·n) → prefix array O(n+K) | EXACT | ~3.7× | ~4.1× | |
| difference_array | K range-updates O(K·n) → diff array O(n+K) | EXACT | ~4.5× | ~5.0× | |
| telescoping_sum | Σ(a[i+1]−a[i]) → a[-1]−a[0], O(n)→O(1) | EXACT | ~1.2× | ~1.2× | honest small win at its f |
| factor_constant | Σ(c·x) → c·Σx | EXACT | proof only | — | distributive |

## PHASE V — wider Z3 equivalence (PROBABILISTIC→EXACT) — `pillar3/equiv_transforms.py`
Reuses the lifting grader as an identity lift (spec≡original); EXACT needs the proof **and** a measured win.
Strength reduction (x⁴→x·x·x·x), loop-invariant hoisting, CSE — all Z3-proven; each clears the win-floor to
EXACT (a proven-but-speed-neutral transform DECLINEs — no "EXACT 1.0×").

## PHASE A — algorithm recognition (PROBABILISTIC) — `pillar3/algorithms.py`
Control flow ⇒ Z3 bounded validation doesn't apply ⇒ graded PROBABILISTIC by differential (PHASE-I evidence)
+ metamorphic (PHASE-M) + coherent measurement.

| recognizer | transform | grade | measured (rep.) | ceiling |
|---|---|---|---|---|
| kadane_max_subarray | O(n²) → O(n) | PROBABILISTIC | ~38× | ~57× |
| two_sum_hash | O(n²) pair → hash O(n) | PROBABILISTIC | ~150× | ~320× |
| majority_boyer_moore | O(n²) → O(n) voting+verify | PROBABILISTIC | ~39× | ~70× |

## PHASE I / PHASE M — the accuracy nets
- **PHASE I** (`inputgen.py`): boundary + property + Z3-guided branch coverage; a fix that only breaks on `[]`
  is caught (δ from real n, shrinks as n grows).
- **PHASE M** (`metamorphic.py`): a dedup-sort passes differential on distinct inputs but the multiset relation
  refutes it on duplicate inputs ⇒ DECLINE.

## PHASE O — SIMD/GPU offload (Amdahl-gated) — `pillar3/offload.py`
Real numpy-vectorized transcendental kernel: dominant ⇒ measured ~2.7× ≤ ceiling ~412× PROBABILISTIC (floats,
δ stated); non-dominant kernel ⇒ DECLINE on the **measured** Amdahl ceiling; GPU ⇒ UNVERIFIED [no GPU].

## The moat — `pillar3/moat.py`
**13/13 adversarial wrong swaps refuted** (9 by Z3 counterexample, 4 by differential), **zero false-accepts**.

## Grade distribution (this campaign's additions)
- **EXACT**: 6 lifts + 3 transforms (Z3 machine-checked).
- **PROBABILISTIC**: 3 recognizers + SIMD offload (differential/metamorphic, δ stated).
- **DECLINE**: every wrong swap; proven-but-no-win transforms; non-dominant offload; GPU.

## Honest scope / UNVERIFIED
- Lifting proofs are **bounded** (per-size symbolic), not unbounded induction — stated.
- Nonlinear constructs (e.g. Horner's x**i) → Z3 returns *unknown* ⇒ they stay PROBABILISTIC, never faked EXACT.
- GPU offload UNVERIFIED [no GPU]; live LLM round-trip is Gemini-only reachable from this sandbox (Groq host
  egress-blocked) — both tagged honestly, never faked.
