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

## Use any API router / gateway (AgentRouter, OpenRouter, TokenMix, …)
HARAN talks to any common gateway via **three env vars** — no code change. The key is read per call and
dropped (`claude_agent.py` still never imports `os`); only non-secret config is read from the env.

| var | meaning | example |
|---|---|---|
| `HARAN_PROVIDER` | `anthropic` (default) · `anthropic_compat` · `openai_compat` | `openai_compat` |
| `HARAN_MODEL` | model id for that gateway | `qwen/qwen3-coder` |
| `HARAN_BASE_URL` | gateway base URL | `https://openrouter.ai/api/v1` |
| `HARAN_KEY` | your gateway key (masked, never stored) | `sk-…` |

**Official Anthropic (default — nothing extra to set):**
```
export HARAN_KEY=sk-ant-...            # HARAN_PROVIDER=anthropic, HARAN_MODEL=claude-opus-4-8 by default
```
**AgentRouter & other Anthropic-shaped gateways** (Anthropic SDK + custom base_url):
```
export HARAN_PROVIDER=anthropic_compat
export HARAN_BASE_URL=https://agentrouter.org/v1
export HARAN_MODEL=claude-opus-4-8
export HARAN_KEY=...
```
**OpenRouter / TokenMix & other OpenAI-shaped gateways** (OpenAI SDK, `/chat/completions`):
```
export HARAN_PROVIDER=openai_compat
export HARAN_BASE_URL=https://openrouter.ai/api/v1
export HARAN_MODEL=qwen/qwen3-coder        # or anthropic/claude-3.5-sonnet, etc.
export HARAN_KEY=...
```
**GLM (Z.ai)** — OpenAI-compatible (base_url + model id web-confirmed against Z.ai docs, June 2026):
```
export HARAN_PROVIDER=openai_compat
export HARAN_BASE_URL=https://api.z.ai/api/paas/v4/   # Z.ai OpenAI-compatible endpoint
export HARAN_MODEL=glm-4.6                            # or glm-4.7; use the exact id from your Z.ai console
export HARAN_KEY=...
```
> Honesty note: **"GLM-5.2" is not a verified model id** — Z.ai's documented ids are `glm-4.6`/`glm-4.7`.
> Use the exact id shown in your Z.ai console. (Z.ai coding-plan users: the OpenAI endpoint is
> `https://api.z.ai/api/coding/paas/v4`.)
Then (works for whichever provider you set):
```
python3 scripts/test_claude.py --shape   # key-free: confirm the request shape for the configured gateway
python3 scripts/test_claude.py           # one real call (uses HARAN_KEY)
python server.py                         # http://localhost:8000
```
> Verified: the `anthropic`/`anthropic_compat` request shape is accepted by the real Anthropic API
> (dummy-key → 401). The `openai_compat` request body is SDK-valid but its gateways
> (openrouter.ai etc.) were outside the build sandbox's network allowlist, so its **live** check is
> yours to run with your key. Anthropic-shaped requests keep the 400-safe body + tripwire; OpenAI-shaped
> requests use the OpenAI message format (where params like `temperature` are allowed).

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
(or add a `render.yaml`). On the **web-UI path** no API key is set as an env var — users enter it in the UI.

## ★ Key security — scoped precisely to each path ★
There are two deployment paths and the guarantee differs; we state each exactly (the marketing absolute must
never be broader than the code):

- **Web-UI path (the product surface).** Enter your key in the browser; it is held in the tab for that one
  request, **stored nowhere, logged nowhere, written to no env/file/cache/DB/localStorage, never in the image**,
  and **sent only to the provider you pick, for that request.** The request handler that makes the call
  (`claude_agent.py`) does not even `import os` (verified: `import os == 0`). The UI masks the key (●●●●).
- **Gateway / CLI path (self-host).** When you run HARAN as a gateway/CLI, it reads a **standard
  environment-variable key, `HARAN_KEY`** (see `provider.resolve_key()` — a server/CLI fallback only), used
  per call and dropped, masked in logs, never persisted beyond the process environment. This is an ordinary
  env-var secret like any server deployment — *not* the "never an env var" guarantee, which is the web-UI path.

So: **"the key is never an env var" is true on the web-UI per-request path; the gateway/CLI path uses the
standard `HARAN_KEY` env var.** Both keep the key out of logs/files/images and send it only to the provider.

## What's auto-verified vs. needs your eyes
- **Auto-verified:** dependency closure (clean repo runs standalone), intent/route logic, real progress
  stages, key never stored (grep), error redaction, front↔back contract. Inline JS via `node --check`.
- **Needs you:** the actual look & feel (themes, gradients, masking display, popover), and **running it
  live with your own key** (`pip install anthropic` + network). A public deploy URL needs your cloud
  account — the commands above are exact.

Coding answers are verified (PROVEN / counterexample labels); chat answers are plain (no verification
label). Marketing copy is tagged in source; unmeasured figures are `[TBD: 측정필요]`.
