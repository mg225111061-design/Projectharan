"""
§BM NEW-4 — finite Markov exact: stationary fold + detailed-balance + absorbing fundamental (closed-form m10).
================================================================================================================
  • stationary π (Axis A fold): solve πP = π, Σπ = 1 EXACTLY over ℚ — no power iteration. cert: re-check πP = π.
  • detailed balance (Axis B): πᵢPᵢⱼ = πⱼPⱼᵢ — a cheap reversibility certificate.
  • absorbing chain: fundamental matrix N = (I−Q)⁻¹ gives EXACT expected hitting times t = N·1.
★ certificate-or-DECLINE, exact Fraction arithmetic (never floats). zero-dep (stdlib).
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Optional, Sequence

import kernel_verdict as KV

Q = Fraction


def _solve(A: List[List[Q]], b: List[Q]) -> Optional[List[Q]]:
    """Exact ℚ Gaussian elimination for the square system A x = b; None if singular."""
    n = len(A)
    M = [[Q(A[i][j]) for j in range(n)] + [Q(b[i])] for i in range(n)]
    for c in range(n):
        piv = next((r for r in range(c, n) if M[r][c] != 0), None)
        if piv is None:
            return None
        M[c], M[piv] = M[piv], M[c]
        inv = M[c][c]
        M[c] = [v / inv for v in M[c]]
        for r in range(n):
            if r != c and M[r][c] != 0:
                f = M[r][c]
                M[r] = [M[r][j] - f * M[c][j] for j in range(n + 1)]
    return [M[i][n] for i in range(n)]


def stationary(P) -> KV.Verdict:
    """EXACT stationary distribution π (πP=π, Σπ=1) iff the re-check πP=π passes; else DECLINE (no unique π)."""
    n = len(P)
    Pq = [[Q(P[i][j]) for j in range(n)] for i in range(n)]
    # (Pᵀ − I) π = 0 with the last row replaced by Σπ = 1 (normalization)
    A = [[Pq[j][i] - (Q(1) if i == j else Q(0)) for j in range(n)] for i in range(n)]
    A[n - 1] = [Q(1)] * n
    b = [Q(0)] * (n - 1) + [Q(1)]
    pi = _solve(A, b)
    if pi is None or any(x < 0 for x in pi):
        return KV.decline("markov: no unique non-negative stationary distribution ⇒ DECLINE", "markov")
    # ★ re-check πP = π exactly
    lhs = [sum(pi[i] * Pq[i][j] for i in range(n)) for j in range(n)]
    if lhs != pi or sum(pi) != 1:
        return KV.decline("markov: stationary re-check πP=π failed ⇒ DECLINE", "markov")
    cert = KV.Cert(KV.EXACT, "stationary_recheck", passed=True, check_cost="O(n²) one vec-mat",
                   detail=f"πP=π verified exactly, Σπ=1; π={[str(x) for x in pi]}")
    return KV.exact({"pi": [str(x) for x in pi]}, "markov", "O(n³) solve", cert)


def detailed_balance(P, pi) -> KV.Verdict:
    """EXACT 'reversible' iff πᵢPᵢⱼ = πⱼPⱼᵢ for all i,j (re-checked); else DECLINE (not reversible)."""
    n = len(P)
    Pq = [[Q(P[i][j]) for j in range(n)] for i in range(n)]
    pq = [Q(x) for x in pi]
    ok = all(pq[i] * Pq[i][j] == pq[j] * Pq[j][i] for i in range(n) for j in range(n))
    if not ok:
        return KV.decline("markov: detailed balance πᵢPᵢⱼ=πⱼPⱼᵢ violated ⇒ NOT reversible ⇒ DECLINE", "markov")
    cert = KV.Cert(KV.EXACT, "detailed_balance", passed=True, check_cost="O(n²)",
                   detail="πᵢPᵢⱼ=πⱼPⱼᵢ ∀i,j ⇒ reversible chain")
    return KV.exact({"reversible": True}, "markov", "O(n²)", cert)


def absorbing_hitting(Qmat) -> KV.Verdict:
    """EXACT expected steps to absorption t = (I−Q)⁻¹·1 over ℚ iff (I−Q) is invertible (re-checked); else DECLINE."""
    m = len(Qmat)
    ImQ = [[(Q(1) if i == j else Q(0)) - Q(Qmat[i][j]) for j in range(m)] for i in range(m)]
    t = _solve(ImQ, [Q(1)] * m)
    if t is None or any(x < 0 for x in t):
        return KV.decline("markov: (I−Q) singular or negative hitting time ⇒ DECLINE", "markov")
    # re-check (I−Q) t = 1
    chk = [sum(ImQ[i][j] * t[j] for j in range(m)) for i in range(m)]
    if chk != [Q(1)] * m:
        return KV.decline("markov: absorbing re-check (I−Q)t=1 failed ⇒ DECLINE", "markov")
    cert = KV.Cert(KV.EXACT, "fundamental_recheck", passed=True, check_cost="O(m²)",
                   detail=f"(I−Q)t=1 verified; t={[str(x) for x in t]}")
    return KV.exact({"expected_steps": [str(x) for x in t]}, "markov", "O(m³)", cert)


def adversarial_battery() -> dict:
    """★ a 2-state chain's stationary π is solved + re-checked EXACT; ★ a reversible chain passes detailed balance,
    a non-reversible one DECLINEs; ★ an absorbing chain's expected hitting time is exact + re-checked."""
    P = [[Q(1, 2), Q(1, 2)], [Q(1, 4), Q(3, 4)]]      # stationary π = (1/3, 2/3)
    st = stationary(P)
    db_ok = detailed_balance(P, [Q(1, 3), Q(2, 3)])   # 2-state chains are always reversible
    # a 3-state non-reversible cycle 0→1→2→0
    Pc = [[0, 1, 0], [0, 0, 1], [1, 0, 0]]
    db_no = detailed_balance(Pc, [Q(1, 3)] * 3)
    # absorbing: one transient state with 1/2 self-loop, 1/2 absorb ⇒ expected steps 2
    hit = absorbing_hitting([[Q(1, 2)]])
    cases = {
        "stationary_exact": st.status == "EXACT" and st.result["pi"] == ["1/3", "2/3"],
        "detailed_balance_reversible": db_ok.status == "EXACT",
        "non_reversible_DECLINE": db_no.status == "DECLINE",
        "absorbing_hitting_2": hit.status == "EXACT" and hit.result["expected_steps"] == ["2"],
        "exact_carries_cert": st.certificate is not None and st.certificate.passed,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
