"""
MATH-Ascent §5 — the unified MATH-mode solver with VISIBLE, grade-tagged reasoning.
====================================================================================
One entry point for MATH mode. It follows the §1 route (top_mode=MATH ⇒ first move is FOLD, structure-first),
accelerates with the §4 broth (O(1) certificate lookup) before paying for a fold, and routes everything else to
the §3 arsenal. Crucially, every step is RECORDED and GRADE-TAGGED — the caller (and the UI) can read exactly
which structure was recognized, which tool fired, what certificate licensed the answer, and the grade
(EXACT / PROBABILISTIC / DECLINE) at each stage. The reasoning is the product, not an afterthought: an honest
DECLINE shows precisely where the structure ran out, never a fabricated formula.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import kernel_verdict as KV
from mathmode import topmode as TM
from mathmode import fold as FOLD
from mathmode import broth as BROTH
from mathmode import combinatorics as CB
from mathmode import number_theory as NT
from mathmode import linear_algebra as LA
from mathmode import algebra as AL
from mathmode import geometry as GE
from mathmode import certified_numeric as CN
from mathmode import optimization as OPT
from mathmode import science_engineering as SE


@dataclass
class Step:
    stage: str                      # route | recognize | broth | fold | arsenal
    detail: str
    grade: Optional[str] = None     # EXACT / PROBABILISTIC / DECLINE if this step produced a graded result


@dataclass
class MathSolution:
    verdict: "KV.Verdict"
    reasoning: List[Step] = field(default_factory=list)
    top_mode: str = "MATH"

    def trace(self) -> str:
        """The visible, grade-tagged reasoning trace (§5)."""
        lines = [f"[MATH mode]"]
        for s in self.reasoning:
            tag = f" «{s.grade}»" if s.grade else ""
            lines.append(f"  → {s.stage}: {s.detail}{tag}")
        lines.append(f"  ⇒ {self.verdict.status}"
                     + (f": {self.verdict.certificate.kind}" if self.verdict.certificate else
                        f" ({self.verdict.reason})"))
        return "\n".join(lines)


_ARSENAL = {
    "number_theory": NT.solve, "linear_algebra": LA.solve, "algebra": AL.solve,
    "geometry": GE.solve, "certified_numeric": CN.solve, "combinatorics": CB.summation,
    "optimization": OPT.solve, "science_engineering": SE.solve,
}


def solve(problem: dict) -> MathSolution:
    """Solve a MATH problem, structure-first, broth-accelerated, with a visible grade-tagged trace.
    Shapes:
      {"sum": "<summand in k>"}                         → fold a summation (broth O(1) → Gosper → DECLINE)
      {"fold": {<structured fold object>}}              → the §2 universal fold directly
      {"domain": "<arsenal>", "op": ..., ...}           → the §3 arsenal solver for that domain
    """
    steps: List[Step] = []
    route = TM.route(TM.TopMode.MATH)
    steps.append(Step("route", f"top_mode=MATH; first move = {route.default_first_move}; "
                               f"fold_is_central={route.fold_is_central}"))

    # ── summation: MATH's first move is fold, accelerated by the O(1) broth ──
    if "sum" in problem:
        summand = problem["sum"]
        steps.append(Step("recognize", f"summation Σ_(k≥1) {summand} — try the broth, then Gosper fold"))
        bv = BROTH.prove(summand)
        if bv.status == KV.EXACT:
            steps.append(Step("broth", f"O(1) lookup HIT — {bv.certificate.detail}", KV.EXACT))
            return MathSolution(bv, steps)
        steps.append(Step("broth", "O(1) lookup MISS — pay for the Gosper fold", None))
        gv = CB.gosper_indefinite(summand)
        if gv.status == KV.EXACT:
            steps.append(Step("fold", f"Gosper creative-telescoping — {gv.certificate.detail}", KV.EXACT))
        else:
            steps.append(Step("fold", "Gosper: PROVEN no hypergeometric closed form (honest)", KV.DECLINE))
        return MathSolution(gv, steps)

    # ── a structured fold object (power sum / recurrence / geometric / telescoping / polynomial identity) ──
    if "fold" in problem:
        fv = FOLD.fold(problem["fold"])
        steps.append(Step("recognize", f"fold structure = {fv.structure}"))
        steps.append(Step("fold", fv.detail or fv.verdict.reason, fv.verdict.status))
        return MathSolution(fv.verdict, steps)

    # ── the §3 arsenal ──
    domain = problem.get("domain")
    if domain in _ARSENAL:
        steps.append(Step("recognize", f"domain = {domain}; op = {problem.get('op')}"))
        v = _ARSENAL[domain](problem)
        steps.append(Step("arsenal", v.certificate.detail if v.certificate else v.reason, v.status))
        return MathSolution(v, steps)

    v = KV.decline("solver: no recognized structure/domain (need 'sum', 'fold', or a known 'domain') ⇒ DECLINE",
                   "mathmode.solve")
    steps.append(Step("recognize", "no recognized structure or domain", KV.DECLINE))
    return MathSolution(v, steps)
