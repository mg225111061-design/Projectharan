"""
§W PHASE 4 — KEY WIRING + MANY MORE PROVIDERS: widen the registry, wire each correctly, key session-only.
================================================================================================================
The provider abstraction already supports the transport types (anthropic_sdk / openai_chat / gemini_generate +
the *_compat gateways — see provider.py / claude_agent.py); this widens the REGISTRY to the major LLM providers and
their compatible gateways. Each carries: id, label, transport, default_model, key_env, key_label, get_key_url,
free_no_card. The OpenAI-compatible providers (Mistral, DeepSeek, xAI, Together, Fireworks, OpenRouter, Perplexity,
Groq) ride the `openai_chat` transport with their own base_url; Anthropic uses `anthropic_sdk`; Google uses
`gemini_generate`.

★ The API key is session-only ALWAYS (the one hard invariant): entered per request, held in the tab, used once,
never persisted — see auth.py (no api_key column) + claude_agent.py (key dropped after the call). Live key validation
(a 1-token call) is pending-real-stack here (egress BLOCKED); the wiring/config is verified, the live call never faked.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

_TRANSPORTS = {"anthropic_sdk", "openai_chat", "gemini_generate", "anthropic_compat", "openai_compat"}


@dataclass
class Provider:
    id: str
    label: str
    transport: str
    default_model: str
    key_env: str
    key_label: str
    get_key_url: Optional[str]
    free_no_card: bool
    base_url: Optional[str] = None       # for the OpenAI-compatible gateways

    def public(self) -> dict:            # what the UI needs (NEVER a key — keys are session-only, never in config)
        d = asdict(self)
        return d


def _P(*a, **k):
    return Provider(*a, **k)


# ── the widened registry: major providers + compatible gateways ──────────────────────────────────────────────
REGISTRY: List[Provider] = [
    _P("anthropic", "Claude (official)", "anthropic_sdk", "claude-opus-4-8", "ANTHROPIC_API_KEY",
       "Anthropic API key", "https://console.anthropic.com/settings/keys", False),
    _P("openai", "ChatGPT (OpenAI)", "openai_chat", "gpt-4o", "OPENAI_API_KEY",
       "OpenAI API key", "https://platform.openai.com/api-keys", False),
    _P("gemini", "Gemini (Google)", "gemini_generate", "gemini-3.5-flash", "GEMINI_API_KEY",
       "Google AI Studio API key", "https://aistudio.google.com/apikey", True),
    _P("groq", "Groq", "openai_chat", "llama-3.3-70b-versatile", "GROQ_API_KEY",
       "Groq API key", "https://console.groq.com/keys", True, "https://api.groq.com/openai/v1"),
    _P("mistral", "Mistral", "openai_chat", "mistral-large-latest", "MISTRAL_API_KEY",
       "Mistral API key", "https://console.mistral.ai/api-keys", False, "https://api.mistral.ai/v1"),
    _P("cohere", "Cohere", "openai_chat", "command-r-plus", "COHERE_API_KEY",
       "Cohere API key", "https://dashboard.cohere.com/api-keys", False, "https://api.cohere.ai/compatibility/v1"),
    _P("deepseek", "DeepSeek", "openai_chat", "deepseek-chat", "DEEPSEEK_API_KEY",
       "DeepSeek API key", "https://platform.deepseek.com/api_keys", False, "https://api.deepseek.com/v1"),
    _P("xai", "Grok (xAI)", "openai_chat", "grok-2-latest", "XAI_API_KEY",
       "xAI API key", "https://console.x.ai", False, "https://api.x.ai/v1"),
    _P("together", "Together AI", "openai_chat", "meta-llama/Llama-3.3-70B-Instruct-Turbo", "TOGETHER_API_KEY",
       "Together API key", "https://api.together.ai/settings/api-keys", False, "https://api.together.xyz/v1"),
    _P("fireworks", "Fireworks AI", "openai_chat", "accounts/fireworks/models/llama-v3p3-70b-instruct",
       "FIREWORKS_API_KEY", "Fireworks API key", "https://fireworks.ai/account/api-keys", False,
       "https://api.fireworks.ai/inference/v1"),
    _P("openrouter", "OpenRouter", "openai_chat", "openai/gpt-4o", "OPENROUTER_API_KEY",
       "OpenRouter API key", "https://openrouter.ai/keys", True, "https://openrouter.ai/api/v1"),
    _P("perplexity", "Perplexity", "openai_chat", "sonar", "PERPLEXITY_API_KEY",
       "Perplexity API key", "https://www.perplexity.ai/settings/api", False, "https://api.perplexity.ai"),
    # the catch-all compatible gateways (anything OpenAI/Anthropic-compatible)
    _P("openai_compat", "OpenAI-compatible gateway", "openai_chat", "", "OPENAI_API_KEY",
       "OpenAI-compatible gateway API key", None, False),
    _P("anthropic_compat", "Claude-compatible gateway", "anthropic_sdk", "claude-opus-4-8", "ANTHROPIC_API_KEY",
       "Claude-compatible gateway API key", None, False),
]

BY_ID: Dict[str, Provider] = {p.id: p for p in REGISTRY}


def list_providers() -> List[dict]:
    """The public registry for the UI — every provider's wiring, NEVER a key (keys are session-only)."""
    return [p.public() for p in REGISTRY]


def validate_registry() -> dict:
    """Verify every provider is correctly wired: valid transport, non-empty key_label/key_env, a model default (except
    the open compat gateway), and that NO provider record carries a key value (session-only invariant at config level)."""
    problems = []
    for p in REGISTRY:
        if p.transport not in _TRANSPORTS:
            problems.append((p.id, f"bad transport {p.transport}"))
        if not p.key_env or not p.key_label:
            problems.append((p.id, "missing key_env/key_label"))
        if not p.default_model and p.id != "openai_compat":
            problems.append((p.id, "missing default_model"))
        # the hard invariant at the config layer: a provider record must never contain a key/secret value
        for fld, val in asdict(p).items():
            if fld not in ("key_env", "key_label") and isinstance(val, str) and ("sk-" in val or "key-" in val.lower()
                                                                                 and "_key" not in fld):
                problems.append((p.id, f"a key-like literal in {fld}!"))
    free = [p.id for p in REGISTRY if p.free_no_card]
    return {"count": len(REGISTRY), "transports": sorted({p.transport for p in REGISTRY}),
            "free_no_card": free, "problems": problems, "ok": not problems,
            "note": "registry widened to the major providers + compatible gateways; each wired with transport/auth-env/"
                    "model/get-key; no key value stored in any record (session-only invariant holds at config level)"}


def validate_key_wiring(provider_id: str, key: Optional[str]) -> dict:
    """Wire a key to a provider and report the connection verdict. A live 1-token validation call is PENDING-REAL-STACK
    (egress BLOCKED); here we verify the WIRING (known provider, key present, transport resolved) and mark the live
    call pending — never faking a connection. Empty key ⇒ clear 'no key' (run the verified engine without a provider)."""
    p = BY_ID.get(provider_id)
    if p is None:
        return {"ok": False, "stage": "wiring", "message": f"unknown provider '{provider_id}'"}
    if not key:
        return {"ok": False, "stage": "wiring", "message": "no key entered — paste a key, or skip to run the verified "
                "engine without a provider (the key is session-only: held in this tab, never stored)"}
    return {"ok": None, "stage": "live_call", "transport": p.transport, "model": p.default_model,
            "message": "wiring verified (provider + transport + key present); the live 1-token validation call is "
                       "PENDING-REAL-STACK (egress BLOCKED here) — never faked", "live": "pending-real-stack",
            "key_persisted": False}
