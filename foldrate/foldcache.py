"""
§AA WEAPON 4 — MEMOIZATION CACHE EXTENSION (raise fold VALUE, not rate).
================================================================================================================
Extends §V's sound cache to the fold pipeline itself: a fold proved ONCE, then served O(1) on re-encounter. Three
sound caches — fold RESULTS (a loop's proved closed form), PROOF obligations (a z3 query's result), and CANONICAL forms
(WEAPON 1's output). The same proof is paid once and looked up forever.

★ SOUND KEYS (precision 1.0): keys are §V's `canonical_ast_key` (α-normalized AST hash — α-equivalent code shares the
entry, proved result-equivalent) or `content_key` (sha256 of bytes). A wrong hit is IMPOSSIBLE: different code ⇒
different key. Two loops sharing an entry are α-equivalent (hence result-equivalent) — never a collision.
★ COLD vs WARM (per §V, reported separately): cold (first encounter) gives ZERO — every fold computed in full; the win
is on WARM re-encounters (O(1) lookup). This raises VALUE / throughput, NOT the fold rate — a fold cached is still one
fold, counted once. We state this distinction honestly (it is §V's discipline).
LLM-free (hashing + lookup are deterministic). No new certificate kind (caches the existing folds/proofs/forms).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple

import enginespeed.cache as C


def _key(code: str) -> str:
    """Sound key: prefer the α-normalized canonical-AST key (α-equivalent code shares, soundly); fall back to the
    content hash for non-parsing fragments. Never a guessed key."""
    return C.canonical_ast_key(code) or C.content_key(code)


class FoldCache:
    """Three §V SoundCaches over the fold pipeline. get-or-compute on a SOUND key; a wrong hit is impossible."""
    def __init__(self):
        self.fold_results = C.SoundCache("fold_results")
        self.proof_obligations = C.SoundCache("proof_obligations")
        self.canonical_forms = C.SoundCache("canonical_forms")

    def fold(self, code: str, fold_fn: Callable[[str], Any]) -> Any:
        """Cache a fold RESULT under the sound key. Cold: compute fold_fn(code) once. Warm: O(1) lookup."""
        return self.fold_results.get_or_compute(_key(code), lambda: fold_fn(code))

    def prove(self, obligation: str, prove_fn: Callable[[], bool]) -> bool:
        """Cache a PROOF obligation's result under its content key (the obligation text is the identity)."""
        return self.proof_obligations.get_or_compute(C.content_key("oblig", obligation), prove_fn)

    def canonicalize(self, code: str, canon_fn: Callable[[str], Any]) -> Any:
        """Cache a CANONICAL form (WEAPON 1's output) under the sound key."""
        return self.canonical_forms.get_or_compute(_key(code), lambda: canon_fn(code))


def cold_warm_measurement() -> dict:
    """Measure cold (first, computed in full) vs warm (re-encounter, O(1)) on the fold cache. The fold_fn counts its
    real invocations; cold pays them all, warm pays none. ★ Value/throughput, NOT fold rate."""
    fc = FoldCache()
    calls = {"n": 0}

    def expensive_fold(code: str):
        calls["n"] += 1                                         # the real (cold) work
        return f"closed_form_of({code.strip()})"

    code = "def f(a):\n    s = 0\n    for i in range(a):\n        s += i\n    return s\n"
    # cold: first encounter computes
    _ = fc.fold(code, expensive_fold)
    cold_calls = calls["n"]
    # warm: 99 re-encounters of the SAME fold ⇒ O(1) hits, no recompute
    for _ in range(99):
        _ = fc.fold(code, expensive_fold)
    warm_calls = calls["n"] - cold_calls
    return {
        "encounters": 100, "cold_computes": cold_calls, "warm_recomputes": warm_calls,
        "hit_rate": fc.fold_results.stats.hit_rate,
        "raises": "value/throughput (the same fold served O(1)), NOT the fold rate — one fold counted once",
        "cold_gives_zero": cold_calls == 1, "warm_gives_win": warm_calls == 0,
    }


def sound_key_check() -> dict:
    """★ α-equivalent code SHARES the entry (sound — same function, same fold); DIFFERENT code gets a DIFFERENT key
    (no wrong hit). Demonstrates a wrong hit is impossible."""
    fc = FoldCache()
    folds = {"n": 0}

    def fold_fn(code: str):
        folds["n"] += 1
        return f"fold#{folds['n']}"

    a = "def f(a):\n    return a + 1\n"
    a_alpha = "def g(b):\n    return b + 1\n"               # α-equivalent to a (renamed) ⇒ SAME canonical key
    different = "def f(a):\n    return a + 2\n"             # different constant ⇒ DIFFERENT key
    r_a = fc.fold(a, fold_fn)
    r_alpha = fc.fold(a_alpha, fold_fn)                     # should HIT a's entry (α-equivalent)
    r_diff = fc.fold(different, fold_fn)                    # should MISS (different code)
    return {
        "alpha_equivalent_shares": _key(a) == _key(a_alpha) and r_a == r_alpha,   # sound share, 1 compute for both
        "different_code_distinct": _key(a) != _key(different) and r_diff != r_a,   # no wrong hit
        "total_computes": folds["n"],                       # 2 (a/alpha share one, different is the second)
    }


def adversarial_battery() -> dict:
    """Cold gives zero / warm gives the win (value not rate); ★ α-equivalent code shares soundly (1 compute); ★ a wrong
    hit is impossible — different code gets a different key (no collision); the cache raises value, not the fold rate."""
    cw = cold_warm_measurement()
    sk = sound_key_check()
    cases = {
        "cold_gives_zero": cw["cold_gives_zero"],
        "warm_gives_win": cw["warm_gives_win"],
        "high_warm_hit_rate": cw["hit_rate"] >= 0.98,
        "alpha_equivalent_shares_soundly": sk["alpha_equivalent_shares"] and sk["total_computes"] == 2,
        "wrong_hit_impossible": sk["different_code_distinct"],
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
