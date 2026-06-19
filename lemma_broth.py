"""
PHASE 3.S1 — lemma broth: offline-proven invariants, O(1) lookup, CHEAP recheck (search paid once).
====================================================================================================
The amortization principle (§ first-principle): the EXPENSIVE proof/search happens ONCE at build time; what
is STORED is the CERTIFICATE, and at runtime we only do a CHEAP recheck (O(1) rational arithmetic / a finite
base-case test) — never re-search. This is what lets a 3000+ invariant library cost ~nothing at runtime.

★ ENV HONESTY: hypergeometric/D-finite SEARCH (`ore_algebra`) is [BLOCKED: not installed]. The broth holds the
families we CAN brew dependency-0: polynomial sums (Faulhaber), C-finite recurrences, geometric — each with a
cheap stored recheck. Frequent honest DECLINE outside these families is correct behaviour, not a bug. ★
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import sympy as sp


def ore_algebra_available() -> bool:
    try:
        import ore_algebra  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


@dataclass
class BrothCert:
    key: str
    kind: str                   # polynomial-sum | c-finite | geometric
    cert_data: str              # closed form (sum) or recurrence coeffs (c-finite)
    strength: str
    recheck_kind: str           # finite-base-case | companion-equality


@dataclass
class AmortReport:
    n_entries: int
    brew_ms: float              # OFFLINE one-time cost (the expensive search/proof)
    recheck_us_per: float       # RUNTIME per-lookup CHEAP recheck cost (O(1))
    hit_rate: float
    recheck_pass_rate: float
    ore_algebra: str


def cheap_recheck(cert: BrothCert) -> bool:
    """The RUNTIME-cheap recheck of a stored certificate (NOT a re-search). Polynomial sum → finite-base-case
    PIT; C-finite → companion≡naive at a few points. Both O(1)-ish, independent of the offline search cost."""
    if cert.kind in ("polynomial-sum", "geometric"):
        import finite_check as FC
        k, n = FC._k, FC._n
        try:
            summand = sp.sympify(cert.key.split("::", 1)[1], locals={"k": k, "n": n})
            closed = sp.sympify(cert.cert_data, locals={"n": n})
            return FC.verify_sum(summand, closed) is not None
        except Exception:  # noqa: BLE001
            return False
    if cert.kind == "c-finite":
        import cfinite
        try:
            c = [int(x) for x in cert.cert_data.strip("[]").split(",")]
            return cfinite.verify_cfinite(c, [0, 1] if len(c) == 2 else [0] * (len(c) - 1) + [1])[0]
        except Exception:  # noqa: BLE001
            return False
    return False


def brew_broth() -> Tuple[Dict[str, BrothCert], float]:
    """BUILD-TIME: assemble the broth from the soup library (the search is paid here, once). Returns the
    O(1) index + the one-time brew cost."""
    import soup_lib as SL
    t0 = time.perf_counter()
    lib, _ = SL.get_library()
    index: Dict[str, BrothCert] = {}
    for lem in lib.lemmas:
        if lem.family == "c-finite":
            index[lem.key] = BrothCert(lem.key, "c-finite", lem.key.split(":", 1)[1], lem.strength, "companion-equality")
        elif lem.summand:
            key = f"sum::{lem.summand}"
            kind = "geometric" if lem.family == "geometric-hypergeometric" else "polynomial-sum"
            index[key] = BrothCert(key, kind, lem.closed_form, lem.strength, "finite-base-case")
    return index, (time.perf_counter() - t0) * 1000


def lookup(index: Dict[str, BrothCert], key: str) -> Optional[BrothCert]:
    """O(1) content lookup of a pre-proven invariant (no search)."""
    return index.get(key)


def measure_amortization() -> AmortReport:
    """Measure the offline (one-time brew) vs runtime (per-lookup cheap recheck) split + hit/recheck rates."""
    index, brew_ms = brew_broth()
    # corpus of lookups (sum summands + recurrence keys) — measure hit rate + cheap-recheck cost
    probes = ["sum::k", "sum::k**2", "sum::k*2**k", "cfin:[1, 1]", "cfin:[2, 1]", "sum::1/k"]
    hits = [lookup(index, p) for p in probes]
    hit_rate = sum(1 for h in hits if h is not None) / len(probes)
    found = [h for h in hits if h is not None]
    t = time.perf_counter()
    passes = 0
    for _ in range(200):
        for c in found:
            passes += int(cheap_recheck(c))
    recheck_us = (time.perf_counter() - t) / (200 * max(1, len(found))) * 1e6
    recheck_pass_rate = (passes / (200 * len(found))) if found else 0.0
    return AmortReport(len(index), round(brew_ms, 1), round(recheck_us, 2), round(hit_rate, 3),
                       round(recheck_pass_rate, 3),
                       "[BLOCKED: ore_algebra — hypergeometric/D-finite search unavailable; C-finite+poly only]"
                       if not ore_algebra_available() else "available")
