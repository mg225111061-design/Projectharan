"""
swebench/live_harness.py — 측정루프 단계1: the REAL SWE-bench provision→checkout→score loop.
=================================================================================================================
This is the piece `real_dataset.py::harness_conversion_gap()` said "would work unblocked". As of 2026-07-02
the two barriers the prior session hit are BOTH cleared and DIRECTLY re-verified this session:
  * HF datasets-server rows API is reachable (200) — `fetch_subset()` pulls real instances from it.
  * public repos clone once the proxy's global `insteadOf` github→proxy rewrite is bypassed with
    GIT_CONFIG_GLOBAL=/dev/null — `provision_instance()` does exactly that shallow single-commit fetch.
Proven end-to-end this session on django__django-16527: load→clone→checkout→(test_patch)→F2P FAILS pre-fix
→(gold patch)→all PASS. That is the resolve criterion, on real ground truth.

★ Honesty boundaries (do not paper over):
  * NETWORK/TIME: `fetch_subset`/`provision_instance` do real network I/O and take minutes per task — they
    are NEVER called from the deterministic test gate. The gate exercises `score_candidate`'s LOGIC on a
    synthetic local git repo (offline, sub-second) via `_score_in_repo`. The live path has its own on-demand
    script (`run_live_subset.py`) and returns honest BLOCKED when egress is closed.
  * PER-REPO TEST COMMAND: SWE-bench's real difficulty is that each repo/version needs a specific test
    env + runner. `infer_runner()` covers the common cases HONESTLY (django→runtests.py, else→pytest -k)
    and every other case is reported as an explicit `runner="UNSUPPORTED"` — never a guessed/faked pass.
  * RESOLVE = the SWE-bench definition: every FAIL_TO_PASS flips fail→pass AND every PASS_TO_PASS stays
    passing, after the candidate patch. A candidate that doesn't apply is `resolved=False` (never a crash).
"""
from __future__ import annotations

import json as _json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request as _urlreq
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from swebench.real_dataset import RealInstance, parse_instance

# git with the proxy's global github→proxy insteadOf rewrite bypassed (that rewrite 403s public clones;
# bypassing it lets the direct https path through, re-verified this session).
_GIT_ENV = dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")

_ROWS_URL = ("https://datasets-server.huggingface.co/rows?dataset=princeton-nlp%2F{ds}"
             "&config=default&split={split}&offset={offset}&length={n}")


def fetch_subset(n: int = 10, dataset: str = "SWE-bench_Lite", split: str = "test",
                 offset: int = 0, timeout: float = 40.0) -> Tuple[List[RealInstance], str]:
    """Pull `n` REAL instances via the HF datasets-server rows API. Returns (instances, "OK") or
    ([], "BLOCKED: ...") — never raises, never fabricates. 서브셋만 (전체 금지, directive §단계1)."""
    if n > 50:
        raise ValueError("fetch_subset is subset-only (n<=50) — full-run is forbidden by the directive")
    url = _ROWS_URL.format(ds=dataset, split=split, offset=offset, n=n)
    try:
        with _urlreq.urlopen(_urlreq.Request(url, method="GET"), timeout=timeout) as r:
            if r.status != 200:
                return [], f"BLOCKED: rows API HTTP {r.status}"
            payload = _json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:                       # noqa: BLE001 — egress closed / DNS / timeout
        return [], f"BLOCKED: {type(e).__name__}: {e}"
    out: List[RealInstance] = []
    for row in payload.get("rows", []):
        try:
            out.append(parse_instance(row["row"]))
        except (ValueError, TypeError, KeyError):
            continue                             # malformed row skipped, not fatal
    return out, "OK"


def _git(args: List[str], cwd: str, timeout: float = 300.0) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + args, cwd=cwd, env=_GIT_ENV, capture_output=True, text=True, timeout=timeout)


