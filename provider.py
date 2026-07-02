"""
provider.py — non-secret gateway/router configuration (the only module that reads the environment).
====================================================================================================
HARAN's model call can target any of the common API gateways/routers. The user picks one with THREE
environment variables; this module resolves them. It deliberately handles only **non-secret config**
(provider mode, model name, base URL). The API KEY stays a per-call argument everywhere else —
`claude_agent.py` never imports `os` and never reads the key from the environment (LEVEL-1).

  HARAN_PROVIDER  one of:
      anthropic         (default) — official Anthropic API (Anthropic SDK, SDK's own base URL)
      anthropic_compat  — Anthropic SDK with a CUSTOM base_url (AgentRouter and other Anthropic-shaped
                          gateways): set HARAN_BASE_URL=https://agentrouter.org/v1
      openai_compat     — OpenAI-shaped gateways (OpenRouter, TokenMix, most others): OpenAI SDK +
                          /chat/completions; set HARAN_BASE_URL=https://openrouter.ai/api/v1
  HARAN_MODEL     model id for the chosen gateway (e.g. claude-opus-4-8, claude-sonnet-4-5-20250929,
                  anthropic/claude-3.5-sonnet, qwen/qwen3-coder). Default: claude-opus-4-8.
  HARAN_BASE_URL  the gateway base URL. Default: none (anthropic mode uses the SDK default).

  HARAN_KEY       the gateway key (read here ONLY as a server/CLI fallback via resolve_key(); the web
                  UI still passes the key per-request and it is never stored). Masked in all output.

So: set HARAN_PROVIDER + HARAN_MODEL + HARAN_BASE_URL (+ HARAN_KEY) and any router works.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

_ANTHROPIC = "anthropic"
_ANTHROPIC_COMPAT = "anthropic_compat"
_OPENAI_COMPAT = "openai_compat"
_OPENAI = "openai"            # PHASE P — native ChatGPT (api.openai.com/v1/chat/completions)
_GEMINI = "gemini"            # PHASE P — native Gemini (generativelanguage.googleapis.com)
_GROQ = "groq"               # PHASE P2 — Groq (OpenAI-compatible; free, no credit card)
# MR.JEFFREY local-Ollama preset — NOT a remote gateway: the engine (real inference incl. quantization) is
# Ollama's, running on whatever machine the SERVER PROCESS itself lives on (self-hosted `python server.py`
# alongside `ollama serve`). A public remote deployment of this server cannot reach the visitor's own
# localhost, so on such a deployment the /api/ollama/status probe honestly reports "not found" — this is
# the correct, honest behavior for that topology, not a bug. Rides the SAME `openai_chat` transport as every
# other family-C provider (Ollama's REST API is OpenAI-compatible at localhost:11434/v1) — zero new transport.
_OLLAMA_LOCAL = "ollama_local"
# §MRJ — the remaining family-C (OpenAI-compatible /chat/completions, Bearer) named providers. Each rides the
# `openai_chat` transport with its own base_url; the author can override base/model in the UI or via env.
_MISTRAL = "mistral"
_COHERE = "cohere"
_DEEPSEEK = "deepseek"
_XAI = "xai"
_TOGETHER = "together"
_FIREWORKS = "fireworks"
_OPENROUTER = "openrouter"
_PERPLEXITY = "perplexity"

DEFAULT_MODEL = "claude-opus-4-8"

# PHASE P — native-endpoint defaults (filled from each vendor's public docs; editable in the UI, never guessed).
_OPENAI_DEFAULT_BASE = "https://api.openai.com/v1"
_GEMINI_DEFAULT_BASE = "https://generativelanguage.googleapis.com/v1beta"
_GROQ_DEFAULT_BASE = "https://api.groq.com/openai/v1"           # OpenAI-compatible /chat/completions
# Ollama's own REST API, confirmed OpenAI-compatible at this path (web-confirmed 2026-07; official desktop
# app since Jul 2025). No key is ever validated by Ollama itself — any non-empty string is accepted.
_OLLAMA_DEFAULT_BASE = "http://localhost:11434/v1"

# §MRJ — family-C registry: id → (base_url, default_model, free_no_card, get_key_url). base_url/model are
# EDITABLE defaults in the UI (HARAN_BASE_URL / HARAN_MODEL override); filled from each vendor's public docs,
# never guessed. Cohere/Fireworks use a vendor-specific compat path / model prefix — confirm on Render.
_OPENAI_CHAT_REGISTRY = {
    _GROQ:       (_GROQ_DEFAULT_BASE, "llama-3.3-70b-versatile", True, "https://console.groq.com/keys"),
    # no universal default model — the local model browser (webapi/local_models.py, real /api/tags query)
    # fills this in from whatever the user actually pulled; get_key_url=None (there is no key to obtain).
    _OLLAMA_LOCAL: (_OLLAMA_DEFAULT_BASE, "", True, None),
    _MISTRAL:    ("https://api.mistral.ai/v1", "mistral-large-latest", False, "https://console.mistral.ai/api-keys"),
    _COHERE:     ("https://api.cohere.ai/compatibility/v1", "command-r-plus", False, "https://dashboard.cohere.com/api-keys"),
    _DEEPSEEK:   ("https://api.deepseek.com/v1", "deepseek-chat", False, "https://platform.deepseek.com/api_keys"),
    _XAI:        ("https://api.x.ai/v1", "grok-2-latest", False, "https://console.x.ai"),
    _TOGETHER:   ("https://api.together.xyz/v1", "meta-llama/Llama-3.3-70B-Instruct-Turbo", False,
                  "https://api.together.ai/settings/api-keys"),
    _FIREWORKS:  ("https://api.fireworks.ai/inference/v1", "accounts/fireworks/models/llama-v3p3-70b-instruct", False,
                  "https://fireworks.ai/account/api-keys"),
    _OPENROUTER: ("https://openrouter.ai/api/v1", "openai/gpt-4o", True, "https://openrouter.ai/keys"),
    _PERPLEXITY: ("https://api.perplexity.ai", "sonar", False, "https://www.perplexity.ai/settings/api"),
}

# all 14: 2 anthropic-family + native openai/gemini + the open compat gateway + the 9 openai_chat named providers
VALID_PROVIDERS = (_ANTHROPIC, _ANTHROPIC_COMPAT, _OPENAI_COMPAT, _OPENAI, _GEMINI,
                   *_OPENAI_CHAT_REGISTRY.keys())

# Per-provider default model ids (free, no-card tiers for groq/gemini). Editable in the UI; never guessed.
DEFAULT_MODELS = {
    _ANTHROPIC: DEFAULT_MODEL,
    _ANTHROPIC_COMPAT: DEFAULT_MODEL,
    _OPENAI: "gpt-4o",
    _OPENAI_COMPAT: "",                                         # gateway-specific; user fills it in
    _GEMINI: "gemini-3.5-flash",                                # free tier, no card (per directive; editable in UI)
    **{pid: meta[1] for pid, meta in _OPENAI_CHAT_REGISTRY.items()},
}


def default_model_for(p: Optional[str] = None) -> str:
    """The prefilled default model for a provider (free-tier ids for groq/gemini). Editable in the UI."""
    return DEFAULT_MODELS.get(p or provider_name(), DEFAULT_MODEL)


def provider_name() -> str:
    p = (os.environ.get("HARAN_PROVIDER") or os.environ.get("PROVIDER") or _ANTHROPIC).strip().lower()
    return p if p in VALID_PROVIDERS else _ANTHROPIC


def model() -> str:
    return (os.environ.get("HARAN_MODEL") or DEFAULT_MODEL).strip()


def base_url(p: Optional[str] = None) -> Optional[str]:
    """Resolve the base URL for the chosen provider. HARAN_BASE_URL wins; otherwise a provider-specific
    fallback (ANTHROPIC_BASE_URL / OPENAI_BASE_URL). Plain `anthropic` returns None → the Anthropic SDK
    uses its own default (or its own ANTHROPIC_BASE_URL handling)."""
    p = p or provider_name()
    bu = os.environ.get("HARAN_BASE_URL")
    if bu:
        return bu.strip()
    if p == _OPENAI_COMPAT:
        return (os.environ.get("OPENAI_BASE_URL") or "").strip() or None
    if p == _ANTHROPIC_COMPAT:
        return (os.environ.get("ANTHROPIC_BASE_URL") or "").strip() or None
    if p == _OPENAI:                                              # native ChatGPT
        return (os.environ.get("OPENAI_BASE_URL") or _OPENAI_DEFAULT_BASE).strip()
    if p == _GEMINI:                                              # native Gemini
        return (os.environ.get("GEMINI_BASE_URL") or _GEMINI_DEFAULT_BASE).strip()
    if p in _OPENAI_CHAT_REGISTRY:                                # groq + the named OpenAI-compatible providers
        return _OPENAI_CHAT_REGISTRY[p][0]
    return None


def transport_kind(p: Optional[str] = None) -> str:
    """Which wire protocol the chosen provider speaks (PHASE P). The proposer selects its HTTP shape from this:
      • anthropic_sdk   — Anthropic Messages API (official or anthropic_compat gateway)
      • openai_chat     — POST {base}/chat/completions (native OpenAI and every openai_compat gateway)
      • gemini_generate — POST {base}/models/{model}:generateContent?key=… (native Gemini)"""
    p = p or provider_name()
    if p in (_ANTHROPIC, _ANTHROPIC_COMPAT):
        return "anthropic_sdk"
    if p == _GEMINI:
        return "gemini_generate"
    return "openai_chat"                                          # openai + openai_compat + groq


def resolve_key_for(p: Optional[str] = None) -> Optional[str]:
    """Provider-specific key fallback for the server/CLI path. HARAN_KEY always wins; otherwise the vendor's
    own var (OPENAI_API_KEY / GEMINI_API_KEY / ANTHROPIC_API_KEY). Returns the key or None — never logged,
    never stored, never phoned home; the web UI passes its own key per request and never touches this."""
    p = p or provider_name()
    if os.environ.get("HARAN_KEY"):
        return os.environ["HARAN_KEY"].strip()
    if p == _OLLAMA_LOCAL:            # Ollama never validates the key; any non-empty string is accepted
        return (os.environ.get("OLLAMA_API_KEY") or "ollama").strip()
    if p == _OPENAI:
        return (os.environ.get("OPENAI_API_KEY") or "").strip() or None
    if p == _GEMINI:
        return (os.environ.get("GEMINI_API_KEY") or "").strip() or None
    if p in (_ANTHROPIC, _ANTHROPIC_COMPAT):
        return (os.environ.get("ANTHROPIC_API_KEY") or "").strip() or None
    if p in _OPENAI_CHAT_REGISTRY:                                    # groq + named OpenAI-compatible providers
        return (os.environ.get(f"{p.upper()}_API_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip() or None
    return (os.environ.get("OPENAI_API_KEY") or "").strip() or None   # openai_compat gateways


def resolve_key() -> Optional[str]:
    """Server/CLI key fallback ONLY. Returns the env key (HARAN_KEY first) or None. The caller uses it
    for exactly one call and drops it; it is never stored here. The web UI path passes its own key and
    never touches this. (claude_agent never calls this — it only ever receives the key as an argument.)"""
    return (os.environ.get("HARAN_KEY") or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("OPENAI_API_KEY") or None)


def is_openai(p: Optional[str] = None) -> bool:
    return (p or provider_name()) == _OPENAI_COMPAT


def is_openai_native(p: Optional[str] = None) -> bool:
    return (p or provider_name()) == _OPENAI


def is_gemini(p: Optional[str] = None) -> bool:
    return (p or provider_name()) == _GEMINI


def is_groq(p: Optional[str] = None) -> bool:
    return (p or provider_name()) == _GROQ


# v26.2 S8 — gateway presets. Each: (provider, base_url, default_model, verified_source).
# base_urls/models are EDITABLE defaults in the UI; only fill from documentation, never guess.
# GLM/Z.ai verified via web search (Z.ai docs + multiple corroborating sources, June 2026):
#   OpenAI-compatible base_url = https://api.z.ai/api/paas/v4/ , model id e.g. glm-4.6 (glm-4.7 also).
#   NOTE: "GLM-5.2" is NOT a verified model id anywhere — use the exact id from your Z.ai console.
GATEWAY_PRESETS = {
    "Claude (official)": (_ANTHROPIC, None, DEFAULT_MODEL, "anthropic"),
    "ChatGPT (OpenAI)":  (_OPENAI, _OPENAI_DEFAULT_BASE, "gpt-4o", "openai docs (native /chat/completions)"),
    "Gemini (Google)":   (_GEMINI, _GEMINI_DEFAULT_BASE, "gemini-3.5-flash", "google docs (generateContent; free, no card)"),
    "Groq":              (_GROQ, _GROQ_DEFAULT_BASE, "llama-3.3-70b-versatile", "groq docs (OpenAI-compatible; free, no card)"),
    "GLM (Z.ai)":        (_OPENAI_COMPAT, "https://api.z.ai/api/paas/v4/", "glm-4.6", "z.ai docs (web-confirmed)"),
    "OpenRouter":        (_OPENAI_COMPAT, "https://openrouter.ai/api/v1", "", "well-known (editable)"),
    "DeepSeek":          (_OPENAI_COMPAT, "https://api.deepseek.com", "deepseek-chat", "well-known (editable)"),
    "Ollama (local)":    (_OLLAMA_LOCAL, _OLLAMA_DEFAULT_BASE, "",
                          "ollama.com docs (web-confirmed 2026-07): OpenAI-compatible /v1/chat/completions "
                          "at localhost:11434; self-hosted only, not reachable from a remote deployment"),
}

# Free, no-credit-card providers (the default way to test the whole site) + where to get a key.
FREE_NO_CARD = (_GEMINI, *(pid for pid, meta in _OPENAI_CHAT_REGISTRY.items() if meta[2]))   # gemini + groq + openrouter
GET_KEY_URL = {
    _GEMINI: "https://aistudio.google.com/apikey",
    _OPENAI: "https://platform.openai.com/api-keys",
    _ANTHROPIC: "https://console.anthropic.com/settings/keys",
    **{pid: meta[3] for pid, meta in _OPENAI_CHAT_REGISTRY.items()},
}


def is_free_no_card(p: Optional[str] = None) -> bool:
    return (p or provider_name()) in FREE_NO_CARD


def get_key_url(p: Optional[str] = None) -> Optional[str]:
    return GET_KEY_URL.get(p or provider_name())


@dataclass
class Config:
    provider: str
    model: str
    base_url: Optional[str]
    has_env_key: bool          # whether a key is available in env (bool only — never the key itself)


def config() -> Config:
    p = provider_name()
    return Config(provider=p, model=model(), base_url=base_url(p), has_env_key=bool(resolve_key()))
