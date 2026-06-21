"""
webapi/engine_bridge.py — the bridge from the web API to the REAL pillar3 engine.
=================================================================================
Every number this returns is produced by the actual engine (pillar3.engine / canonical / corpus_runner /
studio_gen / mode / provider) — measured whole-program, carrying its hotspot fraction and Amdahl ceiling,
graded by the real ADT, ratio ≤ ceiling by construction. No hand-written numbers, no invented wins.

For a user's PASTED code we do REAL AST detection of waste patterns in their source, then report the engine's
REAL measured result for each detected waste class (run under the selected ModePolicy). We never auto-rewrite
arbitrary user code (that needs the LLM proposer + a key; the verifier still arbitrates), so the measured rows
are honestly labelled as the engine's verified result for the detected waste class on a representative workload.
"""
from __future__ import annotations

import ast
import json as _json
import os
import sys
import urllib.error as _urlerr
import urllib.parse as _urlparse
import urllib.request as _urlreq
from typing import Dict, List, Optional, Tuple

# make the repo root importable (webapi/ lives under it)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import provider as PRV
from pillar3 import canonical as C
from pillar3 import corpus_runner as CR
from pillar3 import engine as E
from pillar3.mode import Mode, ModePolicy
import pillar3_studio_gen as STUDIO
from corpus import ai_todo_app, log_analyzer, csv_stats, template_render, json_pipeline


# ── AST waste detection on the user's PASTED source (real; no exec) ────────────────────────────────────
_FETCH = ("fetch", "get", "query", "load", "find", "select", "read", "lookup")


def detect_in_source(src: str) -> List[Dict]:
    """Walk the user's source AST and report waste patterns actually present (mapped to the engine's vocabulary).
    Pure AST — the pasted code is never executed."""
    found: List[Dict] = []
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [{"waste_type": "syntax_error", "evidence": f"could not parse: {e}", "line": getattr(e, "lineno", 0)}]

    def add(wt, ev, line):
        if not any(f["waste_type"] == wt for f in found):
            found.append({"waste_type": wt, "evidence": ev, "line": line})

    list_names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and isinstance(n.value, (ast.List, ast.ListComp)):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    list_names.add(t.id)
    for n in ast.walk(tree):
        if isinstance(n, (ast.For, ast.While, ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            for s in ast.walk(n):
                if isinstance(s, ast.Compare) and any(isinstance(o, (ast.In, ast.NotIn)) for o in s.ops):
                    c = s.comparators[0]
                    if isinstance(c, ast.Name) and c.id in list_names:
                        add("list_as_set", f"`x in {c.id}` (a list) inside a loop → O(n) membership",
                            getattr(s, "lineno", 0))
                if isinstance(s, ast.Call):
                    nm = (s.func.attr if isinstance(s.func, ast.Attribute)
                          else s.func.id if isinstance(s.func, ast.Name) else "")
                    low = nm.lower()
                    if any(low.startswith(p) or low.endswith(p) or ("_" + p) in low for p in _FETCH) and nm not in ("get",):
                        add("n_plus_1", f"`{nm}(...)` (a per-item fetch) inside a loop → N+1", getattr(s, "lineno", 0))
                if isinstance(s, ast.Assign) and isinstance(s.value, ast.BinOp) and isinstance(s.value.op, ast.Add) \
                        and len(s.targets) == 1 and isinstance(s.targets[0], ast.Name):
                    tgt = s.targets[0].id
                    if tgt in {x.id for x in ast.walk(s.value) if isinstance(x, ast.Name)}:
                        add("accidental_quadratic", f"`{tgt} = {tgt} + …` inside a loop → O(n²) build",
                            getattr(s, "lineno", 0))
                if isinstance(s, ast.Call) and isinstance(s.func, ast.Attribute) and s.func.attr == "count":
                    add("accidental_quadratic", "`.count()` inside a loop → O(n²)", getattr(s, "lineno", 0))
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Pow) and isinstance(n.right, ast.Constant) \
                and isinstance(n.right.value, int) and 2 <= n.right.value <= 4:
            add("algo_replace", f"`x ** {n.right.value}` → strength-reducible", getattr(n, "lineno", 0))
        # nested pure-arithmetic loop with math.* → vectorizable / algorithmic
        if isinstance(n, (ast.ListComp, ast.GeneratorExp, ast.For)):
            if any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                   and c.func.attr in ("sin", "cos", "sqrt", "exp", "log") for c in ast.walk(n)):
                add("simd_offload", "scalar math.* over each element → SIMD/vectorizable", getattr(n, "lineno", 0))
    return found


# ── map detected waste → the engine's runnable demo (canonical candidates carry real slow/fast pairs) ───
def _canonical_by_waste() -> Dict[str, "E.Candidate"]:
    return {c.waste_type: c for c in C.build_candidates()}


