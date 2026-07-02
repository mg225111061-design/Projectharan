"""
corpus/csv_stats.py — a data-utility that aggregates rows (representative archetype).
=====================================================================================
Builds a running result list by concatenation (`acc = acc + [row]`) — a genuinely O(n²) accumulation CPython
does not optimise. Authored representative (network blocked).
"""
from typing import Dict, List


def _rest(workload) -> float:
    return sum(workload["weights"]) / max(len(workload["weights"]), 1)


# ── hot path: accidental quadratic list build ─────────────────────────────────────────────────────────
def hot_original(rows: List[int]) -> List[int]:
    acc: List[int] = []
    for r in rows:
        acc = acc + [r * r]                              # O(n) copy each step → O(n²)
    return acc


def hot_optimized(rows: List[int]) -> List[int]:
    out: List[int] = []
    for r in rows:
        out.append(r * r)                                # O(1) amortised append
    return out


def hot_input(workload):
    return (workload["rows"],)


def original(workload):
    return {"rest": _rest(workload), "sq": hot_original(workload["rows"])}


def optimized(workload):
    return {"rest": _rest(workload), "sq": hot_optimized(workload["rows"])}


def floor(workload):
    return {"rest": _rest(workload), "sq": None}


def make_workload():
    return {"rows": list(range(3500)), "weights": [1.0, 2.0, 3.0, 4.0]}


ARCHETYPE = "data utility"
EXACT_JUSTIFICATION = None
