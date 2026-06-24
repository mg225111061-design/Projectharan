"""
CATALOG ENGINE — mechanism-composition router (Constitution §5, the heart of chaos→structure).
==============================================================================================
No single-discipline 1:1 decomposition (§2). An input that the existing fold engine can't collapse is run through
the 14-mechanism probe vector; the TOP candidates form a COMPOSITION pipeline (research-confirmed compositions:
Robertson–Seymour 10→14, dimension-lift 9+2, circle-method 7-split, lattice 13±6, SOS 4|14, classification 9⟂14).
Each stage is §7-gated; one unsound stage ⇒ DECLINE at that point (a wrong answer is never emitted).

PHASE A: routing skeleton with the cheapest §6 DECLINE guard wired + the existing-fold short-circuit. The mechanism
`apply`s are deferred (PHASE B–F), so a catalog hit returns an HONEST DECLINE naming the would-be pipeline
(`mechanism_path`) — never a fake result. PHASE E replaces the deferred tail with real gated composition.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

import kernel_verdict as KV
import mechanisms as MECH
from catalog import decline_boundary as DB


@dataclass
class CatalogResult:
    verdict: KV.Verdict                       # the graded result (EXACT/PROBABILISTIC/DECLINE)
    mechanism_path: List[int] = field(default_factory=list)  # which mechanism composition was used/attempted
    probe: List[float] = field(default_factory=list)         # the [0,1]^14 probe vector (traceability)
    note: str = ""

    @property
    def grade(self) -> str:
        return self.verdict.status


# research-confirmed composition pipelines: (predicate on top-mechanism set) → ordered mechanism path
_COMPOSITIONS: List[Tuple[frozenset, Tuple[int, ...], str]] = [
    (frozenset({10}), (10, 14), "Robertson–Seymour: wqo size-guarantee → finite forbidden-minor obstruction"),
    (frozenset({9}), (9, 2), "dimension-lift: complete invariant → canonical normal form"),
    (frozenset({7}), (7, 13, 12), "structure⊕pseudorandom: fold the structured part, bound the remainder"),
    (frozenset({4}), (4, 14), "relax/dualize: SOS nonnegativity, else impossibility"),
    (frozenset({6}), (6, 13), "renormalize → Kleene fixpoint (± widening)"),
    (frozenset({13}), (13,), "Kleene fixpoint = the existing fold"),
    (frozenset({1}), (1, 9), "diagonalize → complete spectral invariant"),
]


def _existing_fold(x: Any) -> Optional[KV.Verdict]:
    """§5.1 — try the existing fold engine first (only for code-source strings). Returns a Verdict if it collapses."""
    if not (isinstance(x, str) and ("def " in x or "lambda" in x)):
        return None
    try:
        import structure_recognizer as SR
        d = SR.dispatch(x)
    except Exception:  # noqa: BLE001
        return None
    if getattr(d, "status", "NONE") == "OFFLOADED" and getattr(d, "closed_form", ""):
        cert = KV.Cert(KV.EXACT, "fold_closed_form", passed=True, check_cost="differential-equivalence gate",
                       detail=str(d.certificate)[:200])
        return KV.exact(d.closed_form, "fold(structure_recognizer)", getattr(d, "complexity", "O(1)"), cert)
    return None


def plan_pipeline(x: Any) -> Tuple[List[int], List[float], str]:
    """The §5 routing plan: the probe vector + the chosen composition mechanism_path (no execution)."""
    probe = MECH.probe_vector(x)
    top = MECH.top_mechanisms(x, k=3)
    top_set = {i for i, _ in top}
    for pred, path, why in _COMPOSITIONS:
        if pred & top_set:
            return list(path), probe, why
    return [i for i, _ in top], probe, "ad-hoc top-mechanism order (no canonical composition matched)"


def route(x: Any) -> CatalogResult:
    """Top-level chaos→structure entry. Order (§5): arithmetic-hierarchy placement → DECLINE guards → existing
    fold → mechanism composition."""
    # §5 cheapest: arithmetic-hierarchy placement (a Σ⁰₁/Π⁰₁-complete semantic-program-property → DECLINE, Rice)
    import arith_hierarchy as AH
    place = AH.classify(x)
    if place.route == "DECLINE":
        v = KV.decline(f"OBSTRUCTION[arith_hierarchy {place.level}]: {place.reason} (mechanism 14)", "catalog.compose")
        return CatalogResult(v, mechanism_path=[14], probe=MECH.probe_vector(x), note=f"hierarchy {place.level}")
    # §6: proven DECLINE boundary (incompressibility / turbulence; Rice also caught above)
    ob = DB.check(x)
    if ob is not None:
        return CatalogResult(ob, mechanism_path=[14], probe=MECH.probe_vector(x), note="obstruction boundary")
    # §5.1 existing fold
    fold = _existing_fold(x)
    if fold is not None:
        return CatalogResult(fold, mechanism_path=[13], probe=MECH.probe_vector(x), note="existing fold")
    # §5.2-5.4 mechanism composition (PHASE E wires real gated apply; PHASE A returns honest DECLINE w/ the plan)
    path, probe, why = plan_pipeline(x)
    if not path:
        v = KV.decline("no mechanism probe above threshold — honest DECLINE (no hidden structure detected)", "catalog.compose")
        return CatalogResult(v, mechanism_path=[], probe=probe, note="no-fit")
    v = KV.decline(f"HONEST_DEFER[compose]: pipeline {path} planned ({why}) — gated apply lands in PHASE E", "catalog.compose")
    return CatalogResult(v, mechanism_path=path, probe=probe, note=why)
