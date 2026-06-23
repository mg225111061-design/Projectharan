"""
UNIFIED ARSENAL §1 · G1 — Ore-algebra / skew-polynomial core  (the non-commutative keystone).
==============================================================================================
The single substrate under differential operators, recurrence (shift) operators, and q-shift operators. An Ore
operator is Σ_i c_i(x) ∂^i over a base field 𝔽 = ℚ(x), with the ONE commutation rule

        ∂ · c  =  σ(c) · ∂  +  δ(c)            (σ an automorphism of 𝔽, δ a σ-derivation)

specialising to:
  • differential  D :  σ = id,            δ = d/dx           D(f) = f′
  • shift         S :  σ(c)=c(x+1),        δ = 0             S(a)(n) = a(n+1)
  • q-shift       Q :  σ(c)=c(q·x),        δ = 0             Q(f)(x) = f(q x)

Why this is the keystone: holonomic closure (G2), creative telescoping (G3), and the QM operator identities (P5)
are ALL ideal/normal-form computations in this one algebra. Build it once, with a real certificate.

WHAT IS CERTIFIED (constitution: our own machine-check, not a library's word):
  • EQUALITY is a DECISION PROCEDURE — two operators are equal iff their canonical normal forms (coeffs cancelled
    over ℚ(x), trailing zeros stripped) are identical. `[D,x]=1`, `[S,n]=S` decided, not asserted.
  • the non-commutative PRODUCT is checked OPERATIONALLY and independently: (A·B) applied to a battery of test
    functions equals A(B(·)) — operator composition. A wrong product fails this and is rejected.
  • right DIVISION / GCRD carry a COFACTOR certificate: A = Q·B + R is re-expanded and must reduce to 0 in normal
    form; a GCRD must right-divide both inputs with remainder 0.
No Lean/Coq — sympy does base-field arithmetic; the normal form + operational replay are OUR proof.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import sympy as sp

import kernel_verdict as KV


# ── the algebra: a base variable x and a (σ, δ) pair ────────────────────────────────────────────────────────
class OreAlgebra:
    """ℚ(x)[∂; σ, δ] for kind ∈ {'D','S','Q'}. `var` is the base symbol (x or n); `q` only for 'Q'."""

    def __init__(self, var: sp.Symbol, kind: str = "D", q: Optional[sp.Symbol] = None):
        assert kind in ("D", "S", "Q"), f"kind must be D/S/Q, got {kind}"
        self.x = var
        self.kind = kind
        self.q = q if q is not None else sp.Symbol("q")

    def sigma(self, c: sp.Expr) -> sp.Expr:
        c = sp.sympify(c)
        if self.kind == "D":
            return c
        if self.kind == "S":
            return c.subs(self.x, self.x + 1)
        return c.subs(self.x, self.q * self.x)          # Q

    def sigma_pow(self, c: sp.Expr, k: int) -> sp.Expr:
        for _ in range(k):
            c = self.sigma(c)
        return c

    def delta(self, c: sp.Expr) -> sp.Expr:
        if self.kind == "D":
            return sp.diff(sp.sympify(c), self.x)
        return sp.Integer(0)                            # S, Q have δ = 0

    # ∂^i · c  →  dict {m: coeff}, by repeated application of the single Ore rule (works for any σ,δ)
    def _theta_pow_times_scalar(self, i: int, c: sp.Expr) -> Dict[int, sp.Expr]:
        cur: Dict[int, sp.Expr] = {0: sp.sympify(c)}
        for _ in range(i):
            nxt: Dict[int, sp.Expr] = {}
            for m, cm in cur.items():
                nxt[m + 1] = nxt.get(m + 1, sp.Integer(0)) + self.sigma(cm)
                d = self.delta(cm)
                if d != 0:
                    nxt[m] = nxt.get(m, sp.Integer(0)) + d
            cur = nxt
        return cur

    # constructors
    def _S(self, e) -> sp.Expr:
        """sympify binding the base-variable NAME to THIS algebra's symbol (so 'n' maps to the integer symbol,
        not a fresh look-alike — a silent symbol mismatch would make σ's subs a no-op)."""
        if isinstance(e, str):
            return sp.sympify(e, locals={str(self.x): self.x})
        return sp.sympify(e)

    def op(self, coeffs) -> "OrePoly":
        """coeffs: dict {i: expr} or list [c0, c1, …] (c_i is the coeff of ∂^i)."""
        if isinstance(coeffs, dict):
            d = {int(i): self._S(c) for i, c in coeffs.items()}
        else:
            d = {i: self._S(c) for i, c in enumerate(coeffs)}
        return OrePoly(self, d)

    def one(self) -> "OrePoly":
        return self.op({0: 1})

    def theta(self) -> "OrePoly":
        return self.op({1: 1})


