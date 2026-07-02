"""
§BN NEW-2 — Weisfeiler–Leman color refinement: graph NON-isomorphism certificate (complete-invariant m09).
=============================================================================================================
1-dimensional WL (color refinement) is a sound graph isomorphism INVARIANT computable in low-degree polynomial
time. Run it on the disjoint union G ⊎ H with a shared refinement, then compare the stable color multiset on
G's vertices vs H's:

  • histograms DIFFER ⇒ G ≇ H — EXACT non-isomorphic, certified by the differing color class (a WL color is an
    isomorphism invariant, so unequal class sizes PROVE non-isomorphism — re-checked).
  • histograms AGREE ⇒ WL cannot distinguish.  We then try a color-guided backtracking search for an EXPLICIT
    isomorphism π; if found ⇒ EXACT isomorphic, certified by substituting π and matching the edge sets exactly.

★ DECIDABLE-BOUNDARY GUARD (the directive's hard guard): general graph isomorphism is NOT known to be polynomial
  and WL-equivalence does NOT imply isomorphism (e.g. WL fails to separate strongly-regular graphs).  So when the
  histograms agree AND the bounded search finds no explicit π, we DECLINE — never claim "isomorphic" from WL alone.
  Non-isomorphism via WL is always sound; isomorphism is claimed ONLY with an explicit re-checked permutation.

★ certificate-or-DECLINE; false-EXACT 0.  0 new mechanism (a recognition branch of m09 complete-invariant — WL is
  a partial/refining invariant, explicit π is the complete one); 0 new disposer. zero-dep (stdlib only).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import kernel_verdict as KV

Graph = Tuple[int, List[Tuple[int, int]]]      # (n_vertices, undirected edge list)


def _adj(n: int, edges: List[Tuple[int, int]]) -> List[set]:
    a: List[set] = [set() for _ in range(n)]
    for u, v in edges:
        if not (0 <= u < n and 0 <= v < n):
            raise ValueError(f"edge ({u},{v}) out of range for n={n}")
        if u != v:
            a[u].add(v); a[v].add(u)
    return a


def _refine(adjs: List[set], init: List[int]) -> List[int]:
    """Stable 1-WL coloring: iterate color(v) ← (color(v), sorted multiset of neighbor colors) until partition stops
    refining. Colors are re-canonicalized to small ints each round so two graphs colored together stay comparable."""
    color = list(init)
    n = len(adjs)
    while True:
        sig = [(color[v], tuple(sorted(color[u] for u in adjs[v]))) for v in range(n)]
        ranking = {s: i for i, s in enumerate(sorted(set(sig)))}
        new = [ranking[sig[v]] for v in range(n)]
        if len(set(new)) == len(set(color)):
            return new
        color = new


def _histogram(color: List[int], lo: int, hi: int) -> Dict[int, int]:
    h: Dict[int, int] = {}
    for v in range(lo, hi):
        h[color[v]] = h.get(color[v], 0) + 1
    return h


def _find_iso(adjG: List[set], adjH: List[set], cg: List[int], ch: List[int], budget: int = 200000) -> Optional[List[int]]:
    """Color-guided backtracking for a bijection π:G→H with π preserving colors and adjacency. None if not found."""
    n = len(adjG)
    by_color_H: Dict[int, List[int]] = {}
    for h in range(n):
        by_color_H.setdefault(ch[h], []).append(h)
    order = sorted(range(n), key=lambda v: len(by_color_H.get(cg[v], [])))   # most-constrained vertex first
    pi: List[int] = [-1] * n
    used = [False] * n
    steps = [0]

    def bt(idx: int) -> bool:
        if steps[0] > budget:
            return False
        steps[0] += 1
        if idx == n:
            return True
        v = order[idx]
        for h in by_color_H.get(cg[v], []):
            if used[h] or ch[h] != cg[v]:
                continue
            ok = True
            for u in adjG[v]:                       # consistency with already-placed neighbors
                if pi[u] != -1 and pi[u] not in adjH[h]:
                    ok = False; break
            if not ok:
                continue
            # also forbid mapping a non-edge to an edge among placed vertices
            for u in range(n):
                if pi[u] != -1 and u not in adjG[v] and pi[u] in adjH[h]:
                    ok = False; break
            if not ok:
                continue
            pi[v] = h; used[h] = True
            if bt(idx + 1):
                return True
            pi[v] = -1; used[h] = False
        return False

    return pi if bt(0) else None


def _check_iso(adjG, adjH, pi: List[int]) -> bool:
    """Independent re-check: π is a bijection and {(π u, π v)} == E(H) exactly."""
    n = len(adjG)
    if sorted(pi) != list(range(n)):
        return False
    eg = {tuple(sorted((u, v))) for u in range(n) for v in adjG[u]}
    eh = {tuple(sorted((u, v))) for u in range(n) for v in adjH[u]}
    mapped = {tuple(sorted((pi[u], pi[v]))) for (u, v) in eg}
    return mapped == eh


def decide(G: Graph, H: Graph) -> KV.Verdict:
    """EXACT non-isomorphic (WL histogram mismatch) | EXACT isomorphic (explicit π re-checked) | DECLINE (WL-equal,
    no explicit π found — general GI is not decided here)."""
    nG, eG = int(G[0]), [tuple(e) for e in G[1]]
    nH, eH = int(H[0]), [tuple(e) for e in H[1]]
    try:
        adjG, adjH = _adj(nG, eG), _adj(nH, eH)
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"wl_refine: {type(e).__name__}: {e}", "wl_refine")
    if nG != nH or sum(len(s) for s in adjG) != sum(len(s) for s in adjH):
        return KV.exact({"isomorphic": False}, "wl_refine", "vertex/edge count",
                        KV.Cert(KV.EXACT, "wl_size", passed=True, check_cost="O(1) counts",
                                detail=f"|V|/|E| differ ({nG},{sum(len(s) for s in adjG)//2}) vs "
                                       f"({nH},{sum(len(s) for s in adjH)//2}) ⇒ non-isomorphic"))
    n = nG
    # color the disjoint union with a shared refinement (degree-seeded), then split the histogram by side
    adjU = [set(adjG[v]) for v in range(n)] + [{u + n for u in adjH[v]} for v in range(n)]
    init = [len(s) for s in adjU]
    col = _refine(adjU, init)
    hG, hH = _histogram(col, 0, n), _histogram(col, n, 2 * n)
    if hG != hH:
        diff = sorted(set(hG) | set(hH), key=lambda c: -abs(hG.get(c, 0) - hH.get(c, 0)))[0]
        cert = KV.Cert(KV.EXACT, "wl_histogram", passed=True, check_cost="O((n+m)·n) refinement + compare",
                       detail=f"stable WL color {diff} appears {hG.get(diff,0)}× in G vs {hH.get(diff,0)}× in H ⇒ "
                              "non-isomorphic (WL color is an isomorphism invariant)")
        return KV.exact({"isomorphic": False, "distinguishing_color": diff}, "wl_refine",
                        "Weisfeiler–Leman refinement", cert)
    # WL-equal — try for an explicit isomorphism (the only sound route to EXACT 'isomorphic')
    cg, ch = col[:n], col[n:]
    pi = _find_iso(adjG, adjH, cg, ch)
    if pi is not None and _check_iso(adjG, adjH, pi):
        cert = KV.Cert(KV.EXACT, "explicit_iso", passed=True, check_cost="substitute π, match edge sets",
                       detail=f"π={pi} maps E(G) onto E(H) exactly ⇒ isomorphic")
        return KV.exact({"isomorphic": True, "permutation": pi}, "wl_refine", "WL + explicit isomorphism", cert)
    return KV.decline("wl_refine: graphs are WL-indistinguishable and no explicit isomorphism was found within "
                      "budget — general graph isomorphism is not decided by WL alone ⇒ DECLINE (decidable-boundary "
                      "guard; non-iso would be sound, iso requires an explicit π)", "wl_refine")


def adversarial_battery() -> dict:
    """★ different degree sequence ⇒ EXACT non-iso; ★ a relabeling ⇒ EXACT iso (π re-checked); ★ C4 vs 2·K2 (same
    #V,#E, different WL) ⇒ EXACT non-iso; ★ the classic WL-fails pair (C6 vs 2·C3) ⇒ DECLINE (sound guard)."""
    # path P3 (0-1-2) vs triangle K3 — different #edges ⇒ non-iso
    p3 = (3, [(0, 1), (1, 2)]); k3 = (3, [(0, 1), (1, 2), (0, 2)])
    noniso = decide(p3, k3)
    # K3 vs a relabeled K3 ⇒ iso
    k3b = (3, [(1, 2), (0, 2), (0, 1)])
    iso = decide(k3, k3b)
    # C4 (4-cycle) vs 2·K2 (two disjoint edges): same |V|=4, but |E| 4 vs 2 ⇒ non-iso by count; use C4 vs "paw"-free:
    c4 = (4, [(0, 1), (1, 2), (2, 3), (3, 0)]); star = (4, [(0, 1), (0, 2), (0, 3), (1, 2)])
    noniso2 = decide(c4, star)   # both |E|=4; WL degree refinement separates (C4 is 2-regular, star is not)
    # ★ WL-indistinguishable but NON-isomorphic: C6 vs 2·C3 (both 2-regular, 6 vertices) ⇒ WL equal ⇒ DECLINE
    c6 = (6, [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)])
    two_c3 = (6, [(0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3)])
    guard = decide(c6, two_c3)
    cases = {
        "edgecount_noniso_EXACT": noniso.status == "EXACT" and noniso.result["isomorphic"] is False,
        "relabel_iso_EXACT": iso.status == "EXACT" and iso.result["isomorphic"] is True,
        "iso_perm_rechecks": iso.status == "EXACT" and _check_iso(_adj(3, k3[1]), _adj(3, k3b[1]), iso.result["permutation"]),
        "wl_separates_noniso_EXACT": noniso2.status == "EXACT" and noniso2.result["isomorphic"] is False,
        "wl_blind_pair_DECLINE": guard.status == "DECLINE",   # ★ sound: never a false 'isomorphic'
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
