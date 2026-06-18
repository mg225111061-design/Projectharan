"""
v27 STAGE 14 — spectral / Fiedler repo partitioner (a PARALLEL-DECOMPOSITION layer, not modularization).
=========================================================================================================
To fold (S13) and verify a huge repo in parallel we first cut it into WEAKLY-COUPLED chunks: minimizing
the edge cut = minimizing cross-chunk dependencies = maximizing how independently the chunks can be
processed. The classic tool is the Fiedler vector — the eigenvector of the 2nd-smallest eigenvalue of
the graph Laplacian L = D − A — whose sign/median split approximates the normalized cut.

★ CRITICAL HONESTY (§0.7, §5.5) ★: spectral is used ONLY as a decomposition SEED. The one measured study
that used spectral for *module-structure recovery* (Shokoufandeh 2004) found it WORSE than hill-climbing,
so we make NO module-quality claim. The cut is then improved by a Kernighan–Lin / Fiduccia–Mattheyses-style
local refinement (the "METIS-class" multilevel step). The deliverable is a balanced, low-cross-dependency
chunking for parallelism — nothing about "good modules".

Pure-Python (no numpy here, §0.5): L·x is computed from an adjacency list; the Fiedler vector comes from
power iteration on M = cI − L with the all-ones (λ=0) direction deflated out each step. Honest scale: this
is fine for the thousands-of-nodes range; for production-size graphs use numpy/scipy or real METIS — that
regime is [BLOCKED: pure-Python scale] and labeled.

Parallel gain is Amdahl-/synchronization-bounded by the cross-chunk dependencies (reported as `cross_deps`).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

MAX_PRACTICAL_N = 4000   # beyond this, pure-Python power iteration is [BLOCKED: scale] — use numpy/METIS


Graph = Dict[int, List[int]]   # node -> neighbors (undirected; edges symmetric)


@dataclass
class Partition:
    parts: List[int]                 # part id per node
    k: int
    cut: int                         # cross-part (cross-chunk) edges = cross dependencies
    method: str                      # "spectral-seed+KL" | "balanced-seed+KL" | "trivial"
    sizes: List[int] = field(default_factory=list)
    blocked: bool = False
    detail: str = ""

    @property
    def cross_deps(self) -> int:
        return self.cut

    def chunks(self) -> List[List[int]]:
        out: List[List[int]] = [[] for _ in range(self.k)]
        for node, p in enumerate(self.parts):
            out[p].append(node)
        return out

    def __str__(self):
        return (f"{self.method}: k={self.k} chunks {self.sizes}, cut={self.cut} cross-deps "
                f"({'BLOCKED scale' if self.blocked else 'measured'}){' — ' + self.detail if self.detail else ''}")


# ── graph helpers ───────────────────────────────────────────────────────────────────────────────────
def _normalize(graph: Graph) -> Tuple[int, Dict[int, List[int]], List[Tuple[int, int]]]:
    nodes = sorted(graph)
    idx = {n: i for i, n in enumerate(nodes)}
    adj: Dict[int, List[int]] = {i: [] for i in range(len(nodes))}
    edges = set()
    for n in nodes:
        for m in graph[n]:
            if m in idx and idx[m] != idx[n]:
                a, b = sorted((idx[n], idx[m]))
                edges.add((a, b))
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    return len(nodes), adj, sorted(edges)


def cut_size(parts: Sequence[int], edges: List[Tuple[int, int]]) -> int:
    return sum(1 for a, b in edges if parts[a] != parts[b])


# ── Fiedler vector via deflated power iteration on M = cI − L (pure Python) ──────────────────────────
def _l_matvec(adj: Dict[int, List[int]], x: List[float]) -> List[float]:
    # (L x)_i = deg_i * x_i − Σ_{j~i} x_j
    return [len(adj[i]) * x[i] - sum(x[j] for j in adj[i]) for i in range(len(x))]


def fiedler_vector(n: int, adj: Dict[int, List[int]], iters: int = 300, seed: int = 12345) -> List[float]:
    if n <= 1:
        return [0.0] * n
    c = 2.0 * max((len(adj[i]) for i in range(n)), default=1) + 1.0   # c ≥ λ_max(L) (≤ 2·d_max)
    rng = random.Random(seed)
    x = [rng.uniform(-1.0, 1.0) for _ in range(n)]
    def deflate(v):                       # remove the all-ones (λ=0) component, then normalize
        m = sum(v) / n
        v = [vi - m for vi in v]
        nrm = math.sqrt(sum(vi * vi for vi in v)) or 1.0
        return [vi / nrm for vi in v]
    x = deflate(x)
    prev = None
    for _ in range(iters):
        lx = _l_matvec(adj, x)
        mx = [c * x[i] - lx[i] for i in range(n)]   # M x = (cI − L) x  → dominant (post-deflation) = Fiedler
        x = deflate(mx)
        if prev is not None:
            drift = sum(abs(x[i] - prev[i]) for i in range(n)) + sum(abs(x[i] + prev[i]) for i in range(n))
            if min(drift, abs(drift)) < 1e-9:
                break
        prev = x
    return x


# ── Kernighan–Lin / FM-style refinement (the "METIS-class" local improvement) ───────────────────────
def _kl_refine(parts: List[int], adj: Dict[int, List[int]], edges: List[Tuple[int, int]],
               keep_balance: bool = True, max_passes: int = 6) -> List[int]:
    parts = list(parts)
    for _ in range(max_passes):
        best_gain, best_pair = 0, None
        zeros = [i for i, p in enumerate(parts) if p == 0]
        ones = [i for i, p in enumerate(parts) if p == 1]
        def node_gain(i):                 # reduction in cut if node i flips sides
            same = sum(1 for j in adj[i] if parts[j] == parts[i])
            other = sum(1 for j in adj[i] if parts[j] != parts[i])
            return other - same
        if keep_balance:                  # swap a 0-node with a 1-node (size-preserving)
            for a in zeros:
                for b in ones:
                    g = node_gain(a) + node_gain(b) - (2 if b in adj[a] else 0)
                    if g > best_gain:
                        best_gain, best_pair = g, (a, b)
            if best_pair is None:
                break
            a, b = best_pair
            parts[a], parts[b] = 1, 0
        else:
            gi = max(range(len(parts)), key=node_gain)
            if node_gain(gi) <= 0:
                break
            parts[gi] ^= 1
    return parts


# ── public: bisection + recursive k-way ─────────────────────────────────────────────────────────────
def _bisect(n: int, adj: Dict[int, List[int]], edges: List[Tuple[int, int]]) -> Tuple[List[int], str]:
    if n <= 1:
        return [0] * n, "trivial"
    fv = fiedler_vector(n, adj)
    order = sorted(range(n), key=lambda i: fv[i])
    parts = [0] * n
    for rank, node in enumerate(order):       # median split → balanced seed
        parts[node] = 0 if rank < n // 2 else 1
    method = "spectral-seed+KL"
    if len(set(parts)) == 1:                  # degenerate Fiedler → balanced fallback seed
        parts = [0 if i < n // 2 else 1 for i in range(n)]
        method = "balanced-seed+KL"
    refined = _kl_refine(parts, adj, edges, keep_balance=True)
    if cut_size(refined, edges) <= cut_size(parts, edges):
        parts = refined
    return parts, method


def partition(graph: Graph, k: int = 2) -> Partition:
    """Partition the dependency graph into k weakly-coupled chunks (spectral seed + KL refinement)."""
    n, adj, edges = _normalize(graph)
    blocked = n > MAX_PRACTICAL_N
    if n == 0:
        return Partition([], 0, 0, "trivial", [], False, "empty graph")
    if k <= 1 or n <= 1:
        return Partition([0] * n, 1, 0, "trivial", [n], blocked)
    if blocked:
        # honest short-circuit: we do NOT run pure-Python power iteration at production scale (we will not
        # pretend to "measure" it). A balanced placeholder is returned, explicitly labeled [BLOCKED: scale].
        parts = [0 if i < n // 2 else 1 for i in range(n)]
        return Partition(parts, 2, cut_size(parts, edges), "BLOCKED-scale", [n // 2, n - n // 2], True,
                         f"n={n} > {MAX_PRACTICAL_N}: pure-Python spectral is scale-limited — use numpy/scipy "
                         "or METIS for production size (not computed here)")
    parts, method = _bisect(n, adj, edges)
    # recursive bisection for k > 2: repeatedly split the largest current chunk
    next_id = 2
    while next_id < k:
        sizes = [sum(1 for p in parts if p == g) for g in range(next_id)]
        target = max(range(next_id), key=lambda g: sizes[g])
        members = sorted(i for i in range(n) if parts[i] == target)
        if len(members) <= 1:
            break
        remap = {old: new for new, old in enumerate(members)}      # subgraph induced on the target chunk
        subg = {remap[i]: [remap[j] for j in adj[i] if parts[j] == target] for i in members}
        sp, _m = _bisect(len(members), subg, _edges_of(subg))
        for old in members:                                        # side 1 of the split → new chunk id
            if sp[remap[old]] == 1:
                parts[old] = next_id
        next_id += 1
    sizes = [sum(1 for p in parts if p == g) for g in range(max(parts) + 1)]
    detail = "" if not blocked else f"n={n} > {MAX_PRACTICAL_N}: pure-Python power iteration is scale-limited"
    return Partition(parts, max(parts) + 1, cut_size(parts, edges), method, sizes, blocked, detail)


def _edges_of(adj: Dict[int, List[int]]) -> List[Tuple[int, int]]:
    e = set()
    for i in adj:
        for j in adj[i]:
            if i != j:
                e.add(tuple(sorted((i, j))))
    return sorted(e)


def parallel_schedule(p: Partition) -> Dict[str, object]:
    """The chunks are independent work units (fold/verify in parallel, S13); `cross_deps` edges must be
    reconciled across chunks (the Amdahl/sync ceiling on the achievable parallel speedup)."""
    chunks = p.chunks()
    return {"independent_chunks": chunks, "n_chunks": p.k, "cross_deps": p.cross_deps,
            "max_parallel_speedup_ceiling": p.k if p.cross_deps == 0 else
            round(sum(len(c) for c in chunks) / max(max((len(c) for c in chunks), default=1), 1), 2)}
