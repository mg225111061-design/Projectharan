"""
defer_corpus/schema.py — the fixed measurement schema for the fold-coverage study.
==================================================================================
A DeferCase is ONE structured loop the fold engine might or might not close. The corpus is a FIXED
measurement set: we record the CURRENT engine's fold/defer verdict (the baseline M/N), then later
re-measure after adding detectors. ★ Coverage is always MEASURED on this set — never estimated. ★

Honesty rules baked into the schema:
  • `naive` is the GROUND TRUTH (a black box we may only evaluate). A detector must REDERIVE structure
    and a sound verifier must confirm it against `naive` — `truth` (the known closed form) is for display
    /audit ONLY and is NEVER fed to a detector (that would be cheating).
  • `expect` is the honest label of whether ANY sound technique should be able to fold this case
    ("foldable") or whether it must stay deferred/absent ("defer"). Honest negatives (Σ1/k, data-dep,
    non-Liouvillian Airy) carry expect="defer" — a technique that "folds" them is producing FALSE
    structure and must be caught.
  • `split` ∈ {"tune","measure"}: "tune" cases may inform detector design; "measure" cases are HELD OUT
    (never used to tune) so the final coverage number is not overfit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Tuple

# the six structural categories (directive §0.3)
CATEGORIES = (
    "multivariate-poly",   # B1 — Ben-Or–Tiwari sparse interpolation of a black-box polynomial
    "q-holonomic",         # B2 — q-Gosper / q-Zeilberger telescoping
    "ode",                 # A  — differential-Galois / Kovacic Liouvillian decision
    "linear-algebra",      # B3 — ABFT / Freivalds (Clock B verification, NOT a compute speedup)
    "combinatorial",       # mixed — some close via existing Gosper, some need q, some defer
    "blackbox",            # genuinely opaque / data-dependent → honest Ω(N) defer (negative controls)
)

SPLITS = ("tune", "measure")


@dataclass
class DeferCase:
    cid: str                                  # unique id, e.g. "b1_poly_2var_sparse"
    category: str
    desc: str
    split: str                                # "tune" | "measure" (measure = held out)
    expect: str                               # "foldable" | "defer" (honest label; defer = negative control)
    naive: Optional[Callable] = None          # GROUND TRUTH black box (evaluate only)
    arg_spec: Tuple = ()                      # ((name, lo, hi), ...) integer arg ranges for verification sampling
    haran: Optional[str] = None               # HARAN fold source, if fold-expressible (drives baseline engine)
    truth: Optional[str] = None               # known closed form — DISPLAY/AUDIT ONLY, never given to a detector
    meta: dict = field(default_factory=dict)  # category-specific payload (ODE coeffs, q value, matrix dims, …)

    def __post_init__(self):
        assert self.category in CATEGORIES, f"bad category {self.category}"
        assert self.split in SPLITS, f"bad split {self.split}"
        assert self.expect in ("foldable", "defer"), f"bad expect {self.expect}"
