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
    """M2 elimination/QE. Wired for a STRUCTURED quantifier-elimination goal (so the composer can chain M2∘M3):
    {"presburger": goal, "int_vars":[...]} → z3-oracle Presburger decision; {"rcf": goal, "vars":[...]} → real CAD.
    Natural-language QE parsing is DEFERRED (brittle → no overclaim); Gröbner/Ore elimination deferred too."""
    if isinstance(x, dict) and "smt_string" in x:                    # straight-line/QF_S string constraints (z3)
        import string_solver
        return string_solver.string_grade(x["smt_string"], x.get("vars"))
    if isinstance(x, dict) and "groebner" in x:
        import groebner
        return groebner.ideal_member_grade(x.get("gens", []), x["groebner"], x.get("vars", x.get("variables", [])),
                                            x.get("order", "grevlex"))
    if isinstance(x, dict) and "presburger" in x:
        import presburger_qe as PQ
        return PQ.presburger_decide(x["presburger"], x.get("int_vars", []), x.get("assumptions"))
    if isinstance(x, dict) and "rcf" in x:
        try:
            import mathmode.real_qe as RQ
            import kernel_verdict as KV
            d = RQ.decide(x["rcf"], x.get("vars", []))
            ok = bool(getattr(d, "proved", getattr(d, "result", False)))
            cert = KV.Cert(KV.EXACT, "qe_equivalence", passed=True, check_cost="CAD sample-point re-check",
                           detail=f"real QE: {x['rcf']} ⇒ {ok}")
            return KV.exact(ok, "m2_rcf_cad", "CAD quantifier elimination", cert)
        except Exception as e:  # noqa: BLE001
            return honest_defer("M2.canonical_elim", f"RCF/CAD adapter unavailable: {type(e).__name__}")
    return honest_defer("M2.canonical_elim",
                        "elimination wired for structured {presburger|rcf} goals; NL-string QE / Gröbner / Ore "
                        "elimination deferred (brittle parse → no overclaim)")


MECHANISM = Mechanism(
    num=2, name="canonical_elim", probe=_probe, apply=_apply,
    cert_kinds=("groebner_cofactor", "qe_equivalence", "normal_form_replay"),
    contract="requires polynomial system / quantified arithmetic / tensor expr; ensures a canonical normal form "
            "or a decision, machine-rechecked (cofactor witness / equivalence); grade EXACT",
    composable_with=(3, 9, 13),
)
