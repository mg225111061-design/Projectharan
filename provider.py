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
VALID_PROVIDERS = (_ANTHROPIC, _ANTHROPIC_COMPAT, _OPENAI_COMPAT)

DEFAULT_MODEL = "claude-opus-4-8"


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
    return None


def resolve_key() -> Optional[str]:
    """Server/CLI key fallback ONLY. Returns the env key (HARAN_KEY first) or None. The caller uses it
    for exactly one call and drops it; it is never stored here. The web UI path passes its own key and
    never touches this. (claude_agent never calls this — it only ever receives the key as an argument.)"""
    return (os.environ.get("HARAN_KEY") or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("OPENAI_API_KEY") or None)


def is_openai(p: Optional[str] = None) -> bool:
    return (p or provider_name()) == _OPENAI_COMPAT


@dataclass
class Config:
    provider: str
    model: str
    base_url: Optional[str]
    has_env_key: bool          # whether a key is available in env (bool only — never the key itself)


def config() -> Config:
    p = provider_name()
    return Config(provider=p, model=model(), base_url=base_url(p), has_env_key=bool(resolve_key()))
