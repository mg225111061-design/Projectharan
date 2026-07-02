"""
§AU TW — tensor-network contraction = treewidth (variable elimination / junction tree). Net-new (no treewidth code
================================================================================================================
exists in the repo). A sum-product contraction (or marginalisation / DP-on-a-graph) has optimal cost O(exp(tw)),
tw = treewidth of the interaction graph (Markov–Shi 2008). When tw is small (sparse interactions) a variable
elimination in a min-fill order folds an exp(#indices) naive sum to exp(tw).

★ ∀-contraction = the distributive/associative law (variable elimination is exact — §0-a). The z3/exact gate is a
small-instance check: VE result ≡ the naive full sum (exact ℚ over domain d=2). ★ DECLINE when the induced width
exceeds the cap (exp(tw) blow-up) — incl. 2D grids whose treewidth grows (2D PEPS exact contraction is #P-hard,
Schuch–Wolf–Verstraete–Cirac 2007). Float ⇒ DECLINE.
"""
from __future__ import annotations

from fractions import Fraction
from itertools import product
from typing import Dict, List, Optional, Sequence, Tuple

import kernel_verdict as KV


def _interaction_graph(factors: List[dict]) -> Dict[int, set]:
    g: Dict[int, set] = {}
    for f in factors:
        vs = f["vars"]
        for v in vs:
            g.setdefault(v, set())
        for i in range(len(vs)):
            for j in range(i + 1, len(vs)):
                g[vs[i]].add(vs[j])
                g[vs[j]].add(vs[i])
    return g


def _min_fill_order(graph: Dict[int, set]) -> Tuple[List[int], int]:
    """Greedy min-fill elimination order; returns (order, induced_width). induced_width = max created-clique size − 1
    ≈ a treewidth upper bound."""
    g = {v: set(ns) for v, ns in graph.items()}
    order, width = [], 0
    while g:
        # pick the vertex whose elimination adds the fewest fill edges
        best, best_fill = None, None
        for v in g:
            nb = list(g[v])
            fill = sum(1 for i in range(len(nb)) for j in range(i + 1, len(nb)) if nb[j] not in g[nb[i]])
            if best_fill is None or fill < best_fill:
                best, best_fill = v, fill
        nb = list(g[best])
        width = max(width, len(nb))                       # clique size after elimination = |nb| (+self)
        for i in range(len(nb)):                          # connect neighbours (the fill-in)
            for j in range(i + 1, len(nb)):
                g[nb[i]].add(nb[j])
                g[nb[j]].add(nb[i])
        for u in nb:
            g[u].discard(best)
        del g[best]
        order.append(best)
    return order, width


def _naive_contract(factors: List[dict], nvars: int, d: int) -> Fraction:
    total = Fraction(0)
    for asg in product(range(d), repeat=nvars):
        prod = Fraction(1)
        for f in factors:
            prod *= f["vals"][tuple(asg[v] for v in f["vars"])]
        total += prod
    return total


def _ve_contract(factors: List[dict], order: List[int], d: int) -> Fraction:
    facs = [dict(vars=list(f["vars"]), vals=dict(f["vals"])) for f in factors]
    for v in order:
        involved = [f for f in facs if v in f["vars"]]
        rest = [f for f in facs if v not in f["vars"]]
        newvars = sorted(set().union(*[set(f["vars"]) for f in involved]) - {v}) if involved else []
        newvals: Dict[Tuple[int, ...], Fraction] = {}
        for asg in product(range(d), repeat=len(newvars)):
            amap = dict(zip(newvars, asg))
            s = Fraction(0)
            for vv in range(d):
                amap[v] = vv
                prod = Fraction(1)
                for f in involved:
                    prod *= f["vals"][tuple(amap[u] for u in f["vars"])]
                s += prod
            newvals[asg] = s
        facs = rest + [dict(vars=newvars, vals=newvals)]
    result = Fraction(1)
    for f in facs:                                        # remaining scalar factors (empty scope)
        result *= f["vals"][()]
    return result


