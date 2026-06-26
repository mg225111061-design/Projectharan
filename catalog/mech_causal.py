"""
MECHANISM 16 — Causal-structure recovery / relational-asymmetric (in-repo; no causal-discovery libraries).
============================================================================================================
The asymmetric, intervention-supporting structure the fourteen (symmetric) mechanisms lack. The EXACT ledger is
DO-CALCULUS IDENTIFIABILITY relative to a DECLARED DAG: given a causal graph (with latents) and a query
P(Y|do(X)), find an observed back-door adjustment set by EXACT d-separation (Bayes-ball) and emit the do-free
estimand — OR certify non-identifiability (a hedge). This is zero-false-positive RELATIVE TO the declared graph.

★ HARD DISCIPLINE (binding, in every certificate): faithfulness and the graph structure are DECLARED AXIOMS,
  NEVER certified from observation — non-strong-faithful distributions have positive Lebesgue measure
  (Uhler–Raskutti–Bühlmann–Yu 2013) and from observation alone only the CPDAG (Markov equivalence class) is
  recoverable, never the DAG generically (Verma–Pearl). "No causes in, no causes out" (Cartwright). The
  certificate EMITS its assumption set. A confounded query with no observed adjustment ⇒ DECLINE (hedge).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

import kernel_verdict as KV

_ASSUMPTIONS = ["causal Markov condition", "the declared DAG is correct (DECLARED axiom, not certified)",
                "faithfulness (DECLARED axiom — untestable in finite samples; positive-measure violations exist)",
                "declared latents are the only unobserved confounders"]


def _parents(edges, v) -> Set:
    return {u for (u, w) in edges if w == v}


def _children(edges, v) -> Set:
    return {w for (u, w) in edges if u == v}


def _descendants(edges, x) -> Set:
    seen, stack = set(), [x]
    while stack:
        u = stack.pop()
        for c in _children(edges, u):
            if c not in seen:
                seen.add(c); stack.append(c)
    return seen


def _ancestors(edges, base: Set) -> Set:
    anc = set(base)
    changed = True
    while changed:
        changed = False
        for (u, w) in edges:
            if w in anc and u not in anc:
                anc.add(u); changed = True
    return anc


def _d_separated(nodes, edges, X: Set, Y: Set, Z: Set) -> bool:
    """d-separation via the MORALIZED ANCESTRAL GRAPH (the standard, robust algorithm): restrict to An(X∪Y∪Z),
    marry co-parents, drop directions, remove Z, then X⊥Y|Z iff X and Y are disconnected in what remains."""
    from collections import deque
    if X & Y:
        return False
    relevant = _ancestors(edges, X | Y | Z)
    sub = [(u, w) for (u, w) in edges if u in relevant and w in relevant]
    adj: Dict[object, Set] = {v: set() for v in relevant}
    for (u, w) in sub:                                          # drop directions
        adj[u].add(w); adj[w].add(u)
    for v in relevant:                                          # marry parents (moralize)
        ps = [u for (u, w) in sub if w == v]
        for i in range(len(ps)):
            for j in range(i + 1, len(ps)):
                adj[ps[i]].add(ps[j]); adj[ps[j]].add(ps[i])
    start = [x for x in X if x not in Z]
    seen, q = set(start), deque(start)
    while q:
        n = q.popleft()
        if n in Y:
            return False                                       # a path survives ⇒ d-connected
        for m in adj.get(n, ()):
            if m not in Z and m not in seen:
                seen.add(m); q.append(m)
    return True


def _backdoor_adjustment(nodes, edges, observed: Set, X, Y) -> Optional[Set]:
    """Search for an OBSERVED back-door adjustment set Z: Z ⊆ observed non-descendants of X that d-separates X and Y
    in the back-door graph (X's outgoing edges removed). Returns Z (smallest tried) or None (non-identifiable here)."""
    desc_x = _descendants(edges, X) | {X}
    candidates = sorted(observed - desc_x - {Y})
    bd_edges = [(u, w) for (u, w) in edges if u != X]          # remove X's outgoing edges (the back-door graph)
    from itertools import combinations
    for r in range(0, len(candidates) + 1):
        for Z in combinations(candidates, r):
            if _d_separated(nodes, bd_edges, {X}, {Y}, set(Z)):
                return set(Z)
    return None


def causal_grade(spec: dict) -> KV.Verdict:
    """M16 — do-calculus identifiability relative to a DECLARED DAG. spec = {nodes, edges:[(u,v)], treatment,
    outcome, latents?}. EXACT iff an observed back-door adjustment identifies P(Y|do(X)) (estimand emitted, with the
    DECLARED assumption set); a confounded query with no observed adjustment ⇒ DECLINE (hedge — non-identifiable
    under the declared axioms). Observation-only ⇒ never a unique DAG (Verma–Pearl)."""
    if not (isinstance(spec, dict) and "edges" in spec and "treatment" in spec and "outcome" in spec):
        return KV.decline("causal: need {edges, treatment, outcome, [nodes, latents]}", "mech_causal")
    edges = [tuple(e) for e in spec["edges"]]
    nodes = set(spec.get("nodes") or {v for e in edges for v in e})
    latents = set(spec.get("latents") or [])
    observed = nodes - latents
    X, Y = spec["treatment"], spec["outcome"]
    if X not in nodes or Y not in nodes:
        return KV.decline("causal: treatment/outcome not in the graph", "mech_causal")
    if X in latents or Y in latents:
        return KV.decline("causal: treatment/outcome must be observed", "mech_causal")
    Z = _backdoor_adjustment(nodes, edges, observed, X, Y)
    if Z is None:
        return KV.decline(f"causal: P({Y}|do({X})) is NOT identifiable by an observed back-door adjustment under the "
                          f"declared graph (latents {sorted(latents) or 'none'}) ⇒ DECLINE (hedge). Assumptions: "
                          f"{_ASSUMPTIONS}", "mech_causal")
    estimand = (f"P({Y}|do({X})) = Σ_z P({Y}|{X}," + ",".join(sorted(Z)) + ")·P(" + ",".join(sorted(Z)) + ")") \
        if Z else f"P({Y}|do({X})) = P({Y}|{X})  (no adjustment needed — no open back-door path)"
    cert = KV.Cert(KV.EXACT, "causal_do_calculus", passed=True,
                   check_cost="exact d-separation (Bayes-ball) on the declared back-door graph",
                   detail=f"back-door adjustment Z={sorted(Z) or '∅'} d-separates {X},{Y} in the back-door graph ⇒ "
                          f"identifiable. ★ DECLARED axioms (not certified): {_ASSUMPTIONS}")
    return KV.exact({"identifiable": True, "adjustment_set": sorted(Z), "estimand": estimand,
                     "declared_assumptions": _ASSUMPTIONS}, "mech_causal",
                    "causal identifiability (do-calculus, relative to declared DAG)", cert)
