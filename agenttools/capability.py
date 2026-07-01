"""
agenttools/capability.py — LIVE tool-calling capability gate for local Ollama models.
========================================================================================
★ Prime Directive 4 (10H directive) ★: local model tool-calling reliability varies by model
(web-verified 2026-07). Qwen3/Llama-3.1+/Gemma-4-class models are natively trained and stable; others
"know the JSON schema but decide unreliably whether to use it" — and 3-bit quantization can further
erode exactly the structured-output precision tool-calling depends on. Silently exposing tools to an
unsupported/unreliable model would either (a) get ignored (wasted context, degraded answer quality from
the extra prompt noise) or (b) produce malformed tool_calls that break the execution loop. Neither is
acceptable, so we LIVE-CHECK the model's own advertised capability before ever exposing tools to it.

Mechanism (web-confirmed 2026-07 via GitHub PR #10066 "api: return model capabilities from the show
endpoint" + Ollama docs): `POST {host}/api/show {"name": model}` returns a JSON body with a
`"capabilities"` array, e.g. `["completion", "vision", "tools", "thinking"]`. `"tools"` membership is
the live ground truth. Same fail-safe style as `webapi/local_models.py::detect()` — any network error,
timeout, or unexpected response shape is treated as "capability not confirmed" (False), NEVER a
fabricated True. This is a technical-reliability gate (like the vision-capability check it mirrors), not
a taste/aesthetic judgment.
"""
from __future__ import annotations

import json as _json
import urllib.error as _urlerr
import urllib.request as _urlreq
from typing import Optional

DEFAULT_HOST = "http://localhost:11434"
_TIMEOUT_S = 3.0


def _post_show(model: str, host: str) -> Optional[dict]:
    """POST /api/show {"name": model}; returns the parsed JSON body, or None on ANY failure (unreachable
    host, timeout, non-200, unparsable body) — never raises."""
    url = f"{host.rstrip('/')}/api/show"
    data = _json.dumps({"name": model}).encode("utf-8")
    req = _urlreq.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with _urlreq.urlopen(req, timeout=_TIMEOUT_S) as r:
            if r.status != 200:
                return None
            return _json.loads(r.read().decode("utf-8", "replace"))
    except _urlerr.HTTPError:
        return None
    except Exception:                            # noqa: BLE001 — connection refused / no route / bad JSON
        return None


def ollama_supports_tools(model: str, host: str = DEFAULT_HOST) -> bool:
    """True iff Ollama's OWN `/api/show` reports `"tools"` in this model's `capabilities` array.
    Fail-safe False on any error (server unreachable, model not pulled, unexpected shape, missing
    field) — we never guess a model supports tools; an unconfirmed capability means the caller falls
    back to the plain (no-tools) write→verify→fix flow, gracefully, without crashing or silently
    claiming tools were used."""
    if not model or not model.strip():
        return False
    body = _post_show(model, host)
    if not isinstance(body, dict):
        return False
    caps = body.get("capabilities")
    if not isinstance(caps, list):
        return False
    return "tools" in caps
