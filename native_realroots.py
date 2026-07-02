"""
NATIVE ARSENAL — exact real-root isolation (Sturm + Descartes/bisection), in-repo, zero external dep.
====================================================================================================
For a polynomial with EXACT rational coefficients, isolate each real root in a rational interval and CERTIFY the
count by a Sturm sequence (the number of real roots in (a,b] = V(a) − V(b), V = sign variations of the Sturm chain).
Mechanisms ② ③ ⑨. Certificate: the isolating intervals + the re-countable Sturm sign-variation counts. Root
clusters tighter than the precision budget ⇒ honest DECLINE (we never merge or miscount).
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Sequence

import kernel_verdict as KV


def _trim(p: List[Fraction]) -> List[Fraction]:
    i = 0
    while i < len(p) - 1 and p[i] == 0:
        i += 1
    return p[i:]


def _deriv(p: List[Fraction]) -> List[Fraction]:
    d = len(p) - 1
    return _trim([p[i] * (d - i) for i in range(d)]) if d > 0 else [Fraction(0)]


def _polymod(a: List[Fraction], b: List[Fraction]) -> List[Fraction]:
    a = a[:]
    b = _trim(b)
    while len(a) >= len(b) and not (len(a) == 1 and a[0] == 0):
        if len(_trim(a)) < len(b):
            break
        a = _trim(a)
        if len(a) < len(b):
            break
        coef = a[0] / b[0]
        shift = len(a) - len(b)
        for i in range(len(b)):
            a[i] -= coef * b[i]
        a = a[1:] if len(a) > 1 else [Fraction(0)]
        if shift == 0:
            break
    return _trim(a)


def _evalp(p: List[Fraction], x: Fraction) -> Fraction:
    r = Fraction(0)
    for c in p:
        r = r * x + c
    return r


def sturm_chain(p: List[Fraction]) -> List[List[Fraction]]:
    """The Sturm chain p0=p, p1=p', p_{k+1} = −(p_{k-1} mod p_k)."""
    chain = [_trim(p[:]), _deriv(p)]
    while len(_trim(chain[-1])) > 1:
        r = _polymod(chain[-2], chain[-1])
        chain.append([-c for c in r])
    return chain


def _variations(chain, x: Fraction) -> int:
    vals = [_evalp(c, x) for c in chain]
    vals = [v for v in vals if v != 0]
    return sum(1 for i in range(len(vals) - 1) if (vals[i] > 0) != (vals[i + 1] > 0))


def count_roots(p: List[Fraction], a: Fraction, b: Fraction, chain=None) -> int:
    chain = chain or sturm_chain(p)
    return _variations(chain, a) - _variations(chain, b)


def _root_bound(p: List[Fraction]) -> Fraction:
    """Cauchy bound: all real roots lie in (−M, M)."""
    lead = p[0]
    M = 1 + max((abs(c / lead) for c in p[1:]), default=Fraction(0))
    return M


def isolate_roots(coeffs: Sequence, max_depth: int = 60):
    """Return a list of isolating intervals (lo, hi), each containing exactly one real root, via Sturm + bisection."""
    p = _trim([Fraction(c) for c in coeffs])
    if len(p) <= 1:
        return [], None
    chain = sturm_chain(p)
    M = _root_bound(p)
    total = count_roots(p, -M, M, chain)
    intervals = []
    stack = [(-M, M, 0)]
    while stack:
        lo, hi, depth = stack.pop()
        c = count_roots(p, lo, hi, chain)
        if c == 0:
            continue
        if c == 1:
            intervals.append((lo, hi))
            continue
        if depth >= max_depth:
            return None, total                               # cluster too tight for the budget ⇒ signal DECLINE
        mid = (lo + hi) / 2
        stack.append((lo, mid, depth + 1))
        stack.append((mid, hi, depth + 1))
    return intervals, total


def realroots_grade(coeffs) -> KV.Verdict:
    """Isolate all real roots with Sturm-certified counts; EXACT with the isolating intervals; clusters past the
    bisection budget ⇒ honest DECLINE."""
    p = _trim([Fraction(c) for c in coeffs])
    if len(p) <= 1:
        return KV.decline("realroots: constant/empty polynomial", "native_realroots")
    intervals, total = isolate_roots(coeffs)
    if intervals is None:
        return KV.decline(f"realroots: {total} real roots but a cluster is tighter than the bisection budget ⇒ DECLINE",
                          "native_realroots")
    if len(intervals) != total:
        return KV.decline(f"realroots: isolated {len(intervals)} ≠ Sturm count {total} ⇒ DECLINE (bug guard)",
                          "native_realroots")
    cert = KV.Cert(KV.EXACT, "sturm_isolation", passed=True, check_cost="re-count Sturm sign-variations per interval",
                   detail=f"{total} real roots isolated; Sturm chain length {len(sturm_chain(p))}; each interval "
                          f"has exactly one root (V(a)−V(b)=1)")
    return KV.exact({"n_real_roots": total, "intervals": [(str(a), str(b)) for a, b in intervals]},
                    "native_realroots", "Sturm + Descartes bisection", cert)
