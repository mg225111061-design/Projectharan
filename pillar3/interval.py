"""
Pillar 3 · ROUND 3 #70 — interval / range analysis → EXACT machine-int fast path (SOUND abstract interpretation).
=================================================================================================================
Generalises the per-instance "proven no-wraparound bound" used by the NTT convolution and the blocked matmul
into one reusable analysis. Over the INTERVAL domain [lo,hi] (a sound abstraction: the concrete value is ALWAYS
inside), we propagate input ranges through +,-,*,abs,sum-over-n and obtain a CONSERVATIVE output interval. If
that interval fits inside the machine width (|v| < 2^(b-1)), a fixed-width machine-int fast path is provably
overflow-free ⇒ EXACT. If the interval can exceed the width, we DECLINE the fast path (a bigint/wider path is
the honest extension) — never a wrapped answer. Soundness-critical: the abstraction must OVER-approximate
(never claim a tighter range than the true reachable set); a wrong "fits" is a correctness bug.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import kernel_verdict as KV


@dataclass(frozen=True)
class Interval:
    lo: int
    hi: int

    def __post_init__(self):
        assert self.lo <= self.hi, f"empty interval [{self.lo},{self.hi}]"

    def __add__(self, o: "Interval") -> "Interval":
        return Interval(self.lo + o.lo, self.hi + o.hi)

    def __sub__(self, o: "Interval") -> "Interval":
        return Interval(self.lo - o.hi, self.hi - o.lo)

    def __mul__(self, o: "Interval") -> "Interval":
        c = [self.lo * o.lo, self.lo * o.hi, self.hi * o.lo, self.hi * o.hi]
        return Interval(min(c), max(c))                      # sound for all sign combinations

    def abs(self) -> "Interval":
        if self.lo >= 0:
            return self
        if self.hi <= 0:
            return Interval(-self.hi, -self.lo)
        return Interval(0, max(-self.lo, self.hi))           # straddles 0

    def scale_sum(self, n: int) -> "Interval":
        """Bound on a sum of n terms each in this interval (Σ over n) — n·[lo,hi]."""
        return Interval(self.lo * n, self.hi * n)

    def magnitude(self) -> int:
        return max(abs(self.lo), abs(self.hi))


def fits_width(iv: Interval, bits: int) -> bool:
    """Does every value the interval admits fit a signed `bits`-int? (|v| < 2^(bits-1).)"""
    return iv.magnitude() < (1 << (bits - 1))


@dataclass
class RangeResult:
    verdict: "KV.Verdict"
    out_interval: Interval
    fits: bool


def grade_no_overflow(out_interval: Interval, *, bits: int = 64, op: str = "machine-int op") -> RangeResult:
    """EXACT iff the (sound, over-approximating) output interval provably fits the machine width ⇒ the fixed-width
    fast path cannot overflow. Else DECLINE the fast path (never a wrapped answer)."""
    ok = fits_width(out_interval, bits)
    if not ok:
        v = KV.decline(f"range analysis: output interval [{out_interval.lo},{out_interval.hi}] can exceed "
                       f"{bits}-bit (|v|≥2^{bits - 1}) ⇒ DECLINE the fixed-width fast path (no wrap)", "range")
        return RangeResult(v, out_interval, False)
    cert = KV.Cert(KV.EXACT, "interval_no_overflow", passed=True, check_cost="abstract interpretation (intervals)",
                   detail=f"{op}: output ⊆ [{out_interval.lo},{out_interval.hi}] ⊂ signed-{bits} ⇒ overflow-free fast path")
    return RangeResult(KV.exact(out_interval, "range", f"Clock-B range proof (signed-{bits})", cert),
                       out_interval, True)


# ── worked examples: the convolution / matmul accumulator bounds, now as a reusable interval proof ─────────
def conv_accumulator_interval(value_range: int, n: int) -> Interval:
    """Bound on (a⋆b)[k] = Σ_{i} a[i]·b[k−i] with |a|,|b| ≤ value_range over ≤ n terms — the NTT EXACT condition."""
    elt = Interval(-value_range, value_range)
    return (elt * elt).scale_sum(n)


def matmul_accumulator_interval(value_range: int, k: int) -> Interval:
    """Bound on C_ij = Σ_t A_it·B_tj with |A|,|B| ≤ value_range over k terms — the blocked-matmul EXACT condition."""
    elt = Interval(-value_range, value_range)
    return (elt * elt).scale_sum(k)
