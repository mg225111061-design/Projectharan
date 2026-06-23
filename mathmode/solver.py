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
from mathmode import probability as PR
from mathmode import inequalities as IQ
from mathmode import differential as DE
from mathmode import graph as GR
from mathmode import special_functions as SF2
from mathmode import calculus as CAL
from mathmode import logic as LG


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
    "probability": PR.solve, "inequalities": IQ.solve, "differential": DE.solve, "graph": GR.solve,
    "special_functions": SF2.solve, "calculus": CAL.solve, "logic": LG.solve,
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

    # ── three-way DECLINE (1): the parser couldn't read it — a PRECISE parse-failure, not "no structure" ──
    if "_parse_error" in problem:
        v = KV.decline(f"parse: {problem['_parse_error']}", "mathmode.parse")
        steps.append(Step("recognize", f"PARSE FAILURE — {problem['_parse_error']}", KV.DECLINE))
        return MathSolution(v, steps)

    # ── fast kernels (O(log)/O(1) routes + honest O(n) ceilings): modexp / fib / lucas / faulhaber / … ──
    if "kernel" in problem:
        return _solve_kernel(problem, steps)

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


def _solve_kernel(problem: dict, steps: List[Step]) -> MathSolution:
    """Route a fast-kernel op (O(log)/O(1) or honest-O(n)-ceiling) and record a grade-tagged step."""
    from mathmode import fastkernels as FK
    k = problem["kernel"]
    steps.append(Step("recognize", f"fast kernel = {k}"))
    if k == "modexp":
        v = FK.modexp(problem["a"], problem["b"], problem["m"])
    elif k == "fib":
        v = FK.fib_mod(problem["n"], problem.get("m"))
    elif k == "lucas":
        v = FK.lucas_mod(problem["n"], problem.get("m"))
    elif k == "catalan":
        v = FK.catalan(problem["n"], problem.get("m"))
    elif k == "factorial":
        v = FK.factorial(problem["n"], problem.get("m"))
    elif k == "lcm":
        v = FK.lcm(problem["a"], problem["b"])
    elif k == "faulhaber":
        lo = problem.get("lo", 1)
        v = FK.faulhaber(problem["p"], problem["N"], problem.get("m"))
        if v.status == KV.EXACT and lo not in (0, 1):                  # Σ_{lo}^{N} = S(N) − S(lo−1)
            low = FK.faulhaber(problem["p"], lo - 1, problem.get("m"))
            if low.status == KV.EXACT:
                v = KV.exact(v.result - low.result, "fastkernels.faulhaber", v.complexity, v.certificate)
    elif k == "lucas_lehmer":
        v = FK.lucas_lehmer(problem["p"])
    elif k == "collatz":
        v = FK.collatz(problem["n"])
    else:
        v = KV.decline(f"solver: unknown kernel {k!r} ⇒ DECLINE", "mathmode.solve")
    stage = "kernel" if v.status != KV.DECLINE else "kernel"
    steps.append(Step(stage, v.certificate.detail if v.certificate else v.reason, v.status))
    return MathSolution(v, steps)


def parse_problem(text) -> dict:
    """Lenient text → problem dict for the MATH surface, via the robust PHASE-1 parser (`mathmode.parse`):
    Σ/sum(f,k,lo,hi), a^b mod m / pow / towers, fibonacci/lucas/catalan [mod m], Lucas–Lehmer / isprime(2^p−1),
    collatz, n! / factorial, C(n,k), gcd/lcm, det/eigenvalues/inverse([[..]]), factor/solve/integrate/diff/…,
    bare summand in k. Unrecognized ⇒ {"_parse_error": <precise hint>} so the solver gives a SPECIFIC parse DECLINE.
    Legacy 'sum:'/'fold:' prefixes still accepted."""
    if isinstance(text, dict):
        return text
    s = (text or "").strip()
    if not s:
        return {"_parse_error": "empty input"}
    import re
    m2 = re.match(r"\s*fold\s*[:=]\s*(.+)$", s, re.IGNORECASE)
    if m2:
        try:
            return {"fold": json.loads(m2.group(1))}
        except Exception:                                # noqa: BLE001
            return {"_parse_error": "fold: payload is not valid JSON"}
    mleg = re.match(r"\s*sum\s*[:=]\s*(.+)$", s, re.IGNORECASE)
    if mleg:
        return {"sum": mleg.group(1).strip().rstrip(".").replace("^", "**")}
    from mathmode import parse as _P
    return _P.parse(s)


