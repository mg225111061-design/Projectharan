"""
UNIFIED ARSENAL §1 · G4 — Schneider ΠΣ* difference-ring layer (on the G1 idea of a (ring, σ) automorphism).
==========================================================================================================
Gosper/Zeilberger/holonomic close hypergeometric and D-finite objects — but NOT nested sums like the harmonic
numbers H_n = Σ_{k≤n} 1/k, which are transcendental over ℚ(n). Karr/Schneider ΠΣ*-theory handles them by working
in a DIFFERENCE RING (𝔻, σ): σ an automorphism, with
  • a Σ-extension adjoining t with σ(t) = t + f   (a sum, t = Σ f), and
  • a Π-extension adjoining t with σ(t) = u·t      (a product).

The canonical Σ-tower here is ℚ(n)[H] with σ(n)=n+1 and σ(H)=H + 1/(n+1)  (so H ≙ H_n, σ(H)=H_{n+1}). The crown
problem — TELESCOPING in the tower: given f ∈ ℚ(n)[H], DECIDE whether some g ∈ ℚ(n)[H] has σ(g) − g = f (then
Σ f telescopes to g). Karr's algorithm solves it by a triangular descent through the H-degree, each layer a
first-order rational difference equation Δc = rhs whose RATIONAL solvability is itself decidable.

WHAT IS CERTIFIED (our own machine-check via the field automorphism):
  • DECISION: g found ⇒ EXACT; a layer whose Δc=rhs has NO rational solution (a simple pole — e.g. Σ 1/k itself)
    ⇒ honest DECLINE "needs a Σ-extension" (the ΠΣ* boundary), never a fabricated closed form.
  • the certificate is σ(g) − g − f ≡ 0 in ℚ(n)[H] (apply σ as the ring automorphism, simplify to 0) PLUS a
    numeric telescoping cross-check on the REAL harmonic values (g(n+1)−g(n)=f(n) over many n).
Honest scope (§X): the polynomial-coefficient single-Σ harmonic tower (degree in H arbitrary; coefficients in
ℚ(n) with rational-summable layers). Deeper ΠΣ* towers / nested Σ / Π-extensions are flagged future.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import sympy as sp

import kernel_verdict as KV

_n = sp.Symbol("n")
_H = sp.Symbol("H")          # H ≙ H_n, the first harmonic Σ-extension


def _sigma(E: sp.Expr) -> sp.Expr:
    """The difference-ring automorphism σ on ℚ(n)[H]: σ(c(n)·H^i) = c(n+1)·(H + 1/(n+1))^i (n inside 1/(n+1)
    is the BASE n, not shifted). Implemented by collecting in H and shifting coefficients."""
    E = sp.expand(E)
    p = sp.Poly(E, _H)
    out = sp.Integer(0)
    sigmaH = _H + sp.Rational(1, 1) / (_n + 1)
    for (i,), c in p.terms():
        out += c.subs(_n, _n + 1) * sigmaH ** i
    return sp.expand(out)


def telescope(f: sp.Expr, max_ndeg: int = 4) -> KV.Verdict:
    """DECIDE telescoping in ℚ(n)[H]: find g with σ(g)−g=f, or honest DECLINE. Method: a direct LINEAR ANSATZ
    g = Σ_{i≤D, a≤A} g_{i,a} n^a H^i with rational unknowns, expand σ(g)−g−f, clear the (n+1) denominators, and
    solve the resulting linear system over ℚ (this automatically resolves the per-layer free-constant coupling
    that makes Σ H_k² telescope). EXACT with the automorphism + numeric certificate. f is in n and H (H ≙ H_n).
    Honest scope (§X): polynomial-in-n coefficients up to degree max_ndeg; no solution there ⇒ honest DECLINE
    (not a non-existence claim) — deeper towers / rational coefficients are future work."""
    f = sp.expand(sp.sympify(f, locals={"n": _n, "H": _H}))
    D = sp.Poly(f, _H).degree() if f.has(_H) else 0
    for A in range(0, max_ndeg + 1):
        gco = sp.symbols(f"g0:{(D + 1) * (A + 1)}")
        g = sum(gco[i * (A + 1) + a] * _n ** a * _H ** i for i in range(D + 1) for a in range(A + 1))
        eq = _sigma(g) - g - f
        num = sp.numer(sp.together(eq))                    # eq ≡ 0  ⟺  numerator ≡ 0 over ℚ[n,H]
        try:
            sys = sp.Poly(sp.expand(num), _n, _H).coeffs()  # each coeff is linear in the unknowns
        except sp.PolynomialError:
            continue
        sol = sp.linsolve(sys, gco)
        if not sol or sol == sp.S.EmptySet:
            continue
        vals = list(sol)[0]
        subs = {gco[i]: (vals[i] if not vals[i].free_symbols else sp.Integer(0)) for i in range(len(gco))}
        g_sol = sp.expand(g.subs(subs))
        if sp.simplify(_sigma(g_sol) - g_sol - f) == 0 and g_sol != 0 or (f == 0):
            g = g_sol
            break
    else:
        return KV.decline(f"pisigma.telescope: no telescoper with poly coeffs (deg≤{max_ndeg}) ⇒ DECLINE (not a "
                          "non-existence claim; deeper ΠΣ* towers / rational coeffs are future work)", "pisigma")
    # CERTIFICATE 1: automorphism identity σ(g) − g − f ≡ 0 over ℚ(n)[H]
    if sp.simplify(_sigma(g) - g - f) != 0:
        return KV.decline("pisigma.telescope: σ(g)−g ≠ f under the automorphism ⇒ DECLINE", "pisigma")
    # CERTIFICATE 2: numeric telescoping on REAL harmonic values
    def Hn(m):
        return sum(sp.Rational(1, j) for j in range(1, m + 1))
    bad = 0
    for m in range(1, 18):
        lhs = (g.subs({_n: m + 1, _H: Hn(m + 1)}) - g.subs({_n: m, _H: Hn(m)}))
        rhs = f.subs({_n: m, _H: Hn(m)})
        if sp.nsimplify(lhs - rhs) != 0:
            bad += 1
    if bad:
        return KV.decline(f"pisigma.telescope: numeric telescoping fails at {bad} points ⇒ DECLINE", "pisigma")
    cert = KV.Cert(KV.EXACT, "pisigma_telescoping", passed=True, check_cost="σ-automorphism identity + numeric",
                   detail=f"g = {sp.sstr(g)} with σ(g)−g ≡ f over ℚ(n)[H]; verified numerically on H_n values")
    return KV.exact(g, "pisigma.telescope", "ΠΣ* telescoping (DECISION in ℚ(n)[H])", cert)


def definite_sum(f: sp.Expr, lo: int = 1) -> KV.Verdict:
    """Σ_{k=lo}^{n} f(k) via ΠΣ* telescoping: = g(n+1) − g(lo) where σ(g)−g=f. EXACT closed form (in n, H_n) or
    honest DECLINE. (f uses H ≙ H_k, n ≙ k as the running index.)"""
    tv = telescope(f)
    if tv.status != KV.EXACT:
        return tv
    g = tv.result
    g_lo = g.subs({_n: lo, _H: sum(sp.Rational(1, j) for j in range(1, lo + 1))})
    closed = sp.simplify(_sigma(g) - g_lo)        # g(n+1) ≡ σ(g) by definition of the shift
    cert = KV.Cert(KV.EXACT, "pisigma_definite", passed=True, check_cost="telescoping g(n+1)−g(lo)",
                   detail=f"Σ_(k={lo}..n) f = {sp.sstr(closed)} (H ≙ H_n); telescoping certificate verified")
    return KV.exact(closed, "pisigma.definite_sum", "ΠΣ* definite summation", cert)


def solve(problem: dict) -> KV.Verdict:
    """ops: 'telescope' (f in n,H), 'definite_sum' (f in n≙k, H≙H_k, optional lo). DECLINE otherwise."""
    op = problem.get("op")
    if op == "telescope":
        return telescope(problem["f"])
    if op == "definite_sum":
        return definite_sum(sp.sympify(problem["f"], locals={"n": _n, "H": _H}), problem.get("lo", 1))
    return KV.decline(f"pisigma: unknown op {op!r} ⇒ DECLINE", "pisigma")
