"""
v40 PHASE 1B — the GRADE ADT, enforced (Constitution §0.2: grades never mix).
=============================================================================
Generalizes v37's SublinearVerdict.__post_init__ pattern to EVERY collapse kernel. A kernel output is exactly
one of EXACT / PROBABILISTIC(ε,δ) / DECLINE, and the grade is ENFORCED at construction (a runtime exception,
not a label):
  • non-DECLINE  ⇒ a certificate that is passed=True (no rubber stamp);
  • grade == certificate.grade (can't claim EXACT while carrying a PROBABILISTIC cert);
  • PROBABILISTIC ⇒ δ is stated (a number), never None;
  • EXACT ⇒ exact algorithm + exact certificate, OR a proven error interval (machine-ε ball). A SAMPLING count
    can NEVER be EXACT — §0.2: it is bounded by rule-of-three δ=3/n, and if the caller needs a smaller δ than
    the available n affords, the honest answer is DECLINE.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

EXACT = "EXACT"
PROBABILISTIC = "PROBABILISTIC"
DECLINE = "DECLINE"
_GRADES = {EXACT, PROBABILISTIC, DECLINE}


@dataclass
class Cert:
    """A machine-rechecked certificate. `passed` must be the result of the actual fast verifier, not a wish."""
    grade: str
    kind: str                       # freivalds | schwartz_zippel | sylvester | exact_replay | interval | …
    passed: bool
    check_cost: str = ""            # the verifier's cost, e.g. "O(r·n)" — must be ≪ the kernel cost
    epsilon: Optional[float] = None
    delta: Optional[float] = None
    bound: Optional[float] = None
    detail: str = ""


@dataclass
class Verdict:
    status: str
    result: Any
    kernel: str
    complexity: str                 # the COMPUTE cost (NOT output-size); §0.1 keeps these separate
    certificate: Optional[Cert] = None
    reason: str = ""
    crossover_n: Optional[int] = None   # measured n at/after which the kernel beats the baseline (NO_UNMEASURED)
    amdahl_p: Optional[float] = None    # measured runtime-dominance fraction (small p ⇒ collapse barely helps)

    def __post_init__(self):
        assert self.status in _GRADES, f"bad grade {self.status!r}"
        if self.status != DECLINE:
            assert self.certificate is not None and self.certificate.passed, \
                f"{self.status} requires a passed certificate (no rubber stamp)"
            assert self.certificate.grade == self.status, \
                f"grade/cert mismatch: {self.status} vs {self.certificate.grade}"
            if self.status == PROBABILISTIC:
                assert self.certificate.delta is not None, "PROBABILISTIC must state δ (a number)"
            if self.status == EXACT:
                # EXACT forbids a probabilistic δ masquerading as exact (an exact interval uses epsilon/bound)
                assert self.certificate.delta is None, \
                    "EXACT cannot carry a probabilistic δ — use PROBABILISTIC, or an exact interval (epsilon)"


# ── constructors ────────────────────────────────────────────────────────────────────────────────────
def decline(reason: str, kernel: str = "-") -> Verdict:
    return Verdict(DECLINE, None, kernel, "-", None, reason)


def exact(result, kernel: str, complexity: str, cert: Cert, **kw) -> Verdict:
    return Verdict(EXACT, result, kernel, complexity, cert, **kw)


def probabilistic(result, kernel: str, complexity: str, cert: Cert, **kw) -> Verdict:
    return Verdict(PROBABILISTIC, result, kernel, complexity, cert, **kw)


# ── §0.2 rule-of-three: a sampling count yields δ=3/n, never EXACT ────────────────────────────────────
def rule_of_three_delta(n_samples: int) -> float:
    """Upper bound on the failure probability after n independent passes that all succeeded (zero failures):
    P(true rate ≥ 3/n) ≤ ~0.05 — the rule of three. This is the SMALLEST honest δ a pure sampling count earns."""
    return 3.0 / max(int(n_samples), 1)


def sampling_verdict(result, kernel: str, complexity: str, n_samples: int, required_delta: float,
                     kind: str = "differential_sampling", detail: str = "") -> Verdict:
    """Grade a SAMPLING-based check honestly: δ = rule-of-three(3/n). If the caller needs a tighter δ than the
    available samples afford, DECLINE (never inflate a sample count into EXACT — §0.2)."""
    delta = rule_of_three_delta(n_samples)
    if delta > required_delta:
        return decline(f"sampling δ={delta:.2e} (3/{n_samples}) exceeds required {required_delta:.2e} — "
                       f"would need ≥{int(3.0 / required_delta)} samples; DECLINE rather than overclaim", kernel)
    return probabilistic(result, kernel, complexity,
                         Cert(PROBABILISTIC, kind, True, f"{n_samples} samples", delta=delta,
                              detail=detail or f"rule-of-three δ=3/{n_samples}"))
