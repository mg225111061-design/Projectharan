"""
UNIFIED ARSENAL §3 · P7 — Buckingham-Pi (EXACT decision procedure over ℚ).
==========================================================================
Dimensional analysis has two exact pieces:
  (a) CONSISTENCY (always-on guard): an equation is dimensionally valid iff the two sides have equal
      base-dimension exponent vectors — exact vector equality (this lives in `science_engineering`).
  (b) BUCKINGHAM-Pi: with n physical quantities over r independent base dimensions, the number of independent
      dimensionless Π-groups is exactly the NULLITY of the dimension matrix D (rows = base dims, cols =
      quantities): #Π = n − rank(D). Each Π is an INTEGER null-space vector w (the product Πᵢ qᵢ^{wᵢ} is
      dimensionless). Computed by EXACT Gauss–Jordan over ℚ (NOT SVD), then cleared to an integer lattice.

CERTIFICATE (our own, exact): for every returned Π-vector w, D·w = 0 exactly (the group is dimensionless), and
the count equals n − rank(D) by the rank–nullity theorem. Basis NON-uniqueness is flagged honestly; we return a
canonical integer-lattice basis. Pipe flow → {Reynolds ρVD/μ, Euler Δp/ρV²}.
"""
from __future__ import annotations

from typing import Dict, List

import sympy as sp

import kernel_verdict as KV

BASE_DIMS = ("M", "L", "T", "Theta", "I", "N", "J")     # mass, length, time, temperature, current, amount, luminous


def _dimvec(d: Dict[str, int]) -> List[sp.Rational]:
    return [sp.Rational(d.get(b, 0)) for b in BASE_DIMS]


def buckingham_pi(quantities: Dict[str, Dict[str, int]]) -> KV.Verdict:
    """quantities: {name: {base_dim: exponent}}. Returns the Π-groups (EXACT) with the D·w=0 certificate, or a
    DECLINE if there are no dimensionless groups (rank = n)."""
    names = list(quantities)
    cols = [_dimvec(quantities[q]) for q in names]
    used = [i for i, b in enumerate(BASE_DIMS) if any(col[i] != 0 for col in cols)]   # drop unused base dims
    if not used:
        return KV.decline("buckingham: all quantities dimensionless ⇒ trivial ⇒ DECLINE", "buckingham")
    D = sp.Matrix([[cols[j][i] for j in range(len(names))] for i in used])
    rank = D.rank()
    nullity = len(names) - rank
    if nullity == 0:
        cert = KV.Cert(KV.EXACT, "buckingham_rank", passed=True, check_cost="rank over ℚ",
                       detail=f"rank(D)={rank}=#quantities ⇒ NO dimensionless group (Π-count 0)")
        return KV.exact([], "buckingham.pi", "DECISION (no Π-group)", cert)
    # exact rational null space → clear denominators to an integer lattice vector
    pis = []
    for vec in D.nullspace():
        denoms = [sp.denom(c) for c in vec]
        mult = sp.lcm(denoms) if denoms else 1
        w = [int(c * mult) for c in vec]
        g = sp.igcd(*[abs(x) for x in w if x != 0]) or 1
        w = [x // g for x in w]
        assert (D * sp.Matrix(w)).is_zero_matrix, "null-space vector failed D·w=0"   # ★ certificate ★
        group = sp.Mul(*[sp.Symbol(names[i]) ** w[i] for i in range(len(names)) if w[i] != 0])
        pis.append({"exponents": dict(zip(names, w)), "group": group})
    # rank–nullity cross-check + every D·w=0 (re-verified)
    ok = (len(pis) == nullity) and all((D * sp.Matrix([p["exponents"][n] for n in names])).is_zero_matrix for p in pis)
    if not ok:
        return KV.decline("buckingham: Π-count or D·w=0 cross-check failed ⇒ DECLINE", "buckingham")
    cert = KV.Cert(KV.EXACT, "buckingham_nullspace", passed=True, check_cost="D·w=0 (exact) + rank–nullity",
                   detail=f"#Π = n−rank(D) = {len(names)}−{rank} = {nullity}; each Πⱼ dimensionless (D·w=0). "
                          f"Basis non-unique — canonical integer lattice returned. Groups: "
                          f"{', '.join(sp.sstr(p['group']) for p in pis)}")
    return KV.exact(pis, "buckingham.pi", "EXACT Buckingham-Pi (nullity over ℚ)", cert)


def solve(problem: dict) -> KV.Verdict:
    """problem = {'op':'buckingham','quantities': {name: {M:..,L:..,T:..}}}."""
    if problem.get("op") != "buckingham":
        return KV.decline(f"buckingham: unknown op {problem.get('op')!r} ⇒ DECLINE", "buckingham")
    return buckingham_pi(problem["quantities"])
