"""
MECHANISM 20 (scope) — Quasicrystal / aperiodic order (in-repo).
==================================================================
Deterministic aperiodic long-range order = the shadow of a higher-dimensional periodic lattice (cut-and-project).
A 1D model set (Fibonacci-chain-style) has exactly TWO tile lengths whose ORDER is a Sturmian / mechanical word —
the projection of a lattice slice through an irrational-slope window. Such sets have PURE-POINT diffraction (sharp
Bragg peaks) by Poisson summation for the superspace lattice.

★ proposer→EXACT-disposer: the certificate is the cut-and-project signature — (1) the gaps take exactly two values
  (the two projected tiles), and (2) the gap-type sequence is BALANCED (the exact combinatorial characterization of
  a Sturmian word = a 1D cut-and-project set ⇒ pure-point diffraction). A periodic set (one gap) is not a
  quasicrystal; a random / diffuse set (many gaps, or an unbalanced order) FAILS the balanced test ⇒ DECLINE. Note:
  a quasicrystal is DETERMINISTIC aperiodic order, NOT structure+noise — it does not fit M7.
"""
from __future__ import annotations

from fractions import Fraction
from typing import List

import kernel_verdict as KV


def _balanced(word: List[int]) -> bool:
    """A binary word is BALANCED iff for every factor length ℓ, the number of 1s in any two length-ℓ factors differs
    by ≤ 1. Balanced + aperiodic = Sturmian = a 1D cut-and-project set. (O(n²) sliding windows — exact.)"""
    n = len(word)
    pref = [0] * (n + 1)
    for i, c in enumerate(word):
        pref[i + 1] = pref[i] + c
    for L in range(1, n):
        counts = {pref[i + L] - pref[i] for i in range(0, n - L + 1)}
        if max(counts) - min(counts) > 1:
            return False
    return True


def _aperiodic(word: List[int]) -> bool:
    """The word is not purely periodic with a small period (a genuine quasicrystal is aperiodic)."""
    n = len(word)
    for p in range(1, n // 2 + 1):
        if all(word[i] == word[i - p] for i in range(p, n)):
            return False
    return True


def aperiodic_grade(spec) -> KV.Verdict:
    """M20 — recognize a 1D cut-and-project (quasicrystal) point set: exactly two tile lengths whose order is a
    balanced (Sturmian) word ⇒ EXACT (pure-point diffraction by the cut-and-project theorem). Periodic (one tile)
    or random/diffuse (many tiles, or unbalanced order) ⇒ DECLINE."""
    pts = spec.get("positions") if isinstance(spec, dict) else spec
    if not (isinstance(pts, (list, tuple)) and len(pts) >= 12
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in pts)):
        return KV.decline("aperiodic: need ≥12 ordered 1D positions", "mech_aperiodic")
    p = sorted(Fraction(v).limit_denominator(10**9) for v in pts)
    gaps = [p[i + 1] - p[i] for i in range(len(p) - 1)]
    distinct = sorted(set(gaps))
    if len(distinct) == 1:
        return KV.decline("aperiodic: a single tile length ⇒ PERIODIC, not a quasicrystal ⇒ DECLINE", "mech_aperiodic")
    if len(distinct) != 2:
        return KV.decline(f"aperiodic: {len(distinct)} distinct gap lengths (a cut-and-project 1D set has exactly 2) "
                          "⇒ DECLINE (random / diffuse)", "mech_aperiodic")
    L, S = distinct[1], distinct[0]
    word = [1 if g == L else 0 for g in gaps]                  # the gap-type (tile-order) binary word
    if not _aperiodic(word):
        return KV.decline("aperiodic: the two-tile order is periodic ⇒ not a quasicrystal ⇒ DECLINE", "mech_aperiodic")
    if not _balanced(word):
        return KV.decline("aperiodic: the tile-order word is NOT balanced (not Sturmian / not a cut-and-project set) "
                          "⇒ DECLINE (no pure-point diffraction certificate)", "mech_aperiodic")
    ratio = L / S
    cert = KV.Cert(KV.EXACT, "aperiodic_cut_project", passed=True,
                   check_cost="exact: two tile lengths + balanced (Sturmian) tile-order word ⇒ cut-and-project set",
                   detail=f"cut-and-project 1D quasicrystal: tiles L={L}, S={S} (ratio {float(ratio):.4f}); tile-order "
                          "is balanced+aperiodic (Sturmian) ⇒ PURE-POINT diffraction (Poisson summation, superspace lattice)")
    return KV.exact({"tiles": [str(L), str(S)], "ratio": float(ratio), "n_points": len(p), "sturmian": True,
                     "pure_point_diffraction": True}, "mech_aperiodic", "aperiodic order (cut-and-project)", cert)
