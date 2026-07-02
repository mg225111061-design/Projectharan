"""
§BM NEW-1 — Farkas / LP-duality certificate (the purest proposer-verifier; relax-dualize m04 branch, Axis B).
================================================================================================================
Expensive: solve an LP / decide feasibility. Cheap: VERIFY a certificate with one matrix–vector product.
  • Farkas' lemma (infeasibility): the system {A x ≤ b} is INFEASIBLE iff ∃ y ≥ 0 with Aᵀy = 0 and bᵀy < 0.
    Given a claimed y, checking those three facts (exact ℚ) PROVES infeasibility — no search.
  • LP optimality (KKT / complementary slackness): (x*, y*) is optimal for max cᵀx s.t. A x ≤ b, x ≥ 0 iff
    x* primal-feasible, y* ≥ 0 dual-feasible (Aᵀy* ≥ c), complementary slackness, and cᵀx* = bᵀy* (strong
    duality). All exact-ℚ checks of a proposed pair.

★ certificate-or-DECLINE: a verdict is EXACT only when the re-checked certificate passes; otherwise DECLINE.
Exact rational arithmetic (Fraction) — never floats. Reuses the exact-LP family (mathmode/optimization).
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Sequence

import kernel_verdict as KV

Q = Fraction


def _q(M):
    return [[Q(x) for x in row] for row in M]


def _matT_vec(A: List[List[Q]], y: Sequence[Q]) -> List[Q]:
    """Aᵀ y  (columns of A dotted with y)."""
    cols = len(A[0]) if A else 0
    return [sum(A[i][j] * y[i] for i in range(len(A))) for j in range(cols)]


def verify_farkas_infeasible(A, b, y) -> KV.Verdict:
    """EXACT 'infeasible' iff the Farkas certificate y checks out: y ≥ 0, Aᵀy = 0, bᵀy < 0 (exact ℚ). Any failure
    ⇒ DECLINE (we never assert infeasibility without the witness). One matrix–vector product — Axis B."""
    A, b, y = _q(A), [Q(v) for v in b], [Q(v) for v in y]
    if len(y) != len(A) or len(b) != len(A):
        return KV.decline("farkas: dimension mismatch (y/b vs rows of A)", "farkas")
    if any(yi < 0 for yi in y):
        return KV.decline("farkas: certificate has a negative component (y ≥ 0 required)", "farkas")
    ATy = _matT_vec(A, y)
    if any(v != 0 for v in ATy):
        return KV.decline(f"farkas: Aᵀy ≠ 0 (got {ATy}) — not a valid infeasibility witness", "farkas")
    bTy = sum(b[i] * y[i] for i in range(len(b)))
    if not (bTy < 0):
        return KV.decline(f"farkas: bᵀy = {bTy} ≥ 0 — does not prove infeasibility", "farkas")
    cert = KV.Cert(KV.EXACT, "farkas_lemma", passed=True, check_cost="O(nm) one matvec",
                   detail=f"y≥0, Aᵀy=0, bᵀy={bTy}<0 ⇒ {{Ax≤b}} INFEASIBLE (Farkas)")
    return KV.exact({"feasible": False, "witness": [str(v) for v in y]}, "farkas", "O(nm)", cert)


def verify_lp_optimal(c, A, b, x, y) -> KV.Verdict:
    """EXACT 'optimal' iff (x,y) is a verified primal–dual optimal pair for max cᵀx s.t. Ax≤b, x≥0: x feasible,
    y≥0, Aᵀy≥c, complementary slackness yᵢ(Ax−b)ᵢ=0 and xⱼ(Aᵀy−c)ⱼ=0, and cᵀx=bᵀy (strong duality). Else DECLINE."""
    c = [Q(v) for v in c]; A = _q(A); b = [Q(v) for v in b]; x = [Q(v) for v in x]; y = [Q(v) for v in y]
    m, n = len(A), len(c)
    Ax = [sum(A[i][j] * x[j] for j in range(n)) for i in range(m)]
    if any(Ax[i] > b[i] for i in range(m)) or any(xj < 0 for xj in x):
        return KV.decline("lp: x is not primal-feasible (Ax≤b, x≥0)", "lp_kkt")
    if any(yi < 0 for yi in y):
        return KV.decline("lp: y has a negative component (dual y≥0 required)", "lp_kkt")
    ATy = _matT_vec(A, y)
    if any(ATy[j] < c[j] for j in range(n)):
        return KV.decline("lp: dual infeasible (Aᵀy ≥ c violated)", "lp_kkt")
    if any(y[i] * (Ax[i] - b[i]) != 0 for i in range(m)):
        return KV.decline("lp: complementary slackness yᵢ(Ax−b)ᵢ=0 violated", "lp_kkt")
    if any(x[j] * (ATy[j] - c[j]) != 0 for j in range(n)):
        return KV.decline("lp: complementary slackness xⱼ(Aᵀy−c)ⱼ=0 violated", "lp_kkt")
    cTx = sum(c[j] * x[j] for j in range(n)); bTy = sum(b[i] * y[i] for i in range(m))
    if cTx != bTy:
        return KV.decline(f"lp: strong duality cᵀx={cTx} ≠ bᵀy={bTy}", "lp_kkt")
    cert = KV.Cert(KV.EXACT, "lp_kkt", passed=True, check_cost="O(nm) checks",
                   detail=f"primal+dual feasible, complementary slackness, cᵀx=bᵀy={cTx} ⇒ OPTIMAL")
    return KV.exact({"optimal_value": str(cTx)}, "lp_kkt", "O(nm)", cert)


def adversarial_battery() -> dict:
    """★ a valid Farkas y ⇒ EXACT infeasible; ★ a bad y (Aᵀy≠0, or bᵀy≥0, or negative) ⇒ DECLINE; ★ a verified
    primal–dual pair ⇒ EXACT optimal; ★ a suboptimal pair (duality gap) ⇒ DECLINE."""
    # infeasible: x≥0 impossible with  x≤−1  i.e. {x ≤ -1, -x ≤ 0}? use {x≤-1 , -x≤-1}? Build a clean infeasible:
    #   x ≤ -1  and  -x ≤ -1   ⇒  x ≤ -1 and x ≥ 1 — infeasible. A=[[1],[-1]], b=[-1,-1]. Farkas y=[1,1]: Aᵀy=0, bᵀy=-2<0.
    A_inf, b_inf = [[1], [-1]], [-1, -1]
    good = verify_farkas_infeasible(A_inf, b_inf, [1, 1])
    bad_pos = verify_farkas_infeasible(A_inf, b_inf, [1, 0])          # Aᵀy = 1 ≠ 0 ⇒ DECLINE
    bad_neg = verify_farkas_infeasible(A_inf, b_inf, [-1, 1])         # negative component ⇒ DECLINE
    # LP: max x s.t. x ≤ 3, x ≥ 0 ⇒ optimal x=3, dual y=1 (Aᵀy=1≥c=1, cs ok, cᵀx=3=bᵀy)
    opt = verify_lp_optimal([1], [[1]], [3], [3], [1])
    subopt = verify_lp_optimal([1], [[1]], [3], [2], [1])            # cᵀx=2 ≠ bᵀy=3 ⇒ DECLINE
    cases = {
        "farkas_valid_infeasible_EXACT": good.status == "EXACT" and good.result["feasible"] is False,
        "farkas_bad_ATy_DECLINE": bad_pos.status == "DECLINE",
        "farkas_negative_DECLINE": bad_neg.status == "DECLINE",
        "lp_optimal_EXACT": opt.status == "EXACT" and opt.result["optimal_value"] == "3",
        "lp_suboptimal_DECLINE": subopt.status == "DECLINE",
        "exact_carries_cert": opt.certificate is not None and opt.certificate.passed,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
