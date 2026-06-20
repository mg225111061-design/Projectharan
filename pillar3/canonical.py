"""
Pillar 3 · PHASE M — the canonical multi-waste program (the mode-distinctness fixture).
========================================================================================
A single program with several stacked, independent wastes, modelled as a pipeline of stages over a shared
`data` dict. Each stage has a slow and a fast implementation; a fix activates the fast one. Running the SAME
program through fast / normal / extend produces observably, measurably different behaviour — that is the proof
that the three modes are real contracts, not presets.

Stages (waste → detector → tier → max provable grade):
  • S1 list-as-set (dedup via membership-in-list)      → list_as_set          (fast)    PROBABILISTIC
  • S2 N+1 (per-item fetch with overhead)              → n_plus_1             (fast)    EXACT (by construction)
  • S3 accidental-O(n²) (list built by concatenation)  → accidental_quadratic (normal)  PROBABILISTIC
  • S4 algorithmic (naive O(n²) poly eval → Horner)    → algorithm_recognition(extend)  EXACT (Z3-proven)
  • S5 SIMD-offloadable numeric (sin·cos+√ → numpy)    → gpu_simd_offload     (extend)  PROBABILISTIC

Stage fractions are MEASURED at build time (not declared), so the Amdahl ceiling is real and every whole-
program ratio is ≤ its ceiling by construction (the fixed pipeline still pays the residual).
"""
from __future__ import annotations

import math
from typing import Dict, List

import numpy as np

from pillar3 import equiv as EQ
from pillar3 import measure as M
from pillar3.engine import Candidate


# ── bare functions for the Z3 proof (S4) — run on symbolic inputs, independent of the pipeline wrappers ──
def naive_poly(coeffs, x):                       # O(n²): recompute xⁱ by repeated multiply
    s = 0
    for i in range(len(coeffs)):
        term = coeffs[i]
        for _ in range(i):
            term = term * x
        s = s + term
    return s


def horner(coeffs, x):                           # O(n)
    r = 0
    for c in reversed(coeffs):
        r = r * x + c
    return r


def prove_poly_equiv():
    return EQ.prove_equiv(naive_poly, horner, EQ.sym_poly_inputs, (3, 5))


# ── the shared input ────────────────────────────────────────────────────────────────────────────────
_DEG = 78
_NPTS = 95
_NDUP = 820
_NID = 950
_NPARTS = 1400
_NARR = 11000
_DB = {i: i * i for i in range(_NID + 16)}
_FETCH_OVERHEAD = 38
_RESIDUAL_WORK = 22000


def make_input() -> Dict:
    return {
        "dups": list(range(_NDUP)) * 2,
        "ids": list(range(_NID)),
        "parts": list(range(_NPARTS)),
        "coeffs": [((i * 7) % 11) - 5 for i in range(_DEG)],
        "xs": [((i * 3) % 7) - 3 for i in range(_NPTS)],
        "arr": [float(i % 100) - 50.0 for i in range(_NARR)],
    }


# ── residual: the un-optimisable part Amdahl says a hotspot fix cannot speed up ────────────────────────
def residual(data: Dict) -> Dict:
    s = 0
    for _ in range(_RESIDUAL_WORK):
        s += 1
    out = dict(data)
    out["_r"] = s
    return out


# ── S1 list-as-set ────────────────────────────────────────────────────────────────────────────────────
def s1_slow(data: Dict) -> Dict:
    out_list: List = []
    for x in data["dups"]:
        if x not in out_list:                    # O(n²) membership-in-list
            out_list.append(x)
    out = dict(data); out["dedup"] = out_list; return out


def s1_fast(data: Dict) -> Dict:
    out = dict(data); out["dedup"] = list(dict.fromkeys(data["dups"])); return out


# ── S2 N+1 ──────────────────────────────────────────────────────────────────────────────────────────
def _get_one(i: int) -> int:
    s = 0
    for _ in range(_FETCH_OVERHEAD):             # simulate per-call fixed overhead
        s += _DB[i]
    return _DB[i]


def s2_slow(data: Dict) -> Dict:
    out = dict(data); out["mapped"] = [_get_one(i) for i in data["ids"]]; return out


def s2_fast(data: Dict) -> Dict:
    out = dict(data); out["mapped"] = [_DB[i] for i in data["ids"]]; return out


