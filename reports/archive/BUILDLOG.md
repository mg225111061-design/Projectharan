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

---

## v26 S2–S7 — now BUILT (supersedes the earlier "NEXT" note). Each a sound, bounded core; no fake stubs.

Every checker is a genuine algorithm on a modeled/bounded input, emits a certificate (PASS) or a concrete
counterexample/witness, is honestly labeled, and is tested. Tests 16→21 (`test_s2…s7`).

- **S2 `taint_ifds.py`** — distributive taint reachability. source (`requires source(x)`/source-call) →
  sink (query/exec/eval/open…) without a sanitizer ⇒ INJECTION_FLOW (witness: sink+line+source); else
  INJECTION_FREE; no modeled source/sink ⇒ UNMODELED. Sound only w.r.t. modeled sets, intraprocedural (OX).
- **S3 `incorrectness.py`** — UX bug-existence. Z3 finds an input with `requires ∧ path ∧ denom=0` ⇒
  BUG_REACHABLE with a real witness (FP=0 by construction); path-sensitive (guarded divisions not
  reported). NO_BUG_FOUND is **not** a proof of absence (labeled).
- **S4 `race_detector.py`** — Eraser lockset + lock-order-cycle on an explicit thread/event model.
  Conflicting accesses w/ disjoint locksets ⇒ RACE (pair); acquire-while-held cycle ⇒ DEADLOCK; else
  RACE_FREE. Lock-model sound (may over-report like RacerD); cycle = necessary inversion warning.
- **S5 `assume_guarantee.py`** — modular A-G: each module verified (Z3) assuming callees' contracts;
  undischarged callee preconditions **bi-abduced** into the module's inferred pre; calls outside the
  system = **opaque boundaries** → runtime-monitored contract + blame. Emits a conditional/compositional
  **assumption-ledger certificate** (proven core / assumed contracts / opaque boundaries / residual TCB)
  — explicitly **NOT a whole-system proof**.
- **S6 `model_check_bridge.py` + `linearizability.py`** — BFS explicit-state model checker (MODEL_OK |
  counterexample trace | UNMODELED-when-bound-exceeded) + Wing-Gong linearizability search (LINEARIZABLE
  witness order | NOT_LINEARIZABLE). Bounded: state-explosion + NP-complete (labeled).
- **S7 `fold_kernels.py`** — unifies Faulhaber/Gosper/C-finite under a FOLDED/ABSENT/DECLINED certificate
  with an **independent numeric recheck** (closed form vs naive sum for several n) so a wrong form is
  **never emitted** (mismatch ⇒ DECLINE). Honest DECLINE on non-structure; ABSENT on Gosper-nonsummable
  (Σ1/k). Theorem limits: Richardson/Petkovšek ⇒ narrow class, frequent honest DECLINE is correct.

**State:** 8 new v26 modules (S1 ct_certifier + S2–S7), `test_build` **21/21 green**, all modules import.
**Honesty:** each verdict is OX (verification) or UX (bug-existence) labeled; every "proof" is conditional
on the modeled inputs / bounds / assumed contracts spelled out in its certificate. No single trophy number.

---

## v26.2 S8–S11 — live connection, runtime engine, mode allocation, first live test

- **S8 GLM/Z.ai preset (`provider.GATEWAY_PRESETS`)** — `openai_compat` + `https://api.z.ai/api/paas/v4/`
  + `glm-4.6` (base_url & model **web-confirmed** against Z.ai docs; **"GLM-5.2" is not a verified id** →
  not claimed). UI dropdown prefilled. The openai_compat request body is SDK-valid (built by
  `_build_openai_kwargs`); its **live** check is gated on egress (see S11).
