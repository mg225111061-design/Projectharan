"""
local_bundle/launcher.py — 원클릭 번들의 융합층 (번들 지시서 Task 1).
=====================================================================
하는 일 (전부 프로세스/API 층 — Ollama 소스는 절대 건드리지 않는다, 프라임 1):

  1. 동봉된 공식 Ollama 바이너리를 찾아 `ollama serve`로 기동하되, **`OLLAMA_ORIGINS`를 미리 세팅**해서
     우리 사이트/로컬 데몬 origin이 CORS 허용되게 한다 — 기존 "PC방 체크리스트 4번"(수동 CORS 설정)이
     사용자에게서 사라지는 지점이 정확히 여기다.
  2. JEFF 데몬 = **기존 server.py 스택 그대로**(프라임 4 — 새 파이프라인 금지)를 로컬 포트로 기동한다.
     provider 기본값은 서버가 이미 읽는 `HARAN_PROVIDER` env(provider.py)로만 `ollama_local`을 주입 —
     서버/검증 코드는 한 줄도 안 바뀐다. `JEFF_BUNDLE=1`은 표시(About/상태)용 마커일 뿐이며, 검증 경로
     (agentic/kernel_verdict)가 이 env를 절대 읽지 않음은 parity 회귀가 구조적으로 잠근다(같은 Verdict
     경로 — 프라임 4의 parity 확장).
  3. 종료(SIGINT/SIGTERM/atexit) 시 두 자식 프로세스를 terminate→wait→kill 순으로 정리한다.

순수 stdlib(런타임 zero-dep). 테스트 훅: `JEFF_OLLAMA_BIN`으로 바이너리를 주입할 수 있어 Linux
샌드박스에서 mock-ollama로 기동·배선·종료 스모크가 실행된다(진짜 Windows 번들에선 동봉 경로 탐지).

동봉 바이너리 탐지 순서: env `JEFF_OLLAMA_BIN` → <번들루트>/ollama/ollama(.exe) → <번들루트>/ollama(.exe)
→ 시스템 PATH의 ollama(고급 사용자가 이미 설치한 경우). 전부 없으면 **정직한 안내 후 데몬만 기동**
(크래시 금지 — 로컬 모델 없이도 API-provider 경로는 살아 있어야 한다).
"""
from __future__ import annotations

import argparse
import atexit
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import List, Optional, Tuple

DEFAULT_OLLAMA_HOST = "127.0.0.1:11434"    # Ollama 자체 기본값과 동일 — 기존 v2.2 감지 경로가 그대로 맞음
DEFAULT_DAEMON_PORT = 11500                # 로컬 전용 데몬 포트(프라임 4: "포트만 로컬용")


# ── 경로/구성 ────────────────────────────────────────────────────────────────────────────────────────


def bundle_root() -> Path:
    """번들 루트: PyInstaller 프로즌 실행이면 exe가 있는 디렉토리, 개발 모드면 이 파일의 디렉토리."""
    if getattr(sys, "frozen", False):      # PyInstaller가 세팅하는 표준 마커
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def find_ollama_bin() -> Optional[Path]:
    exe = "ollama.exe" if os.name == "nt" else "ollama"
    env = os.environ.get("JEFF_OLLAMA_BIN", "").strip()
    if env:
        p = Path(env)
        if p.exists():
            return p
    root = bundle_root()
    for cand in (root / "ollama" / exe, root / exe):
        if cand.exists():
            return cand
    which = shutil.which("ollama")
    return Path(which) if which else None


def compute_origins(daemon_port: int) -> str:
    """OLLAMA_ORIGINS 값: 로컬 데몬 origin(번들 UI가 브라우저에서 localhost Ollama를 직접 프로브) +
    선택적 사이트 origin(env `JEFF_SITE_ORIGIN`, 쉼표 구분 복수 허용 — Render 도메인은 레포에 고정돼
    있지 않으므로 빌드/실행 시점에 주입한다). 이미 사용자가 OLLAMA_ORIGINS를 직접 세팅했다면 그 값을
    **앞에** 보존한다(사용자 명시 설정 > 우리 기본값)."""
    origins: List[str] = []
    user_set = os.environ.get("OLLAMA_ORIGINS", "").strip()
    if user_set:
        origins.extend(s.strip() for s in user_set.split(",") if s.strip())
    origins.extend([f"http://localhost:{daemon_port}", f"http://127.0.0.1:{daemon_port}"])
    site = os.environ.get("JEFF_SITE_ORIGIN", "").strip()
    if site:
        origins.extend(s.strip() for s in site.split(",") if s.strip())
    seen, out = set(), []
    for o in origins:                       # 순서 보존 dedup
        if o not in seen:
            seen.add(o)
            out.append(o)
    return ",".join(out)


