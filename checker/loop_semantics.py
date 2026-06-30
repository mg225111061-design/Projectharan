"""
§BD CHK-4 — LOOP SEMANTICS via FOLD (the honest O(1) core): the SLOW check, jumped.
================================================================================================================
The expensive semantic question about an accumulator loop — "what total does it reach / does it stay within a
bound / can it overflow" — is naively O(N): you run the loop. We DON'T run it. We recognize the canonical
accumulator shape, hand the summand to the EXISTING fold engine (`loop_decision.decide_sum_collapse`, Gosper +
our differential certificate), and if it collapses to a closed form S(n) we answer the bound question by
evaluating the FORMULA — O(1). NOT "knowing without looking": we read the loop (O(N) parse) and then jump the
slow part with the closed form.

★ Honest DEFER: if the loop is data-dependent (reads an array / calls out) or outside the fold's decided class,
there is no closed form ⇒ we DEFER that loop's semantics ("can't fold this — review it"). No false O(1) claim.
★ No new disposer: the closed form is issued ONLY by `loop_decision` (which carries a kernel_verdict EXACT cert).
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import List, Optional

from checker.structure_index import StructureIndex


@dataclass
class LoopFact:
    line: int
    kind: str                       # "foldable" | "deferred"
    summand: str = ""
    closed_form: str = ""
    complexity: str = ""            # "O(1)" when folded (the loop collapsed)
    detail: str = ""
    verdict: object = None          # the loop_decision kernel_verdict (EXACT cert) — gates a PROVE/EXACT grade


@dataclass
class LoopReport:
    facts: List[LoopFact] = field(default_factory=list)
    n_foldable: int = 0
    n_deferred: int = 0

    @property
    def foldable_ratio(self) -> float:
        total = self.n_foldable + self.n_deferred
        return (self.n_foldable / total) if total else 0.0


def _range_lo(call: ast.Call) -> int:
    """range(n)→0 ; range(lo, hi[, step])→lo if a literal int, else 0 (best-effort; the closed form is in n)."""
    if len(call.args) >= 2 and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, int):
        return call.args[0].value
    return 0


def _accumulator_summand(node: ast.For) -> Optional[tuple]:
    """Recognize  `for <v> in range(...): <acc> += <expr>`  ⇒ (var_name, summand_src, lo). None otherwise."""
    if not isinstance(node.target, ast.Name):
        return None
    if not (isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name)
            and node.iter.func.id == "range"):
        return None
    if len(node.body) != 1 or node.orelse:
        return None
    stmt = node.body[0]
    if not (isinstance(stmt, ast.AugAssign) and isinstance(stmt.op, ast.Add)):
        return None
    var = node.target.id
    try:
        summand = ast.unparse(stmt.value)            # py3.9+
    except Exception:                                # noqa: BLE001
        return None
    return var, summand, _range_lo(node.iter)


def analyze_loops(idx: StructureIndex, src: str) -> LoopReport:
    """For each loop: try the fold (O(1) semantics) else DEFER. Reuses the engine's decide_sum_collapse verbatim."""
    rep = LoopReport()
    if not idx.parsed:
        return rep
    try:
        import loop_decision as LD
    except Exception as e:                           # noqa: BLE001 — fold engine unavailable ⇒ everything DEFERs
        for lp in idx.loops:
            rep.facts.append(LoopFact(getattr(lp, "lineno", 0), "deferred",
                                      detail=f"fold engine unavailable ({e}) ⇒ DEFER"))
        rep.n_deferred = len(rep.facts)
        return rep

    for lp in idx.loops:
        ln = getattr(lp, "lineno", 0)
        shape = _accumulator_summand(lp) if isinstance(lp, ast.For) else None
        if shape is None:
            rep.facts.append(LoopFact(ln, "deferred",
                                      detail="not a closed-range accumulator (data-dependent / non-sum / while) ⇒ "
                                             "no closed form ⇒ DEFER (review)"))
            continue
        var, summand, lo = shape
        try:
            dec = LD.decide_sum_collapse(summand, var=var, lo=lo)
        except Exception as e:                       # noqa: BLE001
            rep.facts.append(LoopFact(ln, "deferred", summand=summand,
                                      detail=f"fold raised ({type(e).__name__}) ⇒ DEFER"))
            continue
        # CLOSED_FORM carries a kernel_verdict EXACT cert (issued by loop_decision, not by us)
        if getattr(dec, "status", "") == "CLOSED_FORM":
            rep.facts.append(LoopFact(ln, "foldable", summand=summand, closed_form=dec.closed_form,
                                      complexity=dec.complexity or "O(1)",
                                      detail=f"Σ {summand} = {dec.closed_form} ⇒ bound/overflow checkable in O(1) "
                                             f"(loop need not run)", verdict=getattr(dec, "verdict", None)))
        else:
            rep.facts.append(LoopFact(ln, "deferred", summand=summand,
                                      detail=f"fold did not yield a closed form ({getattr(dec,'status','?')}) ⇒ "
                                             f"DEFER this loop's semantics"))
    rep.n_foldable = sum(1 for f in rep.facts if f.kind == "foldable")
    rep.n_deferred = sum(1 for f in rep.facts if f.kind == "deferred")
    return rep


def adversarial_battery() -> dict:
    """★ a polynomial accumulator folds to O(1) (Σ i = n(n−1)/2, semantics jumped); ★ a data-dependent loop
    (`s += a[i]`) DEFERS (no closed form — honest, not a false O(1)); ★ a `while` loop DEFERS (not a range sum)."""
    from checker.structure_index import build_index

    def rep(src):
        return analyze_loops(build_index(src), src)

    poly = rep("def f(n):\n s = 0\n for i in range(n):\n  s += i\n return s")
    quad = rep("def f(n):\n s = 0\n for k in range(1, n):\n  s += k*k\n return s")
    data = rep("def f(a, n):\n s = 0\n for i in range(n):\n  s += a[i]\n return s")
    wh = rep("def f(n):\n s = 0\n while s < n:\n  s += 1\n return s")
    cases = {
        "linear_accumulator_folds_O1": poly.n_foldable == 1 and poly.facts[0].complexity == "O(1)",
        "quadratic_accumulator_folds_O1": quad.n_foldable == 1,
        "data_dependent_loop_defers": data.n_deferred == 1 and data.n_foldable == 0,
        "while_loop_defers": wh.n_deferred == 1 and wh.n_foldable == 0,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