- **S9 runtime engine (`layout_simd.py` + `parallel_algebra.py`)** — a 3-tier ceiling analyzer (A: provably
  parallel/vectorizable; B: ≤3×; C: physics floor) + a **differential-equivalence gate** (transformed
  output must equal the scalar reference on every sample — *never a wrong transform*). MEASURED: associative
  parallel reduction **~1.3–2.7× on 4 cores** (varies with the box), equivalence verified; non-associative
  ops **DECLINED**. SIMD/native is **[BLOCKED: no numpy/native backend]** here — classified tier-A but its
  speedup is honestly not measured (no fake number).
- **S10 mode allocation (`mode_policy.py`)** — declarative NORMAL/EXTENDED table (18 techniques × engine).
  NORMAL = cheap mathematics only, terminates before SMT; EXTENDED adds octagon/polyhedra, Gosper/FFT, Z3,
  Coq-∀, race-proved parallelism, deep SIMD, best-of-N 4–8. **Both modes zero-wrong-answer** (a mode is a
  depth dial, not a correctness knob); NORMAL ⊊ EXTENDED; the best-of-N **selector is a sound verifier only**
  (never a learned reward — reward-hacking, Stroebl arXiv:2411.17501). Wired: `agentic.MODE_BUDGET` IS
  `mode_policy.MODE_BUDGET`; `agentic_code` attaches the mode's gate list + best_of_n; `server` surfaces them.
- **S11 first live test (`scripts/s11_live_measure.py`)** — egress probed **empirically** (dummy-key POST):
  `api.anthropic.com` **reachable, spec body ACCEPTED** (401 invalid-key, *not* 400, with a real
  `request_id`); `api.z.ai` & `openrouter.ai` return the proxy's **`Host not in allowlist`** (egress block).
  No key present (LEVEL-1). ⇒ the **live LLM loop is [BLOCKED]** on (key) + (egress for non-Anthropic) —
  reported as such with the exact user procedure, **never faked as "측정됨"**. The **non-LLM half is MEASURED**
  (real wall-clock, with workloads):
    - write→verify→fix **loop convergence** over the mock corpus — *normal* (budget 2) solves **3/4**
      (honestly misses the 3-iteration task), *extended* (budget 5) solves **4/4** (iters {1:2, 2:1, 3:1}),
      **wrong = 0 in both** (zero-wrong-answer, measured);
    - runtime transform **~2× on 4 cores**, differential-equivalence verified;
    - **proof reuse** round-2 re-verify **cold ≈16 ms → warm ≈0.04 ms** (~hundreds×, *perceived-zero*),
      lossless (0 wrong verdicts).

**State:** +4 modules/scripts (S8 preset, S9 ×2, S10, S11 harness), `test_build` **25/25 green**.
**Two-axis honesty (accuracy vs latency/runtime):** verification accuracy is gated at **FP = 0** (spec-gate
false-positives 0, loop wrong = 0, transform mismatches 0); latency/runtime is **measured where runnable**
(loop ms, parallel speedup, re-verify perceived-zero) and **[BLOCKED / TBD: 측정필요]** where it needs a live
key or an egress host the sandbox lacks. No single trophy number; the differentiator is the machine-checked
certificate, not raw speed.

---

## v27 S12–S18 — "prove the structure to skip the work" (write · verify · runtime · replicate)

The thesis of v27: recognize provable structure and SKIP work — in writing (offload), verifying (reuse /
parallel), runtime (tiers), and replication (fold the process). Each stage is a *sound gate* — a certificate
or a concrete counterexample — built on the v26 core (no rewrites). Every action that could change an
answer is gated by execution or Z3, so a misclassification can only DECLINE, never emit a wrong result.

- **S12 `structure_recognizer.py`** — recognizes the algebra (monoid/lattice/semiring/fixpoint) + shape of a
  code piece and either OFFLOADs or does a CERTIFIED REWRITE, else honest NONE→LLM. Two sound actions:
  closed-form loop → fold-solver offload by *verified lifting* (differential-equivalence vs the original
  EXECUTED code; Σk→n(n+1)/2, Σk²→…); equi-join → hash-join rewrite, **MEASURED ~30–54× on two 3000-row
  relations** (pure Python). Product loops / glue → NONE (honest). Only the structured minority offloads (Ω(N)).
