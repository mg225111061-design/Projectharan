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

DETERMINISTIC COST MODEL (so the spine test is robust under full-suite load): each stage's *runtime* is a
controlled busy-loop sized to an exact target fraction of the program; the fast impl shrinks that loop by
`_STAGE_SPEEDUP` (the modelled fix). The stage ALSO performs its real characteristic operation on a small
input and writes the real output, so differential testing is meaningful (a wrong fix is caught) and the S4
Z3 proof is a real equivalence proof. Fractions, marginals and cross-mode monotonicity are therefore
deterministic — they do not depend on incidental timing — while ratio ≤ ceiling still holds by construction
(the engine's floor pipeline passes active stages through, charging them nothing).
"""
from __future__ import annotations

import math
from typing import Dict, List

import numpy as np

from pillar3 import equiv as EQ
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


# ── the deterministic cost model ───────────────────────────────────────────────────────────────────────
_BASE = 600_000                                  # total busy-loop iterations across the program (tunes wall time)
_STAGE_SPEEDUP = 20                              # each fast stage shrinks its busy-loop ~20× (ratios near ceiling
                                                 # ⇒ large, noise-proof diminishing-returns marginals)
_FRAC = {"S1": 0.22, "S2": 0.14, "S3": 0.13, "S4": 0.45, "S5": 0.02}   # exact target fractions
_RESIDUAL_FRAC = 0.04                            # the un-optimisable remainder ⇒ finite Amdahl ceiling


def _busy(work: float) -> int:
    s = 0
    for _ in range(int(work)):
        s += 1
    return s


# small real-op inputs (kept tiny so the busy-loop dominates timing; the real op is for differential/Z3 only)
_DEG, _NPTS, _NDUP, _NID, _NPARTS, _NARR = 14, 16, 60, 120, 80, 200
_DB = {i: i * i for i in range(_NID + 16)}
_FETCH_OVERHEAD = 8


def make_input() -> Dict:
    return {
        "dups": list(range(_NDUP)) * 2,
        "ids": list(range(_NID)),
        "parts": list(range(_NPARTS)),
        "coeffs": [((i * 7) % 11) - 5 for i in range(_DEG)],
        "xs": [((i * 3) % 7) - 3 for i in range(_NPTS)],
        "arr": [float(i % 100) - 50.0 for i in range(_NARR)],
    }


def residual(data: Dict) -> Dict:
    out = dict(data); out["_r"] = _busy(_RESIDUAL_FRAC * _BASE); return out


# ── S1 list-as-set (real dedup + modelled cost) ───────────────────────────────────────────────────────
def s1_slow(data: Dict) -> Dict:
    _busy(_FRAC["S1"] * _BASE)
    out_list: List = []
    for x in data["dups"]:
        if x not in out_list:                    # real O(n²) membership-in-list (small input, for differential)
            out_list.append(x)
    out = dict(data); out["dedup"] = out_list; return out


def s1_fast(data: Dict) -> Dict:
    _busy(_FRAC["S1"] * _BASE / _STAGE_SPEEDUP)
    out = dict(data); out["dedup"] = list(dict.fromkeys(data["dups"])); return out


# ── S2 N+1 ──────────────────────────────────────────────────────────────────────────────────────────
def _get_one(i: int) -> int:
    s = 0
    for _ in range(_FETCH_OVERHEAD):
        s += _DB[i]
    return _DB[i]


def s2_slow(data: Dict) -> Dict:
    _busy(_FRAC["S2"] * _BASE)
    out = dict(data); out["mapped"] = [_get_one(i) for i in data["ids"]]; return out


def s2_fast(data: Dict) -> Dict:
    _busy(_FRAC["S2"] * _BASE / _STAGE_SPEEDUP)
    out = dict(data); out["mapped"] = [_DB[i] for i in data["ids"]]; return out


# ── S3 accidental quadratic ───────────────────────────────────────────────────────────────────────────
def s3_slow(data: Dict) -> Dict:
    _busy(_FRAC["S3"] * _BASE)
    acc: List = []
    for p in data["parts"]:
        acc = acc + [p]                          # real O(n²) self-concat (small input)
    out = dict(data); out["built"] = acc; return out


def s3_fast(data: Dict) -> Dict:
    _busy(_FRAC["S3"] * _BASE / _STAGE_SPEEDUP)
    out = dict(data); out["built"] = list(data["parts"]); return out


# ── S4 algorithm recognition (poly eval → Horner; real, Z3-provable) ──────────────────────────────────
def s4_slow(data: Dict) -> Dict:
    _busy(_FRAC["S4"] * _BASE)
    co = data["coeffs"]; out = dict(data); out["poly"] = [naive_poly(co, x) for x in data["xs"]]; return out


def s4_fast(data: Dict) -> Dict:
    _busy(_FRAC["S4"] * _BASE / _STAGE_SPEEDUP)
    co = data["coeffs"]; out = dict(data); out["poly"] = [horner(co, x) for x in data["xs"]]; return out


# ── S5 SIMD-offloadable numeric kernel ────────────────────────────────────────────────────────────────
def s5_slow(data: Dict) -> Dict:
    _busy(_FRAC["S5"] * _BASE)
    out = dict(data); out["trig"] = [math.sin(x) * math.cos(x) + math.sqrt(abs(x)) for x in data["arr"]]; return out


def s5_fast(data: Dict) -> Dict:
    _busy(_FRAC["S5"] * _BASE / _STAGE_SPEEDUP)
    a = np.asarray(data["arr"], dtype=float)
    out = dict(data); out["trig"] = (np.sin(a) * np.cos(a) + np.sqrt(np.abs(a))).tolist(); return out


def data_eq(a, b) -> bool:
    """Float-tolerant dict equality (the SIMD stage reorders FP); int/list compared elementwise, floats ±1e-9."""
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(data_eq(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(data_eq(x, y) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return abs(a - b) < 1e-9
    return a == b


def build_candidates() -> List[Candidate]:
    """The five stacked wastes as Candidates. Fractions are the DETERMINISTIC target fractions (the busy-loop
    cost model realises them), so the mode-distinctness behaviour is stable under load. Grades: S1/S3/S5 →
    PROBABILISTIC, S2 → EXACT (by construction), S4 → EXACT (Z3)."""
    return [
        Candidate("S1_list_as_set", "list_as_set", "list_as_set", s1_slow, s1_fast,
                  _FRAC["S1"], eq=data_eq),
        Candidate("S2_n_plus_1", "n_plus_1", "n_plus_1", s2_slow, s2_fast,
                  _FRAC["S2"], exact_justification="coalesced_identical_lookups", eq=data_eq),
        Candidate("S3_accidental_quadratic", "accidental_quadratic", "accidental_quadratic", s3_slow, s3_fast,
                  _FRAC["S3"], eq=data_eq),
        Candidate("S4_algorithm_recognition", "algo_replace", "algorithm_recognition", s4_slow, s4_fast,
                  _FRAC["S4"], prove_fn=prove_poly_equiv, region_size=5, eq=data_eq),
        Candidate("S5_simd_offload", "simd_offload", "gpu_simd_offload", s5_slow, s5_fast,
                  _FRAC["S5"], eq=data_eq),
    ]


def sweep_fn(size: int) -> None:
    """A super-linear workload for the extend complexity sweep (the dedup hotspot at varying n)."""
    out: List = []
    for x in list(range(size)):
        if x not in out:
            out.append(x)
