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
| 테스트 | **280 통과 / 280** (`test_build.py`, 결정론 실행; 아래 명령) — §MRJ provider-wiring +1 · §BE 브라우저-떠넘김/격리 +1 · §BS-1 emission-boundary gate +1 · MR.JEFFREY v2.2 Task-1 `ollama_local` preset +1 · per-provider base_url 해석 수정 +1 · 온보딩 UI 구조 +1 (`test_catalog.py` **267** — local-provider kernel_verdict-ADT parity +1 · local_models.py failure-honesty +1 · 10H Task-1 agenttools 프레임워크 +9 · agenttools production-wiring(gap=0 유지) +1 · 10H Task-2 tool catalog +4) |
| 10H Task 1 | **✅ 완료.** 새 `agenttools/` 패키지(registry+router+executor+capability+toolcall) — 카탈로그는 커도(300+) 매 요청 노출은 항상 소수(≤6, router 구조적 보장); Ollama는 `/api/show`의 실제 `capabilities` 배열을 라이브 체크해야만 tool 노출(미확인 시 조용히 no-tools 폴백); provider 분기는 `claude_agent.claude_generate`와 동일; `agentic.py`에 `enable_tools=False` 옵트인으로만 연결(기존 동작 100% 불변). 부작용 하나 발견+수정: 새 패키지가 `engine_inventory.py`의 gap=0 감사를 깨뜨려서(`test_bl/bn/bo/bq/br`), 다른 패키지들과 동일한 방식(`engine_dispatch.agenttools_reach` + `_WIRED_PACKAGES`)으로 배선. 상세는 STATUS.md. |
| 10H Task 2 | **✅ 완료 — 정직한 21개, 300개 아님.** RF-5("count≠fold-rate")와 지시문 자체의 "실망스러워도 정직한 숫자" 원칙에 따라 억지로 채우지 않음: PLAIN 15(`catalog_plain.py` — 파일 I/O 7종·git 7종·`run_python_file` 1종, 전부 워크스페이스 루트 샌드박스 + git 인자-주입 차단) + FOLD-ELIGIBLE 4(`catalog_fold.py` — `frontend.dispatch`/`closure_classifier`/`extract.checksum`/`extract.parse_arith`에 위임) + ACCEL-ELIGIBLE 2(`catalog_accel.py` — `accel.verified_parallel`에 위임). 300+로 갈 여지는 있음(카탈로그 94종 변환·14 메커니즘 등) — 각기 다른 호출 규약이라 개별 래퍼가 필요한 정직한 미래 작업이지, 기계적 개수 채우기가 아님. 모든 tool은 `test_10h_catalog_tools_functionally_real`에서 실제 executor 경로로 실행 검증(피보나치→C-finite EXACT 등). 부작용 하나 발견+수정: self-test가 전역 레지스트리에 프로브 tool을 영구 등록해버려 카운트가 드리프트 — `registry.unregister()` 추가로 해결. 상세는 STATUS.md. |
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
# … 273 passed, 0 failed
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
