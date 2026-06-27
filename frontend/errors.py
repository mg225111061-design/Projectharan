"""
§W PHASE 6 — ERROR SURFACING: every failure a specific, honest, actionable message (no silent fail, no fake success).
================================================================================================================
sound-or-DECLINE at the UI: if something can't be done, say clearly WHAT happened and WHAT to do. A network error
says "network error" (with retry), a bad key says "invalid key" (re-enter), a rate limit says "rate limited" (wait),
an unsupported file says why, the backend being down says "service unavailable." Never a generic "something went
wrong" where a specific cause is known, and never a failed run dressed up as a partial success.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ErrorView:
    kind: str
    message: str                        # specific + honest
    action: str                         # what the user should do
    retryable: bool

    def to_dict(self) -> dict:
        return {"kind": self.kind, "message": self.message, "action": self.action, "retryable": self.retryable}


# the specific, actionable surface for each known failure cause
_TABLE = {
    "network":      ("네트워크 오류 — 연결에 실패했습니다.", "잠시 후 다시 시도하세요.", True),
    "timeout":      ("시간 초과 — 응답이 너무 오래 걸렸습니다.", "다시 시도하거나 더 작은 입력으로 시도하세요.", True),
    "invalid_key":  ("잘못된 키 — 제공자가 키를 거부했습니다.", "키를 다시 입력하세요 (키는 저장되지 않습니다).", False),
    "rate_limited": ("요청 한도 초과 — 제공자가 속도를 제한했습니다.", "잠시 기다린 뒤 다시 시도하세요.", True),
    "provider":     ("제공자 오류 — 제공자가 오류를 반환했습니다.", "제공자 메시지를 확인하거나 다른 제공자를 고르세요.", True),
    "unsupported_file": ("지원하지 않는 파일 — 이 형식은 처리할 수 없습니다.", "지원되는 형식(소스/데이터/텍스트/설정/노트북)으로 올리세요.", False),
    "oversized_file": ("파일이 너무 큼 — 크기 제한을 초과했습니다.", "더 작은 파일로 나눠 올리세요.", False),
    "too_many_files": ("파일이 너무 많음 — 한 번에 최대 5개입니다.", "5개 이하로 올리세요.", False),
    "backend_down": ("서비스를 사용할 수 없음 — 백엔드에 연결할 수 없습니다.", "잠시 후 다시 시도하세요.", True),
    "auth":         ("인증 실패 — 이메일 또는 비밀번호가 올바르지 않습니다.", "다시 확인하고 입력하세요.", False),
    "unknown":      ("알 수 없는 오류 — 예기치 못한 문제가 발생했습니다.", "다시 시도하고, 계속되면 다른 입력/제공자를 시도하세요.", True),
}


def classify(kind: str) -> ErrorView:
    """Map a known failure cause to its specific, honest, actionable view. An unknown cause is surfaced honestly as
    'unknown' (never a fabricated success), but every KNOWN cause gets its specific message."""
    msg, act, retry = _TABLE.get(kind, _TABLE["unknown"])
    return ErrorView(kind if kind in _TABLE else "unknown", msg, act, retry)


def from_exception(exc: BaseException) -> ErrorView:
    """Classify a raised exception into a specific error view (sound-or-DECLINE at the UI). Network/timeout/HTTP-status
    cues map to their specific causes; anything unrecognized is the honest 'unknown' (never dressed as success)."""
    name = type(exc).__name__.lower()
    text = str(exc).lower()
    if "timeout" in name or "timeout" in text:
        return classify("timeout")
    if any(s in name for s in ("connection", "socket")) or any(s in text for s in ("network", "connection refused", "dns")):
        return classify("network")
    if "401" in text or "403" in text or "invalid" in text and "key" in text or "unauthorized" in text:
        return classify("invalid_key")
    if "429" in text or "rate" in text:
        return classify("rate_limited")
    if "5" == text[:1] and text[:3].isdigit() or "service unavailable" in text or "502" in text or "503" in text:
        return classify("backend_down")
    return classify("unknown")


def is_silent_or_fake(view: ErrorView) -> bool:
    """A guard for the honesty rule: an error view must carry a non-empty specific message and action (never silent),
    and a failure is never reported as a success. Returns True if the view VIOLATES this (used to fail the build)."""
    return not view.message.strip() or not view.action.strip()
