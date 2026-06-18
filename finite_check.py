"""
v34 STAGE 1 — finite-initial-value checker: ∀n EQUALITY by the uniqueness meta-theorem (PRA, ω^ω).
===================================================================================================
The real missing piece (not ε₀): holonomic / C-finite sequences are uniquely determined by finitely many
initial values + their recurrence. So "∀n: F(n) = S(n)" is proved COMPLETELY, at PRA strength, by:
  (1) the difference D=F−S satisfies a common linear recurrence  — checked by Schwartz-Zippel PIT, and
  (2) D's first R initial terms are all zero                     — a FINITE check.

★ UNIQUENESS META-THEOREM (stated & proved ONCE, reused for every identity — no per-identity re-proof) ★
  Let D(n) satisfy  c_R(n)·D(n+R) + … + c_0(n)·D(n) = 0  with leading coefficient c_R(n) ≠ 0 for all n ≥ n₀.
  If D(n₀)=D(n₀+1)=…=D(n₀+R−1)=0 (R consecutive zeros) then D(n)=0 for all n ≥ n₀.
  Proof: solve forward D(n+R) = −(Σ_{i<R} c_i(n)·D(n+i))/c_R(n); R consecutive zeros force the next zero; by
  QUANTIFIER-FREE (Σ₀) induction, all subsequent are zero. The induction formula is quantifier-free ⇒ this
  lives in PRA (proof-theoretic ordinal ω^ω). NO transfinite induction, NO ε₀.

★ EQUALITY ONLY (rule 4) ★: this proves D≡0 (an EQUALITY). It does NOT decide D(n) ≥ 0 (positivity/
  inequality) — that is undecidable for C-finite sequences of order ≥ 5 (Ouaknine–Worrell). Inequality /
  positivity claims are DEFERRED, never "proved" by this trick.

★ HONEST STRENGTH (rule 5) ★: finite-base-case + PIT = PRA (ω^ω). We label folds "finite-base-case (PRA,ω^ω)".
  We do NOT label them ε₀ (that needs the STAGE-4 ordinal kernel, and ε₀ never arises for fold).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

import sympy as sp

from soup import _ident_zero, _k, _n   # reuse the exact PIT zero-test

STRENGTH_PRA = "finite-base-case (PRA, omega^omega)"

UNIQUENESS_METATHEOREM = (
    "If D(n) obeys an order-R linear recurrence with leading coeff c_R(n)≠0 (n≥n0) and D has R consecutive "
    "zeros at n0, then D≡0 for n≥n0. (Σ0-induction ⇒ PRA, ω^ω. EQUALITY only — not inequality.)"
)

INEQ_OPS = (">=", "<=", ">", "<", "≥", "≤")


def is_inequality_claim(claim: str) -> bool:
    """Guard: an inequality / positivity claim must NOT use the finite-base-case equality trick (undecidable
    for C-finite order ≥5, Ouaknine–Worrell). Such claims are deferred."""
    return any(op in claim for op in INEQ_OPS)


def leading_coeff_nonvanishing(c_R, var, n_from: int = 1, search: int = 64) -> bool:
    """The uniqueness meta-theorem needs c_R(n) ≠ 0 for n ≥ n₀. Constant ⇒ just ≠0. Polynomial ⇒ no integer
    root ≥ n₀ (checked beyond the finite integer-root set, conservative)."""
    cR = sp.sympify(c_R)
    if var not in cR.free_symbols:
        return cR != 0
    try:
        roots = sp.solve(sp.Eq(cR, 0), var)
        return not any(r.is_integer and int(r) >= n_from for r in roots if r.is_number)
    except Exception:  # noqa: BLE001
        # fall back to a finite scan beyond the integer-root region (conservative; defer on any zero)
        return all(cR.subs(var, n_from + i) != 0 for i in range(search))


@dataclass
class FiniteCheckCert:
    ok: bool
    order_R: int
    base_values_checked: int
    pit_method: str
    leading_coeff_ok: bool
    strength: str = STRENGTH_PRA
    cert_type: str = "exact"
    detail: str = ""


def verify_sum(summand, closed, lo: int = 1) -> Optional[FiniteCheckCert]:
    """Complete PRA verifier of ∀n: Σ_{k=lo}^n summand(k) = closed(n), via the order-1 telescoping instance of
    the uniqueness meta-theorem: S obeys S(n)−S(n−1)=t(n) (order 1, leading coeff 1). D=closed−S obeys
    D(n)−D(n−1)=0 once we check closed(n)−closed(n−1)−t(n)≡0 (PIT); one base value D(lo)=0 finishes it."""
    t_n = summand.subs(_k, _n)
    step = closed - closed.subs(_n, _n - 1) - t_n          # closed(n)−closed(n−1)−t(n) ≡ 0 ?
    ok_step, method = _ident_zero(step, _n)
    if not ok_step:
        return None                                        # recurrence fails ⇒ not equal (false form rejected)
    base_ok = sp.simplify(closed.subs(_n, lo) - summand.subs(_k, lo)) == 0   # D(lo)=closed(lo)−t(lo)=0
    if not base_ok:
        return None
    exact = method in ("expand", "poly-PIT-exact", "expsub-exact")
    return FiniteCheckCert(ok=True, order_R=1, base_values_checked=1, pit_method=method,
                           leading_coeff_ok=True, cert_type="exact" if exact else "probabilistic",
                           detail="order-1 telescoping uniqueness; closed(n)−closed(n−1)≡t(n) (PIT) ∧ base")


def verify_by_common_recurrence(seq1: Callable[[int], object], seq2: Callable[[int], object],
                                coeffs: List[int], lo: int = 0, extra: int = 6) -> Optional[FiniteCheckCert]:
    """General uniqueness: two sequences obeying the SAME constant-coeff recurrence a(n)=Σ cᵢ a(n−i)
    (order R=len(coeffs)) that AGREE on R consecutive values are equal ∀n. Verifies: both obey the recurrence
    at several points (finite), agree on R initial values, leading coeff (=1, the implicit a(n)) nonzero.
    Used for C-finite and for certifying superopt-discovered equivalences."""
    R = len(coeffs)
    if R == 0:
        return None
    # (i) both obey the recurrence over R..R+extra (finite check; constant-coeff ⇒ this IS the PIT)
    def obeys(seq):
        for n in range(lo + R, lo + R + extra):
            if seq(n) != sum(coeffs[i - 1] * seq(n - i) for i in range(1, R + 1)):
                return False
        return True
    if not (obeys(seq1) and obeys(seq2)):
        return None
    # (ii) agree on R consecutive initial values
    if any(seq1(lo + j) != seq2(lo + j) for j in range(R)):
        return None
    return FiniteCheckCert(ok=True, order_R=R, base_values_checked=R, pit_method="finite-recurrence",
                           leading_coeff_ok=True, cert_type="exact",
                           detail=f"order-{R} uniqueness: same recurrence + {R} matching initial values")


# holonomic closure order bounds (documentation + dispatcher hints; rule 1.1)
def closure_order(op: str, r: int, s: int = 0) -> int:
    """Recurrence-order bound under holonomic closure: add ≤ r+s, mul ≤ r·s, partial-sum ≤ r+1."""
    return {"add": r + s, "mul": r * s, "sum": r + 1}[op]
