# TESTENV_INDEX — §BE browser-offload + isolation + fold test environment (§2 pre-build index)

★ Honest goal (§0): we are **not** making Render's weak free-tier CPU fast — it can't be. We **remove the
bottleneck**: push heavy *execution* to the user's browser (their laptop/phone beats Render), kill cold-start with
keep-alive, recompute nothing (cache), and fold the *check* to O(1). NOT "quantum"/"magic speed" (banned — a
classical CPU runs a quantum sim *slower*; proven by plateau). Clever offload + isolation + fold, nothing else.

★ Role split: **execution = browser (Pyodide/WASM, isolated)** · **check = server (fold, O(1))**. The two are
separate ⇒ the weak CPU only orchestrates (LLM call + grade), and user code structurally cannot reach our server.

## Already built (reuse — re-build 0)
| part | location | role in §BE |
|---|---|---|
| **fold check layer (CHECK O(1))** | `checker/` (CHK-1..6, §BD) — `checker.grade_and_fix.check(src)` | TE-3 server-side fold check: loop semantics O(1), grade EXACT/CHECKED/FLAGGED/DEFER |
| fold engine (loop → closed form) | `loop_decision.decide_sum_collapse`, `mathmode/fold.py` | the O(1) core behind CHK-4 |
| effect classifier | `extract/classify/effect_gate.py` | CHK-1 purity/io/nondet/opaque |
| **result caching (recompute 0)** | `pillar3/detectors2.py :: detect_interproc_memoize`, `accel/verified_io.verified_cache` | TE-5 same code/request ⇒ cached grade (content-hash) |
| **`/health` endpoint** | `server.py @app.get("/health")` (line ~345) + `/api/health` | TE-4 keep-alive ping target (UptimeRobot/cron-job.org) |
| **static file serving (suffix allow-list)** | `server.py @app.get("/static/{name}")` — `_STATIC_TYPES` already maps `.js → application/javascript` | TE-1/2 serve `runner.worker.js` + `sandbox_guard.js` with **zero** server changes |
| SSE streaming (perceived-instant) | `server.py stream_events` + `/api/stream` (UI fetch-reader) | TE-5 streaming already shipped — tokens render as they arrive |
| existing UI + run anchor | `mrjeffrey.html` — `.codeblock` render (~line 405-409), `$` DOM helper, `S.live` via `/api/health` | TE-1 the "▶ run in browser" button + grade badge + output attach here |
| key isolation discipline | keys ONLY in server env / request header, never logged, always masked (§MRJ) | TE-2 the run payload sent to the browser carries **only `{code}`** — never a key/session |

## net-new (this build) — NO new mechanism, NO new disposer, NO new math
- `static/runner.worker.js` (TE-1) — Pyodide (WASM Python) **inside a Web Worker**; loads once, reused; runs user
  code; returns `{ok, stdout, value, error}`. ★Worker = DOM/main-thread isolation (an infinite loop can't freeze
  the page). ★Pyodide = structural server isolation (WASM browser sandbox — cannot reach our server).
- `static/sandbox_guard.js` (TE-2, the security heart) — main-thread guard around the worker:
  ★timeout → `worker.terminate()` (kills the infinite loop) · ★network disabled inside the worker (no
  `fetch`/`XMLHttpRequest`/`WebSocket`/`importScripts` after load) · ★best-effort memory watch → terminate ·
  ★payload to the browser is **code-only** (key/session never leave the server) · ★returned output is *untrusted*
  ⇒ size-capped + rendered as text (XSS-safe).
- `server.py` — `GET /warmup` (preload z3/fold/numpy once so the first real request is instant) + `POST /api/check`
  (run the §BD checker layer over the LLM-generated code → return the grade; **reuses `checker.grade_and_fix`**,
  no new logic) + a content-hash check-cache (recompute 0).
- `mrjeffrey.html` — load Pyodide from CDN; "▶ 브라우저에서 실행" button → `sandbox_guard.runUserCode(code)`; show
  the server fold-check grade badge **before** running; render the sanitized browser output below the code.

## Honesty (§4)
- **"Render fast" is false** — the hardware is weak. We remove bottlenecks (execution→browser, wait→keep-alive,
  recompute→cache, check→fold O(1)). No magic.
- **"quantum" / "ultra-speed" banned** — a classical CPU runs a quantum sim *slower*. Offload + isolation + fold only.
- **Isolation is sacred** — user code may be malicious. Pyodide structural isolation (can't reach our server) +
  Worker (DOM isolation) + timeout (kills infinite loops) + network-block + key-0 payload + untrusted-result
  sanitize. Drop one layer ⇒ a threat. (Honest caveat: a hard per-worker *memory* cap is not portably available in
  browsers — we rely on timeout + output-size cap + the structural sandbox, and say so; no overclaim.)
- **fold = O(1) check completeness** — loop semantics closed to a formula (the §BD principle). NOT "know without
  looking" (reading is O(N)).
- **precision 1.0 invariant** — the check is conservative; false-EXACT 0 (the §BD checker rides existing certs).
- **★Sandbox blocks the Pyodide CDN + provider domains here** ⇒ the browser execution path **cannot be live-verified
  in this container**. Code + push only; the author validates on Render. No false "verified" claim.
