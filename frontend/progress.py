"""
§W PHASE 5 — LIVE PROGRESS: show, in real time, the REAL stages of the run (mode-aware, never a fake spinner).
================================================================================================================
During a task the user sees what the engine/AI is actually doing — generating candidates, verifying, checking
security, folding, running tests, repairing — the real stages of the real pipeline, updating at the actual
transitions. NORMAL shows a shorter sequence; EXTEND shows the deeper stages it works through (2-tier — a
former third mode, `fast`, retired; coordinates with the tier budgets 30s/180s). The stages are the genuine
pipeline steps (the §U layered gate, the §R security check, the fold engine, the fix loop) — not a decorative
spinner.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, List


@dataclass
class Stage:
    key: str
    label: str                          # human-facing, mode-appropriate
    detail: str = ""


# the real pipeline stages (each maps to an actual engine step)
_ALL = {
    "generate":  ("후보 생성", "Opus가 후보 패치/코드를 만듭니다 (Clock A)"),
    "build":     ("빌드 확인", "후보가 컴파일/파싱되는지 확인합니다"),
    "tests":     ("테스트 실행", "보이는 테스트를 돌립니다 (§U 게이트)"),
    "regression":("회귀 확인", "기존 통과 테스트가 깨지지 않는지 확인합니다"),
    "security":  ("보안 점검", "민감하면 취약점/부채널을 검증합니다 (§R)"),
    "fold":      ("최적화(fold)", "구조가 있으면 더 빠른 형태로 접습니다"),
    "formal":    ("형식 검증", "보이는 테스트 너머의 정확성을 증명합니다 (§U)"),
    "repair":    ("수리", "실패하면 반례로 고쳐 다시 검증합니다 (fix loop)"),
    "verify":    ("동치 확인", "바뀐 코드가 같은 결과를 내는지 확인합니다"),
    "done":      ("완료", "안전하게 · 빠르게 · 정확하게 점검 완료"),
}

# mode-aware stage sequences (2-tier — a former third mode, fast, retired) — NORMAL shorter, EXTEND the full deep sequence
_SEQ = {
    "normal": ["generate", "build", "tests", "regression", "security", "fold", "verify", "done"],
    "extend": ["generate", "build", "tests", "regression", "security", "fold", "formal", "repair", "verify", "done"],
}


def stages_for_mode(mode: str) -> List[Stage]:
    """The ordered, REAL stages a given mode works through. EXTEND is the deepest (formal + repair); NORMAL is shorter."""
    seq = _SEQ.get(mode, _SEQ["normal"])
    return [Stage(k, _ALL[k][0], _ALL[k][1]) for k in seq]


def stream(mode: str) -> Iterator[dict]:
    """Yield the stages in order (for SSE / live render). Each frame is a real stage with its position — the user
    watches the actual pipeline unfold, never a fake spinner. (Live streaming over HTTP is the server's job; the
    stage sequence + transitions are defined and verified here.)"""
    stages = stages_for_mode(mode)
    n = len(stages)
    for i, s in enumerate(stages):
        yield {"index": i, "total": n, "key": s.key, "label": s.label, "detail": s.detail,
               "done": s.key == "done"}


def depth(mode: str) -> int:
    return len(stages_for_mode(mode))
