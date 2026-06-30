"""
§BN NEW-5 — Alexander polynomial of a knot from a Seifert matrix (complete-invariant m09; amplifies mech_knot).
==================================================================================================================
The Alexander polynomial Δ(t) = det(V − t·Vᵀ) ∈ ℤ[t] of a knot, from a Seifert matrix V (2g×2g, integer).  A
DIFFERENT invariant from mech_knot's Kauffman/Jones (computed from a diagram): Δ comes from the Seifert surface
and is exact, polynomial-time (one determinant), and obeys hard normalization laws that make a strong certificate.

Computation: det(V − tVᵀ) is a degree-n polynomial in t; evaluate it at n+1 integer points (each an EXACT integer
determinant) and Lagrange-interpolate over ℚ (the coefficients must come out integral) — no symbolic algebra dep.

★ certificate-or-DECLINE — three INDEPENDENT re-checks (a bad input / bug fails one ⇒ DECLINE, never false-EXACT):
  (1) Δ(1) = det(V − Vᵀ) = ±1   — the knot normalization (any knot has |Δ(1)|=1); re-checked against a direct det;
  (2) Δ(t) is palindromic up to a unit: coeffs == ± reverse(coeffs)  — the Δ(t)≐Δ(1/t) symmetry of a knot;
  (3) |Δ(−1)| = |det(V + Vᵀ)| = the knot determinant — re-checked against a direct det.
If (1) fails the matrix is not a knot Seifert matrix ⇒ DECLINE (we never emit a polynomial that is not an
Alexander polynomial).  0 new mechanism (complete-invariant m09 branch); 0 new disposer.  Exact ℤ/ℚ. zero-dep.
"""
from __future__ import annotations

from fractions import Fraction
from typing import List

import kernel_verdict as KV

_MAX_N = 30          # Seifert matrix size cap (determinant cost) — beyond ⇒ DECLINE on cost


def _det_int(M: List[List[int]]) -> int:
    """Exact integer determinant via Fraction Gaussian elimination (entries integer ⇒ result integer)."""
    n = len(M)
    A = [[Fraction(x) for x in row] for row in M]
    det = Fraction(1)
    for col in range(n):
        piv = next((r for r in range(col, n) if A[r][col] != 0), None)
        if piv is None:
            return 0
        if piv != col:
            A[col], A[piv] = A[piv], A[col]; det = -det
        det *= A[col][col]
        for r in range(col + 1, n):
            if A[r][col] != 0:
                f = A[r][col] / A[col][col]
                A[r] = [A[r][c] - f * A[col][c] for c in range(n)]
    assert det.denominator == 1
    return int(det)


def _lagrange_int(points: List[tuple]) -> List[Fraction]:
    """Lagrange-interpolate (x_i,y_i) → coefficient list [a_0,…,a_d] over ℚ."""
    n = len(points)
    coeffs = [Fraction(0)] * n
    for i in range(n):
        xi, yi = points[i]
        # basis poly L_i(x) = Π_{j≠i} (x − x_j)/(x_i − x_j)
        num = [Fraction(1)]            # polynomial coeffs, low→high
        denom = Fraction(1)
        for j in range(n):
            if j == i:
                continue
            xj = points[j][0]
            denom *= (Fraction(xi) - Fraction(xj))
            new = [Fraction(0)] * (len(num) + 1)          # multiply num by (x − xj)
            for p, cf in enumerate(num):
                new[p + 1] += cf
                new[p] += cf * (-Fraction(xj))
            num = new
        scale = Fraction(yi) / denom
        for p, cf in enumerate(num):
            coeffs[p] += cf * scale
    return coeffs


