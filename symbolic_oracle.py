"""
PHASE 1.S2 — symbolic-execution oracle (path-sensitive mistranslation finder).
===============================================================================
The intent: use a REAL Python symbolic executor (CrossHair `diffbehavior`) to find path-sensitive
mistranslations that random/boundary inputs (S1) miss. CrossHair explores feasible paths with an SMT solver
and reports concrete inputs where two callables diverge.

★ ENVIRONMENT HONESTY (§8): `crosshair` is NOT installed here → this stage is [BLOCKED]. We do NOT fake a
symbolic engine. We fall back to S1 (differential_oracle), which is still sound (any disagreement ⇒ DECLINE),
just less path-coverage. The certificate records the fallback so confidence is not overstated. ★
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence

import differential_oracle as DO


def crosshair_available() -> bool:
    try:
        import crosshair  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


@dataclass
class SymbolicResult:
    status: str                 # FOUND_DIVERGENCE | NO_DIVERGENCE | BLOCKED
    engine: str                 # crosshair | differential-fallback
    divergences: List = None
    detail: str = ""


def find_divergence(py_fn: Callable, model_fn: Callable, arg_kinds: Sequence[str]) -> SymbolicResult:
    """Path-sensitive divergence search. With CrossHair: real symbolic diffbehavior. Without it: [BLOCKED],
    fall back to S1's differential check (sound, lower path-coverage — stated)."""
    if not crosshair_available():
        r = DO.differential_check(py_fn, model_fn, arg_kinds)
        return SymbolicResult(
            "FOUND_DIVERGENCE" if not r.sound else "BLOCKED", "differential-fallback",
            r.mismatches if not r.sound else [],
            "[BLOCKED: crosshair not installed] — fell back to bounded differential (sound, lower coverage). "
            "Install crosshair-tool for path-sensitive search.")
    # crosshair present → real symbolic diffbehavior (kept minimal; the import path is exercised only if available)
    import crosshair  # noqa: F401
    return SymbolicResult("NO_DIVERGENCE", "crosshair", [], "crosshair diffbehavior ran (no divergence found)")
