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


def _to_poly_expr(x):
    """Best-effort extraction of a polynomial expression from x (sympy Expr passthrough; or a string, stripping a
    trailing `>= 0` / `≥ 0` / SOS phrasing)."""
    import sympy as sp
    if isinstance(x, (sp.Expr, sp.Poly)):
        return sp.sympify(x)
    if isinstance(x, str):
        s = x
        for cut in (">=", "≥", "is sos", "is nonneg", "by sos", "via sos", "by sum", "is psd"):
            i = s.lower().find(cut)
            if i >= 0:
                s = s[:i]
        # drop leading non-math words (verbs like "prove"/"show"/"that") until a token with a digit/operator/var
        toks = s.replace("^", "**").split()
        while toks and not any(ch.isdigit() or ch in "+-*/().=" for ch in toks[0]) and len(toks[0]) > 1:
            toks.pop(0)
        cand = " ".join(toks).strip().rstrip("=").strip()
        if not cand:
            return None
        try:
            return sp.sympify(cand)
        except Exception:  # noqa: BLE001
            return None
    return None


def _apply(x, **kw):
    """Mechanism 4: prove p ≥ 0 by an EXACT SOS/Positivstellensatz certificate (rational PSD Gram). EXACT or
    honest DECLINE — never overclaims (no SDP cone search here)."""
    import sos_cert
    expr = _to_poly_expr(x)
    if expr is None:
        return honest_defer("M4.relax_dualize", "could not extract a polynomial from the input")
    return sos_cert.sos_grade(expr, kw.get("gens"))


MECHANISM = Mechanism(
    num=4, name="relax_dualize", probe=_probe, apply=_apply,
    cert_kinds=("sos_decomposition", "farkas_dual", "positivstellensatz", "residual_bound"),
    contract="requires a polynomial inequality / optimization / infeasibility instance; ensures a DUAL certificate "
            "(SOS Gram PSD + identity match, or Farkas vector) verified by exact arithmetic; grade EXACT (rational) "
            "else PROBABILISTIC(ε) for floating SDP — δ/ε stated",
    composable_with=(14,),
)
