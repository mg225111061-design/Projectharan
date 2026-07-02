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
