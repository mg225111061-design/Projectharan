"""
Pillar 3 · Stage 1 — waste-type detectors (profiler/AST-grounded, deterministic; Rule 5).
==========================================================================================
The detector identifies WHERE and WHAT the waste is; it never decides correctness or speedup (the verifier and
the measure harness do). Four highest-leverage classes:
  1. list-as-set  (membership-in-list inside a loop)        — AST
  2. uncached recompute (repeated identical pure calls)     — runtime call-count
  3. accidental quadratic (empirical super-linearity)       — complexity fitter
  4. N+1 access (one fetch per item where a batch exists)   — AST
"""
from __future__ import annotations

import ast
import inspect
import textwrap
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable, List, Optional


@dataclass
class WasteFinding:
    waste_type: str
    found: bool
    confidence: float
    evidence: str
    location: str = ""


def _ast_of(fn: Callable) -> Optional[ast.AST]:
    try:
        return ast.parse(textwrap.dedent(inspect.getsource(fn)))
    except (OSError, TypeError, SyntaxError):
        return None


# 1 · list-as-set ─────────────────────────────────────────────────────────────────────────────────────
def detect_membership_in_loop(fn: Callable) -> WasteFinding:
    """A `x in <name>` test inside a loop where <name> is built as a list ⇒ O(n) membership in a hot loop."""
    tree = _ast_of(fn)
    if tree is None:
        return WasteFinding("list_as_set", False, 0.0, "source unavailable")
    list_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, (ast.List, ast.ListComp)):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    list_names.add(t.id)
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Name) and node.value.func.id == "list":
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        list_names.add(t.id)
    in_loop = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While)):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Compare) and any(isinstance(op, (ast.In, ast.NotIn)) for op in sub.ops):
                    comp = sub.comparators[0]
                    if isinstance(comp, ast.Name) and comp.id in list_names:
                        in_loop = True
                        nm = comp.id
    if in_loop:
        return WasteFinding("list_as_set", True, 0.9, f"`in {nm}` (a list) inside a loop → O(n) membership",
                            location=fn.__name__)
    return WasteFinding("list_as_set", False, 0.0, "no membership-in-list-in-loop pattern")


# 2 · uncached recompute ──────────────────────────────────────────────────────────────────────────────
def detect_repeated_pure_calls(call_args: List[tuple], threshold: float = 0.2) -> WasteFinding:
    """Given the args of every call to a (pure) function during a run, flag if a meaningful fraction are
    duplicates (re-computed with unchanged args) ⇒ memoizable."""
    if not call_args:
        return WasteFinding("uncached_recompute", False, 0.0, "no calls observed")
    keys = [repr(a) for a in call_args]
    counts = Counter(keys)
    repeats = sum(c - 1 for c in counts.values())
    frac = repeats / len(keys)
    if frac >= threshold:
        return WasteFinding("uncached_recompute", True, min(0.99, frac),
                            f"{repeats}/{len(keys)} calls ({frac:.0%}) repeat identical args → memoizable")
    return WasteFinding("uncached_recompute", False, frac, f"only {frac:.0%} repeated args (< {threshold:.0%})")


# 3 · accidental quadratic ──────────────────────────────────────────────────────────────────────────────
def detect_accidental_quadratic(fn: Callable[[int], None], sizes: List[int], threshold: float = 1.5) -> WasteFinding:
    """Empirical super-linearity via the Stage-0 complexity fitter: b > threshold ⇒ accidentally super-linear."""
    from pillar3 import complexity as C
    fit = C.measure_complexity(fn, sizes)
    if fit.exponent > threshold and fit.r2 > 0.9:
        return WasteFinding("accidental_quadratic", True, fit.r2,
                            f"empirically {fit.klass} (b={fit.exponent:.2f}, R²={fit.r2:.2f}) → super-linear")
    return WasteFinding("accidental_quadratic", False, fit.r2,
                        f"empirically {fit.klass} (b={fit.exponent:.2f}) — not super-linear")


# 4 · N+1 access ────────────────────────────────────────────────────────────────────────────────────────
_FETCH = ("fetch", "get", "query", "load", "find", "select", "read", "lookup")


def detect_n_plus_1(fn: Callable) -> WasteFinding:
    """A call whose name looks like a per-item fetch, issued inside a loop over items ⇒ N+1 (batchable)."""
    tree = _ast_of(fn)
    if tree is None:
        return WasteFinding("n_plus_1", False, 0.0, "source unavailable")
    LOOPS = (ast.For, ast.While, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
    for node in ast.walk(tree):
        if isinstance(node, LOOPS):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    nm = (sub.func.attr if isinstance(sub.func, ast.Attribute)
                          else sub.func.id if isinstance(sub.func, ast.Name) else "")
                    low = nm.lower()
                    if any(low.startswith(p) or ("_" + p) in low or low.endswith(p) for p in _FETCH):
                        return WasteFinding("n_plus_1", True, 0.8,
                                            f"`{nm}(...)` (a per-item fetch) inside a loop/comprehension → N+1; "
                                            f"batch it", location=fn.__name__)
    return WasteFinding("n_plus_1", False, 0.0, "no per-item fetch in a loop")
