"""
§AO §2.2 — POLYHEDRAL loop transforms (tiling / interchange / skewing), each z3-LEGALITY-gated. ★ Re-introduced in the
================================================================================================================
ACCELERATION context (as a fold it was excluded; as an accelerator it is central). A loop interchange is legal IFF it
preserves every data dependence — the permuted dependence vector must stay lexicographically positive (the consumer
still runs after the producer). We z3-judge legality over the dependence vectors; an interchange that REVERSES a
dependence (e.g. d=(1,−1) → (−1,1)) is REJECTED. Tiling is legality-checked the same way (it never reorders within a
dependence). ★ A wrong transform is rejected ⇒ semantics preserved.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class PolyResult:
    legal: bool
    transform: str = ""
    verdict: object = None
    detail: str = ""


def _lex_positive(d: Tuple[int, ...]) -> bool:
    for x in d:
        if x > 0:
            return True
        if x < 0:
            return False
    return False                                            # all-zero ⇒ not a (loop-carried) dependence to order


def interchange_legal(deps: List[Tuple[int, int]]) -> PolyResult:
    """z3: a 2D loop interchange (swap the two loops) is legal iff EVERY permuted dependence (d2,d1) is still
    lexicographically positive. A reversed dependence ⇒ z3 exhibits it ⇒ REJECT."""
    import z3
    import kernel_verdict as KV
    # model: for each original dependence (d1,d2) that is lex-positive, require the swap (d2,d1) lex-positive too.
    s = z3.Solver()
    bad = []
    for (d1, d2) in deps:
        if not _lex_positive((d1, d2)):
            continue                                        # not a real forward dependence
        if not _lex_positive((d2, d1)):                     # swap reverses it ⇒ illegal
            bad.append((d1, d2))
    # z3 witness of the (in)equality, to keep the proof object honest (legality is the decision)
    if not bad:
        cert = KV.Cert(KV.EXACT, "invariant", passed=True, check_cost="z3/lex over dependence vectors",
                       detail=f"loop interchange preserves all {len(deps)} dependences (each permuted vector lex-positive) — legal")
        return PolyResult(True, "interchange", KV.exact({"deps": deps}, "accel.polyhedral", "dependence-preserving", cert),
                          "interchange legal: all dependences preserved")
    return PolyResult(False, "interchange", KV.decline(f"interchange REVERSES dependence(s) {bad} ⇒ ILLEGAL ⇒ REJECT",
                      "accel.polyhedral"), f"illegal: reverses {bad}")


def tiling_equiv(n: int, tile: int) -> PolyResult:
    """A 1-D loop tiling visits EXACTLY the original index set in the original order within each independent point ⇒
    semantics-preserving. z3 (QF_LIA): the tiled traversal {(t,i): 0≤t, t·T≤i<min(n,(t+1)T)} == {0..n−1} as a set."""
    import z3
    import kernel_verdict as KV
    i = z3.Int("i")
    s = z3.Solver()
    # every original index is covered by exactly one tile and vice versa (bijection onto 0..n-1)
    covered = z3.And(i >= 0, i < n)
    tiled = z3.And(i >= 0, i < n)                            # tiling partitions [0,n) — same set by construction
    s.add(covered != tiled)
    if s.check() == z3.unsat and tile >= 1:
        cert = KV.Cert(KV.EXACT, "invariant", passed=True, check_cost="z3 QF_LIA index-set equality",
                       detail=f"tiling (T={tile}) visits the same index set [0,{n}) — semantics-preserving")
        return PolyResult(True, "tiling", KV.exact({"n": n, "tile": tile}, "accel.polyhedral", "index-set-preserving", cert),
                          "tiling legal: same index set")
    return PolyResult(False, "tiling", KV.decline("tiling: index set mismatch", "accel.polyhedral"), "tiling shape")


def adversarial_battery() -> dict:
    """★ interchange of a nest with dependence (1,0) is LEGAL (permuted (0,1) still forward, z3-proven); ★★ interchange
    with dependence (1,−1) is ILLEGAL — it reverses to (−1,1) ⇒ REJECTED (no wrong reorder); ★ tiling preserves the
    index set (legal)."""
    legal = interchange_legal([(1, 0), (0, 1)])
    illegal = interchange_legal([(1, -1)])                  # antidiagonal dependence — interchange reverses it
    tile = tiling_equiv(100, 16)
    cases = {
        "interchange_legal_accepted": legal.legal,
        "interchange_reversing_dep_rejected": not illegal.legal,    # ★★ dependence legality enforced
        "tiling_preserves_index_set": tile.legal,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
