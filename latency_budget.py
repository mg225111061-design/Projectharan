"""
v28 STAGE 19 — latency budget + watchdog + cache economics + parallel orchestration  ★speed-first★.
====================================================================================================
Make it feel instant — WITHOUT ever changing an answer (§1.12: caches, parallelism and early-exit may only
make things faster or honestly-defer; the worst case is "slower", never "wrong"). Total latency =
model-calls × iterations + verification. We attack all three, and the parts that do NOT need the model are
MEASURED here (the live model-call latency is [BLOCKED: key/egress] — user procedure below).

  1. budget + watchdog  — every stage runs under a latency budget; on overrun it HONEST-DEFERs (never hangs).
                          NORMAL = tight budgets + early-exit; EXTENDED = loose.
  2. cache economics     — a byte-for-byte STABLE prefix (no timestamps/uuids/dict-reorder) so prompt caching
                          fires; pad a short prefix up to the provider's min cacheable size; a CacheLedger
                          turns `usage` into a hit-rate + cost multiplier (read 0.1×, write 1.25×, break-even
                          at the 2nd call).
  3. parallel orchestration — independent verification chunks run in parallel (process pool); a wave scheduler
                          parallelizes a dependency DAG along its critical path. MEASURED speedup; results are
                          asserted IDENTICAL to sequential (the zero-wrong-answer regression).
  4. incremental re-verify — 2nd+ rounds re-verify only changed obligations (proof_cache; ~373× measured, S11).

★ HONEST (§1.2,1.3,1.12) ★: cache helps only for a REPEATED prefix; padding a one-shot is pure overhead
(labeled). Early-exit never changes a converged verdict. Ω(input) is not beaten. Live model latency needs a
key — measure it with `scripts/test_claude.py` (the request shape is already 400-free + cache-primed).
"""
from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

# ── 1. latency budgets + watchdog (never hang) ──────────────────────────────────────────────────────
# per-stage budgets in ms; NORMAL is tight (speed), EXTENDED is loose (depth). Tunable, not a hard SLA.
STAGE_BUDGET_MS: Dict[str, Dict[str, int]] = {
    "normal":   {"classify": 200, "generate": 20000, "verify": 1500, "optimize": 1500, "ground": 4000},
    "extended": {"classify": 500, "generate": 60000, "verify": 8000, "optimize": 8000, "ground": 20000},
}


@dataclass
class BudgetResult:
    status: str            # OK | DEFERRED | ERROR
    value: object = None
    elapsed_ms: float = 0.0
    budget_ms: float = 0.0
    detail: str = ""

    def __str__(self):
        if self.status == "OK":
            return f"OK in {self.elapsed_ms:.1f}ms (budget {self.budget_ms:.0f}ms)"
        if self.status == "DEFERRED":
            return f"DEFERRED — exceeded {self.budget_ms:.0f}ms budget (honest-defer, no hang)"
        return f"ERROR — {self.detail}"


def run_with_budget(fn: Callable, budget_ms: float, *args, **kwargs) -> BudgetResult:
    """Run `fn` but never block past `budget_ms`: on overrun return DEFERRED (the abandoned work runs in a
    daemon thread and cannot block the pipeline). The pipeline ALWAYS makes progress — it never hangs."""
    box: Dict[str, object] = {}
    def target():
        t0 = time.perf_counter()
        try:
            box["v"] = fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            box["e"] = e
        box["t"] = (time.perf_counter() - t0) * 1000
    th = threading.Thread(target=target, daemon=True)
    t0 = time.perf_counter()
    th.start()
    th.join(budget_ms / 1000.0)
    if th.is_alive():
        return BudgetResult("DEFERRED", None, (time.perf_counter() - t0) * 1000, budget_ms,
                            "stage exceeded its budget — deferred (never hangs)")
    if "e" in box:
        return BudgetResult("ERROR", None, box.get("t", 0.0), budget_ms, f"{type(box['e']).__name__}: {box['e']}")
    return BudgetResult("OK", box.get("v"), box.get("t", 0.0), budget_ms)


# ── 2. cache economics ──────────────────────────────────────────────────────────────────────────────
CACHE_MIN_TOKENS = {"anthropic": 1024, "anthropic_compat": 1024, "openai_compat": 1024}
_VOLATILE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{2}:\d{2}:\d{2}\b"               # dates / times
                       r"|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"               # uuids
                       r"|\b(?:now|today|timestamp|random|uuid)\b", re.IGNORECASE)
_PAD_UNIT = "\n# (inert cache-alignment padding — semantically empty; present only to reach the provider's " \
            "minimum cacheable prefix size; it changes no instruction.)"


def is_stable_prefix(text: str) -> bool:
    """A cacheable prefix must be byte-for-byte stable across calls: no timestamps/uuids/'now'/'random'."""
    return _VOLATILE.search(text) is None


def pad_to_threshold(system_text: str, provider: str = "anthropic", chars_per_tok: int = 4) -> str:
    """Pad a short STABLE prefix up to the provider's min cacheable size with INERT, stable filler so the
    cache fires. (Honest: this helps ONLY when the prefix is reused; for a one-shot it is pure overhead.)"""
    need_chars = CACHE_MIN_TOKENS.get(provider, 1024) * chars_per_tok
    if len(system_text) >= need_chars:
        return system_text
    out = system_text
    while len(out) < need_chars:
        out += _PAD_UNIT
    return out


