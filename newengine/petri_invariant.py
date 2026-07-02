"""
§BM NEW-2 — Petri-net place-invariant (cheap conservation-law certificate; conservation m05 branch, Axis B).
================================================================================================================
A place-invariant is a vector y with yᵀN = 0 (N = incidence matrix, places × transitions). Then for EVERY
reachable marking M from M₀:  yᵀM = yᵀM₀  (firing any transition adds yᵀ·(column) = 0). So if yᵀM₀ ≠ yᵀM_target
for some invariant y, M_target is provably UNREACHABLE — without exploring the (possibly infinite) state space.

★ Honest scope: this is a SUFFICIENT condition. General Petri reachability is Ackermann-hard — we never claim it;
when no separating invariant is found we DECLINE ("not proven unreachable", not "reachable"). certificate-or-
DECLINE: EXACT 'unreachable' only with a re-checked y (yᵀN=0 ∧ yᵀM₀≠yᵀM_target). Exact ℚ (Fraction), zero-dep.
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Sequence

import kernel_verdict as KV

Q = Fraction


def _nullspace(A: List[List[Q]]) -> List[List[Q]]:
    """Basis of { y : A y = 0 } over ℚ via RREF (A given as rows). Returns each basis vector (length = #cols)."""
    if not A:
        return []
    m, n = len(A), len(A[0])
    M = [[Q(x) for x in row] for row in A]
    pivots = []
    r = 0
    for c in range(n):
        piv = next((i for i in range(r, m) if M[i][c] != 0), None)
        if piv is None:
            continue
        M[r], M[piv] = M[piv], M[r]
        inv = M[r][c]
        M[r] = [v / inv for v in M[r]]
        for i in range(m):
            if i != r and M[i][c] != 0:
                f = M[i][c]
                M[i] = [M[i][j] - f * M[r][j] for j in range(n)]
        pivots.append(c)
        r += 1
        if r == m:
            break
    free = [c for c in range(n) if c not in pivots]
    basis = []
    for fcol in free:
        y = [Q(0)] * n
        y[fcol] = Q(1)
        for ri, pc in enumerate(pivots):
            y[pc] = -M[ri][fcol]
        basis.append(y)
    return basis


def _scale_int(y: List[Q]) -> List[int]:
    """Scale a rational vector to coprime integers (LCM of denominators), for a clean integer invariant."""
    from math import gcd
    den = 1
    for v in y:
        den = den * v.denominator // gcd(den, v.denominator)
    ints = [int(v * den) for v in y]
    g = 0
    for v in ints:
        g = gcd(g, abs(v))
    return [v // g for v in ints] if g else ints


def place_invariants(N: List[List[int]]) -> List[List[int]]:
    """Integer place-invariants y (yᵀN=0) — the left null space of the incidence matrix N (places × transitions)."""
    if not N:
        return []
    NT = [[Q(N[p][t]) for p in range(len(N))] for t in range(len(N[0]))]   # transpose: transitions × places
    return [_scale_int(y) for y in _nullspace(NT)]


def unreachable_cert(N, M0, Mtarget) -> KV.Verdict:
    """EXACT 'unreachable' iff some place-invariant separates M₀ and M_target (yᵀN=0 ∧ yᵀM₀≠yᵀM_target,
    re-checked). Else DECLINE — NOT proven unreachable (general reachability is Ackermann-hard; we never claim it)."""
    for y in place_invariants(N):
        yN = [sum(y[p] * N[p][t] for p in range(len(N))) for t in range(len(N[0]))]
        if any(v != 0 for v in yN):                                  # defensive: must be a true invariant
            continue
        s0 = sum(y[p] * M0[p] for p in range(len(M0)))
        st = sum(y[p] * Mtarget[p] for p in range(len(Mtarget)))
        if s0 != st:
            cert = KV.Cert(KV.EXACT, "place_invariant", passed=True, check_cost="O(P·T) one matvec",
                           detail=f"invariant y={y}: yᵀM₀={s0} ≠ yᵀM_target={st} ⇒ UNREACHABLE (token-sum preserved)")
            return KV.exact({"reachable": False, "invariant": y}, "petri_invariant", "O(P·T)", cert)
    return KV.decline("petri: no separating place-invariant found ⇒ NOT PROVEN unreachable (general reachability is "
                      "Ackermann-hard — we do not claim reachable either)", "petri_invariant")


def adversarial_battery() -> dict:
    """★ a producer/consumer net with a conserved token-sum proves an over-budget marking UNREACHABLE (EXACT cert);
    ★ a reachable target ⇒ DECLINE (honest: no separating invariant, not a false 'reachable'); ★ the certificate
    is a re-checked place-invariant."""
    # 2 places, 1 transition that moves a token p0→p1: N[p][t] = -1 (p0), +1 (p1). Invariant y=[1,1] (sum conserved).
    N = [[-1], [1]]
    M0 = [1, 0]
    unreach = unreachable_cert(N, M0, [1, 1])        # total tokens 2 ≠ 1 ⇒ unreachable (EXACT)
    reach = unreachable_cert(N, M0, [0, 1])          # total tokens 1 = 1 ⇒ no separating invariant ⇒ DECLINE
    invs = place_invariants(N)
    cases = {
        "conserved_sum_invariant": any(y == [1, 1] or y == [-1, -1] for y in invs),
        "over_budget_unreachable_EXACT": unreach.status == "EXACT" and unreach.result["reachable"] is False,
        "reachable_target_DECLINE": reach.status == "DECLINE",          # ★ never a false 'reachable'
        "exact_carries_invariant_cert": unreach.certificate is not None and unreach.certificate.passed,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
