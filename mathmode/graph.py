"""
MATH-Ascent §B4 (arsenal) — GRAPH / DISCRETE MATH: shortest paths & bipartiteness, with constructive certificates.
==================================================================================================================
Discrete answers carry clean, cheap-to-check certificates:
  • SHORTEST PATHS (Bellman–Ford, exact integers) — the distance vector d is OPTIMAL iff d[source]=0, every edge
    satisfies d[v] ≤ d[u]+w (no edge can relax further — dual feasibility), and every reachable v is TIGHT via a
    predecessor edge d[v]=d[u]+w (the path realizes the distance). That triple is the LP-duality optimality
    certificate specialized to shortest paths; a negative cycle reachable from the source ⇒ no shortest path ⇒
    honest DECLINE (and we exhibit it).
  • BIPARTITENESS — a 2-coloring with no monochromatic edge PROVES bipartite (EXACT); otherwise an ODD CYCLE is a
    PROOF of non-bipartiteness (EXACT, constructive). Either way the certificate is exhibited and re-checked.
The computation is offloaded from the LLM; the certificate (not the search) licenses the grade. Exact integers.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import kernel_verdict as KV

Edge = Tuple[int, int, int]      # (u, v, weight)


def shortest_path_grade(n: int, edges: List[Edge], source: int) -> KV.Verdict:
    """Single-source shortest paths (Bellman–Ford, exact ints) + the optimality certificate. A reachable negative
    cycle ⇒ honest DECLINE (no shortest path)."""
    if not (0 <= source < n):
        return KV.decline(f"shortest_path: source {source} out of range ⇒ DECLINE", "graph.sp")
    INF = None
    dist: List[Optional[int]] = [INF] * n
    pred: List[Optional[Tuple[int, int]]] = [None] * n
    dist[source] = 0
    for _ in range(n - 1):
        for (u, v, w) in edges:
            if dist[u] is not None and (dist[v] is None or dist[u] + w < dist[v]):
                dist[v] = dist[u] + w
                pred[v] = (u, w)
    for (u, v, w) in edges:                                   # reachable negative cycle ⇒ no shortest path
        if dist[u] is not None and (dist[v] is None or dist[u] + w < dist[v]):
            return KV.decline("shortest_path: reachable negative cycle ⇒ no finite shortest path ⇒ DECLINE",
                              "graph.sp")
    # ★ the optimality certificate ★ : source=0, edge feasibility, reachable-node tightness
    feasible = all(dist[u] is None or dist[v] is not None and dist[v] <= dist[u] + w for (u, v, w) in edges)
    tight = all(v == source or dist[v] is None or (pred[v] is not None and dist[v] == dist[pred[v][0]] + pred[v][1])
                for v in range(n))
    if not (dist[source] == 0 and feasible and tight):
        return KV.decline("shortest_path: optimality certificate failed ⇒ DECLINE", "graph.sp")
    cert = KV.Cert(KV.EXACT, "shortest_path_optimality", passed=True, check_cost="O(E) feasibility + tightness",
                   detail="d[source]=0 ∧ ∀edge d[v]≤d[u]+w (dual feasible) ∧ reachable v tight d[v]=d[u]+w")
    return KV.exact(dist, "graph.sp", "Bellman–Ford O(VE), O(E) check", cert)


def _find_odd_cycle(n: int, adj: List[List[int]], color: List[int], start: int) -> Optional[List[int]]:
    """BFS 2-color from start; on a same-color edge (u,v), climb u and v to their LCA (by BFS depth) to
    reconstruct the odd cycle u→…→LCA→…→v plus the edge v–u (a constructive proof)."""
    from collections import deque
    parent = [-1] * n
    depth = [-1] * n
    color[start] = 0
    depth[start] = 0
    q = deque([start])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if color[v] == -1:
                color[v] = color[u] ^ 1
                parent[v] = u
                depth[v] = depth[u] + 1
                q.append(v)
            elif color[v] == color[u]:                       # same-color edge ⇒ odd cycle through u, v
                a, b = u, v
                pa, pb = [a], [b]
                while depth[a] > depth[b]:
                    a = parent[a]; pa.append(a)
                while depth[b] > depth[a]:
                    b = parent[b]; pb.append(b)
                while a != b:                                # both at equal depth, climb together to the LCA
                    a = parent[a]; pa.append(a)
                    b = parent[b]; pb.append(b)
                return pa + pb[-2::-1]                        # [u…LCA] + [LCA-child…v]; edge v–u closes it
    return None


def bipartite_grade(n: int, edges: List[Tuple[int, int]]) -> KV.Verdict:
    """Bipartite? EXACT either way: a valid 2-coloring (no monochromatic edge) proves YES; an odd cycle proves NO."""
    adj: List[List[int]] = [[] for _ in range(n)]
    for (u, v) in edges:
        adj[u].append(v)
        adj[v].append(u)
    color = [-1] * n
    for s in range(n):
        if color[s] == -1:
            cyc = _find_odd_cycle(n, adj, color, s)
            if cyc is not None:
                m = len(cyc)
                if m % 2 == 1 and all(cyc[(i + 1) % m] in adj[cyc[i]] for i in range(m)):   # re-check the proof
                    cert = KV.Cert(KV.EXACT, "odd_cycle_witness", passed=True, check_cost="O(len) cycle recheck",
                                   detail=f"odd cycle {cyc} (length {m}) ⇒ NOT bipartite (proof)")
                    return KV.exact({"bipartite": False, "odd_cycle": cyc}, "graph.bipartite", "BFS", cert)
    # verify the 2-coloring has no monochromatic edge (the YES certificate)
    if any(color[u] == color[v] for (u, v) in edges):
        return KV.decline("bipartite: 2-coloring left a monochromatic edge ⇒ DECLINE", "graph.bipartite")
    cert = KV.Cert(KV.EXACT, "two_coloring", passed=True, check_cost="O(E) edge recheck",
                   detail="a valid 2-coloring (every edge bichromatic) ⇒ bipartite (proof)")
    return KV.exact({"bipartite": True, "coloring": color}, "graph.bipartite", "BFS O(V+E)", cert)


def solve(problem: dict) -> KV.Verdict:
    op = problem.get("op")
    if op == "shortest_path":
        return shortest_path_grade(problem["n"], [tuple(e) for e in problem["edges"]], problem["source"])
    if op == "bipartite":
        return bipartite_grade(problem["n"], [tuple(e) for e in problem["edges"]])
    return KV.decline(f"graph: unknown op {op!r} ⇒ DECLINE", "graph")
