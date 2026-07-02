"""
Pillar 3 · ROUND 2 #41 — speculative execution + rollback (waiting-elimination; PROBABILISTIC, report δ).
=========================================================================================================
NOT caching. Speculation BETS ON THE FUTURE: during idle time it precomputes the PREDICTED next query's answer,
so when that query actually arrives its latency is already hidden. On a HIT the result is served with the
expensive compute already done (latency-critical work avoided); on a MISS (misspeculation) it rolls back and
computes on demand — a wasted bet. This trades MORE total work (the speculative precomputes) for LESS
latency-critical work, and is honest: it REPORTS the misspeculation rate δ (a PROBABILISTIC win, never EXACT).
A poor predictor (random stream) hides little latency and wastes the bets ⇒ DECLINE.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

import kernel_verdict as KV


@dataclass
class SpecResult:
    verdict: "KV.Verdict"
    hit_rate: float
    delta: float                 # misspeculation rate
    latency_critical_compute: int
    naive_compute: int


def speculative_serve(queries: List, predict: Callable, compute: Callable):
    """Serve a query stream with speculation. `predict(prev)` guesses the next query (precomputed during idle);
    `compute(q)` is the expensive op. Returns (results, hits, misses, latency_critical_computes)."""
    results = []
    speculated_q = None
    speculated_ans = None
    hits = misses = latency_compute = 0
    prev = None
    for q in queries:
        if speculated_q == q:                              # HIT — the bet paid off, latency already hidden
            results.append(speculated_ans)
            hits += 1
        else:                                              # MISS — roll back, compute on demand (latency-critical)
            results.append(compute(q))
            latency_compute += 1
            misses += 1
        prev = q
        speculated_q = predict(prev)                       # bet on the next query (precomputed in the idle slot)
        speculated_ans = compute(speculated_q) if speculated_q is not None else None
    return results, hits, misses, latency_compute


def speculation_grade(queries: List, predict: Callable, compute: Callable, *, delta_target: float = 0.4) -> SpecResult:
    """PROBABILISTIC: hides latency on the HIT fraction; δ = misspeculation (miss) rate. Correctness is checked
    (speculative results must equal the on-demand results). A poor predictor (δ too high / no latency hidden) ⇒
    DECLINE — the bet isn't worth it."""
    spec_results, hits, misses, latency_compute = speculative_serve(queries, predict, compute)
    on_demand = [compute(q) for q in queries]
    if spec_results != on_demand:                          # speculation must NEVER change the answer
        return SpecResult(KV.decline("speculation produced a wrong result (rollback unsound) ⇒ DECLINE", "speculate"),
                          0.0, 1.0, latency_compute, len(queries))
    total = max(1, len(queries))
    delta = misses / total                                 # misspeculation rate
    hit_rate = hits / total
    if delta > delta_target:
        return SpecResult(KV.decline(f"misspeculation δ={delta:.2f} > {delta_target} — bet not worth it ⇒ DECLINE",
                                     "speculate"), hit_rate, delta, latency_compute, len(queries))
    cert = KV.Cert(KV.PROBABILISTIC, "speculative_execution", passed=True, check_cost=f"{len(queries)} queries",
                   delta=max(delta, 1e-6), detail=f"latency hidden on {hit_rate:.0%} of queries (δ={delta:.3f} "
                                                  f"misspeculation); latency-critical compute {len(queries)}→{latency_compute}")
    return SpecResult(KV.probabilistic(spec_results, "speculate", f"latency-critical {latency_compute}/{len(queries)}", cert),
                      hit_rate, delta, latency_compute, len(queries))


# ── a predictable stream (sequential access — speculation wins) and a random one (speculation loses) ─────
def _expensive(q):
    x = 0
    for i in range(50):
        x = (x * 1103515245 + q + i) & 0x7FFFFFFF
    return x


def make_predictable(n: int = 2000, noise: float = 0.15):
    import random as _rnd
    rng = _rnd.Random(71)
    qs = []
    cur = 0
    for _ in range(n):
        qs.append(cur)
        cur = cur + 1 if rng.random() > noise else rng.randrange(1000)   # mostly sequential (+1), some jumps
    return qs


def make_random(n: int = 2000):
    import random as _rnd
    rng = _rnd.Random(72)
    return [rng.randrange(1000) for _ in range(n)]


def predict_next(prev):
    return None if prev is None else prev + 1              # bet: the next query is the sequential successor