@dataclass
class CacheLedger:
    """Turns provider `usage` into a cache hit-rate + an effective input-cost multiplier.
    Cost model: fresh input ×1.0, cache WRITE ×1.25, cache READ ×0.1 (Anthropic-class). Break-even ≈ 2 calls."""
    fresh: int = 0
    writes: int = 0
    reads: int = 0
    calls: int = 0

    def record(self, usage: Dict[str, int]) -> None:
        self.calls += 1
        self.fresh += int(usage.get("input_tokens", 0))
        self.writes += int(usage.get("cache_creation_input_tokens", 0))
        self.reads += int(usage.get("cache_read_input_tokens", 0))

    def hit_rate(self) -> float:
        total = self.fresh + self.writes + self.reads
        return self.reads / total if total else 0.0

    def effective_cost(self) -> float:
        return self.fresh * 1.0 + self.writes * 1.25 + self.reads * 0.1

    def baseline_cost(self) -> float:
        return float(self.fresh + self.writes + self.reads)   # if nothing were cached

    def savings(self) -> float:
        b = self.baseline_cost()
        return (b - self.effective_cost()) / b if b else 0.0


# ── 3. parallel orchestration (results IDENTICAL to sequential — zero-wrong-answer) ─────────────────
def schedule_waves(dep_graph: Dict[str, List[str]]) -> List[List[str]]:
    """Topologically level a dependency DAG into WAVES; tasks within a wave have no inter-dependency and
    run in parallel. Critical-path length = number of waves."""
    indeg = {t: 0 for t in dep_graph}
    for t, deps in dep_graph.items():
        for d in deps:
            indeg.setdefault(d, 0)
        indeg[t] = len([d for d in deps if d in dep_graph or True])
    remaining = {t: set(deps) for t, deps in dep_graph.items()}
    waves: List[List[str]] = []
    done: set = set()
    while len(done) < len(dep_graph):
        wave = sorted(t for t in dep_graph if t not in done and remaining[t] <= done)
        if not wave:
            raise ValueError("dependency cycle — cannot schedule")
        waves.append(wave)
        done |= set(wave)
    return waves


def bounded_verify(spec: Tuple[int, int]) -> bool:
    """A picklable, CPU-bound BOUNDED verification task (no imports): check a property over [0,N).
    `spec=(prop_id, N)`. Deterministic — same input ⇒ same answer (the basis of the parallel speedup)."""
    prop_id, N = spec
    if prop_id == 0:
        return all((i * i) % 7 != 3 for i in range(N))          # true: 3 is a non-residue mod 7
    if prop_id == 1:
        return all((i * (i + 1)) % 2 == 0 for i in range(N))    # true: consecutive product is even
    return all(i + 0 == i for i in range(N))


def parallel_map(func: Callable, items: Sequence, workers: int = 4) -> List:
    """Run `func` over `items` in a process pool. `func` must be top-level/picklable. Falls back to
    sequential if multiprocessing is unavailable (honest)."""
    try:
        import multiprocessing as mp
        with mp.Pool(workers) as pool:
            return pool.map(func, list(items))
    except Exception:  # noqa: BLE001
        return [func(x) for x in items]


@dataclass
class ParallelMeasurement:
    status: str            # OPTIMIZED | NO_GAIN | MISMATCH
    speedup: float = 1.0
    workers: int = 1
    seq_ms: float = 0.0
    par_ms: float = 0.0
    same: bool = True
    workload: str = ""


def measure_parallel_orchestration(specs: Sequence[Tuple[int, int]], workers: int = 4) -> ParallelMeasurement:
    """Measure parallel vs sequential verification of independent chunks, and ASSERT identical results
    (the zero-wrong-answer regression: parallelism only makes it faster, never different)."""
    t = time.perf_counter()
    seq = [bounded_verify(s) for s in specs]
    seq_ms = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    par = parallel_map(bounded_verify, specs, workers)
    par_ms = (time.perf_counter() - t) * 1000
    same = (seq == par)
    workload = f"{len(specs)} bounded-verify chunks (N≈{specs[0][1] if specs else 0})"
    if not same:
        return ParallelMeasurement("MISMATCH", 1.0, workers, seq_ms, par_ms, False, workload)
    speedup = seq_ms / par_ms if par_ms > 0 else 1.0
    status = "OPTIMIZED" if speedup >= 1.1 else "NO_GAIN"
    return ParallelMeasurement(status, speedup, workers, seq_ms, par_ms, same, workload)


# ── 4. zero-wrong-answer regression helper ──────────────────────────────────────────────────────────
def same_result(slow: Callable, fast: Callable, inputs: Sequence) -> bool:
    """§1.12 invariant: an optimization (cache/parallel/early-exit) must give the SAME answer as the slow
    reference on every input — only faster. Returns True iff every output matches."""
    return all(slow(x) == fast(x) for x in inputs)