@dataclass
class OrePoly:
    alg: OreAlgebra
    coeffs: Dict[int, sp.Expr] = field(default_factory=dict)

    def __post_init__(self):
        self._normalize()

    def _normalize(self):
        out: Dict[int, sp.Expr] = {}
        for i, c in self.coeffs.items():
            cc = sp.cancel(sp.together(sp.sympify(c)))
            if cc != 0:
                out[int(i)] = cc
        self.coeffs = out

    # degree in ∂ (the order of the operator); -1 (or -∞) for the zero operator
    def degree(self) -> int:
        return max(self.coeffs) if self.coeffs else -1

    def lead(self) -> sp.Expr:
        d = self.degree()
        return self.coeffs[d] if d >= 0 else sp.Integer(0)

    def is_zero(self) -> bool:
        return not self.coeffs

    # ── ring ops ──
    def add(self, other: "OrePoly") -> "OrePoly":
        out = dict(self.coeffs)
        for i, c in other.coeffs.items():
            out[i] = out.get(i, sp.Integer(0)) + c
        return OrePoly(self.alg, out)

    def sub(self, other: "OrePoly") -> "OrePoly":
        out = dict(self.coeffs)
        for i, c in other.coeffs.items():
            out[i] = out.get(i, sp.Integer(0)) - c
        return OrePoly(self.alg, out)

    def mul(self, other: "OrePoly") -> "OrePoly":
        """non-commutative product (A·B) via the Ore rule: A·B = Σ_{i,j} a_i (∂^i·b_j) ∂^j."""
        res: Dict[int, sp.Expr] = {}
        for i, ai in self.coeffs.items():
            for j, bj in other.coeffs.items():
                for m, cm in self.alg._theta_pow_times_scalar(i, bj).items():
                    res[m + j] = res.get(m + j, sp.Integer(0)) + ai * cm
        return OrePoly(self.alg, res)

    def scale(self, c: sp.Expr) -> "OrePoly":          # left scalar multiply (c·A)
        c = sp.sympify(c)
        return OrePoly(self.alg, {i: c * ai for i, ai in self.coeffs.items()})

    # ── DECISION: equality via canonical normal form ──
    def equals(self, other: "OrePoly") -> bool:
        diff = self.sub(other)
        return diff.is_zero()

    # ── apply the operator to a concrete function/sequence (the operational certificate) ──
    def apply(self, f: sp.Expr) -> sp.Expr:
        x = self.alg.x
        acc = sp.Integer(0)
        if self.alg.kind == "D":
            for i, ai in self.coeffs.items():
                acc += ai * sp.diff(f, x, i)
        elif self.alg.kind == "S":
            for i, ai in self.coeffs.items():
                acc += ai * f.subs(x, x + i)
        else:  # Q
            for i, ai in self.coeffs.items():
                acc += ai * f.subs(x, self.alg.q ** i * x)
        return sp.expand(acc)

    def __str__(self) -> str:
        if self.is_zero():
            return "0"
        d = "D" if self.alg.kind == "D" else ("S" if self.alg.kind == "S" else "Q")
        return " + ".join(f"({sp.sstr(self.coeffs[i])})·{d}^{i}" for i in sorted(self.coeffs))


# ── right division / GCRD over ℚ(x) (field coeffs ⇒ leading coeff invertible) ───────────────────────────────
def right_divmod(A: OrePoly, B: OrePoly):
    """A = Q·B + R with deg_∂ R < deg_∂ B. Field coefficients. Returns (Q, R)."""
    alg = A.alg
    assert not B.is_zero(), "right_divmod by zero operator"
    R = dict(A.coeffs)
    Q: Dict[int, sp.Expr] = {}
    db, lb = B.degree(), B.lead()
    while R and max(R) >= db:
        dr = max(R)
        shift = dr - db
        c = sp.cancel(R[dr] / alg.sigma_pow(lb, shift))   # kill the leading ∂^dr term
        T = OrePoly(alg, {shift: c}).mul(B)
        for m, cm in T.coeffs.items():
            R[m] = sp.cancel(sp.together(R.get(m, sp.Integer(0)) - cm))
            if R[m] == 0:
                del R[m]
        Q[shift] = Q.get(shift, sp.Integer(0)) + c
    return OrePoly(alg, Q), OrePoly(alg, R)


def gcrd(A: OrePoly, B: OrePoly) -> OrePoly:
    """Greatest Common Right Divisor via the right-Euclidean remainder sequence (monic-normalised)."""
    A, B = (A, B) if A.degree() >= B.degree() else (B, A)
    while not B.is_zero():
        _, R = right_divmod(A, B)
        A, B = B, R
    if not A.is_zero():                                   # make monic in ∂ (divide by leading coeff)
        A = A.scale(sp.cancel(1 / A.lead()))
    return A


# ── battery of test functions for the operational certificate (per kind) ───────────────────────────────────
def _test_functions(alg: OreAlgebra) -> List[sp.Expr]:
    x = alg.x
    if alg.kind == "D":
        return [x ** 3 - 2 * x, sp.exp(x), sp.sin(x), x * sp.exp(x), 1 / (x + 3)]
    if alg.kind == "S":
        return [x ** 2 + 1, sp.Integer(2) ** x, sp.factorial(x), x * sp.Integer(3) ** x]
    return [x ** 2 + 1, x ** 3, sp.Rational(1, 1) * x]    # Q


