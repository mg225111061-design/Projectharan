"""
§BD CHK-2 — BUG-PATTERN CATALOG (the exhaustive CHECK face): data-driven, one-pass over the CHK-1 site map.
================================================================================================================
The catalog is DATA (a list of Pattern records), not control flow — adding a pattern is adding a row. The scan does
NOT re-walk the whole tree per pattern (that would be O(N×P)); it visits only the relevant site lists the CHK-1
index already collected (division_sites, except_handlers, …) ⇒ O(relevant) ≪ O(N×P). That index reuse IS the speed.

★ CHK-3 conservative discipline (precision 1.0): a pattern fires only on a HIGH-SIGNAL shape (a real, common bug),
and where the shape is genuinely ambiguous it FLAGS rather than stays silent — the checker never marks a buggy line
clean. Not-firing on a benign construct (e.g. `a / b` with a guarded divisor) is NOT "marking clean": CHECKED means
"the catalogued bugs are absent", explicitly NOT "no bug exists" (that is the PROVE face's job, kept separate).
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Callable, List, Optional

from checker.structure_index import StructureIndex


@dataclass
class Finding:
    pattern_id: str
    severity: str                 # "high" | "medium"
    line: int
    col: int
    message: str                  # what is wrong
    hint: str                     # how to fix it (the write→fix→recheck instruction)
    grade_hint: str = "FLAG"      # FLAG (a bug pattern matched) | DEFER (cannot analyze)


# ── helpers (small, bounded sub-scans of a single flagged node — still O(relevant), not O(N)) ──────────────
def _loc(node: ast.AST) -> tuple:
    return getattr(node, "lineno", 0), getattr(node, "col_offset", 0)


def _has_exit(body: List[ast.stmt]) -> bool:
    """Does this loop body contain a break/return/raise that is NOT buried in a *nested* loop? (a nested loop's
    own break does not exit the outer `while True`)."""
    return any(_exit_in(stmt) for stmt in body)


def _exit_in(node: ast.AST) -> bool:
    """True if a break/return/raise is reachable in `node` without crossing into a nested For/While."""
    found = False

    class V(ast.NodeVisitor):
        def visit_Break(self, n):  # noqa: N802
            nonlocal found
            found = True

        def visit_Return(self, n):  # noqa: N802
            nonlocal found
            found = True

        def visit_Raise(self, n):  # noqa: N802
            nonlocal found
            found = True

        def visit_For(self, n):  # noqa: N802 — a nested loop's break belongs to IT, not the outer while
            return

        def visit_While(self, n):  # noqa: N802
            return

    V().visit(node)
    return found


def _is_bare_or_broad(h: ast.ExceptHandler) -> Optional[str]:
    """bare `except:` or `except (BaseException|Exception):` ⇒ the type (or lack of it). None ⇒ a specific type."""
    if h.type is None:
        return "bare except"
    if isinstance(h.type, ast.Name) and h.type.id in ("BaseException", "Exception"):
        return h.type.id
    return None


def _body_is_pass_or_ellipsis(body: List[ast.stmt]) -> bool:
    if len(body) != 1:
        return False
    s = body[0]
    return isinstance(s, ast.Pass) or (
        isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and s.value.value is Ellipsis
    )


# ── the catalog: each entry yields 0+ Findings from ONE index site list ────────────────────────────────────
@dataclass
class Pattern:
    pid: str
    severity: str
    sites: str                                  # the StructureIndex attribute to scan
    fire: Callable[[ast.AST, StructureIndex, str], Optional[Finding]]


def _division_by_zero(node, idx, src):
    # build_index already excluded literal-nonzero divisors; flag ONLY a literal-zero divisor (a certain bug).
    right = node.right
    if isinstance(right, ast.Constant) and isinstance(right.value, (int, float)) and right.value == 0:
        ln, col = _loc(node)
        return Finding("div_zero_literal", "high", ln, col,
                       "division/modulo by the literal 0 — always raises ZeroDivisionError",
                       "remove the dead division or replace the 0 with the intended divisor")
    return None  # variable divisor: NOT flagged (unprovable ⇒ not a 'common bug'; CHECKED ≠ 'no bug')


def _mutable_default(node, idx, src):
    ln, col = _loc(node)
    kind = type(node).__name__.lower()
    return Finding("mutable_default_arg", "high", ln, col,
                   f"mutable default argument ({kind} literal) — shared across all calls, accumulates between them",
                   "default to None and create the container inside the body: `def f(x=None): x = [] if x is None else x`")


def _bare_except(node, idx, src):
    kind = _is_bare_or_broad(node)
    if kind is None:
        return None
    ln, col = _loc(node)
    if _body_is_pass_or_ellipsis(node.body):
        return Finding("except_swallow", "high", ln, col,
                       f"`{kind}` whose body silently passes — the error is swallowed with no log/re-raise",
                       "catch a specific exception, and log or re-raise instead of `pass`")
    if kind == "bare except":
        return Finding("bare_except", "medium", ln, col,
                       "bare `except:` also catches SystemExit/KeyboardInterrupt — masks intended interrupts",
                       "catch `Exception` (or a specific type) rather than a bare `except:`")
    return None


def _eq_none(node, idx, src):
    ln, col = _loc(node)
    return Finding("eq_none", "medium", ln, col,
                   "comparison to None with ==/!= — overridable `__eq__` (and numpy arrays) make this wrong/ambiguous",
                   "use `is None` / `is not None` (identity, not equality)")


def _resource_leak(node, idx, src):
    ln, col = _loc(node)
    return Finding("resource_leak", "high", ln, col,
                   "open() outside a `with` block — the file handle leaks if an exception fires before close()",
                   "wrap it in `with open(...) as f:` so the handle is always released")


def _infinite_while(node, idx, src):
    if _has_exit(node.body):
        return None
    ln, col = _loc(node)
    return Finding("infinite_loop", "high", ln, col,
                   "`while True:` with no reachable break/return/raise — the loop cannot terminate",
                   "add an exit condition (break / return) or make the test bound the iteration")


def _assert_tuple(node, idx, src):
    if isinstance(node.test, ast.Tuple) and len(node.test.elts) > 0:
        ln, col = _loc(node)
        return Finding("assert_tuple", "high", ln, col,
                       "assert on a non-empty tuple literal is ALWAYS true — the check never fails",
                       "drop the parentheses: `assert cond, 'msg'` (a tuple makes it a no-op)")
    return None


CATALOG: List[Pattern] = [
    Pattern("div_zero_literal", "high", "division_sites", _division_by_zero),
    Pattern("mutable_default_arg", "high", "mutable_default_args", _mutable_default),
    Pattern("except_swallow", "high", "except_handlers", _bare_except),
    Pattern("eq_none", "medium", "none_compares", _eq_none),
    Pattern("resource_leak", "high", "resource_opens", _resource_leak),
    Pattern("infinite_loop", "high", "while_true", _infinite_while),
    Pattern("assert_tuple", "high", "asserts", _assert_tuple),
]


def scan(idx: StructureIndex, src: str) -> List[Finding]:
    """One sweep over the pre-collected site lists (NOT the whole AST). O(relevant sites), not O(N lines × P patterns)."""
    findings: List[Finding] = []
    if not idx.parsed:
        return findings
    for pat in CATALOG:
        for node in getattr(idx, pat.sites, []):
            f = pat.fire(node, idx, src)
            if f is not None:
                findings.append(f)
    findings.sort(key=lambda f: (f.line, f.col))
    return findings


def adversarial_battery() -> dict:
    """★ every planted bug is FLAGGED with a location; ★ a clean function yields ZERO findings (no false positive);
    ★ a guarded variable division is NOT flagged (CHECKED ≠ 'no bug'); ★ a `while True` WITH a break is not flagged."""
    from checker.structure_index import build_index

    def fids(src):
        return {f.pattern_id for f in scan(build_index(src), src)}

    clean = fids("def f(n):\n s = 0\n for i in range(n):\n  s += i\n return s")
    md = fids("def f(x=[]):\n x.append(1)\n return x")
    bex = fids("def f():\n try:\n  g()\n except:\n  pass")
    none = fids("def f(x):\n return x == None")
    leak = fids("def f(p):\n fh = open(p)\n return fh.read()")
    inf = fids("def f():\n while True:\n  pass")
    inf_ok = fids("def f():\n while True:\n  if done():\n   break")
    at = fids("def f(x):\n assert (x > 0, 'must be positive')")
    var_div = fids("def f(a, b):\n return a / b")          # variable divisor: conservative NON-flag
    dz = fids("def f(a):\n return a % 0")
    cases = {
        "clean_zero_findings": clean == set(),
        "mutable_default_flagged": "mutable_default_arg" in md,
        "bare_except_swallow_flagged": "except_swallow" in bex,
        "eq_none_flagged": "eq_none" in none,
        "resource_leak_flagged": "resource_leak" in leak,
        "infinite_while_flagged": "infinite_loop" in inf,
        "while_true_with_break_not_flagged": "infinite_loop" not in inf_ok,
        "assert_tuple_flagged": "assert_tuple" in at,
        "variable_division_not_flagged": var_div == set(),     # ★ precision: not every division is a 'bug'
        "literal_zero_division_flagged": "div_zero_literal" in dz,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
