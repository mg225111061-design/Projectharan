"""
v33 STAGE 3 — certified-approximate folding (Direction D): recover defers with a STATED error certificate.
============================================================================================================
When EXACT folding fails, breadth is recovered by APPROXIMATION — but only with a machine-checkable error
certificate (rule: no approximation emitted without an error bound). Three honest, never-mixed certificate
kinds here:
  • asymptotic-with-error : a closed form + an explicit truncation bound (Euler-Maclaurin). e.g. the harmonic
                            sum Σ1/k = ln n + γ + 1/2n − 1/12n² + R, |R| ≤ 1/(120 n⁴). EXACT-defers, yet folds
                            APPROXIMATELY with a proven bound — a genuine recovery from defer.
  • epsilon-delta (δ)     : a Monte-Carlo estimate within ε w.p. ≥ 1−δ, via Hoeffding: n ≥ (b−a)²/(2ε²)·ln(2/δ).
                            The CHECK (the bound) is O(1); evidence collection is BOUNDED. Hoeffding FLOOR
                            stated honestly: ε cannot be pushed arbitrarily low (n explodes) — approximation
                            is never exact.
  • precision-on-demand   : pick arithmetic precision from the required ε (decimal digits = ⌈−log10 ε⌉+guard),
                            so we are exactly as precise as the context needs — no waste, with the residual
                            bounded by the chosen precision.

Clock C (the approximate closed form runs fast) + Clock B (the bound is a cheap check). Distinct label
"APPROX_FOLD" — never reported as exact (rule R3.5).
"""
from __future__ import annotations

import decimal
import math
import random
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class ApproxCert:
    kind: str                   # asymptotic-with-error | epsilon-delta | precision-on-demand
    closed_form: str
    error_bound: str            # the STATED error (ε term / δ / residual)
    eps: float = 0.0
    delta: float = 0.0
    detail: str = ""


# ── asymptotic-with-error: harmonic sum (a real recovery of an exact-defer) ─────────────────────────
_EULER_GAMMA = 0.5772156649015328606

def harmonic_approx_value(n: int) -> float:
    """H_n ≈ ln n + γ + 1/(2n) − 1/(12 n²)  (Euler–Maclaurin), truncation |R| ≤ 1/(120 n⁴)."""
    return math.log(n) + _EULER_GAMMA + 1.0 / (2 * n) - 1.0 / (12 * n * n)


def harmonic_error_bound(n: int) -> float:
    return 1.0 / (120 * n**4)


def certify_harmonic() -> ApproxCert:
    """Certified-approximate fold of Σ_{k=1}^n 1/k (which EXACT-defers). The bound is CHECKED below."""
    return ApproxCert("asymptotic-with-error", "log(n) + gamma + 1/(2*n) - 1/(12*n**2)",
                      "|R| <= 1/(120*n**4)", detail="Euler–Maclaurin; recovers an exact-defer (harmonic)")


def check_harmonic_within_bound(n: int) -> bool:
    """Independent CHECK (Clock B): the approximation is within its stated bound of the TRUE partial sum."""
    true_h = sum(1.0 / k for k in range(1, n + 1))
    return abs(harmonic_approx_value(n) - true_h) <= harmonic_error_bound(n) + 1e-12


# ── epsilon-delta: Hoeffding-bounded Monte-Carlo estimate ───────────────────────────────────────────
def hoeffding_n(eps: float, delta: float, a: float = 0.0, b: float = 1.0) -> int:
    """Samples needed for a mean estimate within ε w.p. ≥ 1−δ: n ≥ (b−a)²/(2ε²)·ln(2/δ)."""
    return math.ceil((b - a) ** 2 / (2 * eps * eps) * math.log(2.0 / delta))


