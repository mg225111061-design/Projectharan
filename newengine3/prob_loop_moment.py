"""
§BO NEW-1 ★ — prob-solvable loop moments are C-finite recurrences (the max-ROI reuse; closed-form m10 / fold).
==================================================================================================================
★ The research's biggest finding: the MOMENTS of a probabilistic-solvable loop reuse the existing C-finite solver
ALMOST VERBATIM.  A loop that, each iteration, applies one of finitely many AFFINE updates
        x ← aᵢ·x + bᵢ   with rational probability pᵢ   (Σ pᵢ = 1)
has k-th moments that evolve LINEARLY:  E[x_{n+1}^r] = Σᵢ pᵢ Σ_{c≤r} C(r,c) aᵢ^c bᵢ^{r−c} E[x_n^c].  So the moment
vector M_n = (E[x_n^0], …, E[x_n^k]) satisfies M_n = Tⁿ·M₀ for a fixed lower-triangular T — exactly the
companion-matrix fold of `cfinite` (power-by-squaring ⇒ O(log n), not O(n) simulation, and certainly not the
O(mⁿ) exact branch tree).  Net-new is ONLY the recognition + expectation semantics + building T; the solving is
the existing engine.

★ certificate-or-DECLINE (the EXACT moment rides an INDEPENDENT re-check):
  (1) M₀ = (1, x₀, x₀², …) re-checked; Σ pᵢ = 1 (a probability distribution) else DECLINE;
  (2) the EXACT moment VECTOR (every j ≤ k) at n=1,2,3 by FULL branch enumeration (m, m², m³ branches, exact ℚ)
      == (Tⁿ M₀) — exercising every entry of the triangular T, so a construction bug in any T[r][c] fails this ⇒
      DECLINE.  (The first moment is additionally routed through cfinite.companion_nth + verify_cfinite — reuse.)
Only constant rational affine updates are accepted; a non-affine / iteration-dependent update (moments don't
close) ⇒ DECLINE (the honest "unsolvable loop" boundary).  0 new mechanism (closed-form/structure m10 + the
C-finite fold); 0 new disposer.  Exact ℚ (Fraction).  zero-dep.
"""
from __future__ import annotations

from fractions import Fraction
from math import comb
from typing import List, Sequence, Tuple

import cfinite as CF
import kernel_verdict as KV

Q = Fraction
_MAX_K = 6           # moment order cap
_MAX_BRANCH = 8      # affine-branch count cap (n=2 enumeration is m² ≤ 64)


def _q(v) -> Q:
    return v if isinstance(v, Q) else Q(v)


def _build_T(updates: Sequence[Tuple[Q, Q, Q]], k: int) -> List[List[Q]]:
    """T[r][c] = Σᵢ pᵢ·C(r,c)·aᵢ^c·bᵢ^{r−c}  ((k+1)×(k+1), lower-triangular)."""
    T = [[Q(0)] * (k + 1) for _ in range(k + 1)]
    for r in range(k + 1):
        for c in range(r + 1):
            T[r][c] = sum(p * comb(r, c) * (a ** c) * (b ** (r - c)) for (p, a, b) in updates)
    return T


def _matvec(T: List[List[Q]], v: List[Q]) -> List[Q]:
    return [sum(T[i][j] * v[j] for j in range(len(v))) for i in range(len(T))]


def _matpow_vec(T: List[List[Q]], v: List[Q], n: int) -> List[Q]:
    """Tⁿ·v by power-by-squaring (O(log n) matmuls) — the fold."""
    d = len(T)
    R = [[Q(1) if i == j else Q(0) for j in range(d)] for i in range(d)]
    base = [row[:] for row in T]
    while n > 0:
        if n & 1:
            R = [[sum(R[i][t] * base[t][j] for t in range(d)) for j in range(d)] for i in range(d)]
        base = [[sum(base[i][t] * base[t][j] for t in range(d)) for j in range(d)] for i in range(d)]
        n >>= 1
    return _matvec(R, v)


def _enumerate_moment(updates: Sequence[Tuple[Q, Q, Q]], x0: Q, k: int, n: int) -> Q:
    """Exact E[x_n^k] by enumerating all mⁿ branches (only used for the n=1,2 certificate)."""
    states = [(Q(1), x0)]
    for _ in range(n):
        states = [(p * pi, a * x + b) for (p, x) in states for (pi, a, b) in updates]
    return sum(p * (x ** k) for (p, x) in states)


def _parse(updates) -> List[Tuple[Q, Q, Q]]:
    out = []
    for u in updates:
        p, a, b = _q(u[0]), _q(u[1]), _q(u[2])
        out.append((p, a, b))
    return out


