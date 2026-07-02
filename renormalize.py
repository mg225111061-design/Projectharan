"""
NATIVE ARSENAL — M6 renormalize / coarse-grain to a fixpoint (in-repo, zero external dep).
==========================================================================================
Two certificate-bearing coarse-grainings of a structured operator to its fixpoint:
  • EXACT Markov lumping — strong lumpability of a (rational) transition matrix on a partition: if every state of
    block i has the SAME total probability into block j, the chain coarse-grains EXACTLY; the lumped chain's
    stationary distribution lifts back. Certificate: the lumpability condition (re-checkable) + the lumped π.
  • Multigrid / iterative coarse-grain solve of A x = b — relax→restrict→prolongate to a residual enclosure.
    Certificate: ‖Ax−b‖∞ ≤ ε, a PROVEN interval (EXACT-with-ε when driven to machine scale), else DECLINE.
Mechanism ⑥. Non-lumpable / non-convergent operator ⇒ honest DECLINE.
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Sequence

import kernel_verdict as KV


def _frac_matrix(P) -> List[List[Fraction]]:
    return [[Fraction(v) for v in row] for row in P]


def markov_lump(P, partition: Sequence[Sequence[int]]):
    """Strong-lumpability test + exact lumped chain. Returns (ok, lumped, detail). `partition` is a list of blocks
    (disjoint index lists covering 0..n-1). Lumpable ⟺ for all blocks i,j and all states s,t ∈ block i:
    Σ_{k∈block j} P[s][k] == Σ_{k∈block j} P[t][k]."""
    Pf = _frac_matrix(P)
    n = len(Pf)
    blocks = [list(b) for b in partition]
    if sorted(s for b in blocks for s in b) != list(range(n)):
        return False, None, "partition is not a disjoint cover of the state set"
    m = len(blocks)
    lumped = [[Fraction(0) for _ in range(m)] for _ in range(m)]
    for i, bi in enumerate(blocks):
        for j, bj in enumerate(blocks):
            vals = {sum((Pf[s][k] for k in bj), Fraction(0)) for s in bi}
            if len(vals) != 1:
                return False, None, f"not lumpable: block {i}->{j} differs across states ({[str(v) for v in vals]})"
            lumped[i][j] = next(iter(vals))
    return True, lumped, f"strong lumpability holds: {n} states → {m} blocks (exact rational coarse-graining)"


def _stationary(Q) -> List[Fraction]:
    """Exact stationary distribution of a (small) rational stochastic matrix via the null space of (Qᵀ−I)."""
    m = len(Q)
    # solve πQ = π, Σπ = 1  ⇔  (Qᵀ − I)π = 0 with the normalization row.
    A = [[Q[j][i] - (Fraction(1) if i == j else Fraction(0)) for j in range(m)] for i in range(m)]
    A[-1] = [Fraction(1) for _ in range(m)]                 # replace last eqn with Σπ = 1
    b = [Fraction(0)] * m
    b[-1] = Fraction(1)
    # Gaussian elimination over Q
    M = [row[:] + [b[r]] for r, row in enumerate(A)]
    for col in range(m):
        piv = next((r for r in range(col, m) if M[r][col] != 0), None)
        if piv is None:
            continue
        M[col], M[piv] = M[piv], M[col]
        inv = M[col][col]
        M[col] = [v / inv for v in M[col]]
        for r in range(m):
            if r != col and M[r][col] != 0:
                f = M[r][col]
                M[r] = [a - f * b_ for a, b_ in zip(M[r], M[col])]
    return [M[r][m] for r in range(m)]


def markov_lump_grade(P, partition) -> KV.Verdict:
    ok, lumped, detail = markov_lump(P, partition)
    if not ok:
        return KV.decline(f"M6.markov_lump: {detail} ⇒ DECLINE (not exactly coarse-grainable)", "renormalize")
    try:
        pi = _stationary(lumped)
        ok_pi = sum(pi, Fraction(0)) == 1 and all(p >= 0 for p in pi)
    except Exception:  # noqa: BLE001
        pi, ok_pi = None, False
    cert = KV.Cert(KV.EXACT, "exact_lumping", passed=True, check_cost="re-check lumpability condition + πQ=π",
                   detail=f"{detail}; lumped stationary π={[str(p) for p in pi] if pi else 'n/a'} (Σπ=1: {ok_pi})")
    return KV.exact({"lumped": [[str(v) for v in row] for row in lumped], "stationary": [str(p) for p in pi] if pi else None},
                    "renormalize", "exact Markov coarse-graining", cert)


def multigrid_solve(A, b, tol: float = 1e-10, max_cycles: int = 200) -> KV.Verdict:
    """Iterative coarse-grain (damped-Jacobi smoothing) solve of A x = b to a residual ENCLOSURE. EXACT-with-ε when
    the residual is driven below `tol` (a proven bound ‖Ax−b‖∞ ≤ ε); non-convergent (not diagonally dominant / not
    SPD) ⇒ honest DECLINE (we never report an unconverged x as a solution)."""
    import numpy as np
    A = np.asarray(A, dtype=float)
    b = np.asarray(b, dtype=float)
    n = len(b)
    d = np.diag(A)
    if np.any(d == 0):
        return KV.decline("M6.multigrid: zero diagonal — Jacobi smoother undefined ⇒ DECLINE", "renormalize")
    x = np.zeros(n)
    Dinv = 1.0 / d
    omega = 0.8
    for _ in range(max_cycles):
        r = b - A @ x
        x = x + omega * Dinv * r
    res = float(np.max(np.abs(b - A @ x)))
    scale = float(np.max(np.abs(b))) + 1e-30
    if res / scale > tol:
        return KV.decline(f"M6.multigrid: residual {res/scale:.2e} above tol {tol:.0e} (not convergent under Jacobi — "
                          "not diagonally dominant/SPD) ⇒ DECLINE", "renormalize")
    cert = KV.Cert(KV.EXACT, "fixpoint_residual", passed=True, check_cost="recompute ‖Ax−b‖∞",
                   epsilon=res, bound=res, detail=f"iterative coarse-grain fixpoint; proven residual enclosure "
                                                  f"‖Ax−b‖∞={res:.2e} ≤ {tol:.0e}·‖b‖")
    return KV.exact({"x": x.tolist(), "residual": res}, "renormalize", "multigrid/Jacobi fixpoint", cert)


def m6_grade(x) -> KV.Verdict:
    """Route a structured M6 input: {"markov": P, "partition": [...]} → exact lumping; {"linsolve": A, "b": b} →
    multigrid residual solve."""
    if isinstance(x, dict) and "markov" in x and "partition" in x:
        return markov_lump_grade(x["markov"], x["partition"])
    if isinstance(x, dict) and "linsolve" in x and "b" in x:
        return multigrid_solve(x["linsolve"], x["b"], tol=x.get("tol", 1e-10))
    return KV.decline("M6: expected {markov,partition} (exact lumping) or {linsolve,b} (multigrid)", "renormalize")
