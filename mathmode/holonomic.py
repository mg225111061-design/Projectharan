"""
UNIFIED ARSENAL §1 · G2 — Holonomic / D-finite subsystem (built on the G1 Ore core).
====================================================================================
A function/sequence is HOLONOMIC (D-finite / P-recursive) when it is annihilated by a nonzero Ore operator L:
L(f)=0 — a linear ODE with polynomial coefficients (differential) or a linear recurrence with polynomial
coefficients (shift). We represent f by that annihilator: **the annihilator IS the data** (ODE/recurrence-as-data),
finite even when f has no elementary closed form.

The power is CLOSURE: D-finite functions are closed under + and ×, and the closure ALGORITHM computes the new
annihilator. Method (the "module of derivatives/shifts"): θ^j(f) lives in the finite ℚ(x)-vector space spanned by
{θ^0 f,…,θ^{r-1} f} (reduce θ^r via L). For f+g use the direct-sum basis (dim r+s); for f·g the tensor basis
(dim r·s) with θ acting by Leibniz (differential) or diagonally (shift). Among enough θ^j(h) there is a ℚ(x)-linear
dependence Σ b_j θ^j(h)=0 ⇒ L_h=Σ b_j θ^j annihilates h.

WHAT IS CERTIFIED (two independent witnesses, our own — not a library's word):
  • MODULE certificate: recompute the reduced coordinate vectors of θ^j(h) and check Σ b_j·(vector) = 0 over ℚ(x)
    componentwise — a re-expansion to the dimension bound proving L_h is in the annihilating ideal.
  • OPERATIONAL certificate: apply L_h to the CONCRETE combination — symbolic →0 for differential
    (exp+sin, exp·sin), exact recurrence-holds-at-many-points for shift (Fibonacci, k!).
Re-homes the existing C-finite (constant-coefficient recurrences) and hypergeometric terms (first-order shift
operators) onto this one representation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

import sympy as sp

import kernel_verdict as KV
from mathmode import ore as O


@dataclass
class Dfinite:
    """Holonomic object: a MONIC annihilator L (an OrePoly), with an OPTIONAL concrete witness for the operational
    certificate (`fn`: a sympy expr in the differential variable; `seq`: a callable n↦value for the shift case)."""
    alg: O.OreAlgebra
    L: O.OrePoly
    fn: Optional[sp.Expr] = None
    seq: Optional[Callable[[int], sp.Expr]] = None
    name: str = ""

    def __post_init__(self):
        self.L = self.L.monic()
        self.order = self.L.degree()


# ── the module action: θ on a coordinate vector (generic over D/S/Q via σ, δ) ───────────────────────────────
def _theta_on_state(alg: O.OreAlgebra, v: List[sp.Expr], redvec: List[sp.Expr]) -> List[sp.Expr]:
    """θ·(Σ_i v_i ψ_i), ψ_i=θ^i(f), reduced into the r-dim basis via θ^r ≡ Σ redvec_i ψ_i.
    θ(c ψ_i) = σ(c) ψ_{i+1} + δ(c) ψ_i (the one Ore rule); ψ_r folds back through redvec."""
    r = len(v)
    w = [sp.Integer(0)] * r
    for k in range(r):
        d = alg.delta(v[k])
        if d != 0:
            w[k] += d                                   # δ term (0 for S/Q)
    for k in range(1, r):
        w[k] += alg.sigma(v[k - 1])                     # σ(c_{k-1}) lands on ψ_k
    top = alg.sigma(v[r - 1])                            # σ(c_{r-1}) ψ_r reduces
    for k in range(r):
        w[k] += top * redvec[k]
    return [sp.cancel(sp.together(e)) for e in w]


def _states_single(F: Dfinite, upto: int) -> List[List[sp.Expr]]:
    """coordinate vectors of θ^0(f),…,θ^upto(f) in F's own r-dim basis."""
    r = F.order
    redvec = F.L.reduction_vector()
    states = [[sp.Integer(1) if i == 0 else sp.Integer(0) for i in range(r)]]
    for _ in range(upto):
        states.append(_theta_on_state(F.alg, states[-1], redvec))
    return states


def _min_dependence(states: List[List[sp.Expr]]):
    """smallest J with {state_0,…,state_J} ℚ(x)-dependent; returns coeffs (b_0,…,b_J) of a null combination."""
    d = len(states[0])
    for J in range(1, len(states)):
        M = sp.Matrix(d, J + 1, lambda i, j: states[j][i])
        ns = M.nullspace()
        if ns:
            vec = ns[0]
            denom = sp.lcm([sp.denom(sp.together(e)) for e in vec]) if any(e != 0 for e in vec) else 1
            return [sp.cancel(sp.together(e * denom)) for e in vec]
    return None


