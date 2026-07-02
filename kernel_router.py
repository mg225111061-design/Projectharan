"""
v40 PHASE 1A — the ROUTER / dispatcher (the entrance to every collapse kernel).
================================================================================
A cheap (µs) classification of the input picks the right kernel; if none applies (or all DECLINE), the router
falls back honestly (DECLINE). Each kernel carries a HARAN CONTRACT (requires/ensures + grade) — Constitution
§4 (HARAN-first): the applicability + grade rules live in the contract, the dispatch is thin Python glue, and
the grade is ENFORCED by the Verdict ADT (kernel_verdict). UNVERIFIED kernels are never auto-selected (§4.5).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import kernel_verdict as KV


@dataclass
class Kernel:
    num: int                                  # router reference number (Appendix A)
    name: str
    group: str                                # A..H (Appendix A)
    contract: str                             # HARAN contract: requires … ensures … grade …
    detect: Callable[[Any], bool]             # cheap applicability test (µs)
    run: Callable[..., KV.Verdict]            # returns a graded Verdict
    status: str = "VERIFIED"                  # VERIFIED | UNVERIFIED (excluded from auto-select)


REGISTRY: Dict[str, Kernel] = {}
_LAST_US: float = 0.0


def register(k: Kernel) -> Kernel:
    REGISTRY[k.name] = k
    return k


def registered(verified_only: bool = True) -> List[str]:
    return [n for n, k in REGISTRY.items() if (not verified_only or k.status == "VERIFIED")]


def dispatch(data: Any, **kw) -> KV.Verdict:
    """Classify `data` and run the first applicable VERIFIED kernel whose verdict is non-DECLINE; else DECLINE.
    Records the router decision latency (µs) on the verdict (router_us)."""
    global _LAST_US
    t0 = time.perf_counter()
    tried: List[str] = []
    for k in REGISTRY.values():
        if k.status != "VERIFIED":
            continue
        try:
            applicable = k.detect(data)
        except Exception:  # noqa: BLE001 — a detector must never crash the router
            applicable = False
        if not applicable:
            continue
        tried.append(k.name)
        v = k.run(data, **kw)
        if v.status != KV.DECLINE:
            _LAST_US = (time.perf_counter() - t0) * 1e6
            return v
    _LAST_US = (time.perf_counter() - t0) * 1e6
    return KV.decline(f"no kernel applicable (tried {tried or 'none'}) — fallback to existing path", "router")


def last_decision_us() -> float:
    return _LAST_US


# ── dogfood: the contracts are well-formed HARAN-style (requires/ensures/grade) and grades are declared ──
def verify_contracts() -> dict:
    """Constitution §0.1/§4: every registered kernel must carry a contract that names requires, ensures, and a
    grade ∈ {EXACT, PROBABILISTIC, DECLINE}. A malformed contract is a build failure, not a warning."""
    bad = []
    for n, k in REGISTRY.items():
        c = k.contract
        ok = ("requires" in c and "ensures" in c
              and any(g in c for g in (KV.EXACT, KV.PROBABILISTIC, KV.DECLINE)))
        if not ok:
            bad.append(n)
    return {"n_kernels": len(REGISTRY), "verified": len(registered()),
            "unverified": [n for n, k in REGISTRY.items() if k.status != "VERIFIED"],
            "malformed_contracts": bad, "all_well_formed": not bad}
