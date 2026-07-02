# DEPLOY NOTES — MR.JEFFREY (Docker / Render)

## TL;DR for the Render dashboard
The repo is a **Docker** deploy. The fix is in code (committed) — once Render rebuilds from this branch the site
serves the new Korean single-file UI. Confirm these in **Render → Settings**, then **Manual Deploy → Deploy latest commit**:

| Setting | Value |
|---|---|
| **Root Directory** | empty / `.` (the `Dockerfile` is at the repo root) |
| **Dockerfile path** | `./Dockerfile` |
| **Service type** | **Web Service → Docker** (NOT a Static Site — a Static Site cannot run Python; see ⚠️ below) |
| **Docker Command** | leave EMPTY (use the Dockerfile `CMD = uvicorn server:app --host 0.0.0.0 --port $PORT`). If forced, set exactly that, or `python server.py` (equivalent). |
| **Branch** | `claude/charming-brahmagupta-q4wwgh` ← **point Render here** (the confirmed superset of all prior work; carries the new CODE⇄MATH toggle + MATH engine) |
| Port | automatic — the app binds Render's injected `$PORT` (no value needed) |

Then: **Manual Deploy → Clear build cache & deploy** (clearing the cache avoids serving a stale old-UI layer).

## ⚠️ If MATH shows 「보류 — 정적 빌드 / 라이브 엔진 없음」 — the Python backend is NOT running
**Symptom (live site):** switch to MATH, enter a problem → "보류 — 정직한 무주장", ENGINE: "라이브 엔진 없음 — 정적
빌드에서는 정직하게 보류", note: "정적 빌드 — … server:app으로 서빙하면 실제로 증명·계산합니다." Routing works
(`top_mode=MATH · 첫 수: fold`), but `fetch('/api/math/solve')` can't reach a live engine, so the UI **honestly**
falls back to DECLINE instead of fabricating an answer. **The fallback is correct — the fix is to make the backend
reachable, NOT to change MATH.** Root cause = the served process is not the uvicorn backend. Almost always one of:
1. **Render service type is a *Static Site*.** It serves files only and **CANNOT run Python**, so `server:app`
   (fold/arsenal/broth) never boots and every `/api/*` 404s. ➜ The service **MUST be a *Web Service* (Docker)**:
   Root `.`, Dockerfile `./Dockerfile`, Branch `claude/charming-brahmagupta-q4wwgh`. There is no other way to run
   the engine — a Static Site is the one configuration that produces exactly this symptom.
2. **A missing runtime dep crashed the backend.** The image now installs **numpy** (and pydantic explicitly) in
   `requirements.txt`; the CODE engine + several MATH numeric kernels import numpy at runtime. Full served runtime
   set: `fastapi, uvicorn, pydantic, numpy, sympy, z3-solver` (the grade ADT + NATIVE-CORE are stdlib-only per the
   §5 audit, but the *served* engine paths need these).
3. **A separate static build shadowing uvicorn.** There is NO static build in this repo (no npm/web/dist); the
   single-file UI is served by `server:app` itself, which serves BOTH `/` and `/api/*` from one process. Remove any
   static publish dir you added.

### Verified locally (the SAME command the image runs)
`uvicorn server:app --host 0.0.0.0 --port 10000` (≡ `python server.py`):
- `GET /health` → **200**; `GET /` → the Korean UI (`MR.JEFFREY`).
- `POST /api/math/solve {"problem":{"sum":"k**3"},"mode":"extend"}` → **EXACT**, `answer = n²(n+1)²/4` (=(Σk)²) with
  a certificate — the LIVE engine; the response contains **no** "정적 빌드" / "라이브 엔진 없음" string.
- `POST /api/math/solve {"problem":{"sum":"k**10"},"mode":"extend"}` → **EXACT** Faulhaber closed form (instant).
- `POST /api/optimize` (CODE) → **200**; unstructured input → honest **live** DECLINE (not the static fallback).
- Docker image build itself: **UNVERIFIED [no docker in sandbox]** — the CMD target (`server:app`) is verified
  directly, which is exactly what the image runs.

> **Branch change:** earlier notes pointed at `claude/funny-maxwell-im9x07`. Development now lives on
> `claude/charming-brahmagupta-q4wwgh` (a superset of that branch + the MATH ascent and the new UI). Repoint
> Render's **Branch** setting to `claude/charming-brahmagupta-q4wwgh` so the mode toggle / MATH surface go live.

## What was actually wrong (the `/static/design.css` smoking gun)
- The Render service runs **Docker**. The root `Dockerfile`'s last line is `CMD ["python", "server.py"]` — so the
  production ASGI app is **`server:app`** (NOT `webapi.app:app`, which my earlier edit had touched — that app
  was never the one Render boots).
- Old `server.py`: `GET /` returned the **old React landing** (`pages/landing.html`) and `GET /app` the old
  `haran.html`; `GET /static/{name}` served `static/design.css` + `static/site.js`. The new single-file UI inlines
  everything and never requests `/static/...`, so those log lines proved the **old `server:app` root** was live.
- The Dockerfile does **NOT** build the old React app (there is no `npm`/`web/dist` build step); the old UI came
  purely from `server.py`'s `/` route. So the fix is in `server.py` + a Dockerfile clarification — no build step to remove.

