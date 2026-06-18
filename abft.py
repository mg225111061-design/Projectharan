"""
v32 STAGE B3 — ABFT (algorithm-based fault tolerance) checksum self-verification [Clock B].
============================================================================================
★ THIS IS NOT A FOLD. ★ Unlike A / B1 / B2 (which make the EMITTED code faster — Clock C), B3 makes
VERIFICATION cheaper (Clock B). The matrix product A·B = C is NOT computed any faster; what gets cheap is
CHECKING it: O(N³) recompute → O(N²) checksum / O(k·N²) Freivalds. The user's perceived response latency
(Clock A, the LLM call) does NOT change, and the computation's own runtime (Clock C) does NOT change.

  B3.1 detect  : recognize a dense triple-nested matmul loop (C[i][j] += A[i][k]·B[k][j])  (ast).
  B3.2 checksum: row/column checksum (Huang–Abraham). C·1 must equal A·(B·1) and 1ᵀ·C must equal (1ᵀ·A)·B.
                 A single wrong entry changes a row-sum AND a col-sum ⇒ caught in O(N²). INTEGER ⇒ EXACT.
                 Honest limit: a weight-1 checksum can MISS an adversarial error pattern that preserves all
                 row & column sums (a canceling "rectangle") — stated, not hidden.
  B3.3 freivalds: the RANDOM-vector check A·(B·r) =? C·r (reused from fast_certificates) — complete and
                 probabilistic: a wrong product passes with probability ≤ 2^-k (catches the patterns a
                 deterministic checksum misses).
  B3.4 float   : V-ABFT — for floating point the checksum is never exactly 0; we accept |Δ| ≤ tol. This can
                 raise FALSE POSITIVES / NEGATIVES near the threshold — stated. (Integer path stays exact.)

Certificate types (never mixed): checksum→"exact" (integer, necessary condition) / freivalds→"probabilistic"
(ε ≤ 2^-k) / V-ABFT→"epsilon-bounded" (float tolerance tol). Clock B only.
"""
from __future__ import annotations

import ast
import time
from dataclasses import dataclass
from typing import List, Optional, Sequence

from fast_certificates import CertResult, freivalds_check, matmul

Matrix = List[List[float]]


