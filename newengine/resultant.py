"""
§BM NEW-11 — resultant via the Sylvester determinant (ring theory; complete-invariant m09 branch, Axis B).
================================================================================================================
The resultant Res(p,q) = det(Sylvester(p,q)) vanishes iff p,q share a root (over an algebraically closed field) /
a non-constant common factor (over a field). Expensive root-finding is replaced by one determinant + a cheap
cross-check. ★ certificate-or-DECLINE: EXACT iff the resultant's vanishing AGREES with an INDEPENDENT gcd
computation [Res=0 ⟺ deg(gcd)≥1] (the re-checked certificate); a disagreement ⇒ DECLINE. Exact ℚ, zero-dep.

★ Honest scope: submodular MAXIMIZATION (NP-hard) is NOT attempted; matroid/greedy + submodular MINIMIZATION are
deferred to the next tranche (documented in NEWENGINE_INDEX) under the certificate-or-DECLINE discipline.
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Sequence

import kernel_verdict as KV

Q = Fraction


def _deg(p: List[Q]) -> int:
    d = len(p) - 1
    while d > 0 and p[d] == 0:
        d -= 1
    return d


def _det(M: List[List[Q]]) -> Q:
    n = len(M)
    A = [[Q(x) for x in row] for row in M]
    det = Q(1)
    for c in range(n):
        piv = next((r for r in range(c, n) if A[r][c] != 0), None)
        if piv is None:
            return Q(0)
        if piv != c:
            A[c], A[piv] = A[piv], A[c]
            det = -det
        det *= A[c][c]
        inv = A[c][c]
        for r in range(c + 1, n):
            if A[r][c] != 0:
                f = A[r][c] / inv
                A[r] = [A[r][j] - f * A[c][j] for j in range(n)]
    return det


def _sylvester(p: List[Q], q: List[Q]) -> List[List[Q]]:
    """Sylvester matrix of p (deg m) and q (deg n): size (m+n). Coeffs given low→high; rows use high→low."""
    m, n = _deg(p), _deg(q)
    pc = [p[i] for i in range(m + 1)][::-1]              # high→low
    qc = [q[i] for i in range(n + 1)][::-1]
    size = m + n
    M = [[Q(0)] * size for _ in range(size)]
    for r in range(n):                                   # n rows of p-coeffs, each shifted
        for j in range(len(pc)):
            M[r][r + j] = pc[j]
    for r in range(m):                                   # m rows of q-coeffs
        for j in range(len(qc)):
            M[n + r][r + j] = qc[j]
    return M


def _poly_gcd(p: List[Q], q: List[Q]) -> List[Q]:
    """Euclidean gcd over ℚ; returns the (monic) gcd coefficient list low→high."""
    a = [Q(x) for x in p[:_deg(p) + 1]]
    b = [Q(x) for x in q[:_deg(q) + 1]]
    while _deg(b) > 0 or (len(b) == 1 and b[0] != 0) or any(v != 0 for v in b):
        # polynomial remainder a mod b
        a, b = b, _poly_mod(a, b)
        if all(v == 0 for v in b):
            break
    d = _deg(a)
    lead = a[d]
    return [a[i] / lead for i in range(d + 1)] if lead != 0 else [Q(0)]


def _poly_mod(a: List[Q], b: List[Q]) -> List[Q]:
    a = [Q(x) for x in a]
    db = _deg(b)
    while _deg(a) >= db and any(v != 0 for v in a):
        da = _deg(a)
        if a[da] == 0:
            break
        f = a[da] / b[db]
        for i in range(db + 1):
            a[da - db + i] -= f * b[i]
        a = a[:da] + [Q(0)]                              # drop the now-zero leading term
    return a[:db] if db > 0 else [Q(0)]


def resultant(p: Sequence, q: Sequence) -> KV.Verdict:
    """EXACT Res(p,q)=det(Sylvester) with the vanishing re-checked against gcd: Res=0 ⟺ deg(gcd)≥1. DECLINE on
    disagreement (a guard against a determinant bug producing a false 'coprime'/'common-root')."""
    p = [Q(x) for x in p]; q = [Q(x) for x in q]
    if _deg(p) < 1 and _deg(q) < 1:
        return KV.decline("resultant: both inputs constant ⇒ DECLINE", "resultant")
    res = _det(_sylvester(p, q))
    g = _poly_gcd(p, q)
    common = _deg(g) >= 1
    if (res == 0) != common:
        return KV.decline(f"resultant: Res=0?{res == 0} disagrees with gcd-common?{common} ⇒ DECLINE", "resultant")
    cert = KV.Cert(KV.EXACT, "sylvester_gcd_recheck", passed=True, check_cost="O((m+n)³) det + O(·) gcd",
                   detail=f"Res={res}; (Res=0)⟺(deg gcd≥1)={common} re-checked ⇒ {'share a factor' if common else 'coprime'}")
    return KV.exact({"resultant": str(res), "share_common_factor": common}, "resultant", "O((m+n)³)", cert)


def adversarial_battery() -> dict:
    """★ (x−1)(x−2) and (x−2)(x−3) share (x−2) ⇒ Res=0, gcd non-constant (EXACT, agree); ★ (x−1) and (x−2)
    coprime ⇒ Res≠0, gcd constant (EXACT, agree); ★ the gcd cross-check is the certificate."""
    # p=(x-1)(x-2)=x²-3x+2 → [2,-3,1]; q=(x-2)(x-3)=x²-5x+6 → [6,-5,1]; share (x-2)
    share = resultant([2, -3, 1], [6, -5, 1])
    # p=x-1 → [-1,1]; q=x-2 → [-2,1]; coprime
    coprime = resultant([-1, 1], [-2, 1])
    cases = {
        "common_factor_res_zero": share.status == "EXACT" and share.result["share_common_factor"] is True
            and share.result["resultant"] == "0",
        "coprime_res_nonzero": coprime.status == "EXACT" and coprime.result["share_common_factor"] is False
            and coprime.result["resultant"] != "0",
        "exact_carries_cert": share.certificate is not None and share.certificate.passed,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
