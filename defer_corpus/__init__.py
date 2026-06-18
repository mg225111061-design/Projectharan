"""
defer_corpus — a FIXED, categorized set of structured loops for MEASURING fold coverage.
=========================================================================================
STAGE 0 of the fold-engine extension. The whole study's discipline is: coverage is the fold/defer
verdict MEASURED on this fixed set — baseline (current engine) vs after (with new detectors) — never
estimated. `baseline()` records the current engine's verdict per case so the lift is a real number.

Clock separation (§4): fold coverage (Clock C) is measured over the categories whose technique emits
faster CODE (multivariate-poly / q-holonomic / ode / combinatorial). The linear-algebra category is
measured SEPARATELY as Clock B (verification acceleration) — it is never folded into the Clock-C rate.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List

import fold_kernels as FK

from .cases import CASES
from .schema import CATEGORIES, SPLITS, DeferCase

_HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(_HERE, "manifest.json")

# which categories are measured under which clock (never mixed)
CLOCK_C_CATS = ("multivariate-poly", "q-holonomic", "ode", "combinatorial")
CLOCK_B_CATS = ("linear-algebra",)
# the "blackbox" category holds negative controls (must stay defer/absent) — counted in Clock-C denominators
NEGATIVE_CONTROL_CAT = "blackbox"


def load() -> List[DeferCase]:
    """The fixed corpus (in declaration order)."""
    return list(CASES)


def by_category() -> Dict[str, List[DeferCase]]:
    out: Dict[str, List[DeferCase]] = {c: [] for c in CATEGORIES}
    for c in CASES:
        out[c.category].append(c)
    return out


def split(which: str) -> List[DeferCase]:
    assert which in SPLITS
    return [c for c in CASES if c.split == which]


def current_engine_folds(case: DeferCase) -> bool:
    """The BASELINE: does the CURRENT fold engine (fold_kernels) close this case?
    Only HARAN-expressible folds can even be presented to it; ODE / matmul / black-box-poly /
    q-telescoping loops are outside its surface → it cannot fold them (honest baseline DEFER)."""
    if not case.haran:
        return False
    return FK.fold_certificate(case.haran).status == "FOLDED"


@dataclass
class Baseline:
    n: int
    folded: int                       # current engine FOLDED (Clock-C categories)
    deferred: int
    fold_rate: float
    per_category: Dict[str, dict]     # cat -> {n, folded, rate}
    clock_b_n: int                    # linear-algebra cases (measured separately, Clock B)

    def summary(self) -> str:
        return (f"baseline fold-rate (Clock C) = {self.folded}/{self.n} = {self.fold_rate:.0%}; "
                f"+{self.clock_b_n} linear-algebra cases measured separately as Clock B verification")


def baseline() -> Baseline:
    """Measure the CURRENT engine over the corpus. Clock-C categories only for the fold-rate;
    linear-algebra (Clock B) counted separately so clocks are never mixed."""
    clock_c = [c for c in CASES if c.category in CLOCK_C_CATS or c.category == NEGATIVE_CONTROL_CAT]
    per: Dict[str, dict] = {}
    for cat in CATEGORIES:
        cc = [c for c in CASES if c.category == cat]
        if cat in CLOCK_B_CATS or not cc:
            continue
        f = sum(1 for c in cc if current_engine_folds(c))
        per[cat] = {"n": len(cc), "folded": f, "rate": round(f / len(cc), 3)}
    folded = sum(1 for c in clock_c if current_engine_folds(c))
    n = len(clock_c)
    return Baseline(n=n, folded=folded, deferred=n - folded,
                    fold_rate=round(folded / n, 3) if n else 0.0, per_category=per,
                    clock_b_n=sum(1 for c in CASES if c.category in CLOCK_B_CATS))


def write_manifest() -> dict:
    """Serialize the corpus + the measured baseline to manifest.json (auditable; no callables)."""
    b = baseline()
    cats = by_category()
    doc = {
        "n_total": len(CASES),
        "categories": {k: len(v) for k, v in cats.items()},
        "splits": {s: len(split(s)) for s in SPLITS},
        "clock_C_categories": list(CLOCK_C_CATS),
        "clock_B_categories": list(CLOCK_B_CATS),
        "baseline": {
            "clock_C_fold_rate": b.fold_rate, "folded": b.folded, "n": b.n,
            "per_category": b.per_category, "clock_B_n": b.clock_b_n,
        },
        "cases": [
            {"cid": c.cid, "category": c.category, "split": c.split, "expect": c.expect,
             "desc": c.desc, "haran": c.haran, "truth": c.truth,
             "baseline_folds": current_engine_folds(c)}
            for c in CASES
        ],
    }
    with open(MANIFEST, "w") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
    return doc
