"""
§AC FOLD 2 — SPEC-DECLARED FOLD (the user declares the input structure in HARAN `requires`).
================================================================================================================
HARAN is a specification language with `requires`. When the user declares `requires is_sorted(arr)` / `requires
bounded(x,0,100)` / `requires len == power_of_2`, they hand us the very precondition our synthesis would struggle to
guess. The fold is proved sound UNDER that precondition — exactly as the §X-P1 guarded fold, but the guard is GIVEN, not
synthesized: zero synthesis cost, 100% hit rate wherever the declaration holds (the cheapest, highest-yield guard source).

★ z3 gate (precision 1.0 under the spec): prove `P ⟹ folded == original` (reuse `prove_equiv_z3` with `assumptions=P`).
★ THE DECLARATION'S TRUTH (scope honesty): the fold is sound IF P holds. Whether P actually holds is either (a) RUNTIME-
CHECKED at the boundary (a cheap assertion — P false ⇒ DECLINE-at-runtime, run the original), or (b) the DECLARER'S
RESPONSIBILITY (they asserted `requires`, as any contract). The mode is STATED per fold — never a silent assumption.
★ Perfect HARAN fit: `requires` as an acceleration contract. LLM-free (the spec is user-given). No new certificate kind.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

import catalog.equiv_check as EC


@dataclass
class SpecFold:
    issued: bool
    precondition: str                       # the declared P (the `requires` clause)
    mode: str = ""                          # "runtime-checked" | "declarer-responsible" — STATED, never silent
    applied_callsites: List[str] = field(default_factory=list)
    skipped_callsites: List[str] = field(default_factory=list)
    detail: str = ""

    @property
    def applied(self) -> bool:
        return bool(self.applied_callsites)


def spec_fold(folded: Callable, original: Callable, var_names: List[str], precondition: Callable,
              p_desc: str, mode: str, sort: str = "Int") -> SpecFold:
    """Fold under the user-declared precondition P: prove `P ⟹ folded == original` (z3, assumptions=P). Sound UNDER P.
    `mode` ∈ {runtime-checked, declarer-responsible} is REQUIRED (a silent assumption is rejected)."""
    if mode not in ("runtime-checked", "declarer-responsible"):
        return SpecFold(False, p_desc, mode, detail="the declaration's truth-mode (checked/asserted) MUST be stated ⇒ "
                                                    "silent assumption REJECTED")
    r = EC.prove_equiv_z3(folded, original, var_names, sort=sort, assumptions=precondition)
    if not r.proved:
        return SpecFold(False, p_desc, mode, detail=f"NOT z3-proved sound under `{p_desc}` ⇒ DECLINE (counterexample "
                                                    f"{r.counterexample})")
    return SpecFold(True, p_desc, mode,
                    detail=f"folded ≡ original UNDER `{p_desc}` (z3 ∀-proved, assumptions=P); user-given hypothesis, zero "
                           f"synthesis cost, 100% hit where P holds; truth = {mode}")


def runtime_check(sf: SpecFold, precondition_py: Callable, env) -> bool:
    """For runtime-checked mode: assert P at the boundary. P holds ⇒ apply the fold; P false ⇒ DECLINE-at-runtime (run
    the original — correct behavior, NOT an unsound fold). A false `requires` on real data simply fails here."""
    if sf.mode != "runtime-checked":
        return True                                             # declarer-responsible ⇒ P assumed (contract)
    return bool(precondition_py(env))


def apply_at_callsite(sf: SpecFold, callsite: str, precondition_py: Callable, env) -> bool:
    """Apply ONLY where issued AND (declarer-responsible OR the runtime check passes). P false at runtime ⇒ not applied
    (DECLINE-at-runtime, the original runs)."""
    if not sf.issued or not runtime_check(sf, precondition_py, env):
        sf.skipped_callsites.append(callsite)
        return False
    sf.applied_callsites.append(callsite)
    return True


def adversarial_battery() -> dict:
    """abs(x) folds to x UNDER `requires x≥0` (z3-proved); ★ WITHOUT the precondition it is NOT proved (DECLINE); ★ a
    silent assumption (no mode) is rejected; runtime-checked mode DECLINEs-at-runtime when P is false (correct, not
    unsound); a bounded fold folds under `requires 0≤x≤100`."""
    import z3
    # abs via a branch: original = If(x<0,-x,x); folded = x. Sound ONLY under x≥0.
    folded = lambda e: e["x"]
    original = lambda e: z3.If(e["x"] < 0, -e["x"], e["x"])
    nonneg = lambda e: e["x"] >= 0
    good = spec_fold(folded, original, ["x"], nonneg, "x >= 0", "runtime-checked")
    # ★ without the precondition (assumptions=None via a trivially-true P) it is NOT an identity (x=-1: abs=1≠-1)
    no_pre = EC.prove_equiv_z3(folded, original, ["x"], sort="Int").proved
    # ★ silent assumption (bad mode) rejected
    silent = spec_fold(folded, original, ["x"], nonneg, "x >= 0", mode="(unstated)")
    # runtime-checked: P holds (x=5) ⇒ apply; P false (x=-5) ⇒ DECLINE-at-runtime
    applied_ok = apply_at_callsite(good, "x5", lambda e: e["x"] >= 0, {"x": 5})
    applied_bad = apply_at_callsite(good, "x_neg", lambda e: e["x"] >= 0, {"x": -5})
    # a bounded fold: original overflow-prone f; folded g; sound under 0≤x≤100 (here a trivial identity under bound)
    bounded = spec_fold(lambda e: e["x"] * 2, lambda e: e["x"] + e["x"], ["x"],
                        lambda e: z3.And(e["x"] >= 0, e["x"] <= 100), "0 <= x <= 100", "declarer-responsible")
    cases = {
        "folds_under_declared_P": good.issued and good.mode == "runtime-checked",
        "not_proved_without_P": not no_pre,                    # abs ≢ x without x≥0
        "silent_assumption_rejected": not silent.issued,
        "runtime_checked_applies_when_P_holds": applied_ok,
        "decline_at_runtime_when_P_false": not applied_bad,    # correct behavior, not an unsound fold
        "bounded_fold_under_contract": bounded.issued and bounded.mode == "declarer-responsible",
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