def _proposer_block(provider: Optional[str], model: Optional[str], key: Optional[str],
                    detected: List[Dict], mode: Mode) -> Dict:
    """Route to the chosen LLM proposer when a key is given (a REAL provider call), else the deterministic
    structural detectors. The proposer is NEVER the arbiter: even a live LLM proposal is not auto-applied
    (Rule 6 — arbitrary LLM code isn't executed here), so the MEASURED, applied result is always the
    verifier-arbitrated structural fix. The key is header-only and never logged."""
    if not key or not provider or provider not in PRV.VALID_PROVIDERS:
        return {"used": False, "mode": "deterministic",
                "note": "no LLM key — deterministic structural detectors (the measured, applied path). "
                        "Pick a free Groq/Gemini key to have an LLM propose rewrites too."}
    waste = detected[0]["waste_type"] if detected else "general hotspot"
    mdl = (model or "").strip() or PRV.default_model_for(provider)
    prompt = (f"Optimize this Python for the waste pattern `{waste}` while preserving behavior. "
              f"Return only the faster function. Mode: {mode.value}.")
    kind, url, headers, body = _provider_request(provider, mdl, key, prompt, 256)
    status, text = _http_post(url, headers, body)
    if status == 200:
        snippet = _extract_text(kind, text)[:280]
        return {"used": True, "live": True, "provider": provider, "model": mdl, "transport": kind,
                "status": "llm-consulted", "applied": "verifier-arbitrated structural fix",
                "rationale": snippet,
                "note": ("the LLM proposed a rewrite; per Rule 6 LLM-emitted code is not auto-executed here, so the "
                         "shipped rows below are the verifier-arbitrated structural fixes (proposer ≠ arbiter).")}
    cls = _classify(provider, kind, mdl, status, text)
    reason = "egress-blocked in this sandbox" if cls.get("blocked") else "key rejected/unreachable"
    return {"used": False, "live": cls.get("live", False), "provider": provider, "model": mdl, "transport": kind,
            "status": "llm-unavailable", "detail": cls["detail"],
            "note": f"LLM proposer {reason}; fell back to deterministic structural detectors (the measured path)."}


def _extract_text(kind: str, text: str) -> str:
    """Best-effort pull of the model's reply text from a provider response (never raises)."""
    try:
        d = _json.loads(text)
        if kind == "gemini_generate":
            return d["candidates"][0]["content"]["parts"][0].get("text", "").strip()
        if kind == "openai_chat":
            return d["choices"][0]["message"].get("content", "").strip()
        return "".join(b.get("text", "") for b in d.get("content", [])).strip()   # anthropic
    except Exception:                                                              # noqa: BLE001
        return "(model replied; could not parse a text snippet)"


def run_optimize(code: str, mode: str, provider: Optional[str] = None, model: Optional[str] = None,
                 key: Optional[str] = None) -> Dict:
    """Detect waste in the user's code (real), optionally consult the chosen LLM proposer (real provider call
    when a key is given), then run the REAL engine under the selected mode and return measured verification rows.
    The verifier arbitrates; the LLM never decides. Invalid/missing key ⇒ honest deterministic fallback."""
    m = Mode(mode) if mode in (x.value for x in Mode) else Mode.NORMAL
    detected = detect_in_source(code)
    det_types = {d["waste_type"] for d in detected}
    proposer = _proposer_block(provider, model, key, detected, m)

    # the canonical candidates whose waste class was detected in the user's code (engine vocabulary)
    cands = [c for c in C.build_candidates() if c.waste_type in det_types]
    if not cands:
        # nothing the engine recognises — a dignified, honest empty result (not an error)
        return {
            "mode": m.value, "detected": detected, "shipped": [], "declined": [],
            "cumulative_ratio": 1.0, "z3_calls": 0, "ran_complexity_sweep": False, "proposer": proposer,
            "note": ("no known waste pattern detected in the pasted code that this engine has a verified fix for — "
                     "nothing safe to ship. (detection is real AST analysis of your source.)"),
            "policy": _mode_contract(m),
        }
    rep = E.optimize(cands, C.make_input, mode=m, n=1, residual=C.residual, sweep_fn=C.sweep_fn)
    return {
        "mode": m.value,
        "detected": detected,
        "shipped": [_row(s) for s in rep.shipped],
        "declined": [{"name": d.name, "waste_type": d.waste_type, "reason": d.reason} for d in rep.declined],
        "cumulative_ratio": round(rep.fresh_cumulative_ratio, 3),
        "z3_calls": rep.z3_calls,
        "ran_complexity_sweep": rep.ran_complexity_sweep,
        "latency_ms": round(rep.latency_s * 1e3, 1),
        "proposer": proposer,
        "note": ("measured whole-program under the {} contract; detection is real AST analysis of your code, "
                 "the measured rows are the engine's verified result for each detected waste class on a "
                 "representative workload. The LLM (if a key is set) only proposes; the verifier "
                 "arbitrates.").format(m.value),
        "policy": _mode_contract(m),
    }


