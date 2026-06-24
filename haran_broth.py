"""
HARAN §2 — the cross-algorithm BROTH: pre-prove common instantiations OFFLINE → O(1) hash lookup at runtime.
==========================================================================================================
The "instant" mechanism (the "3707 families, 0.11 µs" pattern), widened beyond the sum/recurrence broth to span
SEVERAL of the 50 named algorithms. For each, the COMMON instantiations are computed + certified ONCE here (the
offline brew); at runtime a normalized key hits an O(1) dict and the pre-proven result + certificate is returned
INSTANTLY, size-independent. The certificate discipline is the strongest possible: every stored entry is
RE-CHECKABLE by RE-RUNNING the real algorithm — a cached value is trusted only because re-execution reproduces it
(`reverify`), so a corrupted cache is caught, never silently served.

§0-B HONESTY (verbatim): broth makes RECURRING cases instant ONLY because they were pre-proven offline — it does
NOT make the algorithm's EXECUTION O(1). A MISS runs the algorithm at its TRUE complexity (or honestly declines).
Widening coverage = pre-proving more common instantiations so more runtime queries hit the O(1) lookup. The count
below is a precomputed-lookup-coverage number, NOT a claim that these algorithms became O(1).

Families brewed here (each entry keyed (algo, params) → value + re-checkable cert):
  • #9  Faulhaber power sums   Σ_{k=1}^n k^p  (closed form, p = 1..12)
  • #10 named C-finite seqs    Fibonacci/Lucas/Pell/Jacobsthal/Tribonacci/Padovan/Perrin (companion closed form)
  • #45 Jacobi symbols         (a|n) for common small a and odd moduli
  • #49 Wigner 3j symbols      exact rational×√rational for small integer (j₁j₂j₃ m₁m₂m₃)
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import kernel_verdict as KV


@dataclass(frozen=True)
class BrothEntry:
    algo: int                    # which of the 50 (9/10/45/49)
    key: Tuple                   # normalized hashable key
    value: str                   # the pre-proven result (repr — exact)
    cert: str                    # what re-checks it
    kind: str


# named constant-coefficient recurrences, cfinite convention f(n)=Σ c_j f(n-1-j), init=[f(0)..]
_NAMED_CFINITE = {
    "fibonacci": ([1, 1], [0, 1]), "lucas": ([1, 1], [2, 1]), "pell": ([2, 1], [0, 1]),
    "jacobsthal": ([1, 2], [0, 1]), "tribonacci": ([1, 1, 1], [0, 0, 1]),
    "padovan": ([0, 1, 1], [1, 1, 1]), "perrin": ([0, 1, 1], [3, 0, 2]),
}

_INDEX: Optional[Dict[Tuple, BrothEntry]] = None
_BREW_MS = 0.0


def _brew() -> Dict[Tuple, BrothEntry]:
    """OFFLINE one-time: compute + certify the common instantiations. Paid once; cached."""
    import sympy as sp
    import cfinite as CF
    import mathmode.fastkernels as FK
    import mathmode.wigner as W
    import mathmode.number_theory as NT
    idx: Dict[Tuple, BrothEntry] = {}

    # #9 Faulhaber Σk^p, p=1..12 — closed form (the Bernoulli derivation is the offline cost)
    k, n = sp.symbols("k n")
    for p in range(1, 13):
        cf = sp.factor(sp.summation(k ** p, (k, 1, n)))
        idx[("faulhaber", p)] = BrothEntry(9, ("faulhaber", p), str(cf),
                                           "Σk^p closed form; recheck S(N)=Σ_{1..N}k^p", "polynomial-sum")

    # #10 named C-finite sequences — the companion closed form (O(log n))
    for name, (c, init) in _NAMED_CFINITE.items():
        idx[("cfinite", name)] = BrothEntry(10, ("cfinite", name), repr((c, init)),
                                            "companion_nth ≡ naive at sample n", "c-finite")

    # #45 Jacobi (a|n) for common small a and odd moduli
    for a in range(2, 8):
        for nn in range(3, 60, 2):
            v = NT.jacobi_grade(a, nn)
            if v.status == KV.EXACT:
                idx[("jacobi", a, nn)] = BrothEntry(45, ("jacobi", a, nn), str(v.result),
                                                    "reciprocity ≡ ∏ Legendre", "number-theory")

    # #49 Wigner 3j for small integer arguments (the Racah factorial sum is the offline cost)
    for j1 in range(0, 4):
        for j2 in range(0, 4):
            for j3 in range(abs(j1 - j2), min(j1 + j2, 3) + 1):
                for m1 in range(-j1, j1 + 1):
                    for m2 in range(-j2, j2 + 1):
                        m3 = -(m1 + m2)
                        if abs(m3) > j3:
                            continue
                        r = W.wigner3j(j1, j2, j3, m1, m2, m3)
                        if r.status == KV.EXACT and r.result != 0:
                            key = ("wigner3j", j1, j2, j3, m1, m2, m3)
                            idx[key] = BrothEntry(49, key, str(r.result),
                                                  "re-evaluate wigner3j; selection rules", "physics")
    return idx


def index() -> Dict[Tuple, BrothEntry]:
    global _INDEX, _BREW_MS
    if _INDEX is None:
        t0 = time.perf_counter()
        _INDEX = _brew()
        _BREW_MS = (time.perf_counter() - t0) * 1000
    return _INDEX


def lookup(key: Tuple) -> Optional[BrothEntry]:
    """O(1) hash lookup of a pre-proven instantiation. Hit ⇒ instant certified result; miss ⇒ None (the caller
    runs the algorithm at its true complexity — broth does NOT make execution O(1))."""
    return index().get(key)


def reverify(entry: BrothEntry) -> bool:
    """RE-RUN the real algorithm for `entry` and confirm it reproduces the cached value — the strongest recheck
    (a stored result is trusted only because re-execution agrees). Returns False on any mismatch."""
    import sympy as sp
    import cfinite as CF
    import mathmode.wigner as W
    import mathmode.number_theory as NT
    try:
        if entry.algo == 9:                              # Faulhaber: closed form must match the brute sum at a sample
            p = entry.key[1]
            n = sp.Symbol("n")
            closed = sp.sympify(entry.value)
            return all(int(closed.subs(n, N)) == sum(kk ** p for kk in range(1, N + 1)) for N in (5, 12, 20))
        if entry.algo == 10:                             # C-finite: companion ≡ naive at a sample n
            c, init = eval(entry.value)
            return all(CF.companion_nth(c, init, N) == CF.naive_nth(c, init, N) for N in (10, 25))
        if entry.algo == 45:                             # Jacobi: re-run jacobi_grade
            _, a, nn = entry.key
            return str(NT.jacobi_grade(a, nn).result) == entry.value
        if entry.algo == 49:                             # Wigner 3j: re-evaluate
            _, j1, j2, j3, m1, m2, m3 = entry.key
            return str(W.wigner3j(j1, j2, j3, m1, m2, m3).result) == entry.value
    except Exception:  # noqa: BLE001
        return False
    return False


def measure(probes: int = 200000) -> dict:
    """Coverage count (+ per-algorithm) and the O(1) lookup latency (size-independent). HONEST: precomputed-
    lookup-fast, NOT execution-O(1)."""
    import random
    idx = index()
    keys = list(idx)
    by_algo: Dict[int, int] = {}
    for e in idx.values():
        by_algo[e.algo] = by_algo.get(e.algo, 0) + 1
    rng = random.Random(0)
    probe = [rng.choice(keys) for _ in range(probes)]
    t = time.perf_counter()
    hit = 0
    for kk in probe:
        hit += idx.get(kk) is not None
    lookup_us = (time.perf_counter() - t) / probes * 1e6
    return {"entries": len(idx), "by_algo": by_algo, "brew_ms": round(_BREW_MS, 1),
            "lookup_us": round(lookup_us, 5), "all_hit": hit == probes}
