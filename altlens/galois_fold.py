"""
§Y LENS 5 — EXACT SEMANTIC QUOTIENT VIA GALOIS CONNECTION (semantic-equivalence-class lens).
================================================================================================================
A computation whose state is EXACTLY captured by a small finite abstract domain D (α: Concrete↠D) collapses an n-step
loop to motion inside D. Because |D| is finite, the abstract orbit f#^•(α(x0)) MUST cycle within |D| steps (pigeonhole),
so n≫|D| folds O(n)→O(|D|)≈O(1). Canonical exact domain: ℤ/mℤ under an affine map x←a·x+b — modular arithmetic commutes
with the map EXACTLY. This is the equivalence-class lens — orthogonal to the algebra (tropical) and order (lattice) lenses.

★ z3 gate (precision 1.0): prove the abstraction is EXACT — the diagram commutes, ∀x. α(f(x)) == f#(α(x)). EXACT ⇒ the
abstract orbit reproduces the concrete computation with NO information loss ⇒ fold sound. If only α(f(x)) ⊒ f#(α(x))
(over-approximation — the abstract result is a SET, not a point), the fold would be UNSOUND ⇒ DECLINE. The trap: sign
abstraction of x−1 is an over-approximation (α(+)∈{+,0}, not single-valued) and MUST be declined.
★ |D|-blowup: the fold O(n)→O(|D|) is a speedup ONLY when |D| is genuinely small; a large modulus ⇒ DECLINE (no win).
★ QF_BV overlap SUBTRACTED: when m is a power of two, x mod m == x & (m−1) — already folded by the existing bitvector
(QF_BV) machinery. Such cases are DECLINED here (not a NEW fold) so the lens's added fold rate is not double-counted.

★ Reduces to the existing linear-recurrence / periodic-orbit kind (an affine map over ℤ/mℤ is a linear recurrence mod m);
the certificate NOTES the exact quotient. No new certificate kind.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple


@dataclass
class GaloisFold:
    issued: bool                                # the abstraction was z3-proved EXACT and the domain is small
    paradigm: str = "galois_quotient"
    mechanism: str = "linear_recurrence"        # an EXISTING kind — affine-mod-m is a linear recurrence over ℤ/mℤ
    domain_size: Optional[int] = None           # |D| — the number of abstract states
    tail: Optional[int] = None                  # k: steps before the orbit enters its cycle
    period: Optional[int] = None                # p: the cycle length (k+p ≤ |D|)
    applied_callsites: List[str] = field(default_factory=list)
    skipped_callsites: List[str] = field(default_factory=list)
    detail: str = ""

    @property
    def applied(self) -> bool:
        return bool(self.applied_callsites)


def _is_power_of_two(m: int) -> bool:
    return m > 0 and (m & (m - 1)) == 0


def prove_exact_abstraction(alpha: Callable, f_conc: Callable, f_abs: Callable, sort: str = "Int") -> bool:
    """z3 ∀-prove the abstraction is EXACT: ∀x. α(f(x)) == f#(α(x)) (the Galois diagram commutes with NO loss).
    unsat of the negation ⇒ exact ⇒ fold sound. sat ⇒ over-approximation (or wrong f#) ⇒ NOT exact ⇒ caller DECLINEs."""
    import z3
    x = z3.Int("x") if sort == "Int" else z3.BitVec("x", 32)
    s = z3.Solver()
    s.add(alpha(f_conc(x)) != f_abs(alpha(x)))
    return s.check() == z3.unsat


def _orbit_cycle(step: Callable[[int], int], r0: int, bound: int) -> Tuple[List[int], int, int]:
    """Iterate the abstract step from r0 until a state repeats; return (orbit_prefix, tail k, period p).
    Guaranteed to terminate within `bound` (=|D|) steps by pigeonhole. orbit_prefix lists the first k+p states."""
    seen = {}
    orbit = []
    r = r0
    i = 0
    while r not in seen and i <= bound:
        seen[r] = i
        orbit.append(r)
        r = step(r)
        i += 1
    k = seen[r]                                  # first index where the repeated state was first seen → tail length
    p = i - k                                    # period
    return orbit, k, p


def galois_modular_fold(a: int, b: int, m: int, max_domain: int = 4096) -> GaloisFold:
    """Issue the exact-quotient fold for the affine map x←a·x+b under α(x)=x mod m, iff:
      (1) m is NOT a power of two  (else QF_BV already folds it — overlap subtracted ⇒ DECLINE),
      (2) |D|=m is small           (m>max_domain ⇒ no speedup ⇒ DECLINE),
      (3) the abstraction is z3-proved EXACT: ∀x. (a·x+b) mod m == (a·(x mod m)+b) mod m.
    Then the abstract orbit cycles within m steps ⇒ fold O(n)→O(m). Reduces to linear-recurrence (mod m); kind unchanged."""
    if m <= 1:
        return GaloisFold(False, domain_size=m, detail=f"trivial modulus m={m} ⇒ no quotient ⇒ DECLINE")
    if _is_power_of_two(m):
        return GaloisFold(False, domain_size=m,
                          detail=f"m={m} is a power of two ⇒ x mod m == x & {m-1} is ALREADY folded by QF_BV; "
                                 "overlap SUBTRACTED ⇒ DECLINE (not counted as a new Galois fold)")
    if m > max_domain:
        return GaloisFold(False, domain_size=m,
                          detail=f"|D|=m={m} exceeds the small-domain cap {max_domain} ⇒ O(n)→O(|D|) is no speedup ⇒ DECLINE")

    import z3
    alpha = lambda x: x % m
    f_conc = lambda x: a * x + b
    f_abs = lambda r: (a * r + b) % m
    if not prove_exact_abstraction(alpha, f_conc, f_abs, sort="Int"):
        return GaloisFold(False, domain_size=m,
                          detail="abstraction NOT exact (α∘f ≠ f#∘α — over-approximation) ⇒ fold would be UNSOUND ⇒ DECLINE")

    # exact ⇒ compute the abstract orbit cycle (tail k, period p, both ≤ m) from a representative start
    step = lambda r: (a * r + b) % m
    _, k, p = _orbit_cycle(step, 0, m)
    return GaloisFold(True, domain_size=m, tail=k, period=p,
                      detail=f"α(x)=x mod {m}; affine map x←{a}·x+{b} commutes EXACTLY (z3-proved ∀x); abstract orbit "
                             f"has tail {k}, period {p} (≤|D|={m}) ⇒ n≥{k} folds O(n)→O({k}+(n−{k}) mod {p}). "
                             "Reduces to linear-recurrence over ℤ/mℤ; exact quotient noted (no new kind)")


def fold_eval(a: int, b: int, m: int, x0: int, n: int) -> int:
    """Evaluate f#^n(α(x0)) via the orbit cycle in O(k+p) instead of O(n) — the actual folded computation."""
    step = lambda r: (a * r + b) % m
    orbit, k, p = _orbit_cycle(step, x0 % m, m)
    if n < len(orbit):
        return orbit[n]
    return orbit[k + (n - k) % p]


def verify_orbit_fold(a: int, b: int, m: int, x0: int, sample_n=(1, 3, 7, 13, 50, 97)) -> bool:
    """Differential soundness: the folded f#^n(α(x0)) equals α(f^n(x0)) computed the long way, for sample n. Confirms the
    orbit fold reproduces the abstracted concrete computation exactly (the fold's correctness, separate from exactness)."""
    for n in sample_n:
        x = x0
        for _ in range(n):
            x = a * x + b                        # concrete iteration (unbounded ℤ)
        direct = x % m                           # α(f^n(x0))
        folded = fold_eval(a, b, m, x0, n)       # f#^n(α(x0)) via the cycle
        if direct != folded:
            return False
    return True


def apply_at_callsite(gf: GaloisFold, callsite: str, n: int) -> bool:
    """Apply the quotient fold ONLY where the loop runs n > |D| iterations (then the O(|D|) cycle genuinely beats O(n)).
    n ≤ |D| ⇒ keep the original (no win to bank)."""
    if not gf.issued or gf.domain_size is None or n <= gf.domain_size:
        gf.skipped_callsites.append(callsite)
        return False
    gf.applied_callsites.append(callsite)
    return True


def _sign_abstraction_candidate():
    """Build the sign-abstraction instance for f(x)=x−1 with the natural single-valued candidate f# — used by the battery
    to confirm an OVER-APPROXIMATION is rejected. α(x)=sign(x)∈{−1,0,1}; the candidate guesses f#(+1)=+1, which the
    exactness prover refutes (x=1: α(0)=0 ≠ f#(+1)=+1)."""
    import z3
    def alpha(x):
        return z3.If(x < 0, -1, z3.If(x == 0, 0, 1))
    f_conc = lambda x: x - 1
    # natural monotone single-valued candidate (it CANNOT be exact — that's the point)
    def f_abs(s):
        return z3.If(s == 1, 1, z3.If(s == 0, -1, -1))
    return alpha, f_conc, f_abs


def adversarial_battery() -> dict:
    """An exact ℤ/mℤ affine quotient (m=7, non-power-of-two, small) is issued; sign-abstraction of x−1 (over-approx) is
    DECLINED; a power-of-two modulus (QF_BV overlap) is DECLINED-not-double-counted; a huge modulus (|D|-blowup) is
    DECLINED; the orbit fold reproduces the concrete computation (differential)."""
    exact = galois_modular_fold(3, 1, 7)                     # exact, small, non-power-of-two ⇒ issued
    pow2 = galois_modular_fold(3, 1, 8)                      # power of two ⇒ QF_BV overlap ⇒ declined
    blow = galois_modular_fold(3, 1, 1_000_003)             # |D| huge ⇒ no speedup ⇒ declined
    diff_ok = verify_orbit_fold(3, 1, 7, 5)                  # folded == long-way for sample n
    # sign abstraction of x−1 is an over-approximation ⇒ exactness must FAIL ⇒ declined
    alpha, f_conc, f_abs = _sign_abstraction_candidate()
    sign_exact = prove_exact_abstraction(alpha, f_conc, f_abs, sort="Int")
    # applied only when n > |D|
    applied_big = apply_at_callsite(exact, "n_10000", 10000)
    applied_small = apply_at_callsite(exact, "n_3", 3)
    cases = {
        "exact_modular_issued": exact.issued and exact.period is not None,
        "sign_over_approx_rejected": not sign_exact,
        "power_of_two_overlap_declined": not pow2.issued and "QF_BV" in pow2.detail,
        "domain_blowup_declined": not blow.issued,
        "orbit_fold_sound": diff_ok,
        "applied_when_n_gt_domain": applied_big,
        "kept_original_when_n_le_domain": not applied_small,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
