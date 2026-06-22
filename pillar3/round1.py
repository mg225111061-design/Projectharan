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
    ]
