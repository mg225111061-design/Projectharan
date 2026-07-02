"""
§AP §2.1 — LIBRARY-IDIOM SIGNATURE MATCH (the recognition layer): name the scipy/numpy signal idiom in the source.
================================================================================================================
A large share of "non-foldable" REAL code is a textbook signal/numeric idiom expressed through a library call rather
than an explicit loop — so the black-box oracle extractor never sees the recurrence. These idioms ARE recurrences /
closed forms:
  cumsum → running-sum recurrence s[n]=s[n-1]+x[n];   diff → first difference;   cumprod → product recurrence;
  lfilter / IIR → an ARMA (C-finite) recurrence from the denominator coefficients;   EMA → a geometric recurrence;
  moving_average / uniform convolve → the §Z sliding-window incremental update;   bit popcount → the §AN M22 k-kernel.
★ This is the GENERAL form of the §AN R=44 recognition: popcount is just one idiom; the gap was always "the recurrence
is hidden behind a library name". signature_match is a LIBERAL proposer (syntactic) — §2.2 lifts it and the EXISTING z3
gate disposes, so a wrong name can never manufacture a false EXACT.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IdiomMatch:
    idiom: str                           # "" when nothing recognized
    lens: str = ""                       # which existing lens §2.2 should route to
    foldable_class: str = ""             # the structure the idiom lifts to
    detail: str = ""


# idiom → (recall lens, lifted structure). The transcendental idioms map to a DECLINE lens (honest: not a fold).
_IDIOMS = {
    "popcount":       ("k_automatic", "k_regular(M22)"),
    "cumsum":         ("conjecture", "linear_recurrence"),
    "running_sum":    ("conjecture", "linear_recurrence"),
    "cumprod":        ("conjecture", "product_recurrence"),
    "diff":           ("conjecture", "first_difference"),
    "iir":            ("conjecture", "c_finite(ARMA)"),
    "lfilter":        ("conjecture", "c_finite(ARMA)"),
    "ema":            ("conjecture", "geometric"),
    "moving_average": ("window", "sliding_window_incremental"),
    "dft":            ("decline", "transcendental(non-fold)"),
    "fft":            ("decline", "transcendental(non-fold)"),
}


def signature_match(src: str) -> IdiomMatch:
    """Syntactically recognize the dominant library/numeric idiom in `src` (liberal proposer; the gate disposes)."""
    s = src.lower()
    # bit popcount idioms (the §AN R=44 family) — recognized first (most specific)
    if ".count('1')" in s or '.count("1")' in s or "bit_count" in s or "popcount" in s:
        return _mk("popcount")
    if "cumprod" in s or "running_prod" in s:
        return _mk("cumprod")
    if "cumsum" in s or "running_sum" in s or "np.add.accumulate" in s:
        return _mk("cumsum")
    if "moving_average" in s or "moving_avg" in s or ("convolve" in s and ("ones" in s or "/ w" in s or "/w" in s)):
        return _mk("moving_average")
    if "lfilter" in s or "signal.lfilter" in s:
        return _mk("lfilter")
    if "ema" in s or "ewm" in s or ("alpha" in s and "1 - alpha" in s) or ("alpha" in s and "1-alpha" in s):
        return _mk("ema")
    if "iir" in s or ("y[i-1]" in s and "x[i]" in s):
        return _mk("iir")
    if "np.diff" in s or "diff(" in s:
        return _mk("diff")
    if "fft" in s:
        return _mk("fft")
    if "dft" in s or ("cos(" in s and "sin(" in s):
        return _mk("dft")
    return IdiomMatch("", "", "", "no library/numeric idiom recognized")


def _mk(idiom: str) -> IdiomMatch:
    lens, klass = _IDIOMS[idiom]
    return IdiomMatch(idiom, lens, klass, f"recognized {idiom!r} idiom ⇒ route to the {lens} lens ({klass})")
