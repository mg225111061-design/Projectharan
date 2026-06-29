"""
§AP §1.1 — ATOMIZE: split a COMPOSITE stream into the independent atoms the code already exposes.
================================================================================================================
Real code computes composite quantities as separate sub-computations combined by a known operator
(`return part_a(n) + part_b(n)`, two accumulator loops then add/multiply). When the engine sees the WHOLE f as one
black box it can miss it — especially CROSS-LENS composites: a C-finite atom + a k-automatic atom is neither C-finite
nor k-automatic, so no single conjecturer folds the sum, yet each atom folds in its own lens.

★ Honest (S-4): blind inversion of an arbitrary sum is UNDER-DETERMINED (P-2) — infinitely many (a,b) give a+b=f. So
we do NOT invent a decomposition; we use the one the CODE exposes (separate accumulators / a combine expression). This
module only SEPARATES; §1.2 folds each atom through the existing z3 gate and §1.3 re-verifies the recombination.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List

# the combine operators a composite stream can be reassembled by (each a TOTAL deterministic function)
COMBINERS = {
    "add": lambda xs: sum(xs),
    "sub": lambda xs: xs[0] - sum(xs[1:]),
    "mul": lambda xs: __import__("functools").reduce(lambda a, b: a * b, xs, 1),
    "max": lambda xs: max(xs),
    "min": lambda xs: min(xs),
}


@dataclass
class Atoms:
    atoms: List[Callable[[int], object]]
    combine: str                         # key into COMBINERS
    ok: bool = True
    detail: str = ""


def from_parts(parts: List[Callable[[int], object]], combine: str = "add") -> Atoms:
    """The structural decomposition the code exposes: a list of independent atom oracles + the combine operator. This is
    the SOUND entry point — the atoms are real sub-computations, not a guessed split."""
    if combine not in COMBINERS:
        return Atoms([], combine, False, f"unknown combiner {combine!r} ⇒ cannot atomize")
    if len(parts) < 2:
        return Atoms([], combine, False, "a single atom is not a composite ⇒ fold directly, not via compose")
    return Atoms(list(parts), combine, True, f"{len(parts)} atoms exposed by the code, combined by {combine!r}")


def reconstruct(atoms: Atoms, n: int):
    """Evaluate combine(atom_i(n)) — the recombination, used by §1.3 to re-verify the operator on held-out scales."""
    vals = [a(n) for a in atoms.atoms]
    return COMBINERS[atoms.combine](vals)
