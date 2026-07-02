"""
search_gate.py — search ON/OFF tool-gating policy (PART 2).
==========================================================
The user controls a single toggle. This module turns that toggle into the **structural** decision of whether a
search tool is even *exposed* to the LLM:

  • OFF → the search tool is NOT in the tool list handed to the model → calling it is impossible → search count = 0.
    This is a guarantee by construction, not a prompt request the model could ignore.
  • ON  → the tool IS exposed (available), BUT the system prompt instructs the model to search ONLY when the
    answer needs fresh/external facts; for things it knows or pure reasoning it answers directly. So ON ≠ search
    every time — the model judges. The toggle is permission, not compulsion.

HONEST SCOPE: no real web-search provider is wired in this repo yet, and this build's sandbox egress-blocks the
open web (see SEARCH_INDEX.md). So this module is the *gate + prompt policy* (the contract OFF=0 / ON=available-
but-judged); connecting the exposed tool to a real search backend is the author's step on Render, under the same
egress + input-validation + no-key-leak rules as the provider path (PART 1). Zero external deps (stdlib only).
"""
from __future__ import annotations

from typing import List

# The (future) web-search tool spec — OpenAI/Anthropic tool-use shape. Exposing it is the ON state; the actual
# execution binds to a real search backend on Render. The description itself encodes "only when needed".
_SEARCH_TOOL = {
    "name": "web_search",
    "description": ("Search the web for FRESH or EXTERNAL facts you do not already know — today's prices, recent "
                    "news, current status of a changing thing. Do NOT use it for static knowledge, definitions, "
                    "math, or reasoning you can do yourself."),
    "input_schema": {"type": "object",
                     "properties": {"query": {"type": "string", "description": "the search query"}},
                     "required": ["query"]},
}

_ON_GUIDANCE = ("A web_search tool is AVAILABLE. Use it ONLY when the answer depends on fresh or external "
                "information you don't already know (e.g. today's exchange rate, recent news, a current status). "
                "For things you already know, static facts, or pure reasoning (e.g. 2+2), answer DIRECTLY without "
                "searching. Searching is the exception, not the default — never search when you already know.")

_OFF_GUIDANCE = ("Web search is OFF. Answer only from your own knowledge; do not claim to have searched. If the "
                 "answer genuinely requires fresh external data you don't have, say so honestly.")


def normalize(search_allowed) -> bool:
    """Coerce a request flag (bool / 'true' / 1 / 'on') to a strict bool. Anything not clearly truthy ⇒ OFF
    (fail-safe: ambiguity defaults to the *more restrictive* state — no accidental search exposure)."""
    if isinstance(search_allowed, bool):
        return search_allowed
    if isinstance(search_allowed, (int, float)):
        return search_allowed != 0
    if isinstance(search_allowed, str):
        return search_allowed.strip().lower() in ("1", "true", "on", "yes", "y")
    return False


def tools_for(search_allowed) -> List[dict]:
    """The tool list handed to the LLM. ★ OFF ⇒ [] (search structurally impossible). ON ⇒ [web_search]."""
    return [dict(_SEARCH_TOOL)] if normalize(search_allowed) else []


def search_available(search_allowed) -> bool:
    """True iff a search tool is actually exposed for this request (i.e. the toggle is ON)."""
    return bool(tools_for(search_allowed))


def system_suffix(search_allowed) -> str:
    """Text appended to the system prompt: ON ⇒ 'only when needed' guidance; OFF ⇒ explicit no-search."""
    return "\n\n" + (_ON_GUIDANCE if normalize(search_allowed) else _OFF_GUIDANCE)


def adversarial_battery() -> dict:
    """OFF ⇒ 0 tools (guaranteed); ON ⇒ exactly the search tool; ambiguous/garbage ⇒ OFF (fail-safe)."""
    out = {}
    out["off_zero_tools"] = tools_for(False) == [] and not search_available(False)
    out["on_exposes_search"] = ([t["name"] for t in tools_for(True)] == ["web_search"]) and search_available(True)
    out["string_on"] = search_available("on") and search_available("true") and search_available("1")
    out["failsafe_off"] = (not search_available(None)) and (not search_available("")) and \
                          (not search_available("maybe")) and (not search_available(0))
    out["off_prompt_says_off"] = "OFF" in system_suffix(False) and "AVAILABLE" not in system_suffix(False)
    out["on_prompt_says_when_needed"] = "ONLY when" in system_suffix(True) and "exception" in system_suffix(True)
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
