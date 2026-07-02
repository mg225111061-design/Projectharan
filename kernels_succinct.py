"""
v40 PHASE 4 — succinct / index data structures (O(1)/O(log N) QUERY collapse).
==============================================================================
★ §0.1 strict: this is a QUERY-TIME collapse (after an O(n) / O(n log n) build), NOT value recovery and NOT a
  compute collapse of the underlying data. RMQ answers a range-min in O(1) per query — it does not "recover"
  values. We label it as such. ★ Both kernels are EXACT (exact integer comparisons / sums).

  • 20/25 Sparse-Table RMQ : O(n log n) build → O(1) range-minimum query.
  • 25    Prefix-sum range  : O(n) build → O(1) range-sum query.
"""
from __future__ import annotations

import time
from typing import Any, List, Tuple

import kernel_verdict as KV
import kernel_router as R


# ── 20/25 · Sparse-Table RMQ: O(1) range-minimum query (idempotent ⇒ overlap ok) ──────────────────────
def _build_sparse_table(a: List[int]):
    n = len(a)
    LOG = max(1, n.bit_length())
    table = [a[:]]
    j = 1
    while (1 << j) <= n:
        prev = table[j - 1]
        cur = [min(prev[i], prev[i + (1 << (j - 1))]) for i in range(n - (1 << j) + 1)]
        table.append(cur)
        j += 1
    return table


def _rmq(table, l: int, r: int) -> int:                 # inclusive [l, r], O(1)
    j = (r - l + 1).bit_length() - 1
    return min(table[j][l], table[j][r - (1 << j) + 1])


def _rmq_detect(d: Any) -> bool:
    return (isinstance(d, dict) and d.get("kind") == "rmq"
            and isinstance(d.get("array"), list) and isinstance(d.get("queries"), list))


def _rmq_run(d: Any, **kw) -> KV.Verdict:
    a: List[int] = [int(x) for x in d["array"]]
    qs: List[Tuple[int, int]] = [(int(l), int(r)) for l, r in d["queries"]]
    n = len(a)
    if n == 0 or any(not (0 <= l <= r < n) for l, r in qs):
        return KV.decline("rmq needs non-empty array and in-range [l,r] queries", "rmq_sparse_table")
    table = _build_sparse_table(a)
    ans = [_rmq(table, l, r) for (l, r) in qs]
    # fast EXACT certificate: spot-check a few queries against the naive range-min (exact integer compare)
    import random
    rng = random.Random(0)
    idx = rng.sample(range(len(qs)), min(6, len(qs)))
    ok = all(ans[t] == min(a[qs[t][0]:qs[t][1] + 1]) for t in idx)
    cert = KV.Cert(KV.EXACT, "rmq_spotcheck", passed=ok, check_cost="O(span) × few",
                   detail=f"sparse-table O(1) range-min; {len(idx)} queries spot-checked vs naive min")
    if not ok:
        return KV.decline("rmq spot-check disagreed", "rmq_sparse_table")
    return KV.exact(ans, "rmq_sparse_table", "O(1) per query (O(n log n) build)", cert)


def measure_rmq() -> dict:
    """QUERY-TIME collapse O(n)/query → O(1)/query. Crossover in #queries (build amortizes)."""
    import random
    rng = random.Random(1)
    n = 4096
    a = [rng.randint(-10**6, 10**6) for _ in range(n)]
    qs = [tuple(sorted((rng.randrange(n), rng.randrange(n)))) for _ in range(20000)]
    t = time.perf_counter()
    naive = [min(a[l:r + 1]) for (l, r) in qs]
    tn = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    table = _build_sparse_table(a)
    fast = [_rmq(table, l, r) for (l, r) in qs]
    tf = (time.perf_counter() - t) * 1000
    return {"kernel": "rmq_sparse_table", "collapse": "QUERY-TIME O(n)/q → O(1)/q (NOT value recovery, §0.1)",
            "n": n, "queries": len(qs), "naive_ms": round(tn, 1), "sparse_table_ms": round(tf, 1),
            "exact": naive == fast, "amdahl_p": "high in query-heavy workloads (DBs, LCA, suffix structures)"}


# ── 25 · Prefix-sum range query: O(1) range-sum after O(n) build ───────────────────────────────────────
def _ps_detect(d: Any) -> bool:
    return (isinstance(d, dict) and d.get("kind") == "range_sum"
            and isinstance(d.get("array"), list) and isinstance(d.get("queries"), list))


def _ps_run(d: Any, **kw) -> KV.Verdict:
    a = [int(x) for x in d["array"]]
    qs = [(int(l), int(r)) for l, r in d["queries"]]
    n = len(a)
    if n == 0 or any(not (0 <= l <= r < n) for l, r in qs):
        return KV.decline("range_sum needs non-empty array and in-range queries", "prefix_sum")
    pre = [0] * (n + 1)
    for i in range(n):
        pre[i + 1] = pre[i] + a[i]
    ans = [pre[r + 1] - pre[l] for (l, r) in qs]
    import random
    rng = random.Random(0)
    idx = rng.sample(range(len(qs)), min(6, len(qs)))
    ok = all(ans[t] == sum(a[qs[t][0]:qs[t][1] + 1]) for t in idx)
    cert = KV.Cert(KV.EXACT, "prefix_spotcheck", passed=ok, check_cost="O(span) × few",
                   detail=f"prefix sums; {len(idx)} range-sums spot-checked vs naive (exact integers)")
    if not ok:
        return KV.decline("range_sum spot-check disagreed", "prefix_sum")
    return KV.exact(ans, "prefix_sum", "O(1) per query (O(n) build)", cert)


def register_all():
    R.register(R.Kernel(20, "rmq_sparse_table", "D",
                        "requires array ∧ in-range queries  ensures range-min exact ∧ grade=EXACT ∧ "
                        "cost=O(1)/query (query-time collapse, not value recovery)",
                        _rmq_detect, _rmq_run))
    R.register(R.Kernel(25, "prefix_sum", "D",
                        "requires array ∧ in-range queries  ensures range-sum exact ∧ grade=EXACT ∧ "
                        "cost=O(1)/query",
                        _ps_detect, _ps_run))


register_all()
