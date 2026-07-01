"""
HARAN §4 — TIER ROUTING for the 50 algorithms: fast (~1s) / normal (~30s) / extend (~8min BOUNDED) + broth.
==========================================================================================================
The operational glue that puts §1 (the 50 named algorithms, each tagged with the tier its certified path runs
under) together with §2 (the broth) and the fast/normal/extend CONTRACT in `pillar3/mode.py`. The routing rules,
enforced here and tested per-commit:
  • A BROTH HIT short-circuits in ANY mode — the result was pre-proven offline, so it returns INSTANTLY (O(1)
    lookup) EVEN in fast, regardless of how heavy the underlying algorithm is. (The UI shows "사전증명된 닫힌형 0.1µs".)
  • On a MISS, the algorithm runs ONLY if its tier ≤ the requested mode. fast (~1s) NEVER runs an extend-tier
    heavy decision procedure (CAD/Risch/Gröbner/Kovacic/Petkovšek/ΠΣ*/factorization/Lucas–Lehmer/BSGS) — it
    returns TIER_UP, telling the caller to escalate. normal runs fast+normal; extend runs everything within its
    BOUNDED 8-minute budget.
This is the contract from `ModePolicy`: fast=MICRO (never the heavy solver), extend=FULL_CERT EXACT-or-DECLINE,
all time-bounded. The router decides ROUTING ONLY — it never weakens a grade and never runs past a budget.
"""
from __future__ import annotations

from typing import Optional, Tuple

import algo50 as A
import haran_broth as HB
import kernel_verdict as KV

_RANK = {"fast": 0, "normal": 1, "extend": 2}


def _mode_rank(mode: str) -> int:
    if mode not in _RANK:
        raise ValueError(f"unknown mode {mode!r}")
    return _RANK[mode]


def can_run(algo_num: int, mode: str) -> bool:
    """Can algorithm `algo_num` run a full certified pass in `mode`? True iff its tier ≤ the mode (fast never
    hosts an extend-tier heavy solver)."""
    return _RANK[A.BY_NUM[algo_num].tier] <= _mode_rank(mode)


def route(algo_num: int, mode: str, broth_key: Optional[Tuple] = None) -> dict:
    """Route a request for algorithm `algo_num` under `mode`, optionally with a broth key.
    Returns one of:
      • {action: "BROTH_HIT", ...}  — pre-proven; instant O(1) result, valid in ANY mode (even fast)
      • {action: "RUN", ...}        — a MISS, but the algorithm's tier ≤ mode ⇒ run it in this tier
      • {action: "TIER_UP", ...}    — a MISS and the algorithm is heavier than the mode ⇒ escalate (fast won't
                                       call the heavy solver). The required tier is named."""
    algo = A.BY_NUM[algo_num]
    if broth_key is not None:
        entry = HB.lookup(broth_key)
        if entry is not None:                                # pre-proven offline ⇒ instant, regardless of tier
            # §BS-1 audit fix (A1 emission bypass): route through the ADT instead of a hand-written
            # {"grade": "EXACT"} literal. `passed=True` is justified by test_build.py's gate-enforced
            # HB.reverify() sample-audit (every commit re-runs the real algorithm on a sample of broth
            # entries, including a tampered-entry negative control) — not re-derived here per-request,
            # which would defeat the whole point of an O(1) lookup.
            return KV.to_api(KV.EXACT, entry.value, f"broth#{algo_num}", "O(1)",
                             cert=KV.Cert(KV.EXACT, "broth_precomputed_reverifiable", passed=True,
                                          check_cost="O(1) lookup; re-execution audited per-commit "
                                                     "(test_build.py, not per-lookup)", detail=entry.cert),
                             action="BROTH_HIT", algo=algo_num, mode=mode, value=entry.value,
                             ui="broth 적중 — 사전증명된 닫힌형 (0.1µs)")
    if can_run(algo_num, mode):
        return {"action": "RUN", "algo": algo_num, "mode": mode, "tier": algo.tier,
                "ui": f"fold 적용 중: #{algo_num} {algo.name} ({algo.tier})", "grade": algo.grade}
    return {"action": "TIER_UP", "algo": algo_num, "mode": mode, "required_tier": algo.tier,
            "ui": f"#{algo_num} {algo.name}: {mode} 예산 초과 — {algo.tier} 필요 (heavy solver, fast 금지)"}


def routing_matrix() -> dict:
    """The full {algo × mode} routing decision (miss case), for the per-commit invariant test. Asserts the
    fast-never-heavy-solver contract holds for every one of the 50."""
    rows = {}
    for a in A.ALGOS:
        rows[a.num] = {m: route(a.num, m)["action"] for m in ("fast", "normal", "extend")}
    fast_heavy = [a.num for a in A.ALGOS if a.tier == "extend" and rows[a.num]["fast"] != "TIER_UP"]
    extend_runs_all = all(rows[a.num]["extend"] == "RUN" for a in A.ALGOS)
    return {"rows": rows, "fast_hosts_no_heavy_solver": not fast_heavy,
            "fast_tier_up_count": sum(1 for a in A.ALGOS if rows[a.num]["fast"] == "TIER_UP"),
            "extend_runs_all": extend_runs_all}
