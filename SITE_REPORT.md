# MR.JEFFREY — Site Build Report

The complete web app, built in one pass: a **FastAPI back end wired to the real `pillar3` engine** and a
**React + TypeScript + Vite front end** with all six screens. The full flow works end to end — paste code →
pick a mode → pick a provider + enter a key → run → watch the verification panel → see the corpus proof.

Everything the UI shows is a **measured whole-program** number from the actual engine: it carries the hotspot
fraction `f`, the Amdahl ceiling `1/(1−f)`, and a grade from the real ADT, and the measured ratio is `≤`
ceiling **by construction**. No hand-written numbers. No invented wins.

---

## How to run it locally

```bash
# 1) back end (serves the API and, if built, the React app at /app)
cd Projectharan
python3 -m uvicorn webapi.app:app --port 8000
#   → http://127.0.0.1:8000/        landing (works with or without the React build)
#   → http://127.0.0.1:8000/app/    the full React app (after the build below)
#   → http://127.0.0.1:8000/api/... the JSON API

# 2) front end — production build (already committed under web/dist, so this is optional)
cd web
npm install        # ~67 packages; node_modules is gitignored
npm run build      # → web/dist, which uvicorn auto-serves at /app

# 2b) front end — live dev with hot reload (proxies /api → :8000)
npm run dev        # → http://127.0.0.1:5173/app/
```

The dev server proxies `/api` to `127.0.0.1:8000`, so the same relative API client works in dev and prod.

---

## What's built

### Back end — `webapi/` (VERIFIED against the real engine)

Named `webapi/` (not `server/`) on purpose: the repo already has a tracked `server.py` (HARAN's backend with
`stream_events`) that the test suite imports; a `server/` package directory would shadow it. `webapi/` keeps
the MR.JEFFREY API a clean, separate module and leaves the existing suite green.

| File | Role |
|---|---|
| `webapi/app.py` | FastAPI app, CORS open, serves `web/dist` at `/app` (falls back to `mrjeffrey_landing.html` at `/`). |
| `webapi/engine_bridge.py` | The bridge to the **real** `pillar3` engine — every number originates here. |
| `webapi/__init__.py` | Package marker. |

Endpoints — all return live engine output:

| Method · Path | Source of truth | What it returns |
|---|---|---|
| `GET /api/health` | — | liveness |
| `GET /api/modes` | `pillar3.mode.ModePolicy` | the three mode **contracts** (verifier tier, detector count, acceptable grades, hotspot cap, stop condition) |
| `GET /api/providers` | `provider.VALID_PROVIDERS` | the 5 providers + transport + key env var |
| `POST /api/optimize` | `pillar3.engine.optimize` over `pillar3.canonical` | **real AST detection** of waste in *your* pasted source, then the engine's measured verified result per detected waste class under the chosen mode |
| `POST /api/key/validate` | `pillar3.proposer.build_request` | confirms the provider request is well-formed and the key is **headers-only**; live round-trip is honestly tagged UNVERIFIED |
| `GET /api/corpus` | `pillar3.corpus_runner.run_corpus` | 5 real archetypal repos, each graded, ratio ≤ ceiling, with honest DECLINEs |
| `GET /api/demo` | `pillar3_studio_gen.build` | per-mode canonical runs + corpus panel rows (the studio data) |

**Verified end to end this build** (served via uvicorn on :8000):

- `/api/optimize` on an N+1 sample detects `n_plus_1` and ships `S2_n_plus_1` **EXACT** in all three modes,
  measured `3.76–4.24×` against ceilings `4.80–4.91×` — **ratio ≤ ceiling on every row**.
- Clean code (`return sum(prices)`) → **honest empty result**, no shipped, no declined, a dignified note.
- `/api/corpus` → grades `{exact: 1, probabilistic: 3, decline: 1}`; `template_render` **DECLINEs** (ratio
  ~1.005×); every other row's measured ratio is ≤ its ceiling.
