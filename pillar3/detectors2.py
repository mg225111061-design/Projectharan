"""
Pillar 3 · PHASE D — detector expansion 4 → 40+ (each a new kind of waste; each gated by its ModePolicy tier).
==============================================================================================================
A detector is a profiler/AST/complexity signature: it identifies WHERE and WHAT the waste is and PROPOSES a
fix. It never decides correctness or speedup — the verifier and the measure harness do (Rule 5). Each detector
here returns a `WasteFinding` (reused from detectors.py) and is registered in the right mode tier in mode.py.

Batches:
  D1 — catastrophic single-bug (fast-eligible): redos_regex, redundant_io_parse, accidental_full_scan,
       quadratic_build, redundant_sort.
  D2 — structural / data-representation (normal-tier): dict_to_columnar, loop_invariant_hoist, copy_elim,
       materialize_to_lazy, deep_n_plus_1.
  D3 — heavy (extend-tier): vectorizable_loop, parallelizable_loop, interproc_memoize, egg_algebraic,
       incremental_recompute.
"""
from __future__ import annotations

import ast
import inspect
import re
import textwrap
from typing import Callable, List, Optional

from pillar3.fixers.detectors import WasteFinding, _ast_of


# ══════════════════════════════════════════════════════════════════════════════════════════════════════
# BATCH D1 — catastrophic single-bug detectors (fast-eligible)
# ══════════════════════════════════════════════════════════════════════════════════════════════════════

# 1 · ReDoS / catastrophic backtracking ─────────────────────────────────────────────────────────────────
# nested quantifier on a group: (X+)+ (X*)* (X+)* (X*)+  — the classic exponential-backtracking signature.
_REDOS = re.compile(r"\([^()]*[+*]\)\s*[+*]")


def detect_redos_regex(fn: Callable) -> WasteFinding:
    """A regex literal with a nested quantifier on a group ⇒ catastrophic backtracking on adversarial input.
    The linear-time fix is an equivalent non-backtracking matcher (SlowFuzz, CCS 2017, in spirit)."""
    try:
        src = textwrap.dedent(inspect.getsource(fn))
    except (OSError, TypeError):
        return WasteFinding("redos_regex", False, 0.0, "source unavailable")
    for m in re.finditer(r"""['"]([^'"]+)['"]""", src):
        if _REDOS.search(m.group(1)):
            return WasteFinding("redos_regex", True, 0.95,
                                f"nested quantifier `{m.group(1)}` → exponential backtracking; linearise")
    return WasteFinding("redos_regex", False, 0.0, "no nested-quantifier regex")


# 2 · redundant I/O / parse inside a loop ────────────────────────────────────────────────────────────────
_PARSE = ("loads", "load", "parse", "parse_", "compile", "read", "decode", "fromstring")


def detect_redundant_io_parse(fn: Callable) -> WasteFinding:
    """A parse/load/compile call inside a loop whose argument is loop-invariant (defined outside) ⇒ re-parsing
    the same thing every iteration; hoist it (parse once, reuse)."""
    tree = _ast_of(fn)
    if tree is None:
        return WasteFinding("redundant_io_parse", False, 0.0, "source unavailable")
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While)):
            loop_targets = {t.id for t in ast.walk(node)
                            if isinstance(t, ast.Name) and isinstance(t.ctx, ast.Store)}
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    nm = (sub.func.attr if isinstance(sub.func, ast.Attribute)
                          else sub.func.id if isinstance(sub.func, ast.Name) else "")
                    if any(nm == p or nm.endswith("_" + p) or nm.startswith(p) for p in _PARSE):
                        argnames = {a.id for a in ast.walk(sub) if isinstance(a, ast.Name)}
                        if argnames and not (argnames & loop_targets):     # arg does not depend on the loop var
                            return WasteFinding("redundant_io_parse", True, 0.85,
                                                f"`{nm}(...)` on loop-invariant data inside a loop → hoist (parse once)")
    return WasteFinding("redundant_io_parse", False, 0.0, "no loop-invariant parse")


