"""
§AE ISLAND 4 — HOLONOMIC-SUMMATION (barrier: Risch/Zeilberger non-terminate beyond hypergeometric): the largest island.
================================================================================================================
General summation closed forms are intractable / non-terminating. The island: the summation classes with GUARANTEED
termination — polynomial (Faulhaber), geometric, poly-geometric `Σ p(i)rⁱ`, GOSPER-summable hypergeometric (Gosper's
algorithm is complete & terminating), ZEILBERGER creative telescoping (proper-hypergeometric), KARR's ΠΣ-field, and
C-finite/D-finite (sin/cos via `f(n+2)−2cos(ω)f(n+1)+f(n)=0`). Real algorithms: Gosper (1978), Zeilberger (1991), Karr
(1981).

★ Repo-first: REUSE `catalog/holonomic_sum.py` (nested double-sum) and §AA-W1 + the grandfathered sympy for the symbolic
steps; this EXTENDS ⑬ (Faulhaber/Gosper) — the largest genuinely-new fold territory (structured summation). Grade: EXACT.
★ z3/symbolic gate (TERMINATING): verify the closed form by the TELESCOPING identity `C(n) − C(n−1) == summand(n)`
(sympy simplify==0, terminating). ★ DECLINE: non-holonomic (`H_n`, `H_n/n`, digamma/zeta), non-elementary, unevaluated.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class HolonomicSumFold:
    issued: bool
    summand: str
    closed_form: str = ""
    summation_class: str = ""               # polynomial | geometric | poly_geometric | gosper_hypergeometric | non_holonomic
    grade: str = "EXACT"
    verified: bool = False                  # the telescoping identity C(n)−C(n−1)==summand(n) holds
    detail: str = ""


def _classify(summand, k):
    import sympy as sp
    if summand.is_polynomial(k):
        return "polynomial"
    # geometric r^k / poly-geometric p(k)·r^k
    base = None
    for f in sp.Mul.make_args(summand):
        if f.is_Pow and f.exp.has(k) and not f.base.has(k):
            base = f.base
    if base is not None:
        rest = sp.simplify(summand / base ** k)
        return "geometric" if rest.is_constant() else ("poly_geometric" if rest.is_polynomial(k) else "gosper_hypergeometric")
    # hypergeometric term-ratio rational ⇒ Gosper territory
    ratio = sp.simplify(summand.subs(k, k + 1) / summand)
    return "gosper_hypergeometric" if ratio.is_rational_function(k) else "non_holonomic"


def summation_fold(summand_str: str) -> HolonomicSumFold:
    """Fold Σ_{k=1}^{n} summand to a closed form (sympy summation — Gosper/Zeilberger/C-finite internally), verified by
    the TELESCOPING identity (terminating). ★ A non-elementary result (harmonic/digamma/zeta) or an unevaluated Sum ⇒
    DECLINE (non-holonomic, out of island)."""
    import sympy as sp
    k, n = sp.symbols("k n", integer=True, positive=True)
    try:
        summand = sp.sympify(summand_str, locals={"k": k, "n": n})
        cls = _classify(summand, k)
        closed = sp.summation(summand, (k, 1, n))
    except Exception as e:  # noqa: BLE001
        return HolonomicSumFold(False, summand_str, detail=f"sympy error: {type(e).__name__} ⇒ DECLINE")
    if closed.has(sp.Sum):
        return HolonomicSumFold(False, summand_str, summation_class="non_holonomic",
                                detail="summation did not terminate to a closed form (unevaluated Σ) ⇒ DECLINE")
    if any(closed.has(sf) for sf in (sp.harmonic, sp.digamma, sp.zeta, sp.polygamma)):
        return HolonomicSumFold(False, summand_str, summation_class="non_holonomic",
                                detail=f"closed form is non-elementary ({closed}) — non-holonomic (H_n/digamma/zeta) ⇒ DECLINE")
    # ★ telescoping verification (terminating): C(n) − C(n−1) == summand(n)
    diff = sp.simplify(closed - closed.subs(n, n - 1) - summand.subs(k, n))
    verified = (diff == 0)
    if not verified:
        return HolonomicSumFold(False, summand_str, str(closed), cls, verified=False,
                                detail="telescoping identity C(n)−C(n−1)==summand(n) FAILED ⇒ DECLINE")
    return HolonomicSumFold(True, summand_str, str(closed), cls, "EXACT", True,
                            detail=f"{cls} summation → {closed} (telescoping-verified, terminating); EXACT; extends ⑬")


def adversarial_battery() -> dict:
    """polynomial (Σk²), geometric (Σ2ᵏ), poly-geometric (Σk·2ᵏ), Gosper-telescoping (Σ1/(k(k+1))) all fold EXACT
    (telescoping-verified); ★ the non-holonomic harmonic Σ1/k DECLINES (digamma/harmonic, out of island)."""
    poly = summation_fold("k**2")
    geo = summation_fold("2**k")
    polygeo = summation_fold("k*2**k")
    gosper = summation_fold("1/(k*(k+1))")
    harmonic = summation_fold("1/k")                          # ★ non-holonomic ⇒ DECLINE
    cases = {
        "polynomial_folds": poly.issued and poly.verified and poly.summation_class == "polynomial",
        "geometric_folds": geo.issued and geo.summation_class == "geometric",
        "poly_geometric_folds": polygeo.issued and polygeo.summation_class == "poly_geometric",
        "gosper_telescoping_folds": gosper.issued and gosper.verified,
        "harmonic_declined": (not harmonic.issued) and harmonic.summation_class == "non_holonomic",   # ★ out of island
        "all_telescoping_verified": all(f.verified for f in (poly, geo, polygeo, gosper)),
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
