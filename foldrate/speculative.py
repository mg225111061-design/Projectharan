"""
§AA WEAPON 3 — SPECULATIVE / CONDITIONAL FOLD (the full §X-P1: runtime-guarded, dual-path).
================================================================================================================
Most DECLINEs aren't from absent structure but from ONE dynamic parameter (a stride, modulus, offset). §X-P1 synthesized
the guard Φ and proved `Φ ⟹ folded == original`. WEAPON 3 takes it to its full form: emit BOTH paths — the folded fast
path under Φ and the original as fallback — and check Φ at RUNTIME, dispatching fold-or-original on the actual value.

★ THE FALLBACK INVARIANT (binding): correctness NEVER depends on the guard holding. On a guard-violating input the
fallback (original) runs — correct, just slower. The fold is sound under Φ (z3-proved); off Φ the original is always
correct. So the dispatcher returns the RIGHT answer regardless of the runtime value — only SPEED depends on Φ.
★ RUNTIME-INFORMATION, NOT THE LLM (the honest Maxwell's-demon): the structure is surfaced by a RUNTIME FACT (the actual
value of the dynamic parameter), not by an LLM's guess — the runtime is the observer. It folds STRUCTURED runtime inputs
(a constant stride, a power-of-two length, a fixed modulus); it NEVER folds genuine randomness (no constant guard makes
an input-dependent computation sound ⇒ no fold ⇒ the pigeonhole wall stands).
★ ISSUED ≠ APPLIED: a guard issued ≠ a callsite where Φ provably holds. The fold rate is the APPLIED count.
Reuses §X-P1 `synthesize_guard` for the proof; uses the existing EXACT `guard` field — no new certificate kind. LLM-free.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import thirdpath.axiomatic_fold as P1


@dataclass
class SpeculativeFold:
    issued: bool
    guard: Optional[str] = None
    guard_const: Optional[int] = None
    dyn_var: str = ""
    mechanism: str = "linear_recurrence"    # via §X-P1's existing guard field — no new kind
    applied_callsites: List[str] = field(default_factory=list)
    skipped_callsites: List[str] = field(default_factory=list)
    detail: str = ""

    @property
    def applied(self) -> bool:
        return bool(self.applied_callsites)


def synthesize(folded: Callable, original: Callable, var_names: List[str], dyn_var: str,
               candidates: List[int]) -> SpeculativeFold:
    """Synthesize the speculative guard via §X-P1 (z3-proved `Φ ⟹ folded==original`). Issued ⇒ the dual-path fold is
    available; not issued ⇒ no constant guard makes it sound (e.g. genuinely input-dependent) ⇒ DECLINE."""
    gf = P1.synthesize_guard(folded, original, var_names, dyn_var, candidates)
    const = None
    if gf.issued and gf.guard:
        try:
            const = int(gf.guard.split("==")[1].strip())
        except Exception:  # noqa: BLE001
            const = None
    return SpeculativeFold(gf.issued, gf.guard, const, dyn_var,
                           detail=gf.detail if gf.issued else "no sound guard ⇒ DECLINE (cannot fold input-dependence)")


def runtime_dispatch(sf: SpeculativeFold, folded: Callable, original: Callable, env: Dict) -> Tuple[object, str]:
    """The dual-path runtime executor: check Φ on the ACTUAL runtime value env[dyn_var]; Φ holds ⇒ run the folded fast
    path, else ⇒ run the original fallback. Returns (result, path). The result is correct EITHER way."""
    if sf.issued and sf.guard_const is not None and env.get(sf.dyn_var) == sf.guard_const:
        return folded(env), "folded"
    return original(env), "fallback"


def verify_fallback_invariant(sf: SpeculativeFold, folded: Callable, original: Callable,
                              var_names: List[str], on_env: Dict, off_env: Dict) -> bool:
    """★ Verify correctness is INDEPENDENT of the guard: on a guard-HOLDING input the dispatcher's result == original
    (folded path, proved equal); on a guard-VIOLATING input the result == original (fallback path). Both correct — only
    the path (speed) differs. Returns True iff the dispatcher is correct on BOTH (the fallback invariant holds)."""
    r_on, p_on = runtime_dispatch(sf, folded, original, on_env)
    r_off, p_off = runtime_dispatch(sf, folded, original, off_env)
    return (r_on == original(on_env) and p_on == "folded" and
            r_off == original(off_env) and p_off == "fallback")


def apply_at_callsite(sf: SpeculativeFold, callsite: str, value: Optional[int]) -> bool:
    """Apply ONLY where Φ provably holds at the callsite (value == guard_const). issued ≠ applied: the fold rate is the
    applied count; a callsite where Φ doesn't hold keeps the original (not counted)."""
    if not sf.issued or sf.guard_const is None or value is None or value != sf.guard_const:
        sf.skipped_callsites.append(callsite)
        return False
    sf.applied_callsites.append(callsite)
    return True


def adversarial_battery() -> dict:
    """A dynamic-parameter DECLINE is guarded and dual-pathed (correct on hold AND on miss — the fallback invariant);
    ★ a genuinely input-dependent computation gets NO guard (random/unstructured rejected — pigeonhole); issued≠applied;
    a guard that doesn't make the fold sound is never issued."""
    # foldable under k==4: original x*k, folded x*4
    folded = lambda e: e["x"] * 4
    original = lambda e: e["x"] * e["k"]
    sf = synthesize(folded, original, ["x", "k"], "k", [2, 3, 4, 5])
    # ★ fallback invariant: guard holds (k=4 → folded) and guard fails (k=9 → original), both correct
    fb_ok = verify_fallback_invariant(sf, folded, original, ["x", "k"], {"x": 7, "k": 4}, {"x": 7, "k": 9})
    # dispatch on a guard-violating value returns the CORRECT original result (not a wrong folded one)
    r_off, p_off = runtime_dispatch(sf, folded, original, {"x": 5, "k": 9})
    off_correct = (r_off == 45 and p_off == "fallback")        # 5*9 == 45 via the original, correct despite guard miss
    # ★ genuinely input-dependent: original depends on x in a way no constant-k guard fixes ⇒ NO guard ⇒ DECLINE
    rand = synthesize(lambda e: e["x"] * 4, lambda e: e["x"] * e["k"] + e["x"] % 3, ["x", "k"], "k", [2, 3, 4, 5])
    # issued≠applied
    applied_hit = apply_at_callsite(sf, "k4", 4)
    applied_miss = apply_at_callsite(sf, "k7", 7)
    cases = {
        "guard_issued": sf.issued and sf.guard == "k == 4",
        "fallback_invariant_holds": fb_ok,
        "guard_miss_still_correct": off_correct,               # correctness independent of the profile/guard
        "input_dependent_declined": not rand.issued,           # random/unstructured rejected (pigeonhole)
        "issued_neq_applied": applied_hit and (not applied_miss) and sf.applied_callsites == ["k4"],
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
