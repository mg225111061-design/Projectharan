"""
§AG §2b (optional) — SEPARATION-LOGIC ALIASING PROVER: promote an aliasing DECLINE to ACCEPT *by proof*.
================================================================================================================
Today §P `array_fold` / §AD `loop_fusion` conservatively DECLINE a loop that writes `a[idx(k)]` when two iterations
*might* write the same cell (aliasing → write-order matters → fold/fusion unsound). The frame rule of separation
logic says: if the written cells are a DISJOINT heap, the writes don't interfere and the fold/fusion is sound.

★ Separation logic is NOT a z3-native theory — so we admit ONLY the fragment that reduces to an EXPLICIT
array-separation predicate over z3 QF_LIA: index maps that are AFFINE `idx(k)=a·k+b` (prove injectivity over the
loop range ⇒ no two iterations alias), or two write REGIONS `[lo,hi)` (prove interval-disjointness). A general heap
(data-dependent gather `a[p[k]]`, pointer aliasing) does NOT reduce ⇒ stays DECLINE.

★ net-new = a case we USED TO REJECT is now ACCEPTED *because z3 proved disjointness* — a small, sound coverage
promotion. precision 1.0 is preserved: a WRONG disjointness claim is refuted by z3 (a collision witness ⇒ DECLINE).
No new disposer, no new certificate kind — the non-interference proof is an INVARIANT cert (the existing kind used
by IC3/CHC). LLM-free, zero external deps (z3 + stdlib).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import kernel_verdict as KV


@dataclass
class AliasVerdict:
    promoted: bool                       # DECLINE → ACCEPT (disjointness PROVEN) ?
    reducible: bool                      # did the heap reduce to a QF_LIA separation predicate at all?
    verdict: "KV.Verdict" = None
    witness: Optional[dict] = None       # a collision witness if NOT disjoint
    detail: str = ""


def prove_affine_injective(a: int, b: int, N: int) -> Tuple[bool, Optional[dict]]:
    """z3 QF_LIA: are the writes a[a·k+b] for k∈[0,N) to DISJOINT cells? i.e. is k ↦ a·k+b injective on [0,N)?
    Check UNSAT of (0≤k1 ∧ k1<k2 ∧ k2<N ∧ a·k1+b == a·k2+b). a is a *constant* ⇒ a·k is LINEAR (no bit-blast,
    no nonlinear). Returns (disjoint, collision_witness_or_None)."""
    import z3
    k1, k2 = z3.Ints("k1 k2")
    s = z3.Solver()
    s.add(0 <= k1, k1 < k2, k2 < N, a * k1 + b == a * k2 + b)   # a literal int ⇒ linear
    r = s.check()
    if r == z3.unsat:
        return True, None
    if r == z3.sat:
        m = s.model()
        return False, {"k1": m[k1].as_long(), "k2": m[k2].as_long(), "cell": a * m[k1].as_long() + b}
    return False, None


def prove_regions_disjoint(lo1: int, hi1: int, lo2: int, hi2: int) -> Tuple[bool, Optional[dict]]:
    """z3 QF_LIA: are write regions [lo1,hi1) and [lo2,hi2) disjoint? Check UNSAT of (∃ i in both) =
    (lo1≤i<hi1 ∧ lo2≤i<hi2). Returns (disjoint, overlap_witness_or_None)."""
    import z3
    i = z3.Int("i")
    s = z3.Solver()
    s.add(lo1 <= i, i < hi1, lo2 <= i, i < hi2)
    r = s.check()
    if r == z3.unsat:
        return True, None
    if r == z3.sat:
        return False, {"overlap_index": s.model()[i].as_long()}
    return False, None


def _invariant_verdict(claim: str, detail: str) -> "KV.Verdict":
    """A PROVEN non-interference invariant → EXACT, reusing the EXISTING 'invariant' certificate kind (no new kind)."""
    cert = KV.Cert(KV.EXACT, "invariant", passed=True, check_cost="z3 QF_LIA UNSAT (disjointness)", detail=detail)
    return KV.exact({"disjoint": True, "claim": claim}, "sep_alias", "separation-logic disjoint heap (frame rule)", cert)


def promote_affine(a: int, b: int, N: int) -> AliasVerdict:
    """Try to promote an aliasing DECLINE for `a[a·k+b], k∈[0,N)` to ACCEPT by PROVING injectivity (disjoint writes)."""
    disjoint, wit = prove_affine_injective(a, b, N)
    if disjoint:
        return AliasVerdict(True, True, _invariant_verdict(f"a[{a}·k+{b}] injective on [0,{N})",
                            f"∀ 0≤k1<k2<{N}: {a}·k1+{b} ≠ {a}·k2+{b} (z3 QF_LIA UNSAT) ⇒ disjoint heap ⇒ ACCEPT"),
                            detail="affine index PROVEN injective ⇒ aliasing DECLINE promoted to ACCEPT")
    return AliasVerdict(False, True, KV.decline(f"a[{a}·k+{b}] aliases on [0,{N}) (collision {wit}) — fold unsound", "sep_alias"),
                        witness=wit, detail="affine index NOT injective (z3 found a collision) ⇒ stays DECLINE")


def promote_regions(lo1: int, hi1: int, lo2: int, hi2: int) -> AliasVerdict:
    """Promote a two-region write DECLINE to ACCEPT by PROVING the regions are interval-disjoint."""
    disjoint, wit = prove_regions_disjoint(lo1, hi1, lo2, hi2)
    if disjoint:
        return AliasVerdict(True, True, _invariant_verdict(f"[{lo1},{hi1}) ⊥ [{lo2},{hi2})",
                            f"no i in both regions (z3 QF_LIA UNSAT) ⇒ disjoint ⇒ ACCEPT"),
                            detail="regions PROVEN disjoint ⇒ promoted to ACCEPT")
    return AliasVerdict(False, True, KV.decline(f"regions overlap at {wit} — fusion unsound", "sep_alias"),
                        witness=wit, detail="regions overlap (z3 witness) ⇒ stays DECLINE")


def general_heap_declined(reason: str = "data-dependent gather a[p[k]]") -> AliasVerdict:
    """★ A heap that does NOT reduce to a QF_LIA separation predicate (data-dependent gather, pointer aliasing)
    stays DECLINE — separation logic is not z3-native and we never fake the disjointness proof."""
    return AliasVerdict(False, False, KV.decline(f"non-reducible heap ({reason}) — not a QF_LIA separation fragment", "sep_alias"),
                        detail="general heap does not reduce to an explicit array-separation predicate ⇒ DECLINE (honest)")


def promotion_count() -> dict:
    """★ Honest measurement: how many aliasing-DECLINE cases does the separation prover PROMOTE to ACCEPT (small,
    by design)? Counts promotions on a representative micro-corpus; the non-reducible heap is NOT counted."""
    corpus = [promote_affine(1, 0, 100), promote_affine(2, 1, 50), promote_affine(3, 0, 30),
              promote_affine(0, 5, 10),                       # stride 0 ⇒ all same cell ⇒ NOT promoted
              promote_regions(0, 10, 10, 20),                 # disjoint ⇒ promoted
              promote_regions(0, 10, 5, 20),                  # overlap ⇒ NOT promoted
              general_heap_declined()]                        # non-reducible ⇒ NOT promoted
    promoted = sum(1 for v in corpus if v.promoted)
    return {"corpus": len(corpus), "promoted": promoted, "note": "small sound promotion (disjointness PROVEN); "
            "non-injective / overlapping / non-reducible cases correctly stay DECLINE"}


def adversarial_battery() -> dict:
    """Stride-1 and stride-2 affine writes PROMOTE (z3-proven injective); disjoint regions PROMOTE; ★ stride-0
    (all same cell) is REJECTED (collision witness); ★ overlapping regions are REJECTED; ★ a non-reducible heap
    stays DECLINE (honest); ★ precision 1.0 — every promotion carries a z3-proven invariant cert."""
    p1 = promote_affine(1, 0, 100)
    p2 = promote_affine(2, 3, 64)
    reg_ok = promote_regions(0, 16, 16, 32)
    s0 = promote_affine(0, 7, 20)                              # stride 0 ⇒ collision
    reg_bad = promote_regions(0, 16, 8, 32)                    # overlap
    gen = general_heap_declined()
    cases = {
        "stride1_promoted": p1.promoted and p1.verdict.status == KV.EXACT,
        "stride2_promoted": p2.promoted and p2.verdict.status == KV.EXACT,
        "disjoint_regions_promoted": reg_ok.promoted and reg_ok.verdict.status == KV.EXACT,
        "stride0_collision_rejected": (not s0.promoted) and s0.verdict.status == KV.DECLINE and s0.witness is not None,
        "overlap_regions_rejected": (not reg_bad.promoted) and reg_bad.verdict.status == KV.DECLINE,
        "general_heap_declined": (not gen.promoted) and (not gen.reducible) and gen.verdict.status == KV.DECLINE,
        "cert_kind_is_existing_invariant": p1.verdict.certificate.kind == "invariant",   # ★ no new cert kind
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