def _row(s) -> Dict:
    import math
    return {
        "name": s.name, "waste_type": s.waste_type, "grade": s.grade.lower(),
        "ratio": math.floor(s.ratio * 1000) / 1000,
        "ceiling": (math.ceil(s.ceiling * 100) / 100 if s.ceiling != float("inf") else None),
        "hotspot_fraction": round(s.hotspot_fraction, 3),
    }


def _mode_contract(m: Mode) -> Dict:
    p = ModePolicy.for_mode(m)
    return {
        "mode": m.value, "primary_clock": p.primary_clock, "verifier_tier": p.verifier_tier.name,
        "detectors": len(p.enabled_detectors), "acceptable_grades": sorted(g.lower() for g in p.acceptable_grades),
        "max_hotspots": p.max_hotspots, "runs_complexity_sweep": p.runs_complexity_sweep,
        "latency_budget_s": p.latency_budget_s, "risk_posture": p.risk_posture, "stop_condition": p.stop_condition,
    }


def modes() -> List[Dict]:
    return [_mode_contract(m) for m in (Mode.FAST, Mode.NORMAL, Mode.EXTEND)]


_PROVIDER_LABELS = {"anthropic": "Claude (official)", "anthropic_compat": "Claude-compatible gateway",
                    "openai": "ChatGPT (OpenAI)", "openai_compat": "OpenAI-compatible gateway",
                    "gemini": "Gemini (Google)", "groq": "Groq"}
_PROVIDER_KEYVAR = {"anthropic": "ANTHROPIC_API_KEY", "anthropic_compat": "ANTHROPIC_API_KEY",
                    "openai": "OPENAI_API_KEY", "openai_compat": "OPENAI_API_KEY",
                    "gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY"}
_KEY_LABELS = {"gemini": "Google AI Studio API key", "groq": "Groq API key",
               "openai": "OpenAI API key", "anthropic": "Anthropic API key"}


def providers() -> List[Dict]:
    """Every provider with the UI metadata: transport, default model, free-no-card flag, key field label, and a
    'where to get a key' link. Groq + Gemini are free with no credit card — the default way to test the site."""
    out: List[Dict] = []
    for p in PRV.VALID_PROVIDERS:
        out.append({
            "id": p, "label": _PROVIDER_LABELS.get(p, p), "transport": PRV.transport_kind(p),
            "key_env": _PROVIDER_KEYVAR.get(p, "HARAN_KEY"),
            "default_model": PRV.default_model_for(p),
            "free_no_card": PRV.is_free_no_card(p),
            "key_label": _KEY_LABELS.get(p, _PROVIDER_LABELS.get(p, p) + " API key"),
            "get_key_url": PRV.get_key_url(p),
        })
    # surface the free, no-card providers first (the recommended way in)
    out.sort(key=lambda d: (not d["free_no_card"], d["id"]))
    return out


def corpus() -> Dict:
    repos = [
        CR.CorpusRepo("ai_todo_app", ai_todo_app.ARCHETYPE, ai_todo_app, exact_justification=ai_todo_app.EXACT_JUSTIFICATION),
        CR.CorpusRepo("log_analyzer", log_analyzer.ARCHETYPE, log_analyzer),
        CR.CorpusRepo("csv_stats", csv_stats.ARCHETYPE, csv_stats),
        CR.CorpusRepo("json_pipeline", json_pipeline.ARCHETYPE, json_pipeline, exact_justification=json_pipeline.EXACT_JUSTIFICATION),
        CR.CorpusRepo("template_render", template_render.ARCHETYPE, template_render),
    ]
    rep = CR.run_corpus(repos)
    grades = {g: sum(1 for r in rep.rows if r.grade.lower() == g) for g in ("exact", "probabilistic", "decline")}
    return {
        "rows": [{"name": r.name, "archetype": r.archetype, "detected": r.detected, "grade": r.grade.lower(),
                  "ratio": r.ratio, "ceiling": r.ceiling, "hotspot_fraction": r.hotspot_fraction, "note": r.note}
                 for r in rep.rows],
        "grades": grades, "found_nothing": rep.found_nothing(),
    }


def demo() -> Dict:
    """Real per-mode canonical runs + panel rows (reuses the studio_gen real-data generator)."""
    return STUDIO.build()


