"""
NATIVE-CORE §4 — multi-LLM routing abstraction + high-fidelity OFFLINE mock.
============================================================================
One clean layer over the provider config (`provider.py`) and the live SDK paths (`claude_agent.py`): given a
`provider.Config`, it (1) selects the wire TRANSPORT, (2) shapes the request payload EXACTLY as the live path
would (Anthropic Messages / OpenAI chat.completions / Gemini generateContent — kept in lockstep with
claude_agent._build_kwargs / _build_openai_kwargs), (3) sends it through either a HIGH-FIDELITY OFFLINE MOCK
(provider-shaped raw responses, zero network, deterministic) or an injected LIVE sender, and (4) parses the
reply back to text. So the routing + serialization + parsing for EVERY provider is exercised offline.

HONESTY (constitution §X):
  • mock ≠ live. A mock result is ALWAYS `live=False`, `source="mock-sim:<transport>"` — never dressed up as live.
  • In this sandbox real egress is BLOCKED, so the LIVE multi-provider path is **UNVERIFIED** — `route(mode="live")`
    with no sender returns an explicit UNVERIFIED result; it NEVER fabricates a provider response.
  • Keys are per-call arguments only; this module never reads env, never stores, never logs a key (it redacts).
The LLM only PROPOSES; the HARAN verifier still decides the grade. The mock returns a real, parseable proposal so
the whole propose→verify substrate runs end-to-end with no network and no secret.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import provider as P

TRANSPORTS = ("anthropic_sdk", "openai_chat", "gemini_generate")

# kept in lockstep with claude_agent (imported lazily only to mirror the constant; no network/SDK needed here)
OPENAI_MIN_MAX_TOKENS = 8192

# a fixed, parseable proposal — the mock returns this so the downstream verifier substrate runs end-to-end.
_CANNED = ("def haran_sum(n):\n    # closed form for 0+1+...+n\n    return n * (n + 1) // 2\n")


@dataclass
class Request:
    transport: str
    provider: str
    model: str
    endpoint: str                 # SDK method or HTTP path (no host/secret) — provenance, never a URL with a key
    payload: Dict                 # the canonical wire body the live path would send


@dataclass
class RouteResult:
    text: str
    live: bool                    # True ONLY when an injected live sender returned a real response
    status: str                   # OK | UNVERIFIED
    source: str                   # "mock-sim:<transport>" | "live:<provider>" | "live:unavailable"
    provider: str
    transport: str
    request_fingerprint: str      # deterministic sha256 of the canonical payload (no secrets) — reproducibility
    reason: str = ""


def redact(s: Optional[str]) -> str:
    """Never echo a key. Show only a length-tagged mask so logs/provenance carry zero secret material."""
    if not s:
        return "∅"
    return f"<redacted:{len(s)}chars>"


# ── request shaping (matches claude_agent's builders; pure, no network/secret) ──────────────────────────────
def build_request(cfg: P.Config, prompt: str, system: Optional[str] = None, max_tokens: int = 4096,
                  thinking: bool = True) -> Request:
    t = P.transport_kind(cfg.provider)
    sys_text = system or "You are HARAN's proposer. Propose; the verifier decides."
    if t == "anthropic_sdk":
        payload = {
            "model": cfg.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "system": [{"type": "text", "text": sys_text, "cache_control": {"type": "ephemeral"}}],
        }
        if thinking:
            payload["thinking"] = {"type": "adaptive"}
        return Request(t, cfg.provider, cfg.model, "messages.create", payload)
    if t == "openai_chat":
        payload = {
            "model": cfg.model,
            "max_tokens": max(max_tokens, OPENAI_MIN_MAX_TOKENS),
            "messages": [{"role": "system", "content": sys_text},
                         {"role": "user", "content": prompt}],
            "stream": False,
            "temperature": 0.2,
        }
        return Request(t, cfg.provider, cfg.model, "/chat/completions", payload)
    if t == "gemini_generate":
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": sys_text}]},
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.2},
        }
        return Request(t, cfg.provider, cfg.model, f"models/{cfg.model}:generateContent", payload)
    raise ValueError(f"unknown transport {t}")


# ── response parsing (matches claude_agent._extract_openai_text + the SDK/HTTP shapes) ──────────────────────
def parse_response(transport: str, raw: Dict) -> str:
    if transport == "anthropic_sdk":
        parts = [b.get("text", "") for b in raw.get("content", []) if b.get("type") == "text"]
        return "".join(parts).strip()
    if transport == "openai_chat":
        msg = (raw.get("choices") or [{}])[0].get("message", {})
        return (msg.get("content") or msg.get("reasoning_content") or "").strip()
    if transport == "gemini_generate":
        cands = raw.get("candidates") or [{}]
        parts = cands[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts).strip()
    raise ValueError(f"unknown transport {transport}")


# ── high-fidelity OFFLINE mock: provider-SHAPED raw responses (deterministic, no network) ───────────────────
def mock_response(req: Request, reply_text: str) -> Dict:
    """Return the EXACT JSON shape the chosen provider returns, embedding reply_text — so parse_response is
    exercised against realistic structure (ids, usage, finish_reason). Deterministic; carries no secret."""
    n_out = max(1, len(reply_text) // 4)
    if req.transport == "anthropic_sdk":
        return {"id": "msg_mock_0001", "type": "message", "role": "assistant", "model": req.model,
                "content": [{"type": "text", "text": reply_text}], "stop_reason": "end_turn",
                "usage": {"input_tokens": 64, "output_tokens": n_out}}
    if req.transport == "openai_chat":
        return {"id": "chatcmpl-mock0001", "object": "chat.completion", "model": req.model,
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": reply_text}}],
                "usage": {"prompt_tokens": 64, "completion_tokens": n_out, "total_tokens": 64 + n_out}}
    if req.transport == "gemini_generate":
        return {"candidates": [{"content": {"role": "model", "parts": [{"text": reply_text}]},
                                "finishReason": "STOP", "index": 0}],
                "usageMetadata": {"promptTokenCount": 64, "candidatesTokenCount": n_out}}
    raise ValueError(f"unknown transport {req.transport}")


def request_fingerprint(req: Request) -> str:
    blob = json.dumps({"t": req.transport, "p": req.provider, "m": req.model, "e": req.endpoint,
                       "payload": req.payload}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


# ── the router ──────────────────────────────────────────────────────────────────────────────────────────────
def route(cfg: P.Config, prompt: str, *, system: Optional[str] = None, max_tokens: int = 4096,
          mode: str = "mock", reply_text: Optional[str] = None,
          sender: Optional[Callable[[Request, Optional[str]], Dict]] = None,
          api_key: Optional[str] = None) -> RouteResult:
    """Route one proposal request. mode="mock" ⇒ high-fidelity OFFLINE (live=False, deterministic). mode="live"
    ⇒ uses the injected `sender(req, api_key)->raw` (the real network call in production); with NO sender the
    sandbox cannot reach a provider ⇒ an explicit UNVERIFIED result (never a fabricated response). The api_key,
    if present, is passed to the sender only and never logged here."""
    req = build_request(cfg, prompt, system, max_tokens)
    fp = request_fingerprint(req)
    if mode == "mock":
        raw = mock_response(req, reply_text if reply_text is not None else _CANNED)
        return RouteResult(parse_response(req.transport, raw), False, "OK", f"mock-sim:{req.transport}",
                           req.provider, req.transport, fp)
    if mode == "live":
        if sender is None:
            return RouteResult("", False, "UNVERIFIED", "live:unavailable", req.provider, req.transport, fp,
                               reason="no live sender injected and sandbox egress is blocked — live path UNVERIFIED")
        raw = sender(req, api_key)                       # production: the real HTTP/SDK call (key used, not logged)
        return RouteResult(parse_response(req.transport, raw), True, "OK", f"live:{req.provider}",
                           req.provider, req.transport, fp)
    raise ValueError(f"unknown mode {mode}")


def live_status() -> Dict:
    """The honest live posture in this sandbox: egress is blocked, so live multi-provider is UNVERIFIED. The mock
    path is the verified offline substitute. (The real egress probe lives in scripts/s11_live_measure.py.)"""
    return {"live": "UNVERIFIED", "reason": "EGRESS_BLOCKED (proxy allowlist) — mock-sim is the offline substitute",
            "verified_offline": True, "transports": list(TRANSPORTS)}


def providers_overview() -> List[Dict]:
    """Every configured gateway preset → its transport, so the routing coverage is inspectable (anthropic,
    openai-compat incl. OpenRouter / Z.ai / DeepSeek, native openai, gemini, groq)."""
    out = []
    for label, (prov, base, mdl, src) in P.GATEWAY_PRESETS.items():
        out.append({"label": label, "provider": prov, "transport": P.transport_kind(prov),
                    "default_model": mdl, "base_url": base})
    return out
