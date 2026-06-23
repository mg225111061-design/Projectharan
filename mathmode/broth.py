"""
MATH-Ascent §4 + §8 — BROTH PROVING: O(1) certificate lookup over the 3000+ pre-proven broth, GROWN by Gosper.
==============================================================================================================
The amortization principle (lemma_broth): the EXPENSIVE proof is paid ONCE, offline; what is stored is the
certificate; at runtime a recognized identity is proven by an O(1) dict lookup + a CHEAP recheck (a finite
base-case / companion-equality test, PRA strength) — never a re-search. This is "ultra-fast certificate proving."

§4 wires it into MATH mode as `prove()`: a sum or a C-finite recurrence is proven EXACT by lookup-and-recheck,
or honestly DECLINEd on a miss (⇒ fall back to the full §2 fold). §8 GROWS the broth: the existing library could
NOT brew the hypergeometric family (it needs `ore_algebra`, [BLOCKED]). GOSPER (sympy, dependency-light) brews it
anyway — we generate a hypergeometric summand family, Gosper-sum each, KEEP only those whose closed form passes
the same cheap PRA recheck, and add the genuinely-new ones to the broth. Honest: we report brewed vs new, and the
recheck — not sympy's word — is what licenses EXACT.
"""
from __future__ import annotations

import time
from typing import Optional

import sympy as sp
from sympy.concrete.gosper import gosper_sum
from soup import _k, _n

import finite_check as FC
import lemma_broth as LB
import kernel_verdict as KV


# ── the Gosper hypergeometric family (what the broth could not brew without ore_algebra) ─────────────────
def _gosper_family():
    fam = []
    for b in range(2, 10):                                   # geometric b^k, b = 2..9
        fam.append(sp.Integer(b) ** _k)
        for a in range(1, 4):                                # exp-polynomial k^a · b^k
            fam.append(_k ** a * sp.Integer(b) ** _k)
    fam.append(_k * sp.factorial(_k))                        # factorial: Σ k·k! = (n+1)!−1
    for c in range(1, 6):                                    # partial fractions 1/(k(k+c))
        fam.append(sp.Rational(1) / (_k * (_k + c)))
    for d in range(1, 4):                                    # (d·k+1)·2^k
        fam.append((d * _k + 1) * 2 ** _k)
    return fam


_INDEX = None
_STATS = None


def _brew():
    """Load the base broth (3000+), then GROW it with Gosper-brewed hypergeometric entries that pass the cheap
    recheck. Returns (index, stats). Cached."""
    index, base_ms = LB.brew_broth()
    base_total = len(index)
    base_sums = sum(1 for k in index if k.startswith("sum::"))
    brewed = new = 0
    t0 = time.perf_counter()
    for t in _gosper_family():
        try:
            T = gosper_sum(t, _k)
        except Exception:                                    # noqa: BLE001
            T = None
        if T is None:                                        # Gosper PROVES no closed form ⇒ skip (honest)
            continue
        S = sp.simplify(T.subs(_k, _n + 1) - T.subs(_k, 1))  # partial sum from lo=1: T(n+1) − T(1)
        cert = LB.BrothCert(f"sum::{sp.sstr(t)}", "polynomial-sum", sp.sstr(S), "PRA", "finite-base-case")
        if not LB.cheap_recheck(cert):                       # KEEP only what the cheap PRA recheck accepts
            continue
        brewed += 1
        if cert.key not in index:
            new += 1
        index[cert.key] = cert
    brew_ms = (time.perf_counter() - t0) * 1000
    stats = dict(base_total=base_total, base_sums=base_sums, gosper_brewed=brewed, gosper_new=new,
                 total=len(index), gosper_brew_ms=round(brew_ms, 1))
    return index, stats


def index():
    global _INDEX, _STATS
    if _INDEX is None:
        _INDEX, _STATS = _brew()
    return _INDEX


def stats() -> dict:
    index()
    return dict(_STATS)


# ── prove(): O(1) lookup + cheap recheck ⇒ EXACT, or honest DECLINE on a miss ─────────────────────────────
def prove(query) -> KV.Verdict:
    """Prove an identity by the broth. `query` is a sum summand (str / sympy, in k) or {"cfinite": [c0,…]}.
    Hit ⇒ O(1) lookup + cheap PRA/companion recheck ⇒ EXACT (the closed form / recurrence). Miss ⇒ DECLINE
    (not pre-proven — fall back to the full §2 fold)."""
    idx = index()
    if isinstance(query, dict) and "cfinite" in query:
        coeffs = [int(x) for x in query["cfinite"]]
        key = f"cfin:{coeffs}"
        cert = idx.get(key)
        if cert is None or not LB.cheap_recheck(cert):
            return KV.decline(f"broth: recurrence {coeffs} not in broth (O(1) miss) ⇒ DECLINE", "broth")
        kc = KV.Cert(KV.EXACT, "broth_lookup_companion_recheck", passed=True,
                     check_cost="O(1) dict lookup + companion≡naive recheck",
                     detail=f"C-finite {coeffs}: companion-matrix closed form, proof brewed offline")
        return KV.exact(("cfinite", coeffs), "broth", "O(1) lookup + cheap recheck", kc)

    expr = sp.sympify(query, locals={"k": _k, "n": _n}) if isinstance(query, str) else query
    key = f"sum::{sp.sstr(expr)}"
    cert = idx.get(key)
    if cert is None:
        return KV.decline(f"broth: Σ {sp.sstr(expr)} not pre-proven (O(1) miss) ⇒ DECLINE (fall back to fold)",
                          "broth")
    if not LB.cheap_recheck(cert):                           # the recheck — not the stored label — licenses EXACT
        return KV.decline("broth: stored closed form failed the cheap recheck ⇒ DECLINE", "broth")
    closed = sp.sympify(cert.cert_data, locals={"n": _n})
    kc = KV.Cert(KV.EXACT, "broth_lookup_pra_recheck", passed=True,
                 check_cost="O(1) dict lookup + PRA finite-base recheck",
                 detail=f"Σ_(k=1..n) {sp.sstr(expr)} = {sp.sstr(closed)} (proof brewed offline; recheck PRA)")
    return KV.exact(closed, "broth", "O(1) lookup + cheap recheck", kc)


def measure() -> dict:
    """Measure the O(1) lookup cost (constant, independent of broth size) over the full index."""
    import random
    idx = index()
    keys = list(idx)
    rng = random.Random(0)
    probe = [rng.choice(keys) for _ in range(200000)]
    t = time.perf_counter()
    hit = 0
    for k in probe:
        hit += idx.get(k) is not None
    lookup_us = (time.perf_counter() - t) / len(probe) * 1e6
    return dict(stats(), lookup_us=round(lookup_us, 5), probed=len(probe), all_hit=(hit == len(probe)))