def alexander(V: List[List[int]]) -> KV.Verdict:
    """EXACT Δ(t)=det(V−tVᵀ) of the knot with Seifert matrix V, certified by (1)–(3); else DECLINE."""
    try:
        V = [[int(x) for x in row] for row in V]
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"alexander: {type(e).__name__}: {e}", "alexander_poly")
    n = len(V)
    if n == 0 or any(len(row) != n for row in V):
        return KV.decline("alexander: Seifert matrix must be square and non-empty", "alexander_poly")
    if n > _MAX_N:
        return KV.decline(f"alexander: size {n} > {_MAX_N} ⇒ DECLINE on cost", "alexander_poly")
    VT = [[V[j][i] for j in range(n)] for i in range(n)]
    # evaluate det(V − t·Vᵀ) at t = 0..n (n+1 points)
    pts = []
    for t in range(n + 1):
        M = [[V[i][j] - t * VT[i][j] for j in range(n)] for i in range(n)]
        pts.append((t, _det_int(M)))
    coeffs = _lagrange_int(pts)
    if any(c.denominator != 1 for c in coeffs):
        return KV.decline("alexander: interpolated coefficients non-integral ⇒ DECLINE (bug guard)", "alexander_poly")
    ic = [int(c) for c in coeffs]
    while len(ic) > 1 and ic[-1] == 0:        # trim leading zeros (top of the polynomial)
        ic.pop()
    # (1) Δ(1) = det(V − Vᵀ) = ±1  (knot normalization), cross-checked against direct det
    delta1_direct = _det_int([[V[i][j] - VT[i][j] for j in range(n)] for i in range(n)])
    delta1_poly = sum(ic)
    if delta1_poly != delta1_direct:
        return KV.decline("alexander: Δ(1) poly ≠ direct det ⇒ DECLINE (interpolation bug guard)", "alexander_poly")
    if delta1_direct not in (1, -1):
        return KV.decline(f"alexander: Δ(1)={delta1_direct} ∉ {{±1}} — not a knot Seifert matrix ⇒ DECLINE",
                          "alexander_poly")
    # (2) palindromic up to a unit: ic == ±reverse(ic)
    rev = ic[::-1]
    if not (ic == rev or ic == [-x for x in rev]):
        return KV.decline(f"alexander: Δ not palindromic (coeffs {ic}) — Δ(t)≐Δ(1/t) symmetry fails ⇒ DECLINE",
                          "alexander_poly")
    # (3) |Δ(−1)| = |det(V + Vᵀ)| = knot determinant, cross-checked
    det_knot = abs(_det_int([[V[i][j] + VT[i][j] for j in range(n)] for i in range(n)]))
    delta_m1 = sum(ic[k] * (-1) ** k for k in range(len(ic)))
    if abs(delta_m1) != det_knot:
        return KV.decline(f"alexander: |Δ(−1)|={abs(delta_m1)} ≠ knot det |det(V+Vᵀ)|={det_knot} ⇒ DECLINE",
                          "alexander_poly")
    cert = KV.Cert(KV.EXACT, "alexander_seifert", passed=True,
                   check_cost="Δ(1)=±1 (direct det) + palindromic symmetry + |Δ(−1)|=knot det",
                   detail=f"Δ(t) coeffs (low→high) {ic}; Δ(1)={delta1_direct}=±1 ✓; palindromic ✓; "
                          f"|Δ(−1)|={abs(delta_m1)}=det(V+Vᵀ) ✓")
    return KV.exact({"coeffs": ic, "delta_1": delta1_direct, "knot_determinant": det_knot},
                    "alexander_poly", "Alexander polynomial det(V−tVᵀ)", cert)


def adversarial_battery() -> dict:
    """★ trefoil Seifert V=[[−1,1],[0,−1]] ⇒ Δ=t²−t+1, det 3; ★ figure-eight V=[[1,1],[0,−1]] ⇒ Δ=−t²+3t−1,
    det 5; ★ identity V=I (Δ(1)=0) ⇒ DECLINE (not a knot Seifert matrix); ★ Δ(1)=±1 + palindrome re-checked."""
    tre = alexander([[-1, 1], [0, -1]])
    fig8 = alexander([[1, 1], [0, -1]])
    nonknot = alexander([[1, 0], [0, 1]])             # Δ(1)=det(0)=0 ⇒ DECLINE
    cases = {
        "trefoil_poly_EXACT": tre.status == "EXACT" and tre.result["coeffs"] == [1, -1, 1]
                              and tre.result["knot_determinant"] == 3,
        "fig8_poly_EXACT": fig8.status == "EXACT" and fig8.result["coeffs"] == [-1, 3, -1]
                           and fig8.result["knot_determinant"] == 5,
        "nonknot_DECLINE": nonknot.status == "DECLINE",
        "trefoil_delta1_unit": tre.status == "EXACT" and tre.result["delta_1"] in (1, -1),
        "exact_carries_cert": tre.certificate is not None and tre.certificate.passed,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
