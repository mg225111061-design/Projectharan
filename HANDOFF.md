# HANDOFF — MR.JEFFREY / HARAN  (다음 세션 AI에게 주는 전부)

> 너는 **새 세션**이다. 이전 세션의 기억이 없다. 이 파일은 정직한 현재 상태다 — 한 줄도 장식이 아니다.
> 더 자세하고 항상-최신인 단일 진실원천(single source of truth)은 **`STATUS.md`** 다. 충돌하면 STATUS.md가 이긴다.
>
> 한 줄 요약: **Claude(LLM)가 제안하고, MR.JEFFREY 엔진이 그것을 기계적으로 *증명*한다.** 무기는 속도가 아니라
> — 정직하게 증명된 정확성이다. 증명되면 EXACT(증명서 첨부), 근사면 PROBABILISTIC(ε,δ), 아니면 정직한 DECLINE.

---

## 0. 지금 상태 (FRESH — 추측 아님, 측정값)

| 항목 | 값 |
|---|---|
| 레포 | `mg225111061-design/Projectharan` |
| 개발 브랜치 | **`claude/charming-brahmagupta-q4wwgh`** (이전 `funny-maxwell`의 상위집합 — 여기서 계속) |
| 테스트 | **280 통과 / 280** (`test_build.py`, 결정론 실행; 아래 명령) — §MRJ provider-wiring +1 · §BE 브라우저-떠넘김/격리 +1 · §BS-1 emission-boundary gate +1 · MR.JEFFREY v2.2 Task-1 `ollama_local` preset +1 · per-provider base_url 해석 수정 +1 · 온보딩 UI 구조 +1 (`test_catalog.py` **271** — local-provider kernel_verdict-ADT parity +1 · local_models.py failure-honesty +1 · 10H Task-1 agenttools 프레임워크 +9 · agenttools production-wiring(gap=0 유지) +1 · 10H Task-2 tool catalog +4 · 10H Task-3 swebench +4 · 번들 Task-1 launcher 스모크 +1 · 카탈로그-100 Phase1 A+D +1 · 코더-모델 티어 카탈로그+하드웨어 추천 +3 · 카탈로그-v2 공통계약 파운데이션 +1 = **277**) |
| 10H Task 1 | **✅ 완료.** 새 `agenttools/` 패키지(registry+router+executor+capability+toolcall) — 카탈로그는 커도(300+) 매 요청 노출은 항상 소수(≤6, router 구조적 보장); Ollama는 `/api/show`의 실제 `capabilities` 배열을 라이브 체크해야만 tool 노출(미확인 시 조용히 no-tools 폴백); provider 분기는 `claude_agent.claude_generate`와 동일; `agentic.py`에 `enable_tools=False` 옵트인으로만 연결(기존 동작 100% 불변). 부작용 하나 발견+수정: 새 패키지가 `engine_inventory.py`의 gap=0 감사를 깨뜨려서(`test_bl/bn/bo/bq/br`), 다른 패키지들과 동일한 방식(`engine_dispatch.agenttools_reach` + `_WIRED_PACKAGES`)으로 배선. 상세는 STATUS.md. |
| 10H Task 2 | **✅ 완료 — 정직한 21개, 300개 아님.** RF-5("count≠fold-rate")와 지시문 자체의 "실망스러워도 정직한 숫자" 원칙에 따라 억지로 채우지 않음: PLAIN 15(`catalog_plain.py` — 파일 I/O 7종·git 7종·`run_python_file` 1종, 전부 워크스페이스 루트 샌드박스 + git 인자-주입 차단) + FOLD-ELIGIBLE 4(`catalog_fold.py` — `frontend.dispatch`/`closure_classifier`/`extract.checksum`/`extract.parse_arith`에 위임) + ACCEL-ELIGIBLE 2(`catalog_accel.py` — `accel.verified_parallel`에 위임). 300+로 갈 여지는 있음(카탈로그 94종 변환·14 메커니즘 등) — 각기 다른 호출 규약이라 개별 래퍼가 필요한 정직한 미래 작업이지, 기계적 개수 채우기가 아님. 모든 tool은 `test_10h_catalog_tools_functionally_real`에서 실제 executor 경로로 실행 검증(피보나치→C-finite EXACT 등). 부작용 하나 발견+수정: self-test가 전역 레지스트리에 프로브 tool을 영구 등록해버려 카운트가 드리프트 — `registry.unregister()` 추가로 해결. 상세는 STATUS.md. |
| 10H Task 3 | **✅ 완료 — 정직하게 BLOCKED, 조작 없음.** 실제 SWE-bench 교체가 안 되는 이유를 직접 테스트로 확인: huggingface.co·HF datasets-server 둘 다 프록시에서 403, 외부 저장소 `git clone`은 세션 허용목록 3개 밖에서 차단, `api.github.com`도 차단/리다이렉트. 게다가 스키마 자체도 다름: `harness.Task`는 실행 가능한 파이썬+`(args,expected)`가 필요하지만 실제 인스턴스의 `FAIL_TO_PASS`/`PASS_TO_PASS`는 체크아웃된 저장소에 대한 pytest 노드 ID라 실제로 클론+실행해야 알 수 있음(데이터 재구성이 아님, `real_dataset.harness_conversion_gap()`에 정직하게 설명). 대신 실제 스키마를 정확히 구현: `swebench/real_dataset.py`가 진짜 필드명(`instance_id`/`repo`/`base_commit`/`patch`/`test_patch`/`FAIL_TO_PASS`/`PASS_TO_PASS` 등)을 파싱하고, 불완전한 인스턴스는 거부하고, `live_fetch()`는 매번 실제 네트워크 시도(기억이 아니라 진짜 요청)를 하며 `"OK"`/`"BLOCKED"`만 정직하게 반환(이번 세션 결과: `"BLOCKED"`). `mini_bench()`는 손대지 않음 — 교체할 실데이터가 없으므로 기존 정직한 합성 벤치가 그대로 유지. `webapi/engine_dispatch.swebench_reach()`로 배선. 상세는 STATUS.md. |
| 10H Task 4 | **✅ 완료.** 새 병렬 메커니즘을 만들지 않고 기존 `test_v22_local_provider_parity()`를 그대로 확장(지시문의 "don't invent a new parity mechanism" 명시 준수) — 원래 단언(같은 코드에 대해 provider=anthropic vs ollama_local이 byte-identical kernel_verdict trace/grade/optimization/FoldCache-key)은 전부 그대로 두고, tool 가용성/실행 패리티 블록만 덧붙임. 증명된 것 4가지: (1) `router.select_tools`/`executor.execute` 둘 다 `provider` 파라미터를 아예 받지 않음(`inspect.signature`로 확인, 구조적으로 구분 불가) (2) `toolcall.py`에 `_execute(name, args)` 호출이 정확히 2곳(anthropic·openai 분기)뿐 — 중복 구현 없음 (3) Ollama 라이브 capability gate를 통과했다고 가정하면 두 provider가 완전히 동일한 tool 집합을 받음(와이어 인코딩만 합법적으로 다름: 네이티브 vs OpenAI 래핑) (4) gate 미확인 시(이 샌드박스의 실제 상태) `ollama_local`만 정직하게 빈 tool 목록, `anthropic`은 영향 없음 — 크래시도 조작도 없음. 이번 작업에서 새 회귀는 없음(런타임 코드 무변경, 기존 테스트 확장뿐). 상세는 STATUS.md. |
| 10H Task 5 | **✅ 완료 — 오차(orphan) 0.** `PRODUCTION_LEDGER.md` 신규 생성(사전에 부재 확인) — Task 1-4의 신규 파일 9개(`agenttools/` 9모듈 + `swebench/real_dataset.py`) + 수정된 기존 파일 3개(`agentic.py`/`webapi/engine_dispatch.py`/`engine_inventory.py`)를 전부 등록. 등급은 `engine_inventory.classify()`의 실측값(레포 자체 어휘) 그대로, 눈대중 아님 — 행마다 실제 테스트/reach-probe 근거 명시. 실제로 하나 발견: `toolcall.py`의 `transitive` 판정은 "같은 패키지"에만 근거하는데(자체 self-test는 안 건드림, `__init__.py` 직접 확인), 진짜 도달성은 `agentic.py`의 무조건 최상위 import(실제 프로덕션 진입점)임 — 분류기 판정만 베끼지 않고 grep으로 재확인. 코드 변경 없음(순수 문서, 어떤 테스트도 이 파일을 참조 안 함 — grep 확인) — 전체 게이트 재실행은 불균형하다고 판단해 생략, `test_docs_not_stale`만 재확인. **Part 2 — `AUDIT_LEDGER.md` Batch 1 완료.** "7개 외 나머지" `*_grade` 백로그를 정밀 재검색(93개 파일, 지시문의 대략치 ~115 대체) — 6개 병렬 읽기전용 조사 에이전트(mathmode/·pillar3/×2·catalog/×2·root+gpu+native+misc)가 라인 번호 근거를 수집(최종 판정은 안 맡김 — 등급-정직성 판단은 감사자 몫). 6개 그룹 전체에서 샘플 5건을 직접 재확인 후 신뢰. **결과: 93개 전부 CLEAN** — 모든 disposer가 EXACT/PROBABILISTIC 전에 실제 검증(z3 증명·차분 교차검증·정확 재대입·전수 한계·ADT 구성)을 수행하고 정직한 DECLINE 경로 보유; name-set-membership 지름길·무근거 리터럴 0건. `AUDIT_LEDGER.md` 17-109행에 기록(번호 연속성·컬럼수 스크립트 검증) — **Batch 1 완료**(109/109), 기존 7행(`recall_integrate.py`)만 소유자 판단 대기 FLAG 유지. 상세는 STATUS.md. |
| 번들 Task 1 | **✅ 완료 — 원클릭 번들의 융합층.** `local_bundle/launcher.py`(stdlib만): 무수정 공식 Ollama를 `OLLAMA_ORIGINS` 프리셋으로 기동(수동 CORS 설정 제거) + 기존 `server.py` 스택을 `HARAN_PROVIDER=ollama_local` env만으로 데몬 기동(서버 코드 0줄 변경) + 종료시 두 자식 일괄 정리. 포크 아님 — 프로세스/API 층 배선. NOTICE + Ollama LICENSE 원문 동봉(MIT 고지). parity 회귀 확장: 번들 env(`JEFF_BUNDLE`)는 검증 경로가 읽을 수조차 없음을 구조적으로 잠금. 스모크 회귀: mock-ollama+실데몬 기동·배선·SIGTERM 정리 실측. 게이트: catalog 272/272, build 279/280(실패 1 = 기존 문서화된 triage 타이밍 플레이크, diff 무관 구조 확인 — STATUS.md 상세). |
| 카탈로그-100 Phase 1 (A+D, 도구 21→37) | **✅ 완료.** 설계서 §9 순서 1번. 기존 21개와 대조해 **겹치면 재사용, 신규 16개만 추가**: `catalog_explore.py`(신설, A군 11 — file_write/file_patch/dir_tree/symbol_find/ast_outline/docstring_extract/import_graph/call_graph/reach_closure/todo_scan/loc_stats) + `catalog_plain.py`에 D군 5(recent_changes/git_apply_patch/git_checkout_commit/repo_clone_shallow/git_stash_ops). **16개 전부 PLAIN**(Tier-A: 설계서가 import_graph/call_graph=FOLD·reach_closure=ACCEL로 제안했으나 검증엔진 위임이 아닌 순수 AST/그래프 계산이라 RF-5상 PLAIN이 정직 — 설계서 원칙 1 "애매하면 PLAIN" 적용). 안전: catalog_plain의 `_safe_path` 재사용, file_write=덮어쓰기거부, file_patch=유일성검증, git_stash_ops=화이트리스트, repo_clone=https만. 회귀 `test_cat100_ad_group_functional`(실행 3+·file_patch 거부·라우터 ≤6 라이브 확인). intent 라우팅 매핑(§7)은 후속으로 정직히 유보(기존 keyword 라우터가 이미 ≤6 보장). 게이트: catalog 273/273. 상세는 STATUS.md. |
| 코더-모델 티어 카탈로그 + 하드웨어 추천 | **✅ 작업 1·2 완료(백엔드).** `webapi/coder_models.py`(stdlib만): 4티어(local_frontier/upper/mid/entry)+cpu_offline+API-only 시드 카탈로그(모델마다 vram_gb·quant·license·coder_evidence 인용) + `live_library_names()`가 `ollama.com/library`를 실제로 조회해 이름을 검증(실패시 `"BLOCKED"`+`seed-fallback`+`fetched_at` 타임스탬프 정직 표기, 절대 안 raise) + `recommend(vram_gb)`가 **"들어가는 가장 큰 코더"**를 티어 상→하로 선택(MoE VRAM 왜곡 회피 위해 원시 footprint 정렬 아닌 큐레이션 티어순; 3-bit는 `tight_only`로 강등—표준이 안 들어갈 때만; 0/None→CPU). 라우트 `/api/coder/catalog`(`live=0` 토글)·`/api/coder/recommend`(`vram_gb`, 파싱불가→None). `:cloud` 모델은 로컬 티어에서 격리(quarantine). 회귀 3건(`test_coder_tier_catalog_honest`·`test_coder_recommend_largest_that_fits`·`test_coder_live_fetch_honest`). 파이프라인 동등성은 이미 확립(v2.2)—이건 UX 계층. **작업 3(Ollama풍 모델선택 UI)·작업 4(parity 티어표본)는 다음 체크포인트.** 게이트: catalog 276/276. 상세는 STATUS.md. |
| 최상위 모드 | **CODE**(OMEGA 검증 최적화기) + **MATH**(MATH-Ascent) — UI 토글로 전환 |
| MATH 아스널 | **17 패밀리**(아래) + 중심 도구 `fold` + O(1) `broth`(3,772 항목) |
| 배포 | Docker, `server:app`가 `mrjeffrey.html`(단일파일 한국어 UI)를 `/`에서 서빙 |
| MR.JEFFREY v2.2 | **✅ 완료.** "다운로드=Ollama 스킨"이 아니라 "다운로드=JEFF 엔진+Ollama 로컬추론 융합". `provider.py` `ollama_local` 프리셋 + `claude_generate` per-provider base_url 버그 수정 + `webapi/local_models.py`(stdlib만) + `/api/ollama/{status,models,pull}` + `mrjeffrey.html` 온보딩(API vs 로컬) — 두 경로 모두 같은 `sendMessage`/`checkGrade` 재사용(포크 없음, grep-count-1 회귀), 로컬만 `data-skin="ollama"`(§BG 배지는 절대 재스타일 안 함). 근거: `test_v22_local_provider_parity`(provider=anthropic vs ollama_local 모킹 동일 kernel_verdict) + 이번 세션 실제 Playwright 클릭-스루. **`haran.html`/`mrjeffrey_landing.html`은 미수정**(둘 다 mrjeffrey.html 부재시만 쓰이는 폴백 — 상세는 STATUS.md). |
| HARAN-50 | **✅ COMPLETE — 50 NAMED layer-1 알고리즘 전부 CONFIRMED** (`algo50.py`; A20·B10·C15·D5, 0 PARTIAL·0 GAP). 8 gaps 건설 + 9 partials 폐쇄(전부 1-커밋-1-항목, 증명서 동반·적대적 테스트). §2 broth 확장(`haran_broth.py`, 13개 알고리즘 1,367항목 @ ~0.07µs O(1), 전부 재실행으로 재검증) · §3 측정 커버리지(`algo50_coverage.py`, MATH 53건/25알고리즘 + CODE 코드형태 39붕괴[6타깃×5형태 + 4중첩 + 4필터 + 1지수], 적대적 6/6 DECLINE) · §4 tier 라우팅(`algo50_router.py`, broth-hit 즉시·normal은 heavy solver 금지). §X 정직 캡션 test-enforced(CAD 이중지수·Lucas–Lehmer O(p)·CP/Tucker·ECM NP-hard→DECLINE). 상세는 STATUS.md / CODE_UPGRADE_REPORT.md §5. |
| 빌드 히스토리 | 캠페인별 상세 온보딩 행(§FRONT-END·§AZ·§AU·…·§AE 등 43개, 각 1–3천 자)은 `BUILD_LOG_catalog.md`의 §HANDOFF-ARCHIVE로 **이전**했습니다 (§BF FIX-4 — HANDOFF는 한 페이지 현재상태만). 현재 상태 = 위 표 + 단일 진실원천 `STATUS.md`. |
| NATIVE ARSENAL | **무의존(zero-dep) 인-레포 구현 — 14/14 메커니즘 실제 가동 + 연구도구 네이티브화.** 외부 의존 0(소스 전체에서 z3+stdlib+numpy+기존sympy만; 의존성 감사 `forbidden_present==[]`). 측정(`catalog/arsenal_report.py`): **14/14 메커니즘 가동, 19 네이티브 코어 LIVE, 8 거대엔진 fallback+defer**. PHASE 0(14 완성): `renormalize.py`(M6 정확 Markov lumping+멀티그리드 잔차) · `guaranteed_structure.py`(M10 Erdős–Szekeres/비둘기집/Ramsey 구성적 추출). PHASE 1: `native_lattice.py`(LLL 유니모듈러 검증·정수관계 full-precision 재검·Smith Diophantine) · `native_sequence.py`(**Berlekamp–Massey = 가짜난수↔진짜난수 게이트** L≪n/2 fold·L≈n/2 DECLINE; Re-Pair 무손실 SLP) · `native_realroots.py`(Sturm 실근격리). PHASE 2: `native_rewrite.py`(Knuth–Bendix 단어문제) · `native_modelcount.py`(정확 #SAT, 2-순서+brute 교차검증) · `native_unify.py`(MGU). PHASE 3: `native_telescope.py`(Gosper 초기하 합; 인증서 보호 — 틀린 부정합 절대 통과 못함). PHASE 4(WALL 2): `native_prng.py`(LCG/LFSR 복구, replay 인증; **보안 CSPRNG/SHA-256 → 전경로 DECLINE — 불가능 코어 불변**). PHASE 5(거대엔진): Gröbner/CAD/CAPD/Walnut/QCMod 호출부+인-레포 fallback+정직 defer. 모든 fold per-instance 인증서 재검·lossless 게이트 경유·위양성 0. `test_catalog.py` **38/38**, test_build 273 영향 없음. 상세: `BUILD_LOG_catalog.md` §D. ──────── (이전 캡스톤) |

**※ 오래된 과거 지시 무시:** 예전 HANDOFF는 "`haran-web/`를 Projectharan에 push하라"고 했다 — 그건 **이미 끝났다**.
지금은 Projectharan 위에서 직접 개발 중이고, 앱은 `server.py`가 서빙한다. 그 작업은 더 이상 할 일이 아니다.

### 결정론 테스트 실행 (반드시 이 스레드 캡으로 — 부하성 flake 방지)
```bash
cd /home/user/Projectharan
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 test_build.py
# … 280 passed, 0 failed
```
부하(전체 동시 실행) 하에서만 흔들리는 알려진 flake: HyperLogLog(`test_round2_sublinear_sketches`),
`test_pillar3_stage2_compounding_loop`, 동시성 타이밍 게이트(`test_stage1_clockA_bestofn` — 5개 동시작업 wall<180ms),
일부 절대-임계 perf 게이트(`test_phaseD2_structural_detectors` SoA ~1.3× 등) — **전부 단독 실행 시 통과**(부하 flake, 회귀 아님).
(§0.5 C6에서 perf 게이트를 정확성 게이트와 분리하는 중.)

---

## 1. 규율 (CONSTITUTION — 절대 어기지 마라)
- **MEASURED-ONLY / WHOLE-PROGRAM.** 속도 주장엔 항상 핫스팟 비율 f + Amdahl 천장 1/(1−f), 비율 ≤ 천장. kernel ≠ whole-program. n 명시.
- **등급 ADT:** EXACT(기계검증 증명서 / 결정절차 / 유계-전수, 경계 명시) · PROBABILISTIC(ε,δ — δ≤10⁻¹⁸라도 EXACT 아님) · DECLINE(닫힌형 없음/미결정 — 정직, 위엄). 등급은 절대 섞지 않는다.
- **LLM은 제안만, 검증기가 결정한다.** 틀린 "증명됨"은 정정대상 correctness 버그. 가짜 통과보다 정직한 UNVERIFIED.
- **No Lean/Coq/Isabelle 런타임 의존(=0).** Z3는 허용(+자체 bit-blaster 구축 중, §2). phone-home=0(제공자 API 제외). 키는 세션 전용.
- **normal/extend** 분리(2-tier — 과거 세 번째 티어 `fast`는 §BT-0 아키텍처-전환 지시서로 **은퇴**했다; 그 즉시-반환
  동작은 normal 자신의 내부 certified-only early-exit로 흡수됨 — PROBABILISTIC-for-speed 허용도 함께 은퇴, early-exit는
  EXACT만 반환)를 CODE와 MATH 둘 다 안에서 보존(커밋마다 불변식). **이 2-tier 골격 자체의 재설계는 여전히 금지** — §BT-0은
  fast 흡수 하나만 승인된 전환이었고, 그 밖은 확장만 허용.
  두 티어는 **강제되는 벽시계 예산**의 별개 역할: normal ≈ 30초(첫 수로 certified-only early-exit 시도, 없으면 전체
  compounding loop로 낙하) · **extend ≈ 8분 BOUNDED(무제한 아님)**.
  extend는 예산 소진 시 도달한 최선의 **증명된** 결과(또는 정직한 부분결과)를 반환 — 예산 초과 실행 금지, 시간 채우려 결과 위조 금지, 빨리 가려고 등급 약화 금지.
  계약=`pillar3/mode.py`, 런타임=`mode_budget.run_under_mode_budget`, 하드 워치독=`latency_budget.run_with_budget`(데몬 스레드 — 어떤 티어도 멈춰 매달리지 않음). `test_mode_budget_roles`.

## 2. 두 최상위 모드
- **CODE**(`server.py`+`pillar3/`+`webapi/`): 코드 붙여넣기 → 더 빠른 *검증된* 코드 → 등급. OMEGA 라운드 1–3 완료, EXACT-share ~68%.
- **MATH**(`mathmode/`): 문제 입력/파일첨부 → fold 우선 → 17 패밀리 아스널 → 가시적 등급-태그 추론 + 증명서.
  - 패밀리: number_theory · combinatorics(Gosper) · linear_algebra · algebra · geometry · certified_numeric ·
    optimization(LP duality) · science_engineering(차원) · probability · inequalities · differential(ODE) ·
    graph · special_functions(Γ,ζ) · calculus(∫ 미분검증) · logic(Z3 SAT/타당성) · + `fold` + `broth`.
  - 진입점 `mathmode/solver.py`: free-text/JSON → `solve_in_mode(mode)`; `MathSolution.trace()`가 추론을 보여줌.
  - 엔드포인트: `POST /api/math/solve`, `POST /api/math/ingest`(파일첨부, 아카이브 안전해제 포함).

## 3. 핵심 파일 지도
- `server.py` — 운영 진입점(Docker CMD `python server.py` → `server:app`). `/` = `mrjeffrey.html`. `/api/*`.
- `mrjeffrey.html` — 단일파일 한국어 제품 UI(§S 재구성: 세 기둥 **SECURED·FAST·ACCURATE**, 붙여넣기+제공자 흐름, 세션전용 키; 숫자/등급/천장 없음. MATH UI·CODE⇄MATH 토글은 은퇴, MATH 엔진은 서버에 잔존).
- `mathmode/` — MATH 엔진(22 모듈). `pillar3/` — CODE 엔진. `webapi/` — FastAPI/engine_bridge.
- `test_build.py` — 단일 결정론 스위트(206). `kernel_verdict.py` — 등급 ADT(EXACT/PROBABILISTIC/DECLINE 강제).
- `STATUS.md` — **단일 진실원천**(현재 상태/테스트수/등급분포/done·진행·declined). 과거 캠페인 리포트는 `reports/archive/`.

## 4. 배포 (사용자 액션 1건)
Render(Docker)에서 **Branch를 `claude/charming-brahmagupta-q4wwgh`로 지정** → Root `.`, Dockerfile `./Dockerfile`
→ Manual Deploy(Clear build cache & deploy). 라우트/CMD/`/api/math/*`는 로컬 검증 완료; 리빌드는 사용자 대시보드 작업.
자세한 건 `DEPLOY_NOTES.md`.

## 5. 지금 할 일 (NATIVE-CORE 지시, 진행 중)
- **§0.5 엔트로피 정리 ✅** (C1 HANDOFF 정정 · C2 STATUS.md 단일화+리포트 아카이브 · C3 키-보안 문구 · C4 모듈 매핑(e-graph→§1) · C5 버전체계 · C6 perf↔correctness 분리 · C-process stale-doc 테스트).
- **§3 ✅** AST-깊이 fast-triage(캐시 앞단, `proof_triage.py`) — 결정론 라우팅·무손실 판정·회귀 시연+수정(`proof_cache.measure_triage`).
- **§2 ✅** 무의존 bit-blasting SMT(`bitblast_smt.py`: 자체 DPLL SAT + bit-blaster + 독립 인증서 체커, coqc/cvc5/Bitwuzla/Lean/Z3 전부 불필요). 고정폭 QF-비트벡터(add/sub/상수곱/and/or/xor/not/shift/eq/ult)를 **폭 내에서 EXACT**(경계 2^w)·결정론(결과+인증서 동일)·SAT 모델은 작은 TCB가 재검증. `pillar3/bv_validate.bv_equiv_inhouse`에 배선하고 sound peephole에서 Z3와 교차검증(`cross_check_inhouse_vs_z3` → 전부 일치). **정직한 범위(§X): cvc5/Z3 동급 아님** — 부호비교 `>`·나눗셈·ite-mux·배열/실수/무한정수 없음; overflow-unsafe peephole(부호/나눗셈/ite)은 Z3에 남김.
- **§1 ✅** 무의존 Rust 코어(`rust_core/` std-only cdylib + ctypes, PyO3/maturin/cffi/flint/faer 전부 불필요; `rust_core.py` 브리지). v34가 미룬 것 구현: 평면 **arena AST**(결정론 1패스), **결정론 고정정밀 다중모듈러 CRT ring**(고정 4-소수 기저 Garner 결합 → 정확 정수, Python bignum 대체; |v| ≤ MAX_ABS=(∏p−1)/2(123비트) 내에서 EXACT, 경계 초과는 기저 확장 또는 DECLINE — 랩이 정확히 경계에서 일어남을 정직히 명시), 유계 **유리수 복원**, **결정론 고정순서 모듈러 dot**("SIMD" 데모: 정수+고정순서 ⇒ 벡터화/스레드 무관 비트동일). 검증: Rust≡Python differential + **형식적 유계-전수 등가성**(arena×대입 12,789 케이스 전수, 불일치 0) + CRT 왕복 전수. `test_native_s1_rust_core`. **정직한 측정:** 이 단위에서 속도 교차 없음(ctypes 오버헤드 vs C-빠른 CPython int) ⇒ 속도 **UNVERIFIED**, 정확성이 산출물(v40-phase7 RNS 정직성과 동일). 네이티브는 런타임만 바꾸고 등급 불변; `target/`는 환경 빌드(gitignore), Python ring이 검증된 폴백.
- **§4 ✅** 멀티-LLM 라우팅 추상화 + 고충실 오프라인 mock(`llm_router.py`, `provider.py`/`claude_agent.py` 위). 라우터가 와이어 트랜스포트(Anthropic Messages / OpenAI chat.completions / Gemini generateContent)를 고르고 라이브와 동일하게 요청을 빚어, 제공자-모양 raw를 돌려주는 mock을 통과시켜 다시 파싱 — 모든 게이트웨이(anthropic, openai-compat 포함 OpenRouter/Z.ai/DeepSeek, gemini, groq)의 라우팅+직렬화+파싱이 네트워크 0으로 결정론 실행. `test_native_s4_llm_routing`. **정직(§X):** mock은 항상 live=False/source=mock-sim:*(라이브로 위장 금지), 실제 egress 라이브 경로는 **UNVERIFIED**[egress 차단]이며 응답을 절대 날조하지 않음; 키는 호출당 인자·마스킹·미기록. LLM은 제안, 검증기가 채점.
- **§5 ✅** 의존성 제거, 측정+강제(`dependency_audit.py`, `test_native_s5_dependency_audit`). 금지 대형-프루버/네이티브-바인더(coqc/cvc5/Bitwuzla/Lean/PyO3/maturin/cffi) = **임포트 0**; 등급 ADT + NATIVE-CORE 7모듈은 **stdlib 전용**(서드파티 폐포 공집합, 정적+런타임 증명: numpy/sympy/z3/anthropic/openai/numba/llvmlite 전부 숨긴 서브프로세스에서도 전부 임포트됨); **numpy는 코어에 불필요**(특정 CODE/MATH 수치 커널의 무거운 의존일 뿐); 17개 선택 패키지는 lazy/우아한 강등. 최종 하드 top-level: `fastapi, numpy, pydantic, sympy, z3`.
- **NATIVE-CORE 완료** — 전체 리포트 `NATIVE_CORE_REPORT.md`(§X "주장하면 안 되는 것" 원문 보존). 네이티브 빌드/라이브 egress는 샌드박스 차단 시 **UNVERIFIED**, Python 폴백이 검증된 길 — 날조 없음.
각 항목: 측정/증명, 등급, adversarial-wrong→DECLINE, 결정론 테스트, 커밋. §A2 대체(가짜 금지). 막히면 정직한 `UNVERIFIED[이유]`.
완료 후 `STATUS.md` + `NATIVE_CORE_REPORT.md` 갱신. 멈추지 마라.

## 6. 절대 하지 말 것
가짜 EXACT(증명서 없이), 등급 혼합, 측정 안 한 속도 주장, kernel을 whole-program처럼, 막힌 걸 안 막힌 듯,
네이티브/라이브 수치 날조(샌드박스에 toolchain/egress 없으면 `UNVERIFIED` + Python 폴백), 모델 식별자를 산출물에 기입.
