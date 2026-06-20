# MEGA-DIRECTIVE — running progress log

16-hour autonomous performance-first build on branch `claude/funny-maxwell-im9x07`, building on Pillar 3
Stages 0–5. Append every iteration: timestamp · phase · what was measured · next bottleneck · hours elapsed.

Format: `[T+h.h] PHASE — measured result — next`.

---

- **[T+0.0] START** — Pillar 3 Stages 0–5 landed (v48–v53), 118 tests green. Mode separation is the #1 gap:
  the fast/normal/extend boundary was fuzzy. Plan: M (spine) → P (providers) → D (detectors) → R (corpus) →
  S (extend depth) → U (product) → ∞.

- **[T+1.0] PHASE M (v54–v55) — mode separation spine. DONE.**
  Built `verifier.py` (tier ladder MICRO<CHEAP_CERT<FULL_CERT + Z3 invocation counter), `mode.py`
  (ModePolicy encoding every M.2 row + M.1 philosophy; detector sets 10⊂18⊂27), `engine.py` (mode-aware loop
  controller; coherent floor-pipeline measurement so ratio ≤ ceiling by construction), `canonical.py` (5-waste
  fixture, measured fractions).
  **Measured (one canonical program, three modes):** fast → 1 PROBABILISTIC win, **z3_calls=0**, ~0.5 s,
  1.33×. normal → 3 rounds (EXACT+PROBABILISTIC), 1.87×. extend → EXACT-only, **z3_calls=2**, sweep O(n²)/3
  sizes, 1.97×. Monotonic speedup 1.97≥1.87≥1.33 and latency 0.5<1.1<2.1 s. ★ The same PROBABILISTIC fix is
  accepted in normal, DECLINEd in extend (EXACT-or-DECLINE) ★. All seven distinctness assertions pass; every
  shipped row ratio ≤ ceiling.
  **Next bottleneck:** the proposer is deterministic only — PHASE P wires real LLM providers (still arbitrated
  by the verifier under ModePolicy). Then PHASE D widens detectors 4→40+.

- **[T+1.8] PHASE P (v56) — real LLM provider layer. DONE.**
  `provider.py` extended to FIVE providers (anthropic, anthropic_compat, openai_compat, + native **openai**
  ChatGPT and **gemini**), with `transport_kind()` selecting anthropic_sdk / openai_chat / gemini_generate and
  per-vendor key fallback. `pillar3/proposer.py`: `propose_fix` (LLM-or-deterministic) + `arbitrate` (the
  verifier decides under ModePolicy). `build_request` puts the key only in send-headers.
  **Measured:** five providers resolve + pick the right transport; ★ a wrong LLM fix → DECLINE (arbiter holds)
  ★; ★ an LLM fix in extend with no certificate → DECLINE, same proposal accepted in normal ★; no-key →
  deterministic MEASURED; live code-text → UNVERIFIED (not auto-executed). Keys never logged/stored/committed.
  **Next bottleneck:** only ~4 waste types are covered — PHASE D expands detectors 4 → 40+, each gated by the
  mode tier.

- **[T+2.6] PHASE M2 spine — STABILIZED (robustness fix).** The full suite exposed `test_phaseM2` as flaky
  under load (the diminishing-returns marginal and a once-measured-then-reused baseline are noise-sensitive).
  Fixes: (1) `canonical.py` now uses a DETERMINISTIC cost model (each stage's runtime is a busy-loop sized to
  an exact target fraction; the real op is kept small for differential/Z3), (2) `engine.py` measures
  baseline/floor/candidate in ONE session via best-of-k (`measure.time_best`) — no stale baseline, contention
  spikes filtered. Larger per-stage speedup (20×) makes the marginals noise-proof. **15/15 stability trials
  green** (min extend−normal gap 0.29, normal−fast 0.50).

- **[T+3.0] PHASE D1 (v57) — catastrophic single-bug detectors (fast-eligible). DONE.**
  `pillar3/detectors2.py`: redos_regex, redundant_io_parse, accidental_full_scan, quadratic_build,
  redundant_sort. **Measured whole-program wins:** redos ~3400×, parse-hoist ~20×, full-scan→index ~138×,
  quad-build→append ~150×, sort-hoist ~88×. Each detected, differential-verified, ★wrong fix→DECLINE★, all
  registered fast-tier. **Next:** D2 (structural/data-representation, normal-tier).

- **[T+3.4] PHASE D2 (v58) — structural / data-representation detectors (normal-tier). DONE.**
  dict_to_columnar, loop_invariant_hoist, copy_elim, materialize_to_lazy, deep_n_plus_1. **Measured:** SoA ~1.3×
  (honest pure-Python crossover), loop-invariant-hoist ~700×, copy-elim ~50×, materialize→lazy ~3000× (early
  exit), deep-N+1 ~57×. Each detected, differential-verified, ★wrong→DECLINE★, gated normal-only (in
  NORMAL_DETECTORS, not FAST). 123 tests, 0 regression. **Next:** D3 (heavy, extend-tier).
