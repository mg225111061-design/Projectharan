"""
agenttools/catalog_explore.py — A-group code-exploration tools (카탈로그-100 설계서, §2).
=================================================================================================================
The design doc's A-group is 14 tools; 5 already exist in catalog_plain.py (`read_file`=file_read,
`list_dir`≈dir_tree's shallow case, `grep_search`=code_grep, `file_exists`, `file_stat`) and are NOT
duplicated here (설계서 전제: 겹치면 통합, 새로 만들지 않는다). This module adds the genuinely-new ones:
file_write, file_patch, dir_tree, symbol_find, ast_outline, docstring_extract, import_graph, call_graph,
reach_closure, todo_scan, loc_stats.

★ TIER HONESTY (Tier-A call, logged in SESSION_LOG) ★: the design doc *suggested* FOLD for import_graph/
call_graph and ACCEL for reach_closure. But RF-5 (and the doc's own principle 1: "애매하면 PLAIN으로
보수적으로") is binding here — these are plain AST/graph computations that do NOT delegate to a verified
fold/accel engine, so labelling them FOLD/ACCEL would be exactly the false-EXACT-class mislabel the registry
exists to prevent. They are PLAIN. (Only tools that genuinely call an existing recognizer/fold engine —
catalog_fold.py, and the grade-adapter C-group — earn FOLD.)

Safety: reuses catalog_plain's `_safe_path`/`_workspace_root` verbatim (workspace-sandboxed, path escape →
ValueError → honest tool failure). `file_write` is workspace-scoped but refuses to overwrite an existing
file (the design's "기존 파일이면 거부 → file_patch 유도"); `file_patch` does a uniqueness-checked
str_replace and, on a non-unique/absent match, returns candidate line numbers rather than editing blindly.
"""
from __future__ import annotations

import ast
import os
from typing import Dict, List, Optional

from agenttools.catalog_plain import _safe_path, _schema, _workspace_root
from agenttools.registry import PLAIN, Tool, register


# ── edit tools ──────────────────────────────────────────────────────────────────────────────────────
def file_write(path: str, content: str) -> Dict:
    """Create a NEW file inside the workspace. Refuses if the file already exists (use file_patch to edit) —
    prevents a model from silently clobbering source it should be surgically editing."""
    p = _safe_path(path)
    if os.path.exists(p):
        return {"ok": False, "error": f"{path!r} already exists — use file_patch to edit it, not file_write"}
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(content)
    return {"ok": True, "bytes": len(content), "path": os.path.relpath(p, _workspace_root())}


def file_patch(path: str, old: str, new: str) -> Dict:
    """str_replace-style precise edit: `old` must appear EXACTLY ONCE in the file. If it appears zero or
    many times, no write happens and the candidate line numbers are returned so the caller can disambiguate
    (never a blind or partial edit)."""
    p = _safe_path(path)
    if not os.path.exists(p):
        return {"ok": False, "error": f"{path!r} does not exist — use file_write to create it"}
    with open(p, "r", encoding="utf-8") as fh:
        text = fh.read()
    count = text.count(old)
    if count != 1:
        lines = [i + 1 for i, ln in enumerate(text.splitlines()) if old.splitlines()[0] in ln] if old else []
        return {"ok": False, "error": f"`old` occurs {count} times (need exactly 1)",
                "candidate_lines": lines[:20]}
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text.replace(old, new, 1))
    return {"ok": True, "path": os.path.relpath(p, _workspace_root()),
            "delta_bytes": len(new) - len(old)}


# ── structure tools ─────────────────────────────────────────────────────────────────────────────────
def dir_tree(path: str = ".", max_depth: int = 3, max_entries: int = 400) -> Dict:
    """Recursive structure listing with depth + entry caps (large trees are truncated, honestly flagged)."""
    root = _safe_path(path)
    base_depth = root.rstrip(os.sep).count(os.sep)
    out: List[str] = []
    truncated = False
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in (".git", "__pycache__", "node_modules"))
        depth = dirpath.rstrip(os.sep).count(os.sep) - base_depth
        if depth >= max_depth:
            dirnames[:] = []
            continue
        for fn in sorted(filenames):
            out.append(os.path.relpath(os.path.join(dirpath, fn), _workspace_root()))
            if len(out) >= max_entries:
                truncated = True
                return {"entries": out, "truncated": truncated, "cap": max_entries}
    return {"entries": out, "truncated": truncated, "count": len(out)}


def _parse(path: str):
    p = _safe_path(path)
    with open(p, "r", encoding="utf-8") as fh:
        return ast.parse(fh.read()), p


