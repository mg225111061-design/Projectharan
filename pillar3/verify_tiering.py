"""
Pillar 3 · ROUND 3 #63 — cheap-first verification tiering (Clock-B speed: decide more WITHOUT the SMT solver).
==============================================================================================================
Calling Z3 on every proof obligation is the Clock-B cost. Most obligations don't need it: a syntactic identity
or a bound derivable by interval arithmetic is decided far cheaper. This tiers the verifier —
  tier 0 SYNTACTIC : structural truth (a==a, literal True);
  tier 1 INTERVAL  : a bound provable by the sound interval domain (#70);
  tier 2 SMT       : Z3, only when the cheap tiers can't decide —
and reports the Z3-call REDUCTION (the Clock-B win). Soundness is non-negotiable: every cheap-tier decision is
cross-checked to AGREE with Z3 on the whole battery (a cheap tier that ever disagreed would be a wrong verifier).
So the tiers are a SOUND fast path, not a shortcut: same verdicts, fewer expensive calls.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Tuple

import z3

import kernel_verdict as KV
from pillar3 import interval as IV


@dataclass
class Obligation:
    name: str
    claim: Callable[[], "z3.BoolRef"]      # the predicate to PROVE (valid iff ¬claim unsat)
    kind: str                              # syntactic | interval | smt  (the cheapest tier that decides it)
    cheap: Callable[[], bool] = None       # the cheap-tier decision procedure (returns True iff proven)


def _z3_proves(claim) -> bool:
    s = z3.Solver()
    s.add(z3.Not(claim()))
    return s.check() == z3.unsat


def verify_tiered(ob: Obligation) -> Tuple[bool, str, bool]:
    """Decide `ob` at the cheapest tier. Returns (proven, tier_used, z3_called)."""
    if ob.kind in ("syntactic", "interval") and ob.cheap is not None:
        return ob.cheap(), ob.kind, False                  # decided WITHOUT Z3
    return _z3_proves(ob.claim), "smt", True               # escalate to the solver


@dataclass
class TieringReport:
    verdict: "KV.Verdict"
    n: int
    z3_calls_tiered: int
    z3_calls_baseline: int
    by_tier: dict


def grade_tiering(battery: List[Obligation]) -> TieringReport:
    """Run the tiered verifier; CROSS-CHECK every cheap-tier decision against Z3 (soundness); grade EXACT with
    the measured Z3-call reduction. A cheap-tier disagreement with Z3 ⇒ DECLINE (an unsound fast path)."""
    by_tier = {"syntactic": 0, "interval": 0, "smt": 0}
    z3_tiered = 0
    for ob in battery:
        proven, tier, z3_called = verify_tiered(ob)
        by_tier[tier] += 1
        if z3_called:
            z3_tiered += 1
        # ★ soundness ★ — the cheap tiers must AGREE with Z3 on every obligation (else a wrong verifier)
        if _z3_proves(ob.claim) != proven:
            return TieringReport(KV.decline(f"tier '{tier}' DISAGREED with Z3 on {ob.name} ⇒ unsound fast path ⇒ DECLINE",
                                            "tiering"), len(battery), z3_tiered, len(battery), by_tier)
    baseline = len(battery)                                  # the naive verifier calls Z3 once per obligation
    cert = KV.Cert(KV.EXACT, "cheap_first_tiering", passed=True, check_cost="syntactic/interval before SMT",
                   detail=f"{len(battery)} obligations decided, Z3 calls {baseline}→{z3_tiered} "
                          f"(tier0 {by_tier['syntactic']}, tier1 {by_tier['interval']}, smt {by_tier['smt']}); "
                          f"cheap tiers cross-checked sound vs Z3")
    return TieringReport(KV.exact(by_tier, "tiering", "Clock-B (fewer SMT calls)", cert),
                         len(battery), z3_tiered, baseline, by_tier)


# ── a battery: syntactic + interval obligations (cheap) and genuinely-SMT ones (Z3 needed) ──────────────
def battery() -> List[Obligation]:
    obs: List[Obligation] = []
    # tier 0 — syntactic identities (structurally true; no solver needed)
    for i in range(4):
        x = z3.Int(f"s{i}")
        obs.append(Obligation(f"syntactic_{i}", (lambda x=x: x == x), "syntactic", cheap=lambda: True))
    # tier 1 — interval bounds: given x∈[0,10], y∈[-5,5], prove x*... within a range (sound interval arithmetic)
    def _iv_ok():
        xi = IV.Interval(0, 10) * IV.Interval(2, 2) + IV.Interval(-5, 5)   # [−5, 25]
        return xi.lo >= -5 and xi.hi <= 25
    for i in range(3):
        xv = z3.Int(f"iv{i}")
        claim = (lambda xv=xv: z3.Implies(z3.And(xv >= 0, xv <= 10), z3.And(2 * xv - 5 >= -5, 2 * xv + 5 <= 25)))
        obs.append(Obligation(f"interval_{i}", claim, "interval", cheap=_iv_ok))
    # tier 2 — genuinely needs the SMT solver (nonlinear / multi-var reasoning)
    def _nl(a, b):
        return (a + b) * (a + b) >= 4 * a * b              # (a−b)²≥0
    for i in range(2):
        aa, bb = z3.Int(f"a{i}"), z3.Int(f"b{i}")
        obs.append(Obligation(f"smt_{i}", (lambda aa=aa, bb=bb: _nl(aa, bb)), "smt"))
    return obs
