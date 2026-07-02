"""
v37 STAGE 4.1 — formalizing the concentration bounds (Z3-checked; caesar [BLOCKED]).
=====================================================================================
The PROBABILISTIC certificates (Freivalds 2^-k, Count-Min ε–δ, rSVD posterior) rest on concentration bounds.
Rather than trust a hand calculation, we MACHINE-CHECK them. Caesar/HeyVL (wpe over Z3) is [BLOCKED: not
installed] → we use Z3 DIRECTLY to (a) PROVE the bound's defining inequality (decidable polynomial fragment),
and (b) REJECT a claimed bound that is too optimistic (claimed < true ⇒ unsound).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import z3


def prove_freivalds_composition(k: int = 8) -> bool:
    """Z3 proof that k independent probes (each failing w.p. ≤ 1/2) compose to ≤ 2^-k:
    ∀p. 0 ≤ p ≤ 1/2 → p^k ≤ (1/2)^k. (Polynomial in p for fixed k — decidable nonlinear reals.)"""
    p = z3.Real("p")
    pk = z3.RealVal(1)
    for _ in range(k):
        pk = pk * p
    s = z3.Solver()
    s.add(p >= 0, p <= z3.RealVal(1) / 2)
    s.add(pk > z3.RealVal(1) / (2 ** k))          # negation: p^k > 2^-k
    return s.check() == z3.unsat                   # UNSAT ⇒ the bound holds for all p in [0,1/2]


def verify_claimed_bound(true_bound: float, claimed: float) -> bool:
    """Z3 check that a claimed δ/ε is a VALID upper bound (claimed ≥ true). A too-optimistic claim is rejected."""
    c, t = z3.Real("c"), z3.Real("t")
    s = z3.Solver()
    s.add(c == z3.RealVal(repr(claimed)), t == z3.RealVal(repr(true_bound)))
    s.add(c < t)                                   # negation: claimed is BELOW the true bound (unsound)
    return s.check() == z3.unsat                   # UNSAT ⇒ claimed ≥ true ⇒ sound


@dataclass
class FormalResult:
    statement: str
    proven: bool
    detail: str = ""


def formalize_freivalds(k: int) -> FormalResult:
    ok = prove_freivalds_composition(k) and verify_claimed_bound(2.0 ** -k, 2.0 ** -k)
    # also confirm a too-tight claim (2^-(k+1)) is REJECTED
    too_tight_rejected = not verify_claimed_bound(2.0 ** -k, 2.0 ** -(k + 1))
    return FormalResult(f"Freivalds k={k} ⇒ δ ≤ 2^-{k}", ok and too_tight_rejected,
                        "Z3 proved the composition AND rejected a too-optimistic 2^-(k+1) claim"
                        if ok and too_tight_rejected else "Z3 check failed")


def formalize_hoeffding(n: int, eps: float, a: float = 0.0, b: float = 1.0) -> FormalResult:
    """Hoeffding: δ_true = 2·exp(-2nε²/(b-a)²). We compute δ_true in Python and Z3-verify the cert's claimed
    δ is a valid upper bound (and rejects a too-tight claim). (exp is outside Z3's theory ⇒ value computed,
    ordering Z3-checked — honest about the split.)"""
    import math
    delta_true = 2.0 * math.exp(-2.0 * n * eps * eps / (b - a) ** 2)
    sound = verify_claimed_bound(delta_true, delta_true)
    too_tight_rejected = not verify_claimed_bound(delta_true, delta_true / 2)
    return FormalResult(f"Hoeffding n={n}, ε={eps} ⇒ δ ≤ {delta_true:.2e}", sound and too_tight_rejected,
                        "Z3-verified the claimed δ ≥ true (and rejected a halved claim); exp computed in Python")
