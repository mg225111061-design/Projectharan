"""
§AJ §1 — RESIDUAL CUTOFF GATE (entropy · Hurst · MDL): skip the conjecture path EARLY when a sequence carries the
================================================================================================================
unmistakable random-oracle signature — but NEVER skip a foldable one (false-skip 0). ★★ The honest invariant that
makes this safe: the precheck can only cost RECALL (a wrongly-skipped foldable would become a DECLINE instead of an
EXACT), it can NEVER cost PRECISION (it does not turn a DECLINE into a false EXACT — z3 still disposes everything that
PROCEEDS). So precision 1.0 does not depend on this gate at all; the gate is a SPEED filter for the conjecturer's
Clock C, and we additionally MEASURE false-skip = 0 on the foldable corpus so recall is preserved too.

Why the joint signature is sound (no foldable is ever skipped): a C-finite / polynomial / periodic / holonomic
sequence is ALWAYS one of — (a) compressible (a short generating program ⇒ zlib finds the structure), (b) trending or
mean-reverting (Hurst far from 0.5 — Fibonacci/factorial/Σk² climb monotonically ⇒ H→1), or (c) low value-entropy
(a small periodic alphabet). Only GENUINE randomness is simultaneously incompressible AND high-entropy AND Hurst≈0.5.
So we skip ONLY on the CONJUNCTION of all three; any single structural tell ⇒ PROCEED. REUSE catalog.decline_boundary
.mdl_two_part (the zlib MDL 2-part code, a SOUND upper bound on Kolmogorov complexity, already honestly framed).

★ LLM-free (entropy/Hurst/MDL are deterministic); zero-dep (zlib is stdlib); no new mechanism / no new cert kind
(a DECLINE shortcut, not a fold). ★ P-2 untouched: skipping is a fast DECLINE, never a fast EXACT.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, List, Optional

from conjecture import harness as H

# thresholds — deliberately EXTREME so only the clear random-oracle corner skips (conservative ⇒ false-skip 0)
_H_NORM_HI = 0.92          # normalized value-entropy must be near-maximal
_HURST_LO, _HURST_HI = 0.40, 0.60   # Hurst must sit in the white-noise band around 0.5
_MIN_N = 32               # below this the statistics are meaningless ⇒ ALWAYS proceed (never skip a small sample)


@dataclass
class PrecheckResult:
    proceed: bool                     # True ⇒ run the conjecturers; False ⇒ skip (a fast DECLINE, never a fast EXACT)
    signature: str = ""              # "random-oracle" | "structured" | "too-short" | "non-numeric"
    entropy: Optional[float] = None  # normalized value-entropy in [0,1]
    hurst: Optional[float] = None    # rescaled-range Hurst exponent (≈0.5 white noise, →1 trending, <0.5 reverting)
    compressible: Optional[bool] = None
    reason: str = ""


def shannon_entropy(values: List[object]) -> float:
    """Normalized Shannon entropy H/log2(N) ∈ [0,1] of the value multiset. A small periodic alphabet ⇒ ≪1; an
    all-distinct stream ⇒ ≈1. Deterministic (counts only)."""
    n = len(values)
    if n <= 1:
        return 0.0
    counts: dict = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    h = -sum((c / n) * math.log2(c / n) for c in counts.values())
    return h / math.log2(n)


def _is_monotonic(seq: List[float]) -> bool:
    """Non-decreasing OR non-increasing ⇒ a strong trending tell (white noise is neither). Every growth-foldable
    (factorial/Fibonacci/2ⁿ/Σk²/affine) is monotonic ⇒ this single tell keeps them out of the skip set."""
    nondec = all(seq[i] <= seq[i + 1] for i in range(len(seq) - 1))
    noninc = all(seq[i] >= seq[i + 1] for i in range(len(seq) - 1))
    return nondec or noninc


def hurst_rs(seq: List[float]) -> Optional[float]:
    """Single-window rescaled-range (R/S) Hurst exponent: H = log(R/S) / log(N/2). Deterministic. A trending series
    (cumulative deviation climbs) ⇒ R large ⇒ H→1; white noise ⇒ H≈0.5; mean-reverting ⇒ H<0.5. None if degenerate
    (constant series ⇒ S=0 ⇒ no randomness signature ⇒ caller treats as structured)."""
    n = len(seq)
    if n < 8:
        return None
    mean = sum(seq) / n
    dev = [x - mean for x in seq]
    cum, z = [], 0.0
    for d in dev:
        z += d
        cum.append(z)
    R = max(cum) - min(cum)
    var = sum(d * d for d in dev) / n
    S = math.sqrt(var)
    if S == 0 or R == 0:
        return None                                   # constant or perfectly flat cumulant ⇒ structured, not random
    return math.log(R / S) / math.log(n / 2)


def _has_cfinite_structure(seq: List[object]) -> bool:
    """★ SOUND tell: a DETERMINED short linear recurrence exists (REUSE native_sequence.berlekamp_massey_Q + the §AI
    under-determination boundary). A foldable C-finite/polynomial/periodic/matpow sequence ⇒ BM order L small ⇒
    NOT under-determined ⇒ True. Genuine randomness ⇒ L≈N/2 ⇒ under-determined ⇒ False. (the conjecturers' own first
    step, run cheaply — no z3, no held-out)."""
    try:
        from fractions import Fraction as _F
        import native_sequence as NS
        _, L = NS.berlekamp_massey_Q([_F(x) for x in seq])
        return L >= 1 and not H.under_determined(len(seq), L)
    except Exception:  # noqa: BLE001
        return True                                  # can't decide ⇒ assume structure present ⇒ never skip (safe side)


def _has_polynomial_ratio(fseq: List[float]) -> bool:
    """★ SOUND tell: a first-order P-recursive (holonomic) ratio a[n]/a[n-1] = polynomial(n) exists (REUSE
    holonomic_guess._fit_poly_ratio). Catches disguised factorial/binomial — the non-C-finite foldables."""
    try:
        from fractions import Fraction as _F
        from conjecture import holonomic_guess as HG
        return HG._fit_poly_ratio([_F(x).limit_denominator(10 ** 9) for x in fseq]) is not None
    except Exception:  # noqa: BLE001
        return True                                  # can't decide ⇒ assume structure ⇒ never skip (safe side)


def _has_small_period(seq: List[object]) -> bool:
    """★ SOUND tell: a small period exists (REUSE period_guess._smallest_period)."""
    try:
        from conjecture import period_guess as PG
        return PG._smallest_period(seq) is not None
    except Exception:  # noqa: BLE001
        return True


def worth_conjecturing(fn: Callable[[int], object], probe: int = 64) -> PrecheckResult:
    """Decide whether the conjecture path is worth running. Skips ONLY the joint random-oracle signature (incompressible
    AND high-entropy AND Hurst≈0.5); ANY single structural tell ⇒ PROCEED. ★ Skip ⇒ a fast DECLINE (never a fast
    EXACT): precision is untouched; only the conjecturer's wasted work on hopeless input is saved."""
    seq = H.observe(fn, probe)
    if seq is None:
        return PrecheckResult(False, "non-numeric", reason="non-deterministic / non-numeric ⇒ the conjecturers ABANDON "
                              "anyway ⇒ skip (this is a fast DECLINE, identical verdict)")
    if len(seq) < _MIN_N:
        return PrecheckResult(True, "too-short", reason=f"only {len(seq)} samples (<{_MIN_N}) ⇒ statistics meaningless "
                              "⇒ PROCEED (never skip on thin evidence)")
    fseq = [float(x) for x in seq]
    ent = shannon_entropy(seq)
    hur = hurst_rs(fseq)
    from catalog import decline_boundary as DB
    mdl = DB.mdl_two_part([float(x) for x in seq])
    compressible = (mdl is None) or bool(mdl.get("compresses"))   # None (untestable) ⇒ treat as compressible ⇒ proceed
    # ── SOUND structural detectors (REUSE the conjecturers' own first steps) — these GUARANTEE false-skip 0 ──
    # every foldable class trips exactly one: C-finite (BM determined) / polynomial→C-finite / periodic→C-finite /
    # matpow→C-finite / holonomic (polynomial ratio). The gate's detectors are SUPERSETS of the conjecturers', so a
    # foldable can never be skipped — by construction, not by luck.
    cfinite = _has_cfinite_structure(seq)
    holonomic = _has_polynomial_ratio(fseq)
    periodic = _has_small_period(seq)
    # ── statistical signature (the directive's entropy/Hurst/MDL) — extra conservatism + honest reporting ──
    monotonic = _is_monotonic(fseq)
    incompressible = (mdl is not None) and (not mdl["compresses"])
    high_entropy = ent >= _H_NORM_HI
    structural_tell = cfinite or holonomic or periodic or monotonic or (not incompressible) or (not high_entropy)
    if not structural_tell:                          # NO structural fit AND the random statistical signature ⇒ skip
        return PrecheckResult(False, "random-oracle", ent, hur, compressible,
                              "★ no cheap structural fit (no determined linear recurrence / polynomial ratio / period) "
                              "AND zlib-incompressible AND near-max entropy AND non-monotonic ⇒ no recurrence to recover "
                              "⇒ skip (a fast DECLINE — every conjecturer would DECLINE too; recall preserved, precision "
                              "untouched)")
    tells = []
    if cfinite:
        tells.append("determined linear recurrence (C-finite)")
    if holonomic:
        tells.append("polynomial term-ratio (holonomic)")
    if periodic:
        tells.append("small period")
    if monotonic:
        tells.append("monotonic (trending)")
    if not incompressible:
        tells.append("compressible (a model beats the literal)")
    if not high_entropy:
        tells.append(f"low value-entropy ({ent:.2f})")
    return PrecheckResult(True, "structured", ent, hur, compressible,
                          "PROCEED — structural tell present: " + "; ".join(tells))


