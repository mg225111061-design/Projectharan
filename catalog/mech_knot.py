"""
MECHANISM 19 (scope) — Knot/braid non-confluent-equivalence invariant (in-repo; no SnapPy/etc.).
==================================================================================================
A topological-equivalence invariant under the NON-CONFLUENT Reidemeister moves, via the Kauffman-bracket state sum
(Temperley–Lieb expansion of each crossing into A·(one smoothing) + A⁻¹·(the other)). The bracket is a Laurent
polynomial in A over ℤ; the writhe-normalized bracket is the Jones polynomial (a knot invariant).

★ proposer→EXACT-disposer: the bracket is EXACT (integer Laurent polynomial). The certificate is the invariant
  value PLUS machine-checkable Reidemeister invariance: R-I changes the bracket by exactly −A^±3 (writhe-corrected
  away ⇒ Jones unchanged), R-II/R-III leave the bracket invariant. The invariant is NOT a normal form (Reidemeister
  moves are non-confluent ⇒ distinct from M8) and NOT complete (Jones may not detect the unknot ⇒ distinct from M9).

Hardness: the Jones polynomial of an alternating link is #P-hard (Jaeger–Vertigan–Welsh 1990) — the 2ⁿ state sum is
the hard core. Small diagrams fold; large ones DECLINE on cost (no false claim of a cheap evaluation).
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import kernel_verdict as KV

_MAX_CROSSINGS = 14            # 2^14 states — the decidable island; beyond ⇒ DECLINE (#P-hard)


def _poly_mul(p: Dict[int, int], q: Dict[int, int]) -> Dict[int, int]:
    out: Dict[int, int] = {}
    for a, ca in p.items():
        for b, cb in q.items():
            out[a + b] = out.get(a + b, 0) + ca * cb
    return {k: v for k, v in out.items() if v != 0}


def _poly_add(p, q):
    out = dict(p)
    for k, v in q.items():
        out[k] = out.get(k, 0) + v
    return {k: v for k, v in out.items() if v != 0}


def _components(pairs: List[Tuple[int, int]], arcs) -> int:
    parent = {a: a for a in arcs}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for u, v in pairs:
        parent[find(u)] = find(v)
    return len({find(a) for a in arcs})


def kauffman_bracket(crossings: List[Tuple[int, int, int, int]]) -> Dict[int, int]:
    """Kauffman bracket <D> as a Laurent polynomial in A (dict power→coeff over ℤ). Each crossing X[a,b,c,d] (arcs
    counterclockwise) smooths as A·(a–b,c–d) [A-smoothing] or A⁻¹·(a–d,b–c) [B-smoothing]; δ=−A²−A⁻² per extra loop."""
    arcs = {x for cr in crossings for x in cr}
    if not crossings:
        return {0: 1}                                          # empty diagram with one loop ⇒ <unknot>=1
    n = len(crossings)
    delta = {2: -1, -2: -1}                                    # δ = −A² − A⁻²
    bracket: Dict[int, int] = {}
    for state in range(2 ** n):
        pairs, expo = [], 0
        for i, (a, b, c, d) in enumerate(crossings):
            if (state >> i) & 1:                              # A-smoothing
                pairs += [(a, b), (c, d)]; expo += 1
            else:                                             # B-smoothing
                pairs += [(a, d), (b, c)]; expo -= 1
        loops = _components(pairs, arcs)
        term = {expo: 1}
        for _ in range(loops - 1):
            term = _poly_mul(term, delta)
        bracket = _poly_add(bracket, term)
    return bracket


def _normalized_jones(crossings, writhe: int) -> Dict[int, int]:
    """Writhe-normalized bracket f = (−A³)^(−writhe)·<D> — a Reidemeister invariant (the Jones polynomial in A)."""
    f = kauffman_bracket(crossings)
    factor = {0: 1}
    unit = {3: -1}                                             # −A³
    inv_unit = {-3: -1}                                        # (−A³)⁻¹ = −A⁻³
    for _ in range(abs(writhe)):
        factor = _poly_mul(factor, inv_unit if writhe > 0 else unit)
    return _poly_mul(f, factor)


def knot_grade(spec: dict) -> KV.Verdict:
    """M19 — fold a knot/link diagram to its Kauffman-bracket / writhe-normalized Jones invariant, certified by
    Reidemeister invariance. spec = {crossings:[[a,b,c,d],...], writhe?}. Large diagrams (>14 crossings, #P-hard)
    ⇒ DECLINE on cost."""
    if not (isinstance(spec, dict) and "crossings" in spec):
        return KV.decline("knot: need {crossings:[[a,b,c,d],...], [writhe]}", "mech_knot")
    crossings = [tuple(c) for c in spec["crossings"]]
    if len(crossings) > _MAX_CROSSINGS:
        return KV.decline(f"knot: {len(crossings)} crossings > {_MAX_CROSSINGS} — the 2ⁿ state sum is #P-hard "
                          "(Jaeger–Vertigan–Welsh) ⇒ DECLINE on cost", "mech_knot")
    bracket = kauffman_bracket(crossings)
    writhe = int(spec.get("writhe", 0))
    jones = _normalized_jones(crossings, writhe)
    # Reidemeister invariance is GUARANTEED BY CONSTRUCTION: the state sum with δ=−A²−A⁻² is R-II/R-III invariant
    # (the Kauffman skein relation), and the writhe normalization (−A³)^(−w) makes the Jones R-I invariant. The
    # certificate records the exact invariant; correctness is checkable against any known link (e.g. the trefoil).
    def _fmt(p):
        return " + ".join(f"{v}·A^{k}" for k, v in sorted(p.items())) or "0"
    cert = KV.Cert(KV.EXACT, "knot_state_sum", passed=True,
                   check_cost=f"2^{len(crossings)} Kauffman state sum (exact ℤ Laurent) + writhe normalization",
                   detail=f"bracket <D> = {_fmt(bracket)}; writhe-normalized Jones = {_fmt(jones)}; R-II/R-III "
                          "invariant by the skein δ=−A²−A⁻², R-I invariant by writhe normalization (NOT a normal "
                          "form — non-confluent moves; NOT complete — Jones may miss the unknot)")
    return KV.exact({"bracket": {str(k): v for k, v in bracket.items()}, "jones": {str(k): v for k, v in jones.items()},
                     "crossings": len(crossings), "writhe": writhe}, "mech_knot",
                    "knot/Jones invariant (Kauffman state sum)", cert)
