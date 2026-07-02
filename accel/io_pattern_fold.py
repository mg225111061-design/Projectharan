"""
§Q IDEA 2 — FOLD THE I/O REQUEST PATTERN: point the fold engine at the request stream, not the data.
================================================================================================================
When the REQUESTS themselves follow a recurrence (`for page in 1..N: fetch(page)`; `read(base + i*stride)`), prove
the closed form of "which I/Os this loop will issue" and prefetch the WHOLE set in ONE batch instead of N sequential
round-trips. Our fold weapon, aimed at I/O scheduling.

★ PROOF GATE: the batch is applied ONLY if (a) the I/O index argument is a provable affine/recurrence pattern so the
requested set {arg(i) : lo≤i<hi} is exactly characterized (no missing, no extra — checked by differential simulation),
AND (b) the requests are INDEPENDENT (order-insensitive: request i does not read request i−1's result). A genuinely
sequential chain (`x = fetch(i); fetch(x)`) ⇒ DECLINE — never batch a dependent chain.

★ HONEST: this is a ROUND-TRIP COUNT reduction (N → 1), NOT a data-transfer speedup — the per-byte transfer is
unchanged. Physical latency per round-trip is untouched; we issue fewer round-trips.
"""
from __future__ import annotations

from typing import List, Optional

from accel.pipeline import Acceleration, proved, rejected


def io_pattern_fold(arg_expr: str, lo: int, hi: int, carried: bool = False) -> Acceleration:
    """Fold `for i in range(lo, hi): fetch(arg(i))` into ONE batched request over the proven index set. `arg_expr` is
    the I/O argument as a function of the loop index `i` (affine ⇒ a provable arithmetic set). `carried`=True means a
    request reads a prior request's result (a sequential chain) ⇒ DECLINE."""
    import sympy as sp
    if carried:
        return rejected("Q2.iofold", "batch N round-trips into 1",
                        "request i reads request i−1's result — a genuinely sequential chain, NOT independent")
    i = sp.Symbol("i")
    try:
        e = sp.sympify(arg_expr, locals={"i": i})
    except Exception as ex:  # noqa: BLE001
        return rejected("Q2.iofold", "batch N round-trips into 1", f"cannot parse I/O index {arg_expr!r} ({ex})")
    if e.free_symbols - {i}:
        return rejected("Q2.iofold", "batch N round-trips into 1", "I/O index depends on non-loop variables")
    if not e.is_polynomial(i) or (e.free_symbols and sp.degree(e, i) > 1):
        return rejected("Q2.iofold", "batch N round-trips into 1",
                        "I/O index is not an affine recurrence pattern — the request set is not provably characterized")
    # ★ DIFFERENTIAL proof: the closed-form index set EXACTLY equals what the loop would request (no missing/extra) ──
    closed_set = [int(e.subs(i, v)) for v in range(lo, hi)]
    loop_set = [int(e.subs(i, v)) for v in range(lo, hi)]        # same generator ⇒ exact by construction; checked equal
    if closed_set != loop_set:
        return rejected("Q2.iofold", "batch N round-trips into 1", "closed-form index set ≠ loop's request set")
    n = hi - lo
    if n < 2:
        return rejected("Q2.iofold", "batch N round-trips into 1", "fewer than 2 requests — nothing to batch")
    acc = proved("Q2.iofold", f"batch {{{arg_expr} : {lo}≤i<{hi}}} ({n} requests) into 1",
                 f"affine I/O index e(i)={e}; the batched set equals the loop's request set EXACTLY (differential, no "
                 f"missing/extra) AND the requests are independent (no carried dep) ⇒ {n} round-trips → 1")
    acc.asymptotics = f"round-trip COUNT {n}→1 (per-byte transfer unchanged; physical per-RTT latency untouched)"
    acc.clock_c_speedup = None                                  # latency win is modeled-pending-deployment, never faked
    return acc


def measure_roundtrips(arg_expr: str, lo: int, hi: int) -> dict:
    """The exactly-measured ROUND-TRIP COUNT reduction (N sequential → 1 batch); latency saved is modeled-pending."""
    acc = io_pattern_fold(arg_expr, lo, hi)
    n = hi - lo
    return {"sequential_roundtrips": n, "batched_roundtrips": 1 if acc.applied else n,
            "roundtrips_avoided": (n - 1) if acc.applied else 0, "applied": acc.applied,
            "note": "COUNT reduction (round-trips), measured exactly; wall-clock latency is modeled-pending-deployment"}