def contract_grade(factors: Sequence[dict], nvars: int, tw_cap: int = 6, d: int = 2) -> KV.Verdict:
    """Fold a sum-product tensor contraction by variable elimination when the induced width ≤ tw_cap. EXACT (VE ≡
    naive sum, verified on the concrete instance over domain d); high treewidth (or 2D PEPS #P-hard) ⇒ DECLINE."""
    try:
        facs = [{"vars": list(f["vars"]), "vals": {tuple(k): Fraction(v) for k, v in f["vals"].items()}}
                for f in factors]
    except (ValueError, TypeError, KeyError):
        return KV.decline("contract: malformed/float factors ⇒ DECLINE", "tensor_contract")
    if any(isinstance(x, float) for f in factors for x in f.get("vals", {}).values()):
        return KV.decline("contract: float tensor entries ⇒ DECLINE (no float-EXACT)", "tensor_contract")
    graph = _interaction_graph(facs)
    for v in range(nvars):
        graph.setdefault(v, set())
    order, width = _min_fill_order(graph)
    if width > tw_cap:
        return KV.decline(f"contract: induced width {width} > cap {tw_cap} ⇒ O(exp(tw)) blow-up (dense / 2D-grid / "
                          f"expander; 2D PEPS exact contraction is #P-hard) ⇒ DECLINE", "tensor_contract")
    ve = _ve_contract(facs, order, d)
    naive = _naive_contract(facs, nvars, d)
    if ve != naive:                                       # exact small-instance check (defensive — VE is exact)
        return KV.decline("contract: variable elimination ≠ naive sum ⇒ DECLINE", "tensor_contract")
    cert = KV.Cert(KV.EXACT, "exact_replay", passed=True,
                   check_cost=f"min-fill width {width}; VE ≡ naive sum over domain d={d}",
                   detail=f"variable elimination (min-fill order) folds the sum-product exactly; induced width "
                          f"{width}≤{tw_cap} ⇒ O(exp(tw)) feasible; VE result ≡ naive full sum ✓")
    return KV.exact({"treewidth_ub": width, "value": str(ve)}, "tensor_contract",
                    f"O(exp(tw)) (tw≈{width}) vs O(exp(#idx)={nvars})", cert,
                    reason="Axis-A: sum-product/marginalisation recognized; Axis-B exp(#idx)→exp(tw), crossover when tw≪#idx")


def _chain_factors(n: int) -> Tuple[List[dict], int]:
    """A 1D chain (path) tensor network on n vars — low treewidth (=1)."""
    facs = []
    for i in range(n - 1):
        vals = {(a, b): Fraction((a + 2 * b + i + 1)) for a in range(2) for b in range(2)}
        facs.append({"vars": [i, i + 1], "vals": vals})
    return facs, n


def _grid_factors(r: int, c: int) -> Tuple[List[dict], int]:
    """A 2D grid tensor network (r×c) — treewidth ≈ min(r,c), grows with size (2D PEPS #P-hard regime)."""
    idx = lambda i, j: i * c + j
    facs = []
    for i in range(r):
        for j in range(c):
            if j + 1 < c:
                facs.append({"vars": [idx(i, j), idx(i, j + 1)],
                             "vals": {(a, b): Fraction(1 + a + b) for a in range(2) for b in range(2)}})
            if i + 1 < r:
                facs.append({"vars": [idx(i, j), idx(i + 1, j)],
                             "vals": {(a, b): Fraction(1 + a * 2 + b) for a in range(2) for b in range(2)}})
    return facs, r * c


def adversarial_battery() -> dict:
    """★ EXACT: a 1D chain (treewidth 1) folds — VE ≡ naive sum. ★★ DECLINE: a 6×6 2D grid (treewidth ≈6, the #P-hard
    PEPS regime) exceeds a small cap ⇒ DECLINE; float entries ⇒ DECLINE."""
    chain, nv = _chain_factors(8)
    chain_ok = contract_grade(chain, nv, tw_cap=4).status == KV.EXACT
    grid, gnv = _grid_factors(6, 6)
    grid_declines = contract_grade(grid, gnv, tw_cap=3).status == KV.DECLINE      # tw≈6 > 3
    smallgrid, snv = _grid_factors(2, 2)
    smallgrid_ok = contract_grade(smallgrid, snv, tw_cap=4).status == KV.EXACT    # tw small ⇒ folds + VE≡naive
    flt = contract_grade([{"vars": [0, 1], "vals": {(0, 0): 1.0, (0, 1): 1.0, (1, 0): 1.0, (1, 1): 1.0}}], 2)
    float_declines = flt.status == KV.DECLINE
    cases = {"chain_low_treewidth_folds": chain_ok, "grid_high_treewidth_declines": grid_declines,
             "small_grid_folds_VE_eq_naive": smallgrid_ok, "float_declines": float_declines}
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
