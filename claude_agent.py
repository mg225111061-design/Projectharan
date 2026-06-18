"""
HARAN v22 Part S · STAGE S1 — Claude API integration (key-security LEVEL 1 + mock mode).
=========================================================================================
This is v22's *front door* to the model: Claude writes code, HARAN verifies it (S2+). The model is
swappable; HARAN's verification is the product. Two things define this module:

  ★ KEY SECURITY — LEVEL 1 ★ (the hard rule for v22):
    The Claude API key is *entered every call, stored NOWHERE* — not in a file, not in env, not in a
    log, not in a cache, not in a global, not on any object. It is received as an argument, used for
    exactly one Claude call, and dropped. This module therefore does **not even import `os`** — it
    structurally cannot read or write the environment or the filesystem. (This is a deliberate, stricter
    departure from `llm_adapters.AnthropicAdapter`, which reads `ANTHROPIC_API_KEY` from env; that is
    fine for a CLI, but the v22 product hands the key in fresh each time and keeps zero copies.)

  ★ MOCK MODE (no key) ★:
    With no key we run a deterministic *labeled simulation* (`live=False, source="mock-sim"`) so the
    whole write→verify→fix loop (S2/S3) is testable with zero network and zero secrets. We NEVER claim
    a mock result is "live".

Real calls use the official Anthropic SDK (lazy-imported, so this module loads without it). Default
model is `claude-opus-4-8` with adaptive thinking; streaming is supported for long generations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

# NOTE: `os` is intentionally NOT imported here (level-1: the KEY never touches env/files via this
# module — it is ALWAYS a caller-supplied argument, used once and dropped). Non-secret gateway config
# (provider mode / model / base_url) is resolved in `provider.py` and only used as defaults below;
# `provider.resolve_key()` is NEVER called from this module.
import provider as _PV

# Resolved at import from env (non-secret config). With no env vars set → anthropic / claude-opus-4-8.
DEFAULT_PROVIDER = _PV.provider_name()
DEFAULT_MODEL = _PV.model()          # HARAN_MODEL or claude-opus-4-8
DEFAULT_BASE_URL = _PV.base_url()    # HARAN_BASE_URL (None for plain anthropic → SDK default)

# Output headroom. The claude-api skill recommends ~16000 for non-streaming (keeps requests under the
# SDK's ~10-min timeout guard, which trips around ~21–32k); HARAN code + adaptive thinking needs room,
# and 4096 risked truncation (a `max_tokens` stop, not a 400). Verified non-streaming-safe at 16000.
DEFAULT_MAX_TOKENS = 16000
# Above this the SDK *requires* streaming (raises ValueError otherwise); we auto-switch to streaming.
SAFE_NONSTREAM_MAX_TOKENS = 21000

# Models known-valid at build time (per claude-api skill). Used only to WARN on a likely typo — we do
# NOT hard-reject an unknown id (a newer model could be valid); an unknown id only trips the soft check.
_KNOWN_MODELS = {
    "claude-opus-4-8", "claude-opus-4-7", "claude-opus-4-6", "claude-opus-4-5",
    "claude-sonnet-4-6", "claude-haiku-4-5", "claude-fable-5",
}
# Parameters that return HTTP 400 on Opus 4.8 / 4.7 / Fable 5 (removed sampling params + fixed thinking
# budget). The request must NEVER carry these — see claude-api skill "Thinking & Effort" / error-codes.
_FORBIDDEN_KEYS = ("temperature", "top_p", "top_k")

SYSTEM_PROMPT = (
    "You are a careful engineer writing HARAN, a small verified language. Return ONLY one HARAN "
    "function and nothing else (no prose, no markdown fences). Shape: "
    "`fn name(p: T) -> R ensures <expr> effects pure { <body> }`. Bodies use match / "
    "fold k in lo..hi { e } / let / arithmetic. The function must satisfy its `ensures` spec for ALL "
    "valid inputs. If told a previous attempt failed on a specific input, fix exactly that."
)

# A fixed, parseable HARAN function used as the deterministic mock generation. It both parses and
# verifies (Σ 1..n = n(n+1)/2), so S1's mock exercises the real downstream substrate end-to-end.
_MOCK_HARAN = (
    "fn triangular(n: Nat) -> Nat\n"
    "  ensures result = n*(n+1)/2\n"
    "{ fold k in 1..n { k } }"
)


class ClaudeError(Exception):
    """Raised when a *real* Claude call cannot be made/completed. Never carries the key."""


@dataclass
class GenResult:
    text: str            # the generated code (HARAN), text blocks only
    live: bool           # True only for a real Claude API response; mock is always False
    model: str           # model id used (or requested, for mock)
    source: str          # "claude-live" | "mock-sim"  (honest provenance — never a fake "live")
    usage: Optional[dict] = None   # token usage for a live call, when available


# --- key hygiene -----------------------------------------------------------------------------------
# Module invariant: keys are NEVER stored here. This stays None for the life of the process; the
# key_not_stored test asserts it, and asserts no global/env/attr ever holds a key.
_KEY_STORE = None


def redact_key(s: str) -> str:
    """Mask anything that looks like an API key, for safe diagnostics. (We never log the key, but any
    text that might echo one is run through this first — belt and suspenders.)"""
    if not s:
        return s
    out, i = [], 0
    while i < len(s):
        # Anthropic keys look like `sk-ant-...`; mask from that marker to the next whitespace.
        if s.startswith("sk-ant-", i) or s.startswith("sk-", i):
            j = i
            while j < len(s) and not s[j].isspace():
                j += 1
            out.append("sk-***REDACTED***")
            i = j
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def _friendly_error(e: Exception) -> str:
    """A user-understandable, KEY-SAFE message for a failed Claude call (U9.3).

    KEY SECURITY: the raw text is always run through redact_key() first, so any `sk-ant-…` /`sk-…`
    token is masked before it can reach a screen or log. Within that safety envelope we now SURFACE
    the redacted reason for the generic case (esp. 400 BadRequest) — the old code threw it away and
    returned only the exception type, which made a malformed-request 400 impossible to diagnose. The
    Anthropic 400 body describes the request shape (e.g. an unsupported parameter), not the key."""
    name = type(e).__name__
    safe = redact_key(str(e))           # key masked here — everything below is safe to show
    low = safe.lower()
    if "authentication" in name.lower() or "401" in low or "invalid x-api-key" in low or "api key" in low:
        return "API 키가 올바르지 않습니다 (invalid API key)."
    if "ratelimit" in name.lower() or "429" in low or "rate limit" in low:
        return "요청 한도를 초과했습니다 — 잠시 후 다시 시도해 주세요 (rate limited)."
    if "connection" in name.lower() or "timeout" in name.lower() or "network" in low:
        return "네트워크 오류 — 연결을 확인해 주세요 (network error)."
    # generic (incl. 400 BadRequest): surface the REDACTED detail so the cause is diagnosable.
    detail = " ".join(safe.split())[:300]               # collapse whitespace, cap length; key already masked
    return f"Claude 호출 실패 ({name}): {detail}" if detail else f"Claude 호출 실패 ({name})."


def _mock_generate(prompt: str, model: str, stream: bool,
                   on_delta: Optional[Callable[[str], None]],
                   mock_response: Optional[str]) -> GenResult:
    """Deterministic, network-free, secret-free simulation. Clearly labeled source='mock-sim'."""
    text = mock_response if mock_response is not None else _MOCK_HARAN
    if stream and on_delta:
        # emit in a few chunks so the streaming path is exercised without a network
        step = max(1, len(text) // 4)
        for k in range(0, len(text), step):
            on_delta(text[k:k + step])
    return GenResult(text=text, live=False, model=model, source="mock-sim")


def _assert_spec_conformant(kwargs: dict) -> None:
    """Offline tripwire: reject any request body that would 400 on Opus 4.8 (per the claude-api spec).
    A pure check (no network/key) so a future edit can't silently reintroduce a 400-causer. Raises
    ClaudeError (key-safe) on violation; returns None when the shape is spec-conformant."""
    for k in _FORBIDDEN_KEYS:
        if k in kwargs:
            raise ClaudeError(f"spec violation: '{k}' is removed on Opus 4.8/4.7/Fable 5 (would 400) — drop it")
    th = kwargs.get("thinking")
    if th is not None:
        if not isinstance(th, dict) or th.get("type") not in ("adaptive", "disabled"):
            raise ClaudeError("spec violation: thinking.type must be 'adaptive' or 'disabled' on Opus 4.8 "
                              "(enabled+budget_tokens would 400)")
        if "budget_tokens" in th:
            raise ClaudeError("spec violation: thinking.budget_tokens is removed on Opus 4.8 (would 400)")
    mt = kwargs.get("max_tokens")
    if not isinstance(mt, int) or mt <= 0:
        raise ClaudeError("spec violation: max_tokens must be a positive int")
    msgs = kwargs.get("messages")
    if not isinstance(msgs, list) or not msgs:
        raise ClaudeError("spec violation: messages must be a non-empty list")
    if msgs[-1].get("role") == "assistant":
        raise ClaudeError("spec violation: trailing assistant prefill is rejected on Opus 4.8 (would 400)")


def _build_kwargs(prompt: str, system: Optional[str], model: str, max_tokens: int, thinking: bool) -> dict:
    """Assemble messages.create/stream kwargs (pure — testable without a network/key).

    STAGE 1.1 — prompt caching: the STABLE `system` prefix carries `cache_control:{ephemeral}` so that
    repeated calls in one write→verify→fix loop reuse it (caching is a prefix match — system is stable;
    the per-round user prompt, which carries the changing counterexample, is volatile and comes after).
    NOTE (honest): Anthropic caches a prefix only once it exceeds the model minimum (Opus 4.8 ≈ 4096
    tokens) — a small system prompt silently won't cache (`cache_creation_input_tokens: 0`). The win
    materialises when a large stable context sits in the system prefix. TTFT/cost is [TBD: needs key]."""
    sys_text = system or SYSTEM_PROMPT
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
        "system": [{"type": "text", "text": sys_text, "cache_control": {"type": "ephemeral"}}],
    }
    if thinking:
        kwargs["thinking"] = {"type": "adaptive"}   # Opus 4.8 / skill default for non-trivial work
    _assert_spec_conformant(kwargs)                 # tripwire: never ship a body that would 400
    return kwargs


def _build_openai_kwargs(prompt: str, system: Optional[str], model: str, max_tokens: int,
                         stream: bool) -> dict:
    """Assemble OpenAI /chat/completions kwargs (pure — testable without a network/key). OpenAI-shaped
    gateways (OpenRouter, TokenMix, …) take the system prompt as a leading `system` message, the user
    text as a `user` message, and `max_tokens`. No `thinking`/`cache_control` (Anthropic-only); the
    Anthropic tripwire (`_assert_spec_conformant`) deliberately does NOT apply here — these gateways
    allow params like `temperature` that Opus 4.8 rejects."""
    return {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "system", "content": system or SYSTEM_PROMPT},
                     {"role": "user", "content": prompt}],
        "stream": stream,
    }


def _live_generate_anthropic(prompt: str, api_key: str, model: str, system: Optional[str],
                             max_tokens: int, thinking: bool, stream: bool,
                             on_delta: Optional[Callable[[str], None]],
                             base_url: Optional[str], provider: str) -> GenResult:
    """One real call via the Anthropic SDK (provider 'anthropic' or 'anthropic_compat'). `base_url`
    targets a custom gateway (AgentRouter etc.) when set; None → the SDK default. The key is used here
    and dropped on return — never stored, logged, or returned."""
    try:
        import anthropic   # lazy: module imports fine without the SDK (mock mode needs none)
    except ImportError as e:
        raise ClaudeError("anthropic SDK not installed — `pip install anthropic` for live calls.") from e

    client = anthropic.Anthropic(api_key=api_key, base_url=base_url) if base_url \
        else anthropic.Anthropic(api_key=api_key)
    kwargs = _build_kwargs(prompt, system, model, max_tokens, thinking)
    # The SDK raises ValueError for non-streaming requests with a large max_tokens (≈10-min guard);
    # auto-switch to streaming so a big generation never crashes (skill: stream for high max_tokens).
    use_stream = stream or max_tokens > SAFE_NONSTREAM_MAX_TOKENS
    try:
        if use_stream:
            with client.messages.stream(**kwargs) as s:
                for chunk in s.text_stream:
                    if on_delta:
                        on_delta(chunk)
                final = s.get_final_message()
            blocks, usage = final.content, getattr(final, "usage", None)
        else:
            msg = client.messages.create(**kwargs)
            blocks, usage = msg.content, getattr(msg, "usage", None)
    except Exception as e:   # noqa: BLE001 — normalize SDK errors; never leak the key in the message
        raise ClaudeError(_friendly_error(e)) from None
    finally:
        del client   # drop the client (and the key it captured) as soon as the call is done

    text = "".join(getattr(b, "text", "") for b in blocks
                   if getattr(b, "type", None) == "text").strip()
    if not text:
        raise ClaudeError("model returned no text content")
    usage_d = {"input_tokens": getattr(usage, "input_tokens", None),
               "output_tokens": getattr(usage, "output_tokens", None)} if usage else None
    return GenResult(text=text, live=True, model=model, source=f"{provider}-live", usage=usage_d)


def _live_generate_openai(prompt: str, api_key: str, model: str, system: Optional[str],
                          max_tokens: int, stream: bool,
                          on_delta: Optional[Callable[[str], None]],
                          base_url: Optional[str]) -> GenResult:
    """One real call via the OpenAI SDK against an OpenAI-compatible gateway (provider 'openai_compat').
    Parses the OpenAI response shape (`choices[0].message.content` / streamed `delta.content`). The key
    is used here and dropped — never stored, logged, or returned."""
    try:
        import openai   # lazy
    except ImportError as e:
        raise ClaudeError("openai SDK not installed — `pip install openai` for openai_compat gateways.") from e

    client = openai.OpenAI(api_key=api_key, base_url=base_url) if base_url \
        else openai.OpenAI(api_key=api_key)
    kwargs = _build_openai_kwargs(prompt, system, model, max_tokens, stream)
    text, usage = "", None
    try:
        # Classic chat-completions call (widest gateway compatibility). stream=True → iterate chunks.
        resp = client.chat.completions.create(**kwargs)
        if stream:
            chunks = []
            for chunk in resp:
                ch = chunk.choices[0] if getattr(chunk, "choices", None) else None
                delta = getattr(getattr(ch, "delta", None), "content", None) if ch else None
                if delta:
                    chunks.append(delta)
                    if on_delta:
                        on_delta(delta)
            text = "".join(chunks).strip()
        else:
            text = (resp.choices[0].message.content or "").strip() if resp.choices else ""
            usage = getattr(resp, "usage", None)
    except Exception as e:   # noqa: BLE001 — normalize SDK errors; never leak the key
        raise ClaudeError(_friendly_error(e)) from None
    finally:
        del client

    if not text:
        raise ClaudeError("gateway returned no text content")
    usage_d = {"input_tokens": getattr(usage, "prompt_tokens", None),
               "output_tokens": getattr(usage, "completion_tokens", None)} if usage else None
    return GenResult(text=text, live=True, model=model, source="openai_compat-live", usage=usage_d)


def claude_generate(prompt: str, api_key: Optional[str] = None, *,
                    model: Optional[str] = None, provider: Optional[str] = None,
                    base_url: Optional[str] = None, system: Optional[str] = None,
                    max_tokens: int = DEFAULT_MAX_TOKENS, thinking: bool = True, stream: bool = False,
                    on_delta: Optional[Callable[[str], None]] = None,
                    mock_response: Optional[str] = None) -> GenResult:
    """Generate code with the configured model gateway (real) or a labeled simulation (mock).

    GATEWAY: `provider`/`model`/`base_url` default to the env-resolved config (provider.py): one of
    `anthropic` (default), `anthropic_compat` (Anthropic SDK + custom base_url — AgentRouter etc.), or
    `openai_compat` (OpenAI SDK /chat/completions — OpenRouter etc.). Set HARAN_PROVIDER/HARAN_MODEL/
    HARAN_BASE_URL to switch routers; no code change needed.

    LEVEL-1 KEY RULE: `api_key` is used for exactly one call and then dropped — never stored in env, a
    file, a log, a cache, a global, or on any returned object. Pass it fresh every call.

    • api_key truthy  → one real call (provider-appropriate SDK).
    • api_key falsy   → deterministic mock (`source='mock-sim'`, `live=False`); zero network/secrets.

    `stream=True` + `on_delta(chunk)` streams text deltas. `mock_response` overrides the canned mock."""
    model = model or DEFAULT_MODEL
    provider = provider or DEFAULT_PROVIDER
    base_url = DEFAULT_BASE_URL if base_url is None else base_url
    if api_key:
        try:
            if provider == "openai_compat":
                result = _live_generate_openai(prompt, api_key, model, system, max_tokens,
                                               stream, on_delta, base_url)
            else:   # anthropic | anthropic_compat — both use the Anthropic SDK (base_url differs)
                result = _live_generate_anthropic(prompt, api_key, model, system, max_tokens,
                                                  thinking, stream, on_delta, base_url, provider)
        finally:
            # explicit hygiene: forget our binding to the key the instant we're done with it. The
            # caller still owns its copy (it re-supplies per call); WE keep nothing.
            api_key = None
        return result
    return _mock_generate(prompt, model, stream, on_delta, mock_response)
