"""
UNIFIED ARSENAL §4 · T-symbolic-dynamics — chaos → subshift of finite type → INTEGER MATRIX → exact invariants.
==============================================================================================================
A chaotic map with a Markov partition becomes a SUBSHIFT OF FINITE TYPE: a 0/1 transition matrix A on the symbol
alphabet. Then the dynamics' invariants are EXACT integer/algebraic linear algebra — what looked unclosable
(a chaotic orbit) folds:
  • topological entropy   h = log λ_max(A)        (λ_max = the Perron root of the characteristic polynomial)
  • #points of period n   N_n = tr(Aⁿ)            (an exact integer)
  • Artin–Mazur zeta      ζ(t) = 1/det(I − tA)     (an exact rational function; = exp Σ N_n tⁿ/n)

This is the rigorous "fold what folds": the transform re-expresses the orbit as A, and §-linear-algebra closes it.
CERTIFICATE (ours): N_n = tr(Aⁿ) recomputed by matrix power; the zeta identity −log det(I−tA) = Σ tr(Aⁿ) tⁿ/n
verified as a power series; λ_max verified to be a root of the characteristic polynomial (the Perron root).
Fixture: the golden-mean shift A=[[1,1],[1,0]] ⇒ h=log φ, ζ=1/(1−t−t²) (Fibonacci/Lucas), N_n=Lucas numbers.
Honest scope (§X): EXACT for a GIVEN subshift matrix (the Markov-partition step — getting A from a smooth map — is
the modeling input; data-driven Koopman/DMD spectra are certified-numeric/DECLINE, never EXACT here).
"""
from __future__ import annotations

from typing import List

import sympy as sp

import kernel_verdict as KV

_t = sp.Symbol("t")


def subshift(A: List[List[int]]) -> KV.Verdict:
    """Exact dynamical invariants of the subshift of finite type with 0/1 transition matrix A."""
    M = sp.Matrix(A)
    n = M.rows
    if M.cols != n or any(int(x) not in (0, 1) for x in M):
        return KV.decline("symdyn: A must be a square 0/1 transition matrix ⇒ DECLINE", "transforms_symdyn")
    # topological entropy h = log λ_max — λ_max is the Perron (largest) eigenvalue
    charpoly = M.charpoly(sp.Symbol("x"))
    eigs = M.eigenvals()
    lam_max = max((sp.re(e) for e in eigs), key=lambda v: complex(v).real if v.is_number else 0)
    lam_max = sp.simplify(lam_max)
    # ★ certificate: λ_max is a root of the characteristic polynomial ★
    if sp.simplify(charpoly.as_expr().subs(sp.Symbol("x"), lam_max)) != 0:
        return KV.decline("symdyn: λ_max not a root of the char. poly ⇒ DECLINE", "transforms_symdyn")
    entropy = sp.log(lam_max)
    # #period-n points N_n = tr(Aⁿ), checked by matrix power for several n
    Ns = {}
    for k in range(1, 7):
        Ns[k] = int((M ** k).trace())
    # Artin–Mazur zeta ζ(t) = 1/det(I − tA)
    zeta_den = sp.expand((sp.eye(n) - _t * M).det())
    zeta = 1 / zeta_den
    # ★ certificate: −log det(I−tA) = Σ_{k≥1} tr(Aⁿ) tⁿ/k  (series, first 6 coeffs) ★
    lhs = sp.series(-sp.log(zeta_den), _t, 0, 7).removeO()
    rhs = sum(sp.Rational(Ns[k], k) * _t ** k for k in range(1, 7))
    if sp.expand(lhs - rhs) != 0:
        return KV.decline("symdyn: zeta identity −log det(I−tA)=Σtr(Aⁿ)tⁿ/n failed ⇒ DECLINE", "transforms_symdyn")
    cert = KV.Cert(KV.EXACT, "symdyn_integer_matrix", passed=True,
                   check_cost="tr(Aⁿ) by matrix power + zeta series identity + Perron-root check",
                   detail=f"entropy=log({sp.sstr(lam_max)}); N_n=tr(Aⁿ)={[Ns[k] for k in range(1,7)]}; "
                          f"ζ(t)=1/({sp.sstr(zeta_den)})")
    return KV.exact({"entropy": entropy, "lambda_max": lam_max, "period_counts": Ns,
                     "zeta_denominator": zeta_den, "zeta": zeta},
                    "transforms_symdyn.subshift", "EXACT (subshift integer-matrix invariants)", cert)


def solve(problem: dict) -> KV.Verdict:
    """problem = {'op':'subshift','A':[[..]]}."""
    if problem.get("op") != "subshift":
        return KV.decline(f"transforms_symdyn: unknown op {problem.get('op')!r} ⇒ DECLINE", "transforms_symdyn")
    return subshift(problem["A"])