- **S13 `fold_replicate.py`** — prove a parametric template ONCE (Z3 ∀ over holes), certify N instances by a
  cheap per-instance side-condition check (sound universal instantiation). The solve is paid once, so the
  speedup **GROWS with N — measured 2.7× @24 → 20.4× @150** (the scale gap). NOT_A_TEMPLATE (refuted +cx),
  rejected bad instances, Merkle summary cache (re-run perceived-zero), <30%-repetition gate. Novel logic is
  Ω(K) (Amdahl-bounded, not instant); the parametric spec is supplied (auto-derivation is Rice-hard).
- **S14 `repo_partition.py`** — Fiedler/spectral bisection (pure-Python power iteration, deflated) + KL
  refinement cuts a dep-graph into balanced weakly-coupled chunks for parallelism. **Seed only, NOT a module-
  quality claim** (Shokoufandeh 2004). Verified: two triangles cut=1, K6 cut=9 (honest), 4-ring k=4 cut=4.
  >4000 nodes → [BLOCKED: pure-Python scale].
- **S15 `sbfl.py` + `diffusion_localize.py`** — bug funnel: SBFL (Ochiai/DStar/Op2/Tarantula, RANKED≠proof) →
  graph-Laplacian diffusion (heat = random walk = spectral, **shared L** — the real math, no entropy metaphor)
  → sound confirm (reuse S2/S3): VULN_PROVEN (witness, e.g. div-by-zero b=0) | ABSENCE_PROVEN (class+bounds) |
  RANKED. Rice-bounded; multi-fault degrades SBFL (honest).
- **S16 `typed_decoding.py` + `repo_rag.py`** — accuracy levers, ALL verifier-gated. Type-constrained decoding
  emits **100% well-typed by construction vs ~3% unconstrained** (measured, key-free); repo-RAG + the verified
  cache are PROPOSERS — every proposal must PASS the verifier or be rejected (unverified is never cached/used).
- **S17 `equality_saturation.py` + `ic3_pdr.py` + `tactic_hammer.py`** (EXTENDED depth) — e-graph saturation
  with **Z3-certified** extraction (x*2+x*3→5*x, wrong extraction UNSOUND_BLOCKED); unbounded safety by
  **k-induction** (IC3/PDR family: SAFE-invariant | UNSAFE+trace | UNKNOWN — full IC3 is the extension point);
  a portfolio **hammer** (heuristic order, NOT trained) auto-discharging **~60%** of a mixed corpus, the rest
  honest NOT_PROVED/UNKNOWN, proof reuse perceived-zero.
- **S18 `dogfood.py`** — HARAN re-verifies its own NON-KERNEL components by re-deriving each certificate with
  the trusted core (Z3 + differential), catching a forced wrong claim (no rubber-stamping). **Gödel discipline**:
  the SMT kernel / differential checker / certificate checker are the minimal, human-audited **residual TCB**,
  NEVER self-certified. iCoq-style incremental: only changed components re-verified.

**State:** +12 modules (S12–S18), `test_build` **32/32 green**. Build-env honesty held throughout: no numpy
(SIMD-proper [BLOCKED], parallel/join/eq-sat measured instead), egress allowlist (live-LLM levers [BLOCKED]),
pure-Python spectral scale-capped. Every multiple carries its workload; nothing measured is faked; the
differentiator remains the **machine-checked certificate**, and the gap to a frontier LLM **widens with scale**
(measured) by folding repeated structure — never an instant/uniform speedup (Ω(N), Ω(K), Rice).

---

## v28 S19–S25 — "insanely fast · ground huge inputs · keep integrity unbroken"