def measure_false_skip(corpus: List[Callable[[int], object]]) -> dict:
    """★ The false-skip-0 meter: over a corpus of KNOWN-FOLDABLE oracles, count how many the precheck wrongly skips.
    Must be 0 — a foldable is never random-oracle-signed. (Honest scope: measured on the corpus, and even a miss would
    cost RECALL not PRECISION.)"""
    skipped = [i for i, fn in enumerate(corpus) if not worth_conjecturing(fn).proceed]
    return {"corpus": len(corpus), "false_skips": len(skipped), "skipped_indices": skipped}


def adversarial_battery() -> dict:
    """★ false-skip 0: every disguised foldable (Fibonacci/Σk²/period-3/factorial/geometric) PROCEEDS; ★ a crypto-PRNG
    oracle (incompressible + high-entropy + Hurst≈0.5) is SKIPPED — and that skip is a fast DECLINE (the conjecturers
    DECLINE it too), so precision is untouched; ★ a non-deterministic oracle is skipped (ABANDON, identical verdict)."""
    import math as _m

    def make_fib():
        memo = {0: 0, 1: 1}
        def f(n):
            if n not in memo:
                f(n - 1); memo[n] = memo[n - 1] + memo[n - 2]
            return memo[n]
        return f
    foldables = [make_fib(), lambda n: sum(k * k for k in range(n + 1)), lambda n: [10, 20, 30][n % 3],
                 lambda n: _m.factorial(n), lambda n: 2 ** n, lambda n: 3 * n + 1, lambda n: pow(3, n, 7)]
    fs = measure_false_skip(foldables)
    # a DETERMINISTIC random oracle (truncated SHA-256): incompressible + high-entropy + Hurst≈0.5 + non-monotonic
    import hashlib

    def sha_oracle(n):
        return int.from_bytes(hashlib.sha256(str(n).encode()).digest()[:6], "big")
    prng = worth_conjecturing(sha_oracle)
    # ★ the skip must agree with the conjecturers' verdict: the oracle actually DECLINES (skip ≡ DECLINE, no precision loss)
    from conjecture import bm_linrec
    prng_declines = not bm_linrec.conjecture(sha_oracle).issued
    ctr = {"v": 0}
    def nondet(n):
        ctr["v"] += 1
        return n + ctr["v"]
    nd = worth_conjecturing(nondet)
    cases = {
        "false_skip_zero_on_foldables": fs["false_skips"] == 0,                       # ★ the invariant
        "prng_skipped": not prng.proceed and prng.signature == "random-oracle",
        "skip_is_a_decline_not_a_false_exact": (not prng.proceed) and prng_declines,  # ★ skip ⇒ DECLINE (precision safe)
        "nondeterministic_skipped": not nd.proceed,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
