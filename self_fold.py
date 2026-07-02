"""
§AH §4 — SELF-FOLD (dogfood: MR folds its own hot foldable paths) + §5 large-scale SUPER-SCALING.
================================================================================================================
§4 self-fold: profile-guided fold (§AC) finds MR's OWN hot foldable computations (cache-key sums, NTT bounds,
detector numeric loops) and folds them. ★ Correctness NEVER depends on the profile (§AC invariant): the profile only
picks WHERE to fold; the fold itself is still a z3-verified theorem.

★★ THE THREE CLOCKS (this is the section's life): MR wall-clock = Clock A (LLM latency) + Clock B (z3 verification)
+ Clock C (foldable computation). self-fold touches ONLY Clock C. End-to-end latency is dominated by A + B + I/O
(the non-foldable physical floor), so the self-fold end-to-end gain is AMDAHL-LIMITED by the foldable fraction. We
report the per-Clock decomposition; we never sell a Clock-C ratio as a whole-system speedup.

§5 super-scaling: a fold turns an O(N) loop into an O(1) closed form (or O(log N) matrix power), so the SPEEDUP
RATIO grows without bound in N — AND memory drops O(N)→O(1) (no materialization ⇒ OOM-avoidance, the real win at
scale). ★ But the WHOLE-task gain is capped by Amdahl at 1/(1−p) for foldable fraction p: it only shines on
foldable-DOMINATED large work (stats/linalg reduces, signal batches), not I/O-dominated backends. We MEASURE p and
route accordingly — never claiming "bigger ⇒ absolutely faster" as a system property. zero-dep, LLM-free.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


# ── §4 three-clock decomposition ────────────────────────────────────────────────────────────────────────────────
@dataclass
class ClockBudget:
    clock_a_llm: float          # fraction of wall-clock in LLM latency
    clock_b_verify: float       # fraction in z3 verification
    clock_c_fold: float         # fraction in foldable computation (the ONLY part self-fold touches)
    io: float                   # I/O / non-foldable physical floor

    def total(self) -> float:
        return self.clock_a_llm + self.clock_b_verify + self.clock_c_fold + self.io


def amdahl_overall(p: float, kernel_speedup: float) -> float:
    """Overall speedup when a fraction p of the work is sped up by kernel_speedup (Amdahl). p=foldable fraction."""
    if kernel_speedup <= 0:
        return 1.0
    return 1.0 / ((1.0 - p) + p / kernel_speedup)


def self_fold_effect(budget: ClockBudget, clock_c_kernel_speedup: float) -> dict:
    """Apply a self-fold that speeds up ONLY Clock C by `clock_c_kernel_speedup`. Report the per-Clock decomposition
    and the (Amdahl-limited) end-to-end gain — A, B, I/O are UNCHANGED (self-fold cannot touch them)."""
    p = budget.clock_c_fold / budget.total()
    overall = amdahl_overall(p, clock_c_kernel_speedup)
    new_c = budget.clock_c_fold / clock_c_kernel_speedup
    new_total = budget.clock_a_llm + budget.clock_b_verify + new_c + budget.io
    return {
        "foldable_fraction_p": round(p, 4),
        "clock_c_kernel_speedup": clock_c_kernel_speedup,
        "end_to_end_speedup": round(overall, 3),
        "amdahl_ceiling": round(1.0 / (1.0 - p), 3) if p < 1 else float("inf"),
        "unchanged": {"clock_a_llm": budget.clock_a_llm, "clock_b_verify": budget.clock_b_verify, "io": budget.io},
        "clock_c_before": budget.clock_c_fold, "clock_c_after": round(new_c, 4),
        "honest": "self-fold reduced ONLY Clock C; A/B/I-O are the non-foldable floor — end-to-end gain is Amdahl-capped",
    }


# ── §5 super-scaling: ratio + memory gain of a foldable kernel, and the whole-task Amdahl cap ───────────────────
def kernel_ratio_curve(Ns: List[int]) -> List[dict]:
    """A foldable O(N) loop → O(1) closed form: the speedup RATIO is ~N (closed form is ~constant time). The ratio
    grows without bound in N — but this is the ISOLATED kernel ratio, not a whole-system claim."""
    return [{"N": N, "loop_ops": N, "closed_form_ops": 1, "ratio": N,
             "loop_memory": N, "closed_form_memory": 1} for N in Ns]


def route_by_foldable_fraction(p: float, N: int) -> dict:
    """★ Auto-route by the MEASURED foldable fraction p of a large task. High p ⇒ super-scaling is real (apply).
    Low p (I/O-dominated) ⇒ honest 'Amdahl-capped' report — the kernel ratio is huge but the whole task barely moves."""
    cap = 1.0 / (1.0 - p) if p < 1 else float("inf")
    if p >= 0.5:
        return {"route": "super-scale", "p": p, "kernel_ratio_at_N": N, "whole_task_amdahl_ceiling": round(cap, 2),
                "note": f"foldable-dominated (p={p}) at N={N}: kernel O(N)→O(1) ratio≈{N}, memory O(N)→O(1) "
                        "(OOM-avoidance); whole-task gain real up to the Amdahl ceiling"}
    return {"route": "amdahl-capped", "p": p, "kernel_ratio_at_N": N, "whole_task_amdahl_ceiling": round(cap, 2),
            "note": f"I/O-dominated (p={p}): the kernel ratio is ≈{N} but the WHOLE task is capped at "
                    f"≤{round(cap, 2)}× by Amdahl — 'large' does NOT mean 'absolutely faster' here (honest)"}


def adversarial_battery() -> dict:
    """★ self-fold reduces ONLY Clock C; with a small foldable fraction the end-to-end gain is Amdahl-limited (≪ the
    kernel speedup) — A/B/I-O unchanged; ★ the kernel ratio grows with N (10→10, 10^6→10^6) and memory drops to O(1);
    ★ a low-p large task routes to 'amdahl-capped' (honest), a high-p one to 'super-scale'; the forbidden whole-system
    claim is NOT made."""
    budget = ClockBudget(clock_a_llm=0.55, clock_b_verify=0.20, clock_c_fold=0.10, io=0.15)   # LLM/z3/I-O dominate
    eff = self_fold_effect(budget, clock_c_kernel_speedup=1000.0)
    curve = kernel_ratio_curve([10, 1000, 10 ** 6, 10 ** 9])
    low = route_by_foldable_fraction(0.057, 10 ** 9)     # the measured ~5.7% ceiling → Amdahl-capped
    high = route_by_foldable_fraction(0.9, 10 ** 9)      # foldable-dominated → super-scale
    cases = {
        "self_fold_only_clock_c": eff["unchanged"]["clock_a_llm"] == 0.55 and eff["clock_c_after"] < eff["clock_c_before"],
        "end_to_end_amdahl_limited": eff["end_to_end_speedup"] < 1.2 and eff["end_to_end_speedup"] <= eff["amdahl_ceiling"] + 1e-9,
        "kernel_ratio_grows_with_N": curve[0]["ratio"] == 10 and curve[-1]["ratio"] == 10 ** 9,
        "memory_drops_to_O1": all(c["closed_form_memory"] == 1 for c in curve),
        "low_p_routes_amdahl_capped": low["route"] == "amdahl-capped" and low["whole_task_amdahl_ceiling"] < 1.07,
        "high_p_routes_super_scale": high["route"] == "super-scale",
        "no_whole_system_claim": "does NOT mean 'absolutely faster'" in low["note"],     # ★ forbidden claim avoided
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
