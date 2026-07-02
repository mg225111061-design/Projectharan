"""
§1 (CORE) — normal / extend as ENFORCED TIME-BUDGET roles (not speed presets). 2-tier — a former third tier,
`fast`, retired; its instant-win behaviour is now normal's own internal early-exit (pillar3.engine.optimize).
=====================================================================================
The two CODE tiers are DISTINCT roles with DISTINCT wall-clock budgets and DISTINCT guarantees:

  • normal ≈ 30 s  — the standard tier: real optimisation + real verification within a ~30 s budget; a verified
                     result or an honest "needs extend" at the boundary. It FIRST tries an internal, EXACT-only
                     instant early-exit (no Z3, never a speculative shortcut) before its full compounding loop —
                     the absorbed fast-tier behaviour, now just normal's first move.
  • extend ≈ 8 min — the DEEPEST tier, but TIME-BOUNDED at ~480 s, NOT unlimited. It does the heaviest work that
                     fits in 8 minutes; when the budget is spent it returns the BEST CERTIFIED result reached so
                     far, or an honest partial. It NEVER runs past the budget, NEVER fakes a result to fill the
                     time, and NEVER weakens a grade to go faster.

This module is the ENFORCEMENT runtime. `pillar3.mode.ModePolicy` is the contract (the source of truth for each
mode's `latency_budget_s`); here we (1) read that total budget, (2) run the engine's work under it with a HARD
watchdog (`latency_budget.run_with_budget` — a daemon thread that can never block the pipeline), and (3) expose a
`TimeBudget` the live UI consumes ("extend · 3:12 / 8:00").

★ HONEST (§X) ★: at the boundary we return the best CERTIFIED result the work actually reached (recorded as it
went), or an HONEST partial — never a fabricated result, never a grade weakened to fit the clock. A DEFERRED run
is reported AS deferred/partial, not dressed up as EXACT. The budgets are a CEILING on time, not a promise of a
result: extend may still honestly DECLINE within 8 minutes.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import kernel_verdict as KV
import latency_budget as LB
from pillar3.mode import Mode, ModePolicy


def budget_for_mode(mode: Mode) -> float:
    """The TOTAL wall-clock budget (seconds) for a mode, read from the executable ModePolicy. Every mode is now
    BOUNDED — extend is ~8 min, NOT unlimited — so this never returns None/∞."""
    s = ModePolicy.for_mode(mode).latency_budget_s
    if s is None:
        raise ValueError(f"{mode.value} has no bounded budget — extend must be ~8 min, never unlimited")
    return float(s)


def _fmt(sec: float) -> str:
    """m:ss for the UI (negative/overrun clamped to 0)."""
    m, s = divmod(int(max(0.0, sec)), 60)
    return f"{m}:{s:02d}"


@dataclass
class TimeBudget:
    """A live deadline the engine polls and the UI renders. `expired()` is the cooperative early-exit signal; the
    watchdog in `run_under_mode_budget` is the hard backstop for work that ignores it."""
    mode: Mode
    total_s: float
    t0: float

    def elapsed_s(self) -> float:
        return time.monotonic() - self.t0

    def remaining_s(self) -> float:
        return max(0.0, self.total_s - self.elapsed_s())

    def expired(self) -> bool:
        return self.elapsed_s() >= self.total_s

    def fraction_used(self) -> float:
        return min(1.0, self.elapsed_s() / self.total_s) if self.total_s > 0 else 1.0

    def display(self) -> str:
        """e.g. 'extend · 3:12 / 8:00' — the live tier+budget line for the UI (§3)."""
        return f"{self.mode.value} · {_fmt(self.elapsed_s())} / {_fmt(self.total_s)}"


def start_budget(mode: Mode, *, budget_s: Optional[float] = None) -> TimeBudget:
    b = budget_for_mode(mode) if budget_s is None else float(budget_s)
    return TimeBudget(mode, b, time.monotonic())


@dataclass
class Partial:
    """A thread-safe-enough holder (single assignment under the GIL) for the BEST CERTIFIED result the work has
    reached so far. The work calls `offer(result, grade)` whenever it certifies a stronger result; on a budget
    overrun we return this — the honest best-so-far — never a fabricated one."""
    result: Any = None
    grade: Optional[str] = None
    have: bool = False

    def offer(self, result: Any, grade: str) -> None:
        self.result, self.grade, self.have = result, grade, True


@dataclass
class BudgetedRun:
    status: str                     # WITHIN_BUDGET | DEFERRED_PARTIAL | ERROR
    mode: Mode
    elapsed_s: float
    budget_s: float
    result: Any = None
    grade: Optional[str] = None
    detail: str = ""

    @property
    def deferred(self) -> bool:
        return self.status != "WITHIN_BUDGET"

    def __str__(self) -> str:
        if self.status == "WITHIN_BUDGET":
            return f"{self.mode.value}: done in {_fmt(self.elapsed_s)} / {_fmt(self.budget_s)} (grade={self.grade})"
        if self.status == "DEFERRED_PARTIAL":
            best = f"best-so-far grade={self.grade}" if self.grade else "no certified result yet"
            return f"{self.mode.value}: DEFERRED at {_fmt(self.budget_s)} budget — {best} (honest partial, not faked)"
        return f"{self.mode.value}: ERROR — {self.detail}"


def run_under_mode_budget(mode: Mode, work: Callable[["TimeBudget", "Partial"], Any], *,
                          budget_s: Optional[float] = None) -> BudgetedRun:
    """Run `work(budget, partial)` under the mode's TOTAL wall-clock budget and NEVER hang past it.

    Contract for `work`: do the tier's optimisation/verification, polling `budget.expired()` to early-exit
    cooperatively, and call `partial.offer(result, grade)` each time it reaches a STRONGER certified result. If
    `work` returns before the budget, that is the WITHIN_BUDGET result. If it overruns, the hard watchdog
    (`latency_budget.run_with_budget`, a daemon thread) abandons it — the pipeline never blocks — and we return
    DEFERRED_PARTIAL carrying the best certified result `work` had offered (or none). We NEVER fabricate a result
    to fill the budget and NEVER relabel a partial as EXACT to look complete."""
    b = budget_for_mode(mode) if budget_s is None else float(budget_s)
    budget = TimeBudget(mode, b, time.monotonic())
    partial = Partial()
    r = LB.run_with_budget(work, b * 1000.0, budget, partial)
    elapsed = r.elapsed_ms / 1000.0
    if r.status == "OK":
        res = r.value
        grade = partial.grade
        # if work returned a Verdict, surface its grade; else fall back to the last offered grade
        if isinstance(res, KV.Verdict):
            grade = res.status
        return BudgetedRun("WITHIN_BUDGET", mode, elapsed, b, result=res, grade=grade,
                           detail=f"completed within the {_fmt(b)} {mode.value} budget")
    if r.status == "DEFERRED":
        return BudgetedRun("DEFERRED_PARTIAL", mode, elapsed, b,
                           result=(partial.result if partial.have else None),
                           grade=(partial.grade if partial.have else None),
                           detail=f"reached the {_fmt(b)} {mode.value} budget without closing — returning the best "
                                  f"CERTIFIED result so far (no result faked to fill time; grade NOT weakened)")
    return BudgetedRun("ERROR", mode, elapsed, b, detail=r.detail)


def tier_label(mode: Mode) -> str:
    """The honest one-line role+budget label for the report/UI (§3) — never describes extend as unlimited."""
    return {
        Mode.NORMAL: "normal · ~30 s · standard verified within budget, with an internal certified-only "
                     "instant early-exit (absorbs the retired fast tier) · NEVER calls the heavy solver on "
                     "that early-exit path",
        Mode.EXTEND: "extend · ~8 min (BOUNDED) · deepest; returns the best certified result within budget",
    }[mode]
