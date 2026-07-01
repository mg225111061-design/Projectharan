"""
agenttools/catalog_plain.py — PLAIN tools (10H directive Task 2): file I/O, git, one bounded subprocess.
==========================================================================================================
RF-5: these are I/O-bound by nature — no numeric/structural core to fold, no cache/parallelism win to
certify. That is normal, not a shortcoming (the directive's own words: "most agent tools... are I/O-
bound"). Every tool here is tagged PLAIN; none carries a fold/accel claim.

SAFETY (not a Tier-B call — ordinary engineering practice, same spirit as this repo's own "don't introduce
command injection" discipline): every file tool is sandboxed to a WORKSPACE ROOT (`AGENTTOOLS_WORKSPACE`
env var, default: the process cwd) via `_safe_path()` — a path that resolves outside the root raises
ValueError, which `executor.execute()` already turns into an honest `ToolResult(ok=False, ...)` fed back to
the model, never a crash. Writes are additionally confined to a dedicated scratch subdirectory (never the
real source tree). Git tools shell out via a FIXED argv list (never a shell string — no shell-injection
vector) and reject any path/ref argument that starts with `-` (no argument-injection into a git flag
position). The one subprocess tool (`run_python_file`) only runs a `.py` file already inside the workspace,
under a timeout, with output capped — the same "the agent can execute code it wrote" capability this whole
product exists to verify, not a new privilege.
"""
from __future__ import annotations

import glob as _glob
import os
import re
import subprocess
from typing import Dict, List, Optional

from agenttools.registry import PLAIN, Tool, register

_ENV_ROOT = "AGENTTOOLS_WORKSPACE"


def _workspace_root() -> str:
    return os.path.realpath(os.environ.get(_ENV_ROOT) or os.getcwd())


def _safe_path(path: str) -> str:
    """Resolve `path` (relative to the workspace root, or absolute) and reject anything that escapes the
    root. Raises ValueError (never a silent clamp) — the executor reports this to the model as an honest
    tool failure, the same as any other bad argument."""
    root = _workspace_root()
    candidate = path if os.path.isabs(path) else os.path.join(root, path)
    resolved = os.path.realpath(candidate)
    if resolved != root and not resolved.startswith(root + os.sep):
        raise ValueError(f"path escapes the workspace root ({root!r}): {path!r}")
    return resolved


def _reject_flag_like(value: str, argname: str) -> None:
    """Refuse a git path/ref argument that starts with '-' — closes the argument-injection vector (a
    model-controlled string landing in a flag position) without needing per-subcommand '--' placement."""
    if value.startswith("-"):
        raise ValueError(f"{argname} must not start with '-' (would be read as a flag): {value!r}")


# ── file tools ──────────────────────────────────────────────────────────────────────────────────────
def read_file(path: str, max_bytes: int = 20000) -> str:
    p = _safe_path(path)
    with open(p, "r", encoding="utf-8", errors="replace") as fh:
        data = fh.read(max_bytes + 1)
    if len(data) > max_bytes:
        return data[:max_bytes] + f"\n... [truncated, file exceeds {max_bytes} bytes]"
    return data


def list_dir(path: str = ".") -> List[str]:
    return sorted(os.listdir(_safe_path(path)))


def glob_files(pattern: str, path: str = ".") -> List[str]:
    root = _workspace_root()
    base = _safe_path(path)
    matches = _glob.glob(os.path.join(base, pattern), recursive=True)
    return sorted(os.path.relpath(m, root) for m in matches)


def grep_search(pattern: str, path: str = ".", max_results: int = 50) -> List[Dict]:
    root = _workspace_root()
    base = _safe_path(path)
    rx = re.compile(pattern)
    out: List[Dict] = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", "node_modules")]
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                    for i, line in enumerate(fh, 1):
                        if rx.search(line):
                            out.append({"file": os.path.relpath(fp, root), "line": i,
                                       "text": line.rstrip("\n")[:300]})
                            if len(out) >= max_results:
                                return out
            except (IsADirectoryError, PermissionError, UnicodeDecodeError):
                continue
    return out