# ── S3 accidental quadratic ───────────────────────────────────────────────────────────────────────────
def s3_slow(data: Dict) -> Dict:
    acc: List = []
    for p in data["parts"]:
        acc = acc + [p]                          # O(n) copy each step → O(n²)
    out = dict(data); out["built"] = acc; return out


def s3_fast(data: Dict) -> Dict:
    out = dict(data); out["built"] = list(data["parts"]); return out


# ── S4 algorithm recognition (poly eval → Horner) ─────────────────────────────────────────────────────
def s4_slow(data: Dict) -> Dict:
    co = data["coeffs"]; out = dict(data); out["poly"] = [naive_poly(co, x) for x in data["xs"]]; return out


def s4_fast(data: Dict) -> Dict:
    co = data["coeffs"]; out = dict(data); out["poly"] = [horner(co, x) for x in data["xs"]]; return out


# ── S5 SIMD-offloadable numeric kernel ────────────────────────────────────────────────────────────────
def s5_slow(data: Dict) -> Dict:
    out = dict(data); out["trig"] = [math.sin(x) * math.cos(x) + math.sqrt(abs(x)) for x in data["arr"]]; return out


def s5_fast(data: Dict) -> Dict:
    a = np.asarray(data["arr"], dtype=float)
    out = dict(data); out["trig"] = (np.sin(a) * np.cos(a) + np.sqrt(np.abs(a))).tolist(); return out


def data_eq(a, b) -> bool:
    """Float-tolerant dict equality (the SIMD stage reorders FP); int/list compared elementwise, floats ±1e-9."""
    if isinstance(a, dict) and isinstance(b, dict):
        if a.keys() != b.keys():
            return False
        return all(data_eq(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(data_eq(x, y) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return abs(a - b) < 1e-9
    return a == b


def _measure_fractions() -> Dict[str, float]:
    """Measure each stage's real share of baseline runtime → real Amdahl inputs (ratio ≤ ceiling by const.)."""
    data = make_input()
    mk = lambda: (data,)
    t_res = M.time_median(residual, mk, samples=3)
    times = {
        "S1_list_as_set": M.time_median(s1_slow, mk, samples=3),
        "S2_n_plus_1": M.time_median(s2_slow, mk, samples=3),
        "S3_accidental_quadratic": M.time_median(s3_slow, mk, samples=3),
        "S4_algorithm_recognition": M.time_median(s4_slow, mk, samples=3),
        "S5_simd_offload": M.time_median(s5_slow, mk, samples=3),
    }
    total = t_res + sum(times.values())
    return {k: v / total for k, v in times.items()}


def build_candidates() -> List[Candidate]:
    """The five stacked wastes as Candidates, with MEASURED fractions and per-stage grade ceilings."""
    fr = _measure_fractions()
    return [
        Candidate("S1_list_as_set", "list_as_set", "list_as_set", s1_slow, s1_fast,
                  fr["S1_list_as_set"], eq=data_eq),                          # PROBABILISTIC (differential)
        Candidate("S2_n_plus_1", "n_plus_1", "n_plus_1", s2_slow, s2_fast,
                  fr["S2_n_plus_1"], exact_justification="coalesced_identical_lookups", eq=data_eq),  # EXACT
        Candidate("S3_accidental_quadratic", "accidental_quadratic", "accidental_quadratic", s3_slow, s3_fast,
                  fr["S3_accidental_quadratic"], eq=data_eq),                 # PROBABILISTIC (normal-tier)
        Candidate("S4_algorithm_recognition", "algo_replace", "algorithm_recognition", s4_slow, s4_fast,
                  fr["S4_algorithm_recognition"], prove_fn=prove_poly_equiv, region_size=5, eq=data_eq),  # EXACT (Z3)
        Candidate("S5_simd_offload", "simd_offload", "gpu_simd_offload", s5_slow, s5_fast,
                  fr["S5_simd_offload"], eq=data_eq),                         # PROBABILISTIC (extend-tier)
    ]


def sweep_fn(size: int) -> None:
    """A super-linear workload for the extend complexity sweep (the dedup hotspot at varying n)."""
    out: List = []
    for x in list(range(size)):
        if x not in out:
            out.append(x)
