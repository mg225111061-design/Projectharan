"""
swebench/hybrid_select.py — ★하이브리드 selector: Pass@K(정답이 후보에 있음)를 Best@K(골라냄)로 바꾸는 심장.
=================================================================================================================
두 리서치가 일치한 결론: 반복샘플의 병목은 SELECT 단계이고, 그 격차를 닫는 게 discriminative verification이다.
이 모듈은 8차에 설계된 "등가류 투표 + formal tiebreak"(BQ1/BQ2)와 점수보정(BU1)의 최소 구현 — 3층 신호,
우선순위 순서 고정:

  Layer 1 (sound, 최우선) — JEFF formal. `formal_check.formal_correct`(bounded_equiv 기반)로 후보가 참조
    동작과 도메인 전체에서 등가인지 증명. 증명(proved) = 최강 신호(보정 1.0). 반례(refuted) = **건전한 탈락**
    (테스트를 아무리 통과해도 부활 불가 — test-inflation 방어가 구조적). 적용 불가(no oracle/domain)면 정직하게
    Layer 2로 폴백하고, **적용률(formal_applicable_rate)을 그대로 로깅**한다(낮으면 낮다고 — 실세계 천장).
  Layer 2 (폴백) — 실행 신호. visible 테스트 통과율 + 차별화 테스트(diff_test_gen, 다수결 heuristic) 통과율.
    보정 상한 `TESTED_CAP < 1.0`: 실행-전용 증거는 formal-proven을 **절대** 못 이긴다(회귀가 잠금).
  Layer 3 (타이브레이크) — 의미 등가류 투표 + 정적 신호. 후보끼리 bounded_equiv(오라클 불필요 — 후보 대 후보)로
    등가 클래스를 만들고 클래스 크기가 표. 잔여 동점은 최소 소스(간결성) → 인덱스. 보너스 ε는 등급 간 간격보다
    항상 작아 등급 역전 불가.

★정직 경계: 이 selector는 "고른다"만 한다 — 후보가 전부 refuted/빌드실패면 chosen=None(정직 decline,
절대 refuted를 제출하지 않음). 다수결 차별화 테스트는 heuristic 라벨이 붙은 Layer-2 재료일 뿐이다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from swebench.harness import Candidate, Task, compile_fn, run_cases

# ── BU1 최소 구현: 보정 점수 테이블 (신호의 인식론적 강도 순서를 수로 고정) ─────────────────────────────
CALIB = {
    "formal_proven": 1.00,   # 도메인 전체 증명 — 천장
    "probabilistic": 0.93,   # (예약) 확률적 인증서는 δ 할인 — 이 기질엔 아직 없음, 자리만 정직히 고정
    "tested_cap":    0.85,   # 실행-전용 증거의 상한 — formal-proven을 구조적으로 못 넘는다
    "refuted":       0.00,   # 건전한 반례 — 탈락(테스트 점수와 무관)
}
_VOTE_EPS = 0.04             # Layer-3 보너스 최대치: 등급 간 최소 간격(0.07)보다 작다 → 역전 불가


@dataclass
class CandidateSignals:
    index: int
    label: str
    built: bool
    formal_applicable: bool
    formal: str                          # "proved" | "refuted" | "n/a"
    counterexample: Optional[dict]
    visible_frac: float
    diff_test_frac: Optional[float]      # None = 차별화 테스트 없음/미적용
    cluster: int                         # 등가류 id (-1 = 미배정)
    cluster_votes: int
    src_len: int
    score: float
    grade: str                           # "formal-proven" | "tested" | "refuted" | "build-error"


@dataclass
class SelectionReport:
    chosen: Optional[int]                # candidates 인덱스 (None = 정직 decline)
    chosen_candidate: Optional[Candidate]
    signals: List[CandidateSignals] = field(default_factory=list)
    formal_applicable_rate: float = 0.0  # ★정직 로깅: built 후보 중 formal이 실제로 돈 비율
    layer_used: str = "none"             # "formal" | "test" | "vote" | "none"
    detail: str = ""


def _frac(fn, cases) -> float:
    """(args, expected) 케이스 통과 비율 — run_cases는 첫 실패에서 멈추므로 비율은 직접 센다."""
    if not cases:
        return 0.0
    ok = 0
    for args, expected in cases:
        try:
            if fn(*args) == expected:
                ok += 1
        except Exception:                # noqa: BLE001 — 실패한 케이스는 데이터, 크래시 아님
            pass
    return ok / len(cases)


def _wrap_total(fn):
    """bounded_equiv용 총함수화: 예외를 (타입이름) 값으로 — 같은 입력에서 같은 예외를 던지는 두 후보는
    그 지점에서 '같은 동작'(관찰 동등성), 값-대-예외는 불일치로 정확히 갈린다."""
    def g(t):
        try:
            return ("ok", fn(*t))
        except Exception as e:           # noqa: BLE001
            return ("exc", type(e).__name__)
    return g


def equivalence_classes(fns: Dict[int, object], domain) -> Dict[int, int]:
    """BQ1 등가류: 후보 대 후보 bounded_equiv(오라클 불필요)로 union-find 클러스터링. 도메인이 없으면
    전원 싱글턴(등가 주장 안 함 — 증명 없이 묶지 않는다)."""
    idxs = sorted(fns)
    parent = {i: i for i in idxs}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    if domain:
        from catalog.equiv_check import bounded_equiv
        wrapped = {i: _wrap_total(fns[i]) for i in idxs}
        for ai in range(len(idxs)):
            for bi in range(ai + 1, len(idxs)):
                a, b = idxs[ai], idxs[bi]
                if find(a) == find(b):
                    continue
                if bounded_equiv(wrapped[a], wrapped[b], domain).proved:
                    parent[find(b)] = find(a)
    return {i: find(i) for i in idxs}


def hybrid_select(task: Task, candidates: List[Candidate],
                  diff_tests: Optional[List[Tuple[tuple, object]]] = None) -> SelectionReport:
    """3층 하이브리드 선택. 반환 report는 후보별 전 신호 + formal 적용률 + 어느 층이 결정했는지를 담는다."""
    sigs: List[CandidateSignals] = []
    fns: Dict[int, object] = {}
    from swebench.formal_check import formal_correct

    # Layer 0/1: 빌드 → formal (sound)
    applicable_ct = 0
    for i, c in enumerate(candidates):
        fn = compile_fn(c.src, task.fn_name)
        if fn is None:
            sigs.append(CandidateSignals(i, c.label, False, False, "n/a", None, 0.0, None, -1, 1,
                                         len(c.src), CALIB["refuted"], "build-error"))
            continue
        fns[i] = fn
        fr = formal_correct(task, fn)
        if fr.applicable:
            applicable_ct += 1
            formal = "proved" if fr.proved else "refuted"
        else:
            formal = "n/a"
        sigs.append(CandidateSignals(i, c.label, True, fr.applicable, formal, fr.counterexample,
                                     0.0, None, -1, 1, len(c.src), 0.0,
                                     "formal-proven" if formal == "proved" else
                                     ("refuted" if formal == "refuted" else "tested")))

    built = [s for s in sigs if s.built]
    rate = (applicable_ct / len(built)) if built else 0.0

    # Layer 2: 실행 신호 (refuted도 기록은 하되 점수는 0 고정 — inflation 방어의 구조화)
    for s in sigs:
        if not s.built:
            continue
        s.visible_frac = _frac(fns[s.index], task.visible)
        if diff_tests:
            s.diff_test_frac = _frac(fns[s.index], diff_tests)

    # Layer 3: 등가류 투표 (남은 built 전원 — refuted가 어느 클래스에 속하는지도 정보)
    clusters = equivalence_classes(fns, task.formal_domain or [])
    votes: Dict[int, int] = {}
    for i, root in clusters.items():
        votes[root] = votes.get(root, 0) + 1
    for s in sigs:
        if s.built:
            s.cluster = clusters[s.index]
            s.cluster_votes = votes[clusters[s.index]]

    # BU1 보정 융합
    n = max(1, len(candidates))
    for s in sigs:
        if not s.built or s.grade == "refuted":
            s.score = CALIB["refuted"]
            continue
        if s.grade == "formal-proven":
            base = CALIB["formal_proven"]
        else:
            exec_frac = s.visible_frac if s.diff_test_frac is None else (0.7 * s.visible_frac + 0.3 * s.diff_test_frac)
            base = CALIB["tested_cap"] * exec_frac
        s.score = base + _VOTE_EPS * (s.cluster_votes / n)

    # 선택: refuted/빌드실패 제외 최고점; 동점 → 표 → 짧은 소스 → 인덱스
    alive = [s for s in sigs if s.built and s.grade != "refuted"]
    if not alive:
        return SelectionReport(None, None, sigs, rate, "none",
                               f"no eligible candidate (all refuted/build-error) — honest decline; "
                               f"formal applicable {applicable_ct}/{len(built) or 0}")
    ranked = sorted(alive, key=lambda s: (-s.score, -s.cluster_votes, s.src_len, s.index))
    top = ranked[0]

    if top.grade == "formal-proven":
        layer = "formal"
    elif len(ranked) > 1 and abs(top.score - ranked[1].score) > _VOTE_EPS:
        layer = "test"                   # 실행 신호가 실제로 갈랐다
    elif len(ranked) > 1:
        layer = "vote"                   # 등가류 표/간결성이 갈랐다
    else:
        layer = "test"
    return SelectionReport(top.index, candidates[top.index], sigs, rate, layer,
                           f"chosen #{top.index} ({top.grade}, score {top.score:.3f}); "
                           f"formal applicable {applicable_ct}/{len(built)} "
                           f"({rate:.0%} of built candidates) — honest rate, not a coverage claim")