def file_exists(path: str) -> bool:
    return os.path.exists(_safe_path(path))


def file_stat(path: str) -> Dict:
    p = _safe_path(path)
    st = os.stat(p)
    return {"size_bytes": st.st_size, "is_dir": os.path.isdir(p), "mtime": st.st_mtime}


_SCRATCH_DIR = "agenttools_scratch"


def write_scratch_file(path: str, content: str) -> str:
    """Write ONLY inside a dedicated scratch subdirectory of the workspace — never the real source tree.
    A model-controlled write target could otherwise clobber application code; confining it here bounds the
    blast radius to disposable files regardless of what path string the model supplies."""
    scratch_root = os.path.realpath(os.path.join(_workspace_root(), _SCRATCH_DIR))
    os.makedirs(scratch_root, exist_ok=True)
    resolved = os.path.realpath(os.path.join(scratch_root, path))
    if resolved != scratch_root and not resolved.startswith(scratch_root + os.sep):
        raise ValueError(f"path escapes the scratch root ({scratch_root!r}): {path!r}")
    os.makedirs(os.path.dirname(resolved), exist_ok=True)
    with open(resolved, "w", encoding="utf-8") as fh:
        fh.write(content)
    return f"wrote {len(content)} bytes to {os.path.relpath(resolved, _workspace_root())}"


# ── git tools (read-only; fixed argv, never a shell string) ────────────────────────────────────────
def _run_git(args: List[str], timeout_s: float = 10.0) -> Dict:
    try:
        r = subprocess.run(["git", "-C", _workspace_root()] + args, capture_output=True, text=True,
                           timeout=timeout_s)
        return {"ok": r.returncode == 0, "stdout": r.stdout[:10000], "stderr": r.stderr[:2000],
               "returncode": r.returncode}
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": f"git command timed out after {timeout_s}s",
               "returncode": None}
    except Exception as e:                    # noqa: BLE001 — git missing / permission error / etc.
        return {"ok": False, "stdout": "", "stderr": f"{type(e).__name__}: {e}", "returncode": None}


def git_status() -> Dict:
    return _run_git(["status", "--short"])


def git_diff(path: str = "") -> Dict:
    if path:
        _reject_flag_like(path, "path")
    return _run_git(["diff", path] if path else ["diff"])


def git_log(max_count: int = 10) -> Dict:
    n = max(1, min(int(max_count), 200))
    return _run_git(["log", f"-{n}", "--oneline"])


def git_show(ref: str) -> Dict:
    _reject_flag_like(ref, "ref")
    return _run_git(["show", "--stat", ref])


def git_branch_list() -> Dict:
    return _run_git(["branch", "--list"])


def git_current_branch() -> Dict:
    return _run_git(["rev-parse", "--abbrev-ref", "HEAD"])


def git_blame(path: str, max_lines: int = 50) -> Dict:
    _reject_flag_like(path, "path")
    n = max(1, min(int(max_lines), 500))
    return _run_git(["blame", "-L", f"1,{n}", path])


# ── one bounded subprocess tool ─────────────────────────────────────────────────────────────────────
def run_python_file(path: str, timeout_s: float = 60.0, args: Optional[List[str]] = None) -> Dict:
    """Run a `.py` file ALREADY inside the workspace as a subprocess (fixed argv — `args` are passed
    verbatim to the child interpreter, never through a shell). Output capped; a timeout is honestly
    reported, never silently swallowed."""
    p = _safe_path(path)
    if not p.endswith(".py"):
        raise ValueError("run_python_file only runs .py files")
    cmd = ["python3", p] + [str(a) for a in (args or [])]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s, cwd=_workspace_root())
        return {"ok": r.returncode == 0, "stdout": r.stdout[-10000:], "stderr": r.stderr[-5000:],
               "returncode": r.returncode}
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": f"timed out after {timeout_s}s", "returncode": None}
    except Exception as e:                    # noqa: BLE001
        return {"ok": False, "stdout": "", "stderr": f"{type(e).__name__}: {e}", "returncode": None}


