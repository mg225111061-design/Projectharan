"""
§AP §1.3 — RECOMBINE and re-verify (the soundness seal of the compositional fold).
================================================================================================================
The composite folds iff (1) EVERY atom folded in its own lens (§1.2, each z3-gated) AND (2) the recombination operator
is the claimed one — verified on a MULTI-SCALE held-out that straddles carry boundaries (n≈100/1000/10000, REUSE the
§AL depth scales). The held-out catches a wrong combine op (claim `add` but the code multiplies ⇒ reconstruct ≠ f at a
straddle scale ⇒ DECLINE). ★ S-2: observation is not proof — but each atom is already z3-proven and the only residual
claim (the operator) is checked across multiple structural scales, so a wrong recombination is refuted, not accepted.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from recall.compose import atomize as AT

_SCALES = (100, 1000, 10000)             # carry-straddle held-out scales (REUSE recall.depth._SCALES)


@dataclass
class ComposeResult:
    folded: bool
    n_atoms: int = 0
    combine: str = ""
    lenses: List[str] = None
    detail: str = ""


def recombine_verify(fn: Callable[[int], object], atoms: AT.Atoms, folds) -> ComposeResult:
    """EXACT iff all atoms folded AND combine(atoms)(n) == fn(n) on all carry-straddle scales (operator re-verified)."""
    lenses = [f.lens for f in folds]
    if not all(f.folded for f in folds):
        bad = [i for i, f in enumerate(folds) if not f.folded]
        return ComposeResult(False, len(atoms.atoms), atoms.combine, lenses,
                             f"atom(s) {bad} did not fold in any lens ⇒ composite DECLINE (no false EXACT)")
    try:
        for s in _SCALES:
            for n in (s, s + 1, s + 7):                    # a small straddle past each carry scale
                if AT.reconstruct(atoms, n) != fn(n):
                    return ComposeResult(False, len(atoms.atoms), atoms.combine, lenses,
                                         f"★ recombination operator {atoms.combine!r} BROKE at n={n} (carry scale {s}) "
                                         "⇒ DECLINE (the claimed combine op is wrong)")
    except Exception as e:  # noqa: BLE001
        return ComposeResult(False, len(atoms.atoms), atoms.combine, lenses, f"recombine raised ({e}) ⇒ DECLINE")
    return ComposeResult(True, len(atoms.atoms), atoms.combine, lenses,
                         f"composite folded: {len(atoms.atoms)} atoms each z3-gated in lenses {lenses}, recombined by "
                         f"{atoms.combine!r} and re-verified on carry scales {_SCALES} ⇒ EXACT")
