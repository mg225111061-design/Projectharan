"""
corpus/ai_todo_app.py — an AI-GENERATED-style task manager (representative archetype).
=======================================================================================
The kind of code an LLM emits when asked for a "todo app backend": correct, readable, and quietly O(n²) — it
finds tasks by linear scan and de-duplicates tags with list membership. Never profiled, so the asymptotic waste
survives. This is exactly where the engine finds a large whole-program win.

(Network is blocked in the sandbox, so this is an AUTHORED representative of the archetype, not a vendored
GitHub repo — tagged honestly in the corpus report.)
"""
from typing import Dict, List


def _rest(workload) -> int:                              # the unchanged, non-hot part of the program
    s = 0
    for t in workload["recent"]:
        s += len(t["title"])
    return s


# ── the hot path: find-by-id (linear scan) + tag dedup (list membership) — O(n²) ──────────────────────
def hot_original(tasks: List[Dict]) -> List:
    done = []
    for q in range(len(tasks)):                          # for each id, linear-scan to find it
        found = [t for t in tasks if t["id"] == q]
        if found:
            tags = []
            for tag in found[0]["tags"]:
                if tag not in tags:                      # list-as-set dedup
                    tags.append(tag)
            done.append((q, tuple(tags)))
    return done


def hot_optimized(tasks: List[Dict]) -> List:
    by_id = {t["id"]: t for t in tasks}                  # O(1) index
    done = []
    for q in range(len(tasks)):
        t = by_id.get(q)
        if t is not None:
            done.append((q, tuple(dict.fromkeys(t["tags"]))))   # order-preserving dedup
    return done


def hot_input(workload):
    return (workload["tasks"],)


def original(workload):
    return {"rest": _rest(workload), "done": hot_original(workload["tasks"])}


def optimized(workload):
    return {"rest": _rest(workload), "done": hot_optimized(workload["tasks"])}


def floor(workload):
    return {"rest": _rest(workload), "done": None}   # hot skipped — Amdahl timing floor (rest only)


def make_workload():
    tasks = [{"id": i, "title": f"task-{i}", "tags": [f"t{i % 5}", f"t{i % 7}", f"t{i % 5}"]}
             for i in range(900)]
    return {"tasks": tasks, "recent": tasks[:50]}


ARCHETYPE = "AI-generated (never profiled)"
EXACT_JUSTIFICATION = None          # order-preserving dedup + indexed lookup are equivalent, but graded by test
