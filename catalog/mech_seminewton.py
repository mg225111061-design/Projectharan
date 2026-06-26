"""
POST-CONSOLIDATION PHASE 1d — SEMIRING-NEWTON FIXPOINT (Esparza–Kiefer–Luttenberger), the Jacobian-accelerated lfp.
=================================================================================================================
Newton's method generalizes to ω-continuous semirings: to solve X = F(X) (a polynomial system) one linearizes via
the semiring JACOBIAN J_F and solves the linear system at each step. On COMMUTATIVE IDEMPOTENT (absorptive)
semirings the Newton sequence reaches the LEAST FIXPOINT in ≤ n steps (n = #variables) — and for a LINEAR system in
ONE step (the Kleene-star solve A*⊗b) — whereas naive Kleene iteration X_{k+1}=F(X_k) climbs the chain one rung at a
time (up to n, or unbounded on non-idempotent semirings). Implemented here on the tropical (min,+) semiring.

★ THE HONEST ADJUDICATION (four gates — this candidate DEMOTES):
  gate 2 (z3-closed): ✓ — the certificate is the EXACT semiring re-substitution F(μ)=μ (LRA over ℚ); plus an
      INDEPENDENT Kleene-fixpoint cross-check oracle (a recurrence bug ⇒ mismatch ⇒ DECLINE, never a wrong answer).
  gate 3 (asymptotic): ✓ — Newton ≤ n steps (1 for linear) vs Kleene's n ⇒ a real iteration-count win.
  gate 4 (dependency-free): ✓ — in-repo tropical algebra + Floyd–Warshall star (Fraction only).
  gate 1 (DISTINCT IN KIND): ✗ — Newton computes the SAME object as M13's Kleene: the LEAST FIXPOINT of X=F(X)
      over the semiring (cert kind d. semiring / fixpoint). It is a FASTER SOLVER for M13's fixpoint, not a new kind
      of certificate. ⇒ DEMOTE: a FACE of M13 (parent mechanism 13; the Jacobian-Newton acceleration of the lfp).

Absorptive island: non-negative weights ⇒ a finite lfp, reached in ≤ n Newton steps. A NEGATIVE CYCLE
(non-absorptive ⇒ lfp = −∞) ⇒ DECLINE (no finite least fixpoint). Precision 1.0.
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Optional, Sequence, Tuple

import kernel_verdict as KV

PARENT_MECHANISM = 13   # the least-fixpoint object is M13's (Kleene/semiring); Newton is a faster solver

INF = None              # the tropical additive identity 0̄ = +∞
ONE = Fraction(0)       # the tropical multiplicative identity 1̄ = 0
Trop = Optional[Fraction]
Monomial = Tuple[Fraction, Tuple[int, ...]]    # (coeff, variable indices); () = constant, (j,) = linear, (j,k) = quadratic


def oplus(a: Trop, b: Trop) -> Trop:
    if a is INF:
        return b
    if b is INF:
        return a
    return a if a <= b else b


def otimes(a: Trop, b: Trop) -> Trop:
    if a is INF or b is INF:
        return INF
    return a + b


def _eval_mon(mon: Monomial, x: Sequence[Trop]) -> Trop:
    val = mon[0]
    for v in mon[1]:
        val = otimes(val, x[v])
    return val


def F(system: List[List[Monomial]], x: Sequence[Trop]) -> List[Trop]:
    out: List[Trop] = []
    for eq in system:
        acc: Trop = INF
        for mon in eq:
            acc = oplus(acc, _eval_mon(mon, x))
        out.append(acc)
    return out


def kleene_lfp(system: List[List[Monomial]], n: int, max_iter: int = None) -> Tuple[Optional[List[Trop]], int]:
    """The INDEPENDENT oracle: Kleene iteration X_{k+1}=F(X_k) from 0̄ to the least fixpoint. Returns (lfp, steps),
    or (None, steps) if it fails to stabilize (e.g. a negative cycle drives it down forever)."""
    max_iter = max_iter or (4 * n + 8)
    x: List[Trop] = [INF] * n
    for step in range(1, max_iter + 1):
        nx = F(system, x)
        if nx == x:
            return x, step - 1
        x = nx
    return None, max_iter                                       # did not stabilize ⇒ no finite lfp (negative cycle)


def star(M: List[List[Trop]], n: int) -> Tuple[Optional[List[List[Trop]]], bool]:
    """Tropical matrix star A* = I ⊕ A ⊕ A² ⊕ … via Floyd–Warshall. Returns (A*, neg_cycle). A negative diagonal
    after the closure is a negative cycle ⇒ no finite star."""
    A = [[M[i][j] for j in range(n)] for i in range(n)]
    for k in range(n):
        for i in range(n):
            if A[i][k] is INF:
                continue
            for j in range(n):
                A[i][j] = oplus(A[i][j], otimes(A[i][k], A[k][j]))
    for i in range(n):
        if A[i][i] is not INF and A[i][i] < 0:
            return None, True                                  # negative cycle
        A[i][i] = oplus(A[i][i], ONE)                          # add the identity
    return A, False


def _matvec(M: List[List[Trop]], v: Sequence[Trop], n: int) -> List[Trop]:
    return [_reduce_oplus([otimes(M[i][j], v[j]) for j in range(n)]) for i in range(n)]


def _reduce_oplus(vals) -> Trop:
    acc: Trop = INF
    for v in vals:
        acc = oplus(acc, v)
    return acc


def jacobian(system: List[List[Monomial]], nu: Sequence[Trop], n: int) -> List[List[Trop]]:
    """The semiring JACOBIAN J_F(ν): J[i][j] = ⊕ over monomials of eq i, over each occurrence of variable j, of the
    monomial with that one X_j removed (other variables at ν). The 'differential' that linearizes F at ν."""
    J = [[INF for _ in range(n)] for _ in range(n)]
    for i, eq in enumerate(system):
        for (coeff, vs) in eq:
            for pos, j in enumerate(vs):
                term = coeff
                for q, vq in enumerate(vs):
                    if q != pos:
                        term = otimes(term, nu[vq])
                J[i][j] = oplus(J[i][j], term)
    return J


def newton_lfp(system: List[List[Monomial]], n: int) -> Tuple[Optional[List[Trop]], int, int, bool]:
    """Newton's method (Esparza–Kiefer–Luttenberger, idempotent case): ν₀=F(0̄); ν_{t+1}=J_F(ν_t)*⊗F(0̄); reaches the
    lfp in ≤ n steps. Returns (lfp, stabilize_steps, reached_at, neg_cycle) where reached_at is the FIRST step whose
    value equals the final lfp (1 for a linear system — the single star-solve A*⊗b)."""
    f0 = F(system, [INF] * n)                                   # constant terms (the only monomials surviving 0̄)
    iterates = [list(f0)]
    nu = list(f0)
    stabilize = 0
    for step in range(1, n + 2):
        J = jacobian(system, nu, n)
        Js, neg = star(J, n)
        if neg:
            return None, step, step, True
        nxt = _matvec(Js, f0, n)
        iterates.append(list(nxt))
        if nxt == nu:
            stabilize = step
            break
        nu = nxt
        stabilize = step + 1
    reached_at = next(i for i, it in enumerate(iterates) if it == nu)
    return nu, stabilize, reached_at, False


def _is_system(spec) -> Optional[Tuple[List[List[Monomial]], int]]:
    if not (isinstance(spec, dict) and "n" in spec and "system" in spec):
        return None
    n = int(spec["n"])
    raw = spec["system"]
    if not (isinstance(raw, (list, tuple)) and len(raw) == n):
        return None
    system: List[List[Monomial]] = []
    for eq in raw:
        mons: List[Monomial] = []
        for (c, vs) in eq:
            mons.append((Fraction(c), tuple(int(v) for v in vs)))
        system.append(mons)
    return system, n


def seminewton_grade(spec: dict) -> KV.Verdict:
    """Solve the least fixpoint of a tropical polynomial system X=F(X) by semiring-Newton. spec = {n, system:[[(coeff,
    (vars…)), …], …]}. EXACT iff Newton's lfp re-substitutes (F(μ)=μ exactly) AND matches the INDEPENDENT Kleene
    fixpoint; a negative cycle (non-absorptive, lfp=−∞) ⇒ DECLINE. DEMOTES to a FACE of M13 (same lfp, faster solver)."""
    parsed = _is_system(spec)
    if parsed is None:
        return KV.decline("seminewton: need {n, system:[[(coeff,(vars…)),…]×n]}", "mech_seminewton")
    system, n = parsed
    k_lfp, k_steps = kleene_lfp(system, n)
    nu, n_steps, reached_at, neg = newton_lfp(system, n)
    if neg or k_lfp is None:
        return KV.decline("seminewton: NEGATIVE CYCLE (non-absorptive semiring, least fixpoint = −∞) ⇒ DECLINE "
                          "(no finite least fixpoint)", "mech_seminewton")
    # ★ EXACT disposer: F(μ)=μ in the semiring AND μ matches the independent Kleene oracle ★
    if F(system, nu) != nu:
        return KV.decline("seminewton: Newton lfp fails re-substitution F(μ)≠μ ⇒ DECLINE", "mech_seminewton")
    if nu != k_lfp:
        return KV.decline("seminewton: Newton lfp disagrees with the independent Kleene fixpoint ⇒ DECLINE "
                          "(cross-check failed — never emit a wrong fixpoint)", "mech_seminewton")
    linear = all(len(vs) <= 1 for eq in system for (_, vs) in eq)
    cert = KV.Cert(KV.EXACT, "semiring_newton_fixpoint", passed=True,
                   check_cost=f"exact semiring re-substitution F(μ)=μ + independent Kleene cross-check; Newton reached "
                              f"the lfp at step {reached_at} vs Kleene {k_steps}",
                   detail=f"least fixpoint of X=F(X) over tropical (min,+); Newton reached it at step {reached_at} "
                          f"({'1 — the single star-solve A*⊗b' if linear else f'≤ n={n}'}) vs Kleene's {k_steps}-rung "
                          "climb; SAME lfp as M13's Kleene — a Jacobian-accelerated SOLVER (FACE of M13), not a new "
                          "certificate kind")
    return KV.exact({"parent_mechanism": PARENT_MECHANISM, "face": "semiring_newton", "n": n,
                     "lfp": [("inf" if v is INF else str(v)) for v in nu], "newton_reached_at": reached_at,
                     "newton_stabilize_steps": n_steps, "kleene_steps": k_steps, "linear": linear},
                    "mech_seminewton", f"semiring-Newton lfp (Newton {n_steps} vs Kleene {k_steps}) → M13 face", cert)


def adjudication() -> dict:
    """Honest gate-by-gate: passes z3-closed/asymptotic/dependency-free; FAILS distinct-in-kind (the least fixpoint
    is M13's object — Newton is a faster solver) ⇒ DEMOTE to a FACE of M13."""
    return {"candidate": "semiring-Newton fixpoint", "z3_closed": True, "asymptotic": True, "dependency_free": True,
            "distinct_in_kind": False, "verdict": "DEMOTE → FACE of M13",
            "reason": "Newton computes the SAME least fixpoint of X=F(X) over the semiring as M13's Kleene (cert kind "
                      "d. semiring/fixpoint); it is a Jacobian-accelerated solver (≤n steps / 1 for linear vs Kleene's "
                      "n), not a new certificate kind"}