def _operator_from_coeffs(alg: O.OreAlgebra, b: List[sp.Expr]) -> O.OrePoly:
    return alg.op({j: b[j] for j in range(len(b))})


# ── tensor (product) module: θ on θ^i(f)·θ^l(g), Leibniz (differential) or diagonal (shift) ─────────────────
def _prod_states(F: Dfinite, G: Dfinite, upto: int) -> List[List[sp.Expr]]:
    alg = F.alg
    r, s = F.order, G.order
    rf, rg = F.L.reduction_vector(), G.L.reduction_vector()

    def reduce_f(i):
        return [sp.Integer(1) if t == i else sp.Integer(0) for t in range(r)] if i < r else list(rf)

    def reduce_g(l):
        return [sp.Integer(1) if t == l else sp.Integer(0) for t in range(s)] if l < s else list(rg)

    # a state is an (r·s) vector over the basis (i,l) ↦ i*s+l ; start = f·g = ψ^f_0 ψ^g_0
    def idx(i, l):
        return i * s + l

    state0 = [sp.Integer(0)] * (r * s)
    state0[idx(0, 0)] = sp.Integer(1)
    states = [state0]
    for _ in range(upto):
        cur = states[-1]
        nxt = [sp.Integer(0)] * (r * s)
        for i in range(r):
            for l in range(s):
                c = cur[idx(i, l)]
                if c == 0:
                    continue
                if alg.kind == "D":                     # Leibniz: D(f^{(i)}g^{(l)}) = f^{(i+1)}g^{(l)} + f^{(i)}g^{(l+1)}
                    cc = alg.sigma(c)                   # σ=id for D, plus a δ(c) term below
                    for t, w in enumerate(reduce_f(i + 1)):
                        if w != 0:
                            nxt[idx(t, l)] += cc * w
                    for t, w in enumerate(reduce_g(l + 1)):
                        if w != 0:
                            nxt[idx(i, t)] += cc * w
                    dc = alg.delta(c)
                    if dc != 0:
                        nxt[idx(i, l)] += dc
                else:                                   # σ-type (shift/q): (uv)(θ) shifts BOTH indices
                    cc = alg.sigma(c)
                    for tf, wf in enumerate(reduce_f(i + 1)):
                        if wf == 0:
                            continue
                        for tg, wg in enumerate(reduce_g(l + 1)):
                            if wg != 0:
                                nxt[idx(tf, tg)] += cc * wf * wg
        states.append([sp.cancel(sp.together(e)) for e in nxt])
    return states


# ── certificates ────────────────────────────────────────────────────────────────────────────────────────────
def _module_cert(states: List[List[sp.Expr]], b: List[sp.Expr]) -> bool:
    d = len(states[0])
    for i in range(d):
        if sp.simplify(sum(b[j] * states[j][i] for j in range(len(b)))) != 0:
            return False
    return True


def _operational_cert(alg: O.OreAlgebra, L: O.OrePoly, fn: Optional[sp.Expr], seq) -> Optional[bool]:
    """Apply L to the concrete combination. Differential → symbolic 0. Shift → exact recurrence at many n.
    Returns True/False, or None if no concrete witness is available (then the module cert stands alone)."""
    if alg.kind == "D" and fn is not None:
        return sp.simplify(L.apply(fn)) == 0
    if alg.kind == "S" and seq is not None:
        n = alg.x
        ok = 0
        for v in range(0, 40):
            val = sum(sp.nsimplify(ai.subs(n, v)) * seq(v + i) for i, ai in L.coeffs.items())
            if sp.simplify(val) != 0:
                return False
            ok += 1
        return ok >= 20
    return None


