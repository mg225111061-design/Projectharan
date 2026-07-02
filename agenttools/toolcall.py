"""
agenttools/toolcall.py — the execution-feedback loop: expose tools → model calls one → execute → feed
back → repeat until a final answer (or max_rounds). Generalizes the SAME shape as
`swebench/fix_loop.py::solve_with_fixloop` (generate → check → feed the precise failure back → repeat
to pass-or-budget) into the live tool-calling setting: here every round's "failure" is just "the model
asked for a tool", and the "fix" is the tool's real output handed back verbatim.
=====================================================================================================
This is a WHOLLY SEPARATE code path from `claude_agent.py`'s `_build_kwargs` / `_build_openai_kwargs` /
`_live_generate_anthropic` / `_live_generate_openai` — none of those are modified. Reason (found by
direct inspection): `_live_generate_anthropic` raises `ClaudeError("model returned no text content")` on
empty text, which would incorrectly fire on a legitimate tool-only turn (a model that ONLY calls a tool,
no prose, is normal mid-loop behavior, not an error) — reusing that function in place would need a
tool-aware carve-out threaded through code exercised by ~280 existing passing tests. Building a parallel
function keeps that blast radius at zero; every existing caller of `claude_generate` is byte-for-byte
unaffected by this module's existence.

Both providers funnel through the SAME public entry point (`run_with_tools`) and the SAME `executor.py`
call for actually running a tool — the execution loop shape is provider-agnostic by construction (Prime
Directive 5): only the wire encoding of the request/response differs (`router.to_wire_shape`), never the
loop control flow or which module executes the tool.
"""
from __future__ import annotations

import json as _json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import claude_agent as CA
from agenttools.executor import execute as _execute
from agenttools.registry import Tool
from agenttools.router import to_wire_shape

DEFAULT_MAX_ROUNDS = 4
_ANTHROPIC_NATIVE = ("anthropic", "anthropic_compat")


@dataclass
class ToolCallTrace:
    round: int
    tool_name: str
    arguments: dict
    result_ok: bool
    result_summary: str = field(default="")


def _to_anthropic_blocks(msg) -> List[dict]:
    """Anthropic SDK response content blocks → plain dicts (so they round-trip cleanly as the next
    request's assistant turn, without depending on the SDK's own object identity across calls)."""
    out: List[dict] = []
    for block in getattr(msg, "content", []) or []:
        btype = getattr(block, "type", None)
        if btype == "text":
            out.append({"type": "text", "text": getattr(block, "text", "") or ""})
        elif btype == "tool_use":
            out.append({"type": "tool_use", "id": getattr(block, "id", ""),
                       "name": getattr(block, "name", ""), "input": getattr(block, "input", {}) or {}})
    return out


def _normalize_anthropic_response(msg) -> Tuple[str, List[Tuple[str, str, dict]]]:
    """(text, [(tool_use_id, name, input), ...]) from an Anthropic messages.create() response."""
    text_parts, calls = [], []
    for block in getattr(msg, "content", []) or []:
        btype = getattr(block, "type", None)
        if btype == "text":
            text_parts.append(getattr(block, "text", "") or "")
        elif btype == "tool_use":
            calls.append((getattr(block, "id", ""), getattr(block, "name", ""), getattr(block, "input", {}) or {}))
    return "".join(text_parts).strip(), calls


def _normalize_openai_response(msg) -> Tuple[str, List[Tuple[str, str, dict]]]:
    """(text, [(call_id, name, arguments_dict), ...]) from an OpenAI chat.completions message. A
    malformed `arguments` JSON string (a model mistake) degrades to {} rather than raising — the tool
    executor then reports the resulting missing-argument TypeError back to the model as normal feedback."""
    text = (getattr(msg, "content", None) or "").strip()
    calls: List[Tuple[str, str, dict]] = []
    for tc in getattr(msg, "tool_calls", None) or []:
        fn = getattr(tc, "function", None)
        name = getattr(fn, "name", "") if fn else ""
        raw_args = getattr(fn, "arguments", "{}") if fn else "{}"
        try:
            args = _json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
        except Exception:                        # noqa: BLE001 — malformed model JSON, not our bug
            args = {}
        calls.append((getattr(tc, "id", ""), name, args if isinstance(args, dict) else {}))
    return text, calls


