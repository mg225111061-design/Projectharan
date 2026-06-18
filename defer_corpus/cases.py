"""
defer_corpus/cases.py — the FIXED measurement set of structured loops (STAGE 0).
================================================================================
Each case is a real loop the fold engine might close. Verdicts here are MEASURED (see __init__.baseline),
never assumed. `naive` is the ground-truth black box; `truth` is for audit/display only (never given to a
detector). `expect` honestly marks foldable vs defer (negative controls: Σ1/k, Airy, data-dependent).

Clock per category (directive §4 — never mixed):
  • multivariate-poly / q-holonomic / ode / combinatorial → Clock C  (the EMITTED code gets faster)
  • linear-algebra (matmul)                                → Clock B  (VERIFICATION gets cheaper, NOT compute)
"""
from __future__ import annotations

from fractions import Fraction

from .schema import DeferCase


# ── ground-truth black boxes (B1: sparse multivariate polynomials — evaluate-only) ──────────────────
def _p_2var_sparse(x, y):  return 5 * x**3 * y**2 + 3 * x * y + 7
def _p_3var(x, y, z):      return 2 * x**2 * y + y**3 * z + 1
def _p_dense_2var(x, y):   return x**2 + 2 * x * y + y**2          # (x+y)^2
def _p_1var_highdeg(x):    return 7 * x**5 + x**2 + 9
def _p_4var(a, b, c, d):   return a * b * c * d + 5
def _p_2var_medium(x, y):  return 4 * x**3 + 3 * x**2 * y + 2 * x * y**2 + y**3
def _np_intdiv(x, y):      return x // (y + 1)                    # NOT polynomial → B1 must DEFER
def _np_mod(x):            return x % 7                           # NOT polynomial → B1 must DEFER


# ── ground-truth q-series partial sums (B2). q fixed to a rational for numeric verification ─────────
def _q_partial_sum(term, n, qv):
    """Σ_{k=1}^{n} term(k) evaluated EXACTLY at q=qv (Fraction)."""
    q = Fraction(qv)
    return sum(term(k, q) for k in range(1, n + 1))

def _qt_geom(k, q):        return q**k
def _qt_telescope(k, q):   return q**k / ((1 - q**k) * (1 - q**(k + 1)))   # telescopes (q-Gosper win)
def _qt_telescope2(k, q):  return q**k - q**(k - 1)                        # = q^k - q^{k-1} (telescopes)
def _qt_theta(k, q):       return q**(k * k)                              # theta — NO closed form (defer)
def _qt_qharm(k, q):       return q**k / (1 - q**k)                       # q-harmonic-like — NO closed form


# ── ground-truth ODE reference integrators (A). Euler discretization u_{k+1}=u_k+φ Δx ──────────────
def _euler_2nd(p_fn, q_fn, x0, u0, du0, h, steps):
    """Integrate y'' + p(x)y' + q(x)y = 0 by explicit Euler; returns y at x0+steps*h (reference only)."""
    x, u, du = x0, u0, du0
    for _ in range(steps):
        ddu = -p_fn(x) * du - q_fn(x) * u
        u, du = u + h * du, du + h * ddu
        x += h
    return u


