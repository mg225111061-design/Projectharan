# SECURITY_AUDIT — PART 1 (JEFF philosophy: zero holes, not "almost safe")

Security work-mode audit of THIS build (the §MRJ provider wiring + §SEC search toggle + the surrounding
request path). Method per the directive: **fold/grep is used for SCANNING completeness** (find every key
touch-point, every external-input path — miss none, not for speed) — **security logic is written by hand**
(no fold-generated security logic, which would mass-propagate one mistake). A checklist item passes only when
**every** touch-point across the whole repo passes (grep-wide), not "this one function looks safe". Any
ambiguous/unverified item ⇒ DECLINE (not passed). precision 1.0 = 100% or not at all.

> ★ Sandbox honesty: this environment egress-blocks provider domains, so live calls are NOT verified here.
> Code is ready; the author tests live on Render. No false "verified-live" claim.

## STEP 1 — classification (conservative: any touch ⇒ security work)
This build touches **keys/auth (provider headers, session keys), external input (the prompt, uploaded files,
the search toggle flag), and network boundaries (provider egress)** ⇒ classified SECURITY WORK ⇒ the full
checklist below applies. (Not borderline — it squarely touches keys + network.)

## STEP 2 — fixed checklist, applied to EVERY touch-point (grep-wide)

### A. Keys / secrets
| # | Check | Verdict | Evidence (grep-wide) |
|---|---|---|---|
| A1 | No key in code/git/logs/responses/errors | ✅ | `grep -rnE '(AIza…|sk-…|xai-…|gsk_…|sk-or-v1-…)'` over `*.py/*.html/*.ts/*.tsx/*.json` → **0** real keys; only explicitly-fake fixtures (`sk-ant-FAKEKEY…`, dummy-key egress probes). |
| A2 | Keys read ONLY from env or the request | ✅ | `provider.resolve_key*` reads env (`HARAN_KEY`/vendor) only; web path passes the key per-request. No hardcoded key, no key default, no key in a comment. |
| A3 | Key MASKED at every output point (print/log/return/exception) | ✅ | `claude_agent.redact_key` (sk-/sk-ant- → `sk-***`), `engine_bridge._mask_key` (→ `AIza***`/`gsk_***`), `_friendly_error` runs redact first. `_classify`/`health_provider` return `key_masked` only. grep of print/log lines containing "key" → all prose labels or dummy-key probes, **no real key value printed**. |
| A4 | `.gitignore` has `.env` + `*.key` | ✅ | `.env`, `.env.*`, `*.key`, `*.pem` present. |
| A5 | Key never in URL/query/body (header only) | ✅ | `test_mrj_provider_wiring` asserts, for **every** provider, the key is absent from the request URL and JSON body — only in the auth header. `/health/provider` GET refuses a key in the query (env key only — a key in a URL would land in access logs). |
| A6 | `claude_agent.py` os-import-0 (engine isolation intact) | ✅ | `grep '^import os' claude_agent.py` → none. The family-routing dispatch fix added no `os` import — the key is still only ever a function argument, dropped after one call. |

### B. External input
| # | Check | Verdict | Evidence |
|---|---|---|---|
| B1 | Uploaded files validated (type/size/name) | ✅ | `frontend/files.py:55` rejects `".." in name`, `startswith("/")`, `"\x00"` (path-traversal/null), allow-listed types, size cap. |
| B2 | No unsafe deserialization | ✅ | `grep 'pickle.loads|yaml.load(|shell=True|os.system'` → **0** in the request path. |
| B3 | `eval`/`exec` accounted for (no raw external-string injection) | ✅ (noted) | Hits are: z3 `model.eval` / sympy `Poly.eval` (not Python eval); `pillar3/parteval.py` eval with `__builtins__` stripped on the engine's OWN emitted AST; `swebench/harness.py` exec of candidate code in the **test** harness; `runtime.py`/`properties.py` exec of HARAN-**generated** source — the product's core (generate→verify→run), effect-gated (§AQ `effect_gate`, §AS taint), NOT arbitrary user strings. No request handler `eval`s a raw user string. |
| B4 | Search toggle flag validated | ✅ | `search_gate.normalize` coerces the flag; anything not clearly truthy ⇒ **OFF** (fail-safe — ambiguity → the more restrictive state). |

### C. Boundaries
| # | Check | Verdict | Evidence |
|---|---|---|---|
| C1 | Provider auth headers correct per family | ✅ | Anthropic `x-api-key`+`anthropic-version` (NOT Bearer); Gemini `x-goog-api-key`; family-C `Authorization: Bearer`. Asserted in `test_mrj_provider_wiring`. |
| C2 | Errors expose no internals (stack/path/key) | ✅ | server handlers return `{"error":true,"message": f"{type(e).__name__}: {redact_key(str(e))}"}` — type + redacted message, **no traceback**; SSE error emits `오류: {type}` only. `_classify` hints are author-actionable, key-free. |
| C3 | Egress: only what's needed | ✅ | One outbound host per request (the chosen provider). Sandbox egress-blocks them → honest `error_class:"network"` (not faked). |
| C4 | Search egress (when wired) inherits the boundary | ✅ (gate) | No search backend wired yet; `search_gate` OFF ⇒ tool not exposed (0 egress). When the author wires a real search backend on Render it rides the same egress + input-validation + no-key rules. |

## STEP 3 — red-team (actively hunt the leak path; prove "looked, found none")
- "Find a key printed/logged unmasked" → grep of all print/log lines with key/secret/token → only prose labels + dummy-key probes. **No leak path found.**
- "Find a key in a URL/body" → `test_mrj_provider_wiring` checks every provider → key header-only. **None.**
- "Find a key echoed in an error/response" → redact_key on all error text; `_classify`/`health_provider` return masked only. **None.**
- "Find unsafe deserialization / shell injection" → no `pickle.loads`/`yaml.load`/`shell=True`/`os.system`. **None.**
- "Find a path-traversal in file upload" → `frontend/files.py` rejects `..`/`/`/null. **Blocked.**
Result: no leak path found ⇒ STEP 4 gate passes for the audited surface.

## STEP 4 — gate
All checklist items ✅ (B3 ✅ with the by-design note above). No item is "almost" — each is grep-wide.
`claude_agent.py` os-import-0 intact; existing GLM/provider regression 0; `test_build` 274/0; `test_catalog`
+`test_sec_search_gate` (OFF⇒0 tools structural guarantee). **fold/grep used for scanning only; all security
logic (masking, validation, gating) is hand-written.**

### Deferred / out-of-scope (honest)
- Live provider calls + live search execution: UNVERIFIED here (sandbox egress block) — author tests on Render.
- The React bundle (`web/dist`) toggle: the data-driven `mrjeffrey.html` toggle ships now; the React `web/src`
  search toggle needs `npm run build` by the author (noted, not silently skipped).
