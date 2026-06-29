"""
§AO §1.1 — CONSERVATION-LAW verification: an accelerated dynamics kernel must NOT break mass/momentum/energy.
================================================================================================================
★ This is precision-1.0's PHYSICS version — and nobody else gates an accelerated PDE/ODE kernel on the conservation
laws it must obey. A linear dynamics update u ← M·u (diffusion/wave/transport stencil, tiled/fused for speed) preserves
the conserved quantity Σu IFF every COLUMN of M sums to 1 (equivalently the increment matrix's columns sum to 0). We
z3-prove Σ(M·u) == Σ(u) ∀u (a linear identity, QF_LRA, terminating). A non-conservative accelerated stencil ⇒ z3 finds
a counterexample ⇒ the acceleration is REJECTED (the original kernel is kept). ★ false "conserved" = 0.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ConservationResult:
    conserved: bool
    quantity: str = "mass(Σu)"
    verdict: object = None
    detail: str = ""


def circulant_update(stencil: List[float], n: int = 6) -> List[List[float]]:
    """Build the n×n periodic-BC update matrix M = I + L from a symmetric 3-point stencil [a, b, a] (the increment
    L has row [a, b, a] centered, periodic). For the discrete Laplacian b = −2a, columns of L sum to 0 ⇒ M conserves."""
    L = [[0.0] * n for _ in range(n)]
    a, b, c = stencil
    for i in range(n):
        L[i][(i - 1) % n] += a
        L[i][i] += b
        L[i][(i + 1) % n] += c
    return [[(1.0 if i == j else 0.0) + L[i][j] for j in range(n)] for i in range(n)]


def verify_conservation(M: List[List[float]], quantity: str = "mass(Σu)") -> ConservationResult:
    """z3 (QF_LRA): prove Σᵢ(M·u)ᵢ == Σᵢ uᵢ ∀u — the accelerated update preserves the conserved quantity. A column
    of M not summing to 1 ⇒ z3 counterexample ⇒ DECLINE (reject the acceleration)."""
    import z3
    import kernel_verdict as KV
    n = len(M)
    if n == 0 or any(len(r) != n for r in M):
        return ConservationResult(False, quantity, KV.decline("conservation: non-square update", "accel.conservation"), "shape")
    from fractions import Fraction
    u = [z3.Real(f"u{i}") for i in range(n)]
    Mu = [z3.Sum([z3.RealVal(Fraction(M[i][j]).limit_denominator(10 ** 9)) * u[j] for j in range(n)]) for i in range(n)]
    s = z3.Solver()
    s.add(z3.Sum(Mu) != z3.Sum(u))                          # ∃u where the total is NOT preserved?
    if s.check() == z3.unsat:
        cert = KV.Cert(KV.EXACT, "invariant", passed=True, check_cost="z3 QF_LRA ∀u: Σ(Mu)==Σu",
                       detail=f"accelerated dynamics kernel preserves {quantity} ∀u (column sums == 1) — conservation z3-proven")
        return ConservationResult(True, quantity, KV.exact({"quantity": quantity, "n": n}, "accel.conservation",
                                  "conservation-preserving", cert), f"{quantity} conserved ∀u (z3 UNSAT of violation)")
    return ConservationResult(False, quantity, KV.decline(f"conservation: {quantity} NOT preserved (z3 counterexample) ⇒ "
                              "REJECT acceleration", "accel.conservation"), f"{quantity} broken — acceleration rejected")


def adversarial_battery() -> dict:
    """★ the discrete-Laplacian diffusion stencil [1,−2,1] CONSERVES mass (z3-proven ∀u) — its tiled/fused acceleration
    is accepted; ★ a NON-conservative stencil [1,−1,1] (column sums ≠ 1) is REJECTED (z3 counterexample, false
    "conserved" 0); ★ a pure transport shift (permutation, columns sum 1) conserves."""
    diffusion = circulant_update([1.0, -2.0, 1.0])         # discrete Laplacian — mass-preserving
    ok = verify_conservation(diffusion, "mass")
    bad = circulant_update([1.0, -1.0, 1.0])               # row sum 1 ≠ 0 ⇒ NOT conservative
    nb = verify_conservation(bad, "mass")
    # transport: u'[i] = u[i-1] (cyclic shift) — a permutation, columns sum to 1 ⇒ conserves
    n = 6
    shift = [[1.0 if j == (i - 1) % n else 0.0 for j in range(n)] for i in range(n)]
    tr = verify_conservation(shift, "mass")
    cases = {
        "diffusion_conserves_mass": ok.conserved,
        "nonconservative_rejected": not nb.conserved,           # ★ false "conserved" 0
        "transport_shift_conserves": tr.conserved,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