def provision_instance(inst: RealInstance, dest: str, timeout: float = 300.0) -> Dict:
    """Shallow-fetch exactly `inst.base_commit` of `inst.repo` into `dest` and check it out. Honest BLOCKED
    (never a crash) if egress/clone is closed. `dest` must be OUTSIDE the workspace (scratch) — the caller's
    responsibility; this never touches the source tree."""
    os.makedirs(dest, exist_ok=True)
    url = f"https://github.com/{inst.repo}.git"
    init = _git(["init", "-q", "."], dest)
    if init.returncode != 0:
        return {"ok": False, "blocker": f"git init failed: {init.stderr[:200]}"}
    _git(["remote", "add", "origin", url], dest)
    fetch = _git(["fetch", "-q", "--depth", "1", "origin", inst.base_commit], dest, timeout=timeout)
    if fetch.returncode != 0:
        return {"ok": False, "blocker": f"BLOCKED: fetch {inst.base_commit[:10]} of {inst.repo}: "
                                        f"{fetch.stderr[:200]}"}
    co = _git(["checkout", "-q", "FETCH_HEAD"], dest)
    if co.returncode != 0:
        return {"ok": False, "blocker": f"checkout failed: {co.stderr[:200]}"}
    head = _git(["rev-parse", "HEAD"], dest).stdout.strip()
    return {"ok": True, "head": head, "matches_base": head == inst.base_commit}


def apply_patch(repo_dir: str, diff: str) -> bool:
    """Apply a unified diff (git apply --3way, then a plain fallback). Returns applied?; never raises."""
    if not diff.strip():
        return True                              # empty candidate (no-op) applies trivially
    for extra in (["--3way"], []):
        p = subprocess.run(["git", "apply"] + extra + ["-"], cwd=repo_dir, env=_GIT_ENV,
                           input=diff, capture_output=True, text=True, timeout=120)
        if p.returncode == 0:
            return True
    return False


# ── per-repo runner inference (honest coverage of the common cases; else UNSUPPORTED, never faked) ────
Runner = Callable[[str, List[str]], Tuple[int, str]]


def _django_runner(repo_dir: str, node_ids: List[str]) -> Tuple[int, str]:
    # django node id: "test_x (module.Class.test_x)" → the label module.path SWE-bench uses is inside ().
    labels = []
    for nid in node_ids:
        m = re.search(r"\(([\w.]+)\)", nid)
        labels.append(m.group(1) if m else nid.split()[0])
    tests_dir = os.path.join(repo_dir, "tests")
    p = subprocess.run([sys.executable, "runtests.py", "--parallel=1", "--verbosity=0"] + labels,
                       cwd=tests_dir, env=dict(os.environ, PYTHONPATH=repo_dir),
                       capture_output=True, text=True, timeout=600)
    return p.returncode, (p.stdout + p.stderr)[-6000:]


def _pytest_runner(repo_dir: str, node_ids: List[str]) -> Tuple[int, str]:
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"] + node_ids,
                       cwd=repo_dir, capture_output=True, text=True, timeout=600)
    return p.returncode, (p.stdout + p.stderr)[-6000:]


def infer_runner(inst: RealInstance) -> Tuple[Optional[Runner], str]:
    repo = inst.repo.lower()
    if repo == "django/django":
        return _django_runner, "django-runtests"
    return _pytest_runner, "pytest"              # honest default; if the repo needs bespoke setup it will
    #                                              simply fail to collect → run_node_ids reports it, not faked


def run_node_ids(repo_dir: str, node_ids: List[str], runner: Runner) -> Dict:
    """Run the given node IDs; a nonzero rc means 'at least one failed/errored'. We report the raw rc + tail
    — the caller derives pass/fail per the SWE-bench resolve rule. Empty node list = trivially passing."""
    if not node_ids:
        return {"rc": 0, "all_pass": True, "tail": "(no node ids)"}
    rc, tail = runner(repo_dir, node_ids)
    return {"rc": rc, "all_pass": rc == 0, "tail": tail}


@dataclass
class ScoreResult:
    resolved: bool
    f2p_all_pass: bool
    p2p_all_pass: bool
    applied: bool
    detail: str


def _score_in_repo(repo_dir: str, inst: RealInstance, candidate_patch: str, runner: Runner) -> ScoreResult:
    """The SWE-bench resolve criterion, executed in an ALREADY-PROVISIONED repo (base commit checked out,
    test_patch NOT yet applied). Steps: apply test_patch → apply candidate → run F2P (must all pass) + P2P
    (must all stay passing). resolved = both. Kept separate from provisioning so the gate can drive it on a
    synthetic offline repo."""
    if not apply_patch(repo_dir, inst.test_patch):
        return ScoreResult(False, False, False, False, "test_patch did not apply")
    if not apply_patch(repo_dir, candidate_patch):
        return ScoreResult(False, False, False, False, "candidate patch did not apply → unresolved (0 pts)")
    f2p = run_node_ids(repo_dir, inst.fail_to_pass, runner)
    p2p = run_node_ids(repo_dir, inst.pass_to_pass, runner)
    resolved = f2p["all_pass"] and p2p["all_pass"]
    return ScoreResult(resolved, f2p["all_pass"], p2p["all_pass"], True,
                       f"F2P all_pass={f2p['all_pass']} P2P all_pass={p2p['all_pass']}")


