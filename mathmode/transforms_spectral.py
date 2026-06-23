"""
UNIFIED ARSENAL §4 · T-spectral-operator — chaos → transfer (Perron–Frobenius) operator → exact spectrum.
========================================================================================================
A piecewise-linear expanding MARKOV map has a transfer (Perron–Frobenius) operator that, restricted to densities
piecewise-constant on the Markov partition, is a FINITE column-stochastic RATIONAL matrix M. Its spectrum is then
exact linear algebra:
  • leading eigenvalue = 1, eigenvector = the INVARIANT DENSITY (the physical measure);
  • the SPECTRAL GAP 1 − |λ₂| and the DECAY-OF-CORRELATIONS rate −log|λ₂| (exponential mixing) are EXACT.
So a chaotic map's statistics fold to a rational eigenproblem.

CERTIFICATE (ours): M·v = v exactly (invariant density), each column sums to 1 (probability conservation), and the
eigenvalues are exact roots of the characteristic polynomial. Honest scope (§X): EXACT only for a piecewise-linear
MARKOV operator (the Markov-partition step is the modeling input). For a GENERAL chaotic map the transfer operator
is infinite-dimensional; the RIGOROUS finite approximation is ULAM discretization with interval/ball arithmetic —
CERTIFIED-NUMERIC (PROBABILISTIC with an error bound), NOT EXACT — and data-driven Koopman/DMD is not even that.
We do the EXACT Markov case here and flag the rest as certified-numeric/DECLINE — never a fabricated EXACT.
"""
from __future__ import annotations

from typing import List

import sympy as sp

import kernel_verdict as KV


def transfer_operator_spectrum(M: List[List]) -> KV.Verdict:
    """Spectrum of a piecewise-linear-Markov transfer operator M (column-stochastic, rational). EXACT invariant
    density + spectral gap + decay rate, or DECLINE if M is not a valid transfer operator."""
    A = sp.Matrix(M)
    n = A.rows
    if A.cols != n:
        return KV.decline("spectral: transfer operator must be square ⇒ DECLINE", "transforms_spectral")
    # ★ a Perron–Frobenius/Markov operator: entries ≥ 0 and each COLUMN sums to 1 (probability conserved) ★
    if any(sp.simplify(x) < 0 for x in A):
        return KV.decline("spectral: transfer operator has a negative entry ⇒ not a PF operator ⇒ DECLINE", "transforms_spectral")
    for j in range(n):
        if sp.simplify(sum(A[i, j] for i in range(n)) - 1) != 0:
            return KV.decline(f"spectral: column {j} does not sum to 1 (probability not conserved) ⇒ DECLINE", "transforms_spectral")
    # leading eigenvalue 1 with the invariant density as eigenvector
    ns = (A - sp.eye(n)).nullspace()
    if not ns:
        return KV.decline("spectral: 1 is not an eigenvalue — no invariant density ⇒ DECLINE", "transforms_spectral")
    dens = ns[0]
    s = sum(dens)
    dens = dens / s if s != 0 else dens                      # normalise to a probability density
    if sp.simplify((A * dens - dens)).norm() != 0:           # ★ certificate: M·v = v exactly ★
        return KV.decline("spectral: invariant density failed M·v=v ⇒ DECLINE", "transforms_spectral")
    # spectral gap + decay-of-correlations rate from the subleading eigenvalue magnitude
    eigs = A.eigenvals()
    mags = []
    for e, mult in eigs.items():
        m = sp.Abs(sp.simplify(e))
        mags.extend([m] * mult)
    subleading = sorted((m for m in mags if sp.simplify(m - 1) != 0), key=lambda v: float(v), reverse=True)
    lam2 = subleading[0] if subleading else sp.Integer(0)
    gap = sp.simplify(1 - lam2)
    decay = sp.oo if lam2 == 0 else sp.simplify(-sp.log(lam2))
    cert = KV.Cert(KV.EXACT, "transfer_operator_spectrum", passed=True,
                   check_cost="M·v=v + column sums=1 + exact eigenvalues",
                   detail=f"invariant density {list(dens)}; spectral gap 1−|λ₂| = {sp.sstr(gap)}; "
                          f"decay-of-correlations rate −log|λ₂| = {sp.sstr(decay)} (exact, piecewise-linear Markov)")
    return KV.exact({"invariant_density": list(dens), "lambda_2": lam2, "spectral_gap": gap, "decay_rate": decay,
                     "eigenvalues": dict(eigs)}, "transforms_spectral.transfer_operator_spectrum",
                    "EXACT (Markov transfer-operator spectrum)", cert)


def solve(problem: dict) -> KV.Verdict:
    """problem = {'op':'transfer_operator','M':[[..]]} (column-stochastic rational matrix)."""
    if problem.get("op") != "transfer_operator":
        return KV.decline(f"transforms_spectral: unknown op {problem.get('op')!r} ⇒ DECLINE", "transforms_spectral")
    return transfer_operator_spectrum(problem["M"])
