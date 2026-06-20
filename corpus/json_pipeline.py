"""
corpus/json_pipeline.py — an ETL-ish pipeline (representative archetype).
=========================================================================
Enriches records by fetching a reference value per item (an N+1 access pattern) instead of one batched lookup.
Authored representative (network blocked).
"""
from typing import Dict, List

_REF = {i: i * 10 for i in range(5000)}


def _rest(workload) -> int:
    return len(workload["ids"])


def _fetch_ref(i: int) -> int:
    s = 0
    for _ in range(60):                                  # simulate per-fetch fixed overhead
        s += _REF[i]
    return _REF[i]


# ── hot path: per-item fetch (N+1) ────────────────────────────────────────────────────────────────────
def hot_original(ids: List[int]) -> List[int]:
    return [_fetch_ref(i) for i in ids]                  # get_* per item


def hot_optimized(ids: List[int]) -> List[int]:
    return [_REF[i] for i in ids]                        # one coalesced access


def hot_input(workload):
    return (workload["ids"],)


def original(workload):
    return {"rest": _rest(workload), "enriched": hot_original(workload["ids"])}


def optimized(workload):
    return {"rest": _rest(workload), "enriched": hot_optimized(workload["ids"])}


def floor(workload):
    return {"rest": _rest(workload), "enriched": None}


def make_workload():
    return {"ids": list(range(2200))}


ARCHETYPE = "ETL pipeline"
EXACT_JUSTIFICATION = "coalesced_identical_lookups"      # batched access returns the same reference values
