"""
§AQ §4 — PERIODIC FSM: when control flow is a deterministic function of the loop counter (`i mod k`), find the period P
================================================================================================================
and ★REDUCE to the existing matrix-power / per-residue mechanism (S-1). period_find recognizes the period; stride_fold
disposes via control_flatten (the matrix-power reduction); poly_bound handles `k²<m` guards with the exact ⌊√m⌋ bound.
★ Honest limit: a DATA-dependent branch is not a function of i ⇒ never folds here (→ §5 / spec-declared). ★ Dual metric
(S-3): Axis A + (protocol handlers / lexers / game state); Axis B > 0 only if the FSM dominates runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from extract.periodic_fsm import period_find as PF, stride_fold as SF, poly_bound as PB


@dataclass
class FSMResult:
    folded: bool
    period: int = 0
    reduces_to: str = ""
    axis_a: int = 0
    axis_b: str = "~0 (>0 if FSM dominates)"
    detail: str = ""


def fold(src: str, oracle: Optional[Callable[[int], object]] = None) -> FSMResult:
    p = PF.analyze(src)
    if not p.periodic:
        return FSMResult(False, 0, "", 0, "~0", "★ " + p.detail)
    if oracle is None:
        return FSMResult(True, p.period, "matrix_power (recognition only — no oracle to dispose)", 1, "~0",
                         p.detail + " (recognized; supply an oracle to dispose via control_flatten)")
    sf = SF.fold_periodic(oracle, p.period)
    return FSMResult(sf.folded, p.period, sf.reduces_to, 1 if sf.folded else 0, "~0 (>0 if FSM dominates)",
                     f"{p.detail}; {sf.detail}")


def adversarial_battery() -> dict:
    """★ a period-3 FSM (state updated per i%3) is recognized AND its oracle folds via control_flatten (matrix-power
    reduction); ★★ a DATA-dependent branch is an honest DECLINE (not a function of i); ★ the poly-bound ⌊√m⌋ exact
    iteration count is z3-verified; ★ component batteries green."""
    fsm_src = "def f(n):\n s=0\n for i in range(n):\n  if i%3==0: s+=1\n  elif i%3==1: s+=2\n return s"
    # the matching oracle: per-cycle adds 1+2+0 = 3 over 3 steps ⇒ piecewise-linear, per-residue C-finite
    def fsm_oracle(n):
        s = 0
        for i in range(n):
            if i % 3 == 0:
                s += 1
            elif i % 3 == 1:
                s += 2
        return s
    ok = fold(fsm_src, fsm_oracle)

    data_src = "def f(n, data):\n s=0\n for i in range(n):\n  if data[i] > 0: s += 1\n return s"
    dd = fold(data_src, None)

    cases = {
        "periodic_fsm_folds": ok.folded and ok.period == 3 and "matrix_power" in ok.reduces_to,
        "data_dependent_declines": not dd.folded,                  # ★★ honest
        "poly_bound_exact": PB.adversarial_battery()["all_ok"],
        "period_recognized": ok.period == 3,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
