"""Mechanism 8 — CONFLUENT rewriting to a NORMAL FORM (cut-elimination, ZX-calculus / string-diagram rewriting,
normalization-by-evaluation, Mac Lane coherence / strictification, HoTT/cubical canonicity, PCP robustification).
The purest case of M13 (Kleene fixpoint) on a rewriting system. Output: normal form + strong-normalization /
confluence certificate."""
from mechanisms.base import Mechanism, feats, honest_defer


def _probe(x):
    f = feats(x)
    s = 0.0
    if "proof" in f.tags:
        s += 0.5
    if "zx" in f.text or "string diagram" in f.text or "cut-elim" in f.text or "normaliz" in f.text:
        s += 0.4
    return min(1.0, s)


def _apply(x, **kw):
    return honest_defer("M8.confluent_normalform", "NbE / cut-elim / ZX normal-form applies land in PHASE C/F")


MECHANISM = Mechanism(
    num=8, name="confluent_normalform", probe=_probe, apply=_apply,
    cert_kinds=("normal_form_unique", "strong_normalization", "confluence"),
    contract="requires a (locally) confluent terminating rewriting system / proof term / diagram; ensures a unique "
            "normal form, machine-rechecked by re-normalizing; grade EXACT",
    composable_with=(9, 13),
)
