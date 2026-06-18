"""
v32 STAGE B2 — q-Gosper / q-holonomic telescoping fold core [Clock C].
=======================================================================
Target: q-series summation loops (q-geometric / q-rational terms) whose sum SymPy's `summation` leaves
unevaluated. If t(k) telescopes, Σ_{k=lo}^n t(k) collapses to an O(1) closed form in q^n — a Clock C win.

PIPELINE (detect → candidate → SOUND verify → fold | HONEST_DEFER):
  B2.1 detect : the q-ratio ρ(x)=t(k+1)/t(k) must be RATIONAL in x=q^k (the q-hypergeometric test). The term
                t(k) must itself be rational in q^k (linear-in-k exponents only) — a quadratic exponent
                (q^{k²}, theta) is detected and DEFERRED (it is q-hypergeometric but NOT summable).
  B2.2 solve  : seek a telescoper σ(X) (rational in X=q^n) with σ(X)-σ(X/q)=τ(X) via a BOUNDED rational
                ansatz (partial fractions over q-shifts ∏(1-q^j X) + a polynomial part), solved EXACTLY
                over ℚ(q).  Then S(n)=σ(q^n)-σ(q^{lo-1}).
  B2.3 verify : ★ THE SOUND GATE ★ — require S(n)-S(n-1) ≡ t(n) AND S(lo) ≡ t(lo), simplified to EXACTLY 0
                (symbolic). Only a verified telescoper folds. No certificate ⇒ HONEST_DEFER.
  B2.4 measure: run over the defer corpus `q-holonomic` category — hit rate + verification rate (held out).

HONEST LIMITS: the ansatz search is BOUNDED (dispersion bound). A genuinely summable term outside the
ansatz space is DEFERRED honestly (under-coverage, never a wrong fold). theta / q-harmonic have NO closed
form and are correctly DEFERRED (q-hypergeometric-but-not-summable — informative certificate).
Certificate: exact (bit-exact closed form, verified by exact symbolic telescoping). Clock C only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


class _NonRational(Exception):
    pass


@dataclass
class QFoldVerdict:
    status: str                 # FOLDED | DEFER
    q_hypergeometric: Optional[bool] = None   # did the q-ratio test pass?
    closed_form: str = "—"
    cert_type: str = "exact"
    verified: bool = False
    clock: str = "C"
    detail: str = ""

    def __str__(self):
        if self.status == "FOLDED":
            return f"FOLDED [Clock C] S(n)={self.closed_form}  (cert: {self.cert_type}, exact-verified)"
        return f"DEFER — {self.detail}"


def _to_X(expr, q, k, X):
    """Rewrite a term in q^k as a rational function of X=q^k. q^{c1·k+c0} → q^{c0}·X^{c1}. A non-linear
    exponent in k (e.g. q^{k²}) is NOT rational in q^k → raise _NonRational (theta-type, not summable here)."""
    import sympy as sp
    expr = sp.expand_power_exp(sp.powsimp(expr, force=True))

    def is_qpow(e):
        return isinstance(e, sp.Pow) and e.base == q and k in (e.exp.free_symbols if hasattr(e.exp, "free_symbols") else set())

    for p in expr.atoms(sp.Pow):
        if is_qpow(p):
            poly = sp.Poly(p.exp, k)
            if poly.total_degree() > 1:
                raise _NonRational(f"exponent {p.exp} is non-linear in {k}")

    def repl(p):
        poly = sp.Poly(p.exp, k)
        c1 = poly.coeff_monomial(k)
        c0 = poly.coeff_monomial(1)
        return q**c0 * X**c1

    out = expr.replace(is_qpow, repl)
    if k in out.free_symbols:
        raise _NonRational(f"residual {k} after q^k→X")
    return sp.cancel(sp.together(out))


def _is_zero_in_q(expr, q, n) -> bool:
    """Exact zero-test for an expression in q^n (and q^{n±j}): map q^n→Y (linear exponents) and `cancel`
    as a rational function. Robust where sympy.simplify is incomplete on mixed q^n / q^{n±1} terms."""
    import sympy as sp
    Y = sp.Symbol("_Y")
    try:
        r = _to_X(expr, q, n, Y)
        return sp.cancel(sp.together(r)) == 0
    except _NonRational:
        return sp.simplify(expr) == 0
    except Exception:  # noqa: BLE001
        return sp.simplify(expr) == 0


def _q_ratio_rational(t_expr, q, k, X) -> Optional[object]:
    """B2.1 detector: ρ(x)=t(k+1)/t(k) as a function of x=q^k. Returns the rational ρ(X), or None if the
    ratio is not rational in q^k (not q-hypergeometric)."""
    import sympy as sp
    try:
        ratio = sp.simplify(t_expr.subs(k, k + 1) / t_expr)
        rho = _to_X(ratio, q, k, X)
        rho = sp.cancel(rho)
        if rho.is_rational_function(X):
            return rho
    except _NonRational:
        # ratio non-rational in q^k OR the exponent quadratic — but the ratio of a theta IS rational;
        # fall through: the term itself being non-rational is handled by the summation step.
        try:
            ratio = sp.simplify(t_expr.subs(k, k + 1) / t_expr)
            # ratio may still be rational in q^k even if t isn't (theta): test the ratio alone
            rho = _to_X(ratio, q, k, X)
            return rho if sp.cancel(rho).is_rational_function(X) else None
        except Exception:  # noqa: BLE001
            return None
    except Exception:  # noqa: BLE001
        return None
    return None


def _solve_telescoper(tau_X, q, X, *, shifts=range(0, 4), powers=(1, 2), poly_deg=2):
    """B2.2: find rational σ(X) with σ(X)-σ(X/q)=τ(X) by a BOUNDED ansatz (partial fractions over q-shifts
    + a polynomial part), solved EXACTLY over ℚ(q). Returns σ(X) or None (no telescoper in the ansatz)."""
    import sympy as sp
    coeffs = []
    terms = []
    # polynomial part
    for d in range(poly_deg + 1):
        c = sp.Symbol(f"p{d}")
        coeffs.append(c)
        terms.append(c * X**d)
    # partial fractions A_{j,p} / (1 - q^j X)^p
    for j in shifts:
        for p in powers:
            c = sp.Symbol(f"a_{j}_{p}")
            coeffs.append(c)
            terms.append(c / (1 - q**j * X)**p)
    sigma = sum(terms)
    eq = sp.together(sigma - sigma.subs(X, X / q) - tau_X)
    num = sp.numer(sp.cancel(eq))
    polynum = sp.Poly(sp.expand(num), X)
    # each X-coefficient must vanish → linear system in `coeffs` over ℚ(q)
    sysz = polynum.all_coeffs()
    sol = sp.solve(sysz, coeffs, dict=True)
    if not sol:
        return None
    s0 = sol[0]
    sigma_sol = sigma.subs({c: s0.get(c, 0) for c in coeffs})
    # require a NON-trivial solution (not identically zero unless τ is zero)
    if sp.simplify(sigma_sol) == 0 and sp.simplify(tau_X) != 0:
        return None
    return sp.cancel(sp.together(sigma_sol))


def q_fold(qterm: str, lo: int = 1) -> QFoldVerdict:
    """Decide + (soundly) fold a q-series term Σ_{k=lo}^n t(k). `qterm` is a sympy expression string in q,k."""
    import sympy as sp
    q, k, n, X = sp.symbols("q k n X")
    try:
        t_expr = sp.sympify(qterm, locals={"q": q, "k": k})
    except Exception as e:  # noqa: BLE001
        return QFoldVerdict("DEFER", detail=f"q-term not analyzable ({type(e).__name__})")
    # B2.1 — q-hypergeometric detection (ratio rational in q^k)
    rho = _q_ratio_rational(t_expr, q, k, X)
    q_hyp = rho is not None
    # the SUMMATION needs t(k) itself rational in q^k (linear exponents). Quadratic (theta) ⇒ defer.
    try:
        tau_X = _to_X(t_expr, q, k, X)
    except _NonRational as e:
        return QFoldVerdict("DEFER", q_hypergeometric=q_hyp,
                            detail=f"q-hypergeometric={q_hyp} but term is NOT rational in q^k "
                                   f"({e}) — theta-type, no closed form. HONEST_DEFER.")
    # B2.2 — bounded telescoper search
    sigma = _solve_telescoper(tau_X, q, X)
    if sigma is None:
        return QFoldVerdict("DEFER", q_hypergeometric=q_hyp,
                            detail=f"q-hypergeometric={q_hyp} but no telescoper in the bounded ansatz "
                                   f"(q-Gosper-nonsummable here, e.g. q-harmonic) — HONEST_DEFER.")
    # closed form: S(n) = σ(q^n) - σ(q^{lo-1})
    S_n = sp.cancel(sp.together(sigma.subs(X, q**n) - sigma.subs(X, q**(lo - 1))))
    # B2.3 — ★ SOUND GATE ★: S(n)-S(n-1) ≡ t(n) and S(lo) ≡ t(lo), exact rational-function zero-test
    t_n = t_expr.subs(k, n)
    ok_step = _is_zero_in_q(S_n - S_n.subs(n, n - 1) - t_n, q, n)
    base = sp.simplify(S_n.subs(n, lo) - t_expr.subs(k, lo))
    if (not ok_step) or base != 0:
        return QFoldVerdict("DEFER", q_hypergeometric=q_hyp,
                            detail="candidate telescoper FAILED exact verification (S(n)-S(n-1)≠t(n)) — "
                                   "refusing to fold (no false structure).")
    return QFoldVerdict("FOLDED", q_hypergeometric=q_hyp, closed_form=str(S_n), cert_type="exact",
                        verified=True, clock="C",
                        detail="q-telescoping verified exactly: S(n)-S(n-1)≡t(n) ∧ S(lo)≡t(lo); O(n)→O(1)")


# ─────────────────────────────────────────────────────── B2.4 — corpus measurement
def measure_q_corpus(split: Optional[str] = None) -> dict:
    """Run B2 over the defer corpus `q-holonomic` category. Hit rate + verification rate, ZERO false folds
    (theta / q-harmonic must DEFER). Coverage MEASURED, not estimated."""
    import defer_corpus as DC
    cs = [c for c in DC.load() if c.category == "q-holonomic" and (split is None or c.split == split)]
    folded = correct = verified = 0
    rows = []
    for c in cs:
        v = q_fold(c.meta["qterm"])
        is_fold = (v.status == "FOLDED")
        ok = (is_fold == (c.expect == "foldable"))
        folded += int(is_fold)
        verified += int(v.verified)
        correct += int(ok)
        rows.append((c.cid, c.expect, v.status, ok, v.closed_form if is_fold else ""))
    n = len(cs)
    return {"n": n, "folded": folded, "correct": correct, "verified": verified,
            "hit_rate": round(folded / n, 3) if n else 0.0,
            "correctness": round(correct / n, 3) if n else 0.0,
            "rows": rows, "clock": "C"}