def _schema(props: Dict, required: Optional[List[str]] = None) -> Dict:
    return {"type": "object", "properties": props, "required": required or []}


register(Tool("read_file", "Read a text file's contents (UTF-8, truncated past max_bytes).",
              _schema({"path": {"type": "string"}, "max_bytes": {"type": "integer"}}, ["path"]),
              read_file, PLAIN, keywords=("read", "file", "cat", "open", "contents")))
register(Tool("list_dir", "List the entries of a directory.",
              _schema({"path": {"type": "string"}}), list_dir, PLAIN,
              keywords=("list", "directory", "ls", "dir", "folder")))
register(Tool("glob_files", "Find files under `path` matching a glob pattern (supports **).",
              _schema({"pattern": {"type": "string"}, "path": {"type": "string"}}, ["pattern"]),
              glob_files, PLAIN, keywords=("glob", "find", "pattern", "files", "search")))
register(Tool("grep_search", "Regex-search file contents under `path`, returns matching (file, line, text).",
              _schema({"pattern": {"type": "string"}, "path": {"type": "string"},
                      "max_results": {"type": "integer"}}, ["pattern"]),
              grep_search, PLAIN, keywords=("grep", "search", "regex", "find", "match", "occurrence")))
register(Tool("file_exists", "Check whether a path exists in the workspace.",
              _schema({"path": {"type": "string"}}, ["path"]), file_exists, PLAIN,
              keywords=("exists", "file", "check", "present")))
register(Tool("file_stat", "Get size/mtime/is_dir for a path in the workspace.",
              _schema({"path": {"type": "string"}}, ["path"]), file_stat, PLAIN,
              keywords=("stat", "size", "mtime", "metadata")))
register(Tool("write_scratch_file", "Write content to a path inside the disposable scratch directory "
              "(never the real source tree).",
              _schema({"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
              write_scratch_file, PLAIN, keywords=("write", "save", "scratch", "create", "file")))
register(Tool("git_status", "Show `git status --short` for the workspace repo.", _schema({}),
              git_status, PLAIN, keywords=("git", "status", "changes", "dirty")))
register(Tool("git_diff", "Show `git diff` (optionally for one path) for the workspace repo.",
              _schema({"path": {"type": "string"}}), git_diff, PLAIN,
              keywords=("git", "diff", "changes", "patch")))
register(Tool("git_log", "Show the last N one-line commits for the workspace repo.",
              _schema({"max_count": {"type": "integer"}}), git_log, PLAIN,
              keywords=("git", "log", "history", "commits")))
register(Tool("git_show", "Show a commit's stat summary for the workspace repo.",
              _schema({"ref": {"type": "string"}}, ["ref"]), git_show, PLAIN,
              keywords=("git", "show", "commit", "revision")))
register(Tool("git_branch_list", "List local git branches for the workspace repo.", _schema({}),
              git_branch_list, PLAIN, keywords=("git", "branch", "branches")))
register(Tool("git_current_branch", "The current git branch name for the workspace repo.", _schema({}),
              git_current_branch, PLAIN, keywords=("git", "branch", "current", "checkout")))
register(Tool("git_blame", "Show `git blame` for the first N lines of a file in the workspace repo.",
              _schema({"path": {"type": "string"}, "max_lines": {"type": "integer"}}, ["path"]),
              git_blame, PLAIN, keywords=("git", "blame", "author", "history")))
register(Tool("run_python_file", "Run a .py file already inside the workspace as a subprocess (capped "
              "output, timeout-bounded); use this to execute/verify generated code.",
              _schema({"path": {"type": "string"}, "timeout_s": {"type": "number"},
                      "args": {"type": "array", "items": {"type": "string"}}}, ["path"]),
              run_python_file, PLAIN, keywords=("run", "execute", "python", "test", "verify")))
