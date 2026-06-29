"""
§AQ §4.STRIDE — compose the P-step transition into a single map and fold via the EXISTING matrix-power / per-residue
================================================================================================================
mechanism. A period-P FSM updates state by one of P fixed maps cycling on i mod P; the P-step composite is a single
transition M_P, and N iterations = M_P^(N/P) (matrix-power). Equivalently, the per-residue sub-oracle gᵣ(m)=f(P·m+r) is
each simple — exactly what §AL `control_flatten` disposes (z3-gated). ★ S-1: no new mechanism — this REUSES
control_flatten / matrix-power; §4 only contributes the period RECOGNITION.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class StrideFoldResult:
    folded: bool
    period: int = 0
    reduces_to: str = ""
    detail: str = ""


def fold_periodic(oracle: Callable[[int], object], period: int) -> StrideFoldResult:
    """Fold a period-P oracle by per-residue separation (REUSE §AL control_flatten = the matrix-power reduction)."""
    try:
        from recall.strip import control_flatten as CF
        r = CF.fold(oracle, moduli=(period,))
        return StrideFoldResult(r.folded, period, "matrix_power / control_flatten (per-residue, z3-gated)", r.detail)
    except Exception as e:  # noqa: BLE001
        return StrideFoldResult(False, period, "", f"control_flatten raised ({e}) ⇒ DECLINE")
