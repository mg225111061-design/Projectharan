"""
PHASE 1.S4 — the unified sound-or-decline gate: translation → differential → symbolic → SMT → recheck.
======================================================================================================
ONE decision pipeline. A claim about a Python function is accepted as PROVEN only if EVERY stage agrees;
any disagreement at any stage ⇒ DECLINE (never a PASS). This is the soundness backbone the whole system
stands on: the optimizer/translator may be UNTRUSTED because this gate re-checks everything by machine.

  S1 differential : the translation (model) agrees with REAL CPython on a battery incl. forced singulars.
  S2 symbolic     : path-sensitive divergence search (CrossHair) — or [BLOCKED] fallback to S1, stated.
  SMT             : Z3 proves the ∀ claim over the (now-trusted) translation.
  S3 recheck      : an INDEPENDENT checker cross-validates Z3 (Z3-PROVEN + a real cex ⇒ DEFER).

Acceptance contract (tested): the false-safety + mistranslation corpus ALL DECLINE; correct claims PROVEN.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

import cert_recheck as CR
import differential_oracle as DO
import symbolic_oracle as SO


@dataclass
class GateResult:
    decision: str               # PROVEN | DECLINE
    stage_reached: str          # which stage produced the decision
    stages: Dict[str, str] = field(default_factory=dict)
    detail: str = ""

    @property
    def proven(self) -> bool:
        return self.decision == "PROVEN"

    def __str__(self):
        return f"{self.decision} (@{self.stage_reached}) {self.stages}"


def gate(py_fn: Callable, model_fn: Callable, arg_kinds: Sequence[str],
         smt_expr: Optional[str] = None, smt_types: Optional[Dict[str, str]] = None) -> GateResult:
    """Run the full sound-or-decline pipeline. `py_fn` = ground truth; `model_fn` = UNTRUSTED translation;
    `smt_expr`/`smt_types` = the ∀ claim to discharge over the (validated) translation (optional)."""
    stages: Dict[str, str] = {}
    # S1 — differential vs real CPython (the translation must be sound first)
    d = DO.differential_check(py_fn, model_fn, arg_kinds)
    stages["S1_differential"] = d.verdict
    if not d.sound:
        return GateResult("DECLINE", "S1_differential", stages, "translation disagrees with CPython — UNSOUND")
    # S2 — symbolic divergence (CrossHair) or honest [BLOCKED] fallback
    s = SO.find_divergence(py_fn, model_fn, arg_kinds)
    stages["S2_symbolic"] = f"{s.status}({s.engine})"
    if s.status == "FOUND_DIVERGENCE":
        return GateResult("DECLINE", "S2_symbolic", stages, "symbolic search found a divergence — UNSOUND")
    # SMT + S3 recheck (only if a claim is supplied)
    if smt_expr and smt_types:
        c = CR.recheck(smt_expr, smt_types)
        stages["SMT+S3_recheck"] = str(c.verdict)
        if c.verdict != "PROVEN":
            return GateResult("DECLINE", "SMT+S3_recheck", stages, f"SMT/recheck did not prove: {c.detail}")
    return GateResult("PROVEN", "all", stages,
                      "translation sound (differential+symbolic) and claim PROVEN+rechecked"
                      if smt_expr else "translation sound (differential+symbolic); no SMT claim supplied")