# ── live provider HTTP (real calls; the key is ONLY ever a request header, never logged/stored/returned) ─
def _provider_request(provider_id: str, model: str, key: str, prompt: str,
                      max_tokens: int) -> "Tuple[str, str, Dict[str, str], Dict]":
    """Single-source the wire shape for every provider (validate + proposer share it). Returns
    (transport_kind, url, headers, json_body). The key lives ONLY in `headers` — callers must never log it."""
    kind = PRV.transport_kind(provider_id)
    base = (PRV.base_url(provider_id) or "").rstrip("/")
    if kind == "gemini_generate":                                       # native Gemini (confirmed reachable)
        return (kind, f"{base}/models/{model}:generateContent",
                {"x-goog-api-key": key, "Content-Type": "application/json"},
                {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": max_tokens}})
    if kind == "openai_chat":                                           # groq + openai + openai_compat gateways
        return (kind, f"{base}/chat/completions",
                {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens})
    return ("anthropic_sdk", (base or "https://api.anthropic.com") + "/v1/messages",   # raw Anthropic Messages
            {"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]})


def _http_post(url: str, headers: Dict[str, str], body: Dict, timeout: float = 12.0) -> "Tuple[Optional[int], str]":
    """POST JSON and return (status, body_text). Only the status + provider response body come back — never the
    request headers (which hold the key). Network/egress failures return (None, reason)."""
    data = _json.dumps(body).encode("utf-8")
    req = _urlreq.Request(url, data=data, headers=headers, method="POST")
    try:
        with _urlreq.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except _urlerr.HTTPError as e:                                      # 4xx/5xx incl. egress-allowlist 403
        try:
            return e.code, e.read().decode("utf-8", "replace")
        except Exception:                                              # noqa: BLE001
            return e.code, ""
    except Exception as e:                                             # noqa: BLE001 — DNS/timeout/egress block
        return None, f"{type(e).__name__}: {e}"


_INVALID_MARKERS = ("api_key_invalid", "api key not valid", "invalid api key", "invalid_api_key",
                    "incorrect api key", "unauthorized", "invalid authentication", "permission_denied",
                    "invalid x-api-key", "authentication_error")


def _classify(provider_id: str, kind: str, model: str, status: "Optional[int]", text: str) -> Dict:
    """Honest classification of a live provider response. Never echoes the key. Distinguishes a genuinely
    invalid key (live round-trip happened) from this sandbox's egress allowlist blocking the host."""
    low = (text or "").lower()
    host = _urlparse.urlparse(_provider_request(provider_id, model, "x", "x", 1)[1]).hostname or provider_id
    base = {"transport": kind, "model": model, "provider": provider_id, "key_in_headers_only": True}
    if status == 200:
        return {**base, "ok": True, "live": True, "detail": f"key valid — live {provider_id} call returned 200."}
    if status is None or "allowlist" in low:                            # egress blocked (e.g. groq in this sandbox)
        return {**base, "ok": False, "live": False, "blocked": True,
                "detail": (f"request is well-formed and the key is held session-only (never logged); but this "
                           f"sandbox's network egress blocks {host}. Add {host} to the egress allowlist to enable "
                           f"live validation. [UNVERIFIED here: {'no network response' if status is None else status}]")}
    if status in (400, 401, 403) and any(s in low for s in _INVALID_MARKERS):
        return {**base, "ok": False, "live": True,
                "detail": f"key rejected by {provider_id} (HTTP {status}). Check the key. Get one: {PRV.get_key_url(provider_id)}"}
    return {**base, "ok": False, "live": status is not None,
            "detail": f"{provider_id} returned HTTP {status}; could not confirm the key (response not an auth-OK)."}


def validate_key(provider_id: str, key: str, model: Optional[str] = None) -> Dict:
    """Make a REAL tiny (1-token) test call to the chosen provider with the pasted key and report ok/fail.
    The key is placed ONLY in the request header — never logged, never written to disk, never persisted. With a
    real key + reachable host this is a genuine live validation (e.g. Gemini); when the host is egress-blocked we
    say so honestly rather than faking a pass."""
    if provider_id not in PRV.VALID_PROVIDERS:
        return {"ok": False, "detail": f"unknown provider: {provider_id}"}
    if not key:
        return {"ok": False, "detail": "no key provided", "get_key_url": PRV.get_key_url(provider_id)}
    mdl = (model or "").strip() or PRV.default_model_for(provider_id)
    kind, url, headers, body = _provider_request(provider_id, mdl, key, "ping", 1)
    status, text = _http_post(url, headers, body)
    out = _classify(provider_id, kind, mdl, status, text)
    out["get_key_url"] = PRV.get_key_url(provider_id)
    return out
