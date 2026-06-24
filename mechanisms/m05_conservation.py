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
    return honest_defer("M5.conservation", "Noether/Lax conserved-quantity applies land in PHASE F")


MECHANISM = Mechanism(
    num=5, name="conservation", probe=_probe, apply=_apply,
    cert_kinds=("noether_dIdt", "lax_commutator"),
    contract="requires Lagrangian/Hamiltonian with a symmetry, or a Lax-pair candidate; ensures a conserved I with "
            "machine-checked dI/dt≡0 (symbolic) ; grade EXACT",
    composable_with=(1, 9),
)
