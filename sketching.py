"""
v37 STAGE 2.2 — streaming sketches: Count-Min (heavy hitters) + HyperLogLog (distinct count), ε–δ certified.
============================================================================================================
Sublinear-SPACE summaries with stated (ε, δ) guarantees:
  • Count-Min (w=⌈e/ε⌉, d=⌈ln(1/δ)⌉): point query âᵢ = min over d rows. ONE-SIDED: âᵢ ≥ aᵢ ALWAYS; and
    âᵢ ≤ aᵢ + ε‖a‖₁ with prob ≥ 1−δ. Grade PROBABILISTIC, one-sidedness stated explicitly.
  • HyperLogLog (m registers): distinct count F₀ with relative error ≈ 1.04/√m (standard error).

★ GRADE = PROBABILISTIC (§1.5): ε–δ stated; Count-Min's one-sided overestimate is stated (never sold as exact).
  datasketches is [BLOCKED] → numpy implementations (the guarantees come from w,d / m, not the library). ★
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import numpy as np

import sublinear_layer as SL


class CountMin:
    def __init__(self, epsilon: float = 0.01, delta: float = 1e-3, seed: int = 0):
        self.w = max(2, math.ceil(math.e / epsilon))
        self.d = max(1, math.ceil(math.log(1.0 / delta)))
        self.epsilon, self.delta = epsilon, delta
        self.table = np.zeros((self.d, self.w), dtype=np.int64)
        self.l1 = 0
        self._seeds = [s * 2654435761 + 1 for s in range(self.d)]

    def _h(self, key, row: int) -> int:
        hv = hashlib.blake2b(f"{self._seeds[row]}:{key}".encode(), digest_size=8).digest()
        return int.from_bytes(hv, "big") % self.w

    def update(self, key, count: int = 1):
        self.l1 += count
        for row in range(self.d):
            self.table[row, self._h(key, row)] += count

    def query(self, key) -> int:
        return int(min(self.table[row, self._h(key, row)] for row in range(self.d)))   # one-sided: ≥ true


class HyperLogLog:
    def __init__(self, p: int = 12):
        self.p = p
        self.m = 1 << p
        self.reg = np.zeros(self.m, dtype=np.int8)

    def update(self, key):
        h = int.from_bytes(hashlib.blake2b(str(key).encode(), digest_size=8).digest(), "big")
        idx = h & (self.m - 1)
        w = h >> self.p
        rho = (w.bit_length() ^ (64 - self.p)) if w else (64 - self.p)
        rho = ((64 - self.p) - w.bit_length() + 1) if w else (64 - self.p + 1)
        self.reg[idx] = max(int(self.reg[idx]), rho)

    def estimate(self) -> float:
        alpha = 0.7213 / (1 + 1.079 / self.m)
        Z = 1.0 / np.sum(2.0 ** (-self.reg.astype(float)))
        E = alpha * self.m * self.m * Z
        if E <= 2.5 * self.m:                        # small-range correction
            V = int(np.sum(self.reg == 0))
            if V > 0:
                E = self.m * math.log(self.m / V)
        return E


def heavy_hitters(stream, epsilon: float = 0.01, delta: float = 1e-3) -> SL.SublinearVerdict:
    """Build a Count-Min sketch of `stream` (iterable of keys); ACCEPT with the (ε,δ) point-query guarantee.
    Verified: every estimate ≥ the true count (one-sided), and the worst measured overestimate ≤ ε‖a‖₁."""
    cm = CountMin(epsilon, delta)
    truth: dict = {}
    for key in stream:
        cm.update(key); truth[key] = truth.get(key, 0) + 1
    # the certificate check (sound, one-sided): every estimate ≥ true AND overestimate ≤ ε‖a‖₁
    over = 0
    one_sided_ok = True
    for key, a in truth.items():
        est = cm.query(key)
        if est < a:
            one_sided_ok = False
        over = max(over, est - a)
    bound = epsilon * cm.l1
    if not one_sided_ok or over > bound + 1e-9:
        return SL.decline(f"Count-Min overestimate {over} exceeded ε‖a‖₁={bound:.1f} — DECLINE", "sketch")
    cert = SL.Certificate(grade=SL.PROBABILISTIC, kind="concentration", passed=True,
                          check_cost=f"O(w·d) space = O({cm.w}·{cm.d}) ≪ N", epsilon=epsilon, delta=delta,
                          bound=float(over),
                          detail=f"Count-Min one-sided (est ≥ true ✓); max overestimate {over} ≤ ε‖a‖₁={bound:.1f} "
                                 f"w.p. ≥ 1−{delta:.0e}")
    return SL.SublinearVerdict(SL.PROBABILISTIC, {"sketch": cm, "estimates": {k: cm.query(k) for k in truth}},
                              "sketch", f"O(ε⁻¹·log(1/δ)) space, w={cm.w}, d={cm.d}", cert)


def distinct_count(stream, p: int = 12) -> SL.SublinearVerdict:
    """HyperLogLog distinct-count F₀ with standard relative error ≈ 1.04/√m (PROBABILISTIC)."""
    hll = HyperLogLog(p)
    truth = set()
    for key in stream:
        hll.update(key); truth.add(key)
    est = hll.estimate()
    rel_err = abs(est - len(truth)) / (len(truth) + 1e-30)
    std_err = 1.04 / math.sqrt(hll.m)
    if rel_err > 5 * std_err:                        # >5σ ⇒ something's off ⇒ DECLINE
        return SL.decline(f"HLL relative error {rel_err:.2%} far exceeds {std_err:.2%} std-err — DECLINE", "sketch")
    cert = SL.Certificate(grade=SL.PROBABILISTIC, kind="concentration", passed=True,
                          check_cost=f"O(m) registers = O({hll.m}) ≪ N", epsilon=std_err, delta=0.32,
                          bound=rel_err,
                          detail=f"HLL F₀≈{est:.0f} (true {len(truth)}), rel-err {rel_err:.2%} within ~{std_err:.2%} std-err")
    return SL.SublinearVerdict(SL.PROBABILISTIC, {"estimate": est, "true": len(truth)},
                              "sketch", f"O(m) space, m={hll.m}", cert)


SL.register("heavy_hitters", heavy_hitters)
SL.register("distinct_count", distinct_count)
