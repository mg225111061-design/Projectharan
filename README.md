# MR.JEFFREY — verified conversational coding (web app)

Claude writes the code; **MR.JEFFREY proves it** (Z3 / fold / Coq), fixes it from real counterexamples,
and mathematically optimizes it — and you keep instructing. Chat, intent classification, live progress,
two themes (black ↔ white), and a level-1 API-key policy (entered each time, **stored nowhere**).

This is the **clean web-app repo** — only the ~33 modules the app actually needs (traced from
`server.py`), extracted from the full HARAN engine.

## Run it (localhost — works immediately)
```
pip install -r requirements.txt        # fastapi, uvicorn, anthropic, sympy, z3-solver
python server.py                       # → http://localhost:8000   (env: HARAN_HOST / HARAN_PORT)
# or:  docker compose up
```
Open `http://localhost:8000`, optionally paste your Claude API key, and start typing.
- **No key →** everything runs as a labeled **SIM** (the flow works offline).
- **With a key →** real Claude generation + MR.JEFFREY verification (live stages, `LIVE` tag).

## Verify the live Claude call (with your key)
The request is matched to the current Anthropic spec: model **`claude-opus-4-8`**, **adaptive thinking**
(`thinking:{type:"adaptive"}` — the only on-mode for Opus 4.8), `system` prefix with `cache_control`,
`max_tokens=16000` (non-streaming-safe; auto-streams above ~21k). It carries **no** `temperature` /
`top_p` / `top_k` / `budget_tokens` and **no** assistant prefill — all of which return HTTP 400 on
Opus 4.8. An offline tripwire (`claude_agent._assert_spec_conformant`) fails the build if any of those
ever reappear.
```
# key-free shape check — sends a DUMMY key to the public API; 401 ⇒ the shape is accepted:
python3 scripts/test_claude.py --shape

# real call — uses YOUR key for exactly one request, then drops it (never stored/logged):
export HARAN_KEY=sk-ant-...
python3 scripts/test_claude.py        # prints LIVE OK + token usage + a snippet, or a redacted error
python server.py                      # then use the app live at http://localhost:8000
```
> Note (honest): the `--shape` probe proves the request parses/routes and is rejected *only* for the
> key (401) — auth is checked before body validation, so it does not by itself prove every body param;
> param-level 400-freedom is guaranteed by the spec match + the tripwire above. A real **live** call
> can only be confirmed with a real key (the line above) — that step is yours.

## Make this a standalone GitHub repo (4 commands)
This folder is self-contained. Create the repo on github.com (or `gh repo create mrjeffrey-web --private`),
then from inside `haran-web/`:
```
git init && git add . && git commit -m "MR.JEFFREY web app"
git branch -M main
git remote add origin https://github.com/<you>/mrjeffrey-web.git
git push -u origin main
```
(The build environment's GitHub integration can't create repos for you — `403 not accessible by
integration` — so this one step is yours; everything else is done.)

## Deploy (your account; commands are exact, nothing guessed)
The same image deploys unchanged. Two common options:

**Google Cloud Run**
```
gcloud run deploy mrjeffrey --source . --port 8000 --allow-unauthenticated --region us-central1
```
**Render** — push this repo to GitHub, then "New → Web Service", Docker env, port `8000`
(or add a `render.yaml`). No API key is set as an env var — users enter it in the UI.

> The Claude API key is **never** an env var, image layer, file, or log — it is entered per request
> in the browser. Friends/teammates each paste their own key.

## ★ Key security — LEVEL 1 (no-log, no-store) ★
The key is entered every request, used for exactly one Claude call, and dropped. It is **never** written
to env / file / log / cache / DB / localStorage, never echoed, never in the image. `claude_agent.py`
doesn't even `import os`. The UI masks the key (●●●●) and a `*` next to the field explains the policy.
Verified by grep across the whole repo (see the project's honesty checks).

## What's auto-verified vs. needs your eyes
- **Auto-verified:** dependency closure (clean repo runs standalone), intent/route logic, real progress
  stages, key never stored (grep), error redaction, front↔back contract. Inline JS via `node --check`.
- **Needs you:** the actual look & feel (themes, gradients, masking display, popover), and **running it
  live with your own key** (`pip install anthropic` + network). A public deploy URL needs your cloud
  account — the commands above are exact.

Coding answers are verified (PROVEN / counterexample labels); chat answers are plain (no verification
label). Marketing copy is tagged in source; unmeasured figures are `[TBD: 측정필요]`.