v27 laid the *capability*; v28 makes it (1) feel instant — without ever changing an answer, (2) GROUND huge
prompts/files (not "understand" — Rice), and (3) patch three integrity hazards. Speed-first, but the
**zero-wrong-answer invariant** (§1.12) holds: cache/parallel/early-exit may only be faster or honest-defer.

- **S19 `latency_budget.py`** — watchdog `run_with_budget` (daemon-thread timeout → DEFERRED, never hangs);
  cache economics (`is_stable_prefix` rejects volatile content, `pad_to_threshold` to the provider min,
  `CacheLedger` read 0.1×/write 1.25× → break-even ~2 calls); parallel orchestration (`schedule_waves`
  critical-path + process-pool `parallel_map`). MEASURED: watchdog defers an 80ms-budget stage in ~80ms
  (not 5s); cache **31% input-cost savings** after a 2-call warm; parallel verify **~2.4× / 4 workers** with
  results IDENTICAL to sequential. Live model-call latency is **[BLOCKED: key/egress]** (`scripts/test_claude.py`).
- **S20 `treesitter_frontend.py`** — fixes the regex-scanner soundness hole: a char-level state machine
  strips NESTED block comments and ignores markers inside strings (a nested Rust comment → fully stripped,
  vs the regex baseline leaving garbage; `//` in `"http://…"` preserved). Real Tree-sitter CST when
  `tree_sitter`+grammar present (verified with `tree_sitter_go`), pure-Python fallback otherwise (same
  soundness). Unparsed regions → `assume_unknown` (honest UNKNOWN, never fake PROVEN). Common IR + fact schema.
- **S21 `grounding_pipeline.py`** — large-prompt GROUNDING, not understanding (Rice). Structure + S14
  clustering + EXTRACTIVE summaries + **exact multi-hop graph retrieval** (no lost-in-the-middle by
  construction) + spec-extract-and-verify (GROUNDED proof / REFUTED witness / BEST_EFFORT label). MEASURED:
  multi-hop accuracy 100% vs hand-derived reachability, coverage 100%. LLM head-to-head **[BLOCKED: key]**.
- **S22 `file_ingest.py`** — format-routed ingestion → S21. stdlib formats (json/ipynb/csv/text/zip/tar)
  always extract; docx/xlsx via optional libs (work here); **pdf [BLOCKED]** (a broken `cryptography` rust
  backend panics — caught with `except BaseException` + fd-level stderr redirect), **image OCR [BLOCKED]** (no
  tesseract). BLOCKED/FAILED never fabricate text; confidence labeled.
- **S23 `proof_checker.py`** — soundness-bug defense: an independent **RUP/DRAT UNSAT checker** (re-verifies
  proofs, rejects bogus ones; TCB shrinks to the checker) + a **solver portfolio** (Z3 vs an independent
  bounded search; DEFER on disagreement — a single solver "true" never suffices) + **mapping-axiom
  metamorphic tests** (a flipped `−↦+` is caught).
- **S24 `concretization_gate.py`** — CEGAR: an abstract counterexample is RUN on the real runtime before any
  fix. A SPURIOUS cex against correct code → **NO_BUG, code untouched** (the key protection against
  hallucinated fixes); a real one → REAL_BUG; endless spurious → DEFER; a fix that breaks a passing test →
  ROLLBACK.
- **S25 `spec_propagation.py`** — proof bound to the semantic contract: an α-key (rename/move-invariant,
  constant/operator/spec-sensitive) makes a rename **PROPAGATE** (transport, no re-prove) while a real change
  → **REPROVE_NEEDED** (justified); Merkle-incremental (only changed contracts cost prover work); fail → DEFER.

**State:** +7 modules (S19–S25), `test_build` **39/39 green**. Optional deps (tree_sitter, python-docx,
openpyxl, pypdf) degrade to honest fallbacks/[BLOCKED] — correctness never depends on them. Speed claims
carry workloads; live-LLM latency/accuracy is **[BLOCKED: key/egress]** with a user procedure; the
zero-wrong-answer invariant is regression-tested (parallel == sequential). Three integrity hazards are
**mitigated, not eliminated** (TCB minimization, CEGAR filtering, incremental transport) — honestly bounded.

