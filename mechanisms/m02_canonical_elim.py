"""Mechanism 2 — CANONICAL FORM by ELIMINATION / rewriting (Gröbner/Buchberger, Gosper/Zeilberger via Ore,
tensor canonicalization, Markov bases, Presburger/RCF/ACF quantifier elimination, polyhedral normal form,
Courcelle tree-automata, Riemann–Roch dimension). Output: canonical/normal form + decision."""
from mechanisms.base import Mechanism, feats, honest_defer


def _probe(x):
    f = feats(x)
    s = 0.0
    if "poly" in f.tags:
        s += 0.6
    if "quantifier" in f.tags:
        s += 0.5
    if "physics" in f.tags and "matrix" not in f.tags:
        s += 0.2
    if "sum" in f.tags:
        s += 0.2
    return min(1.0, s)


def _apply(x, **kw):
    return honest_defer("M2.canonical_elim", "elimination/QE applies land in PHASE B (Presburger/RCF/ACF) and PHASE F")


MECHANISM = Mechanism(
    num=2, name="canonical_elim", probe=_probe, apply=_apply,
    cert_kinds=("groebner_cofactor", "qe_equivalence", "normal_form_replay"),
    contract="requires polynomial system / quantified arithmetic / tensor expr; ensures a canonical normal form "
            "or a decision, machine-rechecked (cofactor witness / equivalence); grade EXACT",
    composable_with=(3, 9, 13),
)
