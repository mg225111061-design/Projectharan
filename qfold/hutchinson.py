"""
§AY QLA-7 — Hutchinson stochastic trace / SLQ (PROBABILISTIC, derived δ — NEVER EXACT).
================================================================================================================
E[zᵀAz] = tr(A) for Rademacher z (±1). M probes estimate tr(A) (or tr(f(A)) via SLQ). For SPD A the Roosta–Ascher
bound gives M ≥ 6ε⁻²ln(2/δ) ⟹ δ = 2·exp(−M·ε²/6) — a DERIVED tail bound, NOT an empirical pass-rate. This is a
B-axis (speedup) face only: O(n³)→O(n·matvec·M). It is graded PROBABILISTIC and can NEVER be EXACT (§0.2 / §1.1).

★ If the affordable M cannot meet the required δ ⇒ DECLINE (a sample count is never inflated into EXACT). Probes are
DETERMINISTIC (reproducible) so the estimate is stable; the δ is the derived theorem bound regardless.
"""
from __future__ import annotations

import math
from fractions import Fraction
from typing import Sequence

import kernel_verdict as KV

from . import _la


def _rademacher(idx: int, n: int):
    """A deterministic ±1 probe vector (reproducible — no RNG). Sign = parity of a fixed bit-mix of (idx, j)."""
    out = []
    for j in range(n):
        h = (idx * 73856093) ^ (j * 19349663) ^ ((idx + 1) * (j + 3) * 83492791)
        out.append(1 if bin(h & 0xFFFF).count("1") % 2 == 0 else -1)
    return out


def hutchinson_trace(A: Sequence[Sequence], probes: int = 64, epsilon: float = 0.1,
                     required_delta: float = 0.05) -> KV.Verdict:
    """Estimate tr(A) by M Rademacher probes; grade PROBABILISTIC with the DERIVED Roosta–Ascher δ. DECLINE if the
    affordable M cannot reach required_delta (never inflate a sample count into EXACT)."""
    try:
        Af = _la.fmat(A)
    except _la.NonExact:
        # floats are allowed here (this is a numeric estimator) — coerce loosely for the estimate
        Af = [[Fraction(x).limit_denominator(10 ** 9) if not isinstance(x, float) else x for x in row] for row in A]
    n = len(Af)
    if n == 0 or probes < 1 or epsilon <= 0:
        return KV.decline("hutchinson: bad inputs", "hutchinson_trace")
    delta = 2.0 * math.exp(-probes * epsilon * epsilon / 6.0)             # ★ DERIVED (Roosta–Ascher), not empirical
    if delta > required_delta:
        need = math.ceil(6.0 / (epsilon * epsilon) * math.log(2.0 / required_delta))
        return KV.decline(f"hutchinson: derived δ={delta:.2e} (M={probes}, ε={epsilon}) exceeds required "
                          f"{required_delta:.2e} — would need M≥{need} probes; DECLINE rather than overclaim",
                          "hutchinson_trace")
    acc = 0.0
    for i in range(probes):
        z = _rademacher(i, n)
        Az = [float(sum(Af[r][c] * z[c] for c in range(n))) for r in range(n)]
        acc += sum(z[r] * Az[r] for r in range(n))
    est = acc / probes
    cert = KV.Cert(KV.PROBABILISTIC, "stochastic_trace", passed=True, check_cost=f"{probes} matvecs (O(n·M))",
                   epsilon=epsilon, delta=delta,
                   detail=f"Hutchinson estimate of tr(A) with {probes} Rademacher probes; Roosta–Ascher δ=2·exp(−M·ε²/6)"
                          f"={delta:.2e} (derived). PROBABILISTIC — never EXACT.")
    return KV.probabilistic(est, "hutchinson_trace", f"O(n·matvec·M) (M={probes})", cert,
                            reason="Axis-B only (no Axis-A coverage); a stochastic trace estimate, derived tail bound")


def adversarial_battery() -> dict:
    """★ PROBABILISTIC: a trace estimate with enough probes carries a derived δ ≤ required and is graded PROBABILISTIC
    (never EXACT). ★★ DECLINE: too few probes for the required δ ⇒ DECLINE (no sample-count→EXACT inflation)."""
    diag = [[i + 1 if i == j else 0 for j in range(8)] for i in range(8)]    # tr = 36
    ok = hutchinson_trace(diag, probes=4000, epsilon=0.2, required_delta=0.05)
    prob_ok = ok.status == KV.PROBABILISTIC and ok.certificate.delta is not None and ok.certificate.delta <= 0.05
    never_exact = ok.status != KV.EXACT
    tight = hutchinson_trace(diag, probes=10, epsilon=0.01, required_delta=1e-9)
    tight_declines = tight.status == KV.DECLINE                              # ★★ can't meet δ ⇒ DECLINE
    cases = {"trace_probabilistic": prob_ok, "never_exact": never_exact, "tight_delta_declines": tight_declines}
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, x in cases.items() if not x]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
