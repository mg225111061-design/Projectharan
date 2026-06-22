# DEPLOY NOTES — MR.JEFFREY front end

## What serves the live UI

The deployed site's UI is the single self-contained build **`mrjeffrey.html`** (Korean, `lang="ko"`,
design unchanged). It is served by the FastAPI app `webapi/app.py` at **three routes, all the same new build**:

| Route       | Serves                          |
|-------------|---------------------------------|
| `/`         | `mrjeffrey.html` (site root)    |
| `/app`      | `mrjeffrey.html`                |
| `/onefile`  | `mrjeffrey.html`                |
| `/legacy`   | old React build `web/dist/` (reference only — NOT the root) |
| `/api/*`    | the real pillar3 engine (health, modes, providers, corpus, demo, optimize, key/validate) |

Previously `/` served `web/dist/index.html` (the **old** React UI) or `mrjeffrey_landing.html`, which is why
the deployed site showed the old design. `webapi/app.py` now points `/`, `/app`, `/onefile` at the new
single-file build via `_serve_ui()`, and mounts the legacy React build at `/legacy` for reference only.

## Live mode

When served behind FastAPI, the page calls `GET /api/health` on load; on `{ok:true}` it flips to **live mode**
and routes paste→run through the real engine: `POST /api/optimize`, `POST /api/key/validate`,
`GET /api/modes|providers|corpus|demo`. Opened as a `file://` it stays in honest **static mode** (heuristic
detection + the embedded real measured canonical run, clearly labelled).

## End-to-end verification (sandbox, `uvicorn webapi.app:app --port 8077`)

- `GET /api/health` → `{ok:true, engine:"pillar3", real:true}`.
- `GET /` → **200**, `lang="ko"`, Korean H1 present ("추측이 아니라, 증명된 속도."), single-file (`const DATA` + `#root`),
  **1794 Hangul codepoints** (was 71). `/app` and `/onefile` return the identical build.
- `GET /api/modes|providers|corpus|demo` → **200**, real shapes.
- `POST /api/optimize` (N+1-in-a-loop sample), fast/normal/extend → **200**, each ships a measured
  `EXACT` row `S2_n_plus_1` (~3.9–4.1×), **ratio ≤ ceiling on every row**; cumulative ~4×.
- Clean code (`def total(prices): return sum(prices)`), extend → **0 shipped, 0 false claims** (honest DECLINE/no-op).
- Single-file harness: both `<script>` blocks parse; all 6 screens render without throwing; mode color switch
  (fast=cyan / normal=amber / extend=violet) intact; no banned English UI strings remain.

## Host deploy status

`[deploy: pushed, awaiting host rebuild]` — the route wiring + localized build are committed and pushed to
`claude/funny-maxwell-im9x07`. The actual Render/Netlify rebuild is triggered by the host on push and **could
not be triggered or verified from this sandbox**. Render start command (dashboard-configured) should be:

```
uvicorn webapi.app:app --host 0.0.0.0 --port $PORT
```

Once the host rebuilds from this branch, the site root will serve the new Korean single-file UI in live mode.
(No `render.yaml`/`Procfile` is present in the repo; the start command lives in the host dashboard.)

## Honesty / design

- Visual design **unchanged** — only copy, Korean localization, and deployment wiring changed.
- Korean fonts via the **system stack** (`Apple SD Gothic Neo`, `Malgun Gothic`, `Noto Sans KR`, `Pretendard`) —
  **no webfont request** (phone-home = 0 except the chosen provider's API).
- API key remains **session-only**: held in the tab for the request, never logged, stored, committed, or phoned home.
- Grade tokens render in Korean for display (증명됨 / 확률적 / 보류) while the CSS class keeps the English token for colour.
