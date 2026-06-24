"""Mechanism 12 — ALGORITHMIC STATISTICS / minimal description (Kolmogorov structure function & MDL 2-part code,
Shannon/Huffman/arithmetic coding, kernelization / FPT instance compression, VC sample complexity). Output: a
minimal description length / compressed instance — or, when the 2-part code can't beat the literal, an
incompressibility verdict that composes into M14 DECLINE."""
from mechanisms.base import Mechanism, feats, honest_defer


def _probe(x):
    f = feats(x)
    s = 0.0
    if "random" in f.tags:
        s += 0.4
    if "mdl" in f.text or "huffman" in f.text or "kolmogorov" in f.text or "kernelization" in f.text:
        s += 0.4
    return min(1.0, s)


def _apply(x, **kw):
    return honest_defer("M12.algorithmic_statistics", "MDL / coding / kernelization applies land in PHASE F (+ incompressibility→M14)")


MECHANISM = Mechanism(
    num=12, name="algorithmic_statistics", probe=_probe, apply=_apply,
    cert_kinds=("mdl_two_part", "code_length", "kernel_size"),
    contract="requires data with a candidate model class; ensures a 2-part code (model+residual) shorter than the "
            "literal, machine-measured; if not shorter → incompressible → M14 DECLINE; grade EXACT(length)/DECLINE",
    composable_with=(7, 14),
)
