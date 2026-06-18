"""
STAGE 1 — Clock A (LLM call): parallel best-of-N with first-pass early-exit.
=============================================================================
★ THREE CLOCKS — never mixed ★. This module is ENTIRELY Clock A (the LLM-call clock). It does NOT verify
faster (Clock B) or run code faster (Clock C); it shrinks wall-clock by generating N candidates CONCURRENTLY
and returning the moment a SOUND verifier accepts one — cancelling the rest. So wall-clock ≈ max(candidate
latency), not the sum.

  • candidates launched concurrently (asyncio) — never sequential.
  • a SOUND, deterministic verifier accepts the FIRST passing candidate → early-exit, losers cancelled.
  • mode → N:  Fast N=1 · Normal N=3 · Extend N=6  (more shots = higher success prob, same wall-clock).

★ HONEST (rule 2) ★: hosted APIs (z.ai/Claude) do NOT allow speculative decoding — we never claim it. The
real LLM per-call latency needs a key + egress → [BLOCKED] here. What is genuinely MEASURED is the
ORCHESTRATION: with controlled/simulated per-candidate latencies, parallel+early-exit wall-clock vs the
sequential baseline (sum-until-pass). The win is "sum → max", reported with p (per-candidate success prob)
and N. No fabricated millisecond figures.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable, List, Optional

# mode → number of concurrent candidates (rule 1.3)
MODE_N = {"fast": 1, "normal": 3, "extend": 6}


@dataclass
class BestOfNResult:
    winner: Optional[str]
    n: int
    accepted_index: int = -1
    wall_ms: float = 0.0            # [Clock A] real wall-clock of the parallel+early-exit run
    cancelled: int = 0              # losing candidates cancelled at early-exit
    verified: bool = False


async def best_of_n(n: int, gen_async: Callable[[int], Awaitable[str]],
                    verify: Callable[[str], bool]) -> BestOfNResult:
    """Launch `n` candidate generations CONCURRENTLY; verify each as it lands; return the FIRST that the
    (sound) verifier accepts and cancel the rest. Wall-clock ≈ the winner's latency, not the sum."""
    t0 = time.perf_counter()
    tasks = [asyncio.create_task(gen_async(i)) for i in range(n)]
    idx = {t: i for i, t in enumerate(tasks)}
    winner, accepted = None, -1
    pending = set(tasks)
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for d in sorted(done, key=lambda t: idx[t]):       # deterministic order among same-tick completions
            try:
                cand = d.result()
            except asyncio.CancelledError:
                continue
            if verify(cand):                                # ★ sound verifier — first PASS wins ★
                winner, accepted = cand, idx[d]
                break
        if winner is not None:
            break
    cancelled = 0
    for t in tasks:                                         # early-exit: cancel the losers
        if not t.done():
            t.cancel(); cancelled += 1
    await asyncio.gather(*tasks, return_exceptions=True)
    return BestOfNResult(winner=winner, n=n, accepted_index=accepted,
                         wall_ms=(time.perf_counter() - t0) * 1000, cancelled=cancelled,
                         verified=winner is not None)


async def _sequential_baseline(n: int, gen_async: Callable[[int], Awaitable[str]],
                               verify: Callable[[str], bool]) -> float:
    """Baseline for the A/B: try candidates ONE AT A TIME (await, verify, next) until one passes — the
    wall-clock is the SUM of the tried candidates' latencies. Returns wall_ms."""
    t0 = time.perf_counter()
    for i in range(n):
        cand = await gen_async(i)
        if verify(cand):
            break
    return (time.perf_counter() - t0) * 1000


@dataclass
class ClockAMeasurement:
    n: int
    p: float                        # per-candidate success probability (of the simulated generator)
    sequential_ms: float
    parallel_ms: float
    speedup: float
    note: str = ""


def measure_clock_a(n: int = 6, p: float = 0.5, per_call_ms: float = 60.0, trials: int = 6,
                    seed: int = 7) -> ClockAMeasurement:
    """MEASURED orchestration speedup [Clock A] over `trials` REAL asyncio runs: sequential (try in order,
    sum the latencies up to the first pass) vs parallel+early-exit (all concurrent, the first GOOD candidate
    to FINISH wins). Per-candidate latency is SIMULATED & VARIED (real LLM latency is [BLOCKED: key/egress]);
    the concurrency/early-exit win is real. `p` = per-candidate success prob. Means reported over the trials."""
    import random
    rng = random.Random(seed)
    seq_total = par_total = 0.0
    for _ in range(trials):
        good = [rng.random() < p for _ in range(n)]
        if not any(good):
            good[rng.randrange(n)] = True
        lat = [per_call_ms * (0.6 + 0.8 * rng.random()) for _ in range(n)]   # varied, realistic latencies

        def make_gen(good_, lat_):
            async def gen(i: int) -> str:
                await asyncio.sleep(lat_[i] / 1000.0)
                return f"cand{i}:{'GOOD' if good_[i] else 'BAD'}"
            return gen

        def verify(c: str) -> bool:
            return c.endswith("GOOD")

        async def run():
            g = make_gen(good, lat)
            s = await _sequential_baseline(n, g, verify)     # sum until first pass (real wall-clock)
            p_ = (await best_of_n(n, g, verify)).wall_ms       # first GOOD to finish (real wall-clock)
            return s, p_
        s, p_ = asyncio.run(run())
        seq_total += s
        par_total += p_
    seq_ms, par_ms = seq_total / trials, par_total / trials
    return ClockAMeasurement(n=n, p=p, sequential_ms=round(seq_ms, 1), parallel_ms=round(par_ms, 1),
                             speedup=round(seq_ms / par_ms, 2) if par_ms > 0 else 1.0,
                             note=f"[Clock A] orchestration over {trials} real asyncio trials; per-call latency "
                                  "simulated & varied (live LLM [BLOCKED: key/egress]); win = sum→max.")
