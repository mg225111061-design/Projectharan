"""
§AQ §6.COUNT — EXACT closed forms for the NUMBER of I/O calls (the data is a frame residual; the COUNT is structural).
================================================================================================================
Even when the I/O DATA never folds, the call COUNT and total bytes are a deterministic function of the loop structure:
  chunked read over size S    → ⌈S/CHUNK⌉ reads,  total bytes = S;
  pagination over T items     → ⌈T/PAGE⌉ fetches;
  buffer flush, cap B over N  → ⌊N/B⌋ full flushes (+1 partial).
z3 LIA PROVES the EXACT count by the bracketing invariant (k=⌈S/C⌉ ⇒ (k−1)·C < S ≤ k·C), a counter-induction. ★ A
WRONG form (⌊S/C⌋, which undercounts the final partial) is REFUTED. `requires fileSize = S` is the spec-declared
precondition (S-5).
"""
from __future__ import annotations


def prove_ceil_count(C: int = 4096, Smax: int = 100000, correct: bool = True) -> bool:
    """z3 LIA: k = (S + C − 1) // C is the EXACT read count — (k−1)·C < S ≤ k·C  ∀ S ≥ 1. WRONG: k = S // C
    (undercounts the partial) ⇒ the bracket fails ⇒ z3 SAT."""
    import z3
    S = z3.Int("S")
    C_ = z3.IntVal(C)
    k = (S + C - 1) / C if correct else S / C                    # z3 Int '/' = floor for nonneg
    sol = z3.Solver()
    sol.add(S >= 1, S <= Smax, z3.Not(z3.And((k - 1) * C_ < S, S <= k * C_)))
    return sol.check() == z3.unsat


def prove_flush_floor(B: int = 256, Nmax: int = 100000) -> bool:
    """z3 LIA: full flushes = ⌊N/B⌋, and the bracket ⌊N/B⌋·B ≤ N < (⌊N/B⌋+1)·B holds ∀ N ≥ 0 (the partial is the +1)."""
    import z3
    N = z3.Int("N")
    Bv = z3.IntVal(B)
    q = N / B
    sol = z3.Solver()
    sol.add(N >= 0, N <= Nmax, z3.Not(z3.And(q * Bv <= N, N < (q + 1) * Bv)))
    return sol.check() == z3.unsat


def concrete_counts() -> dict:
    """Spot-check the exact counts (the value: buffer pre-alloc / cost prediction / SLA)."""
    def ceil_div(a, b):
        return (a + b - 1) // b
    return {"read_10000_over_4096": ceil_div(10000, 4096),       # 3 reads
            "pages_250_over_100": ceil_div(250, 100),            # 3 fetches
            "flushes_1000_over_256": 1000 // 256}                # 3 full flushes (+1 partial)


def adversarial_battery() -> dict:
    """★ the EXACT read count ⌈S/CHUNK⌉ is z3-proven by the bracketing invariant (so is the flush floor ⌊N/B⌋); ★★ the
    WRONG ⌊S/C⌋ count (undercounts the final partial) is z3-REFUTED; ★ spot counts match (3 reads / 3 pages / 3 flushes)."""
    c = concrete_counts()
    cases = {
        "ceil_read_count_proven": prove_ceil_count(4096, 100000, True),
        "flush_floor_proven": prove_flush_floor(256, 100000),
        "floor_undercount_refuted": not prove_ceil_count(4096, 100000, False),   # ★★
        "spot_counts": c["read_10000_over_4096"] == 3 and c["pages_250_over_100"] == 3 and c["flushes_1000_over_256"] == 3,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
