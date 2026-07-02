"""
§P P2 — FINISH THE "LAZY DECLINE" CASES: the detector gets scared by a branch / state / nonlinearity and DECLINEs a
sum that is actually foldable. (Detector RECALL — routes to EXISTING kinds, no 23rd mechanism.)
================================================================================================================
Kimi's code surfaced four foldable-but-declined shapes; GAP-1 (`for k in range(n): s+=k`) was already fixed this
session. The remaining three:
  • PERIODIC-CONDITIONAL body (e.g. `s += k % 2`) — the partial-sum SEQUENCE has eventually-constant differences, so
    it is C-FINITE. The white-box lifter declines (sympy emits Mod, z3 can't encode it), but the BLACK-BOX fallback
    (P1) recovers the linear recurrence from the output sequence → `linear_recurrence` (⑪/⑩, periodicity is C-finite).
  • MOD-k FINITE STATE (e.g. `s += k % 3`) — same: a finite-state body's partial sums are C-finite → black-box ⑪.
  • TELESCOPING (e.g. `s += 1/(k*(k+1))`) — NOT C-finite (the closed form 1−1/(n+1) is rational-in-n, not a
    constant-coefficient recurrence), so black-box correctly declines it; it needs Gosper rational antidifference →
    `gosper_antidifference` (⑫). This module adds that recognizer.

★ Precision UNCHANGED: telescoping is admitted ONLY when the Gosper antidifference G satisfies the EXACT symbolic
telescoping identity G(k+1) − G(k) ≡ body(k) AND the definite closed form is rational in n (no harmonic/digamma — a
non-summable body like 1/k yields harmonic(n) and is correctly DECLINED). Near-miss non-telescoping bodies DECLINE.
"""
from __future__ import annotations

import kernel_verdict as KV
from catalog.lift import _SUM_LOOP


def telescoping_grade(code: str, label: str = "telescoping") -> KV.Verdict:
    """Fold `for k in range([a,]b): acc += body` where body is a RATIONAL term with a Gosper rational antidifference G
    (body(k) = G(k+1) − G(k)). Closed form Σ_{k=base}^{n} body = G(n+1) − G(base), PROVED by the EXACT symbolic
    telescoping identity. Polynomial bodies are left to lift (this targets the rational/telescoping case it declines);
    non-summable bodies (1/k → harmonic) and non-telescoping rationals DECLINE. Cert kind: gosper_antidifference (⑫)."""
    import sympy as sp
    m = _SUM_LOOP.search(code)
    if not m:
        return KV.decline("telescoping: no accumulation loop (for k in range([a,]b): acc += body) found ⇒ DECLINE", label)
    var, lo, hi, body = m.group(1), m.group(2), m.group(3).strip(), m.group(4).strip().rstrip(":")
    base = 0
    if lo is not None:
        try:
            base = int(lo.strip())
        except ValueError:
            base = 1
    from sympy.concrete.gosper import gosper_sum, gosper_term
    k = sp.Symbol(var)
    try:
        b = sp.sympify(body, locals={var: k})
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"telescoping: cannot parse body {body!r} ({type(e).__name__}) ⇒ DECLINE", label)
    if b.free_symbols - {k}:
        return KV.decline(f"telescoping: body has free variables other than {var} ⇒ DECLINE", label)
    if b.is_polynomial(k):
        return KV.decline("telescoping: polynomial body — handled by the Faulhaber lifter, not this path ⇒ DECLINE", label)
    # Gosper rational antidifference: R with G(k) = R(k)·body(k) and G(k+1) − G(k) = body(k). None ⇒ NOT summable.
    try:
        R = gosper_term(b, k)
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"telescoping: Gosper search failed ({type(e).__name__}) ⇒ DECLINE", label)
    if R is None:
        return KV.decline("telescoping: body is NOT Gosper-summable (e.g. 1/k → harmonic) ⇒ DECLINE", label)
    G = sp.simplify(R * b)
    # ★ EXACT disposer: the telescoping identity G(k+1) − G(k) ≡ body must hold symbolically (residual = 0)
    identity = sp.simplify(G.subs(k, k + 1) - G - b)
    if identity != 0:
        return KV.decline(f"telescoping: Gosper identity G(k+1)−G(k)−body = {identity} ≠ 0 — not telescoping ⇒ DECLINE", label)
    n = sp.Symbol("n")
    try:
        closed = gosper_sum(b, (k, base, n))
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"telescoping: gosper_sum failed ({type(e).__name__}) ⇒ DECLINE", label)
    if closed is None:
        return KV.decline("telescoping: no closed-form definite sum ⇒ DECLINE", label)
    closed = sp.simplify(closed)
    if closed.free_symbols - {n}:
        return KV.decline(f"telescoping: closed form {closed} not purely in n ⇒ DECLINE", label)
    cert = KV.Cert(KV.EXACT, "gosper_antidifference", passed=True,
                   check_cost="exact symbolic telescoping identity G(k+1)−G(k) ≡ body (residual = 0)",
                   detail=f"Σ_{{{var}={base}}}^n {body} = {closed}; Gosper antidifference G={G}, telescoping identity "
                          "verified exactly (a non-summable body → harmonic ⇒ DECLINE, never a wrong fold)")
    return KV.exact({"closed_form": str(closed), "antidifference": str(G), "target": "telescoping", "via": "gosper"},
                    label, "Gosper rational telescoping (⑫), O(n)→O(1)", cert)


def _wrap_loop_as_function(code: str) -> str:
    """Wrap a bare accumulation loop `for k in range([a,]b): acc += body` into `def _bb(n): ...` so the black-box
    fallback can probe its partial-sum sequence (used for the periodic/mod-k cases the lifter declines). The bound is
    taken to be the parameter n; loops whose bound is not the index parameter are left to the caller."""
    m = _SUM_LOOP.search(code)
    if not m:
        return ""
    var, lo, hi, body = m.group(1), m.group(2), m.group(3).strip(), m.group(4).strip().rstrip(":")
    rng = f"range({lo.strip()}, n)" if lo is not None else "range(n)"
    return (f"def _bb(n):\n    _acc = 0\n    for {var} in {rng}:\n        _acc += {body}\n    return _acc")


def lazy_decline_grade(code: str, label: str = "lazy_decline") -> KV.Verdict:
    """Orchestrate the recall for the lazy-decline shapes the polynomial lifter declines: (1) telescoping (Gosper, ⑫);
    (2) periodic-conditional / mod-k finite state via the black-box fallback (their partial sums are C-finite → ⑪).
    The caller tries the white-box lifter FIRST; this runs only when that declines. Precision unchanged (each path
    carries its own exact proof; an unfoldable body DECLINEs)."""
    v = telescoping_grade(code, label=label)
    if v.status == KV.EXACT:
        return v
    # periodic / mod-k: route the loop's partial-sum function to the black-box fallback (C-finite recovery)
    import catalog.blackbox_fallback as BB
    wrapped = _wrap_loop_as_function(code)
    if wrapped:
        bb = BB.blackbox_grade({"_bb": wrapped}, "_bb", label=label)
        if bb.status == KV.EXACT:
            return bb
    return KV.decline("lazy_decline: not telescoping and not a C-finite periodic/mod-k partial sum ⇒ DECLINE", label)
