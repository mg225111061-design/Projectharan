"""Mechanism 7 — STRUCTURE + PSEUDORANDOM decomposition (★ master principle). Szemerédi regularity, circle
method (major/minor arcs), explicit-formula, Nisan–Wigderson hardness→randomness, zigzag product / expanders,
hardness-vs-randomness. Output: a structured part (foldable by 1/2/13) + a pseudorandom remainder (bounded by
12/14). The deepest recurring idea in the catalog."""
from mechanisms.base import Mechanism, feats, honest_defer


def _probe(x):
    f = feats(x)
    s = 0.0
    if "random" in f.tags:
        s += 0.4
    if "sum" in f.tags:
        s += 0.2
    if "graph" in f.tags:
        s += 0.2
    if "szemer" in f.text or "circle method" in f.text or "expander" in f.text:
        s += 0.4
    return min(1.0, s)


def _apply(x, **kw):
    return honest_defer("M7.structured_pseudorandom", "structure+pseudorandom split applies land in PHASE E/F (bound-only)")


MECHANISM = Mechanism(
    num=7, name="structured_pseudorandom", probe=_probe, apply=_apply,
    cert_kinds=("regularity_partition", "arc_bound", "pseudorandom_bound"),
    contract="requires a near-random object with hidden structure; ensures a decomposition struct⊕pseudo where the "
            "structured part is foldable (EXACT) and the remainder carries a measured bound (PROBABILISTIC) — never "
            "an Ω(N) breach; grade EXACT⊕PROBABILISTIC, per-instance witness only",
    composable_with=(1, 2, 12, 13, 14),
)
