"""
webapi/local_models.py — thin client for Ollama's LOCAL management API (detect / list / pull).
=================================================================================================
This is NOT the chat/generate transport — that already exists: provider.py's `ollama_local` preset rides
the SAME `openai_chat` transport as every other family-C gateway (Ollama's REST API is OpenAI-compatible
at localhost:11434/v1), so `claude_agent.py`'s existing `_live_generate_openai` needs no changes at all.
This module is the small EXTRA surface Ollama's own app has that a plain OpenAI-compatible chat endpoint
doesn't cover: "is Ollama running", "what models are already pulled", "pull one, with progress".

Reachability note: these calls are made by the SERVER PROCESS itself (see server.py's /api/ollama/*
routes), not by the browser. On a self-hosted deployment (`python server.py` next to `ollama serve`) that
IS the user's own machine, so localhost:11434 is exactly the right target. On a remotely-deployed server
(e.g. Render) `localhost` means the server's own container, where nothing is listening — `detect()` then
honestly reports not-found, which is the correct behavior for that topology, not a bug to work around.

Stdlib-only (urllib), matching the zero-dependency discipline of every other live-provider call in this
repo (see webapi/engine_bridge.py::_http_post). Every function is failure-honest: a connection refused or
timeout is a normal, expected "not found" result — never an exception that reaches the caller, and never a
fabricated "found" default.
"""
from __future__ import annotations

import json as _json
import urllib.error as _urlerr
import urllib.request as _urlreq
from typing import Dict, Iterator, List, Optional, Tuple

DEFAULT_HOST = "http://localhost:11434"
INSTALL_URL = "https://ollama.com/download"


def _get(url: str, timeout: float = 3.0) -> Tuple[Optional[int], str]:
    """GET and return (status, body_text). Never raises: unreachable ⇒ (None, reason)."""
    req = _urlreq.Request(url, method="GET")
    try:
        with _urlreq.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except _urlerr.HTTPError as e:
        try:
            return e.code, e.read().decode("utf-8", "replace")
        except Exception:                                          # noqa: BLE001
            return e.code, ""
    except Exception as e:                                         # noqa: BLE001 — connection refused / no route
        return None, f"{type(e).__name__}: {e}"


def detect(host: str = DEFAULT_HOST) -> Dict:
    """Is a local Ollama server reachable at `host`? A tiny GET /api/version — real network, no key needed.
    Never raises: unreachable ⇒ {"ok": False, ...} with install guidance (never a fabricated ok=True)."""
    status, text = _get(f"{host.rstrip('/')}/api/version")
    if status == 200:
        try:
            version = _json.loads(text).get("version", "")
        except Exception:                                          # noqa: BLE001
            version = ""
        return {"ok": True, "host": host, "version": version}
    return {"ok": False, "host": host,
            "detail": "Ollama가 이 주소에서 응답하지 않습니다 — 로컬에 설치되어 실행 중인지 확인하세요.",
            "install_url": INSTALL_URL}


def list_models(host: str = DEFAULT_HOST) -> Dict:
    """The models the user has ALREADY pulled locally (GET /api/tags) — never a hardcoded/guessed list.
    Each entry is defensively parsed (Ollama's own field names); a missing/renamed field never crashes
    this call — it just yields a thinner row, honestly (never a fabricated value)."""
    status, text = _get(f"{host.rstrip('/')}/api/tags")
    if status != 200:
        return {"ok": False, "models": [],
                "detail": "설치된 모델 목록을 가져오지 못했습니다 — Ollama가 실행 중인지 확인하세요."}
    try:
        raw = _json.loads(text).get("models", [])
    except Exception:                                              # noqa: BLE001
        return {"ok": False, "models": [], "detail": "응답을 해석하지 못했습니다 (unexpected /api/tags shape)."}
    out: List[Dict] = []
    for m in raw:
        details = m.get("details") or {}
        out.append({
            "name": m.get("name") or m.get("model") or "",
            "size_bytes": m.get("size"),
            "quant": details.get("quantization_level"),            # e.g. "Q3_K_M" — real tag, never invented
            "family": details.get("family"),
            "parameter_size": details.get("parameter_size"),
        })
    return {"ok": True, "models": out}


def pull_model(name: str, host: str = DEFAULT_HOST) -> Iterator[Dict]:
    """Stream POST /api/pull's newline-delimited JSON progress objects, one dict per line. The caller
    (server.py) re-wraps each as an SSE `data:` event using OUR OWN framing — we mirror Ollama's own
    download-progress SHAPE (status/completed/total), not its wire format, so the UI can render a familiar
    pull progress bar while every byte of the actual HTTP/SSE code is ours."""
    if not name or not name.strip():
        yield {"status": "error", "error": "no model name given"}
        return
    url = f"{host.rstrip('/')}/api/pull"
    data = _json.dumps({"name": name.strip(), "stream": True}).encode("utf-8")
    req = _urlreq.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with _urlreq.urlopen(req, timeout=600) as r:
            for raw_line in r:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    yield _json.loads(line.decode("utf-8", "replace"))
                except Exception:                                  # noqa: BLE001 — a malformed line is skipped
                    continue
    except _urlerr.HTTPError as e:
        yield {"status": "error", "error": f"HTTP {e.code}"}
    except Exception as e:                                         # noqa: BLE001 — connection refused / no route
        yield {"status": "error", "error": f"{type(e).__name__}: {e}"}
