# CATALOG_RECONCILE.md — 카탈로그-v2 §3.1 중복대조 매트릭스 + §3.2 공통계약 파운데이션 원장

> 카탈로그-v2 지시서 §3.1: "1차 실측 카탈로그(37)와 v2(101)의 중복대조 → 겹치면 재사용, 신규만 생성" —
> **이 문서가 그 원장이다.** 3~7차 물결(S~AB·AC~AL·AM~AV·AW~BF·BG~BP)은 각자의 §3.1 매트릭스를
> 이 문서에 **누적**한다(트래커 #347/#350/#353/#357/#361). 측정 시점: 2026-07-02, live registry 실측.

---

## 1. 1차 실측 카탈로그 — 37 도구 (registry 라이브 덤프 + §1.5 샌드박스 분류)

**샌드박스 분류 기준(Tier-A 판단, 기록):** 클래스는 *부작용 위험*을 추적한다 — 메커니즘이 아니라 효과.
고정-argv 읽기전용 git 서브프로세스(`git log` 등)는 부작용 0이므로 **READ**다(인자가 동작을 고르는
임의-코드 실행이 아님 — argv 고정 + `-` 접두 인자 거부는 catalog_plain 헤더에 문서화된 기존 방어).
**EXEC**는 입력이 실행 내용을 결정하는 도구(run_python_file)에만. 이 해석이 아니면 read-only git 14종
전부가 §BE 격리 의무를 지는 EXEC가 되는데, 그건 위험 모델을 과장하고 기존 37종을 소급 비준수로 만든다.

| sandbox | 수 | 도구 |
|---|---|---|
| READ (29) | 부작용 0 | read_file · list_dir · glob_files · grep_search · file_exists · file_stat · git_status · git_diff · git_log · git_show · git_branch_list · git_current_branch · git_blame · recent_changes · dir_tree · symbol_find · ast_outline · docstring_extract · import_graph · call_graph · reach_closure · todo_scan · loc_stats · detect_code_structure(F) · classify_haran_closure(F) · recognize_checksum(F) · recognize_parse_arith(F) · check_tasks_independent(A) · check_loop_parallel_safety(A) |
| WRITE (7) | R7 게이트 대상 | file_write · file_patch · write_scratch_file · git_apply_patch · git_checkout_commit · git_stash_ops · repo_clone_shallow |
| EXEC (1) | §BE 격리(도구 내장) | run_python_file |

(F)=FOLD-ELIGIBLE, (A)=ACCEL-ELIGIBLE, 나머지 PLAIN — RF-5 tier는 기존 그대로, 이번 변경은 sandbox 메타데이터 추가뿐.

## 2. v2 101종 ↔ 1차 37종 대조 (이름충돌 0 — 인접은 "backing 재사용" 관계)

**이름 충돌: 0건** (101개 v2 이름 전부 라이브 37에 없음 — 실측 대조). 아래는 재사용-backing 관계
(v2 도구가 기존 도구/엔진을 호출해야 하고 재구현이 금지되는 지점):

| v2 군 | 수 | 기존 37 중 backing으로 재사용할 것 | 비고 |
|---|---|---|---|
| J 리팩터링 14 | rename_symbol, extract_function, … | symbol_find(위치), file_patch(적용), ast_outline | equiv 게이트는 `pillar3/equiv` — 미증명 적용 금지(J군 안전게이트) |
| K 디버깅 15 | bisect_commits/hunks, regression_pinpoint | git_log/git_checkout_commit/git_apply_patch/run_python_file | delta-debug 계열은 EXEC — run_python_file 재사용 |
| L 테스트 12 | test_skeleton_gen, oracle_from_spec, … | read_file/ast_outline/run_python_file | nonexact 라벨 강제(§1.4) |
| M 성능 11 | fold_opportunity_scan ★, hotspot_profile | detect_code_structure(F)/classify_haran_closure(F) | fold-scan은 기존 FOLD 도구의 상위 조합 — 재호출 |
| N 다중파일 11 | multi_patch_atomic, api_surface_diff | file_patch(단일파일 원자 편집을 루프+롤백으로 조합), git_diff | 원자성 층만 신규 |
| O 언어의미론 11 | int_semantics_check ★, regex_safety_check ★ | frontend/languages(§BJ 80+ langs), ast_outline | 결정절차는 신규(ReDoS star-height 등) |
| P 컨텍스트 11 | context_window_pack ★, similar_code_find | grep_search/read_file/loc_stats/docstring_extract/import_graph | 6차 AW군이 이 P군 위에 fold-압축을 얹음 |
| Q 환경 8 | dep_tree_show, stdlib_only_check | dependency_audit.py(기존 §5 감사 엔진) 재사용 | |
| R 에이전트메타 8 | safe_checkpoint(=R7), gate_quick | git_stash_ops/git_status(체크포인트 기반), run_python_file(게이트) | **internal — 모델 비노출**(라우터 제외 목록) |

**3~7차 사전 지적(각 물결 §3.1에서 정밀화):** 3차 T군↔run_python_file·K군 / 4차 AF↔K·T, AG3↔P4, AH9↔P7 /
5차 AO↔swebench 5메커니즘(재호출 필수), AR8↔M8, AS5↔regression_scope / 6차 AY3↔AN2, AZ5↔AN1, BD8↔R8 /
7차 BL↔AO6, BN2↔AG1, BM1↔P1, BJ↔B군-formal(bounded_equiv), BP2↔swebench/fix_loop.

## 3. §3.2 공통계약 파운데이션 — 구현 상태 (이 커밋)

| §1 조항 | 구현 | 위치 |
|---|---|---|
| 1.1 Result Envelope 단일 shape | ✅ `make_envelope()` — 실행기 전용 생성자. 도구는 raw payload 반환, **실행기가 봉투를 만든다**(Tier-A: 스펙의 실패모드 "개별 도구가 봉투를 제각각 만든다"의 구조적 방지 = 생성 지점 1곳; 101개 도구가 각자 dict를 빚는 것보다 강한 보장) | `agenttools/envelope.py` |
| 1.1 verdict는 to_api만·FOLD만 | ✅ FOLD-ELIGIBLE 도구의 `"verdict"` 키만 봉투로 승격(to_api-shape 검증); 비-FOLD의 verdict는 **가시적으로 strip**(`verdict_stripped_non_fold_tool` 라벨 — 조용히 통과 0) + 회귀가 라이브 도구 0건 강제. 손수 빚은 grade dict는 생성자에서 ValueError | `executor.execute_enveloped()` |
| 1.3 에러 6종 closed-set | ✅ INVALID_INPUT/NOT_FOUND/EXEC_FAILED/TIMEOUT/BLOCKED/UNDECIDABLE — 7번째 코드는 생성자가 거부. 예외 매핑: ValueError(경로탈출 등 도구 자체검증)→INVALID_INPUT · FileNotFoundError→NOT_FOUND · TimeoutError/TimeoutExpired→TIMEOUT · Permission/ConnectionError→BLOCKED · 그 외→EXEC_FAILED | envelope.py + executor.py |
| 1.4 정직 라벨 | ✅ `Tool.labels` 필드(등록 시 선언) → 모든 봉투에 자동 부착. §1.4 강제목록은 해당 v2 도구 구현 시 등록부에 선언 | registry.py |
| 1.5 샌드박스 3클래스 | ✅ `Tool.sandbox` ∈ {READ,WRITE,EXEC} 등록 검증 + 기존 37 전수 분류(29/7/1, §1 표) | registry.py + catalog_*.py |
| 1.5 R7 safe_checkpoint 게이트 | ✅ **훅 선설치**: `execute_enveloped()`가 WRITE 도구를 `allow_write=True` 없이 **BLOCKED로 거부**. R군의 실제 safe_checkpoint(#340)가 이 인자의 유일한 합법 통행로가 된다. v1 `execute()` 경로는 R군 랜딩까지 기존 동작 유지(도구 자체 방어 — 덮어쓰기 거부·유일성 검증·safe_path — 가 현행 방어선) | executor.py |
| 1.5 cost | ✅ wall_ms 실측 · tool_calls=1 · **subprocess_ct=None(미계측 = 정직한 unknown, 0으로 위장 안 함**; 계측은 후속) | envelope.py |
| 1.2 입력 스키마 사전검증 | ⚠️ **부분**: 스키마 밖 인자는 파이썬 호출층 TypeError→INVALID_INPUT으로 잡힘(기존 zero-dep 판단 유지 — jsonschema 패키지 없음). 선언적 required-키 사전검증은 v2 도구 첫 군(P) 구현 시 `_schema` 기반 경량 체커로 추가 예정 | 후속 |
| 1.6 provider 무관 | ✅ 기존 구조 그대로(execute/execute_enveloped 둘 다 provider 인자 자체가 없음 — 10H Task 4 회귀가 잠금) | 기존 |
| 1.7 LLM 비호출 | ✅ 기존 구조 그대로(도구 fn 어디에도 provider/LLM 경로 없음) | 기존 |

## 4. 남은 것 (이 파운데이션 위에서)

v2 군 구현 순서(#336~#342): P → K → J → L → R → M → N·O·Q. 각 군은 이 봉투/코드/라벨/샌드박스를
등록부 선언만으로 상속한다 — 봉투를 손으로 만들 수 없다(구조적). 3~8차는 각자 §3.1을 이 문서에 누적.

### P군 상태: ✅ 구현 완료 (`agenttools/catalog_context.py`, 11/11, 도구 37→48)
전부 READ·PLAIN. **Tier-A override**: 설계서의 P1/P3 ACCEL 제안은 검증된 accel/ 엔진 위임이 없어
PLAIN으로 등록(Phase-1 선례와 동일 근거; 5차 AN1 캐시 엔진이 실재하게 되면 delegate와 함께 승격 가능).
P10은 기존 todo_scan을 재호출(재구현 0). 토큰 수는 stdlib 근사(chars//4)로 payload에 `token_note` 명시.
회귀 `test_catv2_p_group_context` + 실측 카운트 테스트 37→48 동커밋 갱신(스스로의 규칙: "드리프트는
같은 커밋에서 갱신, 조용히 없음").

### K군 상태: ✅ 구현 완료 (`agenttools/catalog_debug.py`, 15/15, 도구 48→63)
READ 9 · WRITE 1(print_instrument — R7 게이트 대상) · EXEC 5(ddmin/bisect×2/settrace/heisenbug — 전부
run_python_file과 동일한 §BE 경계: 워크스페이스 .py + argv, 임의 shell 금지, timeout+출력캡).
**Tier-A override 3건**: K3 ACCEL(신규 ddmin)·K8 FOLD(신규 CFG)·K15 ACCEL(조합) 제안 전부 기각→PLAIN —
검증된 fold/accel 엔진 위임이 아님(RF-5). K8은 동적 raise를 UNDECIDABLE로 위장하지 않고 `unresolved`
목록으로 정직 반환(PLAIN은 verdict/UNDECIDABLE 계열 판정을 흉내내지 않는다). **파운데이션 확장**:
`envelope.BlockedError/UndecidableError` 타입드 에스케이프(+executor 매핑) — K4가 flaky 테스트를
PermissionError 오남용 없이 BLOCKED로 신고. 회귀 `test_catv2_k_group_debug` + 카운트락 8건 동커밋 갱신.
