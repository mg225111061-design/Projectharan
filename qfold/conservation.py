"""
§AY REL-2 — conservation loop-invariant fold (Killing / Noether provenance).
================================================================================================================
If a quantity Q is INVARIANT under the loop step — Q(step(state)) = Q(state) ∀ state — then a loop that queries Q
after N iterations folds to Q(initial) in O(1) (the iteration is irrelevant to Q). The invariance is checked as an
EXACT polynomial identity Q∘step − Q ≡ 0 over the state variables (finite-variable, decidable — the directive's
QF_NRA discharge, done by exact polynomial arithmetic; REUSE the qfold.carleman multivariate-poly engine).

★ ∀-step by the polynomial identity (telescoping over the orbit), then the loop query telescopes to Q(initial).
★ A non-invariant Q ⇒ DECLINE. Finding an invariant in general is undecidable (the Killing PDE) — this VERIFIES a
GIVEN Q, it does not claim to find all Q (the honest scope, matching lagrangian/Noether). Float ⇒ DECLINE.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Dict, Optional, Sequence, Tuple

import kernel_verdict as KV

from . import _la
from .carleman import _padd, _pmul, _ppow, _eval  # REUSE the exact multivariate-poly engine

Mono = Tuple[int, ...]
Poly = Dict[Mono, Fraction]


def _compose_Q_with_step(Q: Poly, step: Sequence[Poly], nvars: int) -> Poly:
    """Q(step(x)) — substitute each variable x_i by its step polynomial step[i] into Q (exact)."""
    out: Poly = {}
    for m, c in Q.items():
        term: Poly = {tuple([0] * nvars): c}
        for var in range(nvars):
            if m[var]:
                term = _pmul(term, _ppow(step[var], m[var], nvars))
        out = _padd(out, term)
    return out


def conservation_fold(step: Sequence[Poly], nvars: int, Q: Poly, x0: Optional[Sequence] = None) -> KV.Verdict:
    """Verify Q is a loop invariant (Q∘step − Q ≡ 0 exactly) ⇒ the loop's Q-query folds to Q(initial), O(1). EXACT
    (invariant) or DECLINE (non-invariant / float)."""
    try:
        Qf = {m: _la.exact(c) for m, c in Q.items()}
        sf = [{m: _la.exact(c) for m, c in p.items()} for p in step]
    except _la.NonExact as e:
        return KV.decline(f"conservation: {e} ⇒ DECLINE (no float-EXACT)", "conservation_invariant")
    if len(sf) != nvars:
        return KV.decline("conservation: step dimension mismatch", "conservation_invariant")
    Qstep = _compose_Q_with_step(Qf, sf, nvars)
    diff = _padd(Qstep, {m: -c for m, c in Qf.items()})
    if diff:                                                          # Q∘step − Q ≠ 0 ⇒ not invariant
        return KV.decline("conservation: Q(step(state)) ≠ Q(state) (Q∘step−Q ≢ 0) ⇒ not a loop invariant ⇒ DECLINE",
                          "conservation_invariant")
    result = {"invariant": True, "folds_to": "Q(initial)"}
    if x0 is not None:
        try:
            result["Q_initial"] = str(_eval(Qf, _la.fvec(x0)))
        except _la.NonExact:
            pass
    cert = KV.Cert(KV.EXACT, "conservation_invariant", passed=True, check_cost="exact polynomial identity Q∘step−Q=0",
                   detail="Q(step(state))=Q(state) as a polynomial identity (∀-step) ⇒ the loop's Q-query telescopes "
                          "to Q(initial)")
    return KV.exact(result, "conservation_invariant", "O(1) (query folds to Q(initial)) vs O(N)", cert,
                    reason="Axis-A: conserved-quantity query recognized; Axis-B O(N)→O(1)")


def adversarial_battery() -> dict:
    """★ EXACT: a linear invariant (x+y under (x,y)→(x+1,y−1)) and a QUADRATIC invariant (x²+y² under the swap
    (x,y)→(y,x)) verify and fold to Q(initial). ★★ DECLINE: a non-invariant Q (x under (x,y)→(x+1,y)) ⇒ DECLINE;
    float coefficients ⇒ DECLINE."""
    F = Fraction
    # linear: step (x,y) -> (x+1, y-1); Q = x+y
    lin = conservation_fold([{(1, 0): F(1), (0, 0): F(1)}, {(0, 1): F(1), (0, 0): F(-1)}], 2,
                            {(1, 0): F(1), (0, 1): F(1)}, x0=[3, 4])
    lin_ok = lin.status == KV.EXACT and lin.result.get("Q_initial") == "7"
    # quadratic: step (x,y) -> (y, x) [swap]; Q = x²+y²
    quad = conservation_fold([{(0, 1): F(1)}, {(1, 0): F(1)}], 2, {(2, 0): F(1), (0, 2): F(1)})
    quad_ok = quad.status == KV.EXACT
    # non-invariant: step (x,y) -> (x+1, y); Q = x  ⇒ x+1 ≠ x
    noninv = conservation_fold([{(1, 0): F(1), (0, 0): F(1)}, {(0, 1): F(1)}], 2, {(1, 0): F(1)})
    noninv_declines = noninv.status == KV.DECLINE
    flt = conservation_fold([{(1, 0): 1.5}, {(0, 1): F(1)}], 2, {(1, 0): F(1)})
    flt_declines = flt.status == KV.DECLINE
    cases = {"linear_invariant_exact": lin_ok, "quadratic_invariant_exact": quad_ok,
             "noninvariant_declines": noninv_declines, "float_declines": flt_declines}
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, x in cases.items() if not x]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
