"""
NATIVE-CORE §5 — dependency audit (toward zero) + the honest, ENFORCED final dependency set.
=============================================================================================
"Eliminate dependencies" only means something if it is MEASURED and cannot silently regress. This module
AST-scans every source file, classifies each third-party package, and exposes the result so a test can assert
the invariants:

  • FORBIDDEN (big provers / native binders) = ∅ — no coqc/cvc5/Bitwuzla/Lean/PyO3/maturin/cffi import anywhere.
    (Coq is reachable only as an OPTIONAL `subprocess` call in haran_coq.py, [BLOCKED] when `coqc` is absent — a
    runtime dep of ZERO; §2's in-house bit-blasting SMT removes even the Z3 need for the bitvector obligations.)
  • CORE is STDLIB-ONLY — the grade ADT and the whole NATIVE-CORE (in-house SMT, the Rust multimodular-ring
    bridge, the proof triage, the LLM router, the provider config) have an EMPTY third-party top-level import
    closure: they import and run with numpy / z3 / sympy / anthropic / openai all absent. That is the part that
    must be dependency-free, and it provably is.
  • numpy is OPTIONAL-not-required for the core: it is NOT in the core closure. It (with sympy, z3) is a heavy dep
    of specific CODE/MATH numeric kernels only — honestly documented, not pretended away.
  • Every other third-party package (LLM SDKs, JIT, file-ingest, exotic frontends) is imported LAZILY (function
    scope) ⇒ optional, graceful-degrade — enforced so a hard top-level import can't sneak back in.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

_ROOT = Path(__file__).resolve().parent

# big provers / native-binder toolchains we must NOT hard-depend on (constitution: Lean/Coq/Isabelle runtime = 0).
FORBIDDEN = {"coqc", "coq", "cvc5", "bitwuzla", "boolector", "lean", "lean4", "isabelle",
             "pyo3", "maturin", "cffi", "flint", "faer"}

# the modules that MUST stay stdlib-only (empty third-party top-level closure): grade ADT + the NATIVE-CORE.
CORE_MODULES = ["kernel_verdict", "bitblast_smt", "proof_triage", "rust_core", "llm_router", "provider", "haran_ast"]

# the three heavy deps the BROADER engine uses (documented honestly; NOT required by CORE).
HEAVY = {"numpy", "sympy", "z3"}


def _stdlib() -> Set[str]:
    return set(sys.stdlib_module_names) | {"__future__"}


def _repo_modules() -> Set[str]:
    """All intra-repo importable top-level names: root *.py stems, package dirs, and their submodule stems."""
    names: Set[str] = set()
    for p in _ROOT.glob("*.py"):
        names.add(p.stem)
    for d in _ROOT.iterdir():
        if d.is_dir() and (d / "__init__.py").exists() or (d.is_dir() and any(d.glob("*.py"))):
            names.add(d.name)
            for sub in d.rglob("*.py"):
                names.add(sub.stem)
    names |= {"rust_accel", "rust_graph", "rust_core"}
    return names


def _iter_py() -> List[Path]:
    return [p for p in _ROOT.rglob("*.py")
            if "reports/" not in str(p) and "target/" not in str(p)]


def _imports(tree: ast.AST) -> List[Tuple[str, bool]]:
    """(top_level_package_name, is_module_top_level) for every import in the AST."""
    out: List[Tuple[str, bool]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out.append((a.name.split(".")[0], node.col_offset == 0))
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                out.append((node.module.split(".")[0], node.col_offset == 0))
    return out


def scan() -> Dict[str, Dict]:
    """Classify every third-party package: which files use it, and whether it is EVER imported at module top level
    (hard) or only inside functions (lazy/optional)."""
    std, repo = _stdlib(), _repo_modules()
    pkgs: Dict[str, Dict] = {}
    for f in _iter_py():
        if f.name == "test_build.py":
            continue
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for name, top in _imports(tree):
            if not name or name in std or name in repo:
                continue
            rec = pkgs.setdefault(name, {"files": set(), "hard": False})
            rec["files"].add(f.name)
            if top:
                rec["hard"] = True
    return pkgs


def _module_file(name: str) -> Path | None:
    p = _ROOT / f"{name}.py"
    return p if p.exists() else None


def core_third_party_closure() -> Dict[str, Set[str]]:
    """For each CORE module, the set of THIRD-PARTY packages reachable through its TRANSITIVE module-top-level
    import graph (following intra-repo imports). Must be empty for every core module — a static proof that
    importing the core triggers no third-party top-level import (numpy/z3/sympy/… not needed to load it)."""
    std, repo = _stdlib(), _repo_modules()
    result: Dict[str, Set[str]] = {}
    for entry in CORE_MODULES:
        seen: Set[str] = set()
        third: Set[str] = set()
        stack = [entry]
        while stack:
            mod = stack.pop()
            if mod in seen:
                continue
            seen.add(mod)
            f = _module_file(mod)
            if f is None:
                continue
            try:
                tree = ast.parse(f.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for name, top in _imports(tree):
                if not top or not name or name in std:
                    continue
                if name in repo and _module_file(name) is not None:
                    stack.append(name)          # follow intra-repo edge
                elif name not in repo:
                    third.add(name)             # a third-party top-level import in the closure
        result[entry] = third
    return result


def runtime_core_without_heavy(hidden=("numpy", "sympy", "z3", "anthropic", "openai", "numba", "llvmlite")) -> Dict:
    """RUNTIME proof (not just static): in a FRESH subprocess, make `hidden` packages un-importable, then import
    every CORE module. If all succeed, the core genuinely runs with those heavy deps absent. Deterministic."""
    import json
    import subprocess
    script = (
        "import sys, importlib, json\n"          # do all real imports BEFORE installing the blocker
        f"HID={set(hidden)!r}\n"
        f"mods={CORE_MODULES!r}\n"
        "class B:\n"
        " def find_spec(self, n, path=None, target=None):\n"
        "  if n.split('.')[0] in HID: raise ImportError('hidden:'+n)\n"
        "  return None\n"
        "sys.meta_path.insert(0, B())\n"
        "ok=[]; fail=[]\n"
        "for m in mods:\n"
        " try: importlib.import_module(m); ok.append(m)\n"
        " except Exception as e: fail.append([m, repr(e)[:80]])\n"
        "print(json.dumps({'ok':ok,'fail':fail}))\n"
    )
    r = subprocess.run([sys.executable, "-c", script], cwd=str(_ROOT),
                       capture_output=True, text=True, timeout=60)
    try:
        out = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"ok": [], "fail": [["<subprocess>", (r.stderr or r.stdout)[:120]]], "hidden": list(hidden)}
    out["hidden"] = list(hidden)
    return out


def final_dependency_set() -> Dict[str, object]:
    """The honest, documented dependency tiers — reproduced by the test so it can never drift."""
    pkgs = scan()
    hard = sorted(k for k, v in pkgs.items() if v["hard"])
    lazy_only = sorted(k for k, v in pkgs.items() if not v["hard"])
    forbidden_hits = sorted(k for k in pkgs if k in FORBIDDEN)
    return {
        "core": "STDLIB-ONLY (grade ADT + NATIVE-CORE): empty third-party closure — runs with numpy/z3/sympy absent",
        "heavy_required_by_kernels": sorted(HEAVY),     # z3, sympy, numpy — broad engine, NOT the core
        "hard_top_level": hard,                         # what is imported at module scope (the real require-set)
        "optional_lazy": lazy_only,                     # function-scope only ⇒ graceful-degrade
        "forbidden_present": forbidden_hits,            # MUST be []  (big provers / native binders)
        "web": ["fastapi", "pydantic", "uvicorn"],      # server layer (uvicorn already lazy)
    }