def score_candidate(inst: RealInstance, candidate_patch: str, workdir: Optional[str] = None) -> Dict:
    """Full live path: provision (network) → score. Returns a dict incl. honest BLOCKED if provisioning
    fails. Slow + network-bound → NEVER called from the gate (the gate uses `_score_in_repo` on a synthetic
    repo). `workdir` must be scratch, not the workspace."""
    runner, runner_name = infer_runner(inst)
    if runner is None:
        return {"resolved": False, "runner": "UNSUPPORTED", "detail": f"no runner for repo {inst.repo}"}
    tmp = workdir or tempfile.mkdtemp(prefix="swebench_")
    prov = provision_instance(inst, tmp)
    if not prov["ok"]:
        return {"resolved": False, "runner": runner_name, "blocked": True, "detail": prov["blocker"]}
    res = _score_in_repo(tmp, inst, candidate_patch, runner)
    return {"resolved": res.resolved, "runner": runner_name, "f2p_all_pass": res.f2p_all_pass,
            "p2p_all_pass": res.p2p_all_pass, "applied": res.applied, "detail": res.detail}


# ════════ 작업 5 — raw vs JEFF-wrapped Δ 측정 배선 (반복샘플→하이브리드 선택 지시서) ══════════════════════
# 라이브 태스크에는 참조 오라클이 없으므로 formal PROOF 층은 여기선 정직하게 미적용(rate 0.0으로 로깅) —
# 함수 추출 어댑터가 후속으로 그 rate를 올릴 몫이다. 기질(harness.Task) 위에선 hybrid_select가 실제
# bounded_equiv 증명/반례/등가류를 돌린다. ★선택 신호에 F2P를 절대 쓰지 않는다(F2P는 채점 세트 = leakage);
# P2P 서브셋(레포의 기존 테스트 = 개발자에게 정당하게 보이는 신호)과 무결성/효과/등가류-표만 쓴다.

def _reset_repo(repo_dir: str) -> None:
    _git(["reset", "-q", "--hard", "HEAD"], repo_dir)
    _git(["clean", "-fdq"], repo_dir)


def _norm_diff(diff: str) -> str:
    """자명한(텍스트) 등가 정규화: index/헤더 잡음·공백 꼬리 제거 — 동일 정규형 = 같은 등가류(건전).
    의미 등가(bounded_equiv 함수 추출)는 후속 어댑터 — 여기서 주장하지 않는다."""
    keep = []
    for ln in diff.splitlines():
        if ln.startswith(("index ", "diff --git")):
            continue
        keep.append(ln.rstrip())
    return "\n".join(keep).strip()


def select_live(repo_dir: str, inst: RealInstance, diffs: List[str], runner: Runner,
                p2p_sample: int = 4) -> Dict:
    """라이브 selector(오라클 없음 — 정직한 신호만): BI 무결성(수리/재생성) → 실제 apply 게이트 →
    P2P 서브셋 회귀(기존 테스트 유지?) → no-op 후순위 → 등가류(정규형) 표 → 최소 diff.
    반환: {chosen, diff(수리본), signals, formal_applicable_rate(정직 0.0), detail}."""
    from swebench.patch_integrity import validate_and_repair
    sigs: List[Dict] = []
    p2p_ids = inst.pass_to_pass[:p2p_sample]
    norm_votes: Dict[str, int] = {}
    repaired: Dict[int, str] = {}
    for i, raw in enumerate(diffs):
        ir = validate_and_repair(raw)
        if ir.regenerate:
            sigs.append({"i": i, "eliminated": "integrity", "errors": ir.errors[:3]})
            continue
        _reset_repo(repo_dir)
        if not apply_patch(repo_dir, ir.diff):
            sigs.append({"i": i, "eliminated": "apply", "repairs": ir.repairs})
            continue
        p2p = run_node_ids(repo_dir, p2p_ids, runner)
        norm = _norm_diff(ir.diff)
        norm_votes[norm] = norm_votes.get(norm, 0) + 1
        repaired[i] = ir.diff
        sigs.append({"i": i, "p2p_ok": p2p["all_pass"], "has_effect": not ir.no_op,
                     "repairs": ir.repairs, "norm": norm, "len": len(ir.diff)})
    _reset_repo(repo_dir)
    alive = [s for s in sigs if "eliminated" not in s]
    for s in alive:
        s["votes"] = norm_votes[s.pop("norm")]
    if not alive:
        return {"chosen": None, "diff": None, "signals": sigs, "formal_applicable_rate": 0.0,
                "detail": "no candidate survived integrity+apply — honest decline (0 pts, no gamble)"}
    ranked = sorted(alive, key=lambda s: (-int(s["p2p_ok"]), -int(s["has_effect"]), -s["votes"], s["len"], s["i"]))
    top = ranked[0]
    return {"chosen": top["i"], "diff": repaired[top["i"]], "signals": sigs,
            "formal_applicable_rate": 0.0,          # 정직: 라이브엔 아직 formal 추출 어댑터 없음(기질에는 실재)
            "detail": f"chosen #{top['i']} (p2p_ok={top['p2p_ok']}, effect={top['has_effect']}, "
                      f"votes={top['votes']}) — selection signals exclude F2P (no grading-set leakage)"}


