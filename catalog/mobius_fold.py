"""
§P P5 — MÖBIUS RATIONAL-RECURRENCE FACE of ⑬: fold homographic recurrences the C-finite detector is blind to.
================================================================================================================
A fractional / homographic recurrence x ← (a·x + b)/(c·x + d) — IIR filter feedback, discrete compound interest,
continued-fraction expansion, perspective transforms — is NOT C-finite (the division blinds the linear-recurrence
detector) and the projective transform is a distinct object. But Möbius maps are exactly PGL₂: lift to projective
coordinates x = u/v, and the update becomes the LINEAR map [u; v] ← [[a, b], [c, d]] · [u; v]. So N iterations =
M^N · [u; v] by binary exponentiation, O(N) → O(log N).

★ PROOF (clear denominators → polynomial identity, z3 NRA, residual=0): for sample N, the N-fold composition f^N(x)
= p_N(x)/q_N(x) and the matrix-power closed form (A·x+B)/(C·x+D) [from M^N] must satisfy p_N(x)·(C·x+D) −
(A·x+B)·q_N(x) ≡ 0 ∀x — a polynomial identity z3 proves exactly. The Möbius–PGL₂ homomorphism (M^N = the N-fold
composition) generalises it to all N. Cert kind: `matrix_recurrence` (EXISTING, a 2×2 projective matrix recurrence) —
NOT a 23rd kind; it is ⑬'s projective extension.

★ HONEST BOUNDARY: decidable for degree-1 homographic with ad−bc ≠ 0 (the projective-linear case). A degree-≥2
rational recurrence (Galois barrier / Julia-set chaos) is not homographic ⇒ the detector does not match ⇒ DECLINE.
A trajectory that hits a pole (c·x+d = 0) is undefined ⇒ DECLINE that initial state.
"""
from __future__ import annotations

import re
from typing import Optional, Sequence, Tuple

import kernel_verdict as KV


def mobius_matpow(a, b, c, d, n: int):
    """[[A,B],[C,D]] = [[a,b],[c,d]]^n over ℚ (exact), by binary exponentiation — O(log n)."""
    import sympy as sp
    M = sp.Matrix([[a, b], [c, d]])
    return M ** n


def _prove_compose_identity(a, b, c, d, sample_ns: Sequence[int]) -> Tuple[bool, Optional[int]]:
    """z3 NRA: for each sample N, prove ∀x the cleared-denominator polynomial identity p_N(x)·(C·x+D) −
    (A·x+B)·q_N(x) ≡ 0, where p_N/q_N is the N-fold composition (sympy) and (A·x+B)/(C·x+D) is M^N. residual=0."""
    import sympy as sp
    import z3
    x = sp.Symbol("x")
    f = (a * x + b) / (c * x + d)
    comp = x
    for N in range(1, max(sample_ns) + 1):
        comp = sp.cancel(f.subs(x, comp))                      # f^N as a single rational
        if N not in sample_ns:
            continue
        p, q = sp.fraction(comp)
        Mn = mobius_matpow(a, b, c, d, N)
        A, B, C, D = Mn[0, 0], Mn[0, 1], Mn[1, 0], Mn[1, 1]
        poly = sp.expand(p * (C * x + D) - (A * x + B) * q)    # must be identically 0
        # z3 NRA: ∀x poly(x) == 0  ⟺  UNSAT of poly(x) != 0
        zx = z3.Real("x")

        def _to_z3(e):
            e = sp.nsimplify(e)
            if e.is_Number:
                r = sp.Rational(e)
                return z3.RealVal(int(r.p)) / z3.RealVal(int(r.q))
            if e == x:
                return zx
            if e.is_Add:
                acc = _to_z3(e.args[0])
                for t in e.args[1:]:
                    acc = acc + _to_z3(t)
                return acc
            if e.is_Mul:
                acc = _to_z3(e.args[0])
                for t in e.args[1:]:
                    acc = acc * _to_z3(t)
                return acc
            if e.is_Pow and e.exp.is_Integer and int(e.exp) >= 0:
                acc = z3.RealVal(1)
                for _ in range(int(e.exp)):
                    acc = acc * _to_z3(e.base)
                return acc
            raise ValueError(f"cannot encode {e}")
        try:
            zpoly = _to_z3(sp.expand(poly))
        except ValueError:
            if poly != 0:
                return False, N
            continue
        s = z3.Solver()
        s.add(zpoly != 0)
        if s.check() != z3.unsat:
            return False, N
    return True, None