# ── strict free-text → arsenal routing (unambiguous patterns only; anything fuzzy ⇒ {} ⇒ honest DECLINE) ──
def _parse_natural(s: str) -> dict:
    import re
    t = s.strip().rstrip("?.").strip()
    NT_OPS = (
        (r"(?:is\s+)?(\d+)\s+(?:a\s+)?prime", lambda m: {"domain": "number_theory", "op": "is_prime", "n": int(m[1])}),
        (r"(?:is_?prime|prime)\s*\(?\s*(\d+)\s*\)?", lambda m: {"domain": "number_theory", "op": "is_prime", "n": int(m[1])}),
        (r"factori[sz]e?\s+(\d+)", lambda m: {"domain": "number_theory", "op": "factorize", "n": int(m[1])}),
        (r"(?:euler\s*)?(?:phi|totient|φ)\s*\(?\s*(\d+)\s*\)?", lambda m: {"domain": "number_theory", "op": "euler_phi", "n": int(m[1])}),
        (r"gcd\s*\(?\s*(-?\d+)\s*,\s*(-?\d+)\s*\)?", lambda m: {"domain": "number_theory", "op": "egcd", "a": int(m[1]), "b": int(m[2])}),
        (r"pell\s*\(?\s*(\d+)\s*\)?", lambda m: {"domain": "number_theory", "op": "pell", "N": int(m[1])}),
        (r"(?:zeta|ζ)\s*\(?\s*(\d+)\s*\)?", lambda m: {"domain": "special_functions", "op": "zeta_even", "s": int(m[1])}),
        (r"gamma\s*\(?\s*(\d+)\s*/\s*2\s*\)?", lambda m: {"domain": "special_functions", "op": "gamma", "two_z": int(m[1])}),
        (r"gamma\s*\(?\s*(\d+)\s*\)?", lambda m: {"domain": "special_functions", "op": "gamma", "two_z": 2 * int(m[1])}),
    )
    for pat, build in NT_OPS:
        mm = re.fullmatch(pat, t, re.IGNORECASE)
        if mm:
            return build(mm)
    # factor <poly-in-x> | factor <int> ; solve/roots <poly> ; <poly> >= 0
    mf = re.fullmatch(r"factor\s+(.+)", t, re.IGNORECASE)
    if mf:
        arg = mf.group(1).strip()
        if re.fullmatch(r"\d+", arg):
            return {"domain": "number_theory", "op": "factorize", "n": int(arg)}
        return {"domain": "algebra", "op": "factor", "poly": arg.replace("^", "**")}
    msv = re.fullmatch(r"(?:solve|roots?(?:\s+of)?)\s+(.+?)(?:\s*=\s*0)?", t, re.IGNORECASE)
    if msv and "x" in msv.group(1):
        return {"domain": "algebra", "op": "solve_poly", "poly": msv.group(1).strip().replace("^", "**")}
    mi = re.fullmatch(r"(?:integrate|∫)\s+(.+?)(?:\s*d\s*x)?", t, re.IGNORECASE)
    if mi and "x" in mi.group(1):
        return {"domain": "calculus", "op": "integrate", "f": mi.group(1).strip().replace("^", "**")}
    mnn = re.fullmatch(r"(.+?)\s*(?:>=|≥)\s*0", t)
    if mnn and "x" in mnn.group(1):
        return {"domain": "inequalities", "op": "nonneg", "poly": mnn.group(1).strip().replace("^", "**")}
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
