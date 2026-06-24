"""Mechanism 4 — RELAX & DUALIZE (★ new EXACT certificate tier). SOS / Positivstellensatz (Lasserre/Parrilo),
Farkas/KKT dual infeasibility witness, FEM a-posteriori residual bound, submodular/matroid duality, Dialectica /
proof-mining bounds, SNARK/STARK / polynomial-IOP certificate technology, SOS/PC/Nullstellensatz refutation.
Output: a dual certificate (nonnegativity / infeasibility) machine-checkable."""
from mechanisms.base import Mechanism, feats, honest_defer


def _probe(x):
    f = feats(x)
    s = 0.0
    if "inequality" in f.tags:
        s += 0.6
    if "optimization" in f.tags:
        s += 0.4
    if "poly" in f.tags:
        s += 0.2
    return min(1.0, s)


def _apply(x, **kw):
    return honest_defer("M4.relax_dualize", "SOS/Positivstellensatz EXACT-tier lands in PHASE B (★ priority)")


MECHANISM = Mechanism(
    num=4, name="relax_dualize", probe=_probe, apply=_apply,
    cert_kinds=("sos_decomposition", "farkas_dual", "positivstellensatz", "residual_bound"),
    contract="requires a polynomial inequality / optimization / infeasibility instance; ensures a DUAL certificate "
            "(SOS Gram PSD + identity match, or Farkas vector) verified by exact arithmetic; grade EXACT (rational) "
            "else PROBABILISTIC(ε) for floating SDP — δ/ε stated",
    composable_with=(14,),
)
