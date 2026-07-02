"""
§AP §4.1 — SUMMARIZE each handler's effect as an affine state map (REUSE the §AI §2 / §P P6 extractor).
================================================================================================================
The per-function summary is the affine pair (a, b) for the single-state update s ← a·s + b. This is exactly what
`catalog.distributed_state._extract_affine` already computes (it takes the FIRST parameter as the shared state and
DECLINEs any non-affine update). summarize is the introspection front-door: it reports each handler's summary (or None
when the handler is not an affine single-state update), so the caller can see WHY a gather will or won't compose.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple


def summarize_one(src: str) -> Optional[Tuple[int, int]]:
    """The affine summary (a, b) of one handler, or None if it is not an affine single-state update."""
    try:
        from catalog import distributed_state as DS
        r = DS._extract_affine(src)
        if r is None:
            return None
        a, b, _sv = r
        return int(a), int(b)
    except Exception:  # noqa: BLE001
        return None


def summarize(handlers: Dict[str, str]) -> Dict[str, Optional[Tuple[int, int]]]:
    return {name: summarize_one(src) for name, src in handlers.items()}