def _run_anthropic(prompt: str, api_key: str, model: str, provider: str, base_url: Optional[str],
                   system: Optional[str], max_tokens: Optional[int], tools: List[Tool],
                   max_rounds: int, trace: Optional[List[ToolCallTrace]]) -> CA.GenResult:
    try:
        import anthropic                          # lazy — mirrors claude_agent._live_generate_anthropic
    except ImportError as e:
        raise CA.ClaudeError("anthropic SDK not installed — `pip install anthropic` for live calls.") from e

    client = anthropic.Anthropic(api_key=api_key, base_url=base_url) if base_url \
        else anthropic.Anthropic(api_key=api_key)
    wire_tools = to_wire_shape(tools, provider)
    messages: List[dict] = [{"role": "user", "content": prompt}]
    sys_text = system or CA.SYSTEM_PROMPT
    mt = max_tokens or CA.DEFAULT_MAX_TOKENS
    try:
        for round_i in range(max(1, max_rounds)):
            msg = client.messages.create(model=model, max_tokens=mt,
                                         system=[{"type": "text", "text": sys_text}],
                                         messages=messages, tools=wire_tools)
            text, calls = _normalize_anthropic_response(msg)
            if not calls:
                if not text:
                    raise CA.ClaudeError("model returned no text content")
                usage = getattr(msg, "usage", None)
                usage_d = {"input_tokens": getattr(usage, "input_tokens", None),
                          "output_tokens": getattr(usage, "output_tokens", None)} if usage else None
                return CA.GenResult(text=text, live=True, model=model, source=f"{provider}-live", usage=usage_d)
            messages.append({"role": "assistant", "content": _to_anthropic_blocks(msg)})
            tool_results = []
            for call_id, name, args in calls:
                r = _execute(name, args)
                if trace is not None:
                    trace.append(ToolCallTrace(round_i + 1, name, args, r.ok,
                                               str(r.output) if r.ok else r.error))
                tool_results.append({"type": "tool_result", "tool_use_id": call_id,
                                     "content": str(r.output) if r.ok else f"ERROR: {r.error}",
                                     "is_error": not r.ok})
            messages.append({"role": "user", "content": tool_results})
        raise CA.ClaudeError(f"tool loop exceeded max_rounds={max_rounds} without a final answer")
    except CA.ClaudeError:
        raise
    except Exception as e:                        # noqa: BLE001 — normalize SDK errors; never leak the key
        raise CA.ClaudeError(CA._friendly_error(e)) from None
    finally:
        del client


