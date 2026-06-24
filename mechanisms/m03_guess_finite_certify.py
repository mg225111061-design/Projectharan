"""Mechanism 3 — GUESS over a FINITE search space + CERTIFY (elliptic-curve descent, certified-numeric zero
verification, IC3/PDR inductive invariant, type-checking decidability, sum-check arithmetization). Output:
decision backed by a finitely-checkable witness."""
from mechanisms.base import Mechanism, feats, honest_defer


def _probe(x):
    f = feats(x)
    s = 0.0
    if "quantifier" in f.tags:
        s += 0.3
    if "proof" in f.tags:
        s += 0.3
    if "recurrence" in f.tags or "fixpoint" in f.tags:
        s += 0.2
    return min(1.0, s)


def _apply(x, **kw):
    return honest_defer("M3.guess_finite_certify", "finite-witness certify applies land in PHASE C/F (IC3, certified-numeric)")


MECHANISM = Mechanism(
    num=3, name="guess_finite_certify", probe=_probe, apply=_apply,
    cert_kinds=("inductive_invariant", "interval_enclosure", "witness_replay"),
    contract="requires a decision with a polynomially-checkable witness over a finite/bounded space; ensures the "
            "witness is machine-rechecked (Cert.passed); grade EXACT (or DECISION)",
    composable_with=(2, 13),
)