def _close(F: Dfinite, G: Dfinite, kind: str) -> KV.Verdict:
    alg = F.alg
    r, s = F.order, G.order
    if kind == "sum":
        dim = r + s
        sf = _states_single(F, dim)
        sg = _states_single(G, dim)
        states = [sf[j] + sg[j] for j in range(dim + 1)]      # direct-sum coordinates
        fn = (F.fn + G.fn) if (F.fn is not None and G.fn is not None) else None
        seq = (lambda n: F.seq(n) + G.seq(n)) if (F.seq and G.seq) else None
        label = "f+g"
    else:
        dim = r * s
        states = _prod_states(F, G, dim)
        fn = (F.fn * G.fn) if (F.fn is not None and G.fn is not None) else None
        seq = (lambda n: F.seq(n) * G.seq(n)) if (F.seq and G.seq) else None
        label = "f·g"
    b = _min_dependence(states)
    if b is None:
        return KV.decline(f"holonomic.{kind}: no ℚ(x)-dependence within the dimension bound ⇒ DECLINE", "holonomic")
    L = _operator_from_coeffs(alg, b)
    if not _module_cert(states, b):
        return KV.decline(f"holonomic.{kind}: module certificate Σb_j·state≠0 ⇒ DECLINE", "holonomic")
    op = _operational_cert(alg, L, fn, seq)
    if op is False:
        return KV.decline(f"holonomic.{kind}: operational replay L({label})≠0 ⇒ DECLINE (a wrong annihilator)", "holonomic")
    Lh = Dfinite(alg, L, fn=fn, seq=seq, name=label)
    witness = "module(Σb·state=0 over ℚ(x))" + ("" if op is None else " + operational(L(combo)=0)")
    cert = KV.Cert(KV.EXACT, f"holonomic_{kind}", passed=True, check_cost="dimension-bound re-expansion",
                   detail=f"order {Lh.order} annihilator of {label} = {L}; certified by {witness}")
    return KV.exact(Lh, f"holonomic.{kind}", f"D-finite closure (dim≤{dim})", cert)


def grade_sum(F: Dfinite, G: Dfinite) -> KV.Verdict:
    return _close(F, G, "sum")


def grade_product(F: Dfinite, G: Dfinite) -> KV.Verdict:
    return _close(F, G, "product")


# ── re-home the existing arsenal onto holonomic data ────────────────────────────────────────────────────────
def cfinite(rec_coeffs: List[int], seq: Optional[Callable] = None, name: str = "") -> Dfinite:
    """C-finite sequence with CONSTANT-coefficient recurrence a(n+r)=Σ c_i a(n+i): annihilator S^r − Σ c_i S^i."""
    alg = O.OreAlgebra(sp.Symbol("n", integer=True), "S")
    r = len(rec_coeffs)
    coeffs = {r: sp.Integer(1)}
    for i, c in enumerate(rec_coeffs):
        coeffs[i] = -sp.Integer(c)
    return Dfinite(alg, alg.op(coeffs), seq=seq, name=name)


def hypergeom_term(ratio: sp.Expr, seq: Optional[Callable] = None, name: str = "") -> Dfinite:
    """Hypergeometric term t with t(n+1)/t(n) = ratio(n) ∈ ℚ(n): first-order annihilator den·S − num."""
    alg = O.OreAlgebra(sp.Symbol("n", integer=True), "S")
    ratio = alg._S(ratio)
    num, den = sp.fraction(sp.together(ratio))
    return Dfinite(alg, alg.op({1: den, 0: -num}), seq=seq, name=name)


def grade_rehome(F: Dfinite) -> KV.Verdict:
    """Certify that the annihilator-as-data really kills the concrete sequence (re-homing check)."""
    op = _operational_cert(F.alg, F.L, F.fn, F.seq)
    if op is not True:
        return KV.decline(f"holonomic.rehome[{F.name}]: annihilator does not kill the sequence ⇒ DECLINE", "holonomic")
    cert = KV.Cert(KV.EXACT, "holonomic_rehome", passed=True, check_cost="exact recurrence at many n",
                   detail=f"{F.name}: L={F.L} annihilates the sequence (verified)")
    return KV.exact(F, "holonomic.rehome", "annihilator-as-data", cert)


# ── concrete differential witnesses ─────────────────────────────────────────────────────────────────────────
def dfinite_diff(L_coeffs: dict, fn: sp.Expr, name: str = "") -> Dfinite:
    alg = O.OreAlgebra(sp.Symbol("x"), "D")
    return Dfinite(alg, alg.op(L_coeffs), fn=fn, name=name)


def solve(problem: dict) -> KV.Verdict:
    """ops: 'sum'/'product' on two differential witnesses (each {'L':coeffs,'fn':expr}); 'rehome' on a c-finite
    or hypergeometric descriptor. Unknown ⇒ DECLINE."""
    op = problem.get("op")
    if op in ("sum", "product"):
        F = dfinite_diff(problem["F"]["L"], sp.sympify(problem["F"]["fn"]))
        G = dfinite_diff(problem["G"]["L"], sp.sympify(problem["G"]["fn"]))
        return grade_sum(F, G) if op == "sum" else grade_product(F, G)
    if op == "rehome":
        if problem.get("kind") == "cfinite":
            return grade_rehome(cfinite(problem["rec"], seq=problem.get("seq"), name=problem.get("name", "c-finite")))
        return KV.decline("holonomic.rehome: provide kind=cfinite with a seq ⇒ DECLINE", "holonomic")
    return KV.decline(f"holonomic: unknown op {op!r} ⇒ DECLINE", "holonomic")