def symbol_find(path: str, name: str) -> Dict:
    """Locate a def/class named `name` (top-level or nested) in a Python file — returns each match's line."""
    tree, _ = _parse(path)
    hits: List[Dict] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
            kind = "class" if isinstance(node, ast.ClassDef) else "def"
            hits.append({"kind": kind, "name": node.name, "line": node.lineno})
    return {"path": path, "matches": hits}


def ast_outline(path: str) -> Dict:
    """Top-level + one-nested outline of a Python file: classes, functions, and their signatures/lines."""
    tree, _ = _parse(path)

    def sig(fn) -> str:
        a = fn.args
        names = [p.arg for p in (a.posonlyargs + a.args)]
        if a.vararg:
            names.append("*" + a.vararg.arg)
        names += [p.arg for p in a.kwonlyargs]
        if a.kwarg:
            names.append("**" + a.kwarg.arg)
        return f"{fn.name}({', '.join(names)})"

    items: List[Dict] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            items.append({"kind": "def", "sig": sig(node), "line": node.lineno})
        elif isinstance(node, ast.ClassDef):
            methods = [{"kind": "method", "sig": sig(m), "line": m.lineno}
                       for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
            items.append({"kind": "class", "name": node.name, "line": node.lineno, "methods": methods})
    return {"path": path, "outline": items}


def docstring_extract(path: str) -> Dict:
    """Extract the module docstring + each top-level function/class docstring (first line only) from a file."""
    tree, _ = _parse(path)
    out = {"module": (ast.get_docstring(tree) or "").split("\n")[0]}
    fns: List[Dict] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            doc = (ast.get_docstring(node) or "").split("\n")[0]
            fns.append({"name": node.name, "line": node.lineno, "doc": doc})
    return {"path": path, "module_doc": out["module"], "definitions": fns}


# ── graph tools (PLAIN — plain AST/graph analysis, NOT fold-engine delegation; see module header) ─────
def import_graph(path: str = ".", max_files: int = 300) -> Dict:
    """Module import dependency edges over the .py files under `path` (top-level `import`/`from` only).
    A plain AST walk — no fold engine, no cache-soundness claim (PLAIN, per RF-5)."""
    root = _workspace_root()
    base = _safe_path(path)
    edges: List[List[str]] = []
    seen = 0
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", "node_modules")]
        for fn in sorted(filenames):
            if not fn.endswith(".py") or seen >= max_files:
                continue
            seen += 1
            mod = os.path.relpath(os.path.join(dirpath, fn), root)
            try:
                tree = ast.parse(open(os.path.join(dirpath, fn), encoding="utf-8").read())
            except SyntaxError:
                continue
            for node in tree.body:
                if isinstance(node, ast.Import):
                    for n in node.names:
                        edges.append([mod, n.name])
                elif isinstance(node, ast.ImportFrom) and node.module:
                    edges.append([mod, node.module])
    return {"edges": edges, "files_scanned": seen, "truncated": seen >= max_files}


def call_graph(path: str) -> Dict:
    """Intra-file call edges: which top-level function calls which other top-level function in `path`.
    Plain AST analysis (PLAIN)."""
    tree, _ = _parse(path)
    defs = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    edges: List[List[str]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id in defs:
                    e = [node.name, sub.func.id]
                    if e not in edges:
                        edges.append(e)
    return {"path": path, "defs": sorted(defs), "call_edges": edges}


def reach_closure(path: str, symbol: str) -> Dict:
    """Intra-file forward reachability: the set of top-level functions transitively callable from `symbol`
    (BFS over call_graph edges). Plain graph BFS (PLAIN — not an accel-engine win)."""
    cg = call_graph(path)
    adj: Dict[str, List[str]] = {}
    for a, b in cg["call_edges"]:
        adj.setdefault(a, []).append(b)
    if symbol not in cg["defs"]:
        return {"ok": False, "error": f"{symbol!r} is not a top-level function in {path!r}",
                "defs": cg["defs"]}
    seen, stack = set(), [symbol]
    while stack:
        cur = stack.pop()
        for nxt in adj.get(cur, []):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return {"path": path, "symbol": symbol, "reachable": sorted(seen)}


# ── survey tools ────────────────────────────────────────────────────────────────────────────────────
def todo_scan(path: str = ".", max_results: int = 100) -> Dict:
    """Collect TODO/FIXME/HACK/XXX markers under `path` (file, line, text)."""
    import re
    root = _workspace_root()
    base = _safe_path(path)
    rx = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")
    out: List[Dict] = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", "node_modules")]
        for fn in sorted(filenames):
            fp = os.path.join(dirpath, fn)
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                    for i, line in enumerate(fh, 1):
                        if rx.search(line):
                            out.append({"file": os.path.relpath(fp, root), "line": i,
                                        "text": line.strip()[:200]})
                            if len(out) >= max_results:
                                return {"markers": out, "truncated": True}
            except (IsADirectoryError, PermissionError, UnicodeDecodeError):
                continue
    return {"markers": out, "truncated": False, "count": len(out)}


def loc_stats(path: str = ".", max_files: int = 500) -> Dict:
    """Per-file line + top-level def/class counts for .py files under `path`, plus totals."""
    root = _workspace_root()
    base = _safe_path(path)
    files: List[Dict] = []
    tot_lines = tot_defs = seen = 0
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", "node_modules")]
        for fn in sorted(filenames):
            if not fn.endswith(".py") or seen >= max_files:
                continue
            seen += 1
            fp = os.path.join(dirpath, fn)
            try:
                src = open(fp, encoding="utf-8", errors="ignore").read()
                nlines = src.count("\n") + 1
                ndefs = sum(1 for n in ast.parse(src).body
                            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)))
            except (SyntaxError, OSError):
                continue
            files.append({"file": os.path.relpath(fp, root), "lines": nlines, "top_defs": ndefs})
            tot_lines += nlines
            tot_defs += ndefs
    return {"files": files[:max_files], "total_lines": tot_lines, "total_top_defs": tot_defs,
            "file_count": seen}


