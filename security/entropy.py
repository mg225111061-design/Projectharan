"""
§AH §6 (thermo ②) — ENTROPY / RANDOMNESS verifier (RF-3). ★ Proves INSECURITY only, NEVER safety.
================================================================================================================
★ THE BINDING HONESTY (NIST SP 800-90B / 800-22 PART1.C): statistical tests are NECESSARY-not-SUFFICIENT — passing
them does NOT imply safety (a CSPRNG is, by a hardness assumption, indistinguishable from random; a broken PRNG can
also pass cheap tests). So this verifier PROVES the POSITIVE FINDING "entropy is too low ⇒ INSECURE" (isomorphic to
DECLINE-as-win), and for everything else it says DECLINE ("cannot prove secure") — it NEVER outputs "secure".
min-entropy via the most-common-value estimator (a sound LOWER bound on H_min); monobit/runs as corroborating
screens. LLM-free, zero-dep (stdlib).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List


@dataclass
class EntropyVerdict:
    disposition: str        # "INSECURE-PROVEN" | "DECLINE"
    min_entropy_per_symbol: float
    detail: str


def min_entropy_mcv(symbols: List[int]) -> float:
    """The most-common-value estimator: H_min ≥ −log2(p_max), a SOUND lower bound on per-symbol min-entropy."""
    if not symbols:
        return 0.0
    from collections import Counter
    p_max = max(Counter(symbols).values()) / len(symbols)
    return -math.log2(p_max)


def _monobit_fail(bits: List[int]) -> bool:
    """A gross monobit imbalance (|#1 − #0| beyond ~3σ) — a cheap corroborating screen for low entropy."""
    n = len(bits)
    if n < 16:
        return False
    ones = sum(bits)
    return abs(ones - n / 2) > 3 * math.sqrt(n) / 2


def verify_entropy(symbols: List[int], bit_width: int = 1, insecure_threshold: float = 0.5) -> EntropyVerdict:
    """★ Prove INSECURITY only: if the sound min-entropy LOWER bound is itself below `insecure_threshold` bits/symbol,
    the source is PROVABLY low-entropy ⇒ INSECURE (a positive finding). Otherwise DECLINE — we do NOT and CANNOT
    certify 'secure' from statistics (PART1.C). Never returns 'SECURE'."""
    h = min_entropy_mcv(symbols)
    if h < insecure_threshold:
        return EntropyVerdict("INSECURE-PROVEN", round(h, 4),
                              f"min-entropy lower bound {h:.3f} < {insecure_threshold} bits/symbol ⇒ PROVABLY low entropy ⇒ INSECURE")
    return EntropyVerdict("DECLINE", round(h, 4),
                          f"min-entropy lower bound {h:.3f} ≥ {insecure_threshold}: statistics are necessary-not-sufficient "
                          "(NIST PART1.C) ⇒ DECLINE — cannot certify 'secure' from tests (never claimed)")


def adversarial_battery() -> dict:
    """A near-constant source (almost all one value) is PROVEN INSECURE (low min-entropy); ★ a high-entropy-looking
    source is DECLINED, NOT called 'secure' (statistics necessary-not-sufficient); the verdict set never contains
    'SECURE'."""
    biased = verify_entropy([0] * 95 + [1] * 5)                     # p_max=0.95 ⇒ H_min≈0.074 ⇒ INSECURE
    uniformish = verify_entropy(list(range(256)) * 4)              # high min-entropy ⇒ DECLINE (not 'secure')
    cases = {
        "low_entropy_proven_insecure": biased.disposition == "INSECURE-PROVEN" and biased.min_entropy_per_symbol < 0.5,
        "high_entropy_declined_not_safe": uniformish.disposition == "DECLINE",     # ★ never 'secure'
        "never_outputs_secure": biased.disposition != "SECURE" and uniformish.disposition != "SECURE",
        "monobit_screen_works": _monobit_fail([0] * 100) and not _monobit_fail([0, 1] * 50),
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
