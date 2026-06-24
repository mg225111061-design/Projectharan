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
    import loop_decision as LD

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
    rc = None
    mc = None
    if dec is not None:
        if dec.status == "CLOSED_FORM":
            yield ev(APPLY, f"fold 적용 중: 결정 절차로 멱합/누적 루프 접는 중… Σ {dec.summand}",
                     detail=f"닫힌형 = {dec.closed_form} ({dec.complexity})")
            yield ev(CERTIFY, "증명서 생성 중… (차분 등가성 게이트로 닫힌형 검증)",
                     grade=dec.verdict.status, certificate=dec.certificate)
            # §4: MEASURE the O(n) loop → O(1) collapse and stream the Amdahl-honest result (real timing)
            sp_meas = LD.measure_collapse_speedup(dec.summand, dec.var, dec.lo, n=20000, trials=3)
            if sp_meas.status == "MEASURED":
                yield ev(VERIFY, f"속도향상 실측 중… O(n) 루프 → O(1) 닫힌형 (n={sp_meas.n})",
                         detail=f"측정 {sp_meas.ratio:.0f}× · f=1 · Amdahl 천장 이하 · domain-conditional · n에 따라 O(n) 증가",
                         grade=sp_meas.verdict.status, certificate=sp_meas.verdict.certificate.detail)
        elif dec.status == "NO_CLOSED_FORM":
            yield ev(APPLY, f"결정 절차 적용 중: Σ {dec.summand} 의 닫힌형 존재 여부 판정 중…")
            yield ev(CERTIFY, "증명서 생성 중… (Gosper 결정 — 닫힌형 없음 증명; 루프는 기약)",
                     grade=dec.verdict.status, certificate=dec.certificate)
        else:                                                # UNDECIDED — honest, no fabricated progress
            yield ev(APPLY, f"결정 절차: Σ {dec.summand} — 이 클래스 밖이라 판정 보류(정직, 아직 닫히지 않음)",
                     detail=dec.certificate)
    else:
        # §4 ceiling-breaker: a C-finite state-update loop (Fibonacci-like) → O(log n) companion collapse
        try:
            import loop_recurrence as LR2
            rc = LR2.decide_recurrence_collapse(code, n=20000, trials=2)
            if rc is None or rc.status != "COLLAPSED":         # exact declined → try the genuine-win modular case
                mc = LR2.decide_modular_recurrence_collapse(code, n=20000, trials=2)
        except Exception:                                    # noqa: BLE001 — analysis must never crash the stream
            rc = None
        if rc is not None and rc.status == "COLLAPSED":
            yield ev(APPLY, f"선형 점화식 인식 중: O(n) 상태-갱신 루프 → O(log n) 동반행렬 (order={rc.order}, c={rc.c})")
            _win = "측정 win" if rc.measured_win else "검증됨 (이 n에선 측정 win 아님 — 정직)"
            yield ev(CERTIFY, f"증명서 생성 중… (동반형 ≡ 루프, held-out n 검증) · {rc.ratio:.1f}× {_win}",
                     grade=rc.verdict.status, certificate=rc.verdict.certificate.detail)
        elif mc is not None and mc.status == "COLLAPSED":
            yield ev(APPLY, f"모듈러 선형 점화식 인식 중: O(n) 루프 → O(log n) 동반행렬 mod M (order={mc.order}, c={mc.c})")
            yield ev(CERTIFY, f"증명서 생성 중… (동반형-mod ≡ 루프, wrap된 held-out n 검증) · {mc.ratio:.1f}× 측정 win "
                     f"[경계 정수 ⇒ 진짜 O(log n)]", grade=mc.verdict.status, certificate=mc.verdict.certificate.detail)

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
    elif dec is not None and dec.status == "CLOSED_FORM":
        yield ev(RESULT, f"결과: O(n) 루프 → O(1) 닫힌형 {dec.closed_form} — 증명된 붕괴 (차분 등가성 검증)",
                 grade=dec.verdict.status, certificate=dec.certificate)
    elif rc is not None and rc.status == "COLLAPSED":
        yield ev(RESULT, f"결과: O(n) 점화식 루프 → O(log n) 동반형 — 증명된 붕괴 (held-out n 검증, {rc.ratio:.1f}×)",
                 grade=rc.verdict.status, certificate=rc.verdict.certificate.detail)
    elif mc is not None and mc.status == "COLLAPSED":
        yield ev(RESULT, f"결과: O(n) 모듈러 점화식 루프 → O(log n) 동반형 mod M — 증명된 붕괴 (wrap된 held-out 검증, "
                 f"{mc.ratio:.1f}×)", grade=mc.verdict.status, certificate=mc.verdict.certificate.detail)
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
