"""
local_bundle — MR.JEFFREY 원클릭 번들의 융합층 (번들 지시서, 2026-07).
=====================================================================
사용자가 설치파일 하나만 받으면 Ollama(무수정 공식 바이너리 동봉 — 포크 금지, 프라임 1) + JEFF 로컬
데몬(기존 server.py/agentic/kernel_verdict/agenttools 스택 그대로 — 새 파이프라인 금지, 프라임 4) +
도구 카탈로그가 전부 설치·연결되게 하는 패키지다. 융합은 소스 안이 아니라 **프로세스/API 층**에서:
`launcher.py`가 동봉 ollama를 `OLLAMA_ORIGINS` 프리셋 상태로 기동하고(수동 CORS 설정 제거), 데몬을
`HARAN_PROVIDER=ollama_local` env로 기동해 둘을 배선한다.

라이선스 고지(프라임 2): 이 디렉토리의 `NOTICE` + `third_party/OLLAMA_LICENSE`(원문, MIT © Ollama)가
빌드 산출물 루트에 포함된다. 모델 가중치는 동봉하지 않는다(모델별 라이선스 상이 — 첫 실행 때 pull).

engine_inventory 분류: 이 패키지는 요청 엔진이 아니라 CLI 오케스트레이션/패키징이므로 `_DEV_PKGS`
(dev_tooling)로 분류된다 — reach-probe 배선 대상이 아님(그 배선은 요청 경로 엔진의 규약이다).
"""
