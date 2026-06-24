"""Mechanism 9 — COMPLETE INVARIANT for classification (univalence = the *definition* of this mechanism;
Cartan–Karlhede, Petrov, operator-algebra type I/II/III, syntactic monoid, modular decomposition, Big-Five
reversal, proof-theoretic ordinal, arithmetic-hierarchy position, stability/U-rank, Hohenberg–Kohn, topological
invariants Chern/Z₂). Output: a complete invariant that decides isomorphism/equivalence (⟂ M14 turbulence when
NO complete invariant exists)."""
from mechanisms.base import Mechanism, feats, honest_defer


def _probe(x):
    f = feats(x)
    s = 0.0
    if "classify" in f.tags:
        s += 0.6
    if "physics" in f.tags:
        s += 0.2
    if "size_class" in f.tags:
        s += 0.1
    return min(1.0, s)


def _apply(x, **kw):
    """Mechanism 9: a complete invariant. Buckingham-Π (dimensionless-group normal form) is wired (PHASE F); other
    complete-invariant instances (Cartan–Karlhede, Petrov, …) exist as modules and are deferred until wired+gated."""
    if isinstance(x, dict) and x and all(isinstance(v, dict) and all(isinstance(e, int) for e in v.values()) for v in x.values()):
        import mathmode.buckingham as B
        return B.buckingham_pi(x)
    return honest_defer("M9.complete_invariant", "non-Buckingham complete-invariant instances gated in a later PHASE")


MECHANISM = Mechanism(
    num=9, name="complete_invariant", probe=_probe, apply=_apply,
    cert_kinds=("complete_invariant", "isomorphism_decision", "ordinal_rank"),
    contract="requires a classification problem admitting a complete invariant; ensures the invariant DECIDES "
            "equivalence (machine-checked: equal invariant ⟺ equivalent on a battery); grade EXACT/DECISION; "
            "if no complete invariant (turbulence/E₀) → defer to M14 DECLINE",
    composable_with=(2, 14),
)