CASES = [
    # ─────────────── multivariate-poly  (B1 — Ben-Or–Tiwari, Clock C) ───────────────
    DeferCase("b1_2var_sparse", "multivariate-poly", "sparse poly 5x³y²+3xy+7 (black box)", "tune",
              "foldable", _p_2var_sparse, (("x", 0, 60), ("y", 0, 60)), truth="5*x**3*y**2 + 3*x*y + 7"),
    DeferCase("b1_1var_highdeg", "multivariate-poly", "sparse univariate 7x⁵+x²+9 (black box)", "tune",
              "foldable", _p_1var_highdeg, (("x", 0, 200),), truth="7*x**5 + x**2 + 9"),
    DeferCase("b1_3var", "multivariate-poly", "3-var 2x²y+y³z+1 (black box)", "measure",
              "foldable", _p_3var, (("x", 0, 40), ("y", 0, 40), ("z", 0, 40)), truth="2*x**2*y + y**3*z + 1"),
    DeferCase("b1_dense_2var", "multivariate-poly", "(x+y)² = x²+2xy+y² (black box)", "measure",
              "foldable", _p_dense_2var, (("x", 0, 80), ("y", 0, 80)), truth="x**2 + 2*x*y + y**2"),
    DeferCase("b1_4var", "multivariate-poly", "4-var abcd+5 (black box)", "measure",
              "foldable", _p_4var, (("a", 0, 25), ("b", 0, 25), ("c", 0, 25), ("d", 0, 25)), truth="a*b*c*d + 5"),
    DeferCase("b1_2var_medium", "multivariate-poly", "4-term 4x³+3x²y+2xy²+y³ (black box)", "measure",
              "foldable", _p_2var_medium, (("x", 0, 50), ("y", 0, 50)),
              truth="4*x**3 + 3*x**2*y + 2*x*y**2 + y**3"),
    DeferCase("b1_neg_intdiv", "multivariate-poly", "x//(y+1) — NOT polynomial (negative control)", "tune",
              "defer", _np_intdiv, (("x", 0, 50), ("y", 0, 50))),
    DeferCase("b1_neg_mod", "multivariate-poly", "x mod 7 — NOT polynomial (negative control)", "measure",
              "defer", _np_mod, (("x", 0, 50),)),

    # ─────────────── q-holonomic  (B2 — q-Gosper, Clock C) ───────────────
    DeferCase("b2_telescope", "q-holonomic", "Σ q^k/((1-q^k)(1-q^{k+1})) — telescopes (q-Gosper win)", "tune",
              "foldable", None, (), meta={"qterm": "q**k/((1-q**k)*(1-q**(k+1)))", "qref": _qt_telescope}),
    DeferCase("b2_qk_diff", "q-holonomic", "Σ (q^k - q^{k-1}) — q-telescoping", "tune",
              "foldable", None, (), meta={"qterm": "q**k - q**(k-1)", "qref": _qt_telescope2}),
    DeferCase("b2_geom", "q-holonomic", "Σ q^k — geometric (baseline already closes)", "measure",
              "foldable", None, (), haran="fn f(n: Nat) -> Nat { fold k in 1..n { q**k } }",
              meta={"qterm": "q**k", "qref": _qt_geom}),
    DeferCase("b2_neg_theta", "q-holonomic", "Σ q^(k²) — theta, NO closed form (negative control)", "measure",
              "defer", None, (), meta={"qterm": "q**(k*k)", "qref": _qt_theta}),
    DeferCase("b2_neg_qharm", "q-holonomic", "Σ q^k/(1-q^k) — q-harmonic, NO closed form (negative)", "measure",
              "defer", None, (), meta={"qterm": "q**k/(1-q**k)", "qref": _qt_qharm}),

    # ─────────────── ode  (A — differential-Galois / Kovacic, Clock C) ───────────────
    # y'' + p(x) y' + q(x) y = 0 ; meta p,q are sympy-parseable in x. Liouvillian ⇒ foldable.
    DeferCase("a_exp", "ode", "y'' - y = 0  → exp (Liouvillian)", "tune", "foldable", None, (),
              meta={"p": "0", "q": "-1", "kind": "constant-coeff"}),
    DeferCase("a_trig", "ode", "y'' + y = 0  → sin/cos (Liouvillian)", "tune", "foldable", None, (),
              meta={"p": "0", "q": "1", "kind": "constant-coeff"}),
    DeferCase("a_damped", "ode", "y'' + 3y' + 2y = 0 → exp (Liouvillian)", "measure", "foldable", None, (),
              meta={"p": "3", "q": "2", "kind": "constant-coeff"}),
    DeferCase("a_euler_cauchy", "ode", "x²y'' + x y' - y = 0 → x, 1/x (Liouvillian)", "measure", "foldable", None, (),
              meta={"p": "1/x", "q": "-1/x**2", "kind": "euler-cauchy"}),
    DeferCase("a_exp_shift", "ode", "y'' - 4y = 0 → exp(±2x) (Liouvillian)", "measure", "foldable", None, (),
              meta={"p": "0", "q": "-4", "kind": "constant-coeff"}),
    DeferCase("a_neg_airy", "ode", "y'' - x y = 0 → Airy, NON-Liouvillian (negative control)", "tune", "defer", None, (),
              meta={"p": "0", "q": "-x", "kind": "airy"}),
    DeferCase("a_neg_bessel", "ode", "y'' + (1/x)y' - y = 0 → Bessel, non-Liouvillian (negative)", "measure", "defer", None, (),
              meta={"p": "1/x", "q": "-1", "kind": "bessel"}),
    DeferCase("a_neg_nonliouv", "ode", "y'' + x² y = 0 → non-Liouvillian (truncated series only) (negative)", "measure", "defer", None, (),
              meta={"p": "0", "q": "x**2", "kind": "non-liouvillian"}),

    # ─────────────── linear-algebra  (B3 — ABFT/Freivalds, Clock B: VERIFICATION, not compute) ───────────────
    DeferCase("b3_matmul_64", "linear-algebra", "dense 64×64 matmul — ABFT/Freivalds verify (Clock B)", "tune",
              "foldable", None, (), meta={"dim": 64, "clock": "B"}),
    DeferCase("b3_matmul_96", "linear-algebra", "dense 96×96 matmul — Freivalds verify (Clock B)", "measure",
              "foldable", None, (), meta={"dim": 96, "clock": "B"}),
    DeferCase("b3_matmul_128", "linear-algebra", "dense 128×128 matmul — Freivalds verify (Clock B)", "measure",
              "foldable", None, (), meta={"dim": 128, "clock": "B"}),
    DeferCase("b3_matpow", "linear-algebra", "matrix square A·A — checksum verify (Clock B)", "measure",
              "foldable", None, (), meta={"dim": 80, "square": True, "clock": "B"}),

    # ─────────────── combinatorial  (mixed — existing Gosper handles some; Clock C) ───────────────
    DeferCase("c_tri", "combinatorial", "Σ k → n(n+1)/2 (baseline folds)", "tune", "foldable", None, (),
              haran="fn f(n: Nat) -> Nat { fold k in 1..n { k } }"),
    DeferCase("c_sumsq", "combinatorial", "Σ k² (baseline folds)", "measure", "foldable", None, (),
              haran="fn f(n: Nat) -> Nat { fold k in 1..n { k*k } }"),
    DeferCase("c_fib", "combinatorial", "Fibonacci recurrence → C-finite (baseline folds)", "measure", "foldable", None, (),
              haran="fn f(n: Nat) -> Nat { match n { 0 => 0 1 => 1 _ => f(n-1)+f(n-2) } }"),
    DeferCase("c_k2k", "combinatorial", "Σ k·2^k (baseline folds via Gosper)", "measure", "foldable", None, (),
              haran="fn f(n: Nat) -> Nat { fold k in 1..n { k * 2**k } }"),

    # ─────────────── blackbox  (negative controls — must stay defer/absent; NO false fold) ───────────────
    DeferCase("x_harmonic", "blackbox", "Σ 1/k — provably ABSENT (Gosper-nonsummable)", "tune", "defer", None, (),
              haran="fn f(n: Nat) -> Nat { fold k in 1..n { 1 / k } }"),
    DeferCase("x_isprime", "blackbox", "Σ is_prime(k) — data-dependent Ω(N) (no structure)", "measure", "defer", None, (),
              haran="fn f(n: Nat) -> Nat { fold k in 1..n { is_prime(k) } }"),
    DeferCase("x_factorial", "blackbox", "Σ k! — no hypergeometric closed form (defer)", "measure", "defer", None, (),
              haran="fn f(n: Nat) -> Nat { fold k in 1..n { fact(k) } }"),
]
