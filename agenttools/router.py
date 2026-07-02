"""
agenttools/router.py — expose only a small, task-matched SUBSET of the catalog per request.
==============================================================================================
★ Prime Directive 1 (10H directive) ★: "300 tools" is catalog SIZE, not exposed-per-request count.
Web-verified (2026-07): models measurably lose tool-call reliability past a handful of exposed tools —
"the real question is how often it actually returns valid tool_calls out of 10 tries, not whether docs
say 'supported'". This router is the STRUCTURAL guarantee that one request never sees the whole catalog:
it always sees a small, keyword-scored, task-matched subset (default cap 6), mirroring
`intent.py::_keyword_intent`'s Stage-1 pattern (local, sub-ms, no network). A locally-imperfect shortlist
just means the model has slightly fewer options that turn — never a wrong answer, since routing is
advisory (which tools to OFFER), not a classification decision with a correctness bar of its own.

`to_wire_shape()` adapts the registry's canonical Anthropic-native shape to whatever the provider's
transport needs — reusing `claude_agent.py::claude_generate`'s EXACT provider split
(`provider in ("anthropic", "anthropic_compat")` → native; everything else → OpenAI-compatible
`/chat/completions`, which is what Ollama's tool-calling also expects, web-confirmed 2026-07).
"""
from __future__ import annotations

from typing import List, Optional

from agenttools.registry import Tool, all_tools

DEFAULT_MAX_TOOLS = 6

# providers whose live transport is the Anthropic Messages SDK (native tool-use shape). Every other
# provider in provider.py's registry rides the OpenAI-compatible /chat/completions surface — mirrors
# claude_agent.py::claude_generate's own `provider in (...)` split verbatim (no new vocabulary invented).
_ANTHROPIC_NATIVE = ("anthropic", "anthropic_compat")


def _score(text: str, tool: Tool) -> int:
    """Local keyword overlap score (no network, no model call). Ties (including all-zero) are broken by
    stable sort, i.e. registration order — deterministic, not random filler."""
    t = text.lower()
    return sum(1 for kw in tool.keywords if kw.lower() in t)


def select_tools(text: str, max_tools: int = DEFAULT_MAX_TOOLS, *,
                 catalog: Optional[List[Tool]] = None) -> List[Tool]:
    """Rank the catalog by local keyword overlap with `text`; return the top `max_tools`.

    ★ Structural guarantee ★: `len(result) <= max_tools` ALWAYS, independent of catalog size — this is
    the mechanism that keeps a 300-entry catalog from ever reaching the model in one request. Callers
    that want tool-calling OFF entirely must not call select_tools at all (an empty/ambiguous `text`
    still returns up to `max_tools` score-0 tools in registration order, not an empty list — "no
    keywords matched" is not the same request as "tools disabled")."""
    pool = catalog if catalog is not None else all_tools()
    ranked = sorted(pool, key=lambda tl: _score(text, tl), reverse=True)
    return ranked[:max(0, max_tools)]


def to_wire_shape(tools: List[Tool], provider: str) -> List[dict]:
    """Adapt the canonical {name, description, input_schema} Tool shape to the provider's wire format.

    `provider` in `("anthropic", "anthropic_compat")` → passthrough (already Anthropic's native tool
    shape). Every other registered provider (openai, groq, openai_compat, ollama_local, mistral, cohere,
    deepseek, xai, together, fireworks, openrouter, perplexity — provider.py's _OPENAI_CHAT_REGISTRY)
    speaks OpenAI-compatible /chat/completions → wrap as
    `{"type": "function", "function": {name, description, parameters}}`, the exact shape Ollama's own
    tool-calling docs specify (web-confirmed 2026-07) and standard OpenAI-compatible gateways expect."""
    if provider in _ANTHROPIC_NATIVE:
        return [{"name": t.name, "description": t.description, "input_schema": t.input_schema} for t in tools]
    return [{"type": "function",
             "function": {"name": t.name, "description": t.description, "parameters": t.input_schema}}
            for t in tools]
