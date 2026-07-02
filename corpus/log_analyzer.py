"""
corpus/log_analyzer.py — a small CLI log-analysis tool (representative archetype).
==================================================================================
Counts error codes across log lines. The hot loop re-parses the (constant) severity config on every line — a
classic redundant-parse waste. Authored representative of the archetype (network blocked).
"""
import json
from typing import Dict, List


_CONFIG = '{"levels": {"ERROR": 3, "WARN": 2, "INFO": 1}, "threshold": 2}'


def _rest(workload) -> int:
    return sum(1 for ln in workload["sample"] if ln)


# ── hot path: re-parse the constant config every iteration ─────────────────────────────────────────────
def hot_original(lines: List[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for ln in lines:
        cfg = json.loads(_CONFIG)                        # loop-invariant parse, every line
        level = ln.split(":", 1)[0]
        if cfg["levels"].get(level, 0) >= cfg["threshold"]:
            counts[level] = counts.get(level, 0) + 1
    return counts


def hot_optimized(lines: List[str]) -> Dict[str, int]:
    cfg = json.loads(_CONFIG)                            # parse once, hoisted
    counts: Dict[str, int] = {}
    for ln in lines:
        level = ln.split(":", 1)[0]
        if cfg["levels"].get(level, 0) >= cfg["threshold"]:
            counts[level] = counts.get(level, 0) + 1
    return counts


def hot_input(workload):
    return (workload["lines"],)


def original(workload):
    return {"rest": _rest(workload), "counts": hot_original(workload["lines"])}


def optimized(workload):
    return {"rest": _rest(workload), "counts": hot_optimized(workload["lines"])}


def floor(workload):
    return {"rest": _rest(workload), "counts": None}


def make_workload():
    levels = ["ERROR", "WARN", "INFO", "DEBUG"]
    lines = [f"{levels[i % 4]}: event {i}" for i in range(6000)]
    return {"lines": lines, "sample": lines[:100]}


ARCHETYPE = "CLI tool"
EXACT_JUSTIFICATION = None
