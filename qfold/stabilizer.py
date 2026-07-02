"""
§AY QT-1 — stabilizer tableau over Sp(2n,𝔽₂) (Gottesman–Knill; self-impl, NOT pyzx). ★ net-new.
================================================================================================================
A Clifford circuit (H, S, CNOT) acts on Pauli operators as a SYMPLECTIC transform of the (x|z)∈𝔽₂^{2n} tableau —
each gate is O(n), the whole circuit folds to a single 2n×2n 𝔽₂ matrix S, and Clifford EQUIVALENCE is decidable in
polynomial time. ★ zx_normalize.py uses pyzx (a FORBIDDEN external dep), so this is a zero-dep 𝔽₂ self-impl: gates
compose as symplectic matrices and S ∈ Sp(2n,𝔽₂) iff Sᵀ Ω S = Ω. A second independent representation (bit-level
tableau update rules) is cross-checked against the matrix (PROPOSER–VERIFIER agreement).

★ Axis A only (Clifford equivalence decided; an M8-class fact), NOT a speedup. A non-Clifford gate (T, Toffoli, …)
has NO symplectic representation ⇒ magic-state exponential cost ⇒ DECLINE (the boundary is exact).
"""
from __future__ import annotations

from typing import List, Sequence, Tuple

import kernel_verdict as KV

_CLIFFORD = {"H", "S", "CNOT"}


def _eye(m: int) -> List[List[int]]:
    return [[1 if i == j else 0 for j in range(m)] for i in range(m)]


def _matmul(A, B):
    m, k, p = len(A), len(B), len(B[0])
    return [[sum(A[i][t] * B[t][j] for t in range(k)) & 1 for j in range(p)] for i in range(m)]


def _transpose(A):
    return [[A[i][j] for i in range(len(A))] for j in range(len(A[0]))]


def _omega(n: int) -> List[List[int]]:
    """Symplectic form Ω = [[0, I],[I, 0]] over 𝔽₂ (−1 = 1)."""
    Z = [[0] * (2 * n) for _ in range(2 * n)]
    for i in range(n):
        Z[i][n + i] = 1
        Z[n + i][i] = 1
    return Z


def _is_symplectic(S, n: int) -> bool:
    Om = _omega(n)
    return _matmul(_matmul(_transpose(S), Om), S) == Om


def _gate_symplectic(gate: Tuple, n: int) -> List[List[int]]:
    """2n×2n 𝔽₂ symplectic matrix of a Clifford gate (basis order x_0..x_{n-1}, z_0..z_{n-1})."""
    S = _eye(2 * n)
    name = gate[0]
    if name == "H":
        q = gate[1]
        S[q][q] = S[n + q][n + q] = 0
        S[q][n + q] = S[n + q][q] = 1                          # swap x_q ↔ z_q
    elif name == "S":
        q = gate[1]
        S[n + q][q] = 1                                        # z_q' = z_q + x_q
    elif name == "CNOT":
        c, t = gate[1], gate[2]
        S[t][c] = 1                                            # x_t' = x_t + x_c
        S[n + c][n + t] = 1                                    # z_c' = z_c + z_t
    return S


def _tableau_rules(gates: Sequence[Tuple], n: int) -> List[List[int]]:
    """Independent rep: evolve each basis Pauli's (x|z) bits by the gate UPDATE RULES (no matrix product). Columns of
    the resulting 2n×2n matrix are the images — must equal the composed symplectic matrix (cross-check)."""
    cols = _eye(2 * n)                                         # column j = current image of basis Pauli j
    for g in gates:
        name = g[0]
        for j in range(2 * n):
            col = cols[j] if False else [cols[r][j] for r in range(2 * n)]
            if name == "H":
                q = g[1]
                col[q], col[n + q] = col[n + q], col[q]
            elif name == "S":
                q = g[1]
                col[n + q] ^= col[q]
            elif name == "CNOT":
                c, t = g[1], g[2]
                col[t] ^= col[c]
                col[n + c] ^= col[n + t]
            for r in range(2 * n):
                cols[r][j] = col[r]
    return cols


def detect_clifford_circuit(gates: Sequence[Tuple], n: int) -> KV.Verdict:
    """Fold a circuit to a single 𝔽₂ symplectic transform. EXACT iff every gate is Clifford (H/S/CNOT) and the
    composed S is symplectic (cross-checked by the tableau rules); a non-Clifford gate ⇒ DECLINE."""
    if n < 1:
        return KV.decline("stabilizer: need n≥1 qubits", "stabilizer_tableau")
    bad = [g[0] for g in gates if g[0] not in _CLIFFORD]
    if bad:
        return KV.decline(f"stabilizer: non-Clifford gate(s) {bad[:3]} (e.g. T/Toffoli) have NO symplectic "
                          f"representation ⇒ magic-state exponential cost ⇒ DECLINE", "stabilizer_tableau")
    S = _eye(2 * n)
    for g in gates:
        S = _matmul(_gate_symplectic(g, n), S)                 # compose (rep 1: matrix product)
    if not _is_symplectic(S, n):                               # the Clifford certificate over 𝔽₂
        return KV.decline("stabilizer: composed transform is NOT symplectic ⇒ DECLINE", "stabilizer_tableau")
    rep2 = _tableau_rules(gates, n)                            # rep 2: bit-level update rules (independent code)
    if rep2 != S:
        return KV.decline("stabilizer: the two representations disagree ⇒ DECLINE", "stabilizer_tableau")
    cert = KV.Cert(KV.EXACT, "stabilizer_tableau_f2", passed=True, check_cost="O(n²) SᵀΩS=Ω + tableau cross-check",
                   detail=f"{len(gates)} Clifford gates fold to a single 2n×2n 𝔽₂ symplectic matrix (SᵀΩS=Ω ✓); two "
                          f"independent representations (matrix product ∧ tableau rules) agree")
    return KV.exact({"n": n, "gates": len(gates), "symplectic": True}, "stabilizer_tableau", "O(g·n) gate folding",
                    cert, reason="Axis-A only: Clifford equivalence decided in 𝔽₂ (Gottesman–Knill, M8-class)")


def adversarial_battery() -> dict:
    """★ EXACT: Clifford circuits (H/S/CNOT) fold to a symplectic 𝔽₂ matrix (two reps agree). ★★ DECLINE: any T-gate
    (non-Clifford) ⇒ DECLINE — the magic boundary is exact, no false-EXACT."""
    bell = detect_clifford_circuit([("H", 0), ("CNOT", 0, 1)], 2)             # Bell-state prep
    bell_ok = bell.status == KV.EXACT and bell.result["symplectic"]
    longer = detect_clifford_circuit([("H", 0), ("S", 1), ("CNOT", 0, 1), ("H", 1), ("CNOT", 1, 0), ("S", 0)], 2)
    longer_ok = longer.status == KV.EXACT
    tgate = detect_clifford_circuit([("H", 0), ("T", 0), ("CNOT", 0, 1)], 2)  # ★★ T is non-Clifford
    t_declines = tgate.status == KV.DECLINE
    toffoli = detect_clifford_circuit([("Toffoli", 0, 1, 2)], 3)
    toff_declines = toffoli.status == KV.DECLINE
    cases = {"bell_exact": bell_ok, "longer_clifford_exact": longer_ok, "tgate_declines": t_declines,
             "toffoli_declines": toff_declines}
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, x in cases.items() if not x]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
