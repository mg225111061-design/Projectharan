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
    """M10 guaranteed-structure-by-size. WIRED (native, zero-dep, CONSTRUCTIVE): Erdős–Szekeres monotone-subsequence
    extraction ({"sequence":[...]}), pigeonhole repeated-state cycle ({"states":[...]}), and Ramsey R(3,3)
    monochromatic-triangle extraction ({"ramsey":fn,"n":n}) — each with a directly-checkable witness above the
    forcing threshold. The NON-CONSTRUCTIVE Robertson–Seymour forbidden-minor bound stays honestly deferred."""
    if isinstance(x, dict) and ("sequence" in x or "states" in x or ("ramsey" in x and "n" in x)):
        import guaranteed_structure
        return guaranteed_structure.m10_grade(x)
    return honest_defer("M10.structure_by_size",
                        "wired for {sequence} Erdős–Szekeres / {states} pigeonhole-cycle / {ramsey,n} Ramsey "
                        "(constructive, with witness); NON-CONSTRUCTIVE wqo / forbidden-minor bound deferred (honest)")


MECHANISM = Mechanism(
    num=10, name="structure_by_size", probe=_probe, apply=_apply,
    cert_kinds=("wqo_guarantee", "vc_bound", "cell_count"),
    contract="requires a minor-closed / bounded-width / finite-VC family; ensures a finiteness or sample-complexity "
            "bound (often NON-CONSTRUCTIVE — stated honestly); grade EXACT (bound) / DECISION; composes → M14",
    composable_with=(2, 14),
)
