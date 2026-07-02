"""
§AL §2 — CONJECTURE DEPTH to the limit + ★ MULTI-SCALE held-out (the permanent P-2 block).
================================================================================================================
Push the §AI conjecturers DEEPER — but S-2 holds: observation is not proof. Two levers:

(1) ESCALATING PROBE: re-run the conjecturers at increasing observation budgets (24 → 48 → 96 → 192); a higher-order
    recurrence that the default probe left under-determined now becomes determined. ★ if observations are insufficient
    for the recovered order, the conjecture is ABANDONED (a fit through too few points is never accepted).

(2) ★★ MULTI-SCALE HELD-OUT: §AK found the digit-function trap — a recurrence that matches a contiguous window but
    breaks at a digit-carry boundary (n=100). A contiguous held-out crosses ONE carry scale; here we verify the
    recovered recurrence on windows that straddle MULTIPLE structural scales (n≈10, 100, 1000), so any carry-class
    sequence is refuted permanently. This is a STRENGTHENING of the gate — it can only turn EXACT into DECLINE, never
    the reverse (precision can only go UP).

★ S-1 no new mechanism — this reuses native_sequence's BM + connection-polynomial verifier. Honest: depth ↑ ⇒ cost ↑
with DIMINISHING RETURNS; `yield_curve()` measures which depth is cost-effective. LLM-free, zero-dep.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, List, Optional, Tuple

_SCALES = (100, 1000, 10000)        # carry-boundary scales the multi-scale held-out must straddle
_PROBE_LADDER = (24, 48, 96, 192)


@dataclass
class DeepResult:
    folded: bool
    order: int = 0
    probe_used: int = 0
    multiscale_ok: bool = False
    detail: str = ""


def _bm(seq: List[Fraction]) -> Tuple[list, int]:
    import native_sequence as NS
    return NS.berlekamp_massey_Q(seq)


def multiscale_witness_ok(fn: Callable[[int], object], C: list, L: int, scales=_SCALES) -> bool:
    """★★ verify the connection-polynomial recurrence (C, L) on windows STRADDLING multiple carry scales — a
    digit-carry-class sequence that matched the contiguous probe is refuted at n≈100/1000/10000. REUSE
    native_sequence._verify_recurrence on each straddling segment (each needs L preceding terms)."""
    import native_sequence as NS
    if L < 1:
        return False
    try:
        for s in scales:
            seg = [Fraction(fn(s - L + i)) for i in range(L + 24)]   # L history + a 24-term straddle past scale s
            if not NS._verify_recurrence(seg, C, L):
                return False
        return True
    except Exception:  # noqa: BLE001
        return False


def deep_conjecture(fn: Callable[[int], object], ladder=_PROBE_LADDER) -> DeepResult:
    """Escalate the probe; on the smallest probe that yields a DETERMINED recurrence, GATE it with the multi-scale
    held-out. Accept EXACT only when the recurrence is determined AND survives all carry scales (S-2)."""
    from conjecture import harness as H
    for probe in ladder:
        try:
            seq = [Fraction(fn(n)) for n in range(probe)]
        except Exception:  # noqa: BLE001
            return DeepResult(False, 0, probe, False, "oracle raised ⇒ ABANDON")
        C, L = _bm(seq)
        if L < 1 or H.under_determined(probe, L):
            continue                                            # under-determined at this depth ⇒ go deeper (or abandon)
        # contiguous run-forward (cheap reject) then ★ the multi-scale carry-straddle gate
        import native_sequence as NS
        if not NS._verify_recurrence(seq, C, L):
            continue
        ms = multiscale_witness_ok(fn, C, L)
        if ms:
            return DeepResult(True, L, probe, True,
                              f"order-{L} recurrence determined at probe {probe} + survives carry scales {_SCALES} ⇒ EXACT")
        return DeepResult(False, L, probe, False,
                          f"★ order-{L} matched the probe but BROKE at a carry scale {_SCALES} ⇒ DECLINE (P-2 blocked)")
    return DeepResult(False, 0, ladder[-1], False, "no determined recurrence within the probe ladder ⇒ DECLINE")


def yield_curve(corpus: List[Callable[[int], object]]) -> dict:
    """★ honest diminishing-returns: how many of `corpus` fold at each probe depth (cumulative). The curve plateaus —
    deeper probes cost more for less marginal recall."""
    curve = {}
    for probe in _PROBE_LADDER:
        folded = sum(1 for fn in corpus if deep_conjecture(fn, ladder=(probe,)).folded)
        curve[probe] = folded
    return {"per_depth_cumulative": curve, "note": "fold yield vs probe depth — plateaus ⇒ diminishing returns "
            "(deeper costs more wall-clock for marginal recall); route deep only on §AJ-promising oracles"}


def adversarial_battery() -> dict:
    """★ a high-order linear recurrence (order 6) that a shallow probe leaves under-determined folds at a deeper probe
    (multi-scale verified); ★★ the digit-function P-2 trap is PERMANENTLY blocked — base-10 digit-sum matches a
    contiguous window but is refuted at a carry scale ⇒ DECLINE (false-EXACT 0); ★ a genuine random oracle DECLINEs."""
    # order-6 linear recurrence a[n]=a[n-1]+a[n-6] (a high-order C-finite, under-determined at tiny probes).
    # ITERATIVE (so it is evaluable at the n=10000 carry scale without hitting Python's recursion limit).
    def high_order(n):
        a = [1, 1, 1, 1, 1, 1]
        if n < 6:
            return 1
        for i in range(6, n + 1):
            a.append(a[i - 1] + a[i - 6])
        return a[n]
    ho = deep_conjecture(high_order)
    # ★★ the P-2 trap: base-10 digit-sum matches a short window, breaks at the n=100 carry — must DECLINE
    ds = deep_conjecture(lambda n: sum(int(d) for d in str(n)))
    # genuine random
    def rnd(n):
        import hashlib
        return int.from_bytes(hashlib.sha256(str(n).encode()).digest()[:6], "big")
    rr = deep_conjecture(rnd)
    # ★ the multi-scale gate is REAL: it rejects a recurrence that only matches contiguously (digit-sum) — show the
    #   contiguous BM "looks" determined but the carry-scale witness fails
    import native_sequence as NS
    seq = [Fraction(sum(int(d) for d in str(n))) for n in range(48)]
    C, L = NS.berlekamp_massey_Q(seq)
    contiguous_then_carry_break = (L >= 1 and NS._verify_recurrence(seq, C, L)
                                   and not multiscale_witness_ok(lambda n: sum(int(d) for d in str(n)), C, L))
    cases = {
        "high_order_folds_at_depth": ho.folded and ho.order == 6 and ho.multiscale_ok,
        "digitsum_P2_trap_blocked": not ds.folded,                  # ★★ permanent P-2 block
        "random_declines": not rr.folded,
        "multiscale_gate_is_real": contiguous_then_carry_break,     # ★ contiguous-match but carry-scale refute
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
