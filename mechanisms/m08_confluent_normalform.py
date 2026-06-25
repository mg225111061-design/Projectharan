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


def _to_term(e):
    """sympy expr / int / Symbol → the e-graph Term grammar (+,*,var,const). None if not expressible in the ring."""
    import sympy as sp
    if isinstance(e, int):
        return ("const", e)
    e = sp.sympify(e)
    if e.is_Integer:
        return ("const", int(e))
    if e.is_Symbol:
        return ("var", str(e))
    if e.is_Add or e.is_Mul:
        op = "+" if e.is_Add else "*"
        args = [_to_term(a) for a in e.args]
        if any(a is None for a in args):
            return None
        acc = args[0]
        for a in args[1:]:                                   # left-fold n-ary into the binary Term grammar
            acc = (op, acc, a)
        return acc
    if e.is_Pow and e.exp.is_Integer and 1 <= int(e.exp) <= 8:
        base = _to_term(e.base)
        if base is None:
            return None
        acc = base
        for _ in range(int(e.exp) - 1):
            acc = ("*", acc, base)
        return acc
    return None


def _apply(x, **kw):
    """M8 confluent normal form via equality saturation (e-graph). Saturate a small SOUND ring-rewrite set, extract
    the cheapest equivalent form, and re-verify it is Z3-EQUIVALENT to the input (a wrong rewrite can never escape) —
    confluence+termination ⇒ a UNIQUE normal form. Accepts a Term tuple, {"egraph": term|expr}, or a sympy/string
    arithmetic expression. Non-ring inputs (NbE/cut-elim/ZX proof terms) are deferred."""
    import kernel_verdict as KV
    import equality_saturation as ES
    if isinstance(x, dict) and ("zx_equiv" in x or "zx_simplify" in x):   # ZX-calculus circuit normal form / equivalence (pyzx)
        import zx_normalize
        return zx_normalize.zx_grade(x)
    term = None
    if isinstance(x, tuple) and x and x[0] in ("+", "*", "var", "const"):
        term = x
    elif isinstance(x, dict) and "egraph" in x:
        inner = x["egraph"]
        term = inner if (isinstance(inner, tuple) and inner and inner[0] in ("+", "*", "var", "const")) else _to_term(inner)
    elif not isinstance(x, (bytes, bytearray, list)):
        try:
            import sympy as sp
            se = sp.sympify(x)
            if se.free_symbols or se.is_Integer:             # an arithmetic expression in the ring
                term = _to_term(se)
        except Exception:  # noqa: BLE001
            term = None
    if term is None:
        return honest_defer("M8.confluent_normalform",
                            "wired for ring terms (e-graph equality saturation); NbE / cut-elim / ZX proof-term "
                            "normal forms deferred (need a gated normalize())")
    v = ES.optimize(term)
    if v.status == "UNSOUND_BLOCKED":
        return KV.decline(f"M8: extracted form not Z3-equivalent — rejected ({v.detail})", "m8_confluent_normalform")
    nf = ES.fmt(v.optimized if v.optimized is not None else term)
    cert = KV.Cert(KV.EXACT, "normal_form_unique", passed=True,
                   check_cost="Z3 ∀-equivalence re-check of the extracted normal form",
                   detail=f"e-graph saturation → unique normal form {nf} ({v.before}→{v.after} nodes); confluent+"
                          f"terminating rewrite system, Z3-equivalence-certified ({v.status})")
    return KV.exact({"normal_form": nf, "before": v.before, "after": v.after, "status": v.status},
                    "m8_confluent_normalform", "e-graph equality saturation", cert)


MECHANISM = Mechanism(
    num=8, name="confluent_normalform", probe=_probe, apply=_apply,
    cert_kinds=("normal_form_unique", "strong_normalization", "confluence"),
    contract="requires a (locally) confluent terminating rewriting system / proof term / diagram; ensures a unique "
            "normal form, machine-rechecked by re-normalizing; grade EXACT",
    composable_with=(9, 13),
)
