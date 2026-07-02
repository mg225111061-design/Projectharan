"""
§BH STAGE 0 — the universal cheap-verifier lane (proposer-verifier, the highest-leverage gem).
================================================================================================================
Compute an expensive result HOWEVER you like (BLAS, GPU, an untrusted/offloaded proposer, a galactic algorithm),
then VERIFY it cheaply. The common engine behind Freivalds (matmul), sum-check, and Schwartz–Zippel
(polynomial identity) is: a wrong answer is a non-zero polynomial, and a non-zero polynomial of degree d agrees
with zero at a random point with probability ≤ d/|S| — so a few random probes catch any error with overwhelming
probability. This is OUR proposer-verifier split, made universal.

★ Honesty (false-EXACT 0): these verifiers are inherently PROBABILISTIC and are graded so — never EXACT (the ADT
forbids EXACT+δ). A *general* deterministic-EXACT O(n²) matmul verifier does NOT exist (that is the whole reason a
cheap check is randomized); we make δ astronomically small (k=128 ⇒ δ=2⁻¹²⁸ ≈ 3e-39, or GVFA Gaussian ⇒ δ=0, a
measure-zero false-positive set) rather than dishonestly claim EXACT. zero-dep: numpy + stdlib (+ kernel_verdict).
"""
from __future__ import annotations

from typing import Callable, List, Optional, Tuple

import numpy as np

import freivalds as FV
import kernel_verdict as KV


def freivalds_verify(A: np.ndarray, B: np.ndarray, C: np.ndarray, k: int = 128) -> KV.Verdict:
    """Verify A·B = C in O(k·n²) ≪ O(n³). ★ k=128 ⇒ δ = 2⁻¹²⁸ ≈ 3e-39 (far below any tolerance — false-EXACT 0 in
    spirit, graded PROBABILISTIC never EXACT). A correct C ALWAYS passes (one-sided); a wrong C ⇒ DECLINE."""
    return FV.verify_matmul((A, B, C), k=k)


def freivalds_gvfa(A: np.ndarray, B: np.ndarray, C: np.ndarray) -> KV.Verdict:
    """GVFA (Gaussian-projection Freivalds): the false-positive set has MEASURE ZERO over the reals ⇒ δ=0. The
    strongest honest verdict short of recomputation — still PROBABILISTIC (a continuous-measure statement), not
    EXACT (the ADT reserves EXACT for a discrete certificate / decision procedure)."""
    return FV.verify_matmul((A, B, C), k=24, gaussian=True)


def _poly_eval_mod(coeffs: List[int], x: int, p: int) -> int:
    """Horner evaluation of Σ coeffs[i]·xⁱ at x, modulo prime p. O(deg)."""
    acc = 0
    for c in reversed(coeffs):
        acc = (acc * x + c) % p
    return acc


def schwartz_zippel_identity(p_coeffs: List[int], q_coeffs: List[int], prime: int = (1 << 61) - 1,
                             k: int = 128, seed: int = 0) -> KV.Verdict:
    """Decide the polynomial identity p ≡ q over ℤ by evaluating both at k random points mod a large prime
    (Schwartz–Zippel): if p≢q (a non-zero difference of degree ≤ d), a random point witnesses p(r)≠q(r) with
    probability ≥ 1 − d/prime, so after k independent agreeing probes δ ≤ (d/prime)ᵏ. Agree on all k ⇒
    PROBABILISTIC(δ); a disagreement ⇒ DECLINE with the witness point (a certificate of NON-identity)."""
    d = max(len(p_coeffs), len(q_coeffs)) - 1
    rng = np.random.default_rng(seed)
    for _ in range(k):
        r = int(rng.integers(1, prime))
        if _poly_eval_mod(p_coeffs, r, prime) != _poly_eval_mod(q_coeffs, r, prime):
            return KV.decline(f"Schwartz–Zippel: p(r)≠q(r) at r={r} (mod {prime}) — a witness that p≢q (refuted)",
                              "schwartz_zippel")
    per = d / prime
    delta = per ** k if per < 1 else 1.0
    cert = KV.Cert(KV.PROBABILISTIC, "schwartz_zippel", passed=True, check_cost=f"O(k·d)=O({k}·{d})",
                   delta=max(delta, 1e-300),
                   detail=f"{k} random points mod {prime}; degree d={d}; δ ≤ (d/p)^k ≈ {delta:.2e} — identity holds w.p. ≥ 1−δ")
    return KV.probabilistic("IDENTICAL", "schwartz_zippel", f"O(k·d), k={k}", cert)


def adversarial_battery() -> dict:
    """★ a correct matmul passes Freivalds(k=128) PROBABILISTIC with δ=2⁻¹²⁸; ★ a wrong matmul ⇒ DECLINE; ★ GVFA
    gives δ=0 (measure-zero); ★ an identical polynomial pair passes Schwartz–Zippel; ★ a non-identical pair ⇒
    DECLINE with a witness. ★ NONE is graded EXACT (Freivalds/SZ are inherently probabilistic — honest)."""
    rng = np.random.default_rng(1)
    A = rng.integers(-9, 9, (30, 30)).astype(float); B = rng.integers(-9, 9, (30, 30)).astype(float); C = A @ B
    Cw = C.copy(); Cw[0, 0] += 1
    fv = freivalds_verify(A, B, C, k=128)
    fvw = freivalds_verify(A, B, Cw, k=128)
    gv = freivalds_gvfa(A, B, C)
    # (x+1)² ≡ x²+2x+1  (coeffs low→high)
    sz_ok = schwartz_zippel_identity([1, 2, 1], [1, 2, 1])
    sz_bad = schwartz_zippel_identity([1, 2, 1], [1, 2, 2])           # x²+2x+1 vs 2x²+2x+1 — differ
    cases = {
        "freivalds_correct_PROB_tiny_delta": fv.status == "PROBABILISTIC" and fv.certificate.delta <= 2.0 ** -128,
        "freivalds_wrong_DECLINE": fvw.status == "DECLINE",
        "freivalds_never_EXACT": fv.status != "EXACT",               # ★ honest: inherently probabilistic
        "gvfa_measure_zero_delta": gv.status == "PROBABILISTIC" and gv.certificate.delta == 0.0,
        "sz_identical_PROB": sz_ok.status == "PROBABILISTIC",
        "sz_nonidentical_DECLINE": sz_bad.status == "DECLINE",
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