# ── registration ────────────────────────────────────────────────────────────────────────────────────
register(Tool("file_write", "Create a NEW file in the workspace (refuses to overwrite — use file_patch to "
              "edit an existing file).",
              _schema({"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
              file_write, PLAIN, keywords=("write", "create", "newfile", "add")))
register(Tool("file_patch", "Precise str_replace edit: `old` must occur exactly once; on ambiguity returns "
              "candidate line numbers instead of editing.",
              _schema({"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}},
                      ["path", "old", "new"]),
              file_patch, PLAIN, keywords=("patch", "edit", "replace", "modify", "fix")))
register(Tool("dir_tree", "Recursive directory tree under `path` (depth + entry capped).",
              _schema({"path": {"type": "string"}, "max_depth": {"type": "integer"},
                      "max_entries": {"type": "integer"}}),
              dir_tree, PLAIN, keywords=("tree", "structure", "recursive", "layout", "directory")))
register(Tool("symbol_find", "Find where a def/class named `name` is defined in a Python file (line numbers).",
              _schema({"path": {"type": "string"}, "name": {"type": "string"}}, ["path", "name"]),
              symbol_find, PLAIN, keywords=("symbol", "definition", "locate", "where", "def", "class")))
register(Tool("ast_outline", "Outline a Python file: top-level functions/classes + method signatures + lines.",
              _schema({"path": {"type": "string"}}, ["path"]), ast_outline, PLAIN,
              keywords=("outline", "ast", "signature", "structure", "overview")))
register(Tool("docstring_extract", "Extract module + top-level def/class docstrings (first line) from a file.",
              _schema({"path": {"type": "string"}}, ["path"]), docstring_extract, PLAIN,
              keywords=("docstring", "doc", "documentation", "purpose")))
register(Tool("import_graph", "Module import dependency edges over .py files under `path` (AST-level).",
              _schema({"path": {"type": "string"}, "max_files": {"type": "integer"}}),
              import_graph, PLAIN, keywords=("import", "dependency", "graph", "module", "deps")))
register(Tool("call_graph", "Intra-file function call edges in a Python file (who calls whom).",
              _schema({"path": {"type": "string"}}, ["path"]), call_graph, PLAIN,
              keywords=("call", "graph", "calls", "invoke", "caller")))
register(Tool("reach_closure", "Top-level functions transitively callable from `symbol` in a file (BFS).",
              _schema({"path": {"type": "string"}, "symbol": {"type": "string"}}, ["path", "symbol"]),
              reach_closure, PLAIN, keywords=("reach", "closure", "reachable", "transitive", "impact")))
register(Tool("todo_scan", "Collect TODO/FIXME/HACK/XXX markers under `path`.",
              _schema({"path": {"type": "string"}, "max_results": {"type": "integer"}}),
              todo_scan, PLAIN, keywords=("todo", "fixme", "hack", "marker", "tech-debt")))
register(Tool("loc_stats", "Per-file line + top-level def/class counts for .py files under `path`, + totals.",
              _schema({"path": {"type": "string"}, "max_files": {"type": "integer"}}),
              loc_stats, PLAIN, keywords=("loc", "lines", "count", "stats", "size")))
