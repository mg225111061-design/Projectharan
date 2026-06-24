"""
CATALOG ENGINE — mechanism base types (Constitution §3.2).
==========================================================
A `Mechanism` is a COMPOSABLE recognizer+certifier — a *kind* of transformation that many catalog entries share,
not a single transform. 14 mechanisms (1..14) + 2 cross-cutting primitives map the entire research catalog
(~190 transforms, passes 1-6 / A-1·A-2 / B-1·B-2 / C-1·C-2 / D-1·D-2). The framework is CLOSED — D-1·D-2 found no
15th mechanism (logical diagonal/fixpoint lemmas are the shared ur-form of mechanisms 1·14, not a new peer).

Honesty (§2): `apply` returns a graded `KV.Verdict` (EXACT / PROBABILISTIC(ε,δ) / DECLINE) with a machine-rechecked
certificate; an un-built `apply` returns an honest `HONEST_DEFER` DECLINE — never a fake pass.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Tuple

import kernel_verdict as KV


@dataclass
class Mechanism:
    num: int                                      # 1..14 (0/-1/-2 reserved for primitives)
    name: str
    probe: Callable[[Any], float]                 # cheap (µs) fit of this mechanism to the input → [0,1]
    apply: Callable[..., "KV.Verdict"]            # apply the mechanism to recognized structure → graded Verdict
    cert_kinds: Tuple[str, ...]                   # certificate kinds this mechanism can emit
    contract: str                                 # HARAN requires/ensures/grade
    composable_with: Tuple[int, ...] = ()         # mechanism numbers that can follow this one in a pipeline
    ur_form: str = ""                             # for 1 & 14: the diagonal/fixpoint ur-form annotation (§D-1·D-2)


def honest_defer(name: str, reason: str) -> "KV.Verdict":
    """A mechanism whose sound `apply` is not yet built returns this — an honest DECLINE, never a fake pass (§1.4)."""
    return KV.decline(f"HONEST_DEFER[{name}]: {reason}", kernel=f"mechanism:{name}")


# ── cheap, uniform feature extraction for probes (µs; pure string/type inspection, no heavy work) ───────
@dataclass
class Features:
    raw: Any
    text: str                  # str(raw), lower-cased, truncated
    kind: str                  # python type name
    is_str: bool
    is_seq: bool
    is_mapping: bool
    n: int                     # len() if sized, else 0
    tags: frozenset            # cheap structural/keyword tags (see _TAG_PATTERNS)


# keyword tags are a CHEAP first-pass signal only — the real recognizers (PHASE E/F) refine per-mechanism.
_TAG_PATTERNS: Dict[str, str] = {
    "matrix": r"\b(matrix|eigen|spectral|svd|pca|diagonal|hermitian|symmetric|covariance)\b",
    "poly": r"\b(poly|polynomial|ideal|groebner|gröbner|ore|monomial|nullstellensatz)\b",
    "sum": r"(\bsum\b|Σ|\bfor\b.*\brange\b|telescop|hypergeom|faulhaber)",
    "recurrence": r"\b(recurrence|fibonacci|c-finite|companion|linear recurrence|holonomic)\b",
    "quantifier": r"(∀|∃|forall|exists|presburger|\bqe\b|quantifier)",
    "inequality": r"(≥|≤|>=|<=|positiv|sos|sum.?of.?squares|nonneg|infeasib|farkas)",
    "optimization": r"\b(minimi|maximi|\blp\b|sdp|socp|kkt|lagrangian dual|optimi)\b",
    "graph": r"\b(graph|vertex|vertices|edge|minor|treewidth|planar|clique|matroid)\b",
    "fixpoint": r"\b(fixpoint|fixed.?point|widening|kleene|tarski|bellman|hjb|value function|abstract interp)\b",
    "loop": r"(\bwhile\b|\bfor\b|\bdef\b.*:\n)",
    "proof": r"\b(proof|cut.?elim|normaliz|sequent|lambda|type|nbe|zx|string.?diagram|coherence)\b",
    "classify": r"\b(classif|invariant|isomorph|equivalence|canonical|petrov|cartan)\b",
    "undecidable": r"\b(halt|rice|undecidable|semantic property|index set|diophant|mrdp)\b",
    "random": r"\b(random|pseudorandom|noise|kolmogorov|incompress|entropy|mdl|szemer)\b",
    "timeseries": r"\b(time.?series|kalman|enkf|cointegration|latent|manifold|tipping|lyapunov|chaos)\b",
    "symmetry": r"\b(symmetr|noether|conserv|lax pair|integrable|representation|wigner)\b",
    "physics": r"\b(metric|curvature|tensor|qft|lagrangian|hamiltonian|renormaliz|hodge)\b",
    "size_class": r"\b(wqo|well.?quasi|vc dimension|o.?minimal|twin.?width|bounded expansion|forbidden)\b",
}
_TAG_RE = {k: re.compile(v, re.IGNORECASE) for k, v in _TAG_PATTERNS.items()}


def feats(x: Any) -> Features:
    """Cheap features for probes. NEVER does heavy work — just type + a truncated string + keyword/struct tags."""
    try:
        is_str = isinstance(x, str)
        text = (x if is_str else repr(x))
        text = text[:4000].lower()
    except Exception:  # noqa: BLE001
        text = ""
    is_seq = isinstance(x, (list, tuple)) and not isinstance(x, str)
    is_mapping = isinstance(x, dict)
    try:
        n = len(x)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001
        n = 0
    tags = frozenset(k for k, rgx in _TAG_RE.items() if rgx.search(text))
    # structural tags from python type (cheap, no parsing)
    extra = set()
    if is_seq and x and all(isinstance(r, (list, tuple)) for r in x):
        extra.add("matrix")          # list-of-lists ⇒ matrix-like
    if isinstance(x, str) and ("def " in x or "for " in x or "while " in x):
        extra.add("loop")
    return Features(raw=x, text=text, kind=type(x).__name__, is_str=is_str, is_seq=is_seq,
                    is_mapping=is_mapping, n=n, tags=tags | frozenset(extra))


def tag_probe(*tags: str, base: float = 0.0) -> Callable[[Any], float]:
    """Build a cheap probe that scores by how many of `tags` are present (capped at 1.0). A heuristic first-pass
    signal — honest about being a probe, not a proof; the real recognizer runs inside `apply` and gates the result."""
    tset = set(tags)

    def _probe(x: Any) -> float:
        f = feats(x)
        hit = len(tset & set(f.tags))
        return min(1.0, base + 0.5 * hit) if hit else base
    return _probe