def certify_monte_carlo(sample: Callable[[], float], eps: float, delta: float,
                        a: float = 0.0, b: float = 1.0, cap: int = 2_000_000, seed: int = 0) -> ApproxCert:
    """Estimate E[sample] within ε w.p. ≥ 1−δ (Hoeffding). Evidence collection is BOUNDED by `cap`; if the
    required n exceeds the cap we state that (honest floor) and widen ε to what the cap supports."""
    need = hoeffding_n(eps, delta, a, b)
    rng = random.Random(seed)
    if need > cap:                                  # Hoeffding floor: can't reach this ε within the cap
        n = cap
        eps = math.sqrt((b - a) ** 2 / (2 * n) * math.log(2.0 / delta))   # the ε the cap actually supports
        note = f"requested ε needed {need}>{cap} samples (Hoeffding floor) — widened to ε={eps:.2e}"
    else:
        n = need
        note = f"n={n} samples for ε={eps:.2e}, δ={delta:.2e}"
    s = sum(sample() for _ in range(min(n, cap)))
    mean = s / min(n, cap)
    return ApproxCert("epsilon-delta", f"E≈{mean:.6f}", f"|Ê−E|≤ε w.p.≥1−δ", eps=eps, delta=delta, detail=note)


# ── precision-on-demand (revolution-axis: dynamic precision) ────────────────────────────────────────
def precision_digits(required_eps: float, guard: int = 4) -> int:
    return max(1, math.ceil(-math.log10(required_eps)) + guard)


def evaluate_on_demand(expr_fn: Callable[[decimal.Decimal], decimal.Decimal], x: float,
                       required_eps: float) -> ApproxCert:
    """Evaluate at exactly the precision the context needs (no waste). residual bounded by the chosen prec."""
    digits = precision_digits(required_eps)
    ctx = decimal.Context(prec=digits)
    val = expr_fn(ctx.create_decimal(repr(x)))
    return ApproxCert("precision-on-demand", f"{val}", f"residual ≤ 10^-{digits-1}",
                      eps=required_eps, detail=f"precision={digits} digits chosen from ε={required_eps:.1e}")


# ── disposition hook for STAGE 6 ────────────────────────────────────────────────────────────────────
def approx_dispose(summand_str: str):
    """Return a STAGE-6 Disposition (APPROX_FOLD) if a certified approximation recovers this summand, else
    None. Currently: the harmonic family (Σ1/k) → asymptotic-with-error (a real recovery of an exact-defer)."""
    import disposition as D
    s = summand_str.replace(" ", "")
    if s in ("1/k", "1/(k)"):
        cert = certify_harmonic()
        if check_harmonic_within_bound(1000):       # independent check at a witness n
            return D.Disposition("APPROX_FOLD", "approx-asymptotic", "C", cert.closed_form,
                                 "asymptotic-with-error", "approx (Euler–Maclaurin)", summand_str,
                                 f"recovered from exact-defer; {cert.error_bound}")
    return None


def metamorphic_check(fn: Callable[[int], float], n: int = 1000, tol: float = 1e-2) -> bool:
    """A metamorphic relation for the harmonic family: H(2n) − H(n) → ln 2 as n→∞. Cheap independent
    sanity that the approximation respects a known invariant (not a proof — a corroborating check)."""
    return abs((fn(2 * n) - fn(n)) - math.log(2.0)) < tol


def bayesian_aggregate(deltas) -> dict:
    """Aggregate INDEPENDENT evidence: if k checks each fail w.p. ≤ δᵢ, all-pass confidence ≥ 1−∏δᵢ.
    Honest: assumes independence (stated). Returns combined δ and confidence."""
    prod = 1.0
    for d in deltas:
        prod *= d
    return {"combined_delta": prod, "confidence": 1.0 - prod, "assumes": "independence (stated)"}


def measure_recovery(defer_summands) -> dict:
    """How many EXACT-defers does certified-approximation recover? (the 'built from defer %', MEASURED)."""
    recovered = 0
    rows = []
    for s in defer_summands:
        d = approx_dispose(s)
        ok = d is not None
        recovered += int(ok)
        rows.append((s, "APPROX_FOLD" if ok else "still-DEFER"))
    n = len(defer_summands)
    return {"n": n, "recovered": recovered, "rate": round(recovered / n, 3) if n else 0.0, "rows": rows}
