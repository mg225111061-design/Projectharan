"""
§AP §2 — SCIPY/NUMPY SIGNAL RECOGNITION: the general form of the §AN R=44 recognition. A recurrence hidden behind a
================================================================================================================
library name (cumsum / lfilter / EMA / moving-average / popcount) is invisible to the black-box oracle extractor;
libsig NAMES the idiom (§2.1) and routes its oracle to the existing lens (§2.2), which disposes it under the z3 gate.
No new mechanism, no new disposer — recognition only. Transcendental DFT/FFT is an honest DECLINE (it is not a fold).
"""
from __future__ import annotations

from typing import Callable, Optional

from recall.libsig import signature_match as SM, extract_recurrence as ER


def fold(src: str, oracle: Optional[Callable[[int], object]]) -> ER.ExtractResult:
    """Recognize the idiom in `src`, then dispose its `oracle` through the matched existing lens (z3-gated)."""
    m = SM.signature_match(src)
    if not m.idiom:
        return ER.ExtractResult(False, "", "", "", "no library idiom recognized ⇒ DECLINE (nothing to route)")
    return ER.extract_and_fold(m.idiom, m.lens, oracle)


def adversarial_battery() -> dict:
    """★ the §AN R=44 identity GENERALIZED: a popcount bit-idiom is recognized and folds via M22; ★ cumsum (running sum
    ⇒ triangular), cumprod (⇒ factorial, holonomic), an IIR/Fibonacci filter (⇒ C-finite), a moving-average (⇒ linear),
    and an EMA (⇒ geometric) each recognized and folded by the existing conjecturers; ★★ a transcendental DFT is an
    honest DECLINE (not a fold); ★★ a body NAMED popcount but computing randomness DECLINEs (the gate, not the name,
    disposes — no false EXACT)."""
    import hashlib

    def fib(n):
        a, b = 0, 1
        for _ in range(n):
            a, b = b, a + b
        return a
    def fact(n):
        p = 1
        for i in range(1, n + 1):
            p *= i
        return p

    pc = fold("x = bin(n).count('1')", lambda n: bin(n).count("1"))                  # popcount → M22 (R=44 identity)
    cs = fold("s = np.cumsum(x)", lambda n: n * (n + 1) // 2)                          # cumsum → triangular
    cp = fold("p = np.cumprod(x)", fact)                                              # cumprod → factorial (holonomic)
    iir = fold("y[i] = y[i-1] + y[i-2]  # iir x[i]", fib)                             # IIR → C-finite (Fibonacci filter)
    ma = fold("y = moving_average(x, w)", lambda n: (n + 1) ** 2)                     # moving-average → linear-recurrence
    ema = fold("y = alpha*x[i] + (1 - alpha)*y[i-1]  # ema", lambda n: 2 ** n)        # EMA → geometric

    dft = fold("X = dft(x)  # cos( ) sin( )", lambda n: n)                            # transcendental ⇒ DECLINE lens
    fake = fold("v = bin(n).count('1')  # popcount", lambda n: int.from_bytes(
        hashlib.sha256(str(n).encode()).digest()[:6], "big"))                        # named popcount but RANDOM

    cases = {
        "popcount_idiom_folds_via_M22": pc.folded and "automatic" in pc.structure.lower(),  # ★ the R=44 identity
        "cumsum_folds": cs.folded,
        "cumprod_folds": cp.folded,
        "iir_filter_folds": iir.folded,
        "moving_average_folds": ma.folded,
        "ema_folds": ema.folded,
        "dft_honest_decline": not dft.folded,                                        # ★★ transcendental, not a fold
        "named_popcount_but_random_declines": not fake.folded,                       # ★★ the gate disposes, not the name
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