def _run_openai(prompt: str, api_key: str, model: str, base_url: Optional[str], system: Optional[str],
                max_tokens: Optional[int], tools: List[Tool], max_rounds: int,
                trace: Optional[List[ToolCallTrace]]) -> CA.GenResult:
    try:
        import openai                              # lazy — mirrors claude_agent._live_generate_openai
    except ImportError as e:
        raise CA.LLMError("openai SDK not installed — `pip install openai` for openai-compatible gateways.") from e

    client = openai.OpenAI(api_key=api_key, base_url=base_url) if base_url else openai.OpenAI(api_key=api_key)
    wire_tools = to_wire_shape(tools, "openai_compat")   # any non-anthropic provider → the wrapped shape
    sys_text = system or CA.SYSTEM_PROMPT
    mt = max(max_tokens or CA.DEFAULT_MAX_TOKENS, CA.OPENAI_MIN_MAX_TOKENS)
    messages: List[dict] = [{"role": "system", "content": sys_text}, {"role": "user", "content": prompt}]
    try:
        for round_i in range(max(1, max_rounds)):
            resp = client.chat.completions.create(model=model, max_tokens=mt, messages=messages,
                                                  tools=wire_tools, temperature=0.2,
                                                  extra_body=CA.OPENAI_EXTRA_BODY)
            choice = resp.choices[0] if getattr(resp, "choices", None) else None
            msg = choice.message if choice else None
            text, calls = _normalize_openai_response(msg) if msg is not None else ("", [])
            if not calls:
                if not text:
                    raise CA.LLMError(f"gateway returned an EMPTY response for model '{model}' with tools "
                                      "exposed — check the model id/key/max_tokens as usual.")
                usage = getattr(resp, "usage", None)
                usage_d = {"input_tokens": getattr(usage, "prompt_tokens", None),
                          "output_tokens": getattr(usage, "completion_tokens", None)} if usage else None
                return CA.GenResult(text=text, live=True, model=model, source="openai_compat-live", usage=usage_d)
            messages.append({"role": "assistant", "content": (msg.content or None),
                             "tool_calls": [{"id": cid, "type": "function",
                                           "function": {"name": name, "arguments": _json.dumps(args)}}
                                          for cid, name, args in calls]})
            for call_id, name, args in calls:
                r = _execute(name, args)
                if trace is not None:
                    trace.append(ToolCallTrace(round_i + 1, name, args, r.ok,
                                               str(r.output) if r.ok else r.error))
                messages.append({"role": "tool", "tool_call_id": call_id,
                                 "content": str(r.output) if r.ok else f"ERROR: {r.error}"})
        raise CA.LLMError(f"tool loop exceeded max_rounds={max_rounds} without a final answer")
    except CA.LLMError:
        raise
    except Exception as e:                         # noqa: BLE001 — normalize SDK errors; never leak the key
        raise CA.LLMError(CA._friendly_error(e)) from None
    finally:
        del client


def run_with_tools(prompt: str, api_key: Optional[str] = None, *,
                   tools: List[Tool],
                   model: Optional[str] = None, provider: Optional[str] = None,
                   base_url: Optional[str] = None, system: Optional[str] = None,
                   max_tokens: Optional[int] = None, max_rounds: int = DEFAULT_MAX_ROUNDS,
                   mock_response: Optional[str] = None,
                   trace: Optional[List[ToolCallTrace]] = None) -> CA.GenResult:
    """Run ONE user turn with `tools` exposed, executing any tool the model calls and feeding the result
    back, until the model returns plain text or `max_rounds` is exhausted.

    `tools` is normally `router.select_tools(prompt)` — a SMALL, task-matched subset, never the whole
    catalog (Prime Directive 1: dumping 300 tools at once measurably degrades reliability). Empty
    `tools` (no live capability confirmed, or the router found nothing worth exposing) falls straight
    through to `claude_agent.claude_generate` with NO tools parameter at all — the exact plain
    write→verify→fix path every existing caller already uses; tool-calling is strictly additive, never a
    replacement code path when it doesn't apply.

    No `api_key` → mock mode: deciding WHETHER to call a tool is a live-model judgment call this loop
    cannot simulate honestly, so mock mode never fabricates a tool call — it returns `mock_response` (or
    the default HARAN mock) exactly like a tools-disabled `claude_generate` call would (`source='mock-
    sim'`), so the whole pipeline stays testable with zero network/secrets.

    `trace`, if given a list, is appended with one `ToolCallTrace` per executed tool call (round, name,
    arguments, ok, summary) — purely observational; omitting it costs nothing."""
    model = model or CA.DEFAULT_MODEL
    provider = provider or CA.DEFAULT_PROVIDER
    if not tools:
        return CA.claude_generate(prompt, api_key, model=model, provider=provider, base_url=base_url,
                                  system=system, max_tokens=max_tokens or CA.DEFAULT_MAX_TOKENS,
                                  mock_response=mock_response)
    if not api_key:
        return CA._mock_generate(prompt, model, False, None, mock_response)

    resolved_base = CA.normalize_base_url(CA._resolve_base_url(provider, base_url))
    try:
        if provider in _ANTHROPIC_NATIVE:
            result = _run_anthropic(prompt, api_key, model, provider, resolved_base, system, max_tokens,
                                    tools, max_rounds, trace)
        else:
            result = _run_openai(prompt, api_key, model, resolved_base, system, max_tokens,
                                 tools, max_rounds, trace)
    finally:
        api_key = None                            # same key-hygiene discipline as claude_agent.claude_generate
    return result