# 3 · accidental full-scan (O(n) lookup that should be O(1) indexed) ─────────────────────────────────────
def detect_accidental_full_scan(fn: Callable) -> WasteFinding:
    """A linear search (a comprehension/`next` with an equality test, or `.index(...)`) performed inside a loop
    ⇒ O(n·m); build a dict index once for O(1) lookups."""
    tree = _ast_of(fn)
    if tree is None:
        return WasteFinding("accidental_full_scan", False, 0.0, "source unavailable")
    for node in ast.walk(tree):
        if not isinstance(node, (ast.For, ast.While)):
            continue
        for sub in ast.walk(node):
            # .index(...) inside the loop
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "index":
                return WasteFinding("accidental_full_scan", True, 0.8,
                                    "`.index(...)` inside a loop → O(n·m) linear search; build a dict index")
            # an inner comprehension/genexp with an == filter (linear find)
            if isinstance(sub, (ast.ListComp, ast.GeneratorExp, ast.SetComp)):
                for cmp in ast.walk(sub):
                    if isinstance(cmp, ast.Compare) and any(isinstance(o, ast.Eq) for o in cmp.ops):
                        return WasteFinding("accidental_full_scan", True, 0.75,
                                            "linear find (== filter) inside a loop → index it for O(1) lookup")
    return WasteFinding("accidental_full_scan", False, 0.0, "no in-loop linear scan")


# 4 · quadratic build (acc = acc + [x] / s = s + t in a loop) ────────────────────────────────────────────
def detect_quadratic_build(fn: Callable) -> WasteFinding:
    """An accumulator REASSIGNED by concatenation inside a loop (`acc = acc + [x]`, `s = s + t`) ⇒ O(n²) copies;
    use list.append + ''.join. (The genuinely-quadratic pattern CPython does NOT optimise.)"""
    tree = _ast_of(fn)
    if tree is None:
        return WasteFinding("quadratic_build", False, 0.0, "source unavailable")
    for node in ast.walk(tree):
        if not isinstance(node, (ast.For, ast.While)):
            continue
        for sub in ast.walk(node):
            if (isinstance(sub, ast.Assign) and isinstance(sub.value, ast.BinOp)
                    and isinstance(sub.value.op, ast.Add) and len(sub.targets) == 1
                    and isinstance(sub.targets[0], ast.Name)):
                tgt = sub.targets[0].id
                names = {x.id for x in ast.walk(sub.value) if isinstance(x, ast.Name)}
                if tgt in names:                                  # acc = acc + ...  (self-reassign concat)
                    return WasteFinding("quadratic_build", True, 0.9,
                                        f"`{tgt} = {tgt} + …` inside a loop → O(n²) copies; append + join")
    return WasteFinding("quadratic_build", False, 0.0, "no self-concat accumulation")


# 5 · redundant sort inside a loop ──────────────────────────────────────────────────────────────────────
def detect_redundant_sort(fn: Callable) -> WasteFinding:
    """`sorted(...)` or `.sort()` inside a loop over data that does not change in the loop ⇒ sort once, hoist."""
    tree = _ast_of(fn)
    if tree is None:
        return WasteFinding("redundant_sort", False, 0.0, "source unavailable")
    for node in ast.walk(tree):
        if not isinstance(node, (ast.For, ast.While)):
            continue
        loop_targets = {t.id for t in ast.walk(node)
                        if isinstance(t, ast.Name) and isinstance(t.ctx, ast.Store)}
        for sub in ast.walk(node):
            is_sort = ((isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id == "sorted")
                       or (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                           and sub.func.attr == "sort"))
            if is_sort:
                argnames = {a.id for a in ast.walk(sub) if isinstance(a, ast.Name)}
                if argnames and not (argnames & loop_targets):    # sorting loop-invariant data
                    return WasteFinding("redundant_sort", True, 0.85,
                                        "sort of loop-invariant data inside a loop → hoist (sort once)")
    return WasteFinding("redundant_sort", False, 0.0, "no in-loop redundant sort")
