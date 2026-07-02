"""
swebench/sample_repair.py — Agentless 뼈대(재구현): localize → sample-repair(N) → hybrid-select.
=================================================================================================================
리서치 결론 그대로: 복잡한 에이전트가 아니라 **고정 3단 뼈대**가 이긴다. 이 모듈은 그 뼈대의 오케스트레이션만
한다 — 각 단은 전부 기존 엔진 재사용:

  1) localize        → swebench/localization.localize_pool (true-locus 필터, §U Phase 5A 그대로)
  2) sample N        → 주입 훅 `gen(task, n)` — **이 모듈은 LLM을 직접 호출하지 않는다**(생성은 파이프라인
                       훅; 게이트에선 recorded/stub, 라이브에선 provider 경로가 훅을 채운다). 온도/프롬프트
                       다양화는 훅 소유자의 일이다.
  3) apply-게이트    → 이 기질(소스 후보)에선 빌드 게이트(compile) = hybrid_select Layer 0이 수행;
                       diff 후보의 라이브 경로에선 patch_integrity(BI)+git apply가 같은 역할(live_harness).
  4) hybrid-select   → swebench/hybrid_select (formal sound → test 폴백 → 등가류 투표, BU1 보정)

provider 무관은 **구조적**이다: 이 함수 시그니처에 provider 인자 자체가 없다(10H Task 4의 blindness 패턴).
N 기본값은 mode_policy.BEST_OF_N(§BU-0 단일 원장)을 재사용 — 로컬(비용≈0)은 extended 상단, API는 normal 상단.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from swebench.harness import Candidate, Task, recorded_generator
from swebench.hybrid_select import SelectionReport, hybrid_select
from swebench.localization import localize_pool


def default_n(local: bool) -> int:
    """반복샘플 N 기본값 — mode_policy.BEST_OF_N 재사용(새 N 테이블 발명 금지, §BU-0 단일 원장).
    로컬 모델은 생성 비용≈0이므로 extended 밴드 상단(리서치: 로컬의 숨은 장점), API는 normal 상단(비용 인지)."""
    from mode_policy import BEST_OF_N
    return BEST_OF_N["extended"][1] if local else BEST_OF_N["normal"][1]


@dataclass
class PipelineResult:
    submitted: Optional[Candidate]       # 선택된 후보 (None = 정직 decline)
    chosen_index: Optional[int]          # localized 풀 내 인덱스
    n_generated: int
    n_localized: int
    n_built: int                         # apply(빌드) 게이트 생존 수 — malformed는 여기서 걸러진다
    n_diff_tests: int
    selection: Optional[SelectionReport]
    stage: str                           # "select" | "no-candidates" | "decline"


def sample_repair(task: Task, gen: Callable = recorded_generator, n: int = 0, *,
                  use_diff_tests: bool = True) -> PipelineResult:
    """Agentless 뼈대 1회전. `gen(task, n)`이 후보 N개를 내면 localize→select가 최선 1개를 고른다.
    후보 0개/전원 탈락이면 정직한 decline(제출 없음) — refuted를 절대 제출하지 않는 hybrid_select 규약 그대로."""
    cands: List[Candidate] = list(gen(task, n) or [])
    if not cands:
        return PipelineResult(None, None, 0, 0, 0, 0, None, "no-candidates")
    pool = localize_pool(task, cands)
    if not pool:
        return PipelineResult(None, None, len(cands), 0, 0, 0, None, "decline")

    diff_cases = []
    if use_diff_tests:
        from swebench.diff_test_gen import as_cases, gen_differentiating_tests
        diff_cases = as_cases(gen_differentiating_tests(task, pool))

    rep = hybrid_select(task, pool, diff_tests=diff_cases or None)
    n_built = sum(1 for s in rep.signals if s.built)
    if rep.chosen is None:
        return PipelineResult(None, None, len(cands), len(pool), n_built, len(diff_cases), rep, "decline")
    return PipelineResult(rep.chosen_candidate, rep.chosen, len(cands), len(pool), n_built,
                          len(diff_cases), rep, "select")
