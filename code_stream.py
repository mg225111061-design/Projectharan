"""
§3 (STREAM EVERY STEP) — the live CODE process trace: ordered, human-readable phase records.
============================================================================================
The UI must show EVERY step of what CODE is doing, live — not just the final result. This module produces the
ORDERED phase records (the "process") the frontend renders progressively, mirroring MATH mode's
ROUTE / RECOGNIZE / KERNEL / 증명서 transparency. `iter_code_trace` is a GENERATOR: it yields each PhaseEvent as
the REAL work completes (parse → recognize → apply fold/decision → certify → verify → result), so the SSE endpoint
streams them incrementally rather than blocking on the whole run.

★ HONEST (§X) ★: every record reflects the REAL tier, the REAL structure/fold/decision, the REAL proof step, the
REAL budget elapsed, and the REAL grade + certificate — NEVER fabricated progress. The grade shown in the RESULT
record is the engine's actual grade (re-read from its verdict), not a guess; a step that is honestly undecided
says so ("아직 닫히지 않음"), it does not invent progress. extend's budget line shows the BOUNDED ~8 min ("/ 8:00").
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterator, List, Optional

import mode_budget as MB
from pillar3.mode import Mode

# phase tags (the live process spine — mirrors MATH's ROUTE/RECOGNIZE/KERNEL/증명서)
ANALYZE = "ANALYZE"
RECOGNIZE = "RECOGNIZE"
APPLY = "APPLY"
CERTIFY = "CERTIFY"
VERIFY = "VERIFY"
RESULT = "RESULT"


@dataclass
class PhaseEvent:
    phase: str                       # ANALYZE | RECOGNIZE | APPLY | CERTIFY | VERIFY | RESULT
    message: str                     # human-readable Korean live status
    tier: str                        # fast | normal | extend
    budget: str                      # the live tier+budget line, e.g. 'extend · 0:03 / 8:00'
    detail: str = ""
    grade: Optional[str] = None      # EXACT | PROBABILISTIC | DECLINE — the REAL grade where one exists
    certificate: str = ""            # the REAL certificate text where one exists

    def to_dict(self) -> dict:
        return asdict(self)


def _mode(mode: str) -> Mode:
    return Mode(mode) if mode in (x.value for x in Mode) else Mode.NORMAL


def iter_code_trace(code: str, mode: str = "normal") -> Iterator[PhaseEvent]:
    """Yield the live CODE process records one at a time AS each real step completes (for SSE streaming). Every
    record is derived from real engine/verdict data — no fabricated progress."""
    from webapi import engine_bridge as EB                    # lazy: keep import light
    import structure_recognizer as SR

    m = _mode(mode)
    budget = MB.start_budget(m)                               # the live deadline (elapsed/remaining for the UI)

    def ev(phase: str, message: str, **kw) -> PhaseEvent:
        return PhaseEvent(phase, message, m.value, budget.display(), **kw)

    # 1) ANALYZE — parsing, under the chosen tier + its enforced budget
    yield ev(ANALYZE, "분석 중… (코드 파싱)", detail=MB.tier_label(m))

    # 2) RECOGNIZE — real AST waste/structure detection
    detected = EB.detect_in_source(code)
    kinds = ", ".join(sorted({d["waste_type"] for d in detected})) or "없음"
    yield ev(RECOGNIZE, f"구조 인식 중… (낭비/구조 패턴 {len(detected)}건 탐지)", detail=kinds)

    # 3+4) APPLY + CERTIFY — the absorbed MATH decision procedure on a Σ-accumulation loop (§2), surfaced live
    dec = SR.decide_loop(code)
    if dec is not None:
        if dec.status == "CLOSED_FORM":
            yield ev(APPLY, f"fold 적용 중: 결정 절차로 멱합/누적 루프 접는 중… Σ {dec.summand}",
                     detail=f"닫힌형 = {dec.closed_form} ({dec.complexity})")
            yield ev(CERTIFY, "증명서 생성 중… (차분 등가성 게이트로 닫힌형 검증)",
                     grade=dec.verdict.status, certificate=dec.certificate)
        elif dec.status == "NO_CLOSED_FORM":
            yield ev(APPLY, f"결정 절차 적용 중: Σ {dec.summand} 의 닫힌형 존재 여부 판정 중…")
            yield ev(CERTIFY, "증명서 생성 중… (Gosper 결정 — 닫힌형 없음 증명; 루프는 기약)",
                     grade=dec.verdict.status, certificate=dec.certificate)
        else:                                                # UNDECIDED — honest, no fabricated progress
            yield ev(APPLY, f"결정 절차: Σ {dec.summand} — 이 클래스 밖이라 판정 보류(정직, 아직 닫히지 않음)",
                     detail=dec.certificate)

    # 5) VERIFY — run the REAL engine UNDER the mode's enforced budget (§1)
    res = EB.run_optimize(code, m.value)
    bd = res.get("budget", {})
    yield ev(VERIFY, "검증 중… (in-house SMT / 차분 등가성으로 원본≡최적화 확인)",
             detail=f"z3_calls={res.get('z3_calls', 0)} · {bd.get('display', budget.display())}")

    # 6) RESULT — the REAL outcome + grade + certificate (never fabricated)
    shipped, declined = res.get("shipped", []), res.get("declined", [])
    if shipped:
        s0 = shipped[0]
        yield ev(RESULT, f"결과: 검증된 수정 {len(shipped)}건 출하 (grade={s0['grade'].upper()})",
                 grade=s0["grade"].upper(),
                 certificate=f"ratio={s0['ratio']} · ceiling={s0.get('ceiling')} (whole-program; Amdahl 천장 이하)")
    elif dec is not None and dec.status == "NO_CLOSED_FORM":
        yield ev(RESULT, "결과: 이 루프는 닫힌형이 없음 — PROVEN DECLINE (루프를 그대로 유지)",
                 grade=dec.verdict.status, certificate=dec.certificate)
    elif declined:
        yield ev(RESULT, f"결과: {len(declined)}건 정직한 DECLINE (안전하게 출하할 게 없음)",
                 grade="DECLINE", detail=declined[0]["reason"])
    else:
        yield ev(RESULT, "결과: 검증된 수정 없음 — 정직한 빈 결과", grade="DECLINE")

    # final budget line (so the UI shows the elapsed/bounded budget at completion)
    yield ev(RESULT, f"완료 · {bd.get('display', budget.display())}", detail=f"status={bd.get('status', '')}")


def build_code_trace(code: str, mode: str = "normal") -> List[PhaseEvent]:
    """Materialize the whole ordered trace (for tests / non-streaming callers)."""
    return list(iter_code_trace(code, mode))


def to_sse(events) -> List[str]:
    """Format phase events as SSE `data:` frames (the frontend's existing event channel renders them live)."""
    import json
    return [f"data: {json.dumps(e.to_dict(), ensure_ascii=False)}\n\n" for e in events]
