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


# ── §BB R-1: backward-slice split of INTERLEAVED accumulators (the one B-4 gap with non-zero corpus possibility) ──
def _interleaved_oracle(temp_fn, accumulators, combine):
    """The original loop as ONE black box: for i in 0..n-1 compute t=temp_fn(i), update each accumulator, then
    combine the finals. Used to re-verify the split is exact (split ≡ original on held-out)."""
    def f(n: int):
        accs = [init for init, _upd in accumulators]
        for i in range(n):
            t = temp_fn(i)
            accs = [upd(accs[k], t, i) for k, (init, upd) in enumerate(accumulators)]
        return COMBINERS[combine]([a for a in accs])
    return f


def backward_slice_split(temp_fn: Callable[[int], object],
                         accumulators: List, combine: str = "add", verify_scales=(7, 19, 41)) -> Atoms:
    """R-1 (B-4): split an INTERLEAVED multi-accumulator loop into independent atom oracles by backward program
    slicing. The loop shares a per-iteration temp `t = temp_fn(i)` and updates several accumulators
    `accumulators[k] = (init_k, update_k(acc, t, i))` in one body — which the existing `from_parts` cannot
    separate (no code-exposed split). Each accumulator's backward slice RECOMPUTES the shared temp and runs only
    that accumulator (Weiser 1981: a slice preserves the sliced variable). The split is EXACT precisely when the
    temp depends on the index alone — which holds structurally here, since `temp_fn` is passed only `i` and cannot
    observe any accumulator. We still re-verify split ≡ original loop on held-out scales (cheap belt-and-suspenders);
    a wrong split would fail this and DECLINE. Returns Atoms → fed to the EXISTING fold_each/recombine gate (z3 +
    held-out=200 via recall/core): NO new mechanism, NO new disposer — false-EXACT remains structurally impossible.
    Partial fold is honest: each atom that DECLINEs is a residual the caller reports, not hidden."""
    if combine not in COMBINERS:
        return Atoms([], combine, False, f"unknown combiner {combine!r} ⇒ cannot slice-split")
    if len(accumulators) < 2:
        return Atoms([], combine, False, "fewer than 2 accumulators is not an interleave ⇒ fold the single loop directly")

    def make_slice(k):
        init_k, upd_k = accumulators[k]
        def atom(n: int):                                  # the backward slice for accumulator k: temp recomputed
            acc = init_k
            for i in range(n):
                acc = upd_k(acc, temp_fn(i), i)
            return acc
        return atom

    atoms = [make_slice(k) for k in range(len(accumulators))]
    candidate = Atoms(list(atoms), combine, True,
                      f"{len(atoms)} interleaved accumulators separated by backward slicing (shared temp recomputed)")
    # ★ re-verify the split is exact: combine(slices) ≡ original interleaved loop on held-out scales
    orig = _interleaved_oracle(temp_fn, accumulators, combine)
    for n in verify_scales:
        if reconstruct(candidate, n) != orig(n):
            return Atoms([], combine, False,
                         f"slice split ≠ original loop at n={n} (cross-iteration state ⇒ slices not independent) ⇒ DECLINE")
    return candidate
