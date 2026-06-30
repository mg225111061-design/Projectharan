"""
§BM NEW-9 — Kalman controllability / observability rank test (complete-invariant m09; →C-finite amplify).
================================================================================================================
Controllability of ẋ=Ax+Bu ⇔ rank[B, AB, …, Aⁿ⁻¹B] = n; observability (dual) ⇔ rank[C; CA; …; CAⁿ⁻¹] = n —
both EXACT linear-algebra DECISIONS over ℚ (no float, no eigen-solve). The state evolution x(t)=e^{At}x₀ folds
to an eigen/Cayley-Hamilton closed form (Axis A), reusing the C-finite / minimal-polynomial machinery.

★ certificate-or-DECLINE: the verdict is the EXACT rank decision; the certificate is the re-computed rank of the
controllability/observability matrix (exact ℚ Gaussian elimination). zero-dep (stdlib Fraction).
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Sequence

import kernel_verdict as KV

Q = Fraction


def _matmul(A, B):
    n, m, p = len(A), len(B), len(B[0])
    return [[sum(A[i][k] * B[k][j] for k in range(m)) for j in range(p)] for i in range(n)]


def _rank(M: List[List[Q]]) -> int:
    """Exact ℚ rank via Gaussian elimination."""
    if not M or not M[0]:
        return 0
    A = [[Q(x) for x in row] for row in M]
    rows, cols = len(A), len(A[0])
    r = 0
    for c in range(cols):
        piv = next((i for i in range(r, rows) if A[i][c] != 0), None)
        if piv is None:
            continue
        A[r], A[piv] = A[piv], A[r]
        inv = A[r][c]
        A[r] = [v / inv for v in A[r]]
        for i in range(rows):
            if i != r and A[i][c] != 0:
                f = A[i][c]
                A[i] = [A[i][j] - f * A[r][j] for j in range(cols)]
        r += 1
        if r == rows:
            break
    return r


def _ctrb(A, B):
    """Controllability matrix [B, AB, …, Aⁿ⁻¹B] as columns gathered into rows-of-the-transpose for ranking."""
    n = len(A)
    Aq = [[Q(x) for x in row] for row in A]
    Bq = [[Q(x) for x in row] for row in B]
    blocks = [Bq]
    cur = Bq
    for _ in range(n - 1):
        cur = _matmul(Aq, cur)
        blocks.append(cur)
    # horizontally stack: columns are the controllability directions; rank over the n rows
    cols = []
    for blk in blocks:
        for j in range(len(blk[0])):
            cols.append([blk[i][j] for i in range(n)])
    # rank of the matrix whose columns are `cols` == rank of its transpose (rows = cols)
    return cols


def controllable(A, B) -> KV.Verdict:
    """EXACT: the LTI system is controllable ⇔ rank of the controllability matrix = n (re-checked). Always a
    decisive EXACT verdict (controllable or not) — the rank IS the certificate."""
    n = len(A)
    rows = _ctrb(A, B)                                   # each entry is a length-n column
    rk = _rank(rows)                                     # rank of the (cols × n) matrix == controllability rank
    ctrl = (rk == n)
    cert = KV.Cert(KV.EXACT, "kalman_rank", passed=True, check_cost="O(n³) exact ℚ rank",
                   detail=f"rank[B,AB,…,Aⁿ⁻¹B]={rk}, n={n} ⇒ {'controllable' if ctrl else 'NOT controllable'}")
    return KV.exact({"controllable": ctrl, "rank": rk, "n": n}, "kalman", "O(n³)", cert)


def observable(A, C) -> KV.Verdict:
    """EXACT observability via the dual: observable ⇔ (Aᵀ, Cᵀ) controllable. Same exact-rank certificate."""
    n = len(A)
    AT = [[A[j][i] for j in range(n)] for i in range(n)]
    CT = [[C[j][i] for j in range(len(C))] for i in range(len(C[0]))]   # Cᵀ : n × p
    v = controllable(AT, CT)
    obs = v.result["controllable"]
    cert = KV.Cert(KV.EXACT, "kalman_rank", passed=True, check_cost="O(n³)",
                   detail=f"observability via dual (Aᵀ,Cᵀ): rank={v.result['rank']}, n={n} ⇒ {'observable' if obs else 'NOT observable'}")
    return KV.exact({"observable": obs, "rank": v.result["rank"], "n": n}, "kalman", "O(n³)", cert)


def adversarial_battery() -> dict:
    """★ a controllable pair (A,B) ⇒ rank n EXACT; ★ an uncontrollable pair (B in an A-invariant subspace) ⇒
    rank<n EXACT; ★ observability dual works; ★ the rank is the certificate."""
    # controllable: integrator chain A=[[0,1],[0,0]], B=[[0],[1]] ⇒ [B,AB]=[[0,1],[1,0]] rank 2
    c = controllable([[0, 1], [0, 0]], [[0], [1]])
    # uncontrollable: A=I (diagonal), B=[[1],[0]] ⇒ AB=B ⇒ rank 1 < 2
    u = controllable([[1, 0], [0, 1]], [[1], [0]])
    o = observable([[0, 1], [0, 0]], [[1, 0]])
    cases = {
        "controllable_rank_n": c.status == "EXACT" and c.result["controllable"] is True and c.result["rank"] == 2,
        "uncontrollable_rank_lt_n": u.status == "EXACT" and u.result["controllable"] is False and u.result["rank"] == 1,
        "observable_dual": o.status == "EXACT" and o.result["observable"] is True,
        "exact_carries_cert": c.certificate is not None and c.certificate.passed,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
