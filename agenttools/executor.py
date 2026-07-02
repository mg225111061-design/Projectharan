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

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from agenttools.envelope import (BLOCKED, EXEC_FAILED, INVALID_INPUT, NOT_FOUND, TIMEOUT, UNDECIDABLE,
                                 WRITE, BlockedError, UndecidableError, is_to_api_shaped, make_envelope)
from agenttools.registry import FOLD_ELIGIBLE
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


def _map_exception(e: BaseException) -> tuple:
    """Map an in-tool exception to the closest of the six §1.3 codes — every crash becomes an honest
    envelope, never a propagated exception, never a seventh invented code."""
    import subprocess
    if isinstance(e, UndecidableError):
        return UNDECIDABLE, "tool cannot decide (honest DECLINE at the tool layer)"
    if isinstance(e, BlockedError):
        return BLOCKED, "blocked (tool-stated reason in detail)"
    if isinstance(e, (TimeoutError, subprocess.TimeoutExpired)):
        return TIMEOUT, "budget/timeout exceeded"
    if isinstance(e, (PermissionError, ConnectionError)):
        return BLOCKED, "permission/network blocked"
    if isinstance(e, FileNotFoundError):
        return NOT_FOUND, "path/file not found"
    if isinstance(e, (ValueError, KeyError)):     # tools reject bad/escaping inputs with ValueError (_safe_path)
        return INVALID_INPUT, "input rejected by the tool's validation"
    return EXEC_FAILED, "tool crashed"


def execute_enveloped(name: str, arguments: Optional[Dict[str, Any]] = None, *,
                      allow_write: bool = False) -> Dict[str, Any]:
    """카탈로그-v2 §1: run one tool call and return the SINGLE Result-Envelope shape (envelope.py). This is
    the v2 execution path; `execute()` above stays byte-identical for the live wire loop (toolcall.py) until
    the pipeline migrates wholesale — Tier-A minimal blast radius, both paths share the same tool fns.

    Contract enforced HERE, structurally, for every current and future tool:
      * failures → one of the SIX §1.3 codes (unknown tool→NOT_FOUND, bad args/ValueError→INVALID_INPUT,
        FileNotFoundError→NOT_FOUND, timeout→TIMEOUT, permission/network→BLOCKED, crash→EXEC_FAILED);
      * WRITE-sandbox tools are REFUSED (BLOCKED) unless `allow_write=True` — the §1.5/R7 safe_checkpoint
        gate hook: only the checkpoint-gated pipeline path may pass it (R군 wires the actual checkpoint);
      * a grade rides ONLY in `verdict`, lifted from a FOLD-ELIGIBLE tool's payload key "verdict" and only
        when to_api-shaped; a non-FOLD tool's verdict-shaped key is STRIPPED with a visible label (RF-5:
        no grade on I/O — and the build gate asserts no live tool ever trips this);
      * the tool's declared §1.4 honest labels are auto-attached to every envelope;
      * cost.wall_ms is measured; subprocess_ct is None (= not yet instrumented — honest unknown, not 0)."""
    t0 = time.perf_counter()
    tool = _get_tool(name)
    if tool is None:
        return make_envelope(name, False, error_code=NOT_FOUND, error_message=f"unknown tool: {name!r}")
    labels = list(tool.labels)
    if tool.sandbox == WRITE and not allow_write:
        return make_envelope(name, False, error_code=BLOCKED, labels=labels,
                             error_message="WRITE tool refused: requires the R7 safe_checkpoint gate "
                                           "(allow_write=True is passed only by the checkpoint-gated path)",
                             wall_ms=(time.perf_counter() - t0) * 1000.0)
    args = arguments if isinstance(arguments, dict) else {}
    try:
        raw = tool.fn(**args)
    except TypeError as e:                        # wrong/missing/extra arguments — a model-shaped mistake
        return make_envelope(name, False, error_code=INVALID_INPUT, labels=labels,
                             error_message=f"bad arguments for {name!r}", error_detail=str(e),
                             wall_ms=(time.perf_counter() - t0) * 1000.0)
    except Exception as e:                        # noqa: BLE001 — §1.3: every crash becomes an envelope
        code, msg = _map_exception(e)
        return make_envelope(name, False, error_code=code, labels=labels,
                             error_message=msg, error_detail=f"{type(e).__name__}: {e}",
                             wall_ms=(time.perf_counter() - t0) * 1000.0)
    wall_ms = (time.perf_counter() - t0) * 1000.0
    verdict = None
    result: Any = raw
    if isinstance(raw, dict) and is_to_api_shaped(raw.get("verdict")):
        if tool.tier == FOLD_ELIGIBLE:            # §1.1: only a FOLD tool may grade, only via to_api shape
            verdict = raw["verdict"]
            result = {k: v for k, v in raw.items() if k != "verdict"}
        else:                                     # RF-5 violation — strip VISIBLY, never silently pass a grade
            result = {k: v for k, v in raw.items() if k != "verdict"}
            labels.append("verdict_stripped_non_fold_tool")
    return make_envelope(name, True, result=result, verdict=verdict, labels=labels, wall_ms=wall_ms)
