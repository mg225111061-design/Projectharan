# DEPLOY NOTES — MR.JEFFREY (Docker / Render)

## TL;DR for the Render dashboard
The repo is a **Docker** deploy. The fix is in code (committed) — once Render rebuilds from this branch the site
serves the new Korean single-file UI. Confirm these in **Render → Settings**, then **Manual Deploy → Deploy latest commit**:

| Setting | Value |
|---|---|
| **Root Directory** | empty / `.` (the `Dockerfile` is at the repo root) |
| **Dockerfile path** | `./Dockerfile` |
| **Docker Command** | leave EMPTY (use the Dockerfile `CMD`). If forced, set: `python server.py` |
| **Branch** | `claude/funny-maxwell-im9x07` |
| Port | automatic — the app binds Render's injected `$PORT` (no value needed) |

Then: **Manual Deploy → Clear build cache & deploy** (clearing the cache avoids serving a stale old-UI layer).

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

## Deploy status
`[deploy: pushed, awaiting Render rebuild]` — code is committed + pushed to `claude/funny-maxwell-im9x07`. The live
site updates when the user **redeploys** (Manual Deploy → Clear build cache & deploy) after confirming Root
Directory `.` + Dockerfile `./Dockerfile`. Not claimed live until the user redeploys — the route/CMD are verified
locally; the Render rebuild is the user's action.

## Honesty / design
Design unchanged — only *which file is served at `/`* (+ the engine routes + port). Korean via system fonts (no
webfont). Keys session-only, never logged/stored/committed.
