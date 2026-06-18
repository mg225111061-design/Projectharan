# BUILDLOG — autonomous accuracy + speed build

Honest log of measured improvements. Every number here is reproduced by `python3 test_build.py`
and the per-stage measurement scripts. No fabricated numbers; blocked items say so with the reason.

**Environment (verified):** Python 3.11, z3 4.16.0, sympy 1.14.0. **No API key** present
(`HARAN_KEY`/`ANTHROPIC_API_KEY` both empty). **No Rust binaries** (`jeff_foldsum`, `cfinite_nth`,
`galois_absence` absent). **No cvc5 / coq / bitwuzla.** These absences gate some stages (noted below).

---

## STAGE 0 — app works

- **0.1 live Claude call — BLOCKED (no key).** Cannot make a real (non-mock) call: no `sk-ant-` key
  in this environment. Verified the request *shape* is API-correct against the `claude-api` skill:
  model `claude-opus-4-8` is valid; `thinking:{type:"adaptive"}` is the correct (and only) on-mode for
  Opus 4.8 — so those are **not** the 400 cause. Root cause of the user being *stuck*: `_friendly_error`
  swallowed the 400 detail. **Fixed:** the redacted reason is now surfaced (key still masked).
  Tested: `test_error_surfacing_shows_cause_hides_key` (cause visible, `sk-ant-…` never leaks).
- **0.2 app end-to-end (mock mode) — VERIFIED (live curl).** `/health`→`{"ok":true}`; `/`→serves page;
  `/api/generate` coding→`PROVEN` + closed form `n*(n+1)/2`; chat→plain reply `verified:false`
  (label separation intact); `/api/stream`→real `classify→generate→token→verify→optimize→done` stages.

---

## STAGE 1.3 — Clover spec consistency gate [ACCURACY · SOUND] — DONE

`spec_gate.py`: a real Z3 decision procedure classifies the `ensures` spec (treating `result`+params
as free): VACUOUS_TRUE (¬spec unsat), CONTRADICTORY (spec unsat), VACUOUS_PRECOND (`requires` unsat),
OK, or UNMODELED (lists/opaque → passed through, never judged). **Wired into `prove_exact.prove_correctness`**
so a vacuous spec returns tier `VACUOUS` instead of a meaningless `PROVEN`.

- **Measured (12-spec corpus): catch_rate = 1.0 (6/6 vacuous caught), false-positive rate = 0.0
  (0/6 real specs wrongly rejected), 1 UNMODELED (opaque `is_sorted`, correctly passed through).**
- No regression: agentic mock corpus still `extended solved=4 proven=4 optimized=4 wrong=0`.
- Tests: `test_spec_gate*`, `test_gate_wired_into_proof_path`.
- Honesty: rejects only when Z3 *proves* vacuity (unsat) — sound, FP=0 by construction; whatever Z3
  can't model passes through to the normal verifier.

---

## STAGE 3.3 — counterexample diversification (SMART ICE) [ACCURACY · SOUND] — DONE

`z3_adapter.find_counterexamples(goal, var_types, k)`: block-and-resolve to return up to k **distinct**
counterexamples, each a real Z3 model of ¬goal (SOUND), tagged by violation shape (lhs<rhs / lhs>rhs /
boundary). Previously a refutation surfaced exactly **1** point.

- **Measured:** on `∀a,b: a*b ≥ a+b` it returns **4 distinct** counterexamples; an independent Python
  re-check confirms **all 4 genuinely violate** the goal (0 spurious). A true goal (`n*n ≥ 0`) → PROVEN, 0 CX.
- Test: `test_counterexample_diversification_sound_and_distinct`.
- Honest scope: the capability + soundness are proven here. Feeding the *diverse set* into the live
  write→verify→**fix** prompt (to measure convergence-rounds reduction) needs (a) a live model key and
  (b) multi-CX surfacing from `mr_haran` obligations — integration point identified; live convergence
  measurement is **[TBD: needs key]**, not claimed.

---

## STAGE 3.1 — fold-engine extension: pure-Python C-finite (SPEED flagship) [lossless] — DONE

`cfinite.py`: exact-integer companion-matrix evaluation (O(log n) power-by-squaring) + O(n) naive
reference; `verify_cfinite` certifies CLOSED only when the two are **identical** across several n
(equal by theorem → lossless, not an approximation). Wired into `closure_classifier.classify_recurrence`,
replacing the absent Rust `cfinite_nth` binary.

- **Coverage (recurrence corpus fib/pell/tribonacci/lucas/jacobsthal): 0% → 100% CLOSED O(log n).**
  Previously every recurrence was UNKNOWN ("cfinite_nth engine not built").
