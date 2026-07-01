"""
HARAN v23 Part T — web backend (FastAPI wrapping the v22 agentic pipeline).
===========================================================================
Serves haran.html and exposes the agentic pipeline over HTTP:

  • T6  POST /api/generate        — JSON: {prompt, mode, apiKey?, history?} → agentic_code(...) result
  • T7  POST /api/stream          — SSE: token → code_done → verify → (fix) → done  (added in T7)
  • T8  history (conversation)    — threaded into agentic_code as context; incremental on follow-ups

★ KEY SECURITY — LEVEL 1 (server side) ★: the API key is read from the request body for exactly one
  call, passed to Claude, and dropped. It is NEVER stored (no env, file, cache, DB, global), NEVER
  logged, and NEVER echoed in a response or error (errors are redacted). Confirmed by test_web6.

Design: all logic lives in plain, dependency-free functions (handle_generate, to_result_dict,
parse_history) so it is testable WITHOUT FastAPI installed. create_app() lazily imports FastAPI and
wires the routes — so this module imports fine in any environment (mirrors claude_agent's SDK-less path).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

import agentic as AG
import auth as AU       # users/sessions/work persistence — NEVER touches the LLM key (LEVEL-1 stays in claude_agent)
import claude_agent as CA
import haran_cache as HC
import intent as IN
import provider as PV   # non-secret gateway config + env-key fallback (web UI key still takes priority)

SESSION_COOKIE = "mrj_session"

# Expose `Request` at MODULE scope so FastAPI can resolve the route handlers' string annotations
# (PEP 563 / `from __future__ import annotations` turns `req: Request` into the string "Request",
# which FastAPI resolves against this module's globals — not create_app's locals). Guarded so the
# module still imports when FastAPI isn't installed.
try:
    from fastapi import Request
except Exception:   # noqa: BLE001
    Request = None

HARAN_HTML = Path(__file__).with_name("haran.html")
ONEFILE = Path(__file__).with_name("mrjeffrey.html")          # the NEW Korean single-file UI (everything inlined)
BASE = Path(__file__).parent
STATIC = BASE / "static"
PAGES = BASE / "pages"
STATS_JSON = BASE / "benchmarks" / "stats.json"
_STATIC_TYPES = {".css": "text/css", ".js": "application/javascript", ".svg": "image/svg+xml"}

# ── intent-gap / scope honesty (rule 5) ─────────────────────────────────────────────────────────
# Whole-program requests can't be generated-from-nothing and verified (Rice). HARAN verifies small~
# medium code AGAINST A SPEC. Detect whole-program asks by their nouns and return an honest scope reply
# instead of fake-verifying. (Keyword-based — NOT length-based; long but tractable requests are fine.)
_SCOPE_RE = re.compile(r"백엔드|서버|backend|server|큐|queue|상태\s*머신|state\s*machine|"
                       r"\bapi\b|jwt|결제|payment", re.I)
SCOPE_MESSAGE = ("scope: HARAN verifies & optimizes small~medium code AGAINST A SPEC (Rice: full "
                 "generation from nothing is impossible). Provide the core logic + a spec (ensures).")


def is_scope(prompt: str) -> bool:
    return bool(_SCOPE_RE.search(prompt or ""))


def _scope_result(prompt: str, mode: str) -> dict:
    return {"request": prompt, "mode": mode, "source": "mock-sim", "scope": True, "converged": False,
            "status": "SCOPE", "code": None, "proof_tier": "(scope)", "optimization": None,
            "ms": 0.0, "history_len": 0, "trace": [], "message": SCOPE_MESSAGE}

# Module invariant: the key is NEVER stored here. Stays None for the process lifetime (test asserts it).
_KEY_STORE = None


def parse_history(raw) -> List[Tuple[str, str]]:
    """Accept history as a list of {request, code} dicts or [request, code] pairs → list of tuples."""
    out: List[Tuple[str, str]] = []
    if not raw:
        return out
    for item in raw:
        if isinstance(item, dict):
            req, code = item.get("request", ""), item.get("code", "")
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            req, code = item[0], item[1]
        else:
            continue
        if code:
            out.append((str(req), str(code)))
    return out


def _gen_cfg(p: dict):
    """v26 S0: per-request gateway selection from the body (NON-secret: provider/model/baseUrl).
    None → env defaults. The key is handled separately and never returned here."""
    return (p.get("provider") or None, p.get("model") or None, p.get("baseUrl") or None)


def to_result_dict(res: AG.AgenticResult) -> dict:
    """Serialize an AgenticResult to a JSON-able dict (never includes the key)."""
    opt = None
    if res.optimization is not None:
        o = res.optimization
        opt = {"optimized": o.optimized, "kind": o.kind, "method": o.method,
               "closed_form": o.closed_form, "speedup": o.speedup}
    trace = [{"iter": s.iteration, "mode": s.mode, "status": s.verdict.status,
              "counterexample": s.verdict.counterexample} for s in res.trace]
    return {"request": res.request, "mode": res.mode, "source": res.source,
            "converged": res.converged, "iters": res.iters, "status": res.status,
            "code": res.final_code, "proof_tier": res.proof_tier, "optimization": opt,
            "ms": round(res.ms, 2), "history_len": res.history_len, "trace": trace,
            "gates": res.gates, "best_of_n": list(res.best_of_n),   # S10: which mathematics this mode spent
            # ★ three clocks, labeled & never mixed ★ (A=LLM call, B=verification; C=fold from `optimization`)
            "clock_a_ms": getattr(res, "clock_a_ms", 0.0), "clock_b_ms": getattr(res, "clock_b_ms", 0.0)}


def handle_generate(payload: Optional[dict]) -> dict:
    """T6 core: run the agentic pipeline for one request. LEVEL-1 key — used once, dropped, never
    stored/logged/echoed. No key → labeled mock (v22). Errors return a redacted dict (never raise)."""
    p = payload or {}
    prompt = str(p.get("prompt", "")).strip()
    mode = p.get("mode", "normal")
    if not prompt:
        return {"error": True, "message": "empty prompt"}
    if is_scope(prompt):                         # intent-gap honesty: don't fake-verify a whole program
        return _scope_result(prompt, mode)
    history = parse_history(p.get("history"))
    api_key = p.get("apiKey") or PV.resolve_key()          # read locally only
    provider, model, base_url = _gen_cfg(p)
    try:
        res = AG.agentic_code(prompt, mode, api_key, history=history,
                              model=model or CA.DEFAULT_MODEL, provider=provider, base_url=base_url)
        return to_result_dict(res)
    except Exception as e:   # noqa: BLE001 — never leak the key in an error message
        return {"error": True, "message": f"{type(e).__name__}: {CA.redact_key(str(e))}"}
    finally:
        api_key = None       # drop our binding immediately (the client re-supplies per request)


# ---------------------------------------------------------------------------------------------------
# T7 — SSE streaming. The verification RESULTS are real (from agentic_code); the event sequence is
# emitted around them so the UI shows a live token→code_done→verify→(fix)→done flow. Hard cases emit a
# 'verifying' (⏳) status first, then resolve (v21 R5 background → non-blocking status; honest: here the
# pipeline is fast/synchronous, so 'verifying' frames the resolved result rather than truly deferring).
# ---------------------------------------------------------------------------------------------------

def sse_event(obj: dict) -> str:
    """One SSE message: a single JSON object on a `data:` line, terminated by a blank line."""
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


def _chunks(s: str, n: int = 16) -> List[str]:
    return [s[i:i + n] for i in range(0, len(s), n)] or [""]


def stream_events(payload: Optional[dict]) -> Iterator[str]:
    """T7/U5 core: route the message, then stream REAL progress stages + results over SSE. LEVEL-1 key
    (used once, dropped, never stored/logged/echoed). Each 'stage' is emitted only when that work runs:
      classify → (chat: thinking → chat) | (scope: note) | (vague: ask) | (code: generate → verify →
      [refuted → fix] → optimize → proven/optimized → done). Stages map 1:1 to the real pipeline."""
    p = payload or {}
    prompt = str(p.get("prompt", "")).strip()
    mode = p.get("mode", "normal")
    history = parse_history(p.get("history"))
    api_key = p.get("apiKey") or PV.resolve_key()
    provider, model, base_url = _gen_cfg(p)
    if not prompt:
        yield sse_event({"type": "error", "message": "empty prompt"})
        return
    import search_gate as SG                                              # PART 2: search toggle gate
    sa = p.get("searchAllowed", p.get("search_allowed"))
    try:
        yield sse_event({"type": "stage", "stage": "classify"})           # 분류중 (local, ~instant)
        # ★ deliver the toggle to the backend + make the structural gate observable: OFF ⇒ no search tool is
        # exposed (search impossible); ON ⇒ available but used only when needed. No search backend is wired yet
        # (egress-blocked) so this announces the gate, not an executed search — honest.
        yield sse_event({"type": "search", "allowed": SG.normalize(sa), "available": SG.search_available(sa),
                         "tools": [t["name"] for t in SG.tools_for(sa)]})
        it = IN.classify_intent(prompt, api_key, provider=provider, model=model, base_url=base_url)

        if it.intent != "CODING":                                          # chat / question
            yield sse_event({"type": "stage", "stage": "thinking"})        # 생각중
            cr = IN.chat_reply(prompt, api_key, history, provider=provider, model=model, base_url=base_url)
            yield sse_event({"type": "chat", "reply": cr.text})            # plain answer, NO verify label
            yield sse_event({"type": "done", "summary": {"kind": "chat", "verified": False,
                                                         "source": cr.source, "intent": it.intent}})
            return

        if IN.is_scope(prompt):                                            # whole-program → scope note
            yield sse_event({"type": "note", "text": IN.SCOPE_REPLY})
            yield sse_event({"type": "done", "summary": {"kind": "chat", "scope": True,
                                                         "verified": False, "source": "local"}})
            return

        if not p.get("force"):                                            # U7: 'proceed anyway' skips it
            clarity = IN.assess_clarity(prompt, api_key, provider=provider, model=model, base_url=base_url)
            if not clarity.clear:                                          # vague → expected questions
                yield sse_event({"type": "ask", "asks": clarity.asks})
                yield sse_event({"type": "done", "summary": {"kind": "ask", "asks": clarity.asks,
                                                             "verified": False, "source": clarity.source}})
                return

        # coding pipeline — emit each real stage as it runs
        for ev in AG.agentic_stream(prompt, mode, api_key, history=history,
                                    model=model or CA.DEFAULT_MODEL, provider=provider, base_url=base_url):
            st = ev["stage"]
            if st in ("generate", "fix", "verify", "optimize"):
                d = {"type": "stage", "stage": st}
                if "iter" in ev:
                    d["iter"] = ev["iter"]
                yield sse_event(d)
            elif st == "code_done":
                for chunk in _chunks(ev["code"]):
                    yield sse_event({"type": "token", "text": chunk})
                yield sse_event({"type": "code_done", "code": ev["code"]})
            elif st == "refuted":
                yield sse_event({"type": "verify", "status": "refuted",
                                 "counterexample": ev.get("counterexample")})
            elif st == "done":
                res = ev["result"]
                rd = to_result_dict(res)
                rd["kind"] = "code"
                yield sse_event({"type": "verify",
                                 "status": "proven" if res.proof_tier == "PROVEN" else "shallow",
                                 "tier": res.proof_tier})
                opt = rd["optimization"]
                if opt and opt["optimized"]:
                    yield sse_event({"type": "optimized", "closed_form": opt["closed_form"],
                                     "speedup": opt["speedup"]})
                yield sse_event({"type": "done", "summary": rd})
    except Exception as e:   # noqa: BLE001 — redact, never leak the key
        yield sse_event({"type": "error", "message": f"{type(e).__name__}: {CA.redact_key(str(e))}"})
    finally:
        api_key = None


# ---------------------------------------------------------------------------------------------------
# T8 — follow-up rounds: conversation history is threaded into agentic_code as context (handle_generate
# / stream_events already pass `history`); with a real key Claude reflects the prior code+instructions.
# Incremental re-verify (v21 R4): when a follow-up changes part of a codebase, ONLY the changed function
# (+ its dependents) re-verifies — so follow-up rounds are perceived-zero. Real measured speedup.
# ---------------------------------------------------------------------------------------------------

def handle_route(payload: Optional[dict]) -> dict:
    """U4: classify + route a message → kind-tagged JSON. CODING → verified pipeline (kind='code',
    carries proof labels); CHAT/QUESTION → plain reply (kind='chat', NO verification label); CODING but
    vague → expected questions (kind='ask'). LEVEL-1 key: used once, dropped, never stored/logged/echoed."""
    p = payload or {}
    text = str(p.get("prompt", "")).strip()
    mode = p.get("mode", "normal")
    history = parse_history(p.get("history"))
    api_key = p.get("apiKey") or PV.resolve_key()
    provider, model, base_url = _gen_cfg(p)
    if not text:
        return {"error": True, "message": "empty prompt"}
    import search_gate as SG                          # PART 2: search toggle gate (OFF ⇒ tool never exposed)
    sa = p.get("searchAllowed", p.get("search_allowed"))
    try:
        rr = IN.route(text, mode, api_key, history, force=bool(p.get("force")),
                      provider=provider, model=model, base_url=base_url)
        out = {"kind": rr.kind, "intent": rr.intent, "source": rr.source, "verified": rr.verified}
        if rr.kind == "code":
            out["result"] = to_result_dict(rr.code_result)
        elif rr.kind == "chat":
            out["reply"] = rr.reply                  # plain answer — NO verification label
        elif rr.kind == "ask":
            out["asks"] = rr.asks                    # expected questions (suggestions)
        # ★ the toggle's structural guarantee, observable on every reply: OFF ⇒ tools=[] (search impossible),
        # ON ⇒ the search tool is exposed but used only when needed (LLM-judged). No search backend is wired yet
        # (egress-blocked sandbox) so this reports the GATE, not an executed search — honest.
        out["search"] = {"allowed": SG.normalize(sa), "available": SG.search_available(sa),
                         "tools": [t["name"] for t in SG.tools_for(sa)]}
        return out
    except Exception as e:   # noqa: BLE001 — never leak the key
        return {"error": True, "message": f"{type(e).__name__}: {CA.redact_key(str(e))}"}
    finally:
        api_key = None


def reverify_incremental(prev_src: str, new_src: str) -> dict:
    """Re-verify a follow-up edit incrementally (v21 Merkle cache): returns which functions actually
    re-verified + measured timings/speedup. Unchanged functions are served from cache (not re-proved)."""
    m = HC.measure_edit_loop(prev_src, new_src)
    return {"reverified": m.reverified_after_edit,
            "cold_ms": round(m.cold_s * 1000, 2),
            "warm_one_edit_ms": round(m.warm_one_edit_s * 1000, 2),
            "speedup_one_edit": round(m.speedup_one_edit, 1),
            "speedup_unchanged": round(m.speedup_unchanged, 1)}


# ── §BE TE-3/4/5: server-side fold CHECK (O(1) loop semantics) + keep-alive warmup + recompute-0 cache ──────────
# Role split (§BE): EXECUTION is the browser's job (Pyodide/WASM, isolated — see static/runner.worker.js); the
# server only ORCHESTRATES + runs the cheap fold CHECK. These are plain functions (testable without FastAPI), and
# they REUSE the §BD checker layer — no new mechanism, no new disposer, no new math.
_CHECK_CACHE: dict = {}          # sha256(code) → result dict; the fastest check is the one we don't recompute
_CHECK_CACHE_MAX = 256


def run_fold_check(code: str) -> dict:
    """Run the §BD checker layer over LLM-generated code → an honest grade (EXACT/CHECKED/FLAGGED/DEFER) + located
    fix instructions. O(N) read + O(1) loop semantics (fold). Content-hash cached (recompute 0 on a repeat)."""
    if not isinstance(code, str) or not code.strip():
        return {"ok": False, "error": "no code to check"}
    key = hashlib.sha256(code.encode("utf-8")).hexdigest()
    if key in _CHECK_CACHE:
        out = dict(_CHECK_CACHE[key]); out["cached"] = True
        return out
    try:
        from checker.grade_and_fix import check as _check    # noqa: PLC0415 — lazy/guarded (mirrors _ENGINE)
        r = _check(code)
        out = {
            "ok": True,
            "grade": r.grade,                                 # EXACT | CHECKED | FLAGGED | DEFER
            "summary": r.summary,
            "effect": r.effect,
            "n_lines": r.n_lines,
            "findings": [{"line": f.line, "severity": f.severity, "pattern": f.pattern_id,
                          "message": f.message, "hint": f.hint} for f in r.findings],
            "fix_instructions": r.fix_instructions(),
            "cached": False,
        }
        # §BF FIX-7: a DEFER/declined grade is FEEDBACK, not a wall — attach WHY + an actionable hint (the
        # checker already computed the reason; we surface + categorize it). Never changes the grade.
        if r.grade == "DEFER":
            try:
                from diagnostics import categorize_decline   # noqa: PLC0415
                out["diagnosis"] = categorize_decline(r.summary)
            except Exception:                                 # noqa: BLE001 — diagnostics is best-effort feedback
                pass
    except Exception as e:                                    # noqa: BLE001 — checker must never crash the server
        return {"ok": False, "error": f"checker unavailable: {type(e).__name__}"}
    if len(_CHECK_CACHE) >= _CHECK_CACHE_MAX:
        _CHECK_CACHE.pop(next(iter(_CHECK_CACHE)))            # simple bounded FIFO
    _CHECK_CACHE[key] = out
    return out


def warmup_engines() -> dict:
    """TE-4: preload the heavy modules ONCE (z3/numpy/fold/checker) so the first real request after a cold start is
    instant. Render free-tier sleeps after ~15min; an external keep-alive ping to /health prevents the sleep, and
    /warmup pays the import/JIT cost ahead of the user. Best-effort — a missing optional module is skipped, not fatal."""
    warmed, skipped = [], []
    for name, thunk in (
        ("numpy", lambda: __import__("numpy")),
        ("z3", lambda: __import__("z3")),
        ("loop_decision", lambda: __import__("loop_decision")),
        ("checker", lambda: __import__("checker.grade_and_fix", fromlist=["check"])),
    ):
        try:
            thunk(); warmed.append(name)
        except Exception:                                     # noqa: BLE001 — optional; never fatal
            skipped.append(name)
    # touch the fold path once so its first real use is JIT-warm (tiny, deterministic)
    try:
        run_fold_check("def f(n):\n s=0\n for i in range(n):\n  s+=i\n return s")
        warmed.append("fold_check")
    except Exception:                                         # noqa: BLE001
        skipped.append("fold_check")
    return {"ok": True, "warmed": warmed, "skipped": skipped}


def _fastapi_available() -> bool:
    return importlib.util.find_spec("fastapi") is not None


def create_app():
    """Wire the FastAPI app (lazy import). Routes delegate to the dependency-free handlers above."""
    from fastapi import FastAPI, Request, Response              # noqa: PLC0415 (lazy by design)
    from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

    app = FastAPI(title="HARAN", docs_url=None, redoc_url=None)
    AU.init_db()                                               # idempotent: create tables if absent

    def _page(name: str) -> "HTMLResponse":
        f = PAGES / f"{name}.html"
        return HTMLResponse(f.read_text(encoding="utf-8")) if f.is_file() else HTMLResponse("not found", 404)

    def _set_session_cookie(resp, sess: dict, req) -> None:
        # httpOnly + SameSite=Lax + Secure(when https). "remember me" → Max-Age (persistent); else a
        # session cookie (no Max-Age → the browser drops it on close). The LLM key is NEVER a cookie.
        max_age = AU.PERSISTENT_DAYS * 86400 if sess.get("persistent") else None
        resp.set_cookie(SESSION_COOKIE, sess["cookie"], httponly=True, samesite="lax",
                        secure=(req.url.scheme == "https"), path="/", max_age=max_age)

    def _onefile() -> "HTMLResponse":
        # THE LIVE UI: the new Korean single-file (everything inlined — no /static/design.css, no /static/site.js)
        if ONEFILE.is_file():
            return HTMLResponse(ONEFILE.read_text(encoding="utf-8"))
        return HTMLResponse(HARAN_HTML.read_text(encoding="utf-8")) if HARAN_HTML.is_file() else HTMLResponse("not found", 404)

    # ---- pages ----
    # ★ ROOT serves the NEW single-file UI ★ (was: the old React landing + /static React build — that is GONE).
    @app.get("/", response_class=HTMLResponse)
    async def landing():                                       # noqa: ANN202
        return _onefile()

    @app.get("/app", response_class=HTMLResponse)
    async def app_page():                                      # noqa: ANN202
        return _onefile()

    @app.get("/onefile", response_class=HTMLResponse)
    async def onefile_page():                                  # noqa: ANN202
        return _onefile()

    @app.get("/login", response_class=HTMLResponse)
    async def login_page():                                    # noqa: ANN202
        return _page("login")

    @app.get("/signup", response_class=HTMLResponse)
    async def signup_page():                                   # noqa: ANN202
        return _page("signup")

    @app.get("/profile", response_class=HTMLResponse)
    async def profile_page():                                  # noqa: ANN202
        return _page("profile")

    @app.get("/health")                                        # deploy health check (Cloud Run/Render) + keep-alive ping
    async def health():                                        # noqa: ANN202
        return {"ok": True, "service": "mrjeffrey"}

    @app.get("/warmup")                                        # §BE TE-4: preload z3/numpy/fold/checker (kill cold-start)
    async def warmup():                                        # noqa: ANN202
        return JSONResponse(warmup_engines())

    # ---- auth API (no LLM key involved anywhere here) ----
    @app.post("/api/auth/signup")
    async def auth_signup(req: Request):                       # noqa: ANN202
        p = await req.json()
        return JSONResponse(AU.signup(p.get("email", ""), p.get("password", ""), p.get("nickname", "")))

    @app.post("/api/auth/login")
    async def auth_login(req: Request):                        # noqa: ANN202
        p = await req.json()
        res = AU.login(p.get("email", ""), p.get("password", ""), bool(p.get("remember")))
        if not res.get("ok"):
            return JSONResponse(res, status_code=401)
        r = JSONResponse({"ok": True, "persistent": res["persistent"]})
        _set_session_cookie(r, res, req)
        return r

    @app.post("/api/auth/logout")
    async def auth_logout(req: Request):                       # noqa: ANN202
        AU.logout(req.cookies.get(SESSION_COOKIE, ""))
        r = JSONResponse({"ok": True})
        r.delete_cookie(SESSION_COOKIE, path="/")
        return r

    @app.get("/api/auth/me")
    async def auth_me(req: Request):                           # noqa: ANN202
        return JSONResponse(AU.whoami(req.cookies.get(SESSION_COOKIE, "")))

    @app.post("/api/auth/profile")
    async def auth_profile(req: Request):                      # noqa: ANN202
        s = AU.verify_session(req.cookies.get(SESSION_COOKIE, ""))
        if not s:
            return JSONResponse({"ok": False, "message": "로그인이 필요합니다."}, status_code=401)
        p = await req.json()
        return JSONResponse(AU.update_profile(s["user_id"], nickname=p.get("nickname"),
                                              password=(p.get("password") or None)))

    @app.get("/api/work")
    async def api_work(req: Request):                          # noqa: ANN202
        s = AU.verify_session(req.cookies.get(SESSION_COOKIE, ""))
        if not s:
            return JSONResponse({"items": []}, status_code=401)
        return JSONResponse({"items": AU.list_work(s["user_id"])})

    # ---- the SPEEDUP ENGINE API (what the new single-file UI calls for LIVE mode) ----
    # Delegates to webapi.engine_bridge (the real pillar3 engine). The submitted LLM key is header/body-only and
    # is NEVER logged or stored here — it only travels to the provider the user chose.
    try:
        from webapi import engine_bridge as _ENGINE            # noqa: PLC0415
    except Exception:                                          # noqa: BLE001
        _ENGINE = None

    @app.get("/api/health")
    async def api_health():                                    # noqa: ANN202
        return JSONResponse({"ok": _ENGINE is not None, "engine": "pillar3", "real": _ENGINE is not None})

    @app.get("/api/modes")
    async def api_modes():                                     # noqa: ANN202
        return JSONResponse({"modes": _ENGINE.modes()} if _ENGINE else {"modes": []})

    @app.post("/api/check")                                    # §BE TE-3: server-side fold CHECK → honest grade
    async def api_check(req: Request):                         # noqa: ANN202
        # ★ code-only: never a key/session (keys live server-side; the browser run payload is code-only too).
        p = await req.json()
        return JSONResponse(run_fold_check(p.get("code", "")))

    @app.get("/api/providers")
    async def api_providers():                                 # noqa: ANN202
        return JSONResponse({"providers": _ENGINE.providers()} if _ENGINE else {"providers": []})

    @app.get("/api/corpus")
    async def api_corpus():                                    # noqa: ANN202
        return JSONResponse(_ENGINE.corpus() if _ENGINE else {"rows": []})

    @app.get("/api/demo")
    async def api_demo():                                      # noqa: ANN202
        return JSONResponse(_ENGINE.demo() if _ENGINE else {})

    @app.post("/api/optimize")
    async def api_optimize(req: Request):                      # noqa: ANN202
        if _ENGINE is None:
            return JSONResponse({"error": "engine unavailable"}, status_code=503)
        p = await req.json()
        return JSONResponse(_ENGINE.run_optimize(p.get("code", ""), p.get("mode", "normal"),
                                                 p.get("provider"), p.get("model"), p.get("key")))

    @app.post("/api/optimize/stream")                          # §3: the LIVE CODE process trace (SSE)
    async def api_optimize_stream(req: Request):               # noqa: ANN202
        import json                                            # noqa: PLC0415
        import code_stream as CS                               # noqa: PLC0415 (lazy: keeps server import light)
        p = await req.json()
        code, mode = p.get("code", ""), p.get("mode", "normal")

        def gen():                                             # yield each phase AS the real work completes
            try:
                for ev in CS.iter_code_trace(code, mode):
                    yield CS.to_sse([ev])[0]
            except Exception as e:                             # noqa: BLE001 — never crash the stream
                yield "data: " + json.dumps({"phase": "RESULT", "message": f"오류: {type(e).__name__}",
                                             "tier": mode, "budget": "", "grade": "DECLINE"},
                                            ensure_ascii=False) + "\n\n"
            yield "data: " + json.dumps({"type": "done"}) + "\n\n"
        return StreamingResponse(gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.post("/api/key/validate")
    async def api_key_validate(req: Request):                  # noqa: ANN202
        if _ENGINE is None:
            return JSONResponse({"ok": False, "detail": "engine unavailable"}, status_code=503)
        p = await req.json()
        return JSONResponse(_ENGINE.validate_key(p.get("provider", ""), p.get("key", ""), p.get("model")))

    # ---- MR.JEFFREY local-Ollama onboarding (detect / list / pull) — see webapi/local_models.py ----
    # These probe the SERVER PROCESS'S OWN localhost:11434 (self-hosted deployment ⇒ the user's own
    # machine; a remote deployment ⇒ honestly not-found). The chat/generate call itself needs NONE of
    # these routes — it reuses /api/stream + /api/generate unchanged via provider="ollama_local".
    try:
        from webapi import local_models as _OLLAMA               # noqa: PLC0415
    except Exception:                                             # noqa: BLE001
        _OLLAMA = None

    @app.get("/api/ollama/status")
    async def api_ollama_status():                                # noqa: ANN202
        if _OLLAMA is None:
            return JSONResponse({"ok": False, "detail": "local_models unavailable"}, status_code=503)
        return JSONResponse(_OLLAMA.detect())

    @app.get("/api/ollama/models")
    async def api_ollama_models():                                # noqa: ANN202
        if _OLLAMA is None:
            return JSONResponse({"ok": False, "models": []}, status_code=503)
        return JSONResponse(_OLLAMA.list_models())

    @app.post("/api/ollama/pull")                                 # SSE: Ollama's own download-progress shape
    async def api_ollama_pull(req: Request):                      # noqa: ANN202
        p = await req.json()
        name = p.get("name", "")

        def gen():
            if _OLLAMA is None:
                yield sse_event({"status": "error", "error": "local_models unavailable"})
                return
            for ev in _OLLAMA.pull_model(name):
                yield sse_event(ev)
            yield sse_event({"type": "done"})
        return StreamingResponse(gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.get("/api/search/policy")                             # PART 2: observable search-toggle gate
    async def api_search_policy(req: Request):                 # noqa: ANN202
        # Returns the structural gate decision for a given toggle state: OFF ⇒ no tools (search impossible),
        # ON ⇒ the web_search tool is exposed (available) but used only when needed (LLM-judged). No key, no
        # network — pure policy. Query: ?on=true|false (default OFF, the fail-safe).
        import search_gate as SG                                # noqa: PLC0415
        on = req.query_params.get("on")
        return JSONResponse({"allowed": SG.normalize(on), "available": SG.search_available(on),
                             "tools": [t["name"] for t in SG.tools_for(on)],
                             "guidance": SG.system_suffix(on).strip()})

    @app.get("/health/provider")                               # §MRJ author diagnostic (Render env-config path)
    async def health_provider(req: Request):                   # noqa: ANN202
        # Reads the Render env config (HARAN_PROVIDER/HARAN_MODEL/HARAN_BASE_URL/HARAN_KEY), masks the key, and
        # makes one tiny ping. ★ NEVER takes a key in the URL/query (it would land in access logs) — only the
        # non-secret provider/model may be overridden via query; the key comes from the env only.
        if _ENGINE is None:
            return JSONResponse({"ok": False, "detail": "engine unavailable"}, status_code=503)
        q = req.query_params
        return JSONResponse(_ENGINE.health_provider(q.get("provider"), q.get("model")))

    # ── MATH mode (the second top-level mode): fold-first solving + the verified arsenal + visible reasoning ──
    @app.post("/api/math/solve")
    async def api_math_solve(req: Request):                    # noqa: ANN202
        from mathmode import solver as _MS                     # noqa: PLC0415 (lazy: keeps server import light)
        p = await req.json()
        problem = p.get("problem")
        text = p.get("text", "")
        mode = p.get("mode", "normal")
        try:
            sol = _MS.solve_in_mode(problem if problem is not None else text, mode)
            return JSONResponse(sol.to_dict())
        except Exception as e:                                 # noqa: BLE001
            return JSONResponse({"status": "DECLINE", "grade_ko": "보류",
                                 "reason": f"math solve failed ({type(e).__name__})", "reasoning": [],
                                 "certificate": None, "answer": ""}, status_code=200)

    # ── B2/B3: universal file attachment — detect → safely extract (archives) → fold-accelerated analysis ──
    @app.post("/api/math/ingest")
    async def api_math_ingest(req: Request):                   # noqa: ANN202
        import base64                                          # noqa: PLC0415
        from mathmode import ingest as _ING                    # noqa: PLC0415
        p = await req.json()
        name = str(p.get("filename", "upload.txt"))
        try:
            data = base64.b64decode(p.get("content_b64", "") or "")
        except Exception:                                      # noqa: BLE001
            return JSONResponse({"kind": "file", "name": name, "unverified": "invalid base64 payload",
                                 "findings": [], "declines": []}, status_code=200)
        if len(data) > 300 * 1024 * 1024:                      # defense-in-depth size guard at the boundary
            return JSONResponse({"kind": "file", "name": name, "findings": [], "declines": [],
                                 "unverified": "file too large (>300MB) — refused (bomb defense)"}, status_code=200)
        try:
            return JSONResponse(_ING.analyze_upload(name, data))
        except Exception as e:                                 # noqa: BLE001
            return JSONResponse({"kind": "file", "name": name, "findings": [], "declines": [],
                                 "unverified": f"ingest failed ({type(e).__name__})"}, status_code=200)

    @app.get("/static/{name}")                                  # shared design system + site script
    async def static_file(name: str):                          # noqa: ANN202
        # allow-listed by suffix + name-only (no path traversal): only files directly under static/.
        p = (STATIC / name).resolve()
        if p.parent != STATIC.resolve() or not p.is_file() or p.suffix not in _STATIC_TYPES:
            return Response(status_code=404)
        return Response(content=p.read_text(encoding="utf-8"), media_type=_STATIC_TYPES[p.suffix])

    @app.get("/static/runtimes/{name}")                         # §BG LANG-1: WASM runtime registry + module cache
    async def static_runtime(name: str):                       # noqa: ANN202
        # same allow-list, one fixed sub-dir only (name-only ⇒ no traversal; suffix in the whitelist).
        rt = (STATIC / "runtimes").resolve()
        p = (rt / name).resolve()
        if p.parent != rt or not p.is_file() or p.suffix not in _STATIC_TYPES:
            return Response(status_code=404)
        return Response(content=p.read_text(encoding="utf-8"), media_type=_STATIC_TYPES[p.suffix])

    @app.get("/stats.json")                                     # STAGE 0 measurement artifact (no hardcoding)
    async def stats():                                          # noqa: ANN202
        if not STATS_JSON.is_file():
            return JSONResponse({"error": "stats not measured — run benchmarks/measure.py"}, status_code=404)
        return Response(content=STATS_JSON.read_text(encoding="utf-8"), media_type="application/json")

    @app.post("/api/generate")                                 # routes through intent (U4): code|chat|ask
    async def generate(req: Request):                          # noqa: ANN202
        payload = await req.json()
        out = handle_route(payload)
        # save WORK for a logged-in user — request/code/labels only. The LLM key (payload['apiKey']) is
        # DELIBERATELY never passed to add_work; it stays LEVEL-1 (used for the call, then dropped).
        s = AU.verify_session(req.cookies.get(SESSION_COOKIE, ""))
        if s and out.get("kind") == "code" and out.get("result"):
            r = out["result"]
            AU.add_work(s["user_id"], request=str(payload.get("prompt", "")), code=r.get("code", ""),
                        status=r.get("status", ""), proof_tier=r.get("proof_tier", ""))
        return JSONResponse(out)

    @app.post("/api/work/save")                                # the streaming app posts its finished result here
    async def work_save(req: Request):                         # noqa: ANN202
        s = AU.verify_session(req.cookies.get(SESSION_COOKIE, ""))
        if not s:
            return JSONResponse({"ok": False}, status_code=401)
        p = await req.json()                                   # request/code/status/proof_tier ONLY — never a key
        AU.add_work(s["user_id"], request=str(p.get("request", "")), code=str(p.get("code", "")),
                    status=str(p.get("status", "")), proof_tier=str(p.get("proof_tier", "")))
        return JSONResponse({"ok": True})

    @app.post("/api/stream")                                    # T7: SSE
    async def stream(req: Request):                            # noqa: ANN202
        payload = await req.json()
        return StreamingResponse(stream_events(payload), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    return app


# Create the ASGI app only when FastAPI is installed (so `uvicorn server:app` works in deployment);
# importing this module without FastAPI is fine (app=None) — the logic is tested via handle_generate.
app = create_app() if _fastapi_available() else None


if __name__ == "__main__":   # pragma: no cover - manual local run
    import os
    if app is None:
        raise SystemExit("FastAPI not installed — `pip install -r requirements.txt` to run the server.")
    import uvicorn
    # Render/Cloud Run inject $PORT; honor it (then HARAN_PORT, then 8000) so the container binds the right port.
    port = int(os.environ.get("HARAN_PORT") or os.environ.get("PORT") or "8000")
    uvicorn.run(app, host=os.environ.get("HARAN_HOST", "0.0.0.0"), port=port)
