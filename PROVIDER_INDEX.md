# PROVIDER_INDEX — MR.JEFFREY multi-provider wiring status (§1)

Index of the existing provider dispatcher **before** completing the 12-provider wiring. Goal: the author picks
any provider on Render (env var or UI session field), pastes a key, throws a fold → it runs on **that** provider.

> ★ Sandbox honesty: this build environment **egress-blocks** most provider domains, so live calls cannot be
> verified here. Code + push only; the author tests live on Render. No false "verified" claims.

## The three auth families (`provider.py :: transport_kind`)
| family | transport | auth header | endpoint |
|---|---|---|---|
| A | `anthropic_sdk` | `x-api-key` + `anthropic-version: 2023-06-01` | `/v1/messages` |
| B | `gemini_generate` | `x-goog-api-key` | `…/v1beta/models/<model>:generateContent` |
| C | `openai_chat` | `Authorization: Bearer` | `{base}/chat/completions` |

The real HTTP wire-shape for all three already exists and is correct in
`webapi/engine_bridge.py :: _provider_request` (key lives ONLY in the request header).
`engine_bridge.validate_key` already makes a real 1-token test call and `_classify` already distinguishes
200 / egress-blocked / invalid-key.

## Two registries existed, OUT OF SYNC (the gap)
| registry | scope | problem |
|---|---|---|
| `frontend/providers.py :: REGISTRY` | **14 providers** (all 12 + 2 compat gateways) with correct transport/base_url/model/key-label/get-key | display-only — its `validate_key_wiring` is a *stub* ("pending-real-stack"), NOT wired to the real HTTP path |
| `provider.py :: VALID_PROVIDERS` + `engine_bridge` | only **6** (anthropic, anthropic_compat, openai, openai_compat, gemini, groq) | the REAL HTTP/validate path; base_url read from **env only**, so a named family-C provider (Mistral, …) couldn't be selected & tested |

## Per-provider status (before → after this build)
| provider | family | base_url | default model | before | after |
|---|---|---|---|---|---|
| Claude (official) | A | `https://api.anthropic.com` | latest Claude | ✅ wired | ✅ |
| Claude-compatible gateway | A | author base | latest Claude | ✅ wired | ✅ |
| ChatGPT (OpenAI) | C | `https://api.openai.com/v1` | gpt-4o | ✅ wired | ✅ |
| Gemini (Google) | B | `…/v1beta` (native) | latest Gemini | ✅ wired (native generateContent) | ✅ (+ OpenAI-compat path in SDK generate) |
| Groq | C | `https://api.groq.com/openai/v1` | llama-3.3-70b-versatile | ✅ wired | ✅ |
| Mistral | C | `https://api.mistral.ai/v1` | mistral-large-latest | ⚠ display-only | ✅ now first-class |
| Cohere | C | `https://api.cohere.ai/compatibility/v1` | command-r-plus | ⚠ display-only | ✅ now first-class |
| DeepSeek | C | `https://api.deepseek.com/v1` | deepseek-chat | ⚠ preset only | ✅ now first-class |
| Grok (xAI) | C | `https://api.x.ai/v1` | grok-2-latest | ⚠ display-only | ✅ now first-class |
| Together AI | C | `https://api.together.xyz/v1` | meta-llama/Llama-3.3-70B-Instruct-Turbo | ⚠ display-only | ✅ now first-class |
| Fireworks AI | C | `https://api.fireworks.ai/inference/v1` | accounts/fireworks/models/llama-v3p3-70b-instruct | ⚠ display-only | ✅ now first-class |
| OpenRouter | C | `https://openrouter.ai/api/v1` | openai/gpt-4o | ⚠ preset only | ✅ now first-class |
| Perplexity | C | `https://api.perplexity.ai` | sonar | ⚠ display-only | ✅ now first-class |
| OpenAI-compatible gateway | C | author base | author model | ✅ generic | ✅ |

## Fix applied (this build)
1. **`provider.py`** — unify the registry: all 12 named providers + 2 compat gateways are now first-class ids in
   `VALID_PROVIDERS`, each with its `transport_kind` (family), default `base_url` (env-overridable via
   `HARAN_BASE_URL`), default model, free-no-card flag, and get-key URL. So `engine_bridge.validate_key(id, …)`
   and `_provider_request(id, …)` compute the correct wire shape for **every** provider with no UI bundle change.
2. **`claude_agent.py`** — the SDK generate path now dispatches by family (anthropic-family → Anthropic SDK;
   everything else → the OpenAI-compatible `/chat/completions` SDK path; Gemini routed via its OpenAI-compatible
   `…/v1beta/openai` endpoint). No `os` import added — the engine stays LEVEL-1 (key never read from env here).
3. **`engine_bridge.py`** — `_classify` now maps status → an author-actionable **hint** (401 key / 403 permission
   / **404 model-name, NOT key** / 429 quota / network), key always masked; new `health_provider()` for the
   `/health/provider` diagnostic.
4. **`server.py`** — `GET /health/provider` (reads the Render env config, masks the key, makes the small ping).
5. **`.gitignore`** — `*.key` added (`.env` already present). `claude_agent.py` `os`-import-0 confirmed intact.

★ Keys never appear in code/git/logs/responses — only Render env vars or the UI session field; always masked.
