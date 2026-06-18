"""
v28 STAGE 24 — spurious-counterexample concretization gate (CEGAR).  ★protects working code★
============================================================================================
The most DANGEROUS failure mode: an over-approximate abstraction reports a "counterexample" that does not
actually occur at runtime, and a fix loop then MANGLES correct code to chase a bug that was never real.
This gate stops that: BEFORE any edit, the abstract counterexample is RUN ON THE REAL RUNTIME.

  • reproduced on the real runtime  → REAL_BUG  (enter the fix loop)
  • NOT reproduced                  → SPURIOUS  (refine the abstraction to exclude it; ★DO NOT edit the code★)
  • refinement budget exhausted     → DEFER     (honest — never loops forever)

Plus a regression guard: any proposed fix that breaks a previously-passing test is ROLLED BACK — a
hallucinated fix can never silently destroy working behavior.

★ HONEST (§1.4, §5.6) ★: CEGAR FILTERS spurious counterexamples; it does not make abstraction free —
precision ↔ speed is a real trade-off (a more precise domain is slower), and each concretization costs a
real execution. We never claim to decide the undecidable — on budget exhaustion we DEFER.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

CounterExample = Dict[str, object]                 # concrete input, e.g. {"a": 1, "b": 0}
ProposeFn = Callable[[set], Optional[CounterExample]]   # abstract analyzer: next cex not in `excluded`
ViolationFn = Callable[[CounterExample, object, Optional[BaseException]], bool]   # is this a real violation?


def _freeze(cex: CounterExample):
    return frozenset(cex.items())


@dataclass
class ConcResult:
    reproduced: bool
    observed: object = None
    exc: Optional[str] = None


def concretize(fn: Callable, cex: CounterExample, is_violation: ViolationFn) -> ConcResult:
    """Run `fn` on the concrete counterexample and decide whether the violation ACTUALLY occurs."""
    try:
        out = fn(**cex)
        return ConcResult(is_violation(cex, out, None), out, None)
    except BaseException as e:  # noqa: BLE001 — a runtime crash IS an observable failure to judge
        return ConcResult(is_violation(cex, None, e), None, type(e).__name__)


@dataclass
class CegarVerdict:
    status: str                 # REAL_BUG | NO_BUG | DEFER
    counterexample: Optional[CounterExample] = None
    observed: object = None
    spurious: List[CounterExample] = field(default_factory=list)
    refinements: int = 0
    detail: str = ""

    def __str__(self):
        if self.status == "REAL_BUG":
            return f"REAL_BUG at {self.counterexample} (reproduced on the real runtime) → fix"
        if self.status == "NO_BUG":
            return f"NO_BUG ({len(self.spurious)} spurious counterexample(s) filtered — code NOT edited)"
        return f"DEFER — {self.detail}"


def cegar(propose: ProposeFn, fn: Callable, is_violation: ViolationFn, max_refine: int = 12) -> CegarVerdict:
    """The CEGAR loop: get an abstract counterexample, CONCRETIZE it; real → REAL_BUG; spurious → refine
    (exclude) and retry; no more counterexamples → NO_BUG; budget exhausted → DEFER (never loops forever)."""
    excluded: set = set()
    spurious: List[CounterExample] = []
    for i in range(max_refine + 1):
        cex = propose(excluded)
        if cex is None:
            return CegarVerdict("NO_BUG", spurious=spurious, refinements=i,
                                detail="abstraction reports no (further) counterexample")
        c = concretize(fn, cex, is_violation)
        if c.reproduced:
            return CegarVerdict("REAL_BUG", cex, c.observed, spurious, i, "reproduced on the real runtime")
        spurious.append(cex)            # ★ SPURIOUS: refine, DO NOT edit the code ★
        excluded.add(_freeze(cex))
    return CegarVerdict("DEFER", spurious=spurious, refinements=max_refine,
                        detail=f"refinement budget ({max_refine}) exhausted — deferred (no hang, no edit)")


# ── regression guard: a fix that breaks a passing test is ROLLED BACK ───────────────────────────────
@dataclass
class FixOutcome:
    status: str                 # APPLIED | ROLLBACK
    fn: Callable = None
    broke: List = field(default_factory=list)
    detail: str = ""


def _passes(fn: Callable, inp: CounterExample, expected) -> bool:
    try:
        return fn(**inp) == expected
    except BaseException:  # noqa: BLE001
        return False


def apply_fix_guarded(orig_fn: Callable, fixed_fn: Callable,
                      tests: List[Tuple[CounterExample, object]]) -> FixOutcome:
    """Apply `fixed_fn` only if it breaks NO test that `orig_fn` passed; otherwise ROLL BACK to orig."""
    broke = [inp for inp, exp in tests if _passes(orig_fn, inp, exp) and not _passes(fixed_fn, inp, exp)]
    if broke:
        return FixOutcome("ROLLBACK", orig_fn, broke,
                          "fix broke previously-passing test(s) — rolled back (no hallucinated regression)")
    return FixOutcome("APPLIED", fixed_fn, [], "fix preserves all previously-passing tests")


def from_candidates(candidates: List[CounterExample]) -> ProposeFn:
    """Build an abstract analyzer that proposes each candidate counterexample once (skipping excluded)."""
    def propose(excluded: set) -> Optional[CounterExample]:
        for c in candidates:
            if _freeze(c) not in excluded:
                return c
        return None
    return propose
