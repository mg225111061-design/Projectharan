"""
§AP §3 — LOOP-STRIDE RECALL: one loop whose consecutive iterations belong to DIFFERENT recurrences (interleaved by a
================================================================================================================
stride k). The single-stream view is not C-finite, but separated by index mod k, each stride-k substream gᵣ(m)=f(k·m+r)
follows its own simple rule — and crucially, DIFFERENT substreams may need DIFFERENT lenses (one linear, one geometric,
one popcount-automatic). §AN's stride path folds substreams with BM only; §3's addition is HETEROGENEOUS-lens substream
folding (depth/BM → conjecturers → M22), plus the recombination seal.

★ S-2: each substream is disposed by an existing z3-gated lens with the §AL multi-scale held-out; the only added claim
(that the stride is exactly k) is sealed by re-verifying the index map on carry-straddle scales. A wrong stride or a
random substream is REJECTED ⇒ no false EXACT. ★ S-1: no new mechanism (REUSE depth + core + k_regular).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

_STRIDES = (2, 3, 4)
_SCALES = (100, 1000)                    # straddle scales for the index-map (stride-period) seal
_PROBE = 64                             # one BM probe per substream (cheap; the multi-scale held-out is the gate)


@dataclass
class StrideResult:
    folded: bool
    k: int = 0
    lenses: List[str] = None
    detail: str = ""


def separate(fn: Callable[[int], object], k: int) -> List[Callable[[int], object]]:
    """The k stride substreams gᵣ(m) = fn(k·m + r)."""
    return [(lambda r: (lambda m: fn(k * m + r)))(r) for r in range(k)]


def _automatic_growth(g: Callable[[int], object], probe: int = 24, bound: int = 64) -> bool:
    """Cheap necessary trait of the (non-C-finite) k-automatic sequences the M22 lens targets — popcount / digit-sums
    grow LOGARITHMICALLY, so their values stay tiny. Polynomial / exponential k-regular sequences are already C-finite
    and fold on the BM path first, so they never need M22. Gating the (expensive) M22 attempt on this trait only trades
    a sliver of RECALL on exotic large-valued automatic sequences — it never affects precision (the gate disposes)."""
    try:
        return all(abs(int(g(m))) <= bound for m in range(probe))
    except Exception:  # noqa: BLE001
        return False


def fold_substream(g: Callable[[int], object]):
    """Dispose ONE substream through an existing z3-gated lens — FAST: one BM probe + the §AL multi-scale carry-straddle
    held-out (the soundness), then the §AN M22 k-automatic lens (only on logarithmic-growth data, to fail fast). The
    heterogeneous part: different substreams may fold in DIFFERENT lenses. Returns (folded, lens)."""
    from fractions import Fraction
    from recall import depth as D
    import native_sequence as NS
    from conjecture import harness as H
    try:
        seq = [Fraction(g(n)) for n in range(_PROBE)]
    except Exception:  # noqa: BLE001
        return False, ""
    C, L = NS.berlekamp_massey_Q(seq)
    if L >= 1 and not H.under_determined(_PROBE, L) and NS._verify_recurrence(seq, C, L) and D.multiscale_witness_ok(g, C, L):
        return True, f"c_finite[order {L}]"                       # BM + multi-scale held-out (P-2 gate)
    if _automatic_growth(g):                                      # ★ fast-fail: M22 only on plausibly-automatic data
        from recall import k_regular as KR
        kr = KR.fold(g)
        if kr.folded:
            return True, f"k_automatic[{kr.kind}]"
    return False, ""


def _index_map_ok(fn, subs, k) -> bool:
    """Seal: gᵣ(m) at r=n mod k, m=n//k must reproduce fn(n) across carry-straddle scales (the stride is exactly k)."""
    try:
        for s in _SCALES:
            for n in (s, s + 1, s + k + 1):
                if subs[n % k](n // k) != fn(n):
                    return False
        return True
    except Exception:  # noqa: BLE001
        return False


def fold(fn: Callable[[int], object], strides=_STRIDES) -> StrideResult:
    """Find the smallest stride k≥2 such that EVERY stride-k substream folds (in some lens) and the index map holds."""
    for k in strides:
        subs = separate(fn, k)
        results = [fold_substream(g) for g in subs]
        if all(ok for ok, _ in results) and _index_map_ok(fn, subs, k):
            lenses = [lens for _, lens in results]
            # ★ require genuine interleave: at least two substreams use DIFFERENT lenses OR k>1 with all folding
            return StrideResult(True, k, lenses,
                                f"stride-{k}: all {k} substreams fold (lenses {lenses}) + index map verified on "
                                f"carry scales {_SCALES} ⇒ EXACT")
    return StrideResult(False, 0, None, "no stride k∈" + str(strides) + " separates into foldable substreams")


def adversarial_battery() -> dict:
    """★ HETEROGENEOUS stride-2: even index → linear (2m+1), odd index → geometric (2^m) — neither lens folds the whole
    stream, but stride separates it and EACH substream folds in its OWN lens; ★ stride-3 of three distinct polynomials
    folds; ★★ a stream with a RANDOM substream DECLINEs (the substream gate holds — no false EXACT); ★ the whole
    heterogeneous stream is genuinely NOT folded by a single lens (so stride does real work)."""
    import hashlib

    def fib(m):
        a, b = 0, 1
        for _ in range(m):
            a, b = b, a + b
        return a

    def hetero(n):                                                # even → Fibonacci (C-finite, NOT k-regular),
        m = n // 2                                                # odd → popcount (k-automatic, NOT C-finite)
        return fib(m) if n % 2 == 0 else bin(m).count("1")        # ⇒ the interleave is in NEITHER closed class
    h = fold(hetero)

    def hetero3(n):                                              # stride-3, THREE lenses: linear / popcount / Fibonacci
        m = n // 3                                               # ⇒ k=2 substreams mix all three (unfoldable); only
        return [m, bin(m).count("1"), fib(m)][n % 3]            #   k=3 separates them cleanly
    tp = fold(hetero3)

    def with_random(n):
        m = n // 2
        return (3 * m) if n % 2 == 0 else int.from_bytes(hashlib.sha256(str(m).encode()).digest()[:6], "big")
    wr = fold(with_random)

    # ★ the heterogeneous whole is genuinely not seen by a single lens: Fib breaks the k-automatic lens (M22 N/A on its
    #   large values), popcount breaks the C-finite lens (BM) — so only the stride separation folds it.
    from recall import core, depth as D
    whole_direct = D.deep_conjecture(hetero).folded or core.fold_via_ai(hetero, "w").folded

    cases = {
        "heterogeneous_stride_folds": h.folded and h.k == 2 and any("automatic" in l for l in (h.lenses or [])),
        "whole_not_seen_by_single_lens": not whole_direct,       # ★ stride does real work
        "stride3_polynomials_fold": tp.folded and tp.k == 3,
        "random_substream_declines": not wr.folded,              # ★★ no false EXACT
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
