"""
v37 STAGE 0 — the sublinear-certificate layer: contract + dispatcher (invoked ONLY after fold DECLINEs).
========================================================================================================
When the fold engine cannot close a NUMERIC problem to O(1) (it returns DECLINED), we ask ONE more question:
"is there hidden structure with a CHEAPLY-VERIFIABLE per-instance witness?" If yes, we drop O(N) to sublinear
WITH a machine-recheckable certificate; if not, we DECLINE honestly. We never beat Ω(N) — we descend from the
SURFACE N to the genuinely-compressible information content (k / r / #exponents). Wrong answers = 0.

★ GRADE SEPARATION (§1.5) — never mixed:
  EXACT          deterministic / measure-zero / machine-ε (e.g. Prony residual ≈ ε, CS dual certificate).
  PROBABILISTIC  a stated (ε, δ) concentration bound (e.g. Freivalds δ=2^-k, Count-Min ε–δ).
  DECLINE        no structure / witness too expensive / residual exceeded / a statistical-computational gap.
★ INVARIANT (§4): status != DECLINE  ⟹  certificate.check ACTUALLY passed (else it is a fake pass, §1.1). ★
★ per-instance witnesses ONLY (§1.7): never verify a uniform property (RIP is NP-hard) — only the witness the
  solver emits (a dual certificate / residual / spectral gap). If the CHECK costs ~O(N), the speedup is a
  mirage ⇒ DECLINE. ★
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

EXACT = "EXACT"
PROBABILISTIC = "PROBABILISTIC"
DECLINE = "DECLINE"


@dataclass
class Certificate:
    grade: str                  # EXACT | PROBABILISTIC
    kind: str                   # dual_cert | residual | spectral_gap | concentration | freivalds_kfold | ...
    passed: bool                # did the machine recheck actually pass?
    check_cost: str = ""        # the recheck cost (must be ≪ O(N) for the speedup to be real)
    epsilon: Optional[float] = None    # PROBABILISTIC only
    delta: Optional[float] = None      # PROBABILISTIC only
    bound: Optional[float] = None       # measured error / residual bound
    detail: str = ""


@dataclass
class SublinearVerdict:
    status: str                 # EXACT | PROBABILISTIC | DECLINE
    result: Any = None          # the computed answer; None on DECLINE → caller falls back to O(N)/original
    kind: str = ""              # sparse_fft | compressed_sensing | prony | rsvd | sketch | planted | freivalds
    complexity: str = ""        # e.g. "O(k log N), k=3, N=4096"
    certificate: Optional[Certificate] = None
    reason: str = ""            # DECLINE reason

    def __post_init__(self):
        # ★ enforce the soundness invariant: a non-DECLINE MUST carry a passed certificate ★
        if self.status != DECLINE:
            assert self.certificate is not None and self.certificate.passed, \
                "INVARIANT VIOLATION: non-DECLINE result without a passed certificate (would be a fake pass)"
            assert self.certificate.grade == self.status, "grade/status mismatch (label leak)"
            if self.status == PROBABILISTIC:
                assert self.certificate.delta is not None, "PROBABILISTIC must state δ (never hide it as EXACT)"

    @property
    def accepted(self) -> bool:
        return self.status != DECLINE


def decline(reason: str, kind: str = "") -> SublinearVerdict:
    return SublinearVerdict(DECLINE, None, kind, reason=reason)


# detector registry: each entry is (problem_tag, detector_fn(data, **kw) -> SublinearVerdict)
_DETECTORS: Dict[str, List[Callable]] = {}


def register(problem: str, fn: Callable) -> None:
    _DETECTORS.setdefault(problem, []).append(fn)


def dispatch(data: Any, problem: str, **kw) -> SublinearVerdict:
    """Invoked AFTER fold DECLINEs a numeric problem. Try the registered detectors for `problem` in order;
    return the FIRST that produces a passed certificate; else honest DECLINE. (Detectors self-gate: they
    only return EXACT/PROBABILISTIC when their witness actually checks — the __post_init__ invariant enforces
    that no fake pass escapes.)"""
    for fn in _DETECTORS.get(problem, []):
        try:
            v = fn(data, **kw)
        except Exception as e:  # noqa: BLE001 — a detector crashing must not yield a wrong answer
            v = decline(f"detector {getattr(fn, '__name__', '?')} raised {type(e).__name__}: {e}")
        if v.accepted:
            return v
    return decline(f"no sublinear structure found for problem '{problem}' (honest DECLINE → O(N) fallback)", problem)


def fold_then_sublinear(fold_declined: bool, data: Any, problem: str, **kw) -> SublinearVerdict:
    """The wiring (§S0.1): this layer is consulted ONLY when the fold engine already DECLINED (fold_declined
    True). If fold could close it, we never get here (no double work). Numeric/signal/matrix domain ONLY."""
    if not fold_declined:
        return decline("fold did not decline — sublinear layer not consulted (no double work)")
    return dispatch(data, problem, **kw)


def registered_problems() -> List[str]:
    return sorted(_DETECTORS.keys())
