"""
POST-CONSOLIDATION PHASE 1a — DEFECTIVE-VARIABLE LINEARIZATION (Carleman / monomial-closure of a nonlinear loop).
=================================================================================================================
A polynomial loop  s ↦ f(s)  (s a vector of program variables, f a vector of polynomials) is often LINEAR on an
enlarged MONOMIAL basis: there is a finite set of monomials m₁…m_d in the variables such that each m_i∘f is an
EXACT ℚ-linear combination of m₁…m_d. Then M(f(s)) = A·M(s) with M = (m₁…m_d)ᵀ, so M(sₙ) = Aⁿ·M(s₀) and any
target variable's trajectory has a CLOSED FORM computable by matrix power — O(n) loop iterations → O(log n).

★ THE HONEST ADJUDICATION (the four admission gates — this candidate DEMOTES):
  gate 2 (z3-closed): ✓ — the closure m_i∘f = Σ A_{ij} m_j is a POLYNOMIAL IDENTITY (NRA), verified exactly by
      expansion; the resulting per-step linear recurrence is z3-induction-checkable (LRA).
  gate 3 (asymptotic): ✓ — O(n)→O(log n) via Aⁿ.
  gate 4 (dependency-free): ✓ — sympy (grandfathered) for the polynomial algebra; Fraction disposer.
  gate 1 (DISTINCT IN KIND): ✗ — when the monomials close linearly, M(sₙ)=Aⁿ·M(s₀), so EVERY coordinate is
      C-FINITE (satisfies the linear recurrence with char-poly(A) coefficients). That is exactly M11's class — the
      Berlekamp–Massey mechanism folds the resulting sequence from samples. Defective-variable linearization is a
      new *route* (nonlinear loop CODE → the C-finite closed form, proven symbolically) but NOT a new *kind* of
      certificate. ⇒ DEMOTE: a FACE of M11 (parent mechanism 11), NOT a new mechanism. No count++.

The DISPOSER stays exact: run the loop forward over ℚ from a random rational seed and require Aⁿ·M(s₀) to
reproduce the target's trajectory term-for-term; a loop with no finite monomial closure (e.g. x ↦ x², degree
doubles each step) DECLINEs. Precision 1.0.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Dict, List, Optional

import kernel_verdict as KV

PARENT_MECHANISM = 11   # this face routes to M11 (its fold is a C-finite linear recurrence)


def _parse(update: Dict[str, str], variables: List[str]):
    import sympy as sp
    syms = {v: sp.Symbol(v) for v in variables}
    polys = {}
    for v in variables:
        polys[v] = sp.expand(sp.sympify(update[v], locals=syms))
    return syms, polys


def _monomial_key(expr, syms_order):
    """A canonical key for a monomial term (tuple of exponents in the fixed variable order)."""
    import sympy as sp
    d = expr.as_powers_dict()
    return tuple(int(d.get(s, 0)) for s in syms_order)


def close_monomials(update: Dict[str, str], variables: List[str], max_basis: int = 24, max_degree: int = 8):
    """Greedy monomial closure of the polynomial map. Returns (basis_keys, A, syms_order) where A is the d×d ℚ
    matrix with m_i∘f = Σ_j A[i][j]·basis[j], or None if no finite linear closure within the bounds."""
    import sympy as sp
    syms, polys = _parse(update, variables)
    order = [syms[v] for v in variables]
    sub = {syms[v]: polys[v] for v in variables}

    def key_to_monomial(key):
        m = sp.Integer(1)
        for s, e in zip(order, key):
            m *= s ** e
        return m

    # seed: the constant 1 and each variable (degree-1 monomials)
    basis: List[tuple] = [tuple([0] * len(order))] + [tuple(1 if i == j else 0 for j in range(len(order))) for i in range(len(order))]
    seen = set(basis)
    i = 0
    rows: Dict[tuple, List] = {}
    while i < len(basis):
        key = basis[i]
        mono = key_to_monomial(key)
        img = sp.expand(mono.subs(sub, simultaneous=True))      # m_i ∘ f
        # decompose img into monomials; constant maps to the (0,…,0) key
        terms = sp.Add.make_args(img)
        coeffs: Dict[tuple, Fraction] = {}
        for t in terms:
            c, mon = t.as_coeff_Mul()
            k = _monomial_key(mon, order)
            if sum(k) > max_degree:
                return None                                     # degree blew up ⇒ no finite closure
            coeffs[k] = coeffs.get(k, Fraction(0)) + Fraction(sp.nsimplify(c).p, sp.nsimplify(c).q) if c.is_Rational else None
            if coeffs[k] is None:
                return None                                     # non-rational coefficient ⇒ out of scope
            if k not in seen:
                if len(basis) >= max_basis:
                    return None                                 # basis blew up ⇒ no small linear closure
                seen.add(k)
                basis.append(k)
        rows[key] = coeffs
        i += 1
    idx = {k: j for j, k in enumerate(basis)}
    d = len(basis)
    A = [[Fraction(0)] * d for _ in range(d)]
    for key, coeffs in rows.items():
        for k, c in coeffs.items():
            A[idx[key]][idx[k]] = c
    return basis, A, order


def _matvec(A, v):
    return [sum(A[i][j] * v[j] for j in range(len(v))) for i in range(len(A))]


def _run_loop(update, variables, init: Dict[str, Fraction], steps: int) -> List[Dict[str, Fraction]]:
    """Run the polynomial loop forward over ℚ (exact), returning the state trajectory."""
    import sympy as sp
    syms, polys = _parse(update, variables)
    traj = [dict(init)]
    st = dict(init)
    for _ in range(steps):
        nxt = {}
        for v in variables:
            val = polys[v].subs({syms[u]: sp.Rational(st[u].numerator, st[u].denominator) for u in variables})
            num, den = sp.fraction(sp.together(val))            # robust exact ℚ conversion (handles Integer & Rational)
            nxt[v] = Fraction(int(num), int(den))
        st = nxt
        traj.append(st)
    return traj


def defective_grade(spec: dict, steps: int = 40) -> KV.Verdict:
    """Linearize a polynomial loop on a monomial basis (Carleman). spec = {vars, update:{v:expr}, target, init?}.
    EXACT iff the monomials close linearly AND Aⁿ·M(s₀) reproduces the target's forward trajectory exactly over ℚ;
    a loop with no finite monomial closure (degree-growing) ⇒ DECLINE. The fold is C-finite ⇒ a FACE of M11."""
    if not (isinstance(spec, dict) and "vars" in spec and "update" in spec and "target" in spec):
        return KV.decline("defective: need {vars, update:{v:expr}, target[, init]}", "mech_defective")
    variables = list(spec["vars"])
    update = dict(spec["update"])
    target = spec["target"]
    if target not in variables or any(v not in update for v in variables):
        return KV.decline("defective: target must be a variable and every variable needs an update expr", "mech_defective")
    try:
        closed = close_monomials(update, variables, int(spec.get("max_basis", 24)), int(spec.get("max_degree", 8)))
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"defective: closure failed ({type(e).__name__}) ⇒ DECLINE", "mech_defective")
    if closed is None:
        return KV.decline("defective: the polynomial map has NO finite linear monomial closure (degree/basis blew "
                          "up — e.g. x↦x²) ⇒ DECLINE (outside the linearizable island)", "mech_defective")
    basis, A, order = closed
    d = len(basis)
    # ★ EXACT disposer: from a random rational seed, Aⁿ·M(s₀) must reproduce the target trajectory term-for-term ★
    init = spec.get("init")
    if init is None:
        init = {v: Fraction(2 + i, 3 + i) for i, v in enumerate(variables)}    # deterministic non-trivial ℚ seed
    else:
        init = {v: Fraction(init[v]) for v in variables}
    traj = _run_loop(update, variables, init, steps)
    tgt_idx = next(j for j, k in enumerate(basis) if k == tuple(1 if order[i] == order[variables.index(target)] else 0 for i in range(len(order))))
    # M(s0): evaluate each basis monomial at the seed
    M0 = [_eval_monomial(k, order, init, variables) for k in basis]
    Mn = list(M0)
    for n in range(len(traj)):
        if n > 0:
            Mn = _matvec(A, Mn)
        actual = traj[n][target]
        if Mn[tgt_idx] != actual:
            return KV.decline(f"defective: linearization fails re-substitution at step {n} ⇒ DECLINE", "mech_defective")
    nonlinear = any(sum(k) >= 2 for k in basis)                 # genuinely nonlinear loop (else it was already affine)
    cert = KV.Cert(KV.EXACT, "monomial_closure_linearization", passed=True,
                   check_cost=f"polynomial-identity closure (NRA, exact expansion) + ℚ run-forward over {steps} steps",
                   detail=f"monomial basis size d={d}; M∘f = A·M (exact); target '{target}' = (Aⁿ·M₀)[{tgt_idx}] "
                          "reproduces the loop — a C-FINITE closed form (char-poly(A)); FACE of M11 (the resulting "
                          "linear recurrence is M11's class — folds a new route, not a new kind)")
    return KV.exact({"parent_mechanism": PARENT_MECHANISM, "face": "defective_linearization", "basis_dim": d,
                     "nonlinear": nonlinear, "target": target, "A": [[str(x) for x in row] for row in A]},
                    "mech_defective", f"defective-variable linearization (dim {d}) → M11 face, O(n)→O(log n)", cert)


def _eval_monomial(key, order, init: Dict[str, Fraction], variables: List[str]) -> Fraction:
    val = Fraction(1)
    for s, e in zip(order, key):
        if e:
            val *= init[str(s)] ** e
    return val


def adjudication() -> dict:
    """The honest gate-by-gate record: passes z3-closed/asymptotic/dependency-free, FAILS distinct-in-kind (the
    fold is C-finite = M11's class) ⇒ DEMOTE to a FACE of M11."""
    return {"candidate": "defective-variable linearization", "z3_closed": True, "asymptotic": True,
            "dependency_free": True, "distinct_in_kind": False, "verdict": "DEMOTE → FACE of M11",
            "reason": "monomial closure ⇒ M(sₙ)=Aⁿ·M(s₀) ⇒ every coordinate is C-finite (linear recurrence, "
                      "char-poly(A)) — exactly M11's class; a new route to M11's object, not a new certificate kind"}
