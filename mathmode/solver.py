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

import json
from dataclasses import dataclass, field
from typing import List, Optional

import kernel_verdict as KV
from mathmode import topmode as TM
from pillar3 import mode as PM
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


_GRADE_KO = {KV.EXACT: "증명됨", KV.PROBABILISTIC: "확률적", KV.DECLINE: "보류"}


def _safe_repr(x) -> str:
    """A short, JSON-safe rendering of a verdict result (closed-form callable, Fraction, sympy expr, tuple…)."""
    if x is None:
        return ""
    if callable(x):
        try:
            return "closed form: n↦ " + ", ".join(f"f({n})={x(n)}" for n in (1, 2, 3, 10))
        except Exception:                                # noqa: BLE001
            return "(closed-form function)"
    try:
        return str(x)
    except Exception:                                    # noqa: BLE001
        return repr(type(x))


@dataclass
class MathSolution:
    verdict: "KV.Verdict"
    reasoning: List[Step] = field(default_factory=list)
    top_mode: str = "MATH"
    inner_mode: str = "normal"

    def trace(self) -> str:
        """The visible, grade-tagged reasoning trace (§5)."""
        lines = [f"[MATH mode · {self.inner_mode}]"]
        for s in self.reasoning:
            tag = f" «{s.grade}»" if s.grade else ""
            lines.append(f"  → {s.stage}: {s.detail}{tag}")
        lines.append(f"  ⇒ {self.verdict.status}"
                     + (f": {self.verdict.certificate.kind}" if self.verdict.certificate else
                        f" ({self.verdict.reason})"))
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """JSON-safe payload for /api/math/solve — the grade-tagged reasoning + certificate, visible in the UI."""
        v, c = self.verdict, self.verdict.certificate
        return {
            "top_mode": "math", "inner_mode": self.inner_mode,
            "status": v.status, "grade_ko": _GRADE_KO.get(v.status, v.status),
            "reason": v.reason, "answer": _safe_repr(v.result),
            "certificate": (None if c is None else {
                "kind": c.kind, "detail": c.detail, "check_cost": c.check_cost,
                "epsilon": (None if c.epsilon is None else float(c.epsilon)),
                "delta": (None if c.delta is None else float(c.delta))}),
            "reasoning": [{"stage": s.stage, "detail": s.detail, "grade": s.grade} for s in self.reasoning],
        }


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


def parse_problem(text) -> dict:
    """Lenient text → problem dict for the MATH surface. Accepts:
       • a JSON object (used directly),               • 'sum: <expr in k>' / 'Σ <expr>'  → {"sum": …},
       • 'fold: <json>'                               → {"fold": …},
       • a bare summand mentioning k                  → {"sum": …}.
    Anything else returns {} (⇒ the solver DECLINEs honestly)."""
    if isinstance(text, dict):
        return text
    s = (text or "").strip()
    if not s:
        return {}
    if s[0] == "{":
        try:
            return json.loads(s)
        except Exception:                                # noqa: BLE001
            pass
    import re
    m = re.match(r"\s*(?:sum\s*[:=]\s*|Σ\s*)(.+)$", s, re.IGNORECASE)
    if m:
        return {"sum": m.group(1).strip().rstrip(".").replace("^", "**")}
    m2 = re.match(r"\s*fold\s*[:=]\s*(.+)$", s, re.IGNORECASE)
    if m2:
        try:
            return {"fold": json.loads(m2.group(1))}
        except Exception:                                # noqa: BLE001
            return {}
    if "k" in s and not any(ch.isalpha() for ch in s.replace("k", "").replace("factorial", "")):
        return {"sum": s.replace("^", "**")}
    return {}


# ── the OMEGA §B fast/normal/extend grade floor, preserved INSIDE MATH ────────────────────────────────────
def solve_in_mode(problem_or_text, inner_mode: str = "normal") -> MathSolution:
    """Solve, then apply the MATH inner-mode contract (the §B separation, identical to CODE):
       fast / normal accept {EXACT, PROBABILISTIC}; extend is EXACT-or-DECLINE (a PROBABILISTIC answer is
       REJECTED below the extend floor — MATH ships nothing it cannot prove in extend)."""
    problem = problem_or_text if isinstance(problem_or_text, dict) else parse_problem(problem_or_text)
    sol = solve(problem)
    sol.inner_mode = inner_mode
    try:
        policy = PM.ModePolicy.for_mode(PM.Mode(inner_mode))
    except Exception:                                    # noqa: BLE001
        return sol
    g = sol.verdict.status
    if g != KV.DECLINE and not policy.grade_acceptable(g):
        # extend floor bites: a non-EXACT answer is DECLINEd (EXACT-or-DECLINE), with a visible reasoning step
        sol.reasoning.append(Step("mode-floor", f"{inner_mode} contract accepts {sorted(policy.acceptable_grades)}; "
                                                 f"{g} is below the floor ⇒ DECLINE (ship nothing unproven)", KV.DECLINE))
        sol.verdict = KV.decline(f"MATH {inner_mode}: {g} below the extend floor [EXACT] ⇒ DECLINE", "mathmode.mode")
    return sol
