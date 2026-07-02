"""
Pillar 3 · ROUND 1 #6 — THE FREE LEAP: route a recognized closed-form-bearing hotspot to Pillar-1's PROVEN
EXACT kernels (no new proof obligation — the kernel and its certificate already exist and are tested).
==========================================================================================================
Most Pillar-3 recognizers grade PROBABILISTIC: they carry control flow, so Z3 bounded validation cannot apply
(algorithms.py). But a C-finite LINEAR RECURRENCE  f(n) = Σ_i c_i·f(n−1−i)  (Fibonacci, Pell, Tribonacci, …)
is NOT such a case: its n-th term has a companion-matrix closed form that equals the recurrence BY THEOREM
and is computed in EXACT integers (cfinite.companion_nth — O(log n) matrix-power vs the loop's O(n)). Pillar-1
already certifies this EXACT (kernels_symbolic._cfin_run). THE LEAP, made free: when Pillar-3 recognizes a
hotspot as the recurrence (c, init), it
  1. GATES recognition — companion_nth(c,init,·) must reproduce the ACTUAL loop on a probe set (else the
     recurrence was mis-recognized ⇒ DECLINE; we never ship a closed form for a loop it does not match);
  2. ROUTES to the proven EXACT kernel (reuse — the certificate is companion ≡ naive by theorem, exact ints);
  3. MEASURES the whole-program win coherently (ratio ≤ ceiling by construction).
Result: a hotspot the generic recognizer would grade PROBABILISTIC is graded EXACT, O(n)→O(log n), at the cost
of a wire — it RAISES the EXACT share (a ceiling-breaker). A wrong/mis-recognized recurrence ⇒ DECLINE.
Honesty (§X): EXACT is the LOSSLESS closed-form evaluation of the recognized recurrence — exact integers, no
ε,δ — established by the companion-matrix theorem and verify_cfinite; the recognition gate ties it to the loop.
"""
from __future__ import annotations

from typing import Callable, List, Optional, Sequence, Tuple

import cfinite
import kernel_verdict as KV
import kernels_symbolic as KSY
from pillar3 import lifting as LF


def _probe_points(n: int, d: int) -> List[int]:
    """Points beyond the order-d initial window that over-determine the recurrence, plus a far point ≤ n.
    Matching the loop on these is the recognition evidence that the declared (c,init) IS this hotspot."""
    base = [d, d + 1, d + 2, d + 5, d + 9, 2 * d + 3]
    base.append(max(base[-1] + 1, min(n, 64)))
    return sorted({p for p in base if 0 <= p <= n})


def cfinite_lift(c: Sequence[int], init: Sequence[int], naive_loop: Callable[[int], int], *,
                 n: int, samples: int = 5, residual_iters: int = 0,
                 floor: float = 1.10) -> Tuple[KV.Verdict, Optional[object]]:
    """Recognize a hotspot as the C-finite recurrence (c, init) whose n-th term `naive_loop(k)` computes, route
    to the proven EXACT companion-matrix kernel, and measure the whole-program win. Returns (verdict, report).
    EXACT (lossless closed form, exact integers) iff the recognition gate passes, the kernel certifies, AND a
    win is measured; else DECLINE."""
    c = [int(x) for x in c]
    init = [int(x) for x in init]
    d = len(c)
    if d == 0 or len(init) != d or n < 0:
        return KV.decline("free-leap: need len(init)==len(c)>0 and n≥0", "cfinite"), None
    # 1 — recognition gate: the companion closed form must reproduce the ACTUAL loop on a probe set
    for k in _probe_points(n, d):
        try:
            if cfinite.companion_nth(c, init, k) != int(naive_loop(k)):
                return KV.decline(f"free-leap: recurrence {c} mis-recognized — companion≠loop at n={k} ⇒ DECLINE",
                                  "cfinite"), None
        except Exception as e:                              # a loop that raises on a probe is not this recurrence
            return KV.decline(f"free-leap: loop probe failed at n={k}: {e!r} ⇒ DECLINE", "cfinite"), None
    # 2 — route to the PROVEN EXACT kernel (free: companion ≡ naive by theorem, exact integers, already tested)
    verdict = KSY._cfin_run({"kind": "linear_recurrence", "c": c, "init": init, "n": n})
    if verdict.status != KV.EXACT:
        return verdict, None                                # the kernel's own safety net fired (e.g. DECLINE)
    # 3 — coherent whole-program measurement (ratio ≤ ceiling by construction)
    rep = LF.measure_lift(lambda cc, ii, nn: cfinite.naive_nth(cc, ii, nn),
                          lambda cc, ii, nn: cfinite.companion_nth(cc, ii, nn),
                          lambda: (c, init, n), residual_iters, n=n, samples=samples)
    verdict.report = rep
    if not rep.beats(floor):                                # EXACT-correct but not worth shipping here ⇒ DECLINE
        v = KV.decline(f"free-leap: EXACT closed form but no whole-program win "
                       f"(×{rep.whole_program_ratio:.2f} < {floor:.2f}) ⇒ DECLINE", "cfinite")
        v.report = rep
        return v, rep
    return verdict, rep


# ── known C-finite recurrences a Pillar-3 detector can route here (the recognized-structure catalog) ────
RECURRENCES = {
    "fibonacci":  ([1, 1], [0, 1]),
    "pell":       ([2, 1], [0, 1]),
    "tribonacci": ([1, 1, 1], [0, 1, 1]),
    "lucas":      ([1, 1], [2, 1]),
}