def mobius_fold_grade(a, b, c, d, label: str = "mobius_fold",
                      sample_ns: Sequence[int] = (1, 2, 3, 5)) -> KV.Verdict:
    """Fold the homographic recurrence x ← (a·x+b)/(c·x+d) to its O(log N) projective matrix-power closed form, proved
    by the z3 cleared-denominator polynomial identity over sample N (+ the PGL₂ homomorphism for all N). EXACT or
    DECLINE (degenerate ad−bc = 0)."""
    import sympy as sp
    det = sp.Integer(a) * d - sp.Integer(b) * c
    if det == 0:
        return KV.decline("mobius_fold: ad−bc = 0 — degenerate (the map collapses to a constant) ⇒ DECLINE", label)
    ok, badN = _prove_compose_identity(a, b, c, d, sample_ns)
    if not ok:
        return KV.decline(f"mobius_fold: projective identity FAILED at N={badN} — matrix-power ≠ composition ⇒ DECLINE", label)
    n = sp.Symbol("n")
    pole = "no pole (c=0 ⇒ affine, always defined)" if c == 0 else \
           f"decidable island: initial states whose orbit avoids the pole x = {sp.Rational(-d, c)} (per-step undefined)"
    cert = KV.Cert(KV.EXACT, "matrix_recurrence", passed=True,
                   check_cost=f"z3 NRA cleared-denominator polynomial identity ∀x for N∈{tuple(sample_ns)} (residual=0)",
                   detail=f"homographic x↦({a}x+{b})/({c}x+{d}) lifted to P¹: [u;v]↦[[{a},{b}],[{c},{d}]]·[u;v]; "
                          f"N iterations = M^N (O(log N)); proved by the projective polynomial identity; {pole}")
    return KV.exact({"a": a, "b": b, "c": c, "d": d, "via": "projective_matrix_power", "det": int(det),
                     "asymptotic": "O(N)→O(log N)"}, label, "Möbius/homographic fold (⑬ projective face)", cert)


# detect `x = (a*x + b) / (c*x + d)`  (degree-1 homographic, constant integer coefficients)
_MOBIUS = re.compile(
    r"(\w+)\s*=\s*\(\s*(-?\d+)\s*\*\s*\1\s*\+\s*(-?\d+)\s*\)\s*/\s*\(\s*(-?\d+)\s*\*\s*\1\s*\+\s*(-?\d+)\s*\)")
# simpler numerator/denominator forms: x = (b) / (c*x + d)  and  x = (a*x+b)/(d)
_MOBIUS_NUMC = re.compile(r"(\w+)\s*=\s*(-?\d+)\s*/\s*\(\s*(-?\d+)\s*\*\s*\1\s*\+\s*(-?\d+)\s*\)")


def mobius_recurrence_grade(code: str, label: str = "mobius_fold") -> KV.Verdict:
    """Detect a constant-coefficient degree-1 homographic recurrence in a loop and fold it. A degree-≥2 rational
    update (x*x in the numerator/denominator) does not match these patterns ⇒ DECLINE (the Galois/chaos boundary)."""
    if "**" in code or re.search(r"\*\s*\w+\s*\*", code):    # crude degree-≥2 guard (x*x etc.)
        return KV.decline("mobius_fold: nonlinear (degree-≥2) rational recurrence — Galois barrier ⇒ DECLINE", label)
    m = _MOBIUS.search(code)
    if m:
        a, b, c, d = int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))
        return mobius_fold_grade(a, b, c, d, label=label)
    m = _MOBIUS_NUMC.search(code)
    if m:
        b, c, d = int(m.group(2)), int(m.group(3)), int(m.group(4))
        return mobius_fold_grade(0, b, c, d, label=label)
    return KV.decline("mobius_fold: no degree-1 homographic recurrence x=(a*x+b)/(c*x+d) found ⇒ DECLINE", label)
