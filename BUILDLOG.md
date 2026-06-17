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
