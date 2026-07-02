"""Mechanism 5 — CONSERVATION law extraction (Noether conserved quantities, Lax pairs / integrable hierarchies,
first integrals). Output: conserved quantity I with dI/dt = 0 certificate."""
from mechanisms.base import Mechanism, feats, honest_defer


def _probe(x):
    f = feats(x)
    s = 0.0
    if "symmetry" in f.tags:
        s += 0.5
    if "physics" in f.tags:
        s += 0.3
    return min(1.0, s)


def _apply(x, **kw):
    """Mechanism 5: a conserved quantity. Noether energy conservation is wired (PHASE F) for a Lagrangian given as
    {'L':expr,'q':Function,'t':Symbol}; Lax-pair/other first integrals are deferred."""
    if isinstance(x, dict) and "L" in x and "q" in x and "t" in x:
        import mathmode.lagrangian as L
        return L.energy_conservation(x["L"], x["q"], x["t"])
    return honest_defer("M5.conservation", "non-Lagrangian conserved-quantity instances (Lax pairs) gated in a later PHASE")


MECHANISM = Mechanism(
    num=5, name="conservation", probe=_probe, apply=_apply,
    cert_kinds=("noether_dIdt", "lax_commutator"),
    contract="requires Lagrangian/Hamiltonian with a symmetry, or a Lax-pair candidate; ensures a conserved I with "
            "machine-checked dI/dt≡0 (symbolic) ; grade EXACT",
    composable_with=(1, 9),
)
