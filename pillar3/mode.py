"""
Pillar 3 · PHASE M — MODE SEPARATION: fast / normal / extend (the spine of the whole engine).
==============================================================================================
The three modes are not speed presets. They are three different **contracts** about what the system is willing
to do and what it refuses. A reader of this file can state, for any input, exactly what each mode will and will
not do — every row of the contract is encoded in `ModePolicy`, and the engine consults it (it does not
hard-code behaviour). Detector-gating, verifier-tier-gating, and grade-floor-gating all flow from here.

──────────────────────────────────────────────────────────────────────────────────────────────────────────
THE PHILOSOPHY OF EACH MODE
──────────────────────────────────────────────────────────────────────────────────────────────────────────
fast — "give me one safe win, right now, and never make me wait."
    fast optimises Clock A (felt speed). It is the mode for an editor save-hook or a tight CI gate. It refuses
    anything that could block: no Z3, no multi-size sweep, no exhaustive search. It takes the cheapest, most
    obvious, highest-confidence win and returns. It accepts PROBABILISTIC grades because a fast likely-win
    beats a slow certain-win *in this mode's contract*. fast would rather miss a big win than make you wait or
    risk a slow verifier. Its acceptable failure is "left speedup on the table"; its forbidden failure is
    "blocked the developer" — never.

normal — "compound real wins until it stops being worth it."
    normal optimises the balance of A/B/C — the default for a PR-time pass. It iterates profile→fix→verify→
    reprofile, compounding measured wins down the flame graph, using certificates where they are cheap and
    differential testing otherwise. It stops at diminishing returns (<10% marginal). normal would rather take
    ten verified medium wins than one unverified huge one. Its contract: every shipped fix is either EXACT or a
    well-tested PROBABILISTIC with a real measured whole-program gain.

extend — "find every reachable win, prove it, and I'll wait as long as it takes."
    extend optimises Clock C (emitted speed) and sacrifices Clock A entirely — the overnight mode for a hot
    service. It runs the full multi-size complexity sweep, algorithm recognition, verified lifting, egg
    superoptimisation, GPU/SIMD offload, and cross-cutting global transforms. It uses full Z3/SMT equivalence
    and is EXACT-or-DECLINE: it ships nothing it cannot prove. extend would rather DECLINE a real 1000× win
    than ship it on differential evidence alone. Its contract is the strongest — every shipped fix carries a
    machine-checked equivalence certificate. This is where the moat lives: the bigger the change, the more the
    proof is worth, and extend is the mode that always pays for the proof.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import FrozenSet, Optional

import kernel_verdict as KV
from pillar3.verifier import VerifierTier


class Mode(enum.Enum):
    FAST = "fast"
    NORMAL = "normal"
    EXTEND = "extend"


# ── the detector registry, grouped by the mode tier that first enables it (M.2 "detector set" row) ─────
# fast: cheap structural only. normal: + structural/data-representation. extend: + heavy/algorithmic.
FAST_DETECTORS: FrozenSet[str] = frozenset({
    "list_as_set", "memoize", "uncached_recompute", "n_plus_1", "repeated_parse",
    # D1 catastrophic single-bug detectors are fast-eligible too
    "redos_regex", "redundant_io_parse", "accidental_full_scan", "quadratic_build", "redundant_sort",
    # D4 (PHASE ∞)
    "regex_compile_in_loop",
    # D5 (PHASE ∞)
    "membership_to_set_param",
})
NORMAL_ONLY_DETECTORS: FrozenSet[str] = frozenset({
    "accidental_quadratic", "serialization", "caching", "dict_to_columnar", "copy_elim",
    "loop_invariant_hoist", "materialize_to_lazy", "deep_n_plus_1",
    # D4 (PHASE ∞)
    "nested_loop_join", "sum_genexpr", "manual_groupby",
})
EXTEND_ONLY_DETECTORS: FrozenSet[str] = frozenset({
    "algorithm_recognition", "verified_lifting", "egg_superopt", "egg_algebraic", "gpu_simd_offload",
    "simd_offload", "vectorizable_loop", "parallelization", "parallelizable_loop", "global_transforms",
    "incremental_recompute", "interproc_memoize",
    # D5 (PHASE ∞)
    "power_strength_reduction",
})

NORMAL_DETECTORS: FrozenSet[str] = FAST_DETECTORS | NORMAL_ONLY_DETECTORS
EXTEND_DETECTORS: FrozenSet[str] = NORMAL_DETECTORS | EXTEND_ONLY_DETECTORS


@dataclass(frozen=True)
class ModePolicy:
    """Every row of the M.2 contract, encoded and enforced. The engine reads these fields; it never decides
    behaviour on its own. A detector not in `enabled_detectors` does not fire; a verifier tier above
    `verifier_tier` is not invoked; a grade not in `acceptable_grades` is DECLINEd (never shipped)."""
    mode: Mode
    primary_clock: str                      # which clock this mode optimises (A felt / balance / C emitted)
    enabled_detectors: FrozenSet[str]       # exactly which detectors may fire
    verifier_tier: VerifierTier             # the highest verifier rung this mode may invoke
    runs_complexity_sweep: bool             # multi-size power-law sweep?
    max_hotspots: Optional[int]             # attack the top-k hotspots only (None = entire profile)
    max_iterations: int                     # compounding rounds cap
    acceptable_grades: FrozenSet[str]       # which shipped grades are allowed (the grade floor)
    stop_condition: str                     # human-readable stop rule
    marginal_floor: float                   # stop when the next marginal whole-program gain drops below this
    latency_budget_s: Optional[float]       # soft latency budget (None = unbounded / overnight)
    risk_posture: str
    deep_search: bool                       # extend searches deeply over candidate fixes
    stop_on_first_win: bool                 # fast: return after the first accepted win
    samples: int = 5                        # measurement samples (fast cheap, extend can afford more)

    def detector_enabled(self, name: str) -> bool:
        return name in self.enabled_detectors

    def grade_acceptable(self, grade: str) -> bool:
        return grade in self.acceptable_grades

    @staticmethod
    def for_mode(mode: "Mode") -> "ModePolicy":
        return _POLICIES[mode]


# ── the three canonical policies (the contract table, made executable) ─────────────────────────────────
_POLICIES = {
    Mode.FAST: ModePolicy(
        mode=Mode.FAST,
        primary_clock="A (felt speed)",
        enabled_detectors=FAST_DETECTORS,
        verifier_tier=VerifierTier.MICRO,            # NEVER invokes Z3
        runs_complexity_sweep=False,                 # single size only
        max_hotspots=3,                              # top 1–3 only
        max_iterations=1,                            # single pass
        acceptable_grades=frozenset({KV.EXACT, KV.PROBABILISTIC}),
        stop_condition="first accepted win",
        marginal_floor=0.0,
        latency_budget_s=1.0,                        # sub-second target
        risk_posture="miss-a-win OK; block-the-dev NEVER",
        deep_search=False,
        stop_on_first_win=True,
        samples=3,
    ),
    Mode.NORMAL: ModePolicy(
        mode=Mode.NORMAL,
        primary_clock="balance A/B/C",
        enabled_detectors=NORMAL_DETECTORS,
        verifier_tier=VerifierTier.CHEAP_CERT,       # differential + small-region Z3
        runs_complexity_sweep=False,                 # optional/cheap — off by default in the canonical run
        max_hotspots=None,                           # iterate down the flame graph
        max_iterations=12,
        acceptable_grades=frozenset({KV.EXACT, KV.PROBABILISTIC}),
        stop_condition="next marginal whole-program gain < 10%",
        marginal_floor=0.10,
        latency_budget_s=30.0,                       # moderate
        risk_posture="balanced",
        deep_search=False,
        stop_on_first_win=False,
        samples=5,
    ),
    Mode.EXTEND: ModePolicy(
        mode=Mode.EXTEND,
        primary_clock="C (emitted speed); A sacrificed",
        enabled_detectors=EXTEND_DETECTORS,
        verifier_tier=VerifierTier.FULL_CERT,        # full Z3/SMT on every algorithm swap
        runs_complexity_sweep=True,                  # always, multi-size
        max_hotspots=None,                           # entire profile
        max_iterations=64,
        acceptable_grades=frozenset({KV.EXACT}),     # ★ EXACT-or-DECLINE — PROBABILISTIC-only fixes REJECTED ★
        stop_condition="every enabled detector tried; floor or Clock-B budget reached",
        marginal_floor=0.0,                          # do not stop early — find every reachable win
        latency_budget_s=None,                       # unbounded / overnight
        risk_posture="DECLINE-a-real-win OK; ship-unproven NEVER",
        deep_search=True,
        stop_on_first_win=False,
        samples=5,
    ),
}
