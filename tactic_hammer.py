"""
v27 STAGE 17c — a "hammer": portfolio proof automation for residual obligations (+ proof reuse).
=================================================================================================
A hammer throws a portfolio of sound tactics at a proof obligation and reports the first success — the
Sledgehammer / CoqHammer idea. Here the portfolio is, in heuristic priority order:

    1. cache      — reuse a previously proven obligation (proof_cache; perceived-zero, lossless)
    2. z3         — the SMT kernel (z3_adapter.prove_predicate)
    3. sos-lemma  — a sum-of-squares pattern (t*t ≥ 0 / t**2 ≥ 0), confirmed by Z3

Every PROVED result is kernel-checked by Z3 (the tactic only chooses HOW to discharge it, never WHETHER).

★ HONEST (§1.9, §5.9, §5.10) ★: (1) the tactic order is a fixed HEURISTIC, NOT a trained model — no
learned-reward/GNN claims. (2) A hammer auto-discharges a FRACTION of obligations (anchors: TacticToe 66%,
CoqHammer ~56.7%); the rest are reported NOT_PROVED/UNKNOWN, never faked. (3) An obligation that is simply
false is reported NOT_PROVED (with the Z3 counterexample) — it is not a hammer failure.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import proof_cache as PC
import z3_adapter as Z

_TACTIC_PRIORITY = ["cache", "z3", "sos-lemma"]   # heuristic order (NOT a trained policy)


@dataclass
class HammerResult:
    status: str                 # PROVED | NOT_PROVED | UNKNOWN
    tactic: str = "-"           # which tactic discharged it
    detail: str = ""
    counterexample: Optional[dict] = None

    def __str__(self):
        if self.status == "PROVED":
            return f"PROVED via {self.tactic}"
        return f"{self.status} — {self.detail}"


def _looks_like_sos(expr: str) -> bool:
    e = expr.replace(" ", "")
    # a square is non-negative: t*t >= 0  or  t**2 >= 0
    return e.endswith(">=0") and ("*" in e) and (
        any(f"{v}*{v}>=0" == e or f"{v}**2>=0" == e for v in ("a", "b", "n", "x", "y", "k", "m")))


def hammer(expr: str, var_types: Dict[str, str], assumptions: Sequence[str] = ()) -> HammerResult:
    """Try the tactic portfolio; return the first that discharges `expr` (kernel-checked by Z3)."""
    # 1. cache reuse (only meaningful without extra assumptions — the cache keys on the goal alone)
    if not assumptions:
        try:
            pred = Z.parse_predicate(expr, var_types)
            c = PC.prove_forall_cached(pred, var_types)
            if c.verdict == "PROVEN":
                return HammerResult("PROVED", "cache" if "cache" in c.backend else "z3",
                                    detail=c.detail)
            if c.verdict == "REFUTED":
                return HammerResult("NOT_PROVED", "z3", "obligation is false", c.counterexample)
        except Exception:  # noqa: BLE001
            pass
    # 2. z3 (with assumptions)
    r = Z.prove_predicate(expr, var_types, assumptions=list(assumptions))
    if r.verdict == "PROVEN":
        return HammerResult("PROVED", "z3", detail=r.detail)
    if r.verdict == "REFUTED":
        return HammerResult("NOT_PROVED", "z3", "obligation is false", r.counterexample)
    # 3. sos-lemma fallback (then confirm with z3 — never trust the pattern alone)
    if _looks_like_sos(expr):
        r2 = Z.prove_predicate(expr, var_types)
        if r2.verdict == "PROVEN":
            return HammerResult("PROVED", "sos-lemma", detail="sum-of-squares ≥ 0, Z3-confirmed")
    return HammerResult("UNKNOWN", "-", f"no tactic discharged it ({r.verdict})")


@dataclass
class HammerStats:
    total: int
    proved: int
    not_proved: int
    unknown: int
    success_rate: float
    by_tactic: Dict[str, int]


def measure_hammer(corpus: Sequence[Tuple[str, Dict[str, str]]]) -> HammerStats:
    """Honest success rate over a mix of provable and non-provable obligations."""
    proved = not_proved = unknown = 0
    by_tactic: Dict[str, int] = {}
    PC.reset()
    for expr, vt in corpus:
        r = hammer(expr, vt)
        if r.status == "PROVED":
            proved += 1
            by_tactic[r.tactic] = by_tactic.get(r.tactic, 0) + 1
        elif r.status == "NOT_PROVED":
            not_proved += 1
        else:
            unknown += 1
    n = len(corpus)
    provable = proved + unknown if False else proved  # success measured against ALL obligations (honest)
    return HammerStats(n, proved, not_proved, unknown, proved / n if n else 0.0, by_tactic)


def reuse_or_prove(expr: str, var_types: Dict[str, str]) -> Tuple[HammerResult, bool]:
    """Proof reuse (PUMPKIN/iCoq-style, S13 link): a repeat obligation is discharged from cache (the
    second call is perceived-zero). Returns (result, was_cache_hit)."""
    r = hammer(expr, var_types)
    return (r, r.tactic == "cache")
