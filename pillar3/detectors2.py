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


# ══════════════════════════════════════════════════════════════════════════════════════════════════════
# BATCH D2 — structural / data-representation detectors (normal-tier)
# ══════════════════════════════════════════════════════════════════════════════════════════════════════

# 6 · dict-of-objects → struct-of-arrays (hot scan over list-of-dicts with repeated key access) ──────────
def detect_dict_to_columnar(fn: Callable) -> WasteFinding:
    """A hot scan over a list of dicts/objects with repeated subscript field access (`r[k]`) → struct-of-arrays
    (parallel lists) eliminates per-row dict hashing when the data is scanned many times."""
    tree = _ast_of(fn)
    if tree is None:
        return WasteFinding("dict_to_columnar", False, 0.0, "source unavailable")
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.ListComp, ast.GeneratorExp, ast.SetComp)):
            subs = [s for s in ast.walk(node) if isinstance(s, ast.Subscript) and isinstance(s.value, ast.Name)]
            if len(subs) >= 2:
                return WasteFinding("dict_to_columnar", True, 0.7,
                                    f"{len(subs)} per-row field accesses in a scan → struct-of-arrays")
    return WasteFinding("dict_to_columnar", False, 0.0, "no list-of-dicts hot scan")


# 7 · loop-invariant computation hoisting ────────────────────────────────────────────────────────────────
def detect_loop_invariant_hoist(fn: Callable) -> WasteFinding:
    """A non-trivial computation (Call/BinOp) inside a loop whose operands are all loop-invariant (not the loop
    target, not assigned in the loop) → hoist it out (compute once)."""
    tree = _ast_of(fn)
    if tree is None:
        return WasteFinding("loop_invariant_hoist", False, 0.0, "source unavailable")
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        loopvars = {t.id for t in ast.walk(node.target) if isinstance(t, ast.Name)}
        assigned = {t.id for s in ast.walk(node) if isinstance(s, ast.Assign)
                    for t in ast.walk(s) if isinstance(t, ast.Name) and isinstance(t.ctx, ast.Store)}
        for s in node.body:
            if isinstance(s, ast.Assign) and isinstance(s.value, (ast.Call, ast.BinOp)):
                names = {x.id for x in ast.walk(s.value) if isinstance(x, ast.Name)}
                rhs_targets = {t.id for t in ast.walk(s) if isinstance(t, ast.Name) and isinstance(t.ctx, ast.Store)}
                used = names - rhs_targets
                if used and not (used & loopvars) and not (used & (assigned - rhs_targets)):
                    return WasteFinding("loop_invariant_hoist", True, 0.8,
                                        "loop-invariant computation inside a loop → hoist (compute once)")
    return WasteFinding("loop_invariant_hoist", False, 0.0, "no hoistable invariant")


# 8 · defensive-copy elimination ─────────────────────────────────────────────────────────────────────────
def detect_copy_elim(fn: Callable) -> WasteFinding:
    """A defensive copy (list(x) / x[:] / .copy()) of data that is then only read → eliminate the copy."""
    tree = _ast_of(fn)
    if tree is None:
        return WasteFinding("copy_elim", False, 0.0, "source unavailable")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "copy":
                return WasteFinding("copy_elim", True, 0.7, "`.copy()` of read-only data → eliminate the copy")
            if isinstance(node.func, ast.Name) and node.func.id in ("list", "dict", "set") and node.args \
                    and isinstance(node.args[0], ast.Name):
                return WasteFinding("copy_elim", True, 0.6,
                                    f"`{node.func.id}(x)` defensive copy of read-only data → eliminate")
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice) \
                and node.slice.lower is None and node.slice.upper is None and node.slice.step is None:
            return WasteFinding("copy_elim", True, 0.6, "`x[:]` full-slice copy of read-only data → eliminate")
    return WasteFinding("copy_elim", False, 0.0, "no defensive copy")


# 9 · materialize → lazy (a list built only to be iterated once) ─────────────────────────────────────────
def detect_materialize_to_lazy(fn: Callable) -> WasteFinding:
    """A list comprehension bound to a name that is then consumed exactly once (a for-loop / any / all / next)
    → a generator avoids building the whole intermediate list (and enables early exit)."""
    tree = _ast_of(fn)
    if tree is None:
        return WasteFinding("materialize_to_lazy", False, 0.0, "source unavailable")
    built = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.ListComp) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            built[node.targets[0].id] = node
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and node.iter.id in built:
            return WasteFinding("materialize_to_lazy", True, 0.75,
                                f"list `{node.iter.id}` materialised only to iterate once → use a generator")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("any", "all", "next") \
                and node.args and isinstance(node.args[0], ast.Name) and node.args[0].id in built:
            return WasteFinding("materialize_to_lazy", True, 0.8,
                                f"list `{node.args[0].id}` materialised then {node.func.id}() → generator (early exit)")
    return WasteFinding("materialize_to_lazy", False, 0.0, "no materialise-then-consume-once")


# 10 · deeper N+1 (per-item fetch inside a NESTED loop) ──────────────────────────────────────────────────
def detect_deep_n_plus_1(fn: Callable) -> WasteFinding:
    """A fetch-like call inside a nested loop (depth ≥ 2) → coalesce across both levels (a deeper N+1)."""
    from pillar3.fixers.detectors import _FETCH
    tree = _ast_of(fn)
    if tree is None:
        return WasteFinding("deep_n_plus_1", False, 0.0, "source unavailable")
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            if not any(isinstance(s, ast.For) and s is not node for s in ast.walk(node)):
                continue
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    nm = (sub.func.attr if isinstance(sub.func, ast.Attribute)
                          else sub.func.id if isinstance(sub.func, ast.Name) else "")
                    low = nm.lower()
                    if any(low.startswith(p) or low.endswith(p) for p in _FETCH):
                        return WasteFinding("deep_n_plus_1", True, 0.8,
                                            f"`{nm}(...)` inside a nested loop → coalesce (deep N+1)")
    return WasteFinding("deep_n_plus_1", False, 0.0, "no nested-loop fetch")
