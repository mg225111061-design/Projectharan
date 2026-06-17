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
