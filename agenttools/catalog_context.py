"""
agenttools/catalog_context.py — 카탈로그-v2 P군: 컨텍스트/문서 11종 (우선순위 1, intent repo-fix/code-gen).
==============================================================================================================
All 11 are READ-sandbox tools returning raw payloads — the §1.1 Result Envelope is built by
`executor.execute_enveloped()` (envelope.py), never here. Failure semantics ride the §1.3 mapping:
a validation reject raises ValueError (→ INVALID_INPUT), a missing file/symbol raises
FileNotFoundError (→ NOT_FOUND). Honest labels are declared AT REGISTRATION (§1.4) and auto-attach
to every envelope: P3/P7/P11 `heuristic`, P8 `flag_only`.

★Tier-A override, recorded here + SESSION_LOG + STATUS (same precedent as 카탈로그-100 Phase 1):
the design doc marks P1/P3 as ACCEL, but neither delegates to a verified accel/ engine — P1's
relevance ranking and P3's similarity are plain lexical computation. RF-5 says ACCEL requires a real
`delegate`; "애매하면 PLAIN". Both register PLAIN. If a later wave backs them with the real cache
engine (5차 AN1 repo_scale_index), the tier can be upgraded WITH the delegate then.

Token counts are an ESTIMATE (chars//4, stated in the payload as `token_note`) — stdlib has no real
tokenizer and installing one is forbidden (v2 §3.6); an estimate labeled as such beats a fake exact.
"""
from __future__ import annotations

import ast
import os
import re
from typing import Dict, List, Optional

from agenttools.catalog_plain import _run_git, _safe_path, _schema, _workspace_root
from agenttools.registry import PLAIN, Tool, register

_SKIP_DIRS = {".git", "__pycache__", "node_modules", "target", ".venv", "venv", "reports"}
_MIN_BUDGET = 200


def _iter_py(max_files: int = 800) -> List[str]:
    """Deterministic bounded walk (sorted dirs+files). The workspace holds ~731 .py files — the default
    cap covers ALL of them; a smaller explicit cap is an honest partial scan the caller asked for."""
    root = _workspace_root()
    out: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS and not d.startswith("."))
        for fn in sorted(filenames):
            if fn.endswith(".py"):
                out.append(os.path.join(dirpath, fn))
                if len(out) >= max_files:
                    return out
    return out


def _rel(p: str) -> str:
    return os.path.relpath(p, _workspace_root())


def _read(p: str, cap: int = 60000) -> str:
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return f.read(cap)
    except OSError:
        return ""


