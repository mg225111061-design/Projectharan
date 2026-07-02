"""
agenttools/catalog_accel.py — ACCEL-ELIGIBLE tools (10H directive Task 2): not fold, but a real proved-or-
declined safety check delegating to an EXISTING accel engine (RF-5: every entry names its `delegate`).
=================================================================================================================
  check_tasks_independent      -> accel.verified_parallel.verified_async_overlap  (I/O overlap safety)
  check_loop_parallel_safety   -> accel.verified_parallel.verified_data_parallel  (loop parallelization safety)

Both PROVE-or-DECLINE (never a guessed "looks parallel-safe") — a caller cannot get a false "safe to
parallelize" out of these; the underlying engine's own dependence/race analysis is what decides, this module
only translates JSON-shaped tool arguments into the engine's own dict/loop-spec inputs and returns its
verdict verbatim.
"""
from __future__ import annotations

import dataclasses
from typing import Dict, List

from agenttools.registry import ACCEL_ELIGIBLE, Tool, register


def check_tasks_independent(tasks: List[Dict]) -> Dict:
    """`tasks`: [{"name": str, "reads": [str,...], "writes": [str,...]}, ...] — proposes issuing them
    concurrently; PROVEN only if every pair is read/write-disjoint (no data dependence)."""
    from accel.verified_parallel import verified_async_overlap
    return dataclasses.asdict(verified_async_overlap(tasks))


def check_loop_parallel_safety(loop: Dict) -> Dict:
    """`loop`: {"carried": bool, "shared_writes": [str,...]?, "reduction": None} — proposes mapping loop
    iterations across cores; PROVEN only if no loop-carried dependence and no unreduced shared write."""
    from accel.verified_parallel import verified_data_parallel
    return dataclasses.asdict(verified_data_parallel(loop))


def _schema(props: Dict, required=None) -> Dict:
    return {"type": "object", "properties": props, "required": required or []}


register(Tool("check_tasks_independent",
              "Check whether a set of I/O tasks (each with declared reads/writes) can be safely issued "
              "concurrently — PROVEN only if every pair is read/write-disjoint, else DECLINED with the "
              "conflicting pair named.",
              _schema({"tasks": {"type": "array", "items": {"type": "object",
                      "properties": {"name": {"type": "string"},
                                    "reads": {"type": "array", "items": {"type": "string"}},
                                    "writes": {"type": "array", "items": {"type": "string"}}}}}},
                     ["tasks"]),
              check_tasks_independent, ACCEL_ELIGIBLE,
              delegate="accel.verified_parallel.verified_async_overlap",
              keywords=("parallel", "concurrent", "async", "overlap", "independent", "race")))
register(Tool("check_loop_parallel_safety",
              "Check whether a loop is safe to parallelize across cores — PROVEN only if there is no "
              "loop-carried dependence and no un-reduced shared write, else DECLINED with the reason.",
              _schema({"loop": {"type": "object",
                      "properties": {"carried": {"type": "boolean"},
                                    "shared_writes": {"type": "array", "items": {"type": "string"}}}}},
                     ["loop"]),
              check_loop_parallel_safety, ACCEL_ELIGIBLE,
              delegate="accel.verified_parallel.verified_data_parallel",
              keywords=("parallel", "loop", "vectorize", "multicore", "safety", "dependence")))
