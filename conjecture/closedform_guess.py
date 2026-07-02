"""
§AI §1.3 — POLYNOMIAL / RATIONAL closed-form conjecturer. Defeats: disguised Σk, Σk², polynomial DP.
================================================================================================================
Observe the output, detect a polynomial closed form by FINITE DIFFERENCES (a degree-d sequence has a constant d-th
difference and a zero (d+1)-th), then z3-prove the closed form satisfies the (d+1)-order linear recurrence with
characteristic (x−1)^{d+1} ∀n (REUSE the harness companion proof), with the held-out divergence guard. A
degree-d conjecture needs ≥ 2d+2 observations (under-determination guard). DECLINE if not polynomial / unproven.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Callable, List, Optional

from conjecture import harness as H


def _poly_degree(seq: List[Fraction], max_deg: int = 8) -> Optional[int]:
    """Smallest d such that the (d+1)-th finite difference is all zero (⇒ degree-d polynomial). None if none ≤ max_deg."""
    diffs = list(seq)
    for d in range(max_deg + 1):
        if all(x == 0 for x in diffs):
            return max(0, d - 1)
        diffs = [diffs[i + 1] - diffs[i] for i in range(len(diffs) - 1)]
        if not diffs:
            return None
    return None


def _binom_recurrence_coeffs(d: int) -> List[int]:
    """A degree-d polynomial satisfies a[n] = Σ_{j=1}^{d+1} (-1)^{j+1} C(d+1,j) a[n-j] (characteristic (x−1)^{d+1})."""
    from math import comb
    return [((-1) ** (j + 1)) * comb(d + 1, j) for j in range(1, d + 2)]


def conjecture(fn: Callable[[int], object], probe: int = 24, holdout: int = 200) -> H.ConjResult:
    import kernel_verdict as KV
    seq = H.observe(fn, probe)
    if seq is None:
        return H.ConjResult(False, "none", 0, "-", None, "non-deterministic / non-numeric ⇒ ABANDON")
    fseq = [Fraction(x) for x in seq]
    d = _poly_degree(fseq)
    if d is None:
        return H.ConjResult(False, "none", 0, "-", KV.decline("not a finite-difference polynomial ⇒ DECLINE", "closedform"),
                            "no finite polynomial degree ⇒ DECLINE (not this structure class)")
    if H.under_determined(probe, d):
        return H.ConjResult(False, "polynomial", d, "-", KV.decline("under-determined ⇒ ABANDON", "closedform"),
                            f"degree {d} needs ≥{2 * d + 2} observations ⇒ ABANDON")
    coeffs = _binom_recurrence_coeffs(d)
    if not H.prove_companion_consecution(coeffs):
        return H.ConjResult(False, "polynomial", d, "-", KV.decline("z3 ∀-proof failed ⇒ DECLINE", "closedform"),
                            "★ observation polynomial-like but z3 ∀-proof failed ⇒ DECLINE (P-2)")
    # held-out divergence guard: the (d+1)-order recurrence must predict unseen terms EXACTLY
    try:
        ext = [Fraction(fn(i)) for i in range(probe, probe + holdout)]
    except Exception:  # noqa: BLE001
        return H.ConjResult(False, "polynomial", d, "-", KV.decline("held-out probe raised ⇒ DECLINE", "closedform"), "held-out raised")
    s = fseq + ext
    for i in range(probe, len(s)):
        pred = sum(Fraction(coeffs[j]) * s[i - 1 - j] for j in range(len(coeffs)))
        if pred != s[i]:
            return H.ConjResult(False, "polynomial", d, "-", KV.decline("held-out diverged ⇒ DECLINE", "closedform"),
                                f"★ matched the probe but held-out term {i} diverged ⇒ DECLINE (P-2)")
    cert = KV.Cert(KV.EXACT, "closed_form", passed=True, check_cost=f"finite-diff degree {d} + z3 ∀-proof + {holdout} held-out",
                   detail=f"polynomial closed form degree {d}; (d+1)-order recurrence z3-verified ∀n + held-out divergence guard")
    return H.ConjResult(True, "polynomial", d, "blackbox+z3", KV.exact({"degree": d}, "closedform", "O(1) closed form", cert),
                        f"disguised degree-{d} polynomial recovered; z3 ∀-proof + held-out ⇒ EXACT (closed_form kind)")


def adversarial_battery() -> dict:
    """A disguised Σk² (degree-3) folds EXACT (finite-diff + z3 + held-out); ★ the primes — which MATCH an
    interpolating polynomial on the probe but diverge — DECLINE; a too-short probe ABANDONS (under-determination)."""
    sq = conjecture(lambda n: sum(k * k for k in range(n + 1)))      # Σk² = degree-3 polynomial
    # ★ primes: a degree-k polynomial fits the first k+1 primes exactly, but they are NOT polynomial ⇒ held-out diverges
    def nth_prime(n):
        c, x = 0, 1
        while True:
            x += 1
            if all(x % p for p in range(2, int(x ** 0.5) + 1)):
                if c == n:
                    return x
                c += 1
    primes = conjecture(nth_prime)
    short = conjecture(lambda n: sum(k * k for k in range(n + 1)), probe=4)   # too few for degree 3
    cases = {
        "disguised_poly_folds": sq.issued and sq.structure_class == "polynomial",
        "primes_decline": not primes.issued,                        # ★ P-2: poly-fit but not polynomial ⇒ DECLINE
        "under_determined_abandons": not short.issued,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
