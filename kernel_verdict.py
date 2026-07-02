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


class GradeViolation(AssertionError):
    """A SOUNDNESS-gate violation — the construction would permit a false-EXACT (rubber-stamp / grade-cert
    mismatch / δ-masquerade). ★ §BF FIX-1: subclasses AssertionError so every existing handler still catches it,
    but the gates `raise` it EXPLICITLY (never via `assert`), so `python -O` — which strips `assert` statements —
    CANNOT remove the false-EXACT guard. The false-EXACT-0 spine is structural, not flag-dependent."""


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
        # ★ §BF FIX-1: these are SOUNDNESS gates (each one's removal would permit a false-EXACT), so they `raise`
        #   explicitly — NEVER `assert`, which `python -O` strips. Do not "simplify" these back to assert.
        if self.status not in _GRADES:
            raise GradeViolation(f"bad grade {self.status!r}")                      # soundness gate
        if self.status != DECLINE:
            if not (self.certificate is not None and self.certificate.passed):
                raise GradeViolation(f"{self.status} requires a passed certificate (no rubber stamp)")  # soundness gate
            if self.certificate.grade != self.status:
                raise GradeViolation(f"grade/cert mismatch: {self.status} vs {self.certificate.grade}")  # soundness gate
            if self.status == PROBABILISTIC and self.certificate.delta is None:
                raise GradeViolation("PROBABILISTIC must state δ (a number)")        # soundness gate
            if self.status == EXACT and self.certificate.delta is not None:
                # EXACT forbids a probabilistic δ masquerading as exact (an exact interval uses epsilon/bound)
                raise GradeViolation("EXACT cannot carry a probabilistic δ — use PROBABILISTIC, or an exact "
                                     "interval (epsilon)")                            # soundness gate

    def as_dict(self) -> dict:
        """Plain-dict, JSON-safe serialization of an ALREADY-validated Verdict. Grade enforcement happened
        ONCE, in __post_init__ at construction time — this is a safe projection, not a second gate. The
        canonical grade key is "grade" (deliberately NOT aliased as "status": several bespoke API response
        shapes already use "status" for an unrelated outcome label, e.g. "CLOSED_FORM"/"OFFLOADED" — aliasing
        would silently collide with those on merge)."""
        d = {"grade": self.status, "result": self.result, "kernel": self.kernel,
             "complexity": self.complexity, "reason": self.reason}
        if self.certificate is not None:
            c = self.certificate
            d["certificate"] = {"grade": c.grade, "kind": c.kind, "passed": c.passed, "check_cost": c.check_cost,
                                "epsilon": c.epsilon, "delta": c.delta, "bound": c.bound, "detail": c.detail}
        else:
            d["certificate"] = None
        if self.crossover_n is not None:
            d["crossover_n"] = self.crossover_n
        if self.amdahl_p is not None:
            d["amdahl_p"] = self.amdahl_p
        return d


# ── constructors ────────────────────────────────────────────────────────────────────────────────────
def decline(reason: str, kernel: str = "-") -> Verdict:
    return Verdict(DECLINE, None, kernel, "-", None, reason)


def exact(result, kernel: str, complexity: str, cert: Cert, **kw) -> Verdict:
    return Verdict(EXACT, result, kernel, complexity, cert, **kw)


def probabilistic(result, kernel: str, complexity: str, cert: Cert, **kw) -> Verdict:
    return Verdict(PROBABILISTIC, result, kernel, complexity, cert, **kw)


# ── §BS-1 emission-boundary gate: "grade enforced at construction" extended to the API/dict boundary ───
def to_api(status: str, result: Any, kernel: str, complexity: str, cert: Optional[Cert] = None,
           reason: str = "", **extras) -> dict:
    """The ONE sanctioned way to build an API/response dict that carries a grade. Constructs a real
    `Verdict` internally, so `__post_init__`'s soundness gates apply EXACTLY as they would to any other
    kernel output — a raw `{"grade": "EXACT", ...}` dict literal with no certificate, or a grade/certificate
    mismatch, is STRUCTURALLY unreachable via this path (§BP-16/§BQ audit finding: several call-sites hand-
    wrote such literals, bypassing the ADT entirely).

    `extras` may ADD route-specific display keys (e.g. `action`/`ui`/`kind`/`status` — a bespoke response's
    OWN "status" field, distinct from the grade) but can never OVERRIDE the enforced core fields (grade/
    result/kernel/complexity/certificate/reason/crossover_n/amdahl_p) — a caller cannot smuggle a bypass
    grade past the gate through a same-named kwarg; the enforced value always wins."""
    v = Verdict(status, result, kernel, complexity, cert, reason)   # __post_init__ enforces every soundness gate
    d = v.as_dict()
    for k, val in extras.items():
        if k not in d:
            d[k] = val
    return d


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
