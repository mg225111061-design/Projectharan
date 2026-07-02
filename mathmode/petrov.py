"""
UNIFIED ARSENAL §3 · P3 — Petrov classification of the Weyl tensor (algebraic DECISION).
========================================================================================
The Petrov type (I, II, D, III, N, O) is the algebraic type of the Weyl tensor, read off the FIVE Newman–Penrose
complex scalars Ψ₀…Ψ₄ via the PRINCIPAL NULL DIRECTIONS: the roots of the quartic
        p(λ) = Ψ₀ + 4Ψ₁λ + 6Ψ₂λ² + 4Ψ₃λ³ + Ψ₄λ⁴
(with a root at ∞ of multiplicity 4−deg p when Ψ₄=0). The MULTIPLICITY PARTITION of the 4 roots is the type:
   (1,1,1,1)→I · (2,1,1)→II · (2,2)→D · (3,1)→III · (4)→N · (p≡0)→O (conformally flat).
This is a DECISION (the partition is computed exactly from the squarefree factorization + the ∞-root deficit).
Certificate: the quartic + the root-multiplicity partition, cross-checked by the speciality invariant
I³−27J² (=0 ⟺ algebraically special) with I=Ψ₀Ψ₄−4Ψ₁Ψ₃+3Ψ₂², J=det[[Ψ₀,Ψ₁,Ψ₂],[Ψ₁,Ψ₂,Ψ₃],[Ψ₂,Ψ₃,Ψ₄]].
Fixture: Schwarzschild has only Ψ₂≠0 ⇒ partition (2,2) ⇒ type D (and I³=27J²). Honest scope (§X): from the Ψ
scalars (a null tetrad is needed to GET them from a metric — that is the NP step, separate). Segre (Ricci type) is
the analogous eigenvalue-multiplicity classification — flagged.
"""
from __future__ import annotations

from typing import List, Tuple

import sympy as sp

import kernel_verdict as KV

_lam = sp.Symbol("lambda")

_PARTITION_TYPE = {
    (): "O", (1, 1, 1, 1): "I", (2, 1, 1): "II", (2, 2): "D", (3, 1): "III", (4,): "N",
}


def _multiplicity_partition(psi: List[sp.Expr]) -> Tuple[int, ...]:
    p0, p1, p2, p3, p4 = psi
    p = p0 + 4 * p1 * _lam + 6 * p2 * _lam ** 2 + 4 * p3 * _lam ** 3 + p4 * _lam ** 4
    p = sp.expand(p)
    if p == 0:
        return ()                                            # all PNDs coincide ⇒ type O
    poly = sp.Poly(p, _lam)
    d = poly.degree()
    parts: List[int] = []
    # finite-root multiplicities via squarefree factorization (degree × multiplicity), no need to name the roots
    _, factors = sp.sqf_list(poly)
    for fac, mult in factors:
        parts.extend([mult] * sp.Poly(fac, _lam).degree())
    if d < 4:                                                # the null direction l itself is a PND of multiplicity 4−d
        parts.append(4 - d)
    return tuple(sorted(parts, reverse=True))


def classify(psi: List) -> KV.Verdict:
    """Petrov type from Ψ₀…Ψ₄. EXACT (a decision via the PND multiplicity partition)."""
    psi = [sp.sympify(x) for x in psi]
    if len(psi) != 5:
        return KV.decline("petrov: need exactly 5 Weyl scalars Ψ₀…Ψ₄ ⇒ DECLINE", "petrov")
    part = _multiplicity_partition(psi)
    ptype = _PARTITION_TYPE.get(part)
    if ptype is None:
        return KV.decline(f"petrov: unrecognized PND multiplicity partition {part} ⇒ DECLINE", "petrov")
    p0, p1, p2, p3, p4 = psi
    I = sp.simplify(p0 * p4 - 4 * p1 * p3 + 3 * p2 ** 2)
    J = sp.simplify(sp.Matrix([[p0, p1, p2], [p1, p2, p3], [p2, p3, p4]]).det())
    special = sp.simplify(I ** 3 - 27 * J ** 2) == 0
    # cross-check: types {II,D,III,N,O} are algebraically special (I³=27J²); type I is general (I³≠27J²)
    consistent = (ptype == "I") != special if ptype in ("I",) else (special if ptype in ("II", "D", "III", "N", "O") else True)
    if ptype != "I" and not special:
        return KV.decline(f"petrov: partition says {ptype} (special) but I³≠27J² ⇒ DECLINE (inconsistent)", "petrov")
    cert = KV.Cert(KV.EXACT, "petrov_pnd_partition", passed=True, check_cost="quartic squarefree partition + I³,J² speciality",
                   detail=f"Petrov type {ptype}; PND multiplicity partition {part}; I={sp.sstr(I)}, J={sp.sstr(J)}, "
                          f"algebraically special (I³=27J²)={special}")
    return KV.exact({"type": ptype, "partition": part, "I": I, "J": J, "special": special},
                    "petrov.classify", "DECISION (Petrov type via PND multiplicities)", cert)


def solve(problem: dict) -> KV.Verdict:
    """problem = {'op':'petrov','psi':[Ψ0,Ψ1,Ψ2,Ψ3,Ψ4]}."""
    if problem.get("op") != "petrov":
        return KV.decline(f"petrov: unknown op {problem.get('op')!r} ⇒ DECLINE", "petrov")
    return classify(problem["psi"])
