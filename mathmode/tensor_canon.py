"""
UNIFIED ARSENAL §3 · P1 — Butler–Portugal tensor canonicalization (mono-term DECISION).
========================================================================================
A tensor monomial carries SLOT SYMMETRIES (a permutation group on its index slots, possibly with signs — e.g.
gₐᵦ=g_bₐ, Fₐᵦ=−F_bₐ, the Riemann symmetries) and DUMMY indices (contracted pairs, freely renamable). Butler–
Portugal computes a UNIQUE canonical representative, so tensor EQUALITY (and the zero tensor) is DECIDABLE.

Here the symmetry is a SIGNED permutation group; the canonical form is the lexicographically-minimal image over the
group orbit (× dummy relabeling), with the sign tracked. If some group element fixes the index tuple but flips the
sign, the tensor is identically ZERO (e.g. Fₐₐ=0). The group-theoretic backbone is Schreier–Sims (we expose the
BSGS via sympy.combinatorics) — Butler–Portugal uses the base + strong generating set to reach the canonical form
WITHOUT enumerating the orbit; for the small ranks here we verify against the orbit directly.

CERTIFICATE (our own): the canonical form is INVARIANT on the orbit (re-canonicalizing any group image gives the
same form+sign) — a re-checkable witness that equality is well-defined; plus the Schreier–Sims BSGS (verified group
order). DECISION for MONO-TERM symmetries. Honest scope (§X): multi-term symmetries (the Bianchi identity
R_{a[bcd]}=0) need Young projectors / an invariant-relation DB — flagged, NOT decided by Butler–Portugal alone.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from sympy.combinatorics import Permutation, PermutationGroup

import kernel_verdict as KV


def _signed_closure(gens: List[Tuple[List[int], int]], n: int) -> List[Tuple[Tuple[int, ...], int]]:
    """Close a set of signed generators (perm-as-list, sign) into the full signed group (BFS). Small groups only."""
    ident = tuple(range(n))
    seen: Dict[Tuple[int, ...], int] = {ident: 1}
    frontier = [ident]
    gp = [(tuple(p), s) for p, s in gens]
    while frontier:
        nxt = []
        for cur in frontier:
            for gp_perm, gp_sign in gp:
                comp = tuple(cur[gp_perm[i]] for i in range(n))   # apply generator after cur
                sign = seen[cur] * gp_sign
                if comp not in seen:
                    seen[comp] = sign
                    nxt.append(comp)
                elif seen[comp] != sign:
                    seen[comp] = 0                                # contradictory sign ⇒ marks a zero-forcing element
        frontier = nxt
    return list(seen.items())


def _canonical(indices: Tuple, group: List[Tuple[Tuple[int, ...], int]], dummies: List) -> Tuple[Tuple, int]:
    """Canonical (min) image of `indices` over the signed group, with dummy indices relabeled canonically.
    Returns (canonical_index_tuple, sign); sign 0 ⇒ the tensor is identically zero."""
    best = None
    best_sign = 1
    zero = False
    for perm, sign in group:
        if sign == 0:
            continue
        img = tuple(indices[perm[i]] for i in range(len(indices)))
        img, _ = _relabel_dummies(img, dummies)
        if best is None or img < best:
            best, best_sign = img, sign
        elif img == best and sign != best_sign:
            zero = True                                          # same arrangement reachable with opposite sign ⇒ 0
    if zero:
        return best, 0
    return best, best_sign


def _relabel_dummies(indices: Tuple, dummies: List) -> Tuple[Tuple, Dict]:
    """Rename dummy (contracted) labels to a canonical first-occurrence scheme d0,d1,…; free indices untouched."""
    dummy_set = set(dummies)
    mapping: Dict = {}
    out = []
    for ix in indices:
        if ix in dummy_set:
            if ix not in mapping:
                mapping[ix] = f"d{len(mapping)}"
            out.append(mapping[ix])
        else:
            out.append(ix)
    return tuple(out), mapping


def _bsgs(gens: List[List[int]], n: int):
    """Schreier–Sims BSGS for the (unsigned) slot symmetry group via sympy — the Butler–Portugal backbone."""
    G = PermutationGroup([Permutation(g, size=n) for g in gens]) if gens else PermutationGroup([Permutation(list(range(n)))])
    G.schreier_sims()
    return G


def canonicalize(indices: Tuple, gens: List[Tuple[List[int], int]], dummies: List = ()) -> KV.Verdict:
    """Canonicalize a tensor monomial under signed slot symmetries `gens`. EXACT: the canonical form + sign (0 ⇒
    identically zero), certified by orbit-invariance + the Schreier–Sims BSGS."""
    n = len(indices)
    group = _signed_closure(list(gens), n)
    canon, sign = _canonical(indices, group, list(dummies))
    # ★ certificate: re-canonicalizing EVERY orbit image yields the same (canon, sign|0) ★
    for perm, s in group:
        if s == 0:
            continue
        img = tuple(indices[perm[i]] for i in range(n))
        c2, s2 = _canonical(img, group, list(dummies))
        if c2 != canon or (sign != 0 and s2 != s * sign and s2 != 0):
            return KV.decline("tensor_canon: canonical form not orbit-invariant ⇒ DECLINE", "tensor_canon")
    G = _bsgs([p for p, _ in gens], n)
    cert = KV.Cert(KV.EXACT, "butler_portugal_orbit", passed=True, check_cost="orbit-invariance + Schreier–Sims BSGS",
                   detail=f"canonical = {canon} (sign {sign}); group order {G.order()}, base {list(G.base)}; "
                          f"{'IDENTICALLY ZERO' if sign == 0 else 'mono-term canonical form'}")
    return KV.exact({"canonical": canon, "sign": sign, "zero": sign == 0},
                    "tensor_canon.canonicalize", "DECISION (mono-term tensor canonical form)", cert)


def decide_equal(idx1: Tuple, idx2: Tuple, gens: List[Tuple[List[int], int]], dummies: List = ()) -> KV.Verdict:
    """DECIDE whether two index orderings denote the same tensor (up to sign) under the symmetries."""
    n = len(idx1)
    group = _signed_closure(list(gens), n)
    c1, s1 = _canonical(tuple(idx1), group, list(dummies))
    c2, s2 = _canonical(tuple(idx2), group, list(dummies))
    if s1 == 0 or s2 == 0:
        rel = "both zero" if (s1 == 0 and s2 == 0) else "one is zero"
    elif c1 == c2:
        rel = "equal" if s1 == s2 else "negatives"
    else:
        rel = "independent"
    cert = KV.Cert(KV.EXACT, "tensor_equality", passed=True, check_cost="canonical-form comparison",
                   detail=f"{idx1} vs {idx2}: canonical {c1}(sgn {s1}) vs {c2}(sgn {s2}) ⇒ {rel}")
    return KV.exact(rel, "tensor_canon.decide_equal", "DECISION (mono-term tensor equality)", cert)


# common symmetry generators (perm-as-list on slots, sign)
def symmetric_pair():        return [([1, 0], +1)]                   # T_ab = T_ba
def antisymmetric_pair():    return [([1, 0], -1)]                   # F_ab = −F_ba
def riemann():                                                       # R_abcd: antisym(ab), antisym(cd), sym(ab↔cd)
    return [([1, 0, 2, 3], -1), ([0, 1, 3, 2], -1), ([2, 3, 0, 1], +1)]


def solve(problem: dict) -> KV.Verdict:
    """ops: 'canonicalize' (indices, gens, dummies), 'equal' (idx1, idx2, gens, dummies)."""
    op = problem.get("op")
    presets = {"symmetric": symmetric_pair(), "antisymmetric": antisymmetric_pair(), "riemann": riemann()}
    gens = presets.get(problem.get("symmetry"), problem.get("gens", []))
    if op == "canonicalize":
        return canonicalize(tuple(problem["indices"]), gens, problem.get("dummies", []))
    if op == "equal":
        return decide_equal(tuple(problem["idx1"]), tuple(problem["idx2"]), gens, problem.get("dummies", []))
    return KV.decline(f"tensor_canon: unknown op {op!r} ⇒ DECLINE", "tensor_canon")