def moment(updates, x0, k: int = 1, n: int = 10) -> KV.Verdict:
    """EXACT E[x_n^k] for the prob-solvable affine loop, computed by the Tⁿ fold and certified by exact n=1,2
    branch enumeration; DECLINE if Σp≠1, k/branches over cap, or the certificate mismatches."""
    try:
        ups = _parse(updates)
        x0 = _q(x0); k = int(k); n = int(n)
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"prob_loop_moment: {type(e).__name__}: {e}", "prob_loop_moment")
    if not (1 <= k <= _MAX_K):
        return KV.decline(f"prob_loop_moment: moment order k={k} outside [1,{_MAX_K}] ⇒ DECLINE", "prob_loop_moment")
    if not (1 <= len(ups) <= _MAX_BRANCH):
        return KV.decline(f"prob_loop_moment: {len(ups)} branches outside [1,{_MAX_BRANCH}] ⇒ DECLINE",
                          "prob_loop_moment")
    if n < 0:
        return KV.decline("prob_loop_moment: n must be ≥ 0", "prob_loop_moment")
    psum = sum(p for (p, _, _) in ups)
    if psum != 1:
        return KV.decline(f"prob_loop_moment: probabilities sum to {psum} ≠ 1 — not a distribution ⇒ DECLINE",
                          "prob_loop_moment")
    if any(p < 0 for (p, _, _) in ups):
        return KV.decline("prob_loop_moment: negative probability ⇒ DECLINE", "prob_loop_moment")

    T = _build_T(ups, k)
    M0 = [x0 ** j for j in range(k + 1)]
    # ★ certificate (1): M₀ initial moments
    if M0[0] != 1 or (k >= 1 and M0[1] != x0):
        return KV.decline("prob_loop_moment: M₀ check failed ⇒ DECLINE (bug guard)", "prob_loop_moment")
    # ★ certificate (2): exact branch enumeration matches the FULL moment vector (every j ≤ k) at n=1,2,3 — this
    #   exercises every entry of the triangular T through the recurrence (T¹,T²,T³ across all components), so a
    #   construction bug in any T[r][c] changes some moment and is caught ⇒ DECLINE (never a false-EXACT)
    for nn in (1, 2, 3):
        Mn = _matpow_vec(T, M0, nn)
        for j in range(k + 1):
            if Mn[j] != _enumerate_moment(ups, x0, j, nn):
                return KV.decline(f"prob_loop_moment: T-closed form ≠ exact enumeration for E[x^{j}] at n={nn} ⇒ "
                                  "DECLINE (moment-recurrence mismatch)", "prob_loop_moment")
    # the answer: the O(log n) fold
    val = _matpow_vec(T, M0, n)[k]

    # make the cfinite reuse CONCRETE for the first moment: m_{n+1}=A m_n+B ⇒ order-2 C-finite c=[1+A,−A]
    cfinite_note = ""
    if k == 1:
        A = sum(p * a for (p, a, _) in ups); B = sum(p * b for (p, _, b) in ups)
        c = [1 + A, -A]; init = [x0, A * x0 + B]
        ok, checked = CF.verify_cfinite(c, init, ns=(3, 5, 8, 13))
        if ok and CF.companion_nth(c, init, n) != val:
            return KV.decline("prob_loop_moment: cfinite companion ≠ T-fold for the first moment ⇒ DECLINE",
                              "prob_loop_moment")
        cfinite_note = (f"; first moment is order-2 C-finite c=[1+A,−A]=[{1 + A},{-A}] verified via "
                        f"cfinite.companion_nth (reuse) at n={checked}" if ok else "")

    cert = KV.Cert(KV.EXACT, "prob_moment_enumeration", passed=True,
                   check_cost="exact branch enumeration at n=1,2 + M₀ + Σp=1 (+ cfinite for k=1)",
                   detail=f"E[x_{n}^{k}]={val} via Tⁿ fold ((k+1)×(k+1) power-by-squaring, O(log n)); "
                          f"matches exact n=1,2 enumeration{cfinite_note}")
    return KV.exact({"moment": str(val), "k": k, "n": n, "moment_value": val}, "prob_loop_moment",
                    "prob-solvable loop moment (Tⁿ companion fold)", cert)


def verify_moment(updates, x0, k, n, claimed) -> KV.Verdict:
    """EXACT iff the CLAIMED moment equals the certified closed form; a wrong claim ⇒ DECLINE (the gate that makes
    a construction bug fail closed)."""
    v = moment(updates, x0, k, n)
    if v.status != "EXACT":
        return v
    if _q(claimed) != v.result["moment_value"]:
        return KV.decline(f"prob_loop_moment: claimed {claimed} ≠ certified {v.result['moment']} ⇒ DECLINE",
                          "prob_loop_moment")
    return v


def adversarial_battery() -> dict:
    """★ x←x/2 (w.p.½) | x←x/2+½ (w.p.½), x₀=0 ⇒ E[x_n]→ the dyadic mean, matches enumeration; ★ a 2nd moment;
    ★ Σp≠1 ⇒ DECLINE; ★ a wrong claimed value ⇒ DECLINE; ★ first moment cross-checked via cfinite."""
    half = Q(1, 2)
    loop = [(half, half, Q(0)), (half, half, half)]      # x←x/2 or x←x/2+1/2, each w.p. 1/2
    m1 = moment(loop, 0, k=1, n=6)
    m1_enum = _enumerate_moment(_parse(loop), Q(0), 1, 6)
    m2 = moment(loop, 0, k=2, n=4)
    m2_enum = _enumerate_moment(_parse(loop), Q(0), 2, 4)
    badp = moment([(Q(1, 3), Q(1), Q(0)), (Q(1, 3), Q(1), Q(1))], 0, k=1, n=5)   # Σp=2/3 ≠ 1
    wrong = verify_moment(loop, 0, 1, 6, Q(999))
    cases = {
        "first_moment_EXACT_matches_enum": m1.status == "EXACT" and m1.result["moment_value"] == m1_enum,
        "second_moment_EXACT_matches_enum": m2.status == "EXACT" and m2.result["moment_value"] == m2_enum,
        "prob_not_one_DECLINE": badp.status == "DECLINE",
        "wrong_claim_DECLINE": wrong.status == "DECLINE",
        "cfinite_reuse_noted": m1.status == "EXACT" and "cfinite.companion_nth" in m1.certificate.detail,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