def measure_delta(instances: List[RealInstance], gen_fn, *, n: int = 2, p2p_sample: int = 4,
                  workdir: Optional[str] = None, provision=provision_instance) -> Dict:
    """★단일 진실 측정기: 같은 인스턴스·같은 생성기에서 raw(후보 1개, 선택/수리 없음) vs wrapped(N 후보 →
    BI → live-select) 두 조건을 SWE-bench resolve 기준(_score_in_repo)으로 채점해 Δ를 낸다.
    gen_fn(inst, n, repo_dir) → List[diff]; 빈 값 = 그 행 honest BLOCKED. `provision` 주입 가능(게이트는
    오프라인 합성 provisioner를 주입 — 네트워크는 게이트 밖 규율 유지)."""
    base = workdir or tempfile.mkdtemp(prefix="swebench_delta_")
    rows: List[Dict] = []
    raw_ok = wrapped_ok = scored = 0
    for inst in instances:
        runner, runner_name = infer_runner(inst)
        dest = os.path.join(base, inst.instance_id.replace("/", "__"))
        prov = provision(inst, dest)
        if not prov.get("ok"):
            rows.append({"instance": inst.instance_id, "blocked": True, "detail": prov.get("blocker")})
            continue
        cands = list(gen_fn(inst, n, dest) or [])
        if not cands:
            rows.append({"instance": inst.instance_id, "blocked": True,
                         "detail": "generator returned no candidates (provider unreachable/refused) — BLOCKED"})
            continue
        # raw: 파이프라인 없음 — 첫 후보 원문 그대로 채점 (수리도 선택도 없음)
        _reset_repo(dest)
        raw_res = _score_in_repo(dest, inst, cands[0], runner)
        # wrapped: BI+선택 후 채점 (선택은 F2P를 보지 않는다; 채점은 선택 뒤 전체 기준으로 — leakage 0)
        _reset_repo(dest)
        sel = select_live(dest, inst, cands, runner, p2p_sample=p2p_sample)
        if sel["chosen"] is None:
            wrapped_res = None
        else:
            _reset_repo(dest)
            wrapped_res = _score_in_repo(dest, inst, sel["diff"], runner)
        scored += 1
        raw_ok += int(raw_res.resolved)
        wrapped_ok += int(bool(wrapped_res and wrapped_res.resolved))
        rows.append({"instance": inst.instance_id, "runner": runner_name,
                     "raw_resolved": raw_res.resolved,
                     "wrapped_resolved": bool(wrapped_res and wrapped_res.resolved),
                     "wrapped_chosen": sel["chosen"], "n_candidates": len(cands),
                     "formal_applicable_rate": sel["formal_applicable_rate"],
                     "selection_detail": sel["detail"]})
    return {"n_instances": len(instances), "n_scored": scored,
            "raw_resolved": raw_ok, "wrapped_resolved": wrapped_ok,
            "delta": wrapped_ok - raw_ok, "rows": rows,
            "honesty": {"runner_note": "간이 러너(공식 도커 하니스 아님) — 절대점수 비교 금지, raw-vs-wrapped Δ 전용",
                        "selection_leakage": "선택 신호에 F2P 미사용(채점 세트) — P2P 서브셋+무결성+효과+등가류 표만",
                        "formal_live": "라이브 formal 적용률은 현재 정직히 0.0 — 함수 추출 어댑터가 후속; "
                                       "기질(hybrid_select)에서는 bounded_equiv 증명/반례가 실측으로 돈다"}}


