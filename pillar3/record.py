"""
Pillar 3 · Stage 0 — I/O recorder + differential tester (the gold oracle).
===========================================================================
The known-correct-but-slow ORIGINAL is the ideal test oracle (Rule 4). We record its (args, output) pairs and
replay them against every candidate fix; a single mismatch ⇒ the candidate diverges ⇒ DECLINE. Caches local;
phone-home 0.
"""
from __future__ import annotations

import pickle
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Tuple


@dataclass
class DiffResult:
    passed: bool
    n: int                          # number of recorded cases checked
    mismatches: int
    first_mismatch: Optional[Tuple[Any, Any, Any]] = None   # (args, expected, got)

    @property
    def rule_of_three_delta(self) -> float:
        """If all n cases pass with zero mismatches, the rule-of-three upper bound on the failure rate is 3/n.
        This is the δ a PROBABILISTIC grade carries when there is no proof — never EXACT from sampling alone."""
        return 3.0 / max(self.n, 1)


def record_oracle(fn: Callable, cases: List[tuple]) -> List[Tuple[tuple, Any]]:
    """Run the trusted original on each input tuple; capture (args, output). This is the gold oracle."""
    return [(args, fn(*args)) for args in cases]


def save_oracle(oracle: List[Tuple[tuple, Any]], path: str) -> None:
    with open(path, "wb") as f:
        pickle.dump(oracle, f)


def load_oracle(path: str) -> List[Tuple[tuple, Any]]:
    with open(path, "rb") as f:
        return pickle.load(f)


def differential_test(candidate: Callable, oracle: List[Tuple[tuple, Any]], eq: Callable[[Any, Any], bool] = None) -> DiffResult:
    """Run `candidate` on every recorded input and compare to the recorded (original) output. eq defaults to
    structural equality; pass a tolerance-eq for floats. Zero mismatches ⇒ passed (grade gated by the caller)."""
    eq = eq or (lambda a, b: a == b)
    mism = 0
    first = None
    for args, expected in oracle:
        try:
            got = candidate(*args)
        except Exception as e:  # noqa: BLE001 — a crash is a divergence
            got = f"<exception {type(e).__name__}: {e}>"
        if not eq(got, expected):
            mism += 1
            if first is None:
                first = (args, expected, got)
    return DiffResult(passed=(mism == 0), n=len(oracle), mismatches=mism, first_mismatch=first)