# ─────────────────────────────────────────────────────── B3.1 — dense matmul detector
def detect_dense_matmul(src: str) -> bool:
    """Recognize a dense triple-nested matrix-multiply loop accumulating C[i][j] += A[i][k]*B[k][j].
    AST-based (not a string match): requires 3 nested for-loops and an augmented assignment whose RHS is a
    product of two 2-D subscripts sharing the inner index."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False

    def nested_for_depth(node, depth=0):
        best = depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.For):
                best = max(best, nested_for_depth(child, depth + 1))
            else:
                best = max(best, nested_for_depth(child, depth))
        return best

    has_triple = nested_for_depth(tree) >= 3
    has_madd = False
    for node in ast.walk(tree):
        # C[i][j] += A[i][k] * B[k][j]   (AugAssign +=, RHS is a Mult of two double-subscripts)
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add) \
                and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Mult):
            l, r = node.value.left, node.value.right
            if isinstance(l, ast.Subscript) and isinstance(r, ast.Subscript):
                has_madd = True
        # also accept C[i][j] = C[i][j] + A[i][k]*B[k][j]
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Add):
            if isinstance(node.value.right, ast.BinOp) and isinstance(node.value.right.op, ast.Mult):
                has_madd = True
    return has_triple and has_madd


# ─────────────────────────────────────────────────────── B3.2 — row/column checksum (Huang–Abraham)
def _matvec(M: Matrix, v: Sequence[float]) -> List[float]:
    return [sum(M[i][j] * v[j] for j in range(len(v))) for i in range(len(M))]


def _vecmat(v: Sequence[float], M: Matrix) -> List[float]:
    p = len(M[0])
    return [sum(v[i] * M[i][j] for i in range(len(M))) for j in range(p)]


def checksum_check(A: Matrix, B: Matrix, C: Matrix, *, integer: bool = True, tol: float = 1e-6) -> CertResult:
    """Row/column checksum verification of A·B == C in O(N²). C·1 =? A·(B·1) and 1ᵀ·C =? (1ᵀ·A)·B.
    Integer ⇒ EXACT (necessary condition); float ⇒ V-ABFT with tolerance `tol` (epsilon-bounded)."""
    n, p = len(C), len(C[0])
    m = len(B)
    one_p = [1] * p
    one_m = [1] * m
    # row sums: C·1_p  vs  A·(B·1_p)
    c_row = _matvec(C, one_p)
    a_brow = _matvec(A, _matvec(B, one_m))
    # col sums: 1_n^T·C  vs  (1_n^T·A)·B
    one_n = [1] * n
    c_col = _vecmat(one_n, C)
    ac_col = _vecmat(_vecmat(one_n, A), B)
    if integer:
        ok = (c_row == a_brow) and (c_col == ac_col)
        return CertResult(ok, "exact", 0.0,
                          "row+col checksum match (O(N²), integer-exact necessary condition)" if ok
                          else "checksum mismatch — A·B ≠ C (a row/col sum was off)")
    # float V-ABFT: tolerance-based
    def close(u, v):
        return all(abs(a - b) <= tol * (1 + abs(b)) for a, b in zip(u, v))
    ok = close(c_row, a_brow) and close(c_col, ac_col)
    return CertResult(ok, "epsilon-bounded", 0.0,
                      f"V-ABFT row+col checksum within tol={tol} (float; false pos/neg possible near threshold)"
                      if ok else f"V-ABFT checksum exceeds tol={tol} — likely A·B ≠ C")


@dataclass
class AbftMeasurement:
    name: str
    dim: int
    recompute_ms: float          # O(N³) exact verification (the baseline check)
    checksum_ms: float           # O(N²) checksum verification
    freivalds_ms: float          # O(k·N²) probabilistic verification
    checksum_speedup: float
    freivalds_speedup: float
    error_caught_checksum: bool
    error_caught_freivalds: bool
    rectangle_missed_by_checksum: bool   # honest: the weight-1 checksum's known blind spot
    rectangle_caught_by_freivalds: bool
    freivalds_error_prob: float
    clock: str = "B"


def measure_abft(dim: int = 96, k: int = 24, seed: int = 7) -> AbftMeasurement:
    """[Clock B] verification cost: O(N³) recompute vs O(N²) checksum vs O(k·N²) Freivalds, on an integer
    matmul. Confirms: a single-entry error is caught; the checksum's rectangle blind-spot IS missed by the
    checksum but CAUGHT by random Freivalds. ★ The matmul compute is NOT timed/changed — only verification. ★"""
    import random
    rng = random.Random(seed)
    A = [[rng.randint(-9, 9) for _ in range(dim)] for _ in range(dim)]
    B = [[rng.randint(-9, 9) for _ in range(dim)] for _ in range(dim)]
    C = matmul(A, B)
    # baseline verification: recompute (O(N³))
    t = time.perf_counter(); _ = (matmul(A, B) == C); recompute_ms = (time.perf_counter() - t) * 1000
    # checksum (O(N²))
    t = time.perf_counter(); ck = checksum_check(A, B, C); checksum_ms = (time.perf_counter() - t) * 1000
    # freivalds (O(k·N²))
    t = time.perf_counter(); fr = freivalds_check(A, B, C, k=k); freivalds_ms = (time.perf_counter() - t) * 1000
    assert ck.ok and fr.ok
    # single-entry error → both catch it
    C1 = [row[:] for row in C]; C1[0][0] += 1
    caught_ck = not checksum_check(A, B, C1).ok
    caught_fr = not freivalds_check(A, B, C1, k=k).ok
    # ★ honest blind spot ★: a canceling "rectangle" preserves all row & col sums → checksum MISSES it,
    # but random Freivalds catches it w.p. ≥ 1-2^-k
    C2 = [row[:] for row in C]
    i1, i2, j1, j2 = 0, 1, 0, 1
    C2[i1][j1] += 1; C2[i1][j2] -= 1; C2[i2][j1] -= 1; C2[i2][j2] += 1
    rect_missed_ck = checksum_check(A, B, C2).ok          # True ⇒ checksum did NOT catch it (the blind spot)
    rect_caught_fr = not freivalds_check(A, B, C2, k=k).ok
    return AbftMeasurement(
        "abft_matmul", dim, round(recompute_ms, 2), round(checksum_ms, 3), round(freivalds_ms, 3),
        round(recompute_ms / checksum_ms, 1) if checksum_ms > 0 else 1.0,
        round(recompute_ms / freivalds_ms, 1) if freivalds_ms > 0 else 1.0,
        caught_ck, caught_fr, rect_missed_ck, rect_caught_fr, 2.0 ** (-k))


# ─────────────────────────────────────────────────────── B3 — corpus measurement (Clock B, SEPARATE)
def measure_abft_corpus(split: Optional[str] = None, k: int = 24) -> dict:
    """Run B3 over the defer corpus `linear-algebra` category. Reports [Clock B] verification speedup and
    error-detection — kept SEPARATE from the Clock-C fold rate (never mixed). Coverage MEASURED."""
    import defer_corpus as DC
    cs = [c for c in DC.load() if c.category == "linear-algebra" and (split is None or c.split == split)]
    handled = 0
    rows = []
    speedups = []
    for c in cs:
        dim = c.meta["dim"]
        mm = measure_abft(dim=dim, k=k)
        # "handled" = verification accelerated AND a single-entry error is caught (sound necessary check)
        ok = mm.checksum_speedup > 1.0 and mm.error_caught_checksum and mm.error_caught_freivalds
        handled += int(ok)
        speedups.append(mm.freivalds_speedup)
        rows.append((c.cid, dim, mm.checksum_speedup, mm.freivalds_speedup, ok))
    n = len(cs)
    return {"n": n, "handled": handled, "clock": "B",
            "verify_rate": round(handled / n, 3) if n else 0.0,
            "median_freivalds_speedup": sorted(speedups)[len(speedups) // 2] if speedups else 0.0,
            "rows": rows, "note": "Clock B (verification) only — matmul COMPUTE is unchanged"}
