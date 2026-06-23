# PHASE U (v62) — MR.JEFFREY Studio: mode + provider + key UI, panel on real engine data

The product surface: paste code, pick a mode, pick a provider, enter a key, run write→verify→fix, and watch the
verification panel — all bound to **real engine output**.

## Delivered
- `pillar3_studio_gen.py` — serialises everything the UI binds to, from the real engine: the three **mode
  contracts** (straight from `ModePolicy`), the five **providers** (from `provider.py`, with transports), a real
  **canonical run through each mode** (shipped/declined/ratio/z3_calls/latency), and the **verification-panel
  rows from the real corpus**. No hand-edited numbers; the API key is never part of this data.
- `pillar3_studio.html` — the studio UI:
  - **Mode picker** — three cards showing each contract (primary clock, verifier tier, detector count, hotspot
    cap, sweep, latency budget, risk posture, **grade floor**). Selecting a mode shows that mode's real run.
  - **Provider picker** — Claude / ChatGPT / Gemini / OpenAI-compatible / Claude-compatible, each with its wire
    transport.
  - **API-key field** — `type="password"`, **session-only** (held in one JS variable for the request),
    **never logged, never stored** (no `localStorage`/`console.log`/cookie), validate-button stubbed
    `[BLOCKED: no network]`.
  - **Verification panel** — the corpus rows with grade badges, measured whole-program ratios, hotspot
    fractions and Amdahl ceilings.

## Tested (data binding == engine output)
- The displayed **mode contracts match `ModePolicy` exactly** (MICRO/CHEAP_CERT/FULL_CERT, 10/18/30 detectors,
  extend = EXACT-or-DECLINE) — a fabricated contract would fail the build.
- The **providers match `provider.py`** (all five, native ChatGPT + Gemini included) with the correct transport.
- The runs are coherent and mode-distinct (fast z3=0, extend EXACT-only + swept, every shipped row ratio ≤
  ceiling); the panel is the real corpus (grades EXACT/PROBABILISTIC/DECLINE).
- ★ **Key safety:** no key in the data; the HTML never logs, stores, or cookies the key. ★

## Honest scope
The full React+TS studio with **live provider calls** and CI visual/a11y/perf gates needs a frontend toolchain
+ network absent in this sandbox `[BLOCKED: toolchain]`. This is a self-contained artifact whose **data binding
is real and tested**; visual quality goes to **human review**. 127 tests, 0 regression.
