"""Mechanism 6 — RENORMALIZE to a FIXPOINT (RG fixed point + critical exponents, multigrid/AMG convergence,
abstract interpretation Kleene/Tarski fixpoint + widening). Output: fixpoint + convergence/critical bound.
Closely related to M13 (Kleene fixpoint) — M6 is the *scale/coarsening* specialization."""
from mechanisms.base import Mechanism, feats, honest_defer


def _probe(x):
    f = feats(x)
    s = 0.0
    if "fixpoint" in f.tags:
        s += 0.5
    if "physics" in f.tags and "renormaliz" in f.text:
        s += 0.4
    if "loop" in f.tags:
        s += 0.1
    return min(1.0, s)


def _apply(x, **kw):
    return honest_defer("M6.renormalize_fixpoint", "RG / multigrid / abstract-interp widening applies land in PHASE C/F")


MECHANISM = Mechanism(
    num=6, name="renormalize_fixpoint", probe=_probe, apply=_apply,
    cert_kinds=("fixpoint_inductive", "contraction_bound", "critical_exponent"),
    contract="requires a scale-invariant flow or a monotone lattice iteration; ensures a (post-)fixpoint with an "
            "inductiveness check or a contraction factor; grade EXACT (inductive) else PROBABILISTIC",
    composable_with=(13,),
)
