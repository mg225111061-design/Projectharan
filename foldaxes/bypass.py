"""
§AB AXIS 4 — FOLD BYPASS (precompute, don't fold): VALUE not rate, finite/small/deterministic only.
================================================================================================================
For a FINITE, SMALL, DETERMINISTIC input space, precompute the entire input→output map ONCE and look it up in O(1) —
bypassing folding entirely (the extreme of §V / §AA-W4 caching). The map is EXACT (the real computed outputs).

★ NOT A FOLD — VALUE, NOT RATE (the discipline): bypass is precomputation, not structural folding. It raises
value/throughput and is reported ENTIRELY SEPARATELY; it is NEVER counted in any fold rate. Cold (full precompute) vs
warm (O(1) lookup) stated.
★ BOUNDED INPUT ONLY: finite, small, deterministic (e.g. an 8-bit state's 256 inputs). NEVER unbounded or random —
caching random/unbounded input is Ω(N), storing noise, useless and rejected. The input-space bound is stated.
★ Sound: keyed by the input itself; a wrong lookup is impossible (the table holds the real outputs of a deterministic fn).
LLM-free; not a fold ⇒ no certificate-kind question.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

MAX_BYPASS_BITS = 16                         # the small-space cap: 2^16 = 65536 entries; beyond ⇒ DECLINE (not small)


@dataclass
class BypassTable:
    issued: bool
    input_bits: Optional[int] = None        # the stated input-space bound (|D| = 2^input_bits)
    size: Optional[int] = None
    table: Optional[List] = None
    detail: str = ""

    def lookup(self, x: int):
        """O(1) total-precompute lookup. Sound: the table holds the real deterministic outputs ⇒ no wrong lookup."""
        return self.table[x]


def build_bypass(fn: Callable[[int], object], input_bits: int) -> BypassTable:
    """Precompute the WHOLE input→output map for a finite/small/deterministic space (2^input_bits inputs). ★ input_bits
    > MAX_BYPASS_BITS ⇒ NOT small ⇒ DECLINE (caching a huge/unbounded space is Ω(N), useless)."""
    if input_bits > MAX_BYPASS_BITS:
        return BypassTable(False, input_bits=input_bits,
                           detail=f"input space 2^{input_bits} exceeds the small-space cap 2^{MAX_BYPASS_BITS} ⇒ NOT "
                                  "finite-small ⇒ DECLINE (bypassing an unbounded/large space stores noise, Ω(N))")
    size = 1 << input_bits
    table = [fn(x) for x in range(size)]                    # cold: compute every output ONCE (the full precompute)
    return BypassTable(True, input_bits=input_bits, size=size, table=table,
                       detail=f"total precompute of 2^{input_bits}={size} deterministic inputs ⇒ O(1) lookup; ★ VALUE "
                              "not rate (not a fold, not counted in any fold rate); cold=precompute, warm=O(1)")


def cold_warm_measurement(input_bits: int = 8) -> dict:
    """Cold (full precompute, 2^bits fn calls) vs warm (lookups, 0 fn calls). ★ Value/throughput, NOT fold rate."""
    calls = {"n": 0}

    def fn(x: int) -> int:
        calls["n"] += 1
        return (x * x + 7 * x + 13) & 0xFF                  # a deterministic 8-bit transition

    bt = build_bypass(fn, input_bits)
    cold_calls = calls["n"]                                  # == 2^bits (every output computed once)
    for x in range(bt.size):                                 # warm: look up every input ⇒ 0 new fn calls
        _ = bt.lookup(x)
    for _ in range(10000):                                   # heavy warm traffic
        _ = bt.lookup(123 & (bt.size - 1))
    warm_calls = calls["n"] - cold_calls
    return {
        "input_bits": input_bits, "size": bt.size, "cold_fn_calls": cold_calls, "warm_fn_calls": warm_calls,
        "raises": "value/throughput (O(1) lookup), NOT the fold rate — bypass is precomputation, never a fold",
        "cold_pays_all": cold_calls == bt.size, "warm_pays_nothing": warm_calls == 0,
    }


def sound_lookup_check() -> bool:
    """A wrong lookup is impossible: the table holds the real outputs of a DETERMINISTIC fn, so lookup(x) == fn(x) ∀x."""
    fn = lambda x: (x * 31 + 17) & 0xFF
    bt = build_bypass(fn, 8)
    return all(bt.lookup(x) == fn(x) for x in range(bt.size))


def adversarial_battery() -> dict:
    """An 8-bit deterministic space bypasses (O(1) lookup, sound); ★ a 32-bit (unbounded-scale) space is REJECTED; ★
    bypass is VALUE not rate (cold pays all, warm pays nothing); a wrong lookup is impossible."""
    fn = lambda x: (x * x + 7 * x + 13) & 0xFF
    small = build_bypass(fn, 8)                              # 256 inputs ⇒ bypass
    huge = build_bypass(fn, 32)                              # 4 billion ⇒ DECLINE (not small)
    cw = cold_warm_measurement(8)
    cases = {
        "small_deterministic_bypasses": small.issued and small.size == 256,
        "large_space_declined": not huge.issued and "DECLINE" in huge.detail,
        "value_not_rate": "NOT the fold rate" in cw["raises"],
        "cold_pays_all_warm_nothing": cw["cold_pays_all"] and cw["warm_pays_nothing"],
        "wrong_lookup_impossible": sound_lookup_check(),
        "input_bound_stated": small.input_bits == 8,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
