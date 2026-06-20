"""
corpus/template_render.py — a WELL-WRITTEN small template renderer (representative archetype).
==============================================================================================
This one is already idiomatic: a single pass, dict lookups, ''.join. There is no asymptotic waste to find. It
exists to prove the engine reports an HONEST MISS (DECLINE-everywhere) instead of fabricating a win — the most
important kind of corpus row. Authored representative (network blocked).
"""
from typing import Dict, List


def _rest(workload) -> int:
    return len(workload["context"])


# ── hot path: already optimal (the "optimized" is identical — there is nothing to fix) ─────────────────
def hot_original(rows: List[Dict], ctx: Dict[str, str]) -> List[str]:
    out = []
    for r in rows:
        out.append("".join(ctx.get(tok, tok) for tok in r["tokens"]))   # single pass, dict lookups, join
    return out


hot_optimized = hot_original                             # nothing to improve → no change


def hot_input(workload):
    return (workload["rows"], workload["context"])


def original(workload):
    return {"rest": _rest(workload), "rendered": hot_original(workload["rows"], workload["context"])}


def optimized(workload):
    return {"rest": _rest(workload), "rendered": hot_optimized(workload["rows"], workload["context"])}


def floor(workload):
    return {"rest": _rest(workload), "rendered": None}


def make_workload():
    ctx = {f"k{i}": f"v{i}" for i in range(50)}
    rows = [{"tokens": [f"k{i % 50}", "x", f"k{(i + 3) % 50}"]} for i in range(4000)]
    return {"rows": rows, "context": ctx}


ARCHETYPE = "parser/renderer (well-written)"
EXACT_JUSTIFICATION = None
