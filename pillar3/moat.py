"""
Pillar 3 · §∞ — the moat battery (one place that proves the verifier refutes EVERY wrong swap).
================================================================================================
The whole system's credibility is the moat: a faster-but-wrong transform must be REJECTED, every time. This
module gathers an adversarial battery of subtly-wrong swaps from every family (lifting, equiv transforms,
algorithm recognizers) plus a few new subtle bugs, and checks each is caught — by Z3 (a counterexample, for
linear-arithmetic swaps) or by differential over a strong input set (for control-flow swaps). The test asserts
ZERO false-accepts: not one wrong swap slips through. Widening this battery widens the moat.
"""
from __future__ import annotations

from typing import Callable, List, Optional, Tuple

import z3

from pillar3 import algorithms as AG
from pillar3 import equiv as EQ
from pillar3 import equiv_transforms as ET
from pillar3 import inputgen as IG
from pillar3 import lifting as LF


# ── a few NEW subtle wrongs (beyond the per-phase ones) — each is "right on many inputs, wrong somewhere" ──
def rs_wrong_drop_first(a):                                  # prefix sums but omits a[0] from every prefix
    out = []
    s = 0
    first = True
    for x in a:
        if first:
            first = False
        else:
            s = s + x
        out.append(s)
    return out


def fc_wrong_sign(a, c):                                     # sum(c*x) but negates c — wrong for c≠0
    return -c * sum(a)


def abs_square_wrong(a):                                     # "x*x" but writes |x|*x — wrong for negatives only
    return [(x if x >= 0 else -x) * x for x in a]


def square_ref(a):
    return [x * x for x in a]


def rs_wrong_double_last(a):                                 # correct prefix sums EXCEPT the last entry is doubled
    out = []
    s = 0
    for x in a:
        s = s + x
        out.append(s)
    if out:
        out[-1] = out[-1] + a[-1]
    return out


def fc_wrong_off_by_one(a, c):                              # c·Σa but +1 — wrong by a constant
    return c * sum(a) + 1


_Z3_WRONGS: List[Tuple[str, Callable, Callable, Callable]] = [
    ("prefix_sum_offbyone", LF.rs_original, LF.rs_wrong, LF._sym_int_list),
    ("prefix_sum_drop_first", LF.rs_original, rs_wrong_drop_first, LF._sym_int_list),
    ("telescope_signflip", LF.ts_original, LF.ts_wrong, LF._sym_int_list),
    ("range_query_offbyone", LF.rq_original, LF.rq_wrong, LF._sym_int_list_and_q),
    ("diff_array_sign", LF.da_original, LF.da_wrong, LF._sym_int_list_and_ups),
    ("factor_constant_signflip", LF.fc_original, fc_wrong_sign, LF._sym_int_list_and_c),
    ("strength_reduction_wrong", ET.sr_original, ET.sr_wrong, ET._sym_list),
    ("cse_wrong", ET.cse_original, ET.cse_wrong, ET._sym_list),
    ("loop_invariant_wrong", ET.li_original, ET.li_wrong, ET._sym_abxs),
    ("prefix_sum_double_last", LF.rs_original, rs_wrong_double_last, LF._sym_int_list),
    ("factor_constant_off_by_one", LF.fc_original, fc_wrong_off_by_one, LF._sym_int_list_and_c),
]


def _neg_bearing_inputs() -> List[tuple]:
    return [([-1],), ([3, -2, 5],), ([-7, -8],), ([0, -1, 2],), ([10, -10, 10],)]


_DIFF_WRONGS: List[Tuple[str, Callable, Callable, Callable]] = [
    ("kadane_no_running_sum", AG.kadane_naive, AG.kadane_wrong, AG._kadane_inputs),
    ("two_sum_same_index", AG.two_sum_naive, AG.two_sum_wrong, AG._two_sum_inputs),
    ("majority_no_verify", AG.majority_naive, AG.majority_wrong, AG._majority_inputs),
    # control-flow swap (uses `if x>=0`) so Z3 can't run it symbolically — caught differentially on negatives
    ("abs_square_neg_only", square_ref, abs_square_wrong, _neg_bearing_inputs),
]


def refute_z3(orig: Callable, wrong: Callable, sym_factory: Callable,
              sizes: Tuple[int, ...] = (3, 5, 8)) -> "Tuple[bool, Optional[str]]":
    """A wrong swap is refuted iff Z3 is NOT able to prove equivalence AND produced a counterexample."""
    proven, cex = EQ.prove_equiv(orig, wrong, sym_factory, sizes)
    return (not proven and "counterexample" in str(cex)), cex


def refute_diff(orig: Callable, wrong: Callable, gen: Callable[[], List[tuple]]) -> "Tuple[bool, Optional[str]]":
    """A control-flow wrong swap is refuted iff the strong evidence set finds a divergence from the gold oracle."""
    div = IG.first_divergence(orig, wrong, gen())
    return div is not None, div


def battery() -> List[Tuple[str, str, bool, str]]:
    """Run the whole battery. Returns (name, mode, refuted?, witness) for each adversarial wrong swap."""
    out: List[Tuple[str, str, bool, str]] = []
    for name, o, w, sf in _Z3_WRONGS:
        ok, cex = refute_z3(o, w, sf)
        out.append((name, "z3", ok, str(cex)[:60]))
    for name, o, w, gen in _DIFF_WRONGS:
        ok, div = refute_diff(o, w, gen)
        out.append((name, "differential", ok, str(div)[:60]))
    return out
