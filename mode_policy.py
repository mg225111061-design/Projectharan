"""
v26.2 STAGE 10 — NORMAL/EXTENDED mode-allocation policy (which mathematics, how far).
=====================================================================================
A mode is a DIAL on *how much mathematics to spend*, never a knob on correctness — BOTH modes are
zero-wrong-answer (the difference is depth/coverage, not soundness). This module is the declarative
allocation the pipeline consults; it faithfully encodes the v26.2 directive table.

  NORMAL   = cheap mathematics at full power: prefix-caching / grammar / speculative decoding, interval
             abstract interpretation as the main gate, obvious Σ / C-finite folds, type+property+
             metamorphic gates (TERMINATE here if clean — do NOT call SMT), obvious monoid parallelism,
             cheap (local-aliasing) layout transforms, small best-of-N (1–2), incremental re-verify,
             Clover spec-gate.
  EXTENDED = everything above PLUS the expensive mathematics: octagon/polyhedra, Gosper-Zeilberger /
             Toeplitz / FFT folds, Z3 SMT, Coq unbounded-∀, race-freedom-proved parallelism, deep
             (full-equivalence) layout/SIMD transforms, large best-of-N (4–8).

★ INVARIANTS ★: (1) both modes never emit a wrong answer; (2) the best-of-N SELECTOR is a SOUND
verifier only — NEVER a learned reward model / LLM-judge (raising N with an unsound selector lowers
accuracy via reward hacking, Stroebl et al. arXiv:2411.17501); (3) 2nd+ rounds reuse incremental
re-verification (perceived-zero).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

# technique -> (in NORMAL, in EXTENDED, engine-family). The directive's table, verbatim.
POLICY: Dict[str, Tuple[bool, bool, str]] = {
    "prefix_caching":        (True,  True,  "information-theory"),
    "grammar_constrained":   (True,  True,  "information-theory"),
    "speculative_decoding":  (True,  True,  "information-theory"),
    "interval_abstract":     (True,  True,  "abstract-interpretation"),   # NORMAL main gate / EXTENDED fast pre-pass
    "octagon_polyhedra":     (False, True,  "abstract-interpretation"),
    "cfinite_obvious_fold":  (True,  True,  "complexity"),
    "gosper_toeplitz_fft":   (False, True,  "complexity"),
    "type_property_metamorphic": (True, True, "abstract-interpretation"),  # NORMAL terminates here if clean
    "z3_smt":                (False, True,  "abstract-interpretation"),
    "coq_forall":            (False, True,  "abstract-interpretation"),
    "monoid_parallel":       (True,  True,  "concurrency"),               # obvious associativity
    "racefree_parallel":     (False, True,  "concurrency"),               # needs race-freedom proof (S4)
    "layout_simd_cheap":     (True,  True,  "runtime"),                   # local-aliasing proof
    "layout_simd_deep":      (False, True,  "runtime"),                   # full differential equivalence
    "incremental_reverify":  (True,  True,  "information/concurrency"),
    "clover_spec_gate":      (True,  True,  "all"),                       # FP=0 vacuity gate, always
    "ct_certifier":          (True,  True,  "security"),                  # cheap IR taint, always on
    "taint_ifds":            (True,  True,  "security"),
}

# write→verify→fix loop depth. ★ fast = single shot (fewest iterations) — still SOUNDLY verified; "검증 최소"
# = minimal depth/retries, NOT skipping the sound gate (we never emit unverified code). ★
MODE_BUDGET = {"fast": 1, "normal": 2, "extended": 5}
BEST_OF_N = {"fast": (1, 1), "normal": (1, 2), "extended": (4, 8)}  # selector = SOUND verifier only (never learned reward)


@dataclass
class ModePlan:
    mode: str
    gates: List[str]
    best_of_n: Tuple[int, int]
    loop_budget: int
    sound_selector_only: bool = True   # invariant (2): never a learned reward / LLM-judge
    zero_wrong_answer: bool = True     # invariant (1): both modes


def _idx(mode: str) -> int:
    # fast & normal share the CHEAP (sound) gate column; only extended unlocks the expensive column.
    # "fast" is still SOUNDLY verified — it just spends fewer retries (MODE_BUDGET), never a weaker gate.
    return 1 if mode == "extended" else 0


def should_run(technique: str, mode: str) -> bool:
    t = POLICY.get(technique)
    if t is None:
        return False
    return t[_idx(mode)]


def gates_for(mode: str) -> List[str]:
    """The techniques enabled in `mode`, in declaration order."""
    return [k for k, v in POLICY.items() if v[_idx(mode)]]


def plan(mode: str) -> ModePlan:
    mode = mode if mode in ("fast", "normal", "extended") else "normal"
    return ModePlan(mode=mode, gates=gates_for(mode), best_of_n=BEST_OF_N[mode],
                    loop_budget=MODE_BUDGET[mode])


def progress_stages(mode: str) -> List[str]:
    """Honest progress labels for the SSE UI — only the stages this mode actually runs.
    fast/normal share the cheap-but-SOUND gate set; extended adds the expensive proofs."""
    base = ["classify", "generate", "clover_spec_gate", "type_property_metamorphic", "verify"]
    if mode == "extended":
        base += ["z3_smt", "octagon_polyhedra", "optimize"]
    else:
        base += ["optimize"]
    return base
