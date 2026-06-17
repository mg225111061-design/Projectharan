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