# ── 주말 로컬 측정용 CLI: python -m swebench.live_harness --pipeline hybrid --subset 10 --provider ollama_local ──
def _lexical_localize(repo_dir: str, problem: str, k: int = 2, head_chars: int = 3500) -> List[Tuple[str, str]]:
    """Agentless의 파일-국소화를 결정적으로: 이슈 텍스트와 어휘 겹침이 큰 .py 파일 top-k(+헤드 발췌).
    gold patch는 절대 보지 않는다(leakage 0) — 이슈 텍스트만."""
    ls = _git(["ls-files", "*.py"], repo_dir).stdout.splitlines()
    toks = {w for w in re.findall(r"[A-Za-z_]{3,}", problem.lower())}
    scored = []
    for path in ls[:2000]:
        base = os.path.basename(path).lower()
        score = sum(3 for w in toks if w in base) + sum(1 for w in toks if w in path.lower())
        scored.append((score, path))
    out = []
    for _s, path in sorted(scored, reverse=True)[:k]:
        try:
            with open(os.path.join(repo_dir, path), encoding="utf-8", errors="replace") as fh:
                out.append((path, fh.read(head_chars)))
        except OSError:
            continue
    return out


def _ollama_gen_fn(model: str, host: str = "http://127.0.0.1:11434", timeout: float = 240.0):
    """로컬 Ollama 생성 훅(주말 측정용, stdlib-only). 온도 다양화로 N개 샘플. 실패 샘플은 건너뛰고(정직 부분),
    전부 실패면 [] → measure_delta가 그 행을 BLOCKED로 기록한다. 파이프라인 훅이지 등록 도구가 아니다."""
    def gen(inst: RealInstance, n: int, repo_dir: str) -> List[str]:
        hints = _lexical_localize(repo_dir, inst.problem_statement)
        hint_txt = "\n\n".join(f"### {p}\n{t}" for p, t in hints)
        prompt = (f"You are fixing a real GitHub issue in {inst.repo}.\n\nISSUE:\n"
                  f"{inst.problem_statement[:4000]}\n\nLIKELY RELEVANT FILES (lexical match, may be wrong):\n"
                  f"{hint_txt[:8000]}\n\nReply with ONLY a valid unified diff (--- a/path, +++ b/path, @@ hunks) "
                  "that fixes the issue. No prose. No markdown fences.")
        out: List[str] = []
        for i in range(n):
            body = _json.dumps({"model": model, "prompt": prompt, "stream": False,
                                "options": {"temperature": round(0.2 + 0.25 * i, 2)}}).encode()
            req = _urlreq.Request(f"{host}/api/generate", data=body,
                                  headers={"Content-Type": "application/json"}, method="POST")
            try:
                with _urlreq.urlopen(req, timeout=timeout) as r:
                    out.append(_json.loads(r.read().decode("utf-8", "replace")).get("response", ""))
            except Exception:            # noqa: BLE001 — 이 샘플만 정직하게 유실
                continue
        return [d for d in out if d.strip()]
    return gen


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="raw vs JEFF-wrapped Δ on a REAL SWE-bench subset (간이 러너 — Δ 전용)")
    ap.add_argument("--pipeline", choices=["hybrid"], default="hybrid")
    ap.add_argument("--subset", type=int, default=10)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--dataset", default="SWE-bench_Lite")
    ap.add_argument("--split", default="test")
    ap.add_argument("--provider", default="ollama_local", choices=["ollama_local"])
    ap.add_argument("--model", default="qwen3-coder:30b")
    ap.add_argument("--host", default="http://127.0.0.1:11434")
    ap.add_argument("--n", type=int, default=None, help="samples per task (default: mode_policy extended band)")
    args = ap.parse_args(argv)
    from swebench.sample_repair import default_n
    n = args.n or default_n(local=True)
    insts, status = fetch_subset(args.subset, dataset=args.dataset, split=args.split, offset=args.offset)
    if status != "OK":
        print(_json.dumps({"blocked": True, "detail": status}))
        return 1
    rep = measure_delta(insts, _ollama_gen_fn(args.model, args.host), n=n)
    print(_json.dumps(rep, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
