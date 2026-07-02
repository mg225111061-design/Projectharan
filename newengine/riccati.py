"""
§BM NEW-14 — algebraic Riccati (CARE) residual certificate (guess-and-certify m03 branch).
================================================================================================================
The continuous-time algebraic Riccati equation AᵀP + PA − PBR⁻¹BᵀP + Q = 0 (LQR) is solved by whatever proposer
you like (Schur, Newton, symbolic), then CERTIFIED by the residual. ★ The directive's hard rule: a numeric Schur
solve ALONE is forbidden — the residual grows with order and silently fails. So EXACT is granted ONLY when the
residual is EXACTLY zero over ℚ (a symbolic/rational P, re-checked); a nonzero residual ⇒ DECLINE (never a faked
EXACT). A numeric P with small-but-nonzero residual is reported as an approximation WITH its residual bound, never
EXACT. zero-dep (stdlib Fraction).
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Optional, Sequence

import kernel_verdict as KV

Q = Fraction


def _mm(A, B):
    n, m, p = len(A), len(B), len(B[0])
    return [[sum(A[i][k] * B[k][j] for k in range(m)) for j in range(p)] for i in range(n)]


def _T(A):
    return [[A[j][i] for j in range(len(A))] for i in range(len(A[0]))]


def _add(*Ms):
    n, m = len(Ms[0]), len(Ms[0][0])
    return [[sum(M[i][j] for M in Ms) for j in range(m)] for i in range(n)]


def _neg(A):
    return [[-A[i][j] for j in range(len(A[0]))] for i in range(len(A))]


def _inv1(R):
    """Inverse of a 1×1 (scalar) R over ℚ (the common SISO case kept exact)."""
    return [[Q(1) / Q(R[0][0])]]


def verify_care(A, B, Q_, R, P) -> KV.Verdict:
    """EXACT iff the residual AᵀP+PA−PBR⁻¹BᵀP+Q is EXACTLY the zero matrix over ℚ (re-checked). A nonzero residual
    ⇒ DECLINE with the residual reported (numeric-alone is never accepted). Requires R 1×1 (exact R⁻¹)."""
    A = [[Q(x) for x in r] for r in A]; B = [[Q(x) for x in r] for r in B]
    Qm = [[Q(x) for x in r] for r in Q_]; P = [[Q(x) for x in r] for r in P]
    if len(R) != 1 or len(R[0]) != 1 or R[0][0] == 0:
        return KV.decline("riccati: only 1×1 R supported with exact R⁻¹ (zero-dep) ⇒ DECLINE otherwise", "riccati")
    Rinv = _inv1(R)
    AtP = _mm(_T(A), P)
    PA = _mm(P, A)
    PB = _mm(P, B)
    PBRinv = _mm(PB, Rinv)
    PBRinvBtP = _mm(PBRinv, _mm(_T(B), P))
    resid = _add(AtP, PA, _neg(PBRinvBtP), Qm)
    norm = sum(abs(resid[i][j]) for i in range(len(resid)) for j in range(len(resid[0])))
    if norm != 0:
        return KV.decline(f"riccati: residual ‖AᵀP+PA−PBR⁻¹BᵀP+Q‖₁ = {norm} ≠ 0 ⇒ DECLINE (numeric-alone forbidden)",
                          "riccati")
    cert = KV.Cert(KV.EXACT, "care_residual", passed=True, check_cost="O(n³) exact ℚ residual",
                   detail="AᵀP+PA−PBR⁻¹BᵀP+Q = 0 exactly (re-checked over ℚ) ⇒ P solves the CARE")
    return KV.exact({"solves_care": True}, "riccati", "O(n³)", cert)


def adversarial_battery() -> dict:
    """★ the scalar CARE a=0,b=1,q=1,r=1 ⇒ P=1 verifies (residual 0, EXACT); ★ a wrong P (P=2) ⇒ nonzero residual
    ⇒ DECLINE (numeric-alone never faked EXACT); ★ the residual is the certificate."""
    A, B, Qm, R = [[0]], [[1]], [[1]], [[1]]
    good = verify_care(A, B, Qm, R, [[1]])               # 0+0-1+1 = 0 ✓
    bad = verify_care(A, B, Qm, R, [[2]])                # 0+0-4+1 = -3 ≠ 0 ⇒ DECLINE
    # a 2×2 with P known exactly: A=0, B=I-col? keep SISO for exact R⁻¹. Use a=−1: 2(−1)P − P² + 1 = 0 ⇒ P²+2P−1=0
    # ⇒ P=−1+√2 (irrational) ⇒ not exact ℚ ⇒ a rational guess must DECLINE (honest).
    irr = verify_care([[-1]], [[1]], [[1]], [[1]], [[Fraction(414, 1000)]])   # ≈√2−1 but not exact ⇒ DECLINE
    cases = {
        "exact_P_solves_EXACT": good.status == "EXACT" and good.result["solves_care"] is True,
        "wrong_P_DECLINE": bad.status == "DECLINE",
        "irrational_rational_guess_DECLINE": irr.status == "DECLINE",     # ★ numeric-alone never faked EXACT
        "exact_carries_cert": good.certificate is not None and good.certificate.passed,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
