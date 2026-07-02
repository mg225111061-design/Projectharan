"""
agenttools/envelope.py — 카탈로그-v2 §1 공통 계약: the ONE Result-Envelope shape + 6 error codes + 3 sandbox classes.
=====================================================================================================================
Every tool execution on the v2 path returns EXACTLY this envelope (§1.1) — built HERE and only here, by the
executor, never hand-assembled by individual tools. That centralization is the point: the spec's stated failure
mode is "개별 도구가 봉투를 제각각 만든다" (each tool inventing its own dict), and the structural fix is a single
constructor the executor owns. Tool `fn`s keep returning their raw payloads; `executor.execute_enveloped()` wraps
them (Tier-A: minimal blast radius — the 37 live tools change registration metadata only, not return shapes).

    {
      "ok": bool,          # execution success (NOT "the result is good")
      "tool": str,
      "result": <json> | None,                      # when ok
      "error": {code, message, detail} | None,      # when not ok — code ∈ ERROR_CODES (§1.3, exactly 6)
      "verdict": <kernel_verdict.to_api dict> | None,  # ONLY a FOLD-ELIGIBLE tool, ONLY via to_api (§1.1)
      "labels": [str],     # honest labels (§1.4) — tool-declared, auto-attached
      "cost": {"wall_ms": float, "tool_calls": int, "subprocess_ct": int|None},   # §1.5; None = not instrumented
    }

Grade honesty at this boundary (§1.1): a grade exists only inside `verdict`, and `verdict` is lifted from a
FOLD tool's payload only when it is to_api-SHAPED (the enforced core fields of `Verdict.as_dict()`); a non-FOLD
tool returning a verdict-shaped key gets it STRIPPED — visibly (a "verdict_stripped_non_fold_tool" label), never
silently, and never passed through (RF-5: no grade on I/O; the build gate asserts no live tool trips this).
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

# ── §1.3 error codes — exactly these six, never a seventh ─────────────────────────────────────────────
INVALID_INPUT = "INVALID_INPUT"   # schema violation / bad arguments / rejected path (traversal guard)
NOT_FOUND = "NOT_FOUND"           # path / symbol / tool-name missing
EXEC_FAILED = "EXEC_FAILED"       # subprocess abnormal exit, or an in-tool crash (mapped, never propagated)
TIMEOUT = "TIMEOUT"               # budget exceeded (partial result, if any, rides in `result` + label "partial")
BLOCKED = "BLOCKED"               # network/permission blocked — the honest SWE-bench pattern, incl. the R7 gate
UNDECIDABLE = "UNDECIDABLE"       # a FOLD tool cannot decide — the tool-layer expression of DECLINE
ERROR_CODES = (INVALID_INPUT, NOT_FOUND, EXEC_FAILED, TIMEOUT, BLOCKED, UNDECIDABLE)

# ── §1.5 sandbox classes — declared per tool at registration ──────────────────────────────────────────
READ = "READ"     # workspace read only, zero side effects (fixed-argv read-only subprocess like `git log`
                  # counts as READ by EFFECT — the class tracks side-effect risk, not the mechanism)
WRITE = "WRITE"   # mutates workspace files — the executor's v2 path refuses it without the R7 checkpoint gate
EXEC = "EXEC"     # runs input-controlled code (subprocess whose behavior the arguments choose) — §BE isolation
SANDBOXES = (READ, WRITE, EXEC)

# the enforced-core fingerprint of kernel_verdict.Verdict.as_dict() — what to_api() (the ONE sanctioned
# grade emitter) always produces. Shape-checking these keys here + the repo-wide §BS-1 emission-boundary
# gate (which polices that no call-site hand-writes grade dicts) together keep this boundary honest.
_TO_API_CORE_KEYS = ("grade", "kernel", "complexity")


def is_to_api_shaped(v: Any) -> bool:
    return isinstance(v, dict) and all(k in v for k in _TO_API_CORE_KEYS)


def make_envelope(tool: str, ok: bool, *, result: Any = None,
                  error_code: Optional[str] = None, error_message: str = "", error_detail: str = "",
                  verdict: Optional[dict] = None, labels: Sequence[str] = (),
                  wall_ms: float = 0.0, subprocess_ct: Optional[int] = None) -> Dict[str, Any]:
    """The single §1.1 envelope constructor. Rejects unknown error codes (the 6 are a closed set) and
    non-to_api-shaped verdicts at construction time — an envelope carrying a hand-shaped grade dict is
    structurally unbuildable through this path."""
    if not ok:
        if error_code not in ERROR_CODES:
            raise ValueError(f"error_code must be one of {ERROR_CODES}, got {error_code!r}")
        error: Optional[Dict[str, str]] = {"code": error_code, "message": error_message, "detail": error_detail}
    else:
        error = None
    if verdict is not None and not is_to_api_shaped(verdict):
        raise ValueError("envelope verdict must be a kernel_verdict.to_api()-shaped dict (grade/kernel/"
                         "complexity present) — hand-shaped grade dicts are emission-bypass and unbuildable here")
    return {
        "ok": bool(ok),
        "tool": tool,
        "result": result if ok else result,   # a TIMEOUT may carry an honest partial result alongside its error
        "error": error,
        "verdict": verdict,
        "labels": list(labels),
        "cost": {"wall_ms": round(float(wall_ms), 3), "tool_calls": 1, "subprocess_ct": subprocess_ct},
    }
