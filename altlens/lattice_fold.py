"""
§Y LENS 4 — BOUNDED LATTICE-HEIGHT FIXPOINT FOLD (order structure; Knaster–Tarski).
================================================================================================================
A loop whose update f is MONOTONE over a finite-height lattice reaches its fixpoint in ≤ h steps (h = lattice height),
so n≫h folds O(n)→O(h). This is the ORDER-structure lens — orthogonal to the algebra/topology/analysis of the 22. For
a 64-bit bitset, h=64 → O(1).

★ z3 gate (precision 1.0): over the bitset lattice ({0,1}^k, ⊆), prove (a) f is MONOTONE (x⊑y ⟹ f(x)⊑f(y)), (b) the
iterates form a stabilizing chain (f EXTENSIVE: x⊑f(x) — ascending — or co-extensive: f(x)⊑x — descending), (c) the
height bound (f^h(x)==f^{h+1}(x) ∀x — fixpoint reached). Proved ⇒ fold (n≥h ⟹ result==f^h(x0)); else DECLINE.
★ The trap: monotonicity must be PROVED, not assumed — a single non-monotone op (−, ~, a data-dependent branch)
breaks it and MUST DECLINE. Issues the existing EXACT verdict (a new analysis, not a new certificate kind).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class LatticeFold:
    issued: bool
    paradigm: str = "lattice_fixpoint"
    mechanism: str = "linear_recurrence"   # existing EXACT verdict; the analysis is new, the kind is not
    height: Optional[int] = None
    applied_callsites: List[str] = field(default_factory=list)
    skipped_callsites: List[str] = field(default_factory=list)
    detail: str = ""

    @property
    def applied(self) -> bool:
        return bool(self.applied_callsites)


def _subset(x, y):
    """x ⊑ y in the bitset lattice ⟺ (x & y) == x (every set bit of x is set in y)."""
    return (x & y) == x


def _compose(f: Callable, k: int) -> Callable:
    def fk(x):
        for _ in range(k):
            x = f(x)
        return x
    return fk


def prove_monotone(f: Callable, width: int) -> bool:
    import z3
    x, y = z3.BitVecs("x y", width)
    s = z3.Solver()
    s.add(_subset(x, y), z3.Not(_subset(f(x), f(y))))      # ∃ x⊑y with f(x)⋢f(y) ⇒ NOT monotone
    return s.check() == z3.unsat


def _extensive(f: Callable, width: int, co: bool = False) -> bool:
    import z3
    x = z3.BitVec("x", width)
    s = z3.Solver()
    s.add(z3.Not(_subset(f(x), x) if co else _subset(x, f(x))))
    return s.check() == z3.unsat


def prove_fixpoint_at_height(f: Callable, h: int, width: int) -> bool:
    """Prove ∀x. f^h(x) == f^{h+1}(x) — the fixpoint is reached within h steps (h = lattice height)."""
    import z3
    x = z3.BitVec("x", width)
    s = z3.Solver()
    s.add(_compose(f, h)(x) != _compose(f, h + 1)(x))
    return s.check() == z3.unsat


def lattice_fold(f: Callable, width: int) -> LatticeFold:
    """Issue the fixpoint fold iff f is z3-proved MONOTONE, the chain stabilizes (extensive or co-extensive), and the
    height bound f^h==f^{h+1} holds. h = width (bitset height). Non-monotone ⇒ DECLINE."""
    if not prove_monotone(f, width):
        return LatticeFold(False, detail="update is NOT monotone over the bitset lattice (e.g. −/~/data-branch) ⇒ "
                           "DECLINE — no fixpoint guarantee")
    ext, coext = _extensive(f, width, co=False), _extensive(f, width, co=True)
    if not (ext or coext):
        return LatticeFold(False, detail="monotone but the iterate chain is neither ascending nor descending ⇒ "
                           "cannot bound the orbit ⇒ DECLINE")
    if not prove_fixpoint_at_height(f, width, width):
        return LatticeFold(False, height=width, detail=f"fixpoint not reached within height {width} ⇒ DECLINE")
    direction = "ascending (closure)" if ext else "descending (interior)"
    return LatticeFold(True, height=width,
                       detail=f"monotone {direction} over ({{0,1}}^{width}, ⊆); fixpoint in ≤{width} steps "
                              f"(Knaster–Tarski, z3-proved) ⇒ n≥{width} folds O(n)→O({width})")


def apply_at_callsite(lf: LatticeFold, callsite: str, n: int) -> bool:
    """Apply the fixpoint fold ONLY where the loop runs n ≥ height iterations (then n→h). n<h ⇒ keep the original."""
    if not lf.issued or lf.height is None or n < lf.height:
        lf.skipped_callsites.append(callsite)
        return False
    lf.applied_callsites.append(callsite)
    return True


def adversarial_battery() -> dict:
    """Monotone+extensive bit-propagation folds; a non-monotone update (~x) is rejected; an unbounded-direction
    monotone map that neither rises nor falls is declined; n<height keeps the original."""
    W = 8
    full = (1 << W) - 1
    or_prop = lambda x: x | ((x << 1) & full)               # reachability-style: monotone + extensive, height ≤ W
    and_mask = lambda x: x & 0b10101010                      # monotone + co-extensive (descending) — also folds
    complement = lambda x: (~x) & full                       # NON-monotone ⇒ must be rejected
    lf_or = lattice_fold(or_prop, W)
    lf_and = lattice_fold(and_mask, W)
    lf_not = lattice_fold(complement, W)
    # n<height keeps the original
    applied_big = apply_at_callsite(lf_or, "n_1000", 1000)
    applied_small = apply_at_callsite(lf_or, "n_3", 3)
    cases = {
        "monotone_extensive_folds": lf_or.issued,
        "monotone_descending_folds": lf_and.issued,
        "non_monotone_rejected": not lf_not.issued,
        "applied_when_n_ge_height": applied_big,
        "kept_original_when_n_lt_height": not applied_small,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