- `/api/key/validate` → `key_in_headers_only: true` for a dummy key (never echoed, never logged).

### Front end — `web/` (VERIFIED: builds clean, served, type-checks)

React 18 + TypeScript 5 + Vite 5. `npm run build` → 42 modules, `dist/index.html` + hashed JS/CSS;
`tsc --noEmit` exits clean. Served and confirmed at `/app/` (HTTP 200 on index + both assets).

| File | Role |
|---|---|
| `web/src/App.tsx` | screen state machine + stepper top bar; holds the session (mode, provider, key, code, result) in **tab memory only** |
| `web/src/api.ts` | typed client; relative `/api` paths (dev proxy + prod same-origin) |
| `web/src/types.ts` | types mirroring the exact engine output shape |
| `web/src/styles.css` | the `/design` system as tokens (white canvas, mode accents, grade colors, weight-500 headings, mono numbers, motion restraint, dark mode) |
| `web/src/components/VerificationRow.tsx` | **the signature element**: a meter whose fill (ratio) can never pass the wall (ceiling) |
| `web/src/components/ModeCard.tsx` | a mode rendered as its contract |
| `web/src/screens/*` | the six screens (below) |
| `web/src/icons.tsx`, `samples.ts` | inline icons; sample snippets that light up real detectors |

**The six screens:**

1. **Landing** — what it is and why a verifier (not the model) decides; live mode summary from `/api/demo`.
2. **Mode select** — the three modes as **contracts**; picking one recolors the whole app's accent (fast=cyan,
   normal=amber, extend=violet) from `/api/modes`.
3. **Provider + key** — 5 providers from `/api/providers`; paste a key, “validate request shape” hits
   `/api/key/validate`; the key stays in this tab. Skippable (verified detectors run with no key).
4. **Code input + run** — paste a function (or a sample), `POST /api/optimize` under the chosen mode.
5. **Verification panel** — cumulative whole-program ratio, z3 calls, sweep, latency, what was detected, and
   the shipped/declined rows drawn with ceiling walls and enforced grade chips.
6. **Corpus / proof** — `/api/corpus` on five real repos, grade tally, honest DECLINE shown as “no claim”.

---

## Honesty, encoded

- **Keys:** held in React state (tab memory) only — never `localStorage`, never logged client-side, never in
  a URL. Server-side the key is used solely to build the provider request and is never logged or persisted.
  It only ever travels to the provider you choose. **Phone-home = 0.**
- **Amdahl:** every row shows `f` and its ceiling; the meter fill is clamped behind the ceiling wall, so a row
  *cannot* render a claim larger than its ceiling.
- **Grades:** `exact` / `probabilistic` / `decline`, colored by the design system; a DECLINE renders as “no
  claim”, not a hidden failure.
- **Proposer ≠ arbiter:** the LLM only proposes; the verifier decides. The UI says so on the provider screen.
- **No false averages:** we never claim 50–100×. The corpus’s large ratios are genuinely quadratic code on
  large inputs (high `f` → high ceiling), with the ceiling shown next to every number.

---

## VERIFIED / UNVERIFIED / BLOCKED

| Item | Status |
|---|---|
| Back end serves real engine output on all 7 endpoints | **VERIFIED** (smoke-tested on :8000) |
| `ratio ≤ ceiling` on optimize + corpus rows | **VERIFIED** |
| Honest empty/DECLINE paths | **VERIFIED** |
| React app builds + type-checks + is served at `/app` | **VERIFIED** |
| Python regression suite (`test_build.py`) | **VERIFIED — see commit message for count** |
| Live LLM provider round-trip (real key over the network) | **UNVERIFIED [toolchain]** — no outbound provider call in this sandbox; the request is built and shape-checked, and this is labeled as such in the UI |

Nothing is faked to look passing. The one thing we can't do here — a live provider call — is the one thing
the UI explicitly tags UNVERIFIED.