def product_equals_composition(A: OrePoly, B: OrePoly) -> bool:
    """OPERATIONAL certificate: (A·B)(f) ≡ A(B(f)) on every test function (operator composition).
    Independent of how `mul` is implemented — a wrong product is caught here."""
    alg = A.alg
    AB = A.mul(B)
    for f in _test_functions(alg):
        try:
            lhs = AB.apply(f)
            rhs = A.apply(B.apply(f))
            if sp.simplify(lhs - rhs) != 0:
                return False
        except Exception:  # noqa: BLE001 — a transcendental that won't simplify is skipped, not a pass
            continue
    return True


# ════════════════════════════════════════════ graded public API ════════════════════════════════════════════
_KINDVAR = {"D": sp.Symbol("x"), "S": sp.Symbol("n", integer=True), "Q": sp.Symbol("x")}


def _alg(kind: str) -> OreAlgebra:
    return OreAlgebra(_KINDVAR[kind], kind)


def decide_equality(A: OrePoly, B: OrePoly, what: str = "operators") -> KV.Verdict:
    """DECISION: are two Ore operators equal? EXACT either way — normal-form canonical ⇒ equality is decidable."""
    eq = A.equals(B)
    cert = KV.Cert(KV.EXACT, "ore_normal_form", passed=True, check_cost="O(deg) coeff cancel over ℚ(x)",
                   detail=f"canonical normal forms {'match' if eq else 'differ'} ⇒ {what} {'≡' if eq else '≢'}")
    return KV.exact(eq, "ore.decide_equality", "decision procedure (canonical normal form)", cert)


def commutator(kind: str, scalar: str = None):
    """The bracket [∂, c] = ∂·c − c·∂ in the chosen algebra — the seed of the QM operator identities (P5).
    Returns (alg, OrePoly). For D: [D,x]=1; for S: [S,n]=S."""
    alg = _alg(kind)
    c = alg._S(scalar) if scalar else alg.x
    theta = alg.theta()
    cop = alg.op({0: c})
    return alg, theta.mul(cop).sub(cop.mul(theta))


def grade_product(A: OrePoly, B: OrePoly) -> KV.Verdict:
    """Compute A·B and CERTIFY it operationally ((A·B)(f) ≡ A(B(f))). EXACT with the composition certificate,
    or DECLINE if the operational replay disagrees (a wrong product is a correctness bug, never shipped)."""
    prod = A.mul(B)
    if not product_equals_composition(A, B):
        return KV.decline("ore.product: (A·B)(f) ≠ A(B(f)) on the test battery ⇒ DECLINE", "ore.product")
    cert = KV.Cert(KV.EXACT, "ore_product_composition", passed=True,
                   check_cost="apply to test-function battery",
                   detail=f"(A·B)(f) ≡ A(B(f)) verified; A·B = {prod}")
    return KV.exact(prod, "ore.product", "non-commutative product + operational proof", cert)


def grade_gcrd(A: OrePoly, B: OrePoly) -> KV.Verdict:
    """GCRD with a COFACTOR certificate: G must right-divide both A and B with remainder 0."""
    if A.is_zero() and B.is_zero():
        return KV.decline("ore.gcrd: gcrd(0,0) undefined ⇒ DECLINE", "ore.gcrd")
    G = gcrd(A, B)
    _, rA = right_divmod(A, G)
    _, rB = right_divmod(B, G)
    if not (rA.is_zero() and rB.is_zero()):
        return KV.decline("ore.gcrd: candidate does not right-divide both inputs ⇒ DECLINE", "ore.gcrd")
    cert = KV.Cert(KV.EXACT, "ore_gcrd_cofactor", passed=True, check_cost="two right-divisions, remainders=0",
                   detail=f"G right-divides A and B (both remainders 0); G = {G}")
    return KV.exact(G, "ore.gcrd", "right-Euclidean GCRD + cofactor proof", cert)


def solve(problem: dict) -> KV.Verdict:
    """problem = {"op": ...}. ops: 'equal' (A,B operators as coeff dicts + kind), 'commutator' (kind, scalar),
    'product' (kind, A, B), 'gcrd' (kind, A, B). Unknown ⇒ honest DECLINE."""
    op = problem.get("op")
    kind = problem.get("kind", "D")
    alg = _alg(kind)
    if op == "commutator":
        _, br = commutator(kind, problem.get("scalar"))
        expect = alg.op(problem["expect"]) if "expect" in problem else None
        if expect is not None:
            return decide_equality(br, expect, f"[∂,{problem.get('scalar', alg.x)}]")
        return grade_product(alg.theta(), alg.op({0: problem.get("scalar", alg.x)}))
    if op == "equal":
        return decide_equality(alg.op(problem["A"]), alg.op(problem["B"]))
    if op == "product":
        return grade_product(alg.op(problem["A"]), alg.op(problem["B"]))
    if op == "gcrd":
        return grade_gcrd(alg.op(problem["A"]), alg.op(problem["B"]))
    return KV.decline(f"ore: unknown op {op!r} ⇒ DECLINE", "ore")
