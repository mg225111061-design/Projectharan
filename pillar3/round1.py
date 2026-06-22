"""
Pillar 3 · ROUND 1 — big-multiplier recognizers (asymptotic jumps; the win grows with n).
==========================================================================================
Each recognizer is (naive, fast, wrong) graded through algorithms.recognize_and_grade: differential over a
strong input set (PHASE I) + metamorphic (PHASE M) + a coherent whole-program measurement (ratio ≤ ceiling).
These carry control flow ⇒ Z3 bounded validation does not apply ⇒ graded PROBABILISTIC with a stated δ (never
EXACT, §X). The adversarial wrong version is caught by the net ⇒ DECLINE. Operating n is quoted in the test.
"""
from __future__ import annotations

import random as _rnd
from typing import List

from pillar3.algorithms import Recognizer


# ── item 7 — linear recurrence O(n) → O(log n) via fast-doubling (Fibonacci-class) ──────────────────────
def fib_iter(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def fib_fast_doubling(n):
    def fd(k):
        if k == 0:
            return (0, 1)
        a, b = fd(k >> 1)
        c = a * (2 * b - a)
        d = a * a + b * b
        return (d, c + d) if (k & 1) else (c, d)
    return fd(n)[0]


def fib_fd_wrong(n):                                         # drops the 2*b-a correction ⇒ wrong
    def fd(k):
        if k == 0:
            return (0, 1)
        a, b = fd(k >> 1)
        c = a * b
        d = a * a + b * b
        return (d, c + d) if (k & 1) else (c, d)
    return fd(n)[0]


def _mk_fib(n=24000):
    return (n,)


def _fib_in():
    return [(0,), (1,), (2,), (7,), (10,), (50,), (97,), (200,)]


# ── item 11 — naive substring search O(n·m) → KMP O(n+m) (all match start indices) ─────────────────────
def search_naive(text, pat):
    out = []
    n, m = len(text), len(pat)
    if m == 0:
        return list(range(n + 1))
    for i in range(n - m + 1):
        j = 0
        while j < m and text[i + j] == pat[j]:
            j += 1
        if j == m:
            out.append(i)
    return out


def search_kmp(text, pat):
    n, m = len(text), len(pat)
    if m == 0:
        return list(range(n + 1))
    lps = [0] * m
    k = 0
    for i in range(1, m):
        while k and pat[i] != pat[k]:
            k = lps[k - 1]
        if pat[i] == pat[k]:
            k += 1
        lps[i] = k
    out = []
    k = 0
    for i in range(n):
        while k and text[i] != pat[k]:
            k = lps[k - 1]
        if text[i] == pat[k]:
            k += 1
        if k == m:
            out.append(i - m + 1)
            k = lps[k - 1]
    return out


def search_kmp_wrong(text, pat):                            # off-by-one in the lps reset ⇒ wrong indices
    n, m = len(text), len(pat)
    if m == 0:
        return list(range(n + 1))
    lps = [0] * m
    k = 0
    for i in range(1, m):
        while k and pat[i] != pat[k]:
            k = lps[k]
        if pat[i] == pat[k]:
            k += 1
        lps[i] = k
    out = []
    k = 0
    for i in range(n):
        while k and text[i] != pat[k]:
            k = lps[k - 1]
        if text[i] == pat[k]:
            k += 1
        if k == m:
            out.append(i - m)
            k = lps[k - 1]
    return out


_KMP_CACHE: dict = {}


def _mk_kmp(n=24000):
    if n not in _KMP_CACHE:
        _KMP_CACHE[n] = ("a" * n, "a" * 80 + "b")           # naive worst case; KMP linear
    return _KMP_CACHE[n]


def _kmp_in():
    return [("abababab", "abab"), ("aaaa", "aa"), ("xyz", "a"), ("", "a"), ("aaa", ""), ("mississippi", "issi")]


# ── item 14 — repeated connectivity: naive per-query BFS O(q·(V+E)) → union-find near O(q·α) ────────────
def connectivity_naive(n, edges, queries):
    adj = [[] for _ in range(n)]
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    out = []
    for a, b in queries:
        seen = [False] * n
        stack = [a]
        seen[a] = True
        while stack:
            u = stack.pop()
            for v in adj[u]:
                if not seen[v]:
                    seen[v] = True
                    stack.append(v)
        out.append(seen[b])
    return out


def connectivity_uf(n, edges, queries):
    p = list(range(n))
    r = [0] * n
    def find(x):
        while p[x] != x:
            p[x] = p[p[x]]
            x = p[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        if r[ra] < r[rb]:
            ra, rb = rb, ra
        p[rb] = ra
        if r[ra] == r[rb]:
            r[ra] += 1
    for a, b in edges:
        union(a, b)
    return [find(a) == find(b) for a, b in queries]


def connectivity_uf_wrong(n, edges, queries):              # union without linking roots ⇒ wrong connectivity
    p = list(range(n))
    def find(x):
        while p[x] != x:
            x = p[x]
        return x
    for a, b in edges:
        p[a] = b                                            # BUG: link node, not root
    return [find(a) == find(b) for a, b in queries]


_UF_CACHE: dict = {}


def _mk_uf(n=600, m=1200, q=600):
    key = (n, m, q)
    if key not in _UF_CACHE:
        rng = _rnd.Random(61)
        edges = [(rng.randrange(n), rng.randrange(n)) for _ in range(m)]
        queries = [(rng.randrange(n), rng.randrange(n)) for _ in range(q)]
        _UF_CACHE[key] = (n, edges, queries)
    return _UF_CACHE[key]


def _uf_in():
    # the last case unions a NON-root after a chain (0→1→2, then union 0,3) — exposes a link-node-not-root bug
    return [(3, [(0, 1)], [(0, 1), (0, 2)]), (4, [(0, 1), (2, 3)], [(0, 3), (1, 0)]),
            (2, [], [(0, 1)]), (5, [(0, 1), (1, 2), (3, 4)], [(0, 2), (2, 4)]),
            (4, [(0, 1), (1, 2), (0, 3)], [(1, 0), (1, 3), (0, 2)])]


# ── item 9-ext — coin-change min-coins: exponential recursion → O(amount·|coins|) DP ───────────────────
def coins_naive(coins, amount):
    def go(a):
        if a == 0:
            return 0
        best = float("inf")
        for c in coins:
            if c <= a:
                best = min(best, 1 + go(a - c))
        return best
    r = go(amount)
    return -1 if r == float("inf") else r


def coins_dp(coins, amount):
    INF = float("inf")
    dp = [0] + [INF] * amount
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a and dp[a - c] + 1 < dp[a]:
                dp[a] = dp[a - c] + 1
    return -1 if dp[amount] == INF else dp[amount]


def coins_dp_wrong(coins, amount):                         # off-by-one base ⇒ wrong counts
    INF = float("inf")
    dp = [1] + [INF] * amount                              # BUG: dp[0] should be 0
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a and dp[a - c] + 1 < dp[a]:
                dp[a] = dp[a - c] + 1
    return -1 if dp[amount] == INF else dp[amount]


def _mk_coins(amount=26):
    return ([1, 3, 4], amount)


def _coins_in():
    return [(([1, 2, 5], 11),), (([2], 3),), (([1], 0),), (([1, 5, 10], 18),), (([3, 7], 5),)]


def _coins_in_fixed():
    # coins recognizer takes (coins, amount); build proper arg tuples
    return [([1, 2, 5], 11), ([2], 3), ([1], 0), ([1, 5, 10], 18), ([3, 7], 5), ([1, 3, 4], 13)]


# ── item 12 — repeated point-update + range-sum: naive O((U+Q)·n) → Fenwick/BIT O((U+Q)·log n) ──────────
def fenwick_naive(n, ops):
    arr = [0] * n
    out = []
    for op in ops:
        if op[0] == "u":
            arr[op[1]] += op[2]
        else:
            s = 0
            for i in range(op[1], op[2]):
                s += arr[i]
            out.append(s)
    return out


def fenwick_fast(n, ops):
    tree = [0] * (n + 1)
    def upd(i, v):
        i += 1
        while i <= n:
            tree[i] += v
            i += i & (-i)
    def pre(i):
        s = 0
        while i > 0:
            s += tree[i]
            i -= i & (-i)
        return s
    out = []
    for op in ops:
        if op[0] == "u":
            upd(op[1], op[2])
        else:
            out.append(pre(op[2]) - pre(op[1]))
    return out


def fenwick_wrong(n, ops):                                  # off-by-one query range (r inclusive) ⇒ wrong sums
    tree = [0] * (n + 1)
    def upd(i, v):
        i += 1
        while i <= n:
            tree[i] += v
            i += i & (-i)
    def pre(i):
        s = 0
        while i > 0:
            s += tree[i]
            i -= i & (-i)
        return s
    out = []
    for op in ops:
        if op[0] == "u":
            upd(op[1], op[2])
        else:
            out.append(pre(min(op[2] + 1, n)) - pre(op[1]))   # BUG: includes one extra element
    return out


_FEN_CACHE: dict = {}


def _mk_fenwick(n=2000, k=1500):
    key = (n, k)
    if key not in _FEN_CACHE:
        rng = _rnd.Random(71)
        ops = []
        for _ in range(k):
            if rng.random() < 0.5:
                ops.append(("u", rng.randrange(n), rng.randrange(-50, 50)))
            else:
                l = rng.randrange(n - 1)
                ops.append(("q", l, rng.randrange(l + 1, n)))
        _FEN_CACHE[key] = (n, ops)
    return _FEN_CACHE[key]


def _fen_in():
    # the 1st case has a nonzero element JUST above a query's range (q 0..2 with arr[2]=9) — exposes an
    # r-inclusive off-by-one (sum[l,r] vs sum[l,r))
    return [(3, [("u", 2, 9), ("q", 0, 2), ("q", 0, 3)]),
            (3, [("u", 0, 5), ("q", 0, 2), ("u", 1, 3), ("q", 0, 3)]),
            (4, [("q", 0, 4), ("u", 2, 7), ("q", 1, 3)]),
            (2, [("u", 0, 1), ("u", 1, 2), ("q", 0, 2)]),
            (5, [("u", 4, 9), ("q", 0, 5), ("u", 0, 1), ("q", 0, 1), ("q", 1, 4)])]


# ── item 13 — repeated range-minimum: naive O(q·n) per-query scan → sparse-table O(n log n) build + O(1)/query ─
def rmq_naive(arr, queries):
    return [min(arr[l:r]) for (l, r) in queries]             # O(n) per query


def rmq_sparse(arr, queries):
    n = len(arr)
    if n == 0:
        return [min(arr[l:r]) for (l, r) in queries]
    import math
    K = max(1, n.bit_length())
    sp = [arr[:]]                                            # sp[k][i] = min over [i, i+2^k)
    k = 1
    while (1 << k) <= n:
        prev = sp[k - 1]
        half = 1 << (k - 1)
        row = [min(prev[i], prev[i + half]) for i in range(n - (1 << k) + 1)]
        sp.append(row)
        k += 1
    out = []
    for (l, r) in queries:                                   # half-open [l, r), r > l
        j = (r - l).bit_length() - 1                         # floor(log2(len))
        out.append(min(sp[j][l], sp[j][r - (1 << j)]))       # O(1): two overlapping blocks cover [l,r)
    return out


def rmq_wrong(arr, queries):                                 # off-by-one: uses an inclusive log split ⇒ wrong min
    n = len(arr)
    if n == 0:
        return [min(arr[l:r]) for (l, r) in queries]
    sp = [arr[:]]
    k = 1
    while (1 << k) <= n:
        prev = sp[k - 1]
        half = 1 << (k - 1)
        sp.append([min(prev[i], prev[i + half]) for i in range(n - (1 << k) + 1)])
        k += 1
    out = []
    for (l, r) in queries:
        j = (r - l).bit_length() - 1
        out.append(min(sp[j][l], sp[j][min(r - (1 << j) + 1, n - 1)]))   # BUG: +1 shifts the second block
    return out


_RMQ_CACHE: dict = {}


def _mk_rmq(n=4000, q=4000):
    key = (n, q)
    if key not in _RMQ_CACHE:
        rng = _rnd.Random(73)
        arr = [rng.randrange(-10**6, 10**6) for _ in range(n)]
        queries = []
        for _ in range(q):
            a = rng.randrange(n - 1)
            b = rng.randrange(a + 1, n)
            queries.append((a, b))
        _RMQ_CACHE[key] = (arr, queries)
    return _RMQ_CACHE[key]


def _rmq_in():
    # mixed lengths incl. a window whose min sits just outside an inclusive-split bug's reach
    return [([5, 2, 8, 1, 9, 3], [(0, 3), (1, 5), (0, 6), (2, 4), (3, 6)]),
            ([4, 4, 4, 4], [(0, 2), (1, 4)]), ([9, 1], [(0, 2), (0, 1)]),
            ([7, 6, 5, 4, 3, 2, 1], [(0, 7), (2, 5), (4, 7)]),
            ([1, 100, 100, 100, 100], [(1, 5), (0, 5)])]


# ── item 13b — single-source shortest path: naive O(V²) scan-for-min → heap-based O((V+E)·log V) ─────────
import heapq as _heapq


def _dij_adj(n, edges):
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
        adj[v].append((u, w))
    return adj


def dijkstra_naive(n, edges, src):
    adj = _dij_adj(n, edges)
    INF = float("inf")
    dist = [INF] * n
    dist[src] = 0
    visited = [False] * n
    for _ in range(n):
        u, best = -1, INF
        for i in range(n):                                  # O(V) scan for the min each step ⇒ O(V²) total
            if not visited[i] and dist[i] < best:
                best, u = dist[i], i
        if u == -1:
            break
        visited[u] = True
        for v, w in adj[u]:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
    return dist


def dijkstra_heap(n, edges, src):
    adj = _dij_adj(n, edges)
    INF = float("inf")
    dist = [INF] * n
    dist[src] = 0
    pq = [(0, src)]
    while pq:
        d, u = _heapq.heappop(pq)
        if d > dist[u]:
            continue                                        # stale entry
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                _heapq.heappush(pq, (nd, v))
    return dist


def dijkstra_wrong(n, edges, src):                          # stores d instead of d+w on relax ⇒ wrong distances
    adj = _dij_adj(n, edges)
    INF = float("inf")
    dist = [INF] * n
    dist[src] = 0
    pq = [(0, src)]
    while pq:
        d, u = _heapq.heappop(pq)
        if d > dist[u]:
            continue
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = d                                 # BUG: drops the edge weight w
                _heapq.heappush(pq, (d, v))
    return dist


_DIJ_CACHE: dict = {}


def _mk_dij(n=1500, extra=2200):
    key = (n, extra)
    if key not in _DIJ_CACHE:
        rng = _rnd.Random(91)
        edges = [(i, i + 1, rng.randrange(1, 20)) for i in range(n - 1)]   # a path ⇒ connected
        for _ in range(extra):
            a, b = rng.randrange(n), rng.randrange(n)
            if a != b:
                edges.append((a, b, rng.randrange(1, 20)))
        _DIJ_CACHE[key] = (n, edges, 0)
    return _DIJ_CACHE[key]


def _dij_in():
    return [(4, [(0, 1, 1), (1, 2, 2), (0, 2, 4), (2, 3, 1)], 0),
            (3, [(0, 1, 5), (1, 2, 5), (0, 2, 3)], 0),
            (5, [(0, 1, 1), (1, 2, 1), (2, 3, 1), (3, 4, 1)], 0),
            (2, [(0, 1, 7)], 0),
            (4, [(0, 1, 2), (0, 2, 2), (1, 3, 3), (2, 3, 1)], 0)]


def catalog() -> List[Recognizer]:
    return [
        Recognizer("matrix_power_recurrence", "algo_replace", fib_iter, fib_fast_doubling,
                   lambda: _mk_fib(24000), residual_iters=0, gen_inputs=_fib_in, relations=[], n=24000, floor=1.30),
        Recognizer("kmp_substring", "algo_replace", search_naive, search_kmp,
                   lambda: _mk_kmp(24000), residual_iters=0, gen_inputs=_kmp_in, relations=[], n=24000, floor=1.20),
        Recognizer("union_find_connectivity", "algo_replace", connectivity_naive, connectivity_uf,
                   lambda: _mk_uf(600, 1200, 600), residual_iters=0, gen_inputs=_uf_in, relations=[], n=600, floor=1.20),
        Recognizer("coin_change_dp", "algo_replace", coins_naive, coins_dp,
                   lambda: _mk_coins(26), residual_iters=0, gen_inputs=_coins_in_fixed, relations=[], n=26, floor=1.30),
        Recognizer("fenwick_range_query", "algo_replace", fenwick_naive, fenwick_fast,
                   lambda: _mk_fenwick(2000, 1500), residual_iters=0, gen_inputs=_fen_in, relations=[], n=2000, floor=1.20),
        Recognizer("sparse_table_rmq", "algo_replace", rmq_naive, rmq_sparse,
                   lambda: _mk_rmq(4000, 4000), residual_iters=0, gen_inputs=_rmq_in, relations=[], n=4000, floor=1.30),
        Recognizer("dijkstra_heap", "algo_replace", dijkstra_naive, dijkstra_heap,
                   lambda: _mk_dij(1500, 2200), residual_iters=0, gen_inputs=_dij_in, relations=[], n=1500, floor=1.30),
    ]
