"""
PHASE 4.S2 — spec strengthening: mine candidate invariants → Houdini-filter (keep only SOUND) → conjoin.
=======================================================================================================
A weak spec (e.g. `ensures result >= 0`) lets bad implementations pass. We Daikon-style MINE candidate
invariants from execution traces (these are LIKELY/unsound), then Houdini-FILTER them — keep ONLY the ones
the verifier cannot refute (drop any with a counterexample). The surviving sound invariants are conjoined to
strengthen the spec. Mined invariants are NEVER trusted directly — they must survive the filter (§ rule).

★ ENV HONESTY: no Daikon here → a fixed TEMPLATE miner (range / sign / linear & quadratic relations /
divisibility), self-built. The filter (sound, bounded) is what makes mining safe. ★
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Sequence, Tuple

import differential_oracle as DO


# candidate-invariant templates: each is (name, predicate(n, result) -> bool)
def _templates() -> List[Tuple[str, Callable[[int, int], bool]]]:
    return [
        ("result >= 0", lambda n, r: r >= 0),
        ("result >= n", lambda n, r: r >= n),
        ("result <= n*n", lambda n, r: r <= n * n),
        ("2*result == n*(n+1)", lambda n, r: 2 * r == n * (n + 1)),     # the exact relation for Σk
        ("result == n*n", lambda n, r: r == n * n),                     # a WRONG candidate (Σk² closed-ish)
        ("result % 2 == 0", lambda n, r: r % 2 == 0),                   # wrong in general
        ("result <= n*(n+1)", lambda n, r: r <= n * (n + 1)),
    ]


@dataclass
class StrengthenResult:
    mined: List[str]
    sound: List[str]            # survived Houdini filter
    dropped: List[str]          # mined-but-unsound (filtered out)
    mutation_before: float
    mutation_after: float

    @property
    def improved(self) -> bool:
        return self.mutation_after > self.mutation_before


def mine_and_filter(fn: Callable[[int], int], arg_kind: str = "nat",
                    seed: int = 1, trials: int = 400) -> Tuple[List[str], List[str], List[str]]:
    """Mine template invariants from traces of `fn`, then HOUDINI-FILTER: keep only those holding on ALL
    sampled inputs (drop any with a counterexample). Returns (mined, sound, dropped)."""
    rng = random.Random(seed)
    ns = [a[0] for a in DO._product_sample((arg_kind,), rng, cap=trials)]
    ns = [n for n in ns if n >= 1]
    mined = [name for name, _ in _templates()]
    sound, dropped = [], []
    for name, pred in _templates():
        holds = all(pred(n, fn(n)) for n in ns)        # bounded soundness check (the filter)
        (sound if holds else dropped).append(name)
    return mined, sound, dropped


def _post_from_invariants(invs: List[str]) -> Callable[[int, int], bool]:
    """Build a postcondition that is the CONJUNCTION of the named invariants."""
    table = dict(_templates())
    preds = [table[name] for name in invs if name in table]
    return lambda n, r: all(p(n, r) for p in preds)


def strengthen(fn: Callable[[int], int], weak_invariants: List[str], mutants: List[Callable[[int], int]],
               arg_kind: str = "nat") -> StrengthenResult:
    """Strengthen a weak spec: mine+filter sound invariants, conjoin them, and measure the mutation-kill
    BEFORE (weak) vs AFTER (strengthened)."""
    import spec_strength_gate as SG
    mined, sound, dropped = mine_and_filter(fn, arg_kind)
    weak_post = _post_from_invariants(weak_invariants)
    strong_post = _post_from_invariants(sorted(set(weak_invariants) | set(sound)))
    before = SG.mutation_score(lambda n, r: weak_post(n, r), mutants, (arg_kind,))
    after = SG.mutation_score(lambda n, r: strong_post(n, r), mutants, (arg_kind,))
    return StrengthenResult(mined, sound, dropped, before, after)
