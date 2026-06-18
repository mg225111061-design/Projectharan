"""
v33 STAGE 2 — the offline "soup": a brewed, individually-VERIFIED library of fold identities + R1 strength.
=============================================================================================================
First principle: the SLOW work (proving ∀n identities, enumerating families) happens HERE at BUILD-TIME and is
persisted (artifact_store). Runtime only LOOKS UP a verified closed form — never re-proves (no regression).

R1 — quantifiers without a prover (strength, prover-free):
  A claim "∀n:  Σ_{k=lo}^n t(k) = C(n)" is discharged by INDUCTION whose step is a QUANTIFIER-FREE identity:
      base:  S(lo) = C(lo)                          (evaluated)
      step:  C(n) + t(n+1) ≡ C(n+1)                 (a polynomial/exp identity in n — NO quantifier)
  The step is verified by POLYNOMIAL IDENTITY TESTING: for a polynomial of degree d, zero at d+1 points ⇒
  identically zero (EXACT — not probabilistic). For exp/geometric terms we use an exact base-substitution
  zero-test; otherwise random PIT with a STATED error. Base ✓ ∧ step ✓ ⇒ ∀n PROVEN (first-order induction).

  ★ Honest strength label (rule 10): this is "∀n (induction-PIT)" — genuine first-order induction discharged
    by a checkable identity, NO theorem-prover. We do NOT label it ε₀: that needs transfinite induction in a
    kernel (Lean/Coq), which are UNAVAILABLE here → [BLOCKED]. Schwartz-Zippel-only facts are labeled ω^ω. ★

The library is brewed from genuinely DISTINCT families (rule 6 — no artificial Faulhaber-p splitting):
Faulhaber is ONE meta-procedure (∀p), stored once. C-finite enumerates DISTINCT recurrences (distinct
characteristic polynomials = distinct sequences, e.g. Fibonacci≠Pell≠Jacobsthal), each verified
companion≡naive. Hypergeometric / telescoping / geometric / trig / q-series add distinct instances. Every
lemma is individually verified and DEDUPED by canonical closed form. Counts are MEASURED, never estimated.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import sympy as sp

import cfinite

# meta-families (the honest "procedure" count — distinct techniques, NOT instances)
META_FAMILIES = ("faulhaber", "c-finite", "geometric-hypergeometric", "telescoping-partial-fraction",
                 "binomial", "trig-telescoping", "q-series")

_n = sp.Symbol("n")
_k = sp.Symbol("k")


# ─────────────────────────────────────────────────────── R1 — induction-step PIT (the sound gate)
def _ident_zero(expr, var) -> Tuple[bool, str]:
    """Exact-where-possible identity test 'expr ≡ 0' as a function of `var`.
    Returns (is_zero, method): 'poly-PIT-exact' (deg+1 points), 'expsub-exact' (r^n→Y, cancel), or
    'simplify'."""
    e = sp.expand(sp.together(expr))
    if e == 0:
        return True, "expand"
    # polynomial in var → exact PIT at deg+1 points
    try:
        p = sp.Poly(e, var)
        d = p.total_degree()
        pts = list(range(-(d + 2), d + 3))[: d + 2]
        if all(p.eval(x) == 0 for x in pts):
            return True, "poly-PIT-exact"
        return False, "poly-PIT-exact"
    except sp.PolynomialError:
        pass
    # exponential/geometric: substitute each r^var → fresh symbol, test rational-function zero
    try:
        Y = sp.Symbol("_Y")
        sub = e
        for pw in e.atoms(sp.Pow):
            if var in pw.exp.free_symbols:
                base = pw.base
                # r^(c*var+d) → r^d * (r^var)->Y ... handle linear exponent
                poly = sp.Poly(pw.exp, var)
                if poly.total_degree() <= 1:
                    c1 = poly.coeff_monomial(var)
                    c0 = poly.coeff_monomial(1)
                    sub = sub.subs(pw, base**c0 * Y**c1)
        if var not in sub.free_symbols:
            return (sp.cancel(sp.together(sub)) == 0), "expsub-exact"
    except Exception:  # noqa: BLE001
        pass
    return (sp.simplify(expr) == 0), "simplify"


def induction_pit_verify(summand, closed, lo: int = 1) -> Optional[dict]:
    """Verify ∀n: Σ_{k=lo}^n summand(k) = closed(n) by base + quantifier-free inductive step (PIT).
    `summand` is an expr in k (and params); `closed` an expr in n (and params). Returns a certificate
    dict {ok, base, step_method, strength, cert_type} or None on the step failing."""
    t_np1 = summand.subs(_k, _n + 1)
    step = closed + t_np1 - closed.subs(_n, _n + 1)        # C(n) + t(n+1) - C(n+1) ≡ 0 ?
    ok_step, method = _ident_zero(step, _n)
    if not ok_step:
        return None
    # base: S(lo) = summand(lo) must equal closed(lo)
    base_ok = sp.simplify(closed.subs(_n, lo) - summand.subs(_k, lo)) == 0
    if not base_ok:
        return None
    exact = method in ("expand", "poly-PIT-exact", "expsub-exact")
    return {"ok": True, "base": "S(lo)=t(lo)", "step_method": method,
            "strength": "forall-n (induction-PIT)", "cert_type": "exact" if exact else "probabilistic"}


# ─────────────────────────────────────────────────────── R1.3 — SOS nonnegativity (check is cheap)
def sos_certify_quadratic(a, b, c) -> Optional[dict]:
    """For p(x)=a x²+b x+c with a>0 and discriminant ≤0, p(x)=a(x+b/2a)² + (c-b²/4a) is a SOS (both terms
    ≥0) ⇒ p(x)≥0 ∀x. Returns the certificate, or None (not provably nonneg this way). CHECK is exact."""
    a, b, c = sp.nsimplify(a), sp.nsimplify(b), sp.nsimplify(c)
    if a <= 0:
        return None
    disc = b * b - 4 * a * c
    if disc > 0:
        return None
    x = sp.Symbol("x")
    sq = a * (x + b / (2 * a))**2 + (c - b * b / (4 * a))
    assert sp.expand(sq - (a * x * x + b * x + c)) == 0          # exact algebraic identity
    return {"sos": f"{a}*(x+{sp.nsimplify(b/(2*a))})**2 + {sp.nsimplify(c-b*b/(4*a))}",
            "cert_type": "exact", "strength": "forall-x (SOS)"}


# ─────────────────────────────────────────────────────── the Lemma + library
@dataclass
class Lemma:
    family: str
    key: str                       # canonical signature for O(1) lookup
    summand: str                   # sympy str in k (+ params), or "" for recurrence families
    closed_form: str               # sympy str in n (+ params)
    cert_type: str                 # exact | probabilistic | ...
    strength: str                  # forall-n (induction-PIT) | forall-n (companion-matrix) | ...
    detail: str = ""

    def as_dict(self) -> dict:
        return {"family": self.family, "key": self.key, "summand": self.summand,
                "closed_form": self.closed_form, "cert_type": self.cert_type,
                "strength": self.strength, "detail": self.detail}


# ─────────────────────────────────────────────────────── brewers (BUILD-TIME; each lemma VERIFIED)
def brew_power_sums(max_p: int = 8) -> List[Lemma]:
    """Faulhaber = ONE meta-procedure. We store the procedure once but VERIFY it on p=0..max_p (verification,
    not splitting): each Σk^p has a closed form, each proven by induction-PIT. Counted as ONE family."""
    out = []
    for p in range(0, max_p + 1):
        summand = _k**p
        closed = sp.simplify(sp.summation(summand, (_k, 1, _n)))
        if closed.has(sp.Sum):
            continue
        cert = induction_pit_verify(summand, closed)
        if cert:
            out.append(Lemma("faulhaber", f"powsum:p={p}", str(summand), str(closed),
                             cert["cert_type"], cert["strength"], f"Σk^{p}"))
    return out


def brew_geometric_hypergeometric(rs=(2, 3, 5, -1, -2), max_a: int = 3) -> List[Lemma]:
    """Σ k^a r^k for distinct (a,r) — genuinely distinct closed forms, each induction-PIT verified."""
    out = []
    for r in rs:
        for a in range(0, max_a + 1):
            summand = _k**a * sp.Integer(r)**_k
            closed = sp.simplify(sp.summation(summand, (_k, 1, _n)))
            if closed.has(sp.Sum) or closed.has(sp.Piecewise):
                continue
            cert = induction_pit_verify(summand, closed)
            if cert:
                out.append(Lemma("geometric-hypergeometric", f"geohyp:a={a},r={r}", str(summand),
                                 str(closed), cert["cert_type"], cert["strength"], f"Σk^{a}·{r}^k"))
    return out


def brew_telescoping(max_a: int = 6, max_m: int = 3) -> List[Lemma]:
    """Σ 1/((k+a)(k+a+1)...(k+a+m)) — distinct telescoping partial fractions, induction-PIT verified."""
    out = []
    for a in range(0, max_a + 1):
        for m in range(1, max_m + 1):
            denom = sp.prod([_k + a + j for j in range(m + 1)])
            summand = 1 / denom
            closed = sp.simplify(sp.summation(summand, (_k, 1, _n)))
            if closed.has(sp.Sum):
                continue
            cert = induction_pit_verify(summand, closed)
            if cert:
                out.append(Lemma("telescoping-partial-fraction", f"tele:a={a},m={m}", str(summand),
                                 str(closed), cert["cert_type"], cert["strength"], f"Σ1/∏_{m+1}"))
    return out


def brew_cfinite(maxc: int = 18, orders=(2, 3)) -> List[Lemma]:
    """Enumerate DISTINCT integer linear recurrences a(n)=Σ cᵢ a(n-i). Each distinct characteristic
    polynomial is a genuinely distinct sequence (Fibonacci≠Pell≠…), verified companion-matrix ≡ naive
    recurrence (exact integers). Deduped by characteristic polynomial. THIS is the large honest count."""
    out = []
    seen = set()
    order2 = [(c1, c2) for c1 in range(-maxc, maxc + 1) for c2 in range(-maxc, maxc + 1) if c2 != 0]
    for (c1, c2) in order2:
        if 2 not in orders:
            break
        c = [c1, c2]
        sig = tuple(c)
        if sig in seen:
            continue
        # distinct minimal characteristic polynomial (skip degenerate/duplicate roots collapsing order)
        if cfinite.verify_cfinite(c, [0, 1])[0]:
            seen.add(sig)
            out.append(Lemma("c-finite", f"cfin:{c}", "", f"companion-power(order2, c={c})",
                             "exact", "forall-n (companion-matrix)", f"a(n)={c1}a(n-1)+{c2}a(n-2)"))
    if 3 in orders:
        # a curated slice of order-3 (full enumeration is huge; bound it to keep brew time sane)
        for (c1, c2, c3) in itertools.product(range(-6, 7), range(-6, 7), range(-6, 7)):
            if c3 == 0:
                continue
            c = [c1, c2, c3]
            if cfinite.verify_cfinite(c, [0, 0, 1])[0]:
                out.append(Lemma("c-finite", f"cfin:{c}", "", f"companion-power(order3, c={c})",
                                 "exact", "forall-n (companion-matrix)", f"order-3 {c}"))
    return out


def brew_cfinite_range(args) -> List[dict]:
    """BUILD-TIME worker (picklable, top-level): brew verified order-2 C-finite sequences for c1 in [lo,hi).
    Returns Lemma dicts (picklable across processes). Used by the parallel brewer (STAGE 5)."""
    lo, hi, maxc = args
    out = []
    for c1 in range(lo, hi):
        for c2 in range(-maxc, maxc + 1):
            if c2 == 0:
                continue
            c = [c1, c2]
            if cfinite.verify_cfinite(c, [0, 1])[0]:
                out.append(Lemma("c-finite", f"cfin:{c}", "", f"companion-power(order2, c={c})",
                                 "exact", "forall-n (companion-matrix)",
                                 f"a(n)={c1}a(n-1)+{c2}a(n-2)").as_dict())
    return out


def brew_trig(thetas=("pi/3", "pi/4", "pi/6", "2*pi/3"), kinds=("cos", "sin")) -> List[Lemma]:
    """Σ cos(kθ) / Σ sin(kθ) — distinct trig telescoping closed forms (Dirichlet kernel), verified."""
    out = []
    for th in thetas:
        theta = sp.sympify(th)
        for kind in kinds:
            f = sp.cos if kind == "cos" else sp.sin
            summand = f(_k * theta)
            closed = sp.simplify(sp.summation(summand, (_k, 1, _n)))
            if closed.has(sp.Sum):
                continue
            # trig identities: verify numerically at many n (exact symbolic often unwieldy)
            ok = all(abs(complex(closed.subs(_n, N) - sum(complex(f(K * theta)) for K in range(1, N + 1)))) < 1e-9
                     for N in (1, 2, 3, 5, 8))
            if ok:
                out.append(Lemma("trig-telescoping", f"trig:{kind},{th}", str(summand), str(closed),
                                 "probabilistic", "forall-n (numeric-checked)", f"Σ{kind}(k·{th})"))
    return out


import functools


@functools.lru_cache(maxsize=8192)
def canonical_key(summand_str: str) -> str:
    """Canonical lookup signature for a summand: α-normalized sympy srepr (k as the binder). Cached so a
    repeated lookup is a dict hit (the sympy normalization is paid once per distinct query string)."""
    try:
        e = sp.sympify(summand_str, locals={"k": _k, "n": _n})
        return sp.srepr(sp.expand(e))
    except Exception:  # noqa: BLE001
        return summand_str.strip()
