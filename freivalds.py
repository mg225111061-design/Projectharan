"""
v37 STAGE 0 — Freivalds matrix-product verification: the first sound sublinear certificate (the TEMPLATE).
==========================================================================================================
Verify a CLAIMED product A·B = C without the O(N³) recompute: pick random r, check A(Br) = Cr in O(N²); k
independent probes ⇒ a WRONG product passes with probability ≤ 2^-k, a CORRECT product ALWAYS passes
(one-sided — false-reject = 0, guaranteed). Grade = PROBABILISTIC(δ = 2^-k); never dressed up as EXACT.

This is the template the whole layer follows: a CHEAP (O(kN²) ≪ O(N³)) per-instance witness with a STATED
bound, sound-or-decline. GVFA (Gaussian r) variant gives a measure-zero false-positive alternative.
"""
from __future__ import annotations

import time
from typing import Optional, Tuple

import numpy as np

import sublinear_layer as SL


def _freivalds_pass(A: np.ndarray, B: np.ndarray, C: np.ndarray, k: int, rng: np.random.Generator,
                    gaussian: bool) -> bool:
    """k independent probes of A(Br) == Cr, BATCHED as one O(k·N²) BLAS computation (R is N×k): a CORRECT
    product matches on every column; a wrong one differs on a column w.p. ≥ 1-2^-k. True iff all agree."""
    n = B.shape[1]
    R = rng.standard_normal((n, k)) if gaussian else rng.integers(0, 2, size=(n, k)).astype(np.float64)
    return bool(np.allclose(A @ (B @ R), C @ R, rtol=0, atol=1e-6))


def verify_matmul(data: Tuple[np.ndarray, np.ndarray, np.ndarray], k: int = 24,
                  gaussian: bool = False, seed: int = 0) -> SL.SublinearVerdict:
    """Sublinear verification of A·B = C. PROBABILISTIC(δ=2^-k), one-sided. The 'result' is the boolean
    verdict 'C is the correct product' — a PASS is the certificate that C may be USED without recompute."""
    A, B, C = (np.asarray(x, dtype=np.float64) for x in data)
    rng = np.random.default_rng(seed)
    n = B.shape[1]
    ok = _freivalds_pass(A, B, C, k, rng, gaussian)
    if not ok:
        return SL.decline("A·B ≠ C — a probe separated them (definitely wrong); recompute O(N³)", "freivalds")
    delta = (0.0 if gaussian else 2.0 ** (-k))     # GVFA: measure-zero false positive
    cert = SL.Certificate(
        grade=SL.PROBABILISTIC, kind="freivalds_kfold", passed=True,
        check_cost=f"O(k·N²)=O({k}·{n}²) ≪ O(N³)=O({n}³)", epsilon=None, delta=delta,
        bound=delta, detail=f"{k} {'Gaussian (GVFA)' if gaussian else 'binary'} probes; one-sided "
                            f"(correct ALWAYS passes); wrong passes w.p. ≤ {delta:.2e}")
    return SL.SublinearVerdict(SL.PROBABILISTIC, True, "freivalds",
                              f"O(k·N²), k={k}, N={n}", cert)


SL.register("matmul_check", verify_matmul)


# ── measurement: O(kN²) verification vs O(N³) recompute ──
def measure_speedup(N: int = 300, k: int = 24, seed: int = 1) -> dict:
    rng = np.random.default_rng(seed)
    A = rng.integers(-9, 9, size=(N, N)).astype(np.float64)
    B = rng.integers(-9, 9, size=(N, N)).astype(np.float64)
    C = A @ B
    t = time.perf_counter(); _ = A @ B; recompute_ms = (time.perf_counter() - t) * 1000
    t = time.perf_counter(); v = verify_matmul((A, B, C), k=k); verify_ms = (time.perf_counter() - t) * 1000
    return {"N": N, "k": k, "recompute_ms": round(recompute_ms, 3), "verify_ms": round(verify_ms, 3),
            "speedup": round(recompute_ms / verify_ms, 1) if verify_ms > 0 else 0.0,
            "accepted": v.accepted, "delta": v.certificate.delta}


def adversarial_false_accept(trials: int = 200_000, N: int = 6, k: int = 20, seed: int = 7) -> dict:
    """One-sidedness empirically: (1) CORRECT products are NEVER rejected (false-reject = 0, GUARANTEED);
    (2) WRONG products (single-entry corruption) are caught — measured false-ACCEPT over `trials`, which must
    be consistent with the ≤ trials·2^-k bound (observed ~0). HONEST: 0 observed is probabilistic, not a proof."""
    rng = np.random.default_rng(seed)
    false_reject = 0
    false_accept = 0
    for _ in range(trials):
        A = rng.integers(-5, 5, size=(N, N)).astype(np.float64)
        B = rng.integers(-5, 5, size=(N, N)).astype(np.float64)
        C = A @ B
        # (1) correct → must accept (one-sided guarantee)
        if not _freivalds_pass(A, B, C, k, rng, gaussian=False):
            false_reject += 1
        # (2) wrong (corrupt one entry) → should be caught
        Cw = C.copy()
        i, j = rng.integers(0, N), rng.integers(0, N)
        Cw[i, j] += 1.0
        if _freivalds_pass(A, B, Cw, k, rng, gaussian=False):
            false_accept += 1
    return {"trials": trials, "N": N, "k": k, "false_reject": false_reject, "false_accept": false_accept,
            "false_accept_bound": trials * 2.0 ** (-k),
            "note": "false_reject=0 is GUARANTEED (one-sided); false_accept~0 is consistent with ≤trials·2^-k"}
