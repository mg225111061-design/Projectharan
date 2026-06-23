# v39 PHASE A — integration report (waking the sleeping parts into the live product)

Branch `claude/funny-maxwell-im9x07`, on top of v38 `0a79da4`. §0 gap: v37/v38 were *additive opt-in* — the
parts were fast but the **product** still ran the old paths. PHASE A wires the parts into live call sites and
proves **product-level** regression-0 + real gains. Three clocks kept separate (this is Clock B / Clock C /
scaling — not Clock A / LLM latency).

## A1 — integration audit (what was green-but-sleeping)
`grep` of every v37/v38 module's live call sites found **almost all SLEEPING**: `graph_core`, `semantic_cache`,
`egraph_native`, `hidden_closed`, and the entire v37 sublinear cluster (freivalds/prony/CS/rSVD/sketch/…) had
**no live caller**. Risk-labelled: graph_core→grounding (MED), semantic_cache→verify (HIGH), native→optimize
(MED), sublinear cluster (deferred to PHASE B by design — consulted post-DECLINE).

## A2 — Rust graph core → LIVE grounding pipeline  ✅ woke up
`grounding_pipeline.build_index` now routes its spectral partition through `graph_core` (differential-bit-
identical Rust) with internal Python fallback.
- **Product measurement (n=1500, k=6):** before(Python) **12,041 ms → after(Rust) 50.6 ms**, clusters
  **bit-identical** → **NO REGRESSION** (a ~238× product-level win on the orchestration path).
- **Ceiling gone in the product:** `build_index` completes at n=8000 (~1s) where pure-Python capped at 4000.

## A3 — semantic 2nd level → LIVE proof_cache, behind a break-even gate  ⚖️ measured OFF (honest)
`proof_cache.prove_forall_cached` now falls through to a lossless semantic 2nd level on a structural miss —
**only when `SEMANTIC_ENABLED`**, which a break-even gate sets (key 325µs vs solve 2839µs ⇒ pays off above
**11.4%** hit-rate-among-structural-misses).
- **Honest finding:** on a transparent fix-loop traffic **proxy** (real LLM fix-traffic is **[BLOCKED: no key/
  egress]**) the measured rate is **11.1% — marginally BELOW** break-even (the structural cache already catches
  most reuse; many obligations are α-equivalent). So the gate **leaves it OFF** — wiring it would be a net loss.
- `SEMANTIC_ENABLED` defaults **False ⇒ proof_cache byte-identical ⇒ 0 regression.** The gate is data-driven (a
  33% stream flips it ON) and will enable automatically if real measurement clears the bar. 2-level verified
  **lossless**.

## A4 — LLVM native emission → LIVE optimize() (opt-in), translation-validated  ✅ woke up
`agentic.optimize(code, emit_native=…)`: a CLOSED form is lowered to native i64 and **translation-validated**
against the exact (sympy) value of the same closed form (catches i64 overflow / lowering bugs; closed_form ≡
naive is already proven by the classifier).
- **`emit_native` defaults False ⇒ bare optimize() byte-identical (0 regression).** LLVM JIT compile is ~39 ms
  (build-time); the **pipeline opts in** (`run_pipeline`, `stage_pipeline`) where that is negligible vs the
  LLM/verify seconds and yields the O(1) Clock-C native artifact.
- **Measured:** Σk / Σk² / Σk³ → EMITTED, native **bit-exact** vs the naive sum; non-closed folds never attempt
  native (byte-identical); overflow/non-univariate/no-llvmlite ⇒ honest DECLINE, structural result intact.

## A5 — product regression gate (the #1 condition)
| live path | before (integrations off) | after | verdict |
|---|---|---|---|
| grounding build_index (n=1500,k=6) [Clock B] | 12,041 ms | **50.6 ms** | NO REGRESSION (faster, identical result) |
| verify batch via proof_cache [Clock B] | — | byte-identical (SEMANTIC OFF) | NO REGRESSION |
| optimize() non-closed (runtime-rep) | <1 ms | <1 ms (native not attempted) | NO REGRESSION |
| optimize() closed (build-time, opts native) | <1 ms | ~39 ms build-time → O(1) Clock-C artifact | not a runtime regression (opt-in, build-time) |

- **Woke up:** graph_core (live in grounding), native emission (live in pipeline optimize). **Still deferred by
  design:** the v37 sublinear cluster → its wake-up is **PHASE B** (DECLINE-pile recovery).
- **phone-home 0** (in-memory/ctypes only; no socket/http in touched modules); **keys LEVEL-1** (per-call,
  unstored — only `api_key` parameter passing to the provider, the existing Clock-A path, untouched);
  verify loop has **0 network round-trips**.
- Fixed a **pre-existing flaky** ABFT timing assertion (`freivalds_speedup ≥ 1.0`, single-shot, noisy near 1×)
  by black-boxing the measurement (median-of-5 + warmup → stable 1.4–1.5×). Unrelated to v39 (passed 5/5 in
  isolation); rule 1: black-box measurement bugs.

**100 tests pass, 0 regression.** PHASE A success: two real parts woke into the live product with a measured
238× grounding win and 0 runtime regression; the semantic cache was honestly measured below break-even and left
OFF rather than imposing a net loss.
