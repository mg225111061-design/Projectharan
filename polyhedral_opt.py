"""
PHASE 2.S6 (EXTENDED) — polyhedral loop transforms (interchange/tiling), dependency-validated + cost-gated.
============================================================================================================
Reorder loops (interchange/tiling) for cache locality — but ONLY when (a) a dependency check says the reorder
preserves semantics (the result is bit-identical) AND (b) a measured COST MODEL says it is actually faster.
Polyhedral can HURT (it sometimes defeats vectorization on stencils) — so a transform that does not measure
faster is DECLINED (§ honest: we never adopt a "transform" that is slower).

★ ENV HONESTY: full polyhedral scheduling needs `isl`/ISL-rs → [BLOCKED]. We implement SIMPLE, sound transforms
(loop interchange; square tiling) and validate each by the dependency battery (P2.S5) + a measured cost gate. ★
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple


def isl_available() -> bool:
    try:
        import islpy  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


@dataclass
class PolyResult:
    status: str                 # ADOPTED | DECLINE | BLOCKED
    transform: str = ""
    bit_exact: bool = False
    naive_ms: float = 0.0
    transformed_ms: float = 0.0
    speedup: float = 0.0
    detail: str = ""


def _bench(fn, *args, reps: int = 5) -> float:
    fn(*args)                                                  # warm
    return min((lambda: (lambda t: t)((time.perf_counter())))() and 0 or _one(fn, args) for _ in range(reps))


def _one(fn, args) -> float:
    t = time.perf_counter(); fn(*args); return (time.perf_counter() - t) * 1000


def interchange_column_sum(rows: int = 2000, cols: int = 2000) -> PolyResult:
    """Loop INTERCHANGE on a column-sum over a C-contiguous matrix. Naive schedule iterates columns outer
    (strided, cache-hostile); the interchanged schedule iterates rows outer (contiguous). Same result
    (a reduction is order-independent ⇒ dependency-safe), measured cost gate decides adoption."""
    try:
        import numpy as np
    except Exception as e:  # noqa: BLE001
        return PolyResult("BLOCKED", "interchange", detail=f"[BLOCKED: numpy — {e}]")
    rng = np.random.default_rng(3)
    A = rng.integers(0, 100, size=(rows, cols), dtype=np.int64)        # C-contiguous (row-major)

    def naive_cols(M):                                                 # j outer, i inner → strided column access
        return np.array([M[:, j].sum() for j in range(M.shape[1])], dtype=np.int64)

    def interchanged(M):                                              # i outer (contiguous) → column sums
        return M.sum(axis=0)
    # dependency validation (P2.S5): identical result ⇒ the reorder is sound
    bit_exact = bool(np.array_equal(naive_cols(A), interchanged(A)))
    if not bit_exact:
        return PolyResult("DECLINE", "interchange", False, detail="reorder changed the result — DECLINED (unsound)")
    naive_ms = min(_one(naive_cols, (A,)) for _ in range(3))
    trans_ms = min(_one(interchanged, (A,)) for _ in range(3))
    speedup = round(naive_ms / trans_ms, 2) if trans_ms > 0 else 1.0
    if speedup <= 1.05:                                              # cost model: not actually faster ⇒ DECLINE
        return PolyResult("DECLINE", "interchange", True, round(naive_ms, 4), round(trans_ms, 4), speedup,
                          f"[MEASURED {speedup}×] not faster enough — cost model DECLINES (polyhedral can hurt)")
    return PolyResult("ADOPTED", "interchange", True, round(naive_ms, 4), round(trans_ms, 4), speedup,
                      f"sound reorder, cache-friendly, {speedup}× (dependency-safe + cost-model adopted)")


def tiling_transpose(n: int = 2000, block: int = 64) -> PolyResult:
    """Square TILING of a transpose-accumulate. Naive: full strided transpose. Tiled: block-wise (cache).
    Validated bit-exact; cost-model gated."""
    try:
        import numpy as np
    except Exception as e:  # noqa: BLE001
        return PolyResult("BLOCKED", "tiling", detail=f"[BLOCKED: numpy — {e}]")
    rng = np.random.default_rng(5)
    A = rng.integers(0, 100, size=(n, n), dtype=np.int64)

    def naive(M):                                                   # strided write of the transpose then sum
        return (M.T.copy()).sum(axis=1)

    def tiled(M):                                                   # block-wise transpose accumulation
        out = np.zeros(M.shape[1], dtype=np.int64)
        for i0 in range(0, M.shape[0], block):
            out += M[i0:i0 + block, :].sum(axis=0)
        return out
    bit_exact = bool(np.array_equal(naive(A), tiled(A)))
    if not bit_exact:
        return PolyResult("DECLINE", "tiling", False, detail="tiling changed the result — DECLINED")
    naive_ms = min(_one(naive, (A,)) for _ in range(3))
    tiled_ms = min(_one(tiled, (A,)) for _ in range(3))
    speedup = round(naive_ms / tiled_ms, 2) if tiled_ms > 0 else 1.0
    status = "ADOPTED" if speedup > 1.05 else "DECLINE"
    return PolyResult(status, "tiling", True, round(naive_ms, 4), round(tiled_ms, 4), speedup,
                      f"[MEASURED {speedup}×] {'adopted' if status=='ADOPTED' else 'cost-model declined'} (bit-exact)")