def _est_tokens(s: str) -> int:
    return max(1, len(s) // 4)


def _terms(text: str) -> List[str]:
    return [w for w in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", text.lower())]


# ── P1 context_window_pack ★기함 ─────────────────────────────────────────────────────────────────────
def context_window_pack(task_desc: str, token_budget: int, max_files: int = 800) -> Dict:
    """Rank workspace files by task relevance (lexical term overlap: path hits weigh 3×, content hits 1×,
    capped) and pack the best snippet of each into the budget, most-relevant first. Relevance is honest
    lexical scoring, not semantics — good ranking, never a claim of understanding."""
    if not isinstance(token_budget, int) or token_budget < _MIN_BUDGET:
        raise ValueError(f"token_budget below minimum ({_MIN_BUDGET}) — a pack that small carries no context")
    terms = set(_terms(task_desc))
    if not terms:
        raise ValueError("task_desc has no usable terms")
    scored = []
    for p in _iter_py(max_files):
        rel = _rel(p)
        path_hits = sum(1 for t in terms if t in rel.lower())
        content = _read(p)
        lc = content.lower()
        content_hits = sum(min(lc.count(t), 5) for t in terms)
        score = path_hits * 3 + content_hits
        if score > 0:
            scored.append((score, rel, content))
    scored.sort(key=lambda x: (-x[0], x[1]))
    packed, used = [], 0
    for score, rel, content in scored:
        lines = content.splitlines()
        hit_line = next((i for i, ln in enumerate(lines) if any(t in ln.lower() for t in terms)), 0)
        lo = max(0, hit_line - 5)
        snippet = "\n".join(lines[lo:lo + 40])
        cost = _est_tokens(snippet)
        if used + cost > token_budget:
            if not packed:                          # always deliver at least ONE trimmed snippet
                snippet = snippet[: max(0, (token_budget - used) * 4)]
                packed.append({"path": rel, "snippet": snippet, "relevance": score})
                used += _est_tokens(snippet)
            break
        packed.append({"path": rel, "snippet": snippet, "relevance": score})
        used += cost
    return {"packed_context": packed, "tokens_used": used,
            "token_note": "approx estimate (chars//4) — no real tokenizer in stdlib, stated not hidden"}


# ── P2 readme_context_pack ───────────────────────────────────────────────────────────────────────────
def readme_context_pack(max_lines: int = 60) -> Dict:
    root = _workspace_root()
    readme = ""
    for name in ("README.md", "README.rst", "README.txt", "README"):
        p = os.path.join(root, name)
        if os.path.isfile(p):
            readme = "\n".join(_read(p).splitlines()[:max_lines])
            break
    top = sorted(e for e in os.listdir(root)
                 if not e.startswith(".") and e not in _SKIP_DIRS)[:60]
    return {"compressed_context": (readme + "\n\n[top-level entries]\n" + " ".join(top)).strip()}


# ── P3 similar_code_find (heuristic) ─────────────────────────────────────────────────────────────────
def _func_source(path: str, func: str) -> str:
    p = _safe_path(path)
    src = _read(p)
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func:
            return ast.get_source_segment(src, node) or ""
    raise FileNotFoundError(f"symbol {func!r} not found in {path!r}")


def similar_code_find(path: str, func: str, max_files: int = 800, top: int = 5) -> Dict:
    """Token-set Jaccard similarity between the target function and every other top-level function
    (bounded scan) — a HEURISTIC ranking of lookalikes, never an equivalence claim."""
    target = set(_terms(_func_source(path, func)))
    if not target:
        raise ValueError(f"{func!r} has no comparable tokens")
    results = []
    for p in _iter_py(max_files):
        src = _read(p)
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == func and _rel(p) == os.path.relpath(_safe_path(path), _workspace_root()):
                    continue
                cand = set(_terms(ast.get_source_segment(src, node) or ""))
                if not cand:
                    continue
                sim = len(target & cand) / len(target | cand)
                if sim > 0.15:
                    results.append({"location": f"{_rel(p)}:{node.lineno}", "name": node.name,
                                    "similarity": round(sim, 3)})
    results.sort(key=lambda r: -r["similarity"])
    return {"similar": results[:top]}


# ── P4 example_usage_find ────────────────────────────────────────────────────────────────────────────
def example_usage_find(symbol: str, max_results: int = 20, max_files: int = 800) -> Dict:
    pat = re.compile(rf"\b{re.escape(symbol)}\s*\(")
    usages = []
    for p in _iter_py(max_files):
        for i, line in enumerate(_read(p).splitlines(), 1):
            if pat.search(line):
                usages.append({"location": f"{_rel(p)}:{i}", "arg_example": line.strip()[:200]})
                if len(usages) >= max_results:
                    return {"usages": usages}
    return {"usages": usages}


# ── P5 api_doc_extract ───────────────────────────────────────────────────────────────────────────────
def api_doc_extract(path: str) -> Dict:
    p = _safe_path(path)
    src = _read(p)
    tree = ast.parse(src)
    lines = [f"# API — {_rel(p)}"]
    count = 0
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not node.name.startswith("_"):
            count += 1
            if isinstance(node, ast.ClassDef):
                lines.append(f"## class {node.name}")
            else:
                args = ", ".join(a.arg for a in node.args.args)
                lines.append(f"## {node.name}({args})")
            doc = ast.get_docstring(node)
            lines.append((doc.splitlines()[0] if doc else "(docstring 없음)"))
    return {"markdown_api": "\n".join(lines), "public_count": count}


# ── P6 docstring_gen_check ───────────────────────────────────────────────────────────────────────────
def docstring_gen_check(path: str) -> Dict:
    p = _safe_path(path)
    tree = ast.parse(_read(p))
    missing, stubs = [], []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if ast.get_docstring(node) is None:
                missing.append({"name": node.name, "line": node.lineno})
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = ", ".join(a.arg for a in node.args.args if a.arg not in ("self", "cls"))
                    stubs.append({"name": node.name,
                                  "stub": f'"""{node.name}({args}) — TODO: one-line purpose."""'})
    return {"missing": missing, "stubs": stubs}


# ── P7 type_annotate_infer (heuristic, 제안만 — 자동적용 금지) ────────────────────────────────────────
_LIT_TYPES = {ast.Constant: lambda v: type(v.value).__name__, ast.List: lambda v: "list",
              ast.Dict: lambda v: "dict", ast.Tuple: lambda v: "tuple", ast.Set: lambda v: "set"}


def type_annotate_infer(path: str, func: Optional[str] = None) -> Dict:
    """Suggest annotations from DEFAULT-VALUE literal types only (the one basis that is actually visible
    without running anything). Suggestions, never a patch — the tool's whole output is advisory."""
    p = _safe_path(path)
    tree = ast.parse(_read(p))
    suggestions = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (func is None or node.name == func):
            defaults = node.args.defaults
            params = node.args.args[len(node.args.args) - len(defaults):] if defaults else []
            for a, d in zip(params, defaults):
                if a.annotation is None and type(d) in _LIT_TYPES:
                    t = _LIT_TYPES[type(d)](d)
                    if t != "NoneType":
                        suggestions.append({"func": node.name, "param": a.arg, "suggested": t,
                                            "basis": "default-literal"})
    return {"suggestions": suggestions}


# ── P8 comment_stale_detect (flag_only — 판정 아님) ──────────────────────────────────────────────────
def comment_stale_detect(path: str, max_suspects: int = 20) -> Dict:
    """Comments naming a code-like identifier that appears NOWHERE in the file's code are FLAGGED as
    possibly stale — a suspicion marker, never a verdict (flag_only)."""
    p = _safe_path(path)
    src = _read(p)
    code_idents = set(_terms(re.sub(r"#[^\n]*", "", src)))
    suspects = []
    for i, line in enumerate(src.splitlines(), 1):
        m = re.search(r"#(.*)$", line)
        if not m or line.lstrip().startswith("#!"):
            continue
        for ident in re.findall(r"\b[a-z_]+_[a-z_]+\b|\b[a-z]+[A-Z]\w+\b", m.group(1)):
            if ident.lower() not in code_idents:
                suspects.append({"line": i, "comment": m.group(1).strip()[:120], "missing_identifier": ident})
                break
        if len(suspects) >= max_suspects:
            break
    return {"suspects": suspects}


# ── P9 history_context (git log -L, fixed argv) ──────────────────────────────────────────────────────
def history_context(path: str, func: str, max_count: int = 10) -> Dict:
    p = _safe_path(path)
    tree = ast.parse(_read(p))
    span = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func:
            span = (node.lineno, node.end_lineno or node.lineno)
            break
    if span is None:
        raise FileNotFoundError(f"symbol {func!r} not found in {path!r}")
    rel = _rel(p)
    r = _run_git(["log", f"-L{span[0]},{span[1]}:{rel}", f"--max-count={max_count}",
                  "--format=COMMIT\t%h\t%ad\t%s", "--date=short"])
    history = []
    for line in r["stdout"].splitlines():
        if line.startswith("COMMIT\t"):
            _, h, d, s = (line.split("\t", 3) + ["", "", ""])[:4]
            history.append({"commit": h, "date": d, "subject": s})
    out: Dict = {"change_history": history, "span": {"start": span[0], "end": span[1]}}
    if not r["ok"]:
        out["git_error"] = r["stderr"][:300]          # honest: empty history WITH the reason, not a fake blank
    return out


# ── P10 todo_context_link (grep + git, 재사용) ───────────────────────────────────────────────────────
def todo_context_link(path: str = ".", max_results: int = 15) -> Dict:
    from agenttools.catalog_explore import todo_scan        # REUSE the existing scanner, not a re-scan impl
    todos = todo_scan(path=path, max_results=max_results).get("todos", [])
    out = []
    for t in todos:
        r = _run_git(["log", "-1", "--format=%h %s", "--", t.get("path", "")])
        out.append(dict(t, last_commit=r["stdout"].strip()[:120] if r["ok"] else ""))
    return {"todos_with_context": out}


# ── P11 spec_extract_haran ★HARAN-FIRST 지원 (heuristic, draft만) ────────────────────────────────────
def spec_extract_haran(path: str, func: str) -> Dict:
    """Draft a HARAN requires/ensures skeleton from what the code VISIBLY states (params, asserts, return
    shape). A DRAFT for the pipeline's verifier to formalize — explicitly labeled, never a proven spec."""
    p = _safe_path(path)
    src = _read(p)
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func:
            requires = [f"{a.arg} is provided" for a in node.args.args if a.arg not in ("self", "cls")]
            for stmt in node.body:
                if isinstance(stmt, ast.Assert):
                    requires.append(f"assert holds: {ast.unparse(stmt.test)[:100]}")
            returns = [ast.unparse(s.value)[:80] for s in ast.walk(node)
                       if isinstance(s, ast.Return) and s.value is not None][:3]
            ensures = [f"returns {r}" for r in returns] or ["returns (no explicit value)"]
            return {"haran_draft": {"function": func, "requires": requires, "ensures": ensures},
                    "note": "draft"}
    raise FileNotFoundError(f"symbol {func!r} not found in {path!r}")


# ── registration — all READ sandbox; P1/P3 PLAIN by the recorded Tier-A override ─────────────────────
register(Tool("context_window_pack", "Pack the most task-relevant workspace snippets into a token budget "
              "(lexical relevance ranking; token count is a stated estimate).",
              _schema({"task_desc": {"type": "string"}, "token_budget": {"type": "integer"},
                       "max_files": {"type": "integer"}}, ["task_desc", "token_budget"]),
              context_window_pack, PLAIN, keywords=("context", "pack", "budget", "relevant", "window")))
register(Tool("readme_context_pack", "Compressed README + top-level structure context.",
              _schema({"max_lines": {"type": "integer"}}), readme_context_pack, PLAIN,
              keywords=("readme", "overview", "structure", "context")))
register(Tool("similar_code_find", "Find functions similar to a target (token-set Jaccard, heuristic).",
              _schema({"path": {"type": "string"}, "func": {"type": "string"}, "max_files": {"type": "integer"},
                       "top": {"type": "integer"}}, ["path", "func"]),
              similar_code_find, PLAIN, keywords=("similar", "duplicate", "lookalike", "clone"),
              labels=("heuristic",)))
register(Tool("example_usage_find", "Collect real call-site examples of a symbol across the workspace.",
              _schema({"symbol": {"type": "string"}, "max_results": {"type": "integer"},
                       "max_files": {"type": "integer"}}, ["symbol"]),
              example_usage_find, PLAIN, keywords=("usage", "example", "callsite", "how", "called")))
register(Tool("api_doc_extract", "Public API of a Python file as markdown (signatures + docstring lines).",
              _schema({"path": {"type": "string"}}, ["path"]), api_doc_extract, PLAIN,
              keywords=("api", "doc", "markdown", "reference", "public")))
register(Tool("docstring_gen_check", "List defs/classes missing docstrings + one-line stub suggestions.",
              _schema({"path": {"type": "string"}}, ["path"]), docstring_gen_check, PLAIN,
              keywords=("docstring", "missing", "document", "stub")))
register(Tool("type_annotate_infer", "Suggest parameter annotations from default-literal types "
              "(suggestions only — never applies a patch).",
              _schema({"path": {"type": "string"}, "func": {"type": "string"}}, ["path"]),
              type_annotate_infer, PLAIN, keywords=("type", "annotation", "hint", "infer"),
              labels=("heuristic",)))
register(Tool("comment_stale_detect", "Flag comments naming identifiers absent from the file's code "
              "(suspicion only, never a verdict).",
              _schema({"path": {"type": "string"}, "max_suspects": {"type": "integer"}}, ["path"]),
              comment_stale_detect, PLAIN, keywords=("comment", "stale", "outdated", "drift"),
              labels=("flag_only",)))
register(Tool("history_context", "Per-function change history via git log -L (fixed argv).",
              _schema({"path": {"type": "string"}, "func": {"type": "string"},
                       "max_count": {"type": "integer"}}, ["path", "func"]),
              history_context, PLAIN, keywords=("history", "blame", "evolution", "log", "why")))
register(Tool("todo_context_link", "TODO/FIXME markers linked to each file's last commit (reuses todo_scan).",
              _schema({"path": {"type": "string"}, "max_results": {"type": "integer"}}),
              todo_context_link, PLAIN, keywords=("todo", "fixme", "context", "commit")))
register(Tool("spec_extract_haran", "Draft HARAN requires/ensures from a function's visible params/asserts/"
              "returns (draft for the verifier, never a proven spec).",
              _schema({"path": {"type": "string"}, "func": {"type": "string"}}, ["path", "func"]),
              spec_extract_haran, PLAIN, keywords=("spec", "haran", "requires", "ensures", "contract"),
              labels=("heuristic",)))
