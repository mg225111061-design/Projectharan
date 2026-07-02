"""
ACCEL §1 — the PROPOSE → PROFILE → VERIFY → APPLY → MEASURE pipeline (the central propose–verify–apply invariant).
================================================================================================================
A single orchestrator applied to A/B/C/D in turn. For any target:
  1. PROFILE FIRST (Amdahl gate) — measure where wall-clock actually goes; rank hot paths by share; NO acceleration
     is attempted off a measured hot path (kills the "optimize the 5% compute" trap at the root).
  2. PROPOSE — a specific acceleration from A/B/C/D.
  3. VERIFY — z3 / an in-repo exact oracle PROVES the fast version is semantics-equivalent (or refines) the original.
  4. APPLY — only PROVED accelerations are applied; the applied version carries its certificate.
  5. MEASURE — re-profile; report the WHOLE-PROGRAM wall-clock speedup (NOT the component factor) + Clock A/B/C.

★ THE CENTRAL INVARIANT: an `Acceleration` is APPLIED iff `proved` is True. A proposal is WORTHLESS until the oracle
proves it. `precision()` over a battery = (applied ∩ unsafe) must be ∅ — zero unsafe accelerations applied, ever.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


# ── the result of one propose→verify→apply step ─────────────────────────────────────────────────────────
@dataclass
class Acceleration:
    technique: str                 # A.cache | A.batch | A.dedup | B.async | B.parallel | C.algo | C.cse | D.serde | …
    proposed: str                  # the LLM/detector's proposal (untrusted until proved)
    proved: bool                   # did the exact oracle PROVE it semantics-preserving?
    certificate: Optional[str]     # the proof witness (z3 UNSAT / exact-equivalence / effect-set), or None
    reason: str = ""               # why it was rejected (when not proved)
    clock_a_ms: float = 0.0        # proposal latency
    clock_b_ms: float = 0.0        # verification time
    clock_c_speedup: Optional[float] = None   # measured runtime speedup of the applied version (None if not measured)
    asymptotics: str = "unchanged"

    @property
    def applied(self) -> bool:
        """★ Applied IFF proved. No proof → the slow original stands. This is the whole safety guarantee."""
        return self.proved

    def __str__(self):
        if self.applied:
            return f"APPLIED[{self.technique}] {self.proposed} — proof: {self.certificate}"
        return f"REJECTED[{self.technique}] {self.proposed} — {self.reason}"


def proved(technique: str, proposed: str, certificate: str, **kw) -> Acceleration:
    return Acceleration(technique, proposed, True, certificate, **kw)


def rejected(technique: str, proposed: str, reason: str, **kw) -> Acceleration:
    return Acceleration(technique, proposed, False, None, reason=reason, **kw)


# ── PROFILE FIRST: the Amdahl gate ──────────────────────────────────────────────────────────────────────
@dataclass
class HotPath:
    name: str
    wall_share: float              # measured fraction of total wall-clock
    category: str                  # io | serialization | data_structure | control_flow | allocation | computation


def profile(components: List[tuple], k: int = 5) -> List[HotPath]:
    """Measure where wall-clock goes. `components` = [(name, category, callable), …]. Returns hot paths ranked by
    MEASURED wall-clock share. The Amdahl gate consumes this: only the top shares are attacked. (Clock-agnostic
    wall-clock here — the profiler measures the WHOLE program's time distribution, not a single clock.)"""
    timings = []
    for (name, category, fn) in components:
        best = float("inf")
        for _ in range(max(1, k)):
            t0 = time.perf_counter()
            fn()
            dt = time.perf_counter() - t0
            best = min(best, dt)
        timings.append((name, category, best))
    total = sum(t for _, _, t in timings) or 1.0
    paths = [HotPath(n, round(t / total, 4), c) for (n, c, t) in timings]
    return sorted(paths, key=lambda p: -p.wall_share)


def amdahl_whole_program(component_share: float, component_speedup: float) -> float:
    """The whole-program speedup when a component of `component_share` of wall-clock is sped up by
    `component_speedup`× (Amdahl). A component factor is NEVER reported as a whole-program factor — this converts one
    to the other honestly. Speeding 5% by 10× ⇒ ~1.047× whole-program, not 10×."""
    if component_speedup <= 0:
        return 1.0
    return round(1.0 / ((1.0 - component_share) + component_share / component_speedup), 4)


# ── precision: the safety proof over a battery ──────────────────────────────────────────────────────────
def precision(results: List[tuple]) -> dict:
    """`results` = [(acceleration, is_actually_safe), …]. ★ Precision = 1.0 iff NO unsafe acceleration was applied.
    (Recall — proved-safe ones that got applied — is reported too, but the binding gate is zero unsafe applies.)"""
    unsafe_applied = [a for (a, safe) in results if a.applied and not safe]
    safe_total = [a for (a, safe) in results if safe]
    safe_applied = [a for (a, safe) in results if a.applied and safe]
    return {
        "total": len(results),
        "applied": sum(1 for (a, _) in results if a.applied),
        "unsafe_applied": [a.proposed for a in unsafe_applied],
        "precision": 1.0 if not unsafe_applied else 0.0,
        "precision_is_one": not unsafe_applied,
        "recall_on_safe": round(len(safe_applied) / len(safe_total), 3) if safe_total else 1.0,
    }


# ── the orchestrated step: propose → verify → (apply) → measure ─────────────────────────────────────────
def run_step(technique: str, propose: Callable[[], str], verify: Callable[[], Acceleration],
             measure: Optional[Callable[[], float]] = None) -> Acceleration:
    """One pipeline step. `propose` returns the proposal string (Clock A); `verify` returns an Acceleration whose
    `proved` flag is set by the exact oracle (Clock B); on proof, `measure` (if given) returns the runtime speedup
    (Clock C). Nothing is applied without a passing proof — the central invariant, enforced here."""
    t0 = time.perf_counter()
    _ = propose()
    a_ms = (time.perf_counter() - t0) * 1000
    t1 = time.perf_counter()
    acc = verify()
    acc.clock_a_ms = round(a_ms, 4)
    acc.clock_b_ms = round((time.perf_counter() - t1) * 1000, 4)
    acc.technique = technique
    if acc.applied and measure is not None:
        acc.clock_c_speedup = measure()
    return acc
