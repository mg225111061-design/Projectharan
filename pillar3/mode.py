"""
Pillar 3 · PHASE M — MODE SEPARATION: normal / extend (2-tier; the spine of the whole engine).
================================================================================================
The two modes are not speed presets. They are two different **contracts** about what the system is willing
to do and what it refuses. A reader of this file can state, for any input, exactly what each mode will and will
not do — every row of the contract is encoded in `ModePolicy`, and the engine consults it (it does not
hard-code behaviour). Detector-gating, verifier-tier-gating, and grade-floor-gating all flow from here.

★ ARCHITECTURE-TRANSITION NOTE ★: a third mode, `fast`, used to exist as its own user-selectable tier ("give me
one safe win, right now, never make me wait" — cheap detectors only, no Z3, PROBABILISTIC accepted for speed).
It has been RETIRED as a tier. Its one load-bearing behaviour — returning an instant, already-certified win
before paying for the heavy solver — was not lost: it is absorbed into `normal`'s own internal early-exit (see
`EARLY_EXIT_DETECTORS` below and its pre-pass in `pillar3.engine.optimize`), with the grade floor made STRICTER,
not looser — the early-exit only ever returns an EXACT, by-construction-certified win; the old
"PROBABILISTIC-for-speed" allowance retired along with the tier. If no such instant win exists, `normal` falls
through to exactly its previous full behaviour, unchanged.

──────────────────────────────────────────────────────────────────────────────────────────────────────────
THE PHILOSOPHY OF EACH MODE
──────────────────────────────────────────────────────────────────────────────────────────────────────────
normal — "return an instant certified win if one is free; otherwise compound real wins until it stops being
worth it."
    normal FIRST tries an internal early-exit over the cheapest, most obvious detectors only (no Z3), and
    returns immediately the moment one of them proves an EXACT, by-construction win — never a speculative
    PROBABILISTIC one, and never at the cost of reaching the heavy solver. This is the instant-win behaviour
    that used to be a separate `fast` tier; it is now just normal's first move, not a different contract. If
    nothing qualifies, normal falls through to its full behaviour: optimising the balance of A/B/C, the default
    for a PR-time pass. It iterates profile→fix→verify→reprofile, compounding measured wins down the flame
    graph, using certificates where they are cheap and differential testing otherwise. It stops at diminishing
    returns (<10% marginal). normal would rather take ten verified medium wins than one unverified huge one.
    Its contract: every shipped fix is either EXACT or a well-tested PROBABILISTIC with a real measured
    whole-program gain.

extend — "find every reachable win, prove it — within a BOUNDED ~8-minute budget, then return the best proven."
    extend optimises Clock C (emitted speed) and sacrifices Clock A — but it is NOT unlimited. It runs the full
    multi-size complexity sweep, algorithm recognition, verified lifting, egg superoptimisation, GPU/SIMD offload,
    and cross-cutting global transforms under a HARD ~8-minute (480 s) wall-clock budget. It uses full Z3/SMT
    equivalence and is EXACT-or-DECLINE: it ships nothing it cannot prove. extend would rather DECLINE a real
    1000× win than ship it on differential evidence alone. Its contract is the strongest — every shipped fix
    carries a machine-checked equivalence certificate. When the 8-minute budget is spent it returns the BEST
    CERTIFIED result reached so far, or an honest partial ("couldn't close within the extend budget — here is what
    is proven + what remains"). It NEVER runs past the budget, NEVER fakes a result to fill the time, and NEVER
    weakens a grade to go faster. This is where the moat lives: the bigger the change, the more the proof is worth
    — and extend pays for the proof until the budget runs out, then stops honestly. extend never uses the
    early-exit above — it deliberately explores everything within its budget.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import FrozenSet, Optional

import kernel_verdict as KV
from pillar3.verifier import VerifierTier


class Mode(enum.Enum):
    NORMAL = "normal"
    EXTEND = "extend"


# ── the detector registry, grouped by the mode tier that first enables it (M.2 "detector set" row) ─────
# early-exit: cheap structural only (formerly the separate "fast" tier's detector set) — normal tries these
# FIRST, EXACT-only, before falling through to its full detector set below. normal (full): + structural/
# data-representation. extend: + heavy/algorithmic.
EARLY_EXIT_DETECTORS: FrozenSet[str] = frozenset({
    "list_as_set", "memoize", "uncached_recompute", "n_plus_1", "repeated_parse",
    # D1 catastrophic single-bug detectors are early-exit-eligible too
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
    # D6 (PHASE ∞)
    "list_pop_zero", "exception_control_flow",
    # D7 (PHASE ∞)
    "sorted_min_max", "count_in_loop",
})
EXTEND_ONLY_DETECTORS: FrozenSet[str] = frozenset({
    "algorithm_recognition", "verified_lifting", "egg_superopt", "egg_algebraic", "gpu_simd_offload",
    "simd_offload", "vectorizable_loop", "parallelization", "parallelizable_loop", "global_transforms",
    "incremental_recompute", "interproc_memoize",
    # D5 (PHASE ∞)
    "power_strength_reduction",
})

NORMAL_DETECTORS: FrozenSet[str] = EARLY_EXIT_DETECTORS | NORMAL_ONLY_DETECTORS
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
    latency_budget_s: Optional[float]       # TOTAL wall-clock budget per run — ENFORCED (normal ~30s / extend
                                            # ~8min BOUNDED); none hangs past it (mode_budget.run_under_mode_budget)
    risk_posture: str
    deep_search: bool                       # extend searches deeply over candidate fixes
    stop_on_first_win: bool                 # vestigial (was fast-only); both remaining modes set this False —
                                            # normal's own early-exit pre-pass (pillar3.engine.optimize) is separate
    samples: int = 5                        # measurement samples (extend can afford more)
    min_rounds_before_diminishing: int = 0  # "compound" needs ≥N wins before diminishing-returns can stop it

    def detector_enabled(self, name: str) -> bool:
        return name in self.enabled_detectors

    def grade_acceptable(self, grade: str) -> bool:
        return grade in self.acceptable_grades

    @staticmethod
    def for_mode(mode: "Mode") -> "ModePolicy":
        return _POLICIES[mode]


# ── the two canonical policies (the contract table, made executable) ─────────────────────────────────
_POLICIES = {
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
        min_rounds_before_diminishing=2,             # "compound real wins" — ship ≥2 before stopping on marginal
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
        stop_condition="every enabled detector tried, OR the ~8-min extend budget is spent — then return the "
                       "best CERTIFIED result reached (or an honest partial); never past budget, never faked",
        marginal_floor=0.0,                          # do not stop early — find every reachable win within budget
        latency_budget_s=480.0,                      # ★ BOUNDED ~8 min — NOT unlimited; best-proven-within-budget ★
        risk_posture="DECLINE-a-real-win OK; ship-unproven NEVER; run-past-budget NEVER",
        deep_search=True,
        stop_on_first_win=False,
        samples=5,
    ),
}