## The fix (committed on this branch)
1. **`server.py`** — the real production entrypoint (`server:app`, run by the Dockerfile CMD):
   - `GET /`, `GET /app`, `GET /onefile` now return the **new Korean single-file `mrjeffrey.html`** (everything
     inlined; NO `/static/design.css`, NO `/static/site.js`, NO `web/dist`). The old landing/`haran.html` routes are gone.
   - Added the engine API the new UI calls for **live mode**: `GET /api/health|modes|providers|corpus|demo`,
     `POST /api/optimize`, `POST /api/key/validate` — delegating to `webapi.engine_bridge` (the real pillar3 engine).
     The submitted LLM key is body-only, never logged or stored; it only travels to the chosen provider.
   - Binds `$PORT` (Render) → `HARAN_PORT` → `8000`, host `0.0.0.0`.
   - `GET /static/{name}` is left as a harmless legacy asset route — the new `/` never references it.
2. **`Dockerfile`** — leaves `HARAN_PORT` unset so the container binds Render's `$PORT`; `EXPOSE 8000 10000`;
   `CMD ["python", "server.py"]` documented as serving the new single-file at `/`. `.dockerignore` does NOT
   exclude `mrjeffrey.html`, so it is in the image (`COPY . .`).

## End-to-end verification (local, the SAME app the Docker CMD runs)
Ran `python server.py` exactly as the Docker `CMD` does, with `PORT=8091` (simulating Render's injection,
`HARAN_PORT` unset):
- App bound `$PORT=8091`; `GET /api/health` → `{ok:true, engine:"pillar3", real:true}`.
- `GET /` → **200**, **1794 Hangul**, Korean H1 ("추측이 아니라, 증명된 속도."), single-file (`const DATA` + `#root`),
  and **does NOT reference `/static/design.css`, `/static/site.js`, or `web/dist`** — the exact broken symptom is gone.
- `GET /app`, `GET /onefile` → identical new UI.
- `GET /api/modes|providers|corpus|demo` → 200, real shapes.
- `POST /api/optimize` (N+1 sample), fast/normal/extend → 200, each ships a measured row, **ratio ≤ ceiling**,
  cumulative ≈ 4×, with **Korean** notes; clean code → honest no-claim.

Docker image build itself: **UNVERIFIED [no docker in sandbox]** — could not run `docker build`. The CMD's target
app (`server:app` via `python server.py`) is verified directly, which is what the image runs.

## NEW (MATH ascent + §B UI): the CODE ⇄ MATH mode toggle
The single-file UI now has a **second top-level mode**. A prominent segmented toggle (`코드` ⇄ `수학`) in the
top bar re-themes (a green MATH accent via `data-top="math"`) and re-routes the whole app:
- **CODE** → the existing wizard (paste code → `/api/optimize` → graded verified speedup).
- **MATH** → a fold-first solving surface (enter a problem / pick a sample → **`POST /api/math/solve`** → the
  visible, grade-tagged certified derivation). Backed by `mathmode.solver` (fold → broth → the 10-family arsenal).
- The **fast/normal/extend** sub-selector is preserved INSIDE each mode (OMEGA §B): MATH `extend` is
  EXACT-or-DECLINE; `fast`/`normal` accept PROBABILISTIC.
- New endpoints on `server:app`: `POST /api/math/solve` `{text|problem, mode}` → `{status, grade_ko, answer,
  certificate, reasoning[]}`; and **`POST /api/math/ingest`** `{filename, content_b64}` → file analysis (B2):
  detect → safely extract (archives, B3) → fold-accelerated analysis, JSON-safe. The MATH problem screen has a
  **drag-drop + file picker** (xlsx/docx/pptx/csv/images/zip/tar). Archives are unpacked in-memory with zip-slip
  + decompression-bomb defenses; PDF/images/7z/rar ⇒ honest UNVERIFIED. A 300 MB boundary guard on uploads.

Local verification (the SAME `server:app` the Docker CMD runs): `POST /api/math/solve {"text":"sum: k**2"}` →
`200 EXACT`, closed form `n(2n²+3n+1)/6`, certificate `broth_lookup_pra_recheck`; a Monte-Carlo problem in
`extend` → `DECLINE` (the §B floor). The served `/` HTML carries the toggle markup (node DOM-stub smoke test
renders both surfaces without error). Suite green 189/189.

## Deploy status
`[deploy: pushed, awaiting host rebuild]` — code is committed + pushed to `claude/charming-brahmagupta-q4wwgh`.
The live site updates when the user **redeploys** (Manual Deploy → Clear build cache & deploy) AFTER repointing
the Render **Branch** to `claude/charming-brahmagupta-q4wwgh` and confirming Root Directory `.` + Dockerfile
`./Dockerfile`. Not claimed live until the user redeploys — the route/CMD + the new `/api/math/solve` are verified
locally; the Render rebuild (and the branch repoint) is the user's dashboard action.

## Honesty / design
Design unchanged — only *which file is served at `/`* (+ the engine routes + port). Korean via system fonts (no
webfont). Keys session-only, never logged/stored/committed.
