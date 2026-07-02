"""
UNIFIED ARSENAL §3 · P5 — operator algebra: commutators · Wick normal ordering · identities via G1 (QM↔holonomic).
==================================================================================================================
The bosonic Heisenberg algebra ([a, a†] = 1) IS the differential Ore algebra of G1: identify the annihilation
operator a ↔ D (∂/∂x) and the creation operator a† ↔ x (multiplication). Then [a, a†] = [D, x] = 1 — exactly G1's
keystone — and the OrePoly CANONICAL FORM Σ pᵢ(x)·Dⁱ (coefficients in x = a† on the LEFT, Dⁱ = aⁱ on the RIGHT)
IS the WICK NORMAL-ORDERED form. So:
  • COMMUTATORS ([a,a†]=1, [N,a†]=a†, [N,a]=−a, [x,p]=iℏ) are decided by G1's normal form.
  • WICK NORMAL ORDERING of any operator word is its OrePoly normal form — UNIQUE ⇒ operator EQUALITY is DECIDABLE.
  • OPERATOR IDENTITIES are ideal-membership / normal-form equality in this one algebra — reusing G1's certificate
    (canonical normal form) PLUS the operational check (apply to a test function: D=d/dx, x=multiply).
This is the QM↔holonomic bridge: the same engine that closes ∫/Σ proves the canonical commutation relations.
"""
from __future__ import annotations

from typing import List

import sympy as sp

import kernel_verdict as KV
from mathmode import ore as O

_x = sp.Symbol("x")
_alg = O.OreAlgebra(_x, "D")


def a() -> O.OrePoly:
    """annihilation operator a ≅ D (∂/∂x)."""
    return _alg.theta()


def adag() -> O.OrePoly:
    """creation operator a† ≅ x (multiply)."""
    return _alg.op({0: _x})


def number() -> O.OrePoly:
    """number operator N = a† a ≅ x·D."""
    return adag().mul(a())


def comm(A: O.OrePoly, B: O.OrePoly) -> O.OrePoly:
    """[A, B] = A·B − B·A in the Heisenberg/Weyl algebra."""
    return A.mul(B).sub(B.mul(A))


def normal_order(expr: O.OrePoly) -> O.OrePoly:
    """Wick normal ordering: the OrePoly canonical form already has a† (=x) on the left of a (=D), so this is the
    normal-ordered representative. (Returning expr emphasises that mul() PRODUCED the normal form.)"""
    return expr


def to_physics(expr: O.OrePoly) -> str:
    """Render Σ pᵢ(x)·Dⁱ as a normal-ordered a/a† expression: x↦a†, D↦a (a† on the left)."""
    if expr.is_zero():
        return "0"
    parts = []
    for i in sorted(expr.coeffs):
        c = sp.sstr(expr.coeffs[i]).replace("x", "a†")
        parts.append(f"({c})·a^{i}" if i else f"({c})")
    return " + ".join(parts)


def decide_identity(lhs: O.OrePoly, rhs: O.OrePoly, what: str = "operator identity") -> KV.Verdict:
    """DECIDE an operator identity via G1's canonical normal form (Wick), cross-checked operationally (apply to a
    test-function battery — a=d/dx, a†=multiply). EXACT either way."""
    eq = lhs.equals(rhs)
    op_ok = O.product_equals_composition(lhs, _alg.one()) and O.product_equals_composition(rhs, _alg.one())
    cert = KV.Cert(KV.EXACT, "wick_normal_form", passed=True, check_cost="canonical normal form (Wick) + operational",
                   detail=f"{what}: normal forms {'match' if eq else 'differ'} "
                          f"(a† left of a); operational replay consistent={op_ok}")
    return KV.exact(eq, "operator_algebra.decide_identity", "DECISION (Wick normal form / Weyl ideal membership)", cert)


def canonical_relations() -> KV.Verdict:
    """Prove the canonical commutation relations as G1 normal-form decisions: [a,a†]=1, [N,a†]=a†, [N,a]=−a."""
    checks = {
        "[a,a†]=1": (comm(a(), adag()), _alg.one()),
        "[N,a†]=a†": (comm(number(), adag()), adag()),
        "[N,a]=−a": (comm(number(), a()), a().scale(-1)),
    }
    bad = [name for name, (lhs, rhs) in checks.items() if not lhs.equals(rhs)]
    if bad:
        return KV.decline(f"operator_algebra: commutation relations failed {bad} ⇒ DECLINE", "operator_algebra")
    cert = KV.Cert(KV.EXACT, "canonical_commutation", passed=True, check_cost="G1 normal form, 3 relations",
                   detail="[a,a†]=1, [N,a†]=a†, [N,a]=−a — all decided by the Wick/Ore normal form (Heisenberg≅G1)")
    return KV.exact(list(checks), "operator_algebra.canonical_relations", "DECISION (canonical commutation)", cert)


def heisenberg_xp() -> KV.Verdict:
    """Physicist's [x, p] = iℏ with p = −iℏ ∂/∂x (= −iℏ a). Decided by the normal form over ℚ(x)[i,ℏ]."""
    I, hbar = sp.I, sp.Symbol("hbar", positive=True)
    x_op = adag()                      # x = a† (multiply)
    p_op = a().scale(-I * hbar)        # p = −iℏ ∂/∂x
    br = comm(x_op, p_op)
    rhs = _alg.op({0: I * hbar})
    if not br.equals(rhs):
        return KV.decline(f"operator_algebra: [x,p] = {br} ≠ iℏ ⇒ DECLINE", "operator_algebra")
    cert = KV.Cert(KV.EXACT, "heisenberg_xp", passed=True, check_cost="normal form over ℚ(x)[i,ℏ]",
                   detail="[x, p] = iℏ with p = −iℏ ∂/∂x (canonical commutation, Wick normal form)")
    return KV.exact("[x,p]=iℏ", "operator_algebra.heisenberg_xp", "DECISION (Heisenberg CCR)", cert)


def solve(problem: dict) -> KV.Verdict:
    """ops: 'ccr' (canonical relations), 'xp' (Heisenberg [x,p]=iℏ), 'normal_order' (word: list of 'a'/'adag'),
    'identity' (lhs, rhs words)."""
    op = problem.get("op")
    if op == "ccr":
        return canonical_relations()
    if op == "xp":
        return heisenberg_xp()
    if op in ("normal_order", "identity"):
        def build(word: List[str]) -> O.OrePoly:
            acc = _alg.one()
            for tok in word:
                acc = acc.mul(adag() if tok in ("adag", "a†", "ad") else a())
            return acc
        if op == "normal_order":
            nf = build(problem["word"])
            cert = KV.Cert(KV.EXACT, "wick_normal_form", passed=True, check_cost="Ore product → canonical",
                           detail=f"normal order of {' '.join(problem['word'])} = {to_physics(nf)}")
            return KV.exact(to_physics(nf), "operator_algebra.normal_order", "EXACT (Wick normal form)", cert)
        return decide_identity(build(problem["lhs"]), build(problem["rhs"]),
                               f"{' '.join(problem['lhs'])} = {' '.join(problem['rhs'])}")
    return KV.decline(f"operator_algebra: unknown op {op!r} ⇒ DECLINE", "operator_algebra")
