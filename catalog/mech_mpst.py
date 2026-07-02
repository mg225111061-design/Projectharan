"""
POST-CONSOLIDATION PHASE 2a — MPST: MULTIPARTY SESSION TYPES (global protocol → endpoint projection + safety).
================================================================================================================
A GLOBAL protocol type G describes a whole multiparty interaction; PROJECTION extracts each role's LOCAL (endpoint)
type. Well-formedness = the projection is defined for every role (uninvolved roles MERGE across branches) AND the
composed endpoints realise G with COMMUNICATION SAFETY (no deadlock, no stuck receive). The fold: G → {endpoint
types} + a safety certificate, verified by SYNCHRONOUS-PRODUCT REACHABILITY (in-repo BFS, NO external automata lib).

★ THE HONEST ADJUDICATION (admit M23 only if z3-closed in-repo without external automata AND not a faithful
reduction to an existing mechanism — adjudicated BY BUILDING):
  gate 2 (z3-closed / in-repo no-external-automata): ✓ — safety is a FINITE-state reachability witness (BFS over
      the product), decidable in-repo, no external automata engine.
  gate 4 (dependency-free): ✓ — pure stdlib.
  gate 1 (DISTINCT IN KIND): ✗ — MPST well-formedness is a LOCAL-TO-GLOBAL COHERENCE: the global protocol is
      recoverable iff the local projections glue consistently; an un-projectable choice (uninvolved role cannot
      merge the branches) is precisely a GLUING OBSTRUCTION. That is M17's kind (sheaf cohomology: H⁰ global section
      / H¹ gluing obstruction; M17 generalises M14). The deadlock-freedom witness is in turn an M13-style safety
      invariant. MPST emits NO new certificate kind. ⇒ DEMOTE: a FACE of M17 (parent mechanism 17), with an M13
      safety-reachability lineage. NOT a new mechanism (no count++); M23 is NOT admitted.

A non-well-formed global type (un-mergeable projection) or a composition that DEADLOCKs ⇒ DECLINE (never a false
"safe protocol"). Precision 1.0.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

import kernel_verdict as KV

PARENT_MECHANISM = 17   # local-to-global gluing/coherence — M17's kind (deadlock-freedom = M13-style safety witness)


class NotProjectable(Exception):
    pass


def roles_of(G) -> Set[str]:
    tag = G[0]
    if tag == "end":
        return set()
    if tag == "msg":
        _, p, q, _l, cont = G
        return {p, q} | roles_of(cont)
    if tag == "choice":
        _, p, q, branches = G
        return {p, q} | set().union(*(roles_of(c) for _, c in branches))
    raise ValueError(G)


def project(G, r: str):
    """Project the global type G onto role r → a local (endpoint) type. Raises NotProjectable when an uninvolved
    role cannot MERGE the branches of a choice (the gluing obstruction = a non-well-formed protocol)."""
    tag = G[0]
    if tag == "end":
        return ("end",)
    if tag == "msg":
        _, p, q, label, cont = G
        sub = project(cont, r)
        if r == p:
            return ("send", q, label, sub)
        if r == q:
            return ("recv", p, label, sub)
        return sub
    if tag == "choice":
        _, p, q, branches = G
        projected = tuple((label, project(cont, r)) for label, cont in branches)
        if r == p:
            return ("select", q, projected)
        if r == q:
            return ("branch", p, projected)
        # uninvolved: all branches must project to the SAME local type (mergeable) — else NOT well-formed
        locals_ = [pl for _, pl in projected]
        if any(pl != locals_[0] for pl in locals_):
            raise NotProjectable(f"role {r} cannot merge the branches of a choice by {p}→{q} (gluing obstruction)")
        return locals_[0]
    raise ValueError(G)


# ── synchronous-product reachability: communication safety (deadlock freedom) of the projected endpoints ──
def _enabled(local) -> List[Tuple[str, str, str, object]]:
    """Actions a local type offers: ('send'|'select', peer, label, next) or ('recv'|'branch', peer, label, next)."""
    tag = local[0]
    if tag in ("send", "recv"):
        _, peer, label, nxt = local
        return [(tag, peer, label, nxt)]
    if tag in ("select", "branch"):
        _, peer, branches = local
        return [(tag, peer, label, nxt) for label, nxt in branches]
    return []                                                     # end


def safety(endpoints: Dict[str, object]) -> Tuple[bool, Optional[str]]:
    """BFS the synchronous product of the endpoint types. A transition fires when a sender (send/select to q:ℓ) and
    receiver (recv/branch from p:ℓ) agree on peer+label. SAFE iff every reachable state is either all-`end` or has an
    enabled matched communication (no deadlock / stuck receive)."""
    roles = sorted(endpoints)
    start = tuple(endpoints[r] for r in roles)
    seen: Set[tuple] = set()
    stack = [start]
    while stack:
        state = stack.pop()
        if state in seen:
            continue
        seen.add(state)
        if all(s[0] == "end" for s in state):
            continue                                             # clean termination
        fired = False
        for i, ri in enumerate(roles):
            for (ta, qa, la, na) in _enabled(state[i]):
                if ta not in ("send", "select"):
                    continue
                j = roles.index(qa)
                for (tb, qb, lb, nb) in _enabled(state[j]):
                    if tb in ("recv", "branch") and qb == ri and lb == la:
                        nxt = list(state)
                        nxt[i], nxt[j] = na, nb
                        stack.append(tuple(nxt))
                        fired = True
        if not fired:
            return False, f"deadlock: reachable non-terminal state with no enabled communication ({[s[0] for s in state]})"
    return True, None


def mpst_grade(spec: dict) -> KV.Verdict:
    """Project a global protocol type onto its roles and certify communication safety. spec = {global: G} with G a
    nested ('msg', p, q, label, cont) / ('choice', p, q, [(label, cont)…]) / ('end',). EXACT iff every role projects
    (well-formed) AND the synchronous product is deadlock-free; un-projectable or deadlocking ⇒ DECLINE. DEMOTES to a
    FACE of M17 (local-to-global gluing; M13 safety lineage)."""
    if not (isinstance(spec, dict) and "global" in spec):
        return KV.decline("mpst: need {global: G} (a nested msg/choice/end global type)", "mech_mpst")
    G = spec["global"]
    try:
        roles = sorted(roles_of(G))
        endpoints = {r: project(G, r) for r in roles}
    except NotProjectable as e:
        return KV.decline(f"mpst: global type NOT well-formed — {e} ⇒ DECLINE", "mech_mpst")
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"mpst: malformed global type ({type(e).__name__}) ⇒ DECLINE", "mech_mpst")
    safe, why = safety(endpoints)
    if not safe:
        return KV.decline(f"mpst: projected endpoints are UNSAFE — {why} ⇒ DECLINE", "mech_mpst")
    cert = KV.Cert(KV.EXACT, "mpst_projection_coherence", passed=True,
                   check_cost="syntactic projection (all roles merge) + synchronous-product BFS deadlock-freedom "
                              "(in-repo, no external automata)",
                   detail=f"{len(roles)} roles projected to coherent endpoints; the composition is deadlock-free — a "
                          "LOCAL-TO-GLOBAL gluing (the global protocol = the coherent gluing of the local sections; "
                          "FACE of M17) with an M13-style safety-reachability witness")
    return KV.exact({"parent_mechanism": PARENT_MECHANISM, "face": "mpst", "roles": roles,
                     "endpoints": {r: _flatten(endpoints[r]) for r in roles}, "deadlock_free": True},
                    "mech_mpst", "MPST projection + safety → M17 face", cert)


def _flatten(local) -> str:
    tag = local[0]
    if tag == "end":
        return "end"
    if tag in ("send", "recv"):
        return f"{tag} {local[2]}→{local[1]}; {_flatten(local[3])}" if tag == "send" else f"{tag} {local[2]}←{local[1]}; {_flatten(local[3])}"
    if tag in ("select", "branch"):
        return f"{tag}({local[1]}){{" + " | ".join(f"{lbl}: {_flatten(nxt)}" for lbl, nxt in local[2]) + "}"
    return "?"


def adjudication() -> dict:
    """Honest gate-by-gate: z3-closed/in-repo ✓, dependency-free ✓, but FAILS distinct-in-kind (local-to-global
    gluing = M17; deadlock-freedom = M13 safety) ⇒ DEMOTE to a FACE of M17; M23 NOT admitted."""
    return {"candidate": "MPST (multiparty session types)", "z3_closed_in_repo": True, "no_external_automata": True,
            "dependency_free": True, "distinct_in_kind": False, "verdict": "DEMOTE → FACE of M17 (M23 not admitted)",
            "reason": "MPST well-formedness is a LOCAL-TO-GLOBAL coherence (an un-projectable choice = a gluing "
                      "obstruction = M17's H¹); the deadlock-freedom witness is an M13-style safety invariant. No new "
                      "certificate kind ⇒ a FACE of M17, not a new mechanism"}
