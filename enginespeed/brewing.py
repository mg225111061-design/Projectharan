"""
§V PHASE 4 — PARALLEL BREWING + PREFETCH: fill the caches ahead of need (sound, never speculative-wrong).
================================================================================================================
Use idle time and look-ahead to warm the caches before the work arrives. ★ Brewing only pre-computes results that
will be CORRECT — it is just doing the real computation early, so its results are exactly as sound as on-demand
(never a guessed result that could be wrong). Prefetch only warms entries that WILL be looked up.

Here brewing runs synchronously (real parallel/idle scheduling is a deployment concern); the correctness property is
identical — a brewed entry is the real recompute value, so a later lookup is a sound hit. We measure how many later
lookups land warm BECAUSE of brewing.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from enginespeed.folded_ops import FoldedEngine
from enginespeed.cache import content_key


@dataclass
class BrewResult:
    brewed: int                         # entries pre-computed
    later_hits: int                     # later lookups that landed warm because of brewing
    detail: str = ""


def brew_common_verifications(eng: FoldedEngine, common_pairs: List[tuple]) -> int:
    """Pre-compute (brew) the engine's common verification obligations during idle time, so they are warm when the
    live workload hits them. Each brewed result is the real z3 proof — sound, just computed early."""
    for a, b in common_pairs:
        eng.verify(a, b)                                    # real computation, stored — a later identical verify is a hit
    return len(common_pairs)


def brew_patterns(eng: FoldedEngine, fold_srcs: List[str], compute_fold: Callable[[str], object]) -> int:
    """Pre-fold common code patterns in idle time (the offline pre-proving, generalized to detection/fold/AST)."""
    for src in fold_srcs:
        eng.fold(src, compute_fold)
    return len(fold_srcs)


def prefetch(eng: FoldedEngine, next_pairs: List[tuple]) -> BrewResult:
    """Critical-path prefetch: warm the entries the next pass will need, overlapping the warming with current work.
    Then measure how many of those next lookups land warm (the prefetch payoff). Sound: only real, needed entries."""
    before_hits = eng.c.L2.stats.hits
    for a, b in next_pairs:
        eng.verify(a, b)                                    # warm ahead
    warmed = len(next_pairs)
    # the next pass: the SAME pairs are now hits
    h0 = eng.c.L2.stats.hits
    for a, b in next_pairs:
        eng.verify(a, b)
    later_hits = eng.c.L2.stats.hits - h0
    return BrewResult(warmed, later_hits, f"prefetched {warmed} entries; the next pass hit {later_hits} warm "
                      "(sound — every prefetched entry is the real recompute value, never a guess)")
