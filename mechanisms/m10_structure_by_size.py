"""Mechanism 10 — STRUCTURE GUARANTEED BY SIZE (Robertson–Seymour wqo, VC dimension, o-minimal cell
decomposition / Pila–Wilkie, twin-width / bounded-expansion). Output: a finiteness/tractability guarantee — often
NON-CONSTRUCTIVE, which composes into M14 (the finite obstruction set exists but isn't exhibited)."""
from mechanisms.base import Mechanism, feats, honest_defer


def _probe(x):
    f = feats(x)
    s = 0.0
    if "size_class" in f.tags:
        s += 0.6
    if "graph" in f.tags:
        s += 0.3
    return min(1.0, s)


def _apply(x, **kw):
    return honest_defer("M10.structure_by_size", "wqo / VC / o-minimality applies land in PHASE F (NON-CONSTRUCTIVE bound; honest)")


MECHANISM = Mechanism(
    num=10, name="structure_by_size", probe=_probe, apply=_apply,
    cert_kinds=("wqo_guarantee", "vc_bound", "cell_count"),
    contract="requires a minor-closed / bounded-width / finite-VC family; ensures a finiteness or sample-complexity "
            "bound (often NON-CONSTRUCTIVE — stated honestly); grade EXACT (bound) / DECISION; composes → M14",
    composable_with=(2, 14),
)
