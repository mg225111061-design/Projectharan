"""
swebench/diff_test_gen.py — 차별화 테스트 생성 (CodeT/UTBoost의 ROLE을 LLM-free로 재구현).
=================================================================================================================
목적: 후보들이 **서로 다른 출력**을 내는 입력을 찾아 후보를 가르는 실행 신호를 만든다(BS군 UTBoost류의 재료).
기대값은 후보 다수결(CodeT dual-agreement의 요지) — ★**heuristic이다. 다수가 틀릴 수 있다.**
그래서 이 신호의 지위는 지시서 프라임 2에 못박혀 있다:

  * Layer 2 전용 재료 — hybrid_select에서 실행-신호 상한(TESTED_CAP)에 눌려 있고,
  * **formal(Layer 1)을 절대 못 이긴다** — 오답 다수가 생성 테스트를 전부 통과시켜도(test inflation)
    formal 반례 하나가 그들을 탈락시킨다. 이 방어는 회귀로 잠근다.

오라클(task.reference_src)은 여기서 **쓰지 않는다** — 오라클은 formal 층의 소유다. 여기 끌어오면
생성-테스트가 아니라 몰래 만든 formal 검사가 되고, 실세계(오라클 없는 라이브 태스크)에서의
이 신호의 진짜 가치를 측정할 수 없게 된다.
"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional, Tuple

from swebench.harness import Task, compile_fn


def _mutate_int(v: int) -> List[int]:
    return [v - 1, v + 1, 0, -v]


def _input_pool(task: Task, cap: int) -> List[tuple]:
    """차별화 입력 후보 풀: 선언된 formal_domain이 있으면 그것(경계 포함 완전), 없으면 visible 인자 +
    경계 변이(±1/0/부호 반전/빈 리스트) — off-by-one·경계 버그가 사는 곳을 노린다."""
    if task.formal_domain:
        return list(task.formal_domain)[:cap]
    seen, pool = set(), []

    def add(args: tuple):
        if args not in seen:
            seen.add(args)
            pool.append(args)

    for args, _ in task.visible:
        add(args)
    for args, _ in task.visible:
        for pos, v in enumerate(args):
            if isinstance(v, bool) or not isinstance(v, (int, list)):
                continue
            variants = _mutate_int(v) if isinstance(v, int) else ([], v[:1], v + v)
            for nv in variants:
                add(tuple(nv if p == pos else old for p, old in enumerate(args)))
    return pool[:cap]


def gen_differentiating_tests(task: Task, candidates: List, *, cap: int = 400,
                              max_tests: int = 8) -> List[dict]:
    """후보들이 불일치하는 입력을 찾아 [{args, expected(다수결), votes, label}] 반환. 컴파일되는 후보가
    2개 미만이거나 전원이 모든 입력에서 일치하면 빈 리스트(가를 게 없다는 정직한 답)."""
    fns: Dict[int, object] = {}
    for i, c in enumerate(candidates):
        fn = compile_fn(c.src, task.fn_name)
        if fn is not None:
            fns[i] = fn
    if len(fns) < 2:
        return []
    tests: List[dict] = []
    for args in _input_pool(task, cap):
        outs: Dict[int, tuple] = {}
        for i, fn in fns.items():
            try:
                outs[i] = ("ok", fn(*args))
            except Exception as e:       # noqa: BLE001 — 예외도 하나의 관찰값
                outs[i] = ("exc", type(e).__name__)
        if len(set(outs.values())) < 2:
            continue                     # 이 입력은 아무도 못 가른다
        votes = Counter(outs.values())
        (kind, val), _n = votes.most_common(1)[0]
        if kind != "ok":
            continue                     # 다수가 예외 — 기대값으로 삼지 않는다(정직: 예외를 스펙화하지 않음)
        tests.append({"args": args, "expected": val,
                      "votes": {f"{k}:{v!r}": c for (k, v), c in votes.items()},
                      "label": "majority_heuristic"})
        if len(tests) >= max_tests:
            break
    return tests


def as_cases(tests: List[dict]) -> List[Tuple[tuple, object]]:
    """hybrid_select의 diff_tests 인자 형태(= harness.run_cases 케이스 형태)로 변환."""
    return [(t["args"], t["expected"]) for t in tests]
