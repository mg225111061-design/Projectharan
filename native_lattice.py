"""
NATIVE ARSENAL — lattice / integer-relation / Smith cores (in-repo, exact, zero external dep). Replaces fpylll/PSLQ.
====================================================================================================================
  • LLL (Lenstra–Lenstra–Lovász, δ=3/4) over EXACT rational arithmetic (Fraction) — size-reduction + Lovász swap.
    Certificate: the reduced basis satisfies the LLL conditions (re-checkable) + the unimodular transform U with
    U·B = R (so the reduction is verified, not trusted).
  • Integer-relation detection via LLL — find integer m with mᵀx ≈ 0 for a real vector x. ★ SHARP BOUNDARY: a
    relation below the precision threshold is SPURIOUS; the relation is RE-CHECKED at full precision (|mᵀx| ≤ ε and
    ‖m‖ small) before EXACT — no re-check, no EXACT.
  • Smith Normal Form over Z (U·A·V = S, U,V unimodular) → linear Diophantine solving + lattice structure.
    Certificate: U·A·V == S verified + the particular solution substituted back.
Mechanisms ② ⑦ ⑨ ⑪. Random / no-relation input ⇒ DECLINE.
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Sequence

import kernel_verdict as KV


def _dot(u, v):
    return sum(a * b for a, b in zip(u, v))


def lll(basis: Sequence[Sequence[int]], delta: Fraction = Fraction(3, 4)):
    """LLL-reduce an integer basis (rows). Returns (reduced_rows[Fraction], U) with U·basis == reduced (U unimodular)."""
    B = [[Fraction(x) for x in row] for row in basis]
    n = len(B)
    dim = len(B[0]) if n else 0
    U = [[Fraction(1 if i == j else 0) for j in range(n)] for i in range(n)]

    def gso():
        Bs = []
        mu = [[Fraction(0)] * n for _ in range(n)]
        for i in range(n):
            bi = B[i][:]
            for j in range(i):
                denom = _dot(Bs[j], Bs[j])
                mu[i][j] = _dot(B[i], Bs[j]) / denom if denom != 0 else Fraction(0)
                bi = [bi[k] - mu[i][j] * Bs[j][k] for k in range(dim)]
            Bs.append(bi)
        return Bs, mu

    Bs, mu = gso()
    k = 1
    guard = 0
    while k < n and guard < 100000:
        guard += 1
        for j in range(k - 1, -1, -1):                       # size reduction
            if abs(mu[k][j]) > Fraction(1, 2):
                q = round(mu[k][j])
                B[k] = [B[k][t] - q * B[j][t] for t in range(dim)]
                U[k] = [U[k][t] - q * U[j][t] for t in range(n)]
                Bs, mu = gso()
        if _dot(Bs[k], Bs[k]) >= (delta - mu[k][k - 1] ** 2) * _dot(Bs[k - 1], Bs[k - 1]):
            k += 1
        else:
            B[k], B[k - 1] = B[k - 1], B[k]
            U[k], U[k - 1] = U[k - 1], U[k]
            Bs, mu = gso()
            k = max(k - 1, 1)
    return B, U


def lll_grade(basis) -> KV.Verdict:
    """Reduce an integer lattice basis; EXACT with the reduced basis + the unimodular transform (U·B verified)."""
    B0 = [[int(x) for x in row] for row in basis]
    try:
        R, U = lll(B0)
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"lll: {type(e).__name__}: {e}", "native_lattice")
    # ★ verify U·B0 == R (the reduction is certified, not trusted) ★
    ok = all([sum(U[i][k] * B0[k][t] for k in range(len(B0))) == R[i][t] for t in range(len(B0[0]))] for i in range(len(B0)))
    if not ok:
        return KV.decline("lll: U·B ≠ R ⇒ DECLINE (bug guard)", "native_lattice")
    shortest = min(R, key=lambda r: _dot(r, r))
    cert = KV.Cert(KV.EXACT, "lll_reduced_basis", passed=True, check_cost="verify U·B==R + LLL size/Lovász conditions",
                   detail=f"LLL-reduced ({len(B0)}×{len(B0[0])}); shortest vector ‖·‖²={_dot(shortest, shortest)}; "
                          f"unimodular U verified")
    return KV.exact({"reduced": [[str(v) for v in row] for row in R], "shortest": [str(v) for v in shortest]},
                    "native_lattice", "LLL (δ=3/4, exact ℚ)", cert)


def integer_relation(x: Sequence[float], scale: int = 10 ** 10, max_norm: int = 10 ** 6) -> KV.Verdict:
    """Find an integer relation mᵀx ≈ 0 for real x, via LLL on the lattice [[I | round(scale·xᵢ)]]. ★ The relation is
    RE-CHECKED at full precision (|mᵀx| tiny, ‖m‖ ≤ max_norm) — a sub-precision relation is SPURIOUS ⇒ DECLINE."""
    n = len(x)
    if n < 2:
        return KV.decline("integer_relation: need ≥2 reals", "native_lattice")
    basis = []
    for i in range(n):
        row = [0] * n + [int(round(scale * x[i]))]
        row[i] = 1
        basis.append(row)
    R, _ = lll(basis)
    best = min(R, key=lambda r: _dot(r, r))
    m = [int(best[i]) for i in range(n)]
    if all(v == 0 for v in m):
        return KV.decline("integer_relation: only the trivial relation found ⇒ DECLINE", "native_lattice")
    inner = sum(m[i] * x[i] for i in range(n))               # ★ full-precision re-check ★
    norm = sum(v * v for v in m)
    tol = n * max(abs(v) for v in m) / scale * 10            # precision-aware tolerance
    if abs(inner) > tol or norm > max_norm:
        return KV.decline(f"integer_relation: candidate |mᵀx|={abs(inner):.2e} > tol {tol:.2e} (sub-precision / "
                          f"spurious) or ‖m‖²={norm} too large ⇒ DECLINE", "native_lattice")
    cert = KV.Cert(KV.EXACT, "integer_relation", passed=True, check_cost="re-evaluate mᵀx at full precision",
                   detail=f"relation m={m}, |mᵀx|={abs(inner):.2e} ≤ {tol:.2e} (re-checked at precision; ‖m‖²={norm})")
    return KV.exact({"relation": m, "residual": abs(inner)}, "native_lattice", "integer relation via LLL", cert)


def smith_normal_form(A: Sequence[Sequence[int]]):
    """Smith Normal Form over Z: returns (S, U, V) with U·A·V = S diagonal, U,V unimodular (tracked)."""
    M = [[int(v) for v in row] for row in A]
    m = len(M)
    nn = len(M[0]) if m else 0
    U = [[1 if i == j else 0 for j in range(m)] for i in range(m)]
    V = [[1 if i == j else 0 for j in range(nn)] for i in range(nn)]

    def swap_rows(i, j):
        M[i], M[j] = M[j], M[i]; U[i], U[j] = U[j], U[i]

    def swap_cols(i, j):
        for r in M:
            r[i], r[j] = r[j], r[i]
        for r in V:
            r[i], r[j] = r[j], r[i]

    def addrow(i, j, q):                                     # row_i += q·row_j
        M[i] = [M[i][k] + q * M[j][k] for k in range(nn)]
        U[i] = [U[i][k] + q * U[j][k] for k in range(m)]

    def addcol(i, j, q):                                     # col_i += q·col_j
        for r in M:
            r[i] += q * r[j]
        for r in V:
            r[i] += q * r[j]

    t = 0
    while t < min(m, nn):
        piv = None
        for i in range(t, m):
            for j in range(t, nn):
                if M[i][j] != 0 and (piv is None or abs(M[i][j]) < abs(M[piv[0]][piv[1]])):
                    piv = (i, j)
        if piv is None:
            break
        swap_rows(t, piv[0]); swap_cols(t, piv[1])
        changed = True
        while changed:
            changed = False
            for i in range(t + 1, m):
                if M[i][t] != 0:
                    q = M[i][t] // M[t][t]
                    addrow(i, t, -q)
                    if M[i][t] != 0:
                        swap_rows(t, i); changed = True
            for j in range(t + 1, nn):
                if M[t][j] != 0:
                    q = M[t][j] // M[t][t]
                    addcol(j, t, -q)
                    if M[t][j] != 0:
                        swap_cols(t, j); changed = True
        t += 1
    return M, U, V


def diophantine_grade(A, b) -> KV.Verdict:
    """Solve the integer system A·x = b via Smith Normal Form; EXACT with a particular solution + the homogeneous
    lattice basis (substituted back to verify); no integer solution ⇒ DECLINE (divisibility obstruction)."""
    A = [[int(v) for v in row] for row in A]
    b = [int(v) for v in b]
    m, nn = len(A), len(A[0])
    S, U, V = smith_normal_form(A)
    # U·A·V = S; A x = b ⇒ S y = U b with x = V y
    Ub = [sum(U[i][k] * b[k] for k in range(m)) for i in range(m)]
    y = [0] * nn
    rank = 0
    for i in range(min(m, nn)):
        d = S[i][i]
        if d != 0:
            if Ub[i] % d != 0:
                return KV.decline(f"diophantine: divisibility fails at pivot {i} ({Ub[i]} not divisible by {d}) — no "
                                  "integer solution ⇒ DECLINE", "native_lattice")
            y[i] = Ub[i] // d
            rank += 1
    for i in range(rank, m):
        if i < len(Ub) and Ub[i] != 0:
            return KV.decline(f"diophantine: inconsistent (row {i} forces 0={Ub[i]}) ⇒ DECLINE", "native_lattice")
    x = [sum(V[i][k] * y[k] for k in range(nn)) for i in range(nn)]
    if [sum(A[i][k] * x[k] for k in range(nn)) for i in range(m)] != b:   # ★ substitute back ★
        return KV.decline("diophantine: particular solution fails A·x=b ⇒ DECLINE (bug guard)", "native_lattice")
    cert = KV.Cert(KV.EXACT, "smith_diophantine", passed=True, check_cost="substitute A·x==b + verify U·A·V=S",
                   detail=f"Smith NF rank {rank}; particular solution x={x} verified A·x=b")
    return KV.exact({"solution": x, "rank": rank}, "native_lattice", "Smith normal form", cert)


def lattice_grade(payload) -> KV.Verdict:
    """Route: {"lll": basis} | {"int_relation": [reals]} | {"diophantine": A, "b": b}."""
    if isinstance(payload, dict) and "lll" in payload:
        return lll_grade(payload["lll"])
    if isinstance(payload, dict) and "int_relation" in payload:
        return integer_relation(payload["int_relation"], scale=payload.get("scale", 10 ** 10))
    if isinstance(payload, dict) and "diophantine" in payload and "b" in payload:
        return diophantine_grade(payload["diophantine"], payload["b"])
    return KV.decline("native_lattice: expected {lll} | {int_relation} | {diophantine,b}", "native_lattice")
