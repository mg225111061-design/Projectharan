# PHASE PERFORMANCE REPORT (§C)

All numbers are **measured whole-program**, best-of-k, carry the hotspot fraction `f` and Amdahl ceiling
`1/(1−f)`, and satisfy **ratio ≤ ceiling by construction** (coherent floor-pipeline). Grades from the real
ADT. Asymptotic multipliers are **input-size-dependent — n is quoted**. Representative values (vary with load).

## Flagship — memoized DP (the largest honest win)
- **Fibonacci O(2ⁿ) → O(n)**, recognised → memoised, graded **PROBABILISTIC** (control flow ⇒ Z3 bounded
  validation doesn't apply; differential over a strong input set + a coherent measurement).
- Measured **~10,000× whole-program at n=29**, hotspot fraction f ≈ 0.99999, **Amdahl ceiling ≈ 2.0×10⁵×**,
  ratio ≤ ceiling. The program here *is* the exponential recursion (f≈1), which is exactly when a huge
  multiplier is legitimate (§X: dominant hotspot >95–99% with an asymptotic inefficiency).
- The wrong recurrence (off-by-one) is caught by differential ⇒ **DECLINE**.
- ⚠ This is honest precisely because n is quoted and f≈1. At a smaller n the multiplier is smaller; embedded in
  a larger program (lower f) the whole-program ratio is bounded by 1/(1−f), not 10,000×.

## Big-multiplier recognizers (`pillar3/algorithms.py`)
| recognizer | transform | grade | measured (rep.) | ceiling | n |
|---|---|---|---|---|---|
| memoized_dp_fib | O(2ⁿ) → O(n) | PROBABILISTIC | ~10,000× | ~2e5× | 29 |
| hash_join | nested-loop O(n·m) → hash O(n+m) | PROBABILISTIC | ~28× | ~335× | 300×300 |
| two_sum_hash | O(n²) → hash O(n) | PROBABILISTIC | ~150× | ~320× | 600 |
| majority_boyer_moore | O(n²) → O(n) | PROBABILISTIC | ~39× | ~70× | 260 |
| kadane_max_subarray | O(n²) → O(n) | PROBABILISTIC | ~38× | ~57× | 240 |
| binary_search | O(n·Q) → O(Q·log n) | PROBABILISTIC | ~17× | ~163× | 400 |

All control-flow recognizers are **PROBABILISTIC, never EXACT** (Z3 returns *unknown* on the branching) — and
labelled so. Every adversarial wrong variant is caught (differential) ⇒ **DECLINE**.

## Verified lifting (EXACT, Z3 two-step) — `pillar3/lifting.py` (7 lifts)
running-sum & weighted-running-sum O(n²)→O(n); range-sum-query & difference-array O(K·n)→O(n+K); telescoping
O(n)→O(1); factor-constant; multi-loop-fusion. Each EXACT with a measured win, ratio ≤ ceiling; 5 adversarial
wrong lifts Z3-REFUTED ⇒ DECLINE.

## Real LLM proposer (`pillar3/proposer.py` + `webapi/engine_bridge.py`)
Five providers (Gemini default **gemini-3.5-flash**, Groq, Claude, ChatGPT, OpenAI-compatible) via the
OpenAI-/Anthropic-/Gemini-shaped transports. The LLM **proposes**; the verifier **arbitrates** (Rule 5).
Tests (mocked LLM): correct→verified+win; wrong→DECLINE; extend rejects a no-certificate LLM fix; no key→
deterministic fallback. Live round-trip: **Gemini reachable** (real 400 on a bad key) — Groq host is
egress-blocked in this sandbox ⇒ UNVERIFIED [egress], stated honestly, never faked.

## GPU/SIMD offload (`pillar3/offload.py`)
Real numpy-vectorised transcendental kernel: dominant ⇒ measured ~2.7× ≤ ceiling ~412× PROBABILISTIC (floats);
non-dominant kernel ⇒ DECLINE on the **measured** Amdahl ceiling even with a big kernel speedup; GPU ⇒
UNVERIFIED [no GPU].

## §X — WHAT WE MUST NOT CLAIM (verbatim)
- Whole-program **average** 50–100× is impossible for already-reasonable code (Amdahl). 50–100× requires a
  dominant hotspot (>95–99%) with an asymptotic/algorithmic/offloadable inefficiency; else ~10–20×, <2×
  already-optimized.
- **Kernel ≠ whole-program** (700× kernel → 4–6× end-to-end). Whole-program only.
- Asymptotic multipliers are **input-size-dependent** — quote n.
- Component multipliers **do not multiply** (Whatnot 3×·20×·6.7× → 5.8×). Measure fresh.
- The LLM **proposes**; the verifier decides. Unaided LLMs are wrong ~62% — value is verification. Never ship
  an LLM proposal that failed verification.
- Differential-only evidence is **PROBABILISTIC**, never EXACT.
- The grade is **OUTPUT confidence at runtime** (input + verifier), not a fixed property.
