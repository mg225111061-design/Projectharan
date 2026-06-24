"""
CATALOG ENGINE — the 14 meta-mechanisms (Constitution §3).
==========================================================
~190 catalog transforms (passes 1-6 / A-1·A-2 / B-1·B-2 / C-1·C-2 / D-1·D-2) all map onto exactly 14 composable
mechanisms + 2 cross-cutting primitives. The framework is CLOSED: D-1·D-2 found no 15th mechanism (cut-elimination
is the purest M13; univalence is M9 made definitional; SOS = M4+M14; sum-check = M2+M7; PCP = M8+error-correction;
GCT = M9+symmetry; the logical diagonal/fixpoint lemma is the shared ur-form of M1·M14, not a new peer).

`MECHANISMS[1..14]` are the mechanisms; `PRIMITIVES` are the two techniques (Legendre duality, symmetry reduction).
`probe_vector(x)` is the cheap (µs) §5 routing signal; the composition router lives in `catalog.compose`.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from mechanisms.base import Mechanism, feats, honest_defer, tag_probe  # noqa: F401  (re-exported)
from mechanisms import (
    m01_diagonalize, m02_canonical_elim, m03_guess_finite_certify, m04_relax_dualize,
    m05_conservation, m06_renormalize_fixpoint, m07_structured_pseudorandom, m08_confluent_normalform,
    m09_complete_invariant, m10_structure_by_size, m11_hidden_statespace, m12_algorithmic_statistics,
    m13_kleene_fixpoint, m14_obstruction_cert, primitives,
)

_MODS = [
    m01_diagonalize, m02_canonical_elim, m03_guess_finite_certify, m04_relax_dualize,
    m05_conservation, m06_renormalize_fixpoint, m07_structured_pseudorandom, m08_confluent_normalform,
    m09_complete_invariant, m10_structure_by_size, m11_hidden_statespace, m12_algorithmic_statistics,
    m13_kleene_fixpoint, m14_obstruction_cert,
]

MECHANISMS: Dict[int, Mechanism] = {mod.MECHANISM.num: mod.MECHANISM for mod in _MODS}
PRIMITIVES: Dict[str, Mechanism] = dict(primitives.PRIMITIVES)

assert sorted(MECHANISMS) == list(range(1, 15)), f"the 14 mechanisms must be exactly 1..14, got {sorted(MECHANISMS)}"


def probe_vector(x: Any) -> List[float]:
    """The cheap §5 routing signal: [0,1]^14 fit of each mechanism to the input (a HEURISTIC first pass — the
    real recognizer runs inside each mechanism's gated `apply`)."""
    return [MECHANISMS[i].probe(x) for i in range(1, 15)]


def top_mechanisms(x: Any, k: int = 3, thresh: float = 0.2) -> List[Tuple[int, float]]:
    """The top-k mechanisms by probe score above `thresh` — the candidates the composition router pipelines."""
    scored = [(i, MECHANISMS[i].probe(x)) for i in range(1, 15)]
    return [(i, round(s, 3)) for i, s in sorted(scored, key=lambda t: -t[1]) if s > thresh][:k]


def closure_report() -> dict:
    """The §D-1·D-2 closure claim, as data: 14 mechanisms, 2 primitives, ur-form annotations on 1 & 14."""
    return {
        "n_mechanisms": len(MECHANISMS),
        "primitives": list(PRIMITIVES),
        "ur_form_annotated": [i for i in MECHANISMS if MECHANISMS[i].ur_form],
        "framework_closed": len(MECHANISMS) == 14,
        "fifteenth_candidate": None,   # none found — D-1·D-2 confirmed closure
    }