- **Value-exact:** fib(10)=55, fib(40)=102334155, pell(8)=408; companion≡naive for all n∈[0,60).
- **Measured wall-clock speedup (this pure-Python impl, identical bignum result):**
  n=20000 → **25×**, n=100000 → **39×**, n=300000 → **41×** (O(log n) vs O(n) ring ops).
- Tests: `test_cfinite_lossless_and_coverage`. Fold/sympy path untouched (triangular still CLOSED).
- Honesty: O(log n) is *ring operations*; wall-clock includes bignum-multiply cost, so the measured
  ratio (not "thousands of x") is what's reported, with n stated. CLOSED is issued only after the
  exact-equality check — a mis-extracted recurrence would fail it, never a false CLOSED.

---

## STAGE 2.1 — structural proof cache [SPEED · lossless-decision] — DONE

`proof_cache.py`: caches the Z3 verdict keyed on a canonical α-renamed form of the ∀-goal (+ per-var
types + sorted assumptions). Sound because `prove_forall` proves a universally-closed statement,
invariant under consistent variable renaming; the per-var type guards Int-vs-Real aliasing.

- **Lossless: 0/N mismatches** — every cache hit is re-solved fresh in `measure_cache` and asserted
  equal (claim verified, not just argued).
- **Hit rate** on a reuse workload (repeats + α-renamed equivalents): **0.60**.
- **Wall-clock speedup is honestly conditional:** on *expensive* nonlinear-int proofs (~45ms each),
  cached **2.3×** (0.244s→0.107s). On *trivial* proofs, ~**0.9×** (keying overhead ≈ solve time) — the
  cache helps only when per-proof solve time ≫ keying. Both numbers measured and reported.
- Test: `test_proof_cache_lossless_and_hits`.

---

## STAGE 1.2 — incremental SMT / solver reuse [SPEED · decision-identical] — DONE

`incremental_smt.py`: assert the shared assumption prefix once into one Z3 solver, then push/¬goal/
check/pop per goal (reusing learned clauses), vs a fresh solver per goal.

