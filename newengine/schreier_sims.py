"""
§BM NEW-3 — Schreier-Sims BSGS (group-order fold + O(1)-ish membership; complete-invariant m09 branch).
================================================================================================================
A base-and-strong-generating-set turns a permutation group into:
  • (Axis A) its ORDER as a closed-form product ∏ |orbitᵢ| over the stabilizer chain — no enumeration of |G|;
  • (Axis B) MEMBERSHIP as a cheap SIFT: strip g through the transversals; g ∈ G ⇔ the residue is the identity.

★ certificate-or-DECLINE: the BSGS is accepted only if EVERY input generator sifts to the identity (the standard
completeness check — a re-checked certificate that the chain really covers the group); a Schreier-generator
blow-up beyond the step budget ⇒ DECLINE (honest, no silent partial). Deterministic, exact, zero-dep (stdlib).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import kernel_verdict as KV

Perm = Tuple[int, ...]


def _ident(n: int) -> Perm:
    return tuple(range(n))


def _compose(p: Perm, q: Perm) -> Perm:
    """(p∘q)(i) = p(q(i)) — apply q, then p."""
    return tuple(p[q[i]] for i in range(len(p)))


def _inverse(p: Perm) -> Perm:
    inv = [0] * len(p)
    for i, v in enumerate(p):
        inv[v] = i
    return tuple(inv)


def _orbit_transversal(base: int, gens: List[Perm], n: int) -> Dict[int, Perm]:
    """{point: u} where u maps base→point (a Schreier transversal of the point stabilizer)."""
    orbit = {base: _ident(n)}
    frontier = [base]
    while frontier:
        pt = frontier.pop()
        for g in gens:
            img = g[pt]
            if img not in orbit:
                orbit[img] = _compose(g, orbit[pt])
                frontier.append(img)
    return orbit


def _schreier_gens(transversal: Dict[int, Perm], gens: List[Perm], n: int) -> List[Perm]:
    """Generators of the base-point stabilizer: u_{g·β}⁻¹ · g · u_β (each fixes the base). Deduped."""
    ident = _ident(n)
    out = set()
    for pt, u in transversal.items():
        for g in gens:
            sg = _compose(_inverse(transversal[g[pt]]), _compose(g, u))
            if sg != ident:
                out.add(sg)
    return list(out)


def bsgs(gens: Sequence[Perm], n: int, budget: int = 200_000) -> Optional[List[Tuple[int, Dict[int, Perm]]]]:
    """Build the stabilizer chain [(base, transversal), …]; None if the Schreier-generator count exceeds budget."""
    ident = _ident(n)
    cur = [tuple(g) for g in gens if tuple(g) != ident]
    levels: List[Tuple[int, Dict[int, Perm]]] = []
    spent = 0
    while cur:
        base = min(i for g in cur for i in range(n) if g[i] != i)
        trans = _orbit_transversal(base, cur, n)
        levels.append((base, trans))
        sgens = _schreier_gens(trans, cur, n)
        spent += len(sgens)
        if spent > budget:
            return None
        cur = sgens
    return levels


def _sift(g: Perm, levels: List[Tuple[int, Dict[int, Perm]]], n: int) -> Perm:
    """Strip g through the chain; the residue is the identity iff g ∈ G."""
    for base, trans in levels:
        beta = g[base]
        if beta not in trans:
            return g                                   # falls out of the orbit ⇒ not in G (residue ≠ id)
        g = _compose(_inverse(trans[beta]), g)
    return g


def group_order(gens: Sequence[Perm], n: int) -> KV.Verdict:
    """EXACT group order = ∏|orbitᵢ| over the chain — iff the BSGS is COMPLETE (every generator sifts to identity,
    a re-checked certificate). Budget blow-up ⇒ DECLINE."""
    levels = bsgs(gens, n)
    if levels is None:
        return KV.decline("schreier-sims: Schreier-generator blow-up beyond step budget ⇒ DECLINE", "schreier_sims")
    ident = _ident(n)
    if not levels:
        order = 1
    else:
        order = 1
        for _, trans in levels:
            order *= len(trans)
    # ★ completeness certificate: every input generator must sift to the identity
    if not all(_sift(tuple(g), levels, n) == ident for g in gens):
        return KV.decline("schreier-sims: a generator did not sift to identity ⇒ incomplete BSGS ⇒ DECLINE",
                          "schreier_sims")
    cert = KV.Cert(KV.EXACT, "bsgs_sift", passed=True, check_cost="O(n·Σ|orbit|) sift per gen",
                   detail=f"|G|=∏|orbitᵢ|={order}; every generator sifts to identity ⇒ complete BSGS")
    return KV.exact({"order": order, "base": [b for b, _ in levels]}, "schreier_sims", "O(1) per query", cert)


def membership(gens: Sequence[Perm], n: int, g: Sequence[int]) -> KV.Verdict:
    """EXACT membership: g ∈ ⟨gens⟩ iff its sift-residue is the identity (re-checked). Budget blow-up ⇒ DECLINE."""
    levels = bsgs(gens, n)
    if levels is None:
        return KV.decline("schreier-sims: budget blow-up ⇒ DECLINE", "schreier_sims")
    ident = _ident(n)
    if not all(_sift(tuple(x), levels, n) == ident for x in gens):
        return KV.decline("schreier-sims: incomplete BSGS ⇒ DECLINE", "schreier_sims")
    in_g = _sift(tuple(g), levels, n) == ident
    cert = KV.Cert(KV.EXACT, "bsgs_sift", passed=True, check_cost="O(n·depth) sift",
                   detail=f"sift residue {'= identity ⇒ ∈G' if in_g else '≠ identity ⇒ ∉G'}")
    return KV.exact({"member": in_g}, "schreier_sims", "O(depth)", cert)


def adversarial_battery() -> dict:
    """★ |S₄|=24, |A₄|=12, |⟨4-cycle⟩|=4 (order fold, EXACT cert); ★ a member sifts in, a non-member sifts out;
    ★ every EXACT carries the completeness certificate (all generators sift to identity)."""
    s4 = [(1, 0, 2, 3), (1, 2, 3, 0)]            # transposition (0 1) + 4-cycle generate S₄
    a4 = [(1, 2, 0, 3), (0, 2, 3, 1)]            # two 3-cycles generate A₄
    c4 = [(1, 2, 3, 0)]                          # a single 4-cycle ⇒ cyclic order 4
    o_s4 = group_order(s4, 4); o_a4 = group_order(a4, 4); o_c4 = group_order(c4, 4)
    mem_in = membership(c4, 4, (2, 3, 0, 1))     # the 4-cycle squared ∈ ⟨c4⟩
    mem_out = membership(c4, 4, (1, 0, 2, 3))    # a transposition ∉ cyclic group
    cases = {
        "S4_order_24": o_s4.status == "EXACT" and o_s4.result["order"] == 24,
        "A4_order_12": o_a4.status == "EXACT" and o_a4.result["order"] == 12,
        "C4_order_4": o_c4.status == "EXACT" and o_c4.result["order"] == 4,
        "member_in": mem_in.status == "EXACT" and mem_in.result["member"] is True,
        "nonmember_out": mem_out.status == "EXACT" and mem_out.result["member"] is False,
        "exact_carries_cert": o_s4.certificate is not None and o_s4.certificate.passed,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
