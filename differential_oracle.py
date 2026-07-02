"""
PHASE 1.S1 — differential-execution oracle: the UNTRUSTED translation is checked against REAL CPython.
=====================================================================================================
False-Safety is the deadliest failure: a translation (Python AST → formula/Z3/HARAN) that Z3 then "PROVES"
about — but the translation was WRONG, so the proof is about the wrong program. This gate makes EVERY
translation UNTRUSTED: we run the ORIGINAL Python (ground truth via CPython) AND the translation's predicted
output on a battery of inputs; ONE mismatch ⇒ TRANSLATION_UNSOUND ⇒ DECLINE (never a PASS).

Inputs (no `hypothesis` here → self-built, the directive's allowed fallback): random + boundary + FORCED
singulars (empty, 0, negative, overflow-scale, None, very large). The classic mistranslations this catches:
  • `/` integer-vs-true division        • `and`/`or` short-circuit vs bitwise/multiply
  • negative `%` sign (Python floor-mod vs C trunc-mod)

★ HONEST bound: a PASS is COVERAGE-BOUNDED corroboration, NOT a proof — stated in the certificate. Any
disagreement ⇒ DECLINE. We never upgrade differential agreement to "verified". ★
"""
from __future__ import annotations

import itertools
import math
import random
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence, Tuple

# forced singular values per type — the inputs that break naive translations
_INT_SINGULARS = [0, 1, -1, 2, -2, 7, -7, 10**9, -(10**9), 2**31, -(2**31), 2**63 - 1, -(2**63)]
_FLOAT_SINGULARS = [0.0, -0.0, 1.0, -1.0, 0.5, -0.5, 1e-9, 1e9, float("inf"), -float("inf")]
_BOOL_SINGULARS = [True, False]
_SEQ_SINGULARS = [[], [0], [1, 2, 3], [-1, 0, 1]]


@dataclass
class DiffResult:
    verdict: str                       # SOUND | TRANSLATION_UNSOUND
    n_tested: int
    mismatches: List[Tuple] = field(default_factory=list)   # (inputs, py_out, model_out)
    coverage_note: str = ""

    @property
    def sound(self) -> bool:
        return self.verdict == "SOUND"

    def __str__(self):
        if self.sound:
            return f"SOUND [coverage-bounded, n={self.n_tested}] — {self.coverage_note}"
        return f"TRANSLATION_UNSOUND — {len(self.mismatches)} mismatch(es), e.g. {self.mismatches[0]}"


def _gen_for(kind: str, rng: random.Random) -> List:
    if kind == "int":
        return list(_INT_SINGULARS) + [rng.randint(-1000, 1000) for _ in range(12)]
    if kind == "nat":
        return [0, 1, 2, 3, 5, 8, 13, 100, 1000] + [rng.randint(0, 500) for _ in range(8)]
    if kind == "float":
        return list(_FLOAT_SINGULARS) + [rng.uniform(-1e3, 1e3) for _ in range(10)]
    if kind == "bool":
        return list(_BOOL_SINGULARS)
    if kind == "seq":
        return list(_SEQ_SINGULARS) + [[rng.randint(-9, 9) for _ in range(rng.randint(0, 6))] for _ in range(6)]
    if kind == "nonzero_int":
        return [x for x in _INT_SINGULARS if x != 0] + [rng.choice([-1, 1]) * rng.randint(1, 1000) for _ in range(10)]
    return [None]


def _product_sample(arg_kinds: Sequence[str], rng: random.Random, cap: int = 4000) -> List[Tuple]:
    pools = [_gen_for(k, rng) for k in arg_kinds]
    full = 1
    for p in pools:
        full *= max(1, len(p))
    if full <= cap:
        return list(itertools.product(*pools))
    # sample the cross-product, but ALWAYS include the all-singular corner combinations
    corners = list(itertools.product(*[p[:6] for p in pools]))[:cap // 2]
    sampled = [tuple(rng.choice(p) for p in pools) for _ in range(cap - len(corners))]
    return corners + sampled


def differential_check(py_fn: Callable, model_fn: Callable, arg_kinds: Sequence[str],
                       seed: int = 12345, cap: int = 4000) -> DiffResult:
    """Run py_fn (ground truth) and model_fn (the UNTRUSTED translation) over a battery of inputs. Any
    disagreement ⇒ TRANSLATION_UNSOUND ⇒ DECLINE. Exceptions must match too (both raise, same type)."""
    rng = random.Random(seed)
    inputs = _product_sample(arg_kinds, rng, cap=cap)
    mism = []
    tested = 0
    for args in inputs:
        tested += 1
        try:
            py_out, py_exc = py_fn(*args), None
        except Exception as e:  # noqa: BLE001
            py_out, py_exc = None, type(e).__name__
        try:
            m_out, m_exc = model_fn(*args), None
        except Exception as e:  # noqa: BLE001
            m_out, m_exc = None, type(e).__name__
        if py_exc is not None or m_exc is not None:
            if py_exc != m_exc:                       # one raised and the other didn't / different error
                mism.append((args, f"raise:{py_exc}", f"raise:{m_exc}"))
            continue
        if not _agree(py_out, m_out):
            mism.append((args, py_out, m_out))
            if len(mism) >= 8:
                break
    verdict = "SOUND" if not mism else "TRANSLATION_UNSOUND"
    return DiffResult(verdict, tested, mism,
                      coverage_note=f"{tested} inputs incl. singulars over kinds {list(arg_kinds)}; "
                                    "PASS is coverage-bounded corroboration, NOT a proof")


def _agree(a, b) -> bool:
    if isinstance(a, float) or isinstance(b, float):
        try:
            if math.isnan(a) and math.isnan(b):
                return True
            return abs(float(a) - float(b)) <= 1e-9 * (1 + abs(float(b)))
        except (TypeError, ValueError):
            return a == b
    return a == b
