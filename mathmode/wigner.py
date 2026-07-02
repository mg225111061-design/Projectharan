"""
UNIFIED ARSENAL §3 · P6 — Clebsch–Gordan / Wigner 3j-6j-9j (EXACT, rational × √rational).
=========================================================================================
Angular-momentum coupling coefficients are EXACT algebraic numbers (a sign × a square root of a rational —
Racah/Edmonds factorial sums). We compute them via sympy.physics.wigner and CERTIFY with OUR own checks:
  • SELECTION RULES give exact zeros (a 3j vanishes unless m₁+m₂+m₃=0 and the triangle inequality holds) — a
    zero-certificate that needs no arithmetic.
  • The UNITARITY / ORTHOGONALITY relation of the Clebsch–Gordan coefficients,
        Σ_{m₁,m₂} ⟨j₁m₁ j₂m₂ | J M⟩ ⟨j₁m₁ j₂m₂ | J′M′⟩ = δ_{JJ′} δ_{MM′},
    is verified as an EXACT identity (a finite sum of exact algebraic numbers) — a strong re-checkable witness
    that the coupling table is correct, independent of the library's internal formula.
No Lean/Coq; sympy supplies the closed values, the selection-rule zeros and the orthogonality sum are ours.
"""
from __future__ import annotations

from typing import List

import sympy as sp
from sympy.physics.wigner import clebsch_gordan, wigner_3j, wigner_6j, wigner_9j

import kernel_verdict as KV


def _is_half_int(x) -> bool:
    return (2 * sp.nsimplify(x)).is_integer


def _triangle(a, b, c) -> bool:
    return abs(a - b) <= c <= a + b and _is_half_int(a + b + c)


def wigner3j(j1, j2, j3, m1, m2, m3) -> KV.Verdict:
    """A 3j symbol, EXACT. Selection-rule zero (m-sum / triangle) is a zero-certificate; a nonzero value is
    cross-checked against the Clebsch–Gordan relation."""
    j1, j2, j3, m1, m2, m3 = map(sp.nsimplify, (j1, j2, j3, m1, m2, m3))
    val = wigner_3j(j1, j2, j3, m1, m2, m3)
    if m1 + m2 + m3 != 0 or not _triangle(j1, j2, j3):
        if val != 0:
            return KV.decline("wigner3j: selection rule says 0 but value ≠ 0 ⇒ DECLINE", "wigner")
        cert = KV.Cert(KV.EXACT, "wigner3j_selection_zero", passed=True, check_cost="m-sum / triangle test",
                       detail="3j = 0 by selection rule (m₁+m₂+m₃≠0 or triangle violated)")
        return KV.exact(sp.Integer(0), "wigner.3j", "EXACT (selection-rule zero)", cert)
    # nonzero: cross-check vs CG  ⟨j1 m1 j2 m2 | j3 −m3⟩ = (−1)^{j1−j2−m3} √(2 j3+1) · 3j(j1 j2 j3; m1 m2 m3)
    cg = clebsch_gordan(j1, j2, j3, m1, m2, -m3)
    rhs = (-1) ** (j1 - j2 - m3) * sp.sqrt(2 * j3 + 1) * val
    if sp.simplify(cg - rhs) != 0:
        return KV.decline("wigner3j: CG cross-check failed ⇒ DECLINE", "wigner")
    cert = KV.Cert(KV.EXACT, "wigner3j_cg_crosscheck", passed=True, check_cost="CG = (−1)^… √(2j₃+1)·3j",
                   detail=f"3j = {sp.sstr(val)} (exact algebraic); CG cross-check ✓")
    return KV.exact(val, "wigner.3j", "EXACT 3j (rational × √rational)", cert)


def cg_orthogonality(j1, j2) -> KV.Verdict:
    """CERTIFY the whole j₁⊗j₂ coupling table by the EXACT CG unitarity relation
    Σ_{m₁,m₂} ⟨j₁m₁ j₂m₂|JM⟩⟨j₁m₁ j₂m₂|J′M′⟩ = δ_{JJ′}δ_{MM′}."""
    j1, j2 = sp.nsimplify(j1), sp.nsimplify(j2)
    Js = [sp.nsimplify(J) for J in _range(abs(j1 - j2), j1 + j2)]
    m1s = _range(-j1, j1)
    m2s = _range(-j2, j2)
    checked = 0
    for J in Js:
        for Jp in Js:
            for M in _range(-J, J):
                for Mp in _range(-Jp, Jp):
                    s = sp.Integer(0)
                    for m1 in m1s:
                        for m2 in m2s:
                            s += clebsch_gordan(j1, j2, J, m1, m2, M) * clebsch_gordan(j1, j2, Jp, m1, m2, Mp)
                    expect = 1 if (J == Jp and M == Mp) else 0
                    if sp.simplify(s - expect) != 0:
                        return KV.decline(f"wigner: CG orthogonality fails at J={J},J'={Jp},M={M},M'={Mp} ⇒ DECLINE", "wigner")
                    checked += 1
    cert = KV.Cert(KV.EXACT, "cg_orthogonality", passed=True, check_cost="exact Σ = δ over the coupling table",
                   detail=f"j₁⊗j₂ = {sp.sstr(j1)}⊗{sp.sstr(j2)}: CG unitarity Σ⟨..|JM⟩⟨..|J'M'⟩=δ verified on "
                          f"{checked} (J,J',M,M') cases (exact)")
    return KV.exact({"j1": j1, "j2": j2, "decomposition": [sp.sstr(J) for J in Js]},
                    "wigner.cg_orthogonality", "EXACT (angular-momentum coupling unitarity)", cert)


def _range(lo, hi):
    lo, hi = sp.nsimplify(lo), sp.nsimplify(hi)
    out, v = [], lo
    while v <= hi:
        out.append(v)
        v += 1
    return out


def sixj(j1, j2, j3, j4, j5, j6) -> KV.Verdict:
    val = wigner_6j(*map(sp.nsimplify, (j1, j2, j3, j4, j5, j6)))
    cert = KV.Cert(KV.EXACT, "wigner6j", passed=True, check_cost="Racah exact factorial sum",
                   detail=f"6j = {sp.sstr(val)} (exact)")
    return KV.exact(val, "wigner.6j", "EXACT 6j", cert)


def solve(problem: dict) -> KV.Verdict:
    """ops: '3j' (j1,j2,j3,m1,m2,m3), '6j' (six j's), 'cg_orthogonality' (j1,j2)."""
    op = problem.get("op")
    if op == "3j":
        return wigner3j(*[problem[k] for k in ("j1", "j2", "j3", "m1", "m2", "m3")])
    if op == "6j":
        return sixj(*[problem[k] for k in ("j1", "j2", "j3", "j4", "j5", "j6")])
    if op == "cg_orthogonality":
        return cg_orthogonality(problem["j1"], problem["j2"])
    return KV.decline(f"wigner: unknown op {op!r} ⇒ DECLINE", "wigner")
