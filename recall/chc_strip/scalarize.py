"""
§AP §6.2 — SCALARIZE: turn a scalarizable array loop into a unary oracle a[n] and dispose it through the existing gate.
================================================================================================================
When §6.1 has proven the loop is a self-referential recurrence (no external data), the function f(n) that builds the
array and returns a[n] IS a pure unary oracle — exec it and route to the §AI conjecturers (which recover the closed
form / linear recurrence and z3-verify it with the multi-scale held-out). The O(n) array loop collapses to the O(1)/
O(log n) closed form. ★ Only called after the scalarizability gate passes, so the oracle is genuinely unary.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class ScalarizeResult:
    folded: bool
    structure: str = ""
    detail: str = ""


def build_oracle(src: str, entry: str = "f") -> Optional[Callable[[int], object]]:
    """exec the source and return the unary entry function (a scalarizable array loop's f(n) is pure in n)."""
    try:
        ns: dict = {}
        exec(compile(src, "<chc>", "exec"), ns)                  # noqa: S102
        f = ns.get(entry)
        if not callable(f):
            return None
        import inspect
        if len(inspect.signature(f).parameters) != 1:            # >1 param ⇒ needs external data ⇒ not unary
            return None
        v = f(0)
        return f if isinstance(v, (int, float)) and not isinstance(v, bool) else None
    except Exception:  # noqa: BLE001
        return None


def scalarize(src: str, entry: str = "f") -> ScalarizeResult:
    oracle = build_oracle(src, entry)
    if oracle is None:
        return ScalarizeResult(False, "", "could not build a unary oracle (needs external data) ⇒ DECLINE")
    from recall import core
    r = core.fold_via_ai(oracle, "chc_strip(scalarize)")
    return ScalarizeResult(r.folded, r.structure_class, r.detail)
