"""
agenttools/executor.py — run ONE tool call, real execution, never crash the caller.
=====================================================================================
A tool call is untrusted input shaped by a model (arguments come from an LLM's JSON, not a typed
call-site) — a missing arg, wrong type, unknown tool name, or a bug inside the tool's own `fn` must
never propagate as an exception into the model-conversation loop (`toolcall.py`). Every failure mode
becomes an honest `ToolResult(ok=False, error=...)` that gets fed back to the model exactly like a
successful result would — the model sees its own mistake and can retry, the same "execution-feedback"
shape as `swebench/fix_loop.py::structured_feedback` (a failure is FEEDBACK, not a crash).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from agenttools.registry import get as _get_tool


@dataclass
class ToolResult:
    ok: bool
    output: Any = None
    error: str = ""


def execute(name: str, arguments: Optional[Dict[str, Any]] = None) -> ToolResult:
    """Look up `name` in the registry, call its `fn(**arguments)`, and return a ToolResult. NEVER raises:
    an unknown tool name, a bad-shaped `arguments`, or an exception inside `fn` itself all become
    `ToolResult(ok=False, error=...)` — the caller (toolcall.py) feeds this back to the model unchanged,
    the same way a real tool failure (file not found, grep no-match) would be reported."""
    tool = _get_tool(name)
    if tool is None:
        return ToolResult(ok=False, error=f"unknown tool: {name!r}")
    args = arguments if isinstance(arguments, dict) else {}
    try:
        result = tool.fn(**args)
    except TypeError as e:                      # wrong/missing/extra arguments — a model-shaped mistake
        return ToolResult(ok=False, error=f"bad arguments for {name!r}: {e}")
    except Exception as e:                       # noqa: BLE001 — a bug inside the tool must not crash the loop
        return ToolResult(ok=False, error=f"{name!r} raised {type(e).__name__}: {e}")
    return ToolResult(ok=True, output=result)
