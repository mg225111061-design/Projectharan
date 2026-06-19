"""
PHASE 4.S1 — spec-strength gate: a PROVEN against a WEAK spec is worthless. Reject vacuity, demand mutation-kill.
================================================================================================================
"PROVEN" is only meaningful if the SPEC is strong. Two automatic gates before we ever say PROVEN:
  (a) VACUITY — if the postcondition is satisfied by an ARBITRARY output (it does not pin the result), the
      spec is vacuous (implementation-independent) ⇒ REJECT. e.g. `ensures result = result`.
  (b) MUTATION — the spec, used as the verifier, must KILL known-bad mutant implementations (each mutant must
      VIOLATE the postcondition). A spec that lets a mutant pass is too weak ⇒ FLAG.

Bounded-concrete (sound on the sampled domain; a wider domain only strengthens). Extends spec_gate.py/Clover.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Sequence, Tuple

import differential_oracle as DO   # reuse the input generators


@dataclass
class StrengthResult:
    verdict: str                # PASS | REJECT_VACUOUS | FLAG_WEAK
    vacuity_rate: float         # fraction of random outputs the postcondition wrongly accepts (high ⇒ vacuous)
    mutation_score: float       # fraction of mutants the spec KILLS (1.0 ⇒ strong)
    detail: str = ""

    @property
    def strong(self) -> bool:
        return self.verdict == "PASS"


def vacuity_rate(post: Callable, arg_kinds: Sequence[str], out_range=(-1000, 1000),
                 seed: int = 1, trials: int = 400) -> float:
    """Fraction of (inputs, RANDOM output) pairs the postcondition accepts. ~1.0 ⇒ the spec does not constrain
    the output (vacuous); low ⇒ the spec genuinely pins the result."""
    rng = random.Random(seed)
    inputs = DO._product_sample(arg_kinds, rng, cap=trials)
    accept = 0
    for args in inputs:
        out = rng.randint(*out_range)
        try:
            if post(*args, out):
                accept += 1
        except Exception:  # noqa: BLE001
            pass
    return round(accept / max(1, len(inputs)), 3)


def mutation_score(post: Callable, mutants: List[Callable], arg_kinds: Sequence[str],
                   seed: int = 2, trials: int = 300) -> float:
    """Fraction of mutant implementations the spec KILLS (the mutant's output VIOLATES the postcondition on
    some input). 1.0 ⇒ the spec is strong enough to reject every known-bad mutant."""
    rng = random.Random(seed)
    inputs = DO._product_sample(arg_kinds, rng, cap=trials)
    killed = 0
    for mut in mutants:
        is_killed = False
        for args in inputs:
            try:
                if not post(*args, mut(*args)):       # postcondition fails on the mutant ⇒ killed
                    is_killed = True
                    break
            except Exception:  # noqa: BLE001
                is_killed = True
                break
        killed += int(is_killed)
    return round(killed / max(1, len(mutants)), 3)


def gate(post: Callable, arg_kinds: Sequence[str], mutants: List[Callable],
         vacuity_threshold: float = 0.5) -> StrengthResult:
    """Reject vacuous specs (accept arbitrary outputs too often), FLAG specs that miss a mutant; else PASS."""
    vr = vacuity_rate(post, arg_kinds)
    if vr >= vacuity_threshold:
        return StrengthResult("REJECT_VACUOUS", vr, 0.0,
                              f"postcondition accepts arbitrary outputs {vr:.0%} of the time — vacuous, REJECTED")
    ms = mutation_score(post, mutants, arg_kinds)
    if ms < 1.0:
        return StrengthResult("FLAG_WEAK", vr, ms, f"spec killed only {ms:.0%} of mutants — too weak, FLAGGED")
    return StrengthResult("PASS", vr, ms, f"non-vacuous (accepts arbitrary {vr:.0%}) and kills 100% of mutants")
