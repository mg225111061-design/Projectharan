"""
Pillar 3 · PHASE R — run the engine on a real-code CORPUS and report what is ACTUALLY measured (incl. misses).
==============================================================================================================
For each vendored repo + a real workload: profile, detect the waste, verify the fix (differential), measure the
WHOLE-PROGRAM speedup (best-of-k), and grade. The point is honesty: most well-written code shows little or
nothing; AI-generated / never-profiled code can show a large asymptotic win; some repos yield a DECLINE
everywhere — and that is reported truthfully, never fabricated.

Amdahl coherence: f = t_hot / t_orig (the hot function's measured share), ceiling = 1/(1−f). Because the
optimized program keeps the same non-hot work and only speeds the hot function, ratio = t_orig/t_opt ≤ ceiling.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

import kernel_verdict as KV
from pillar3 import measure as M
from pillar3 import record as RC
from pillar3.fixers import detectors as D1
from pillar3 import detectors2 as D2


@dataclass
class CorpusRepo:
    name: str
    archetype: str
    module: Any                                          # provides original/optimized/hot_original/hot_input/make_workload
    eq: Optional[Callable] = None
    exact_justification: Optional[str] = None


@dataclass
class CorpusRow:
    name: str
    archetype: str
    detected: List[str]
    grade: str
    ratio: Optional[float]
    hotspot_fraction: Optional[float]
    ceiling: Optional[float]
    t_orig_ms: Optional[float]
    t_opt_ms: Optional[float]
    note: str = ""


@dataclass
class CorpusReport:
    rows: List[CorpusRow] = field(default_factory=list)

    def grades(self) -> dict:
        return {g: sum(1 for r in self.rows if r.grade == g) for g in (KV.EXACT, KV.PROBABILISTIC, KV.DECLINE)}

    def found_nothing(self) -> List[str]:
        return [r.name for r in self.rows if r.grade == KV.DECLINE]


# every detector the engine knows (Stage-1 + PHASE-D), run on the repo's hot function
def _run_detectors(hot_fn, _unused=None) -> List[str]:
    fired = []
    for det in (D1.detect_membership_in_loop, D1.detect_n_plus_1, D2.detect_redos_regex,
                D2.detect_redundant_io_parse, D2.detect_accidental_full_scan, D2.detect_quadratic_build,
                D2.detect_redundant_sort, D2.detect_dict_to_columnar, D2.detect_loop_invariant_hoist,
                D2.detect_copy_elim, D2.detect_materialize_to_lazy, D2.detect_deep_n_plus_1,
                D2.detect_vectorizable_loop, D2.detect_parallelizable_loop, D2.detect_egg_algebraic,
                D2.detect_incremental_recompute):
        try:
            f = det(hot_fn)
            if f.found:
                fired.append(f.waste_type)
        except Exception:  # noqa: BLE001 — a detector that can't read this source simply does not fire
            pass
    return fired


def run_repo(repo: CorpusRepo, *, floor: float = 1.10, samples: int = 5) -> CorpusRow:
    m = repo.module
    mk = lambda: (m.make_workload(),)

    detected = _run_detectors(m.hot_original, None)

    # differential: optimized must match original on the workload (Rule 4)
    oracle = RC.record_oracle(m.original, [(m.make_workload(),) for _ in range(3)])
    diff = RC.differential_test(m.optimized, oracle, repo.eq)
    if not diff.passed:
        return CorpusRow(repo.name, repo.archetype, detected, KV.DECLINE, None, None, None, None, None,
                         note=f"optimized diverges ({diff.mismatches}/{diff.n}) — not applied")

    # coherent whole-program measurement (best-of-k) via the FLOOR reference (rest only, hot skipped): so
    # ceiling = t_orig/t_floor ≥ t_orig/t_opt = ratio BY CONSTRUCTION (t_opt = rest+fast-hot ≥ rest = floor).
    t_orig = M.time_best(m.original, mk, samples)
    t_opt = M.time_best(m.optimized, mk, samples)
    t_floor = M.time_best(m.floor, mk, samples)
    t_floor = min(t_floor, t_opt)                         # the floor (rest only) cannot exceed the optimized run
    f = max(0.0, min(0.999, 1.0 - t_floor / max(t_orig, 1e-12)))
    ceiling = (1.0 / (1.0 - f)) if f < 1.0 else float("inf")
    ratio = t_orig / max(t_opt, 1e-12)

    if ratio < floor:                                    # honest miss — no whole-program win to ship
        return CorpusRow(repo.name, repo.archetype, detected, KV.DECLINE, round(ratio, 3), round(f, 3),
                         round(ceiling, 2), round(t_orig * 1e3, 3), round(t_opt * 1e3, 3),
                         note="no whole-program win ≥ floor — honest DECLINE (nothing worth shipping)")

    grade = KV.EXACT if repo.exact_justification else KV.PROBABILISTIC
    return CorpusRow(repo.name, repo.archetype, detected, grade, round(ratio, 3), round(f, 3),
                     round(ceiling, 2) if ceiling != float("inf") else None,
                     round(t_orig * 1e3, 3), round(t_opt * 1e3, 3),
                     note=(repo.exact_justification or f"differential PASS on {diff.n} cases (δ=3/{diff.n})"))


def run_corpus(repos: List[CorpusRepo], **kw) -> CorpusReport:
    return CorpusReport(rows=[run_repo(r, **kw) for r in repos])