---

## v29 S26–S31 (+§4) — prompt-understanding front-end: break garbage-in-garbage-out

The user's premise — "prompt understanding is almost everything; a bad prompt shouldn't doom the result" —
is measurement-backed (Lost-in-the-Middle 30%+ loss; HumanEvalComm: 60%+ of code-LLMs silently emit code on
a bad prompt). v29 detects bad/odd/ambiguous prompts and **reasonably completes / rarely asks / flags
danger** — but it is GROUNDING not understanding (Rice), every detector is **fail-safe** (uncertain →
reasonable completion + stated assumption, never silent-wrong, never hard-block), and it **asks almost
never**. All detectors are deterministic (key-free, measured); LLM-based variants are **[BLOCKED: key/egress]**.

- **S26 `requirement_parser.py`** — prompt → typed slots {goals/constraints/IO/prohibitions/assumptions} by
  cue-phrase slot-filling; `is_well_formed` is the constrained-decoding guarantee; multi-part → least-to-most;
  cached. A measurable EXTRACTION proxy, NOT understanding; a vague prompt gets honest conf 0.0.
- **S27 `missing_info_detector.py`** — schema-coverage: COMPLETE / MINOR (reasonable default + stated
  assumption, no ask) / CRITICAL (→S30). Breaks silent-code-on-incomplete; completeness is schema-relative (Rice).
- **S28 `dangerous_instruction_detector.py`** — CWE danger lexicon (HEURISTIC → FLAG + alternative, never
  hard-block) + **Z3-UNSAT contradiction** (SOUND) + infeasibility catalog. Verified: verify=False→CWE-295,
  "timeout <10 ∧ >30"→sound contradiction, ">10 ∧ <30"→SAFE (no false positive). Breaks GIGO.
- **S29 `ambiguity_detector.py`** — DEFAULT reasonable completion + stated assumption (NEVER asks); only a
  costly/irreversible dimension left genuinely open → HIGH_STAKES_FORK (→S30). Conservative (ClariQ F1 ~0.37);
  semantic-entropy / multi-sample paths [BLOCKED: key].
- **S30 `clarification_policy.py`** — VoI-gated, ask RARELY/SMART/max-one: `ASK_ONE` iff high-stakes fork ∧
  not-detailed ∧ VoI>threshold; **a detailed prompt is NEVER asked** (hard gate); `AskRateMonitor` clamps the
  threshold if a detailed prompt is ever asked. Verified: sparse fork→ASK_ONE, detailed-fork→PROCEED,
  detailed-ask-rate 0.0.
- **S31 `prompt_consistency.py`** — Clover-for-prompts: stated constraint vs worked example, flag ONLY a sound
  numeric violation (**zero-FP**) → route S28/S29; entity grounding to symbols. Consistency ≠ intent (Rice).
- **§4 `prompt_frontend.py`** — the cascade + policy engine into one fail-safe decision (PROCEED / ASK_ONE /
  FLAG). **Additive (zero-wrong-answer)**: the prompt is preserved, downstream verifier correctness unchanged;
  detailed-ask-rate 0.0; cascade ~1.4ms (live model first-token [BLOCKED: key]).

**State:** +7 modules (S26–S31 + front-end), `test_build` **46/46 green**. Two axes kept separate: accuracy@FP0
(extraction proxy, sound contradiction/divergence, zero-FP consistency) vs latency (deterministic cascade,
measured ms). The downstream Pass@1 delta and live UX are **[BLOCKED: key/egress]** (user procedure). The
front-end **grounds, it does not "understand"** (Rice); it asks **almost never**; it never silently obeys a
bad instruction — and it never changes a correct answer.
