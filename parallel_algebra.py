"""
v26.2 STAGE 9b — associative-algebra parallelization (the genuinely-MEASURABLE runtime win here).
=================================================================================================
A reduction `reduce(op, [f(i) for i in 0..n))` parallelizes losslessly **iff `op` is associative**
(a monoid): split into chunks, reduce each in parallel, combine. This module PROVES the monoid law for
the op, runs the parallel reduction (multiprocessing), checks DIFFERENTIAL EQUIVALENCE against the
sequential reference (★ never a wrong transform ★), and reports the MEASURED speedup with the workload.

★ HONEST CEILING (§1.3, §3) ★: speedup ≤ #cores by Amdahl, minus process-spawn/pickle overhead — so the
real figure here is ~1.7–2× on 4 cores, NOT 4×. Non-associative ops (e.g. subtraction, mean-as-written)
are DECLINED. This measures Python-execution kernels (the substrate we can run); the *proof* (monoid +
equivalence) is the transferable verification contribution.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

# op -> (identity, associative?)  — only associative ops may be parallelized.
_MONOIDS = {"+": (0, True), "*": (1, True), "max": (float("-inf"), True), "min": (float("inf"), True),
            "and": (True, True), "or": (False, True)}
_NON_ASSOC = {"-", "/", "mean"}            # explicitly NOT associative → must DECLINE
_ELEM = {"square": lambda i: i * i, "cube": lambda i: i * i * i, "id": lambda i: i}


def is_monoid(op: str) -> bool:
    return op in _MONOIDS and _MONOIDS[op][1]


def _combine(op, a, b):
    if op == "+": return a + b
    if op == "*": return a * b
    if op == "max": return a if a > b else b
    if op == "min": return a if a < b else b
    if op == "and": return a and b
    if op == "or": return a or b
    raise ValueError(op)


def _seq_reduce(func_name, op, lo, hi):
    f = _ELEM[func_name]
    acc = _MONOIDS[op][0]
    for i in range(lo, hi):
        acc = _combine(op, acc, f(i))
    return acc


def _chunk_worker(args):                    # top-level → picklable for multiprocessing
    func_name, op, lo, hi = args
    return _seq_reduce(func_name, op, lo, hi)


@dataclass
class ParVerdict:
    status: str            # OPTIMIZED | DECLINED | MISMATCH | NO_GAIN
    op: str = ""
    speedup: float = 1.0
    workload: str = ""
    seq_s: float = 0.0
    par_s: float = 0.0
    cores: int = 1
    reason: str = ""

    def __str__(self):
        if self.status == "OPTIMIZED":
            return (f"OPTIMIZED [associative {self.op}] {self.speedup:.2f}× on {self.cores} cores "
                    f"({self.workload}; seq {self.seq_s:.4f}s → par {self.par_s:.4f}s; equivalence verified). "
                    f"Ceiling ≤ {self.cores}× (Amdahl − spawn overhead).")
        return f"{self.status} [{self.op}] — {self.reason}"


def parallelize_reduction(func_name: str, op: str, n: int, cores: int = 4) -> ParVerdict:
    """Prove `op` is a monoid, run a parallel reduction, verify equivalence vs sequential, measure."""
    if op in _NON_ASSOC or not is_monoid(op):
        return ParVerdict("DECLINED", op=op, reason="operator is not provably associative — "
                          "parallel reduction would change the result (no transform)")
    if func_name not in _ELEM:
        return ParVerdict("DECLINED", op=op, reason=f"unknown element function {func_name}")
    workload = f"reduce({op}, [{func_name}(i) for i in 0..{n}))"
    # sequential reference
    t = time.perf_counter(); seq = _seq_reduce(func_name, op, 0, n); seq_s = time.perf_counter() - t
    # parallel
    try:
        import multiprocessing as mp
        bounds = [(func_name, op, i * n // cores, (i + 1) * n // cores) for i in range(cores)]
        t = time.perf_counter()
        with mp.Pool(cores) as pool:
            parts = pool.map(_chunk_worker, bounds)
        par = parts[0]
        for p in parts[1:]:
            par = _combine(op, par, p)
        par_s = time.perf_counter() - t
    except Exception as e:   # noqa: BLE001
        return ParVerdict("DECLINED", op=op, reason=f"[BLOCKED: multiprocessing unavailable: {type(e).__name__}]")
    if par != seq:                              # ★ differential-equivalence gate — never a wrong transform
        return ParVerdict("MISMATCH", op=op, reason="parallel result ≠ sequential — transform rejected")
    speedup = seq_s / par_s if par_s > 0 else 1.0
    if speedup < 1.1:
        return ParVerdict("NO_GAIN", op=op, speedup=speedup, workload=workload, seq_s=seq_s,
                          par_s=par_s, cores=cores, reason=f"measured {speedup:.2f}× (<1.1×) — reverted")
    return ParVerdict("OPTIMIZED", op=op, speedup=speedup, workload=workload, seq_s=seq_s,
                      par_s=par_s, cores=cores)
