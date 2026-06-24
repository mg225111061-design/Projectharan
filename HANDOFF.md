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
| 테스트 | **271 통과 / 271** (`test_build.py`, 결정론 실행; 아래 명령) |
| 최상위 모드 | **CODE**(OMEGA 검증 최적화기) + **MATH**(MATH-Ascent) — UI 토글로 전환 |
| MATH 아스널 | **17 패밀리**(아래) + 중심 도구 `fold` + O(1) `broth`(3,772 항목) |
| 배포 | Docker, `server:app`가 `mrjeffrey.html`(단일파일 한국어 UI)를 `/`에서 서빙 |
| HARAN-50 | **✅ COMPLETE — 50 NAMED layer-1 알고리즘 전부 CONFIRMED** (`algo50.py`; A20·B10·C15·D5, 0 PARTIAL·0 GAP). 8 gaps 건설 + 9 partials 폐쇄(전부 1-커밋-1-항목, 증명서 동반·적대적 테스트). §2 broth 확장(`haran_broth.py`, 13개 알고리즘 1,367항목 @ ~0.07µs O(1), 전부 재실행으로 재검증) · §3 측정 커버리지(`algo50_coverage.py`, MATH 53건/25알고리즘 + CODE 코드형태 34붕괴[6타깃×5형태+4중첩], 적대적 6/6 DECLINE) · §4 tier 라우팅(`algo50_router.py`, broth-hit 즉시·fast는 heavy solver 금지). §X 정직 캡션 test-enforced(CAD 이중지수·Lucas–Lehmer O(p)·CP/Tucker·ECM NP-hard→DECLINE). 상세는 STATUS.md / CODE_UPGRADE_REPORT.md §5. |
| (이전) 진행 중 | **UNIFIED ARSENAL**(a 변환계 + b ~70 fold 패밀리 + c 물리) — §1 ✅ (G1·G2·G3·G4) → §2 ✅ (Petkovšek·Abramov·Risch·Kovacic·CAD) → §3 물리 P1–P9 ✅ → §4 transforms ✅ · ROUTER ✅ → **MATH recognition PHASE-1 ✅**. (NATIVE-CORE 완료: `NATIVE_CORE_REPORT.md`.) |

**※ 오래된 과거 지시 무시:** 예전 HANDOFF는 "`haran-web/`를 Projectharan에 push하라"고 했다 — 그건 **이미 끝났다**.
지금은 Projectharan 위에서 직접 개발 중이고, 앱은 `server.py`가 서빙한다. 그 작업은 더 이상 할 일이 아니다.

### 결정론 테스트 실행 (반드시 이 스레드 캡으로 — 부하성 flake 방지)
```bash
cd /home/user/Projectharan
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 test_build.py
# … 271 passed, 0 failed
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
- **fast/normal/extend** 분리를 CODE와 MATH 둘 다 안에서 보존(커밋마다 불변식). 디자인 승인됨 — 확장만, 재설계 금지.
  세 티어는 **강제되는 벽시계 예산**의 별개 역할: fast ≈ 1초(무거운 솔버 호출 금지) · normal ≈ 30초 · **extend ≈ 8분 BOUNDED(무제한 아님)**.
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
- `mrjeffrey.html` — 단일파일 한국어 UI(CODE⇄MATH 토글, 파일 드래그첨부, 등급 추론 뷰).
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
