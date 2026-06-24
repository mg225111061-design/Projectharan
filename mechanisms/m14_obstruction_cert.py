"""Mechanism 14 — OBSTRUCTION CERTIFICATE (★ the DECLINE backbone). Rice's theorem, Liouville/Galois
non-elementary/insolvability, Borel-turbulence (E₀) no-complete-invariant, complexity barriers
(natural-proofs/relativization/algebrization), area-law (volume-law = DECLINE), FTAP no-arbitrage,
Arrow–Debreu/PPAD, SETH/3SUM/APSP fine-grained, chaos beyond Lyapunov time, MIP*=RE, MRDP. Ur-form of the
fixed-point lemma (shared with M1). Output: a POSITIVE proof of impossibility = an honest DECLINE that is a win."""
from mechanisms.base import Mechanism, feats, honest_defer


def _probe(x):
    f = feats(x)
    s = 0.0
    if "undecidable" in f.tags:
        s += 0.7
    if "random" in f.tags:
        s += 0.2
    if "classify" in f.tags and ("turbulence" in f.text or "e0" in f.text):
        s += 0.4
    return min(1.0, s)


def _apply(x, **kw):
    return honest_defer("M14.obstruction_cert", "obstruction guards (Rice/incompressibility/turbulence) land in PHASE D")


MECHANISM = Mechanism(
    num=14, name="obstruction_cert", probe=_probe, apply=_apply,
    cert_kinds=("rice_index_set", "incompressibility", "turbulence_E0", "barrier", "impossibility"),
    contract="requires a request hitting a proven impossibility boundary; ensures a POSITIVE absence-proof "
            "(DECLINE-as-win) naming the obstruction; grade DECLINE (with a machine-checkable obstruction witness "
            "where one exists)",
    composable_with=(),
    ur_form="fixed-point / recursion-theorem lemma is the constructive shadow of the obstruction (Rice via Kleene)",
)