- **Decision-identical:** 0 disagreements vs fresh solving (verified per-goal, incl. a REFUTED case so
  it's clearly not vacuously proving everything). Test: `test_incremental_smt_decision_identical`.
- **Fair A/B (20 linear goals over an 18-fact shared prefix, both strategies decide every goal):
  incremental 0.017s vs fresh 0.068s = 3.97× faster.**
- **Honest caveat (the "find the slow cases" ask):** the win comes from not re-asserting the shared
  prefix; it shrinks toward 1× when the prefix is small or per-goal solving dominates. Separately,
  on a *nonlinear* workload the fresh path hit Z3's 5s timeout on several goals while the reused
  solver resolved them — this inflates the raw ratio to ~1600×, but that is a **timeout artifact**
  (UNKNOWN-vs-PROVEN, Z3-version-dependent), **not** a fair clause-reuse speedup, so it is *not* the
  headline number. The honest, fair figure is ~4× on this shared-prefix workload.

---

## STAGE 1.1 — prompt caching [SPEED · lossless] — IMPLEMENTED (measurement needs key)

`claude_agent._build_kwargs` (extracted, pure, testable): the stable `system` prefix now carries
`cache_control:{ephemeral}`; the volatile per-round user prompt (with the counterexample) follows it,
so a write→verify→fix loop reuses the cached prefix. Verified shape: `thinking:{adaptive}` (the only
on-mode for Opus 4.8), no removed params (`budget_tokens`/`temperature` would 400). Test:
`test_prompt_caching_request_shape`.

- **Honest limits:** (1) Anthropic caches a prefix only above the model minimum (~4096 tokens on Opus
  4.8); HARAN's default system prompt is smaller, so it silently won't cache until a large stable
  context is placed in the prefix. (2) TTFT / cost savings can only be **measured with a live key** →
  **[TBD: needs key]**. The code is correct and tested for shape; the runtime benefit is not claimed.

---

## Headline closure coverage (measured, representative 8-item corpus)

`closure_classifier.closure_ratio` on a mix (polynomial sums, geometric, linear recurrences,
data-dependent): **88% CLOSED, 12% NO_STRUCTURE (Ω(N), honestly recognized), 0% UNKNOWN, 0% false.**
The 3 recurrences (fib/pell/tribonacci) are CLOSED **only because of STAGE 3.1** — without the new
C-finite engine they were UNKNOWN, i.e. this corpus would have been **5/8 = 62%**. So 3.1 lifted
measured closure coverage **62% → 88%** here. Honest scope: this is coverage on a representative
corpus of arithmetic/recurrence code (HARAN's stated domain), not a claim about arbitrary programs;
the data-dependent summand is correctly **not** closed (Ω(N) information floor), never faked.

---

## Stages not completed — honest status (no fake progress)

- **STAGE 2.2 verifier-guided tree search — PARTIAL/BLOCKED.** The search scaffold (branch/backtrack
  with fold as an O(1) value-estimator for pruning) needs MULTIPLE candidate generations per node,
  which requires a live model; the mock provides one scripted sequence. Live convergence can't be
  measured without a key → not implemented rather than faked. fold-as-estimator primitive already
  exists (`closure_classifier.classify_fn`).
- **STAGE 2.3 piCoq parallel proof — BLOCKED.** No `coqc` in this environment (verified: not on PATH).
  Proof-level dependency tracking + parallel re-check can't run real Coq proofs here; a simulated-DAG
  scheduler would be theatre, not a measured Coq speedup, so it was not shipped.
- **STAGE 3.2 SMT portfolio — PARTIAL.** Only z3 is installed (cvc5 / Bitwuzla absent — verified).
  A multi-solver first-to-finish race needs ≥2 solvers; the sound sequential fallback (jeff→sympy→z3)
  already exists in `discharge_correctness`. Multi-solver portfolio is **[needs cvc5/bitwuzla install]**.
- **STAGE 3.4 RLVR post-training — BLOCKED.** No training infrastructure / base-model weights / GPU in
  this environment. The verifier already emits the pass/fail + anti-vacuity signal (STAGE 1.3 gate) an
  RLVR reward would consume, but training itself cannot be run or measured here → not attempted.

---

## STAGE 0.1 follow-up — Claude request matched to spec (key-free), so it works when a key is added

Goal: make the live request 100% spec-conformant *without* a key, so adding a real key Just Works.
Method: a **dummy-key probe against the real public API** (`ANTHROPIC_BASE_URL=https://api.anthropic.com`,
verified) — a fake key returns **401 if the shape is accepted**, **400 if not**.

- **Line-by-line spec check (claude-api skill) + verified:**
  - model `claude-opus-4-8` — valid current id ✓
  - `thinking:{type:"adaptive"}` — the only on-mode for Opus 4.8 ✓ (SDK 0.109.2 knows `ThinkingConfigAdaptiveParam`)
  - `system` as a list block + `cache_control:{ephemeral}` ✓
  - `messages=[{role:user,...}]`, no assistant prefill ✓
  - **no** `temperature`/`top_p`/`top_k`/`budget_tokens` (all 400 on Opus 4.8) ✓
  - **Probe result:** current request → **401 (shape accepted)** for BOTH `create` and `stream`.
- **Honest limit of the probe:** auth is checked **before** body validation (a forbidden `temperature`
  *also* 401'd), so 401 proves parsing/routing/SDK-acceptance, **not** semantic param validity. Param
  400-freedom therefore rests on the **spec match** + an offline tripwire (below), not on the probe alone.
- **Robustness fixes (spec-aligned, key-free):**
  - default `max_tokens` 4096 → **16000** (skill's non-streaming default; less truncation; verified
    non-streaming-safe — SDK's streaming-required guard trips ~21–32k).
  - live path **auto-streams** when `max_tokens > 21000` (never hits the SDK's `ValueError`).
  - `_assert_spec_conformant(kwargs)` tripwire: rejects `temperature`/`top_p`/`top_k`, `budget_tokens`,
    bad `thinking.type`, prefill, bad `max_tokens`/`messages` — so a future edit can't silently 400.
    Test: `test_spec_conformance_tripwire` (8 400-causers all rejected).
- **`scripts/test_claude.py`** for the user's own live test: `--shape` (key-free 401 check) and the real
  call (reads `$HARAN_KEY`, one call, dropped). README updated with the exact commands.
- **Still honest:** a real **live success** can only be confirmed with a real key → **user's step**.

---

## Multi-provider router compatibility + UI fixes — DONE

**Routers/gateways (any of three via env, no code change):** new `provider.py` resolves non-secret
config (`HARAN_PROVIDER` ∈ anthropic|anthropic_compat|openai_compat, `HARAN_MODEL`, `HARAN_BASE_URL`);
`claude_agent.py` dispatches accordingly — Anthropic SDK (±custom base_url) or OpenAI SDK
(`/chat/completions`, system+user messages, OpenAI response parse). `claude_agent.py` stays **os-free**
(imports `provider` for config defaults only; the key is ALWAYS a per-call arg, never read from env
here). `server.py` adds an env-key fallback (`HARAN_KEY`) but the web-UI per-request key still wins.
`openai` added to requirements. `scripts/test_claude.py` is provider-aware (`--shape` + real call).

- **Verified (key-free):** provider resolution for all 3 modes (`test_provider_config_resolution`);
  OpenAI request shape (`test_openai_request_shape`); dispatch routing — `anthropic_compat`→Anthropic
  SDK→**401 shape-OK** at the real API, `openai_compat`→OpenAI SDK (reached HTTP). Mock + all prior
  paths unchanged. **13/13** `test_build` green.
- **Honest limit:** this build sandbox's egress allowlist permits only `api.anthropic.com`, so the
  `openai_compat` **live** 401 probe (openrouter.ai/api.openai.com) is **blocked here** — the request
  body is SDK-valid and routes correctly; live confirmation is the user's step (their env + key).

**UI fixes in `haran.html` (read in full to locate; visual confirm still the user's):**
- **2.1 asterisk/no-log popover invisible:** root cause `.chat{overflow:hidden}` clipped `.key-pop`
  (positioned ABOVE the key row via `bottom:100%`). Fix: `.chat{overflow:visible}` + round the
  composer's bottom corners so the card's rounded look is preserved. (If the report instead meant the
  `*` glyph itself, its CSS is present/visible — a screenshot would disambiguate.)
- **2.2 English comma→semicolon:** the English `hero` string used `;` where the Korean uses `,` (no
  systematic `replace()` — just that one string). Fixed to a comma (", and", matching the Korean
  conjunction). JS still passes `node --check`; server serves both fixes (curl-confirmed).

---

# v26 — machine-verified certificates (the differentiated axis)

Errata applied: **no PQC/ML-KEM/ML-DSA premise** anywhere (not in this codebase; KyberSlash cited only
as the *class example* of secret-dependent-division timing leaks). Build order S0→S1→…→S7.

## v26 S0 — runtime provider/model/baseURL selection — DONE
Threaded `provider`/`model`/`baseUrl` from the request body → `server` handlers → `intent.route`/
`classify`/`clarity`/`chat` + `agentic_code`/`agentic_stream` → `claude_generate` (existing
3-provider dispatch). UI: gateway dropdown (Claude/OpenRouter/DeepSeek/Mistral/GLM (Z.ai)/MiniMax/
Qwen/custom) + editable model & base_url + `sk-ant-` auto-detect; **GLM/Z.ai endpoint NOT guessed**
(blank + "verify with docs" note — honesty §1.2). Key stays per-request LEVEL-1; `claude_agent` still
`os`-free. VERIFIED: 14→15 tests; per-request `openai_compat` routes to the OpenAI path (egress-blocked
in sandbox, so the **live** call is the user's step); mock/Claude paths unchanged.

## v26 S1 — constant-time / secret-taint certifier (FLAGSHIP) — DONE
`ct_certifier.py`: HARAN-IR-level 2-safety taint analysis. A `secret`-labeled value (via `requires
secret(x)` or `secrets={...}`) that reaches (a) a `match` branch, (b) an index-style call, (c) a `/`/`%`
op, or (d) a fold trip-count → **CT_VIOLATION** with the exact line + a concrete fix; otherwise
**CT_PROVEN**. Unmodeled construct → **UNMODELED** (never a false PROVEN); no labels → **NO_SECRETS**.
`ct_feedback()` turns a leak into a precise loop fix instruction.
- **Measured (general corpus, no PQC):** CT_PROVEN for safe code incl. a **public-branch** case
  (false-positive guard); all 4 leak classes (branch / var_time_op / mem_index / secret_loop_bound)
  → CT_VIOLATION with correct kind+line; NO_SECRETS when unlabeled. **0 false positives.**
- **Honesty:** certificate states **"HARAN-IR level; binary-level NOT covered"** (compilers can inject
  leaks — Binsec/Rel). OX (verification) labeled; this is *not* a binary-CT claim.
- Test: `test_ct_certifier_proves_and_refutes`. Measurement anchor: Binsec/Rel (338 crypto impls).

## v26 S2–S7 — NOT built this session (honest; each is substantial, no fake stubs)
Per §1 (가짜 통과 0) I did **not** ship shallow stubs claiming sound IFDS / incorrectness-logic / race /
assume-guarantee / model-checking. Honest scope for each (NEXT, real work):
- **S2 taint/IFDS injection-freedom** — needs an IFDS/IDE solver over a call-graph + source/sink/sanitizer
  models. (S1's taint engine is a partial foundation.)
- **S3 incorrectness logic (UX)** — under-approximate symbolic execution; must label NO_BUG_FOUND ≠ proof.
- **S4 race/deadlock** — happens-before/vector-clock or RacerD-style; needs a concurrency model extractor.
- **S5 assume-guarantee + bi-abduction + opaque runtime-contracts** — the big compositional engine; ties
  to `spec_infer.py`; conditional/assumption-ledger certificates (never "whole-system proof").
- **S6 TLA+/model-checking + linearizability** — needs a TLC/Porcupine bridge (bounded; NP-complete).
- **S7 fold-kernel expansion** — `cfinite.py` (C-finite) already lands; holonomic/hypergeometric/FFT/
  Toeplitz remain, each with a collapse-soundness certificate + honest DECLINE on non-structure.
