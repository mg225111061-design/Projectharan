"""
CATALOG ENGINE — the ~190-transform catalog, organized as mechanisms (vertical) × transforms (horizontal).
==========================================================================================================
Every research transform (passes 1-6 / A-1·A-2 / B-1·B-2 / C-1·C-2 / D-1·D-2) is registered as a `Transform`
mapped onto the 14 mechanisms (a tuple ⇒ composition). "100% registered" (§1.4) = every transform has an HONEST
entry; `coverage()` reports registered N / verified M / deferred K — never a faked 100% pass.
"""
from __future__ import annotations

from typing import Dict, List

from catalog.base import Transform, TRANSFORMS, register, reg_many  # noqa: F401  (re-exported)
# importing the pass modules registers their transforms into TRANSFORMS
from catalog import pass_1to6, pass_A, pass_B, pass_C, pass_D  # noqa: F401,E402

# unique transform ids enforced by base.register; mechanisms must all be in 1..14 (+0/-1 primitives)
assert len(TRANSFORMS) == len({t.tid for t in TRANSFORMS}), "duplicate transform ids"

# PHASE B+ : registering §7-gated kernels into kernel_router.REGISTRY + flipping their transforms to VERIFIED.
# (imported AFTER the passes so the transforms exist to be flipped.)
from catalog import kernels_phaseB  # noqa: F401,E402
from catalog import kernels_phaseC  # noqa: F401,E402
from catalog import kernels_phaseD  # noqa: F401,E402
from catalog import kernels_phaseF  # noqa: F401,E402


def by_mechanism(num: int) -> List[Transform]:
    return [t for t in TRANSFORMS if num in t.mechanisms]


def by_pass(label: str) -> List[Transform]:
    return [t for t in TRANSFORMS if t.pass_label == label]


def composed() -> List[Transform]:
    return [t for t in TRANSFORMS if t.composed]


def coverage() -> Dict[str, object]:
    """The honest catalog coverage (§1.4): registered / verified / deferred + per-mechanism + per-pass."""
    verified = [t for t in TRANSFORMS if t.verified]
    deferred = [t for t in TRANSFORMS if not t.verified]
    per_mech = {m: len(by_mechanism(m)) for m in range(1, 15)}
    per_pass = {}
    for t in TRANSFORMS:
        per_pass[t.pass_label] = per_pass.get(t.pass_label, 0) + 1
    mech_covered = sorted({m for t in TRANSFORMS for m in t.mechanisms if 1 <= m <= 14})
    return {
        "registered": len(TRANSFORMS),
        "verified": len(verified),
        "deferred": len(deferred),
        "composed": len(composed()),
        "mechanisms_covered": mech_covered,
        "all_14_mechanisms_have_a_transform": mech_covered == list(range(1, 15)),
        "per_mechanism": per_mech,
        "per_pass": per_pass,
    }
