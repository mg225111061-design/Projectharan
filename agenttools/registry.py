"""
agenttools/registry.py — the tool CATALOG: name / description / JSON schema / impl / RF-5 tier tag.
=====================================================================================================
A `Tool` is the Anthropic-native tool-use shape (`name`, `description`, `input_schema`) — the SAME shape
`search_gate.py::_SEARCH_TOOL` already uses — plus the actual Python callable (`fn`) and an RF-5 `tier`.
`to_wire_shape()` in router.py adapts this canonical shape to whatever the transport needs (Anthropic
native passthrough, or OpenAI's `{type:"function",function:{...}}` wrapper).

The registry itself is a plain in-process dict, populated by catalog_*.py modules at import time (Task
2). This module only owns the CONTRACT (what a Tool is, that its tier is always one of the 3) — it knows
nothing about which specific tools exist.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

# RF-5: every tool gets EXACTLY one of these three tags — never a fold/EXACT label on a plain tool.
FOLD_ELIGIBLE = "FOLD-ELIGIBLE"     # genuine numeric/structural core — delegates to an existing fold engine
ACCEL_ELIGIBLE = "ACCEL-ELIGIBLE"   # not fold, but legitimately fast via caching/parallelization (accel/)
PLAIN = "PLAIN"                     # I/O-bound (file/git/subprocess/grep-class) — not an acceleration target
TIERS = (FOLD_ELIGIBLE, ACCEL_ELIGIBLE, PLAIN)


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict                       # {"type":"object","properties":{...},"required":[...]}
    fn: Callable[..., object]                 # kwargs in → result. No JSON-schema validator is run (zero-dep: no
                                               # jsonschema pkg); a shape mismatch surfaces as Python's own
                                               # call-time TypeError, which executor.execute() catches honestly.
    tier: str                                 # one of TIERS (RF-5)
    delegate: str = ""                        # for FOLD/ACCEL: the real engine this delegates to (honesty trail)
    keywords: Tuple[str, ...] = ()            # router hint words — Stage-1 local match (mirrors intent.py)

    def __post_init__(self) -> None:
        if self.tier not in TIERS:
            raise ValueError(f"tool {self.name!r}: tier must be one of {TIERS}, got {self.tier!r}")
        if self.tier in (FOLD_ELIGIBLE, ACCEL_ELIGIBLE) and not self.delegate:
            raise ValueError(f"tool {self.name!r}: tier={self.tier} requires `delegate` naming the real "
                             "engine it calls (RF-5 honesty trail — never a bare fold/accel claim)")


_REGISTRY: Dict[str, Tool] = {}


def register(tool: Tool) -> Tool:
    """Add (or replace) a tool in the process-wide catalog. Returns the tool so call sites can write
    `FOO = register(Tool(...))` and keep a local reference too."""
    _REGISTRY[tool.name] = tool
    return tool


def unregister(name: str) -> None:
    """Remove a tool from the process-wide catalog, if present (no error if absent). For TEMPORARY
    registrations only (e.g. a self-test's own probe tool that must be executable-via-the-real-executor
    for the duration of the check, but must not permanently inflate the live catalog's measured count)."""
    _REGISTRY.pop(name, None)


def all_tools() -> List[Tool]:
    return list(_REGISTRY.values())


def get(name: str) -> Optional[Tool]:
    return _REGISTRY.get(name)


def counts_by_tier(tools: Optional[List[Tool]] = None) -> Dict[str, int]:
    """Tier histogram over `tools` (default: the whole live registry). Accepting an explicit list (same
    override pattern as `router.select_tools`'s `catalog` param) keeps this testable against a small
    fixture without mutating or depending on global registry state."""
    pool = tools if tools is not None else all_tools()
    out = {t: 0 for t in TIERS}
    for tool in pool:
        out[tool.tier] += 1
    return out


def total_count() -> int:
    return len(_REGISTRY)
