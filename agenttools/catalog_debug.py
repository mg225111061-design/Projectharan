"""
agenttools/catalog_debug.py — 카탈로그-v2 K군: 디버깅/진단 15종 (우선순위 2, intent debug).
================================================================================================
Raw payloads; the §1 envelope is built by `executor.execute_enveloped()`. Failure semantics:
ValueError→INVALID_INPUT · FileNotFoundError→NOT_FOUND · envelope.BlockedError→BLOCKED (typed, e.g.
"the test itself is flaky") · envelope.UndecidableError→UNDECIDABLE. §1.4 labels at registration:
K1/K12/K15 heuristic · K10/K13 flag_only · K3/K14 nonexact.

★Tier-A overrides (recorded here + SESSION_LOG + RECONCILE, same precedent as A/D/P groups):
the design doc marks K3 ACCEL ("신규 ddmin"), K8 FOLD ("ast CFG 신규"), K15 ACCEL ("bisect+blame
조합") — none delegates to a verified fold/accel ENGINE; ddmin/CFG/rank are new plain computation,
so all three register PLAIN (RF-5: FOLD/ACCEL require a real `delegate`).

★EXEC boundary (Tier-A, §BE): every "test_command" input is restricted to the SAME shape
run_python_file already enforces — a workspace-internal .py path + list args, subprocess with
timeout + capped output, NEVER an arbitrary shell string. Tools that must move the git worktree
(K4 bisect) restore the original ref in `finally`.
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional

from agenttools.catalog_plain import _run_git, _safe_path, _schema, _workspace_root
from agenttools.envelope import BlockedError
from agenttools.registry import PLAIN, Tool, register

_PROBE_MARKER = "# JEFF_PROBE_MARKER"


def _run_py(path: str, args: Optional[List[str]] = None, timeout_s: float = 20.0) -> Dict:
    """The one bounded runner every K-group EXEC tool uses: workspace .py + argv list, no shell."""
    p = _safe_path(path)
    if not p.endswith(".py"):
        raise ValueError("test_command must be a workspace .py file (no arbitrary shell — §BE boundary)")
    if not os.path.isfile(p):
        raise FileNotFoundError(f"no such file: {path!r}")
    argv = [sys.executable, p] + [str(a) for a in (args or [])]
    r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout_s, cwd=_workspace_root())
    return {"returncode": r.returncode, "stdout": r.stdout[-4000:], "stderr": r.stderr[-4000:]}


# ── K1 error_explain (heuristic) ─────────────────────────────────────────────────────────────────────
_ERROR_RULES = {
    "KeyError": [("looked up a key that is absent from the dict", 0.6, "print the dict's keys just before"),
                 ("stale cache/state carrying an old key", 0.2, "clear the cache and retry")],
    "IndexError": [("index computed past the end (off-by-one)", 0.6, "print len() and the index"),
                   ("empty sequence where at least one element was assumed", 0.3, "guard the empty case")],
    "TypeError": [("None flowed into an operation (a call returned None implicitly)", 0.5,
                   "trace the value back to its producer"),
                  ("wrong arity/argument shape at a call site", 0.3, "inspect the callee signature")],
    "AttributeError": [("object is None or a different type than assumed", 0.6, "print type(obj) at the site")],
    "ZeroDivisionError": [("denominator reaches 0 on an edge input", 0.7, "guard or prove the nonzero range")],
    "FileNotFoundError": [("relative path resolved from an unexpected cwd", 0.5, "print os.getcwd() + the path")],
    "RecursionError": [("missing/never-reached base case", 0.6, "log the argument at each recursion")],
    "UnicodeDecodeError": [("bytes read with the wrong encoding assumption", 0.6, "open with errors='replace' to inspect")],
}


def error_explain(exception_type: str, message: str = "", traceback: str = "") -> Dict:
    """Hypotheses with stated confidence — a HEURISTIC direction-finder, never a verdict."""
    rules = _ERROR_RULES.get(exception_type.strip())
    if not rules:
        return {"hypotheses": [{"cause": f"no rule for {exception_type!r} — inspect the traceback frames",
                                "confidence": 0.1, "check": "use stack_deep_parse on the traceback"}]}
    hyp = [{"cause": c, "confidence": conf, "check": chk} for c, conf, chk in rules]
    if "not" in message.lower() and exception_type == "AttributeError":
        hyp.insert(0, {"cause": "value is None where an object was expected", "confidence": 0.7,
                       "check": "find where the None was produced (var_flow_trace)"})
    return {"hypotheses": hyp}


# ── K2 stack_deep_parse ──────────────────────────────────────────────────────────────────────────────
_FRAME_RE = re.compile(r'File "(?P<file>[^"]+)", line (?P<line>\d+), in (?P<func>\S+)')


def stack_deep_parse(traceback_text: str) -> Dict:
    frames = []
    lines = traceback_text.splitlines()
    for i, ln in enumerate(lines):
        m = _FRAME_RE.search(ln)
        if m:
            code = lines[i + 1].strip() if i + 1 < len(lines) and not _FRAME_RE.search(lines[i + 1]) else ""
            frames.append({"file": m.group("file"), "line": int(m.group("line")),
                           "func": m.group("func"), "locals_hint": code})
    if not frames:
        raise ValueError("no traceback frames found in the given text")
    return {"frames": frames, "innermost": frames[-1]}


# ── K3 delta_debug_input (nonexact — ddmin, bounded) ─────────────────────────────────────────────────
def delta_debug_input(failing_input: str, test_path: str, max_runs: int = 48) -> Dict:
    """ddmin over the input string: the test .py gets the CANDIDATE via argv[1]; 'failing' = rc != 0.
    Bounded runs; if the failure is nondeterministic the result is best-effort (nonexact label)."""
    def fails(s: str) -> bool:
        return _run_py(test_path, [s], timeout_s=15.0)["returncode"] != 0

    runs = [0]
    def fails_counted(s: str) -> bool:
        runs[0] += 1
        if runs[0] > max_runs:
            raise TimeoutError(f"ddmin exceeded max_runs={max_runs}")
        return fails(s)

    if not fails_counted(failing_input):
        raise ValueError("the given input does not fail the test — nothing to minimize")
    cur, n = failing_input, 2
    while len(cur) >= 2:
        chunk = max(1, len(cur) // n)
        reduced = False
        for i in range(0, len(cur), chunk):
            cand = cur[:i] + cur[i + chunk:]
            if cand and fails_counted(cand):
                cur, n, reduced = cand, max(2, n - 1), True
                break
        if not reduced:
            if n >= len(cur):
                break
            n = min(len(cur), n * 2)
    return {"minimal_input": cur, "iterations": runs[0], "original_len": len(failing_input),
            "minimal_len": len(cur)}


# ── K4 bisect_commits (EXEC — worktree moved, restored in finally) ───────────────────────────────────
def bisect_commits(good_ref: str, bad_ref: str, test_path: str, max_steps: int = 12) -> Dict:
    for ref in (good_ref, bad_ref):
        if ref.startswith("-"):
            raise ValueError(f"ref may not start with '-': {ref!r}")
    lst = _run_git(["rev-list", "--first-parent", f"{good_ref}..{bad_ref}"])
    if not lst["ok"]:
        raise ValueError(f"rev-list failed: {lst['stderr'][:200]}")
    commits = lst["stdout"].split()            # newest → oldest
    if not commits:
        raise ValueError("no commits between the refs")
    # flakiness gate: the verdict substrate must be deterministic at bad_ref
    orig = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])["stdout"].strip() or "HEAD"
    def test_fails_at(ref: str) -> bool:
        co = _run_git(["checkout", "--quiet", ref])
        if not co["ok"]:
            raise ValueError(f"checkout {ref} failed: {co['stderr'][:200]}")
        return _run_py(test_path, timeout_s=30.0)["returncode"] != 0
    steps = 0
    try:
        first = test_fails_at(bad_ref); second = test_fails_at(bad_ref)
        if first != second:
            raise BlockedError("the test itself is flaky at bad_ref — bisect verdicts would be noise")
        if not first:
            raise ValueError("test does not fail at bad_ref — nothing to bisect")
        lo, hi = 0, len(commits) - 1           # commits[hi] oldest(≈good side), commits[0] newest(bad)
        culprit = commits[0]
        while lo <= hi and steps < max_steps:
            mid = (lo + hi) // 2
            steps += 1
            if test_fails_at(commits[mid]):
                culprit = commits[mid]; lo = mid + 1     # failure extends older — culprit is at/after mid
            else:
                hi = mid - 1
        return {"culprit_commit": culprit, "steps": steps, "candidates_scanned": len(commits)}
    finally:
        _run_git(["checkout", "--quiet", orig])


# ── K5 bisect_hunks ──────────────────────────────────────────────────────────────────────────────────
def bisect_hunks(patch_text: str, test_path: str) -> Dict:
    """Split a unified diff into per-hunk patches, apply each ALONE (3-way, then revert), and report
    which hunks flip the test to failing. Worktree restored after every probe."""
    hunks, cur_head, cur = [], [], []
    for ln in patch_text.splitlines(keepends=True):
        if ln.startswith(("--- ", "+++ ")):
            if cur:
                hunks.append((list(cur_head), cur)); cur = []
            if ln.startswith("--- "):
                cur_head = [ln]
            else:
                cur_head.append(ln)
        elif ln.startswith("@@"):
            if cur:
                hunks.append((list(cur_head), cur))
            cur = [ln]
        elif cur:
            cur.append(ln)
    if cur:
        hunks.append((list(cur_head), cur))
    if not hunks:
        raise ValueError("no hunks found in patch_text")
    breaking = []
    for idx, (head, body) in enumerate(hunks):
        single = "".join(head + body)
        pr = subprocess.run(["git", "-C", _workspace_root(), "apply", "--3way", "-"],
                            input=single, capture_output=True, text=True, timeout=20)
        if pr.returncode != 0:
            breaking.append({"hunk": idx, "applies": False, "reason": pr.stderr[:200]})
            continue
        try:
            fails = _run_py(test_path, timeout_s=30.0)["returncode"] != 0
            if fails:
                breaking.append({"hunk": idx, "applies": True, "breaks_test": True})
        finally:
            subprocess.run(["git", "-C", _workspace_root(), "apply", "--3way", "--reverse", "-"],
                           input=single, capture_output=True, text=True, timeout=20)
    return {"breaking_hunks": breaking, "hunk_count": len(hunks)}


# ── K6 print_instrument (WRITE — marker-removable) ───────────────────────────────────────────────────
def print_instrument(path: str, lines: Optional[List[int]] = None, vars: Optional[List[str]] = None,
                     remove: bool = False) -> Dict:
    p = _safe_path(path)
    src = open(p, encoding="utf-8").read().splitlines(keepends=True)
    if remove:
        kept = [ln for ln in src if _PROBE_MARKER not in ln]
        open(p, "w", encoding="utf-8").write("".join(kept))
        return {"removed": len(src) - len(kept), "removal_marker": _PROBE_MARKER}
    if not lines:
        raise ValueError("lines required (or remove=True)")
    vs = vars or []
    out, inserted = [], 0
    for i, ln in enumerate(src, 1):
        out.append(ln)
        if i in lines:
            indent = re.match(r"\s*", ln).group(0)
            payload = ", ".join([f"'L{i}'"] + [f"{v}={{{v}!r}}".replace("{", "{").replace("}", "}") for v in vs])
            probe = f"{indent}print(f\"JEFF_PROBE {payload}\")  {_PROBE_MARKER}\n"
            out.append(probe); inserted += 1
    open(p, "w", encoding="utf-8").write("".join(out))
    return {"inserted": inserted, "removal_marker": _PROBE_MARKER,
            "patch": f"inserted {inserted} probe line(s) tagged {_PROBE_MARKER}"}


# ── K7 state_snapshot (EXEC — settrace driver subprocess) ────────────────────────────────────────────
def state_snapshot(path: str, line: int, timeout_s: float = 20.0) -> Dict:
    p = _safe_path(path)
    driver = (
        "import sys, json, runpy\n"
        f"TARGET, LINE = {p!r}, {int(line)}\n"
        "cap = {}\n"
        "def tr(frame, event, arg):\n"
        "    if event == 'line' and frame.f_code.co_filename == TARGET and frame.f_lineno == LINE and not cap:\n"
        "        for k, v in frame.f_locals.items():\n"
        "            try: cap[k] = repr(v)[:200]\n"
        "            except Exception: cap[k] = '<unreprable>'\n"
        "    return tr\n"
        "sys.settrace(tr)\n"
        "try: runpy.run_path(TARGET, run_name='__main__')\n"
        "except SystemExit: pass\n"
        "except Exception as e: cap.setdefault('__uncaught__', repr(e)[:200])\n"
        "sys.settrace(None)\n"
        "print('JEFF_SNAPSHOT ' + json.dumps(cap))\n")
    r = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                       timeout=timeout_s, cwd=_workspace_root())
    for ln in r.stdout.splitlines():
        if ln.startswith("JEFF_SNAPSHOT "):
            snap = json.loads(ln[len("JEFF_SNAPSHOT "):])
            if not snap:
                raise FileNotFoundError(f"line {line} never reached while running {path!r}")
            return {"locals_at_line": snap, "line": line}
    raise FileNotFoundError(f"line {line} never reached while running {path!r} "
                            f"(rc={r.returncode}, stderr={r.stderr[-200:]!r})")


# ── K8 raise_path_trace (PLAIN — static; dynamic raises listed honestly, not decided) ────────────────
def raise_path_trace(path: str, exception_type: str) -> Dict:
    p = _safe_path(path)
    tree = ast.parse(open(p, encoding="utf-8").read())
    static, dynamic = [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise):
            exc = node.exc
            name = ""
            if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
                name = exc.func.id
            elif isinstance(exc, ast.Name):
                name = exc.id
            entry = {"line": node.lineno, "raises": name or "<dynamic>"}
            (static if name else dynamic).append(entry)
    hits = [s for s in static if s["raises"] == exception_type]
    return {"reachable_paths": hits, "all_static_raises": static,
            "dynamic_raises_unresolved": dynamic,      # honest: statically undecidable, listed not guessed
            "note": "static AST walk — dynamic re-raises are LISTED as unresolved, never classified"}


# ── K9 var_flow_trace ────────────────────────────────────────────────────────────────────────────────
def var_flow_trace(path: str, var: str, line: Optional[int] = None) -> Dict:
    p = _safe_path(path)
    tree = ast.parse(open(p, encoding="utf-8").read())
    chain = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == var:
            kind = "def" if isinstance(node.ctx, (ast.Store, ast.Del)) else "use"
            chain.append({"line": node.lineno, "kind": kind})
        elif isinstance(node, ast.arg) and node.arg == var:
            chain.append({"line": node.lineno, "kind": "def(param)"})
    chain.sort(key=lambda e: e["line"])
    if not chain:
        raise FileNotFoundError(f"variable {var!r} not found in {path!r}")
    if line is not None:
        chain = [e for e in chain if e["line"] <= line] or chain
    return {"def_use_chain": chain}


# ── K10 race_pattern_scan (flag_only) ────────────────────────────────────────────────────────────────
def race_pattern_scan(path: str) -> Dict:
    p = _safe_path(path)
    src = open(p, encoding="utf-8").read()
    suspects = []
    has_thread = bool(re.search(r"\bthreading\.|\bThread\(", src))
    for i, ln in enumerate(src.splitlines(), 1):
        if has_thread and re.search(r"\bglobal\s+\w+", ln):
            suspects.append({"line": i, "pattern": "global mutated in a threaded module (check-then-act risk)"})
        if re.search(r"if\s+.*\bin\s+\w+\s*:", ln) and has_thread:
            suspects.append({"line": i, "pattern": "check-then-act on shared container under threading"})
        if re.search(r"\+=\s*1\b", ln) and has_thread:
            suspects.append({"line": i, "pattern": "non-atomic increment under threading"})
    return {"suspects": suspects[:30], "threading_present": has_thread}


# ── K11 resource_leak_scan ───────────────────────────────────────────────────────────────────────────
def resource_leak_scan(path: str) -> Dict:
    p = _safe_path(path)
    src = open(p, encoding="utf-8").read()
    tree = ast.parse(src)
    with_lines = {n.lineno for n in ast.walk(tree) if isinstance(n, (ast.With, ast.AsyncWith))
                  for n in ast.walk(n) if isinstance(n, ast.Call)}
    leaks = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open":
            parent_with = any(abs(node.lineno - wl) <= 0 for wl in with_lines)
            seg = src.splitlines()[node.lineno - 1]
            if "with " not in seg and ".close" not in src[src.find(seg):src.find(seg) + 500]:
                leaks.append({"line": node.lineno, "resource": "open() outside `with` and no nearby .close()"})
    return {"leaks": leaks}


# ── K12 nan_inf_probe (heuristic) ────────────────────────────────────────────────────────────────────
def nan_inf_probe(path: str) -> Dict:
    p = _safe_path(path)
    risk = []
    for i, ln in enumerate(open(p, encoding="utf-8").read().splitlines(), 1):
        if re.search(r"/\s*[a-zA-Z_]", ln) and "if" not in ln and "#" not in ln.split("/")[0]:
            risk.append({"line": i, "risk": "division by a variable (0-denominator path?)"})
        if re.search(r"\b(math\.)?(log|sqrt)\s*\(", ln):
            risk.append({"line": i, "risk": "log/sqrt domain edge (<=0 / <0)"})
    return {"risk_sites": risk[:30]}


# ── K13 off_by_one_scan (flag_only — never patches) ──────────────────────────────────────────────────
def off_by_one_scan(path: str) -> Dict:
    p = _safe_path(path)
    suspects = []
    for i, ln in enumerate(open(p, encoding="utf-8").read().splitlines(), 1):
        if re.search(r"range\(len\(\w+\)\s*-\s*1\)", ln):
            suspects.append({"line": i, "pattern": "range(len(x)-1) — last element intentionally skipped?"})
        if re.search(r"\[\s*\w+\s*\+\s*1\s*\]", ln) and "range" in ln:
            suspects.append({"line": i, "pattern": "x[i+1] inside a full range — boundary overrun?"})
        if re.search(r"<=\s*len\(", ln):
            suspects.append({"line": i, "pattern": "<= len(x) comparison — off-by-one at the boundary?"})
    return {"suspects": suspects[:30]}


# ── K14 heisenbug_rerun (EXEC, nonexact) ─────────────────────────────────────────────────────────────
def heisenbug_rerun(test_path: str, runs: int = 5) -> Dict:
    if not (1 <= runs <= 12):
        raise ValueError("runs must be 1..12 (bounded)")
    p = _safe_path(test_path)
    outcomes = []
    for k in range(runs):
        env = dict(os.environ, PYTHONHASHSEED=str(k))
        r = subprocess.run([sys.executable, p], capture_output=True, text=True, timeout=30,
                           cwd=_workspace_root(), env=env)
        outcomes.append(r.returncode == 0)
    rate = sum(outcomes) / len(outcomes)
    return {"nondeterminism": {"pass_rate": rate, "varied_by": ["PYTHONHASHSEED"],
                               "deterministic": rate in (0.0, 1.0)}, "runs": runs}


# ── K15 regression_pinpoint (heuristic — log↔commit lexical correlation + blame) ─────────────────────
def regression_pinpoint(failing_log: str, max_commits: int = 20) -> Dict:
    r = _run_git(["log", f"--max-count={max_commits}", "--format=%H%x09%s"])
    if not r["ok"]:
        raise ValueError(f"git log failed: {r['stderr'][:200]}")
    terms = {t.lower() for t in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{3,}", failing_log)} if failing_log else set()
    scored = []
    for ln in r["stdout"].splitlines():
        h, _, subj = ln.partition("\t")
        show = _run_git(["show", "--stat", "--format=", h])
        touched = " ".join(show["stdout"].split()) if show["ok"] else ""
        score = sum(1 for t in terms if t in subj.lower() or t in touched.lower())
        scored.append({"commit": h[:12], "subject": subj[:80], "score": score})
    scored.sort(key=lambda c: -c["score"])
    return {"suspect_commits": scored[:5], "basis": "lexical overlap of failing log with subjects+touched files"}


# ── registration ─────────────────────────────────────────────────────────────────────────────────────
register(Tool("error_explain", "Hypotheses (with confidence) for an exception — heuristic direction-finder.",
              _schema({"exception_type": {"type": "string"}, "message": {"type": "string"},
                       "traceback": {"type": "string"}}, ["exception_type"]),
              error_explain, PLAIN, keywords=("error", "exception", "explain", "why", "cause"),
              labels=("heuristic",)))
register(Tool("stack_deep_parse", "Structure a raw traceback into frames (file/line/func).",
              _schema({"traceback_text": {"type": "string"}}, ["traceback_text"]),
              stack_deep_parse, PLAIN, keywords=("traceback", "stack", "parse", "frames")))
register(Tool("delta_debug_input", "ddmin-minimize a failing input against a workspace test .py (bounded).",
              _schema({"failing_input": {"type": "string"}, "test_path": {"type": "string"},
                       "max_runs": {"type": "integer"}}, ["failing_input", "test_path"]),
              delta_debug_input, PLAIN, keywords=("minimize", "ddmin", "shrink", "input", "reduce"),
              sandbox="EXEC", labels=("nonexact",)))
register(Tool("bisect_commits", "Binary-search the culprit commit between good and bad refs (worktree "
              "restored; flaky test -> honest BLOCKED).",
              _schema({"good_ref": {"type": "string"}, "bad_ref": {"type": "string"},
                       "test_path": {"type": "string"}, "max_steps": {"type": "integer"}},
                      ["good_ref", "bad_ref", "test_path"]),
              bisect_commits, PLAIN, keywords=("bisect", "culprit", "regression", "commit"),
              sandbox="EXEC"))
register(Tool("bisect_hunks", "Isolate which hunks of a patch break the test (each applied alone, reverted).",
              _schema({"patch_text": {"type": "string"}, "test_path": {"type": "string"}},
                      ["patch_text", "test_path"]),
              bisect_hunks, PLAIN, keywords=("hunk", "bisect", "patch", "isolate"), sandbox="EXEC"))
register(Tool("print_instrument", "Insert marker-tagged print probes (fully removable via remove=True).",
              _schema({"path": {"type": "string"}, "lines": {"type": "array", "items": {"type": "integer"}},
                       "vars": {"type": "array", "items": {"type": "string"}},
                       "remove": {"type": "boolean"}}, ["path"]),
              print_instrument, PLAIN, keywords=("print", "instrument", "probe", "debug"), sandbox="WRITE"))
register(Tool("state_snapshot", "Capture locals at a specific line via a settrace driver subprocess.",
              _schema({"path": {"type": "string"}, "line": {"type": "integer"},
                       "timeout_s": {"type": "number"}}, ["path", "line"]),
              state_snapshot, PLAIN, keywords=("snapshot", "locals", "state", "inspect"), sandbox="EXEC"))
register(Tool("raise_path_trace", "Static raise-site map for an exception type (dynamic raises listed "
              "unresolved, never guessed).",
              _schema({"path": {"type": "string"}, "exception_type": {"type": "string"}},
                      ["path", "exception_type"]),
              raise_path_trace, PLAIN, keywords=("raise", "exception", "path", "reachable")))
register(Tool("var_flow_trace", "Def-use chain of a variable in a file (AST).",
              _schema({"path": {"type": "string"}, "var": {"type": "string"}, "line": {"type": "integer"}},
                      ["path", "var"]),
              var_flow_trace, PLAIN, keywords=("variable", "flow", "defuse", "trace", "where")))
register(Tool("race_pattern_scan", "Known thread-misuse patterns (suspicion only, never a race verdict).",
              _schema({"path": {"type": "string"}}, ["path"]),
              race_pattern_scan, PLAIN, keywords=("race", "thread", "concurrency", "unsafe"),
              labels=("flag_only",)))
register(Tool("resource_leak_scan", "open() outside `with` and no nearby .close().",
              _schema({"path": {"type": "string"}}, ["path"]),
              resource_leak_scan, PLAIN, keywords=("leak", "resource", "close", "with")))
register(Tool("nan_inf_probe", "Division/log/sqrt sites that can hit NaN/Inf domains (heuristic).",
              _schema({"path": {"type": "string"}}, ["path"]),
              nan_inf_probe, PLAIN, keywords=("nan", "inf", "division", "numeric"), labels=("heuristic",)))
register(Tool("off_by_one_scan", "Boundary-suspicious range/slice patterns (flags only — never patches).",
              _schema({"path": {"type": "string"}}, ["path"]),
              off_by_one_scan, PLAIN, keywords=("boundary", "offbyone", "range", "slice"),
              labels=("flag_only",)))
register(Tool("heisenbug_rerun", "Re-run a test .py varying PYTHONHASHSEED to expose nondeterminism.",
              _schema({"test_path": {"type": "string"}, "runs": {"type": "integer"}}, ["test_path"]),
              heisenbug_rerun, PLAIN, keywords=("flaky", "nondeterministic", "heisenbug", "rerun"),
              sandbox="EXEC", labels=("nonexact",)))
register(Tool("regression_pinpoint", "Rank suspect commits by lexical overlap with the failing log "
              "(+touched files).",
              _schema({"failing_log": {"type": "string"}, "max_commits": {"type": "integer"}},
                      ["failing_log"]),
              regression_pinpoint, PLAIN, keywords=("regression", "suspect", "commit", "pinpoint"),
              labels=("heuristic",)))