# ── 프로세스 기동 ────────────────────────────────────────────────────────────────────────────────────


def start_ollama(bin_path: Path, origins: str) -> Tuple[subprocess.Popen, str]:
    """무수정 공식 바이너리를 `serve`로 기동 — 융합은 이 env 두 개가 전부다(포크 금지의 실체)."""
    env = dict(os.environ)
    env.setdefault("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)   # 사용자가 이미 세팅했으면 존중
    env["OLLAMA_ORIGINS"] = origins
    proc = subprocess.Popen([str(bin_path), "serve"], env=env)
    return proc, env["OLLAMA_HOST"]


def start_daemon(port: int) -> subprocess.Popen:
    """기존 server.py 스택을 자식 프로세스로 기동. 프로즌 모드에선 같은 exe를 `--daemon`으로 재호출
    (PyInstaller에선 sys.executable이 번들 exe 자신), 개발 모드에선 이 파일을 `--daemon`으로 실행."""
    env = dict(os.environ)
    env.setdefault("HARAN_HOST", "127.0.0.1")            # 번들 데몬은 로컬 바인드가 기본(원격 노출 아님)
    env["HARAN_PORT"] = str(port)
    env.setdefault("HARAN_PROVIDER", "ollama_local")     # provider.py:105가 이미 읽는 env — 코드 무변경
    env["JEFF_BUNDLE"] = "1"                             # 표시용 마커 — 검증 경로는 이 env를 읽지 않는다(parity 회귀가 잠금)
    if getattr(sys, "frozen", False):
        cmd = [sys.executable, "--daemon"]
    else:
        cmd = [sys.executable, str(Path(__file__).resolve()), "--daemon"]
    return subprocess.Popen(cmd, env=env)


def run_daemon() -> None:
    """`--daemon` 모드: 기존 서버 앱을 이 프로세스에서 그대로 실행(server.py의 __main__ 경로와 동일한
    계약 — HARAN_HOST/HARAN_PORT). 개발 모드에선 레포 루트를 sys.path에 넣어 `import server`가 되게 한다."""
    root = bundle_root()
    for cand in (root, root.parent):        # 프로즌: exe 옆 / 개발: local_bundle/의 부모(레포 루트)
        if (cand / "server.py").exists() and str(cand) not in sys.path:
            sys.path.insert(0, str(cand))
    import server as SV                     # noqa: PLC0415 — 의도된 지연 임포트(프로즌/개발 공용)
    if SV.app is None:
        raise SystemExit("FastAPI not installed — the bundle build must include it (requirements.txt).")
    import uvicorn                          # noqa: PLC0415
    port = int(os.environ.get("HARAN_PORT") or str(DEFAULT_DAEMON_PORT))
    uvicorn.run(SV.app, host=os.environ.get("HARAN_HOST", "127.0.0.1"), port=port, log_level="warning")


# ── 대기/정리 ────────────────────────────────────────────────────────────────────────────────────────


def wait_http_ok(url: str, timeout_s: float, proc: Optional[subprocess.Popen] = None) -> bool:
    """URL이 2xx~4xx로 응답할 때까지 폴링(5xx/연결거부는 미기동으로 간주). proc이 먼저 죽으면 즉시 False —
    죽은 자식을 계속 기다리는 것은 무인 모드에서 최악의 침묵이다."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if proc is not None and proc.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url, timeout=2) as r:   # noqa: S310 — localhost 전용
                if 200 <= r.status < 500:
                    return True
        except Exception:                   # noqa: BLE001 — 기동 중 연결거부는 정상 경로
            pass
        time.sleep(0.25)
    return False


def _terminate_all(procs: List[subprocess.Popen]) -> None:
    for p in procs:
        if p.poll() is None:
            p.terminate()
    deadline = time.monotonic() + 6
    for p in procs:
        remain = max(0.1, deadline - time.monotonic())
        try:
            p.wait(timeout=remain)
        except subprocess.TimeoutExpired:
            p.kill()


# ── 오케스트레이션 ───────────────────────────────────────────────────────────────────────────────────


def orchestrate(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="MR.JEFFREY local bundle launcher (Ollama 동봉 + JEFF 데몬)")
    ap.add_argument("--port", type=int, default=int(os.environ.get("HARAN_PORT") or str(DEFAULT_DAEMON_PORT)))
    ap.add_argument("--no-ollama", action="store_true", help="데몬만 기동(로컬 모델 없이 API-provider 경로만)")
    ap.add_argument("--selfcheck", action="store_true",
                    help="기동→확인→정리 후 종료코드로 보고(CI/스모크용): 데몬 필수, ollama는 바이너리가 있을 때만 필수")
    ap.add_argument("--ollama-wait", type=float, default=30.0)
    ap.add_argument("--daemon-wait", type=float, default=90.0)
    args = ap.parse_args(argv)

    procs: List[subprocess.Popen] = []
    cleaned = {"done": False}

    def _cleanup(*_sig) -> None:
        if not cleaned["done"]:
            cleaned["done"] = True
            _terminate_all(procs)

    atexit.register(_cleanup)
    signal.signal(signal.SIGINT, lambda *a: (_cleanup(), sys.exit(130)))
    signal.signal(signal.SIGTERM, lambda *a: (_cleanup(), sys.exit(143)))

    origins = compute_origins(args.port)
    ollama_ok: Optional[bool] = None        # None = 기동 안 함(바이너리 없음/--no-ollama) — 실패와 구분
    obin = None if args.no_ollama else find_ollama_bin()
    if obin is not None:
        oproc, ohost = start_ollama(obin, origins)
        procs.append(oproc)
        base = ohost if ohost.startswith("http") else f"http://{ohost}"
        ollama_ok = wait_http_ok(f"{base}/api/version", args.ollama_wait, oproc)
        print(f"[번들] Ollama: bin={obin} host={ohost} origins={origins} → "
              f"{'OK' if ollama_ok else 'FAILED(기동 실패 — 로그 확인)'}  pid={oproc.pid}", flush=True)
    elif not args.no_ollama:
        print("[번들] Ollama 바이너리를 찾지 못함(JEFF_OLLAMA_BIN/동봉경로/PATH) — 로컬 모델 없이 "
              "데몬만 기동합니다(API-provider 경로는 정상 동작).", flush=True)

    dproc = start_daemon(args.port)
    procs.append(dproc)
    daemon_ok = wait_http_ok(f"http://127.0.0.1:{args.port}/", args.daemon_wait, dproc)
    print(f"[번들] JEFF 데몬: http://127.0.0.1:{args.port}/ → {'OK' if daemon_ok else 'FAILED'}  "
          f"pid={dproc.pid}  (provider 기본값: {os.environ.get('HARAN_PROVIDER', 'ollama_local')})", flush=True)

    if args.selfcheck:
        _cleanup()
        ok = daemon_ok and (ollama_ok is not False)   # 기동 시도한 ollama가 실패했으면 selfcheck도 실패
        print(f"[번들] selfcheck: {'PASS' if ok else 'FAIL'} (daemon={daemon_ok}, ollama={ollama_ok})", flush=True)
        return 0 if ok else 1

    if not daemon_ok:
        _cleanup()
        return 1
    print(f"[번들] 준비 완료 — 브라우저에서 http://127.0.0.1:{args.port}/ 를 여세요. (종료: Ctrl+C)", flush=True)
    try:
        rc = dproc.wait()
    finally:
        _cleanup()
    return rc or 0


def main() -> int:
    if "--daemon" in sys.argv[1:]:
        run_daemon()
        return 0
    return orchestrate(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
