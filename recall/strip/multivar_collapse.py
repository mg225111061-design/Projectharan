"""
§AL §1.2 — MULTIVAR COLLAPSE: a function whose foldable sequence is ONE component of a tuple / one of several state
================================================================================================================
variables (the "hidden single variable"). The raw `f(n) → (a, b, c)` is NON-numeric, so the §AI black-box `observe`
rejects it outright. The strip PROJECTS each numeric component to its own unary oracle `fᵢ(n)=f(n)[i]` and folds each;
the genuinely-coupled-but-single sequence is then exposed. ★ projection is semantics-trivial; z3 disposes each.
"""
from __future__ import annotations

from typing import Callable, List, Optional

from recall import core


def _component_oracles(src: str, entry: str) -> List[Callable[[int], object]]:
    """exec the source; if the entry returns a tuple/list, return one projecting oracle per numeric component."""
    try:
        ns: dict = {}
        exec(compile(src, "<multivar>", "exec"), ns)         # noqa: S102
        fn = ns.get(entry)
        if not callable(fn):
            return []
        out = fn(3)
        if not isinstance(out, (tuple, list)):
            return [fn] if isinstance(out, (int, float)) and not isinstance(out, bool) else []
        oracles = []
        for i in range(len(out)):
            if isinstance(out[i], (int, float)) and not isinstance(out[i], bool):
                oracles.append((lambda idx: (lambda n: fn(n)[idx]))(i))
        return oracles
    except Exception:  # noqa: BLE001
        return []


def fold(src: str, entry: str = "f") -> core.StripResult:
    """Fold the FIRST component that the §AI gate accepts; report the index. DECLINE if no component folds."""
    for i, fn in enumerate(_component_oracles(src, entry)):
        r = core.fold_via_ai(fn, f"multivar(component[{i}])")
        if r.folded:
            return r
    return core.StripResult(False, "multivar", "", None, "no numeric component folded (z3 gate)")


def adversarial_battery() -> dict:
    """★ a tuple-returning accumulator (a=Σ1, b=Σa=triangular) — non-numeric to the raw black-box — folds after
    projecting a component (z3-gated); ★ a tuple whose components are all non-foldable (digit-sum pair) DECLINEs."""
    coupled = ("def f(n):\n    a = 0\n    b = 0\n    for k in range(n + 1):\n        a += 1\n        b += a\n"
               "    return (a, b)\n")
    r = fold(coupled)
    nonf = ("def f(n):\n    return (sum(int(d) for d in str(n)), sum(int(d) for d in str(2 * n)))\n")
    d = fold(nonf)
    cases = {
        "tuple_component_folds": r.folded,                       # ★ exposed the hidden single variable
        "nonfoldable_tuple_declines": not d.folded,              # ★ z3 gate holds
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
