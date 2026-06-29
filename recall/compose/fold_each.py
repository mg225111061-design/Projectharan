"""
§AP §1.2 — FOLD EACH atom through the EXISTING z3 gate (S-1: no new disposer).
================================================================================================================
Each atom is disposed exactly the way every recall module disposes: route it through `recall.core.fold_via_ai` (the
§AI/§AJ path: precheck → router → five conjecturers, each z3 ∀-proof + held-out=200) AND, for the k-automatic lens
that `fold_via_ai` does not cover, `recall.k_regular.fold` (the M22 k-kernel, §AN). An atom folds iff one of these
existing gates accepts it. A wrong atom (random residual) is REJECTED here — so a wrong decomposition can never
manufacture a false EXACT.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass
class AtomFold:
    folded: bool
    lens: str = ""                       # which existing lens disposed it
    structure: str = ""
    detail: str = ""


def fold_one(atom: Callable[[int], object]) -> AtomFold:
    """Dispose ONE atom via the existing gates: §AI/§AJ conjecturers first, then the §AN k-automatic (M22) lens."""
    from recall import core
    r = core.fold_via_ai(atom, "compose(atom)")
    if r.folded:
        return AtomFold(True, "conjecture[z3+held-out]", r.structure_class, r.detail)
    try:
        from recall import k_regular as KR
        kr = KR.fold(atom)
        if kr.folded:
            return AtomFold(True, "k_automatic(M22)", kr.kind, kr.detail)
    except Exception:  # noqa: BLE001
        pass
    return AtomFold(False, "", "", "atom not disposed by any existing lens (conjecturers + M22) ⇒ DECLINE")


def fold_all(atoms: List[Callable[[int], object]]) -> List[AtomFold]:
    return [fold_one(a) for a in atoms]
