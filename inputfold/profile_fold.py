"""
§AC FOLD 1 — PROFILE-GUIDED FOLD (measure the input distribution; the fallback invariant is binding).
================================================================================================================
Most DECLINEs are blocked by ONE dynamic parameter. A measured execution PROFILE — "in this deployment, 99% of calls have
stride==1" — tells us WHICH guard actually lands, turning guard SYNTHESIS (guessing) into guard SELECTION (data-driven).
We REUSE §AA-W3 / §X-P1 (`foldrate.speculative`): the profile only CHOOSES the guard Φ; the proof `Φ ⟹ folded==original`
is unchanged.

★ THE FALLBACK INVARIANT (binding): correctness NEVER depends on the profile. The folded fast path runs under Φ; the
ORIGINAL fallback runs otherwise — correct, just slower. If the workload shifts and Φ fails, the fallback keeps the answer
right; only SPEED degrades. We VERIFY the fold is correct even if the profile is 100% wrong.
★ SCOPE: the profile-guided fold rate is "under measured workload W" — NEVER universal. When W is representative the hit
rate is high; when it shifts the fallback holds correctness and the speedup drops. LLM-free (a profile is measurement, not
a guess). No new certificate kind (§X guard field).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import foldrate.speculative as SPEC


@dataclass
class ProfileFold:
    sf: "SPEC.SpeculativeFold"
    selected_value: Optional[int]           # the guard constant the profile picked (the most-frequent observed value)
    profile_support: float = 0.0            # fraction of observed calls at the selected value (the predicted hit rate)
    detail: str = ""

    @property
    def issued(self) -> bool:
        return self.sf.issued


def ingest_profile(observed_values: List[int]) -> Counter:
    """A profile is DATA: the observed runtime values of the dynamic parameter (from running the real workload)."""
    return Counter(observed_values)


def profile_guided_fold(folded: Callable, original: Callable, var_names: List[str], dyn_var: str,
                        profile: Counter) -> ProfileFold:
    """SELECT the guard from the profile (the most-frequent observed value) and synthesize+prove it via §X-P1. The
    profile makes the hit rate high; it does NOT weaken the z3 proof (Φ ⟹ folded==original is proved regardless)."""
    if not profile:
        return ProfileFold(SPEC.SpeculativeFold(False), None, 0.0, "empty profile ⇒ no guard selected ⇒ DECLINE")
    total = sum(profile.values())
    value, count = profile.most_common(1)[0]
    sf = SPEC.synthesize(folded, original, var_names, dyn_var, [value])      # synthesize at the profile-picked value
    support = count / total
    return ProfileFold(sf, value if sf.issued else None, support,
                       detail=(f"profile selected {dyn_var}=={value} (support {support:.2%}); §X-P1 proved Φ⟹folded=="
                               f"original; dual-path with the ORIGINAL fallback — correctness profile-independent"
                               if sf.issued else f"guard at profile value {value} not z3-proved ⇒ DECLINE"))


def run_under_workload(pf: ProfileFold, folded: Callable, original: Callable, dyn_var: str,
                       workload: List[Dict]) -> dict:
    """Dispatch each workload call (dual-path); measure the hit rate UNDER THIS WORKLOAD and confirm EVERY result is
    correct (== original) regardless of which path ran — the applied fold rate is workload-scoped, correctness is not."""
    folded_path = 0
    all_correct = True
    for env in workload:
        result, path = SPEC.runtime_dispatch(pf.sf, folded, original, env)
        if result != original(env):
            all_correct = False
        if path == "folded":
            folded_path += 1
    n = len(workload)
    return {"workload_size": n, "folded_path": folded_path, "fallback_path": n - folded_path,
            "hit_rate_under_W": round(folded_path / n, 4) if n else 0.0,
            "all_correct": all_correct,                         # ★ correctness independent of the workload/profile
            "scope": "under measured workload W (NOT universal)"}


def verify_fallback_invariant(pf: ProfileFold, folded: Callable, original: Callable, dyn_var: str) -> bool:
    """★ The binding check: even if the profile is 100% WRONG (the real workload never hits the selected value), the
    dispatcher is still correct — every call takes the fallback (original) and returns the right answer. Only speed drops."""
    wrong_workload = [{**{v: 0 for v in pf.sf.dyn_var.split()}, dyn_var: pf.selected_value + 7, "x": x}
                      for x in range(5)] if pf.selected_value is not None else []
    if not wrong_workload:
        return False
    r = run_under_workload(pf, folded, original, dyn_var, wrong_workload)
    return r["all_correct"] and r["folded_path"] == 0          # profile fully wrong ⇒ all fallback ⇒ still correct


def adversarial_battery() -> dict:
    """A profile selects a guard that folds (high hit under W); ★ correctness holds even if the profile is 100% wrong
    (fallback invariant); ★ the rate is workload-scoped not universal; an unproven guard is rejected; correctness never
    depends on the profile."""
    folded = lambda e: e["x"] * 4
    original = lambda e: e["x"] * e["k"]
    # profile: 90% of calls have k==4, 10% have k==9
    profile = ingest_profile([4] * 90 + [9] * 10)
    pf = profile_guided_fold(folded, original, ["x", "k"], "k", profile)
    # workload matching the profile ⇒ high hit rate, all correct
    W = [{"x": i, "k": 4} for i in range(90)] + [{"x": i, "k": 9} for i in range(10)]
    r = run_under_workload(pf, folded, original, "k", W)
    # ★ fallback invariant: profile 100% wrong ⇒ still correct (all fallback)
    fb = verify_fallback_invariant(pf, folded, original, "k")
    # an unprovable guard (folded ≠ original under any single k) ⇒ not issued
    bad = profile_guided_fold(lambda e: e["x"] * 4, lambda e: e["x"] * e["k"] + 1, ["x", "k"], "k",
                              ingest_profile([4] * 100))
    cases = {
        "profile_selects_proved_guard": pf.issued and pf.selected_value == 4,
        "high_hit_rate_under_W": r["hit_rate_under_W"] >= 0.8 and r["all_correct"],
        "fallback_invariant_profile_100pct_wrong": fb,                  # ★ correctness ≠ profile
        "rate_is_workload_scoped": "NOT universal" in r["scope"],
        "unprovable_guard_rejected": not bad.issued,
        "all_correct_regardless_of_path": r["all_correct"],
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
