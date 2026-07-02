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
    """M14 standalone obstruction certificate (a POSITIVE impossibility proof = a DECLINE-as-win). The Rice /
    incompressibility / turbulence guards live in catalog.decline_boundary (reached first in the router). WIRED here:
    Galois (insolvability by radicals) and Liouville (non-elementary integral) via closure_classifier —
      • {"galois_quintic": (a, b)} → x⁵+ax+b solvable by radicals? insolvable ⇒ DECLINE-as-win;
      • {"liouville": "erf"}       → ∫e^{-x²} elementary? non-elementary ⇒ DECLINE-as-win.
    The actual obstruction compute needs the `galois_absence` engine; if it is not built, HONEST_DEFER (call site
    wired — plug the engine in and it works) — never a fabricated impossibility."""
    import kernel_verdict as KV
    if isinstance(x, dict) and "galois_quintic" in x:
        import closure_classifier as CC
        a, b = x["galois_quintic"]
        cv = CC.classify_radical_absence(int(a), int(b))
        if cv.kind == "ABSENT":
            return KV.decline(f"OBSTRUCTION[galois_radical]: x⁵+{a}x+{b} is INSOLVABLE by radicals — {cv.proof} "
                              f"(mechanism 14 — impossibility proof = DECLINE-as-win)", "m14_galois")
        return honest_defer("M14.obstruction_cert", f"galois insolvability: {cv.proof} (galois_absence engine not built — "
                            f"call site wired, compute deferred)")
    if isinstance(x, dict) and x.get("liouville") == "erf":
        import closure_classifier as CC
        cv = CC.classify_elementary_absence_erf()
        if cv.kind == "ABSENT":
            return KV.decline(f"OBSTRUCTION[liouville_elementary]: ∫e^(−x²)dx is NON-ELEMENTARY — {cv.proof} "
                              f"(mechanism 14 — impossibility proof = DECLINE-as-win)", "m14_liouville")
        return honest_defer("M14.obstruction_cert", f"liouville non-elementary: {cv.proof} (galois_absence engine not "
                            f"built — call site wired, compute deferred)")
    return honest_defer("M14.obstruction_cert",
                        "standalone obstructions wired for {galois_quintic|liouville}; Rice/incompressibility/"
                        "turbulence guards are in catalog.decline_boundary (router checks them first)")


MECHANISM = Mechanism(
    num=14, name="obstruction_cert", probe=_probe, apply=_apply,
    cert_kinds=("rice_index_set", "incompressibility", "turbulence_E0", "barrier", "impossibility"),
    contract="requires a request hitting a proven impossibility boundary; ensures a POSITIVE absence-proof "
            "(DECLINE-as-win) naming the obstruction; grade DECLINE (with a machine-checkable obstruction witness "
            "where one exists)",
    composable_with=(),
    ur_form="fixed-point / recursion-theorem lemma is the constructive shadow of the obstruction (Rice via Kleene)",
)
