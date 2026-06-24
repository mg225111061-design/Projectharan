"""
CATALOG ENGINE — Transform registry base types (Constitution §3.3).
===================================================================
A `Transform` is one catalog entry (a research transform), mapped to the mechanism(s) that realize it (a tuple ⇒
composition). Honesty (§1.4): "100% implemented" = every transform has an HONEST entry — NOT 100% passing. A
transform that can't yet be soundly built carries `status="UNVERIFIED(reason)"` (and `kernel=None`); the router
never auto-selects an UNVERIFIED kernel (§2). `status` flips to "VERIFIED" only once a §7-gated kernel backs it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# canonical output shapes (§3.3)
OUTPUTS = {"closed-form", "finite-invariant", "decision", "ordinal-rank", "cert-bound", "obstruction",
           "normal-form", "latent-state", "code-length"}
GRADES = {"EXACT", "PROBABILISTIC", "DECISION", "DECLINE"}


@dataclass
class Transform:
    tid: str                              # "A1.hecke_eigenform", "B2.robertson_seymour", …
    pass_label: str                       # "1-6" | "A-1" | … | "D-2"
    discipline: str                       # source field (a LABEL only — routing is by mechanism, never discipline)
    mechanisms: Tuple[int, ...]           # mechanism number(s); a tuple of >1 ⇒ composition (e.g. (10, 14))
    output: str
    cert_kind: str
    routing_probe: str                    # the cheap trigger (natural language; code where available)
    software: str = ""                    # mature external SW / algorithm name, or [이미 있음: module]
    grade_default: str = "DECISION"
    status: str = "UNVERIFIED(registered; sound apply gated in a later PHASE)"
    kernel: Optional[str] = None          # kernel_router REGISTRY key once a §7-gated kernel backs it

    def __post_init__(self):
        assert self.output in OUTPUTS, f"{self.tid}: bad output {self.output!r}"
        assert self.grade_default in GRADES, f"{self.tid}: bad grade {self.grade_default!r}"
        assert self.mechanisms and all(1 <= m <= 14 or m in (0, -1) for m in self.mechanisms), \
            f"{self.tid}: mechanisms must be 1..14 (or 0/-1 primitives), got {self.mechanisms}"
        assert self.verified or self.status.startswith("UNVERIFIED"), f"{self.tid}: status must be VERIFIED or UNVERIFIED(reason)"

    @property
    def verified(self) -> bool:
        return self.status == "VERIFIED"

    @property
    def composed(self) -> bool:
        return len(self.mechanisms) > 1


TRANSFORMS: List[Transform] = []
_SEEN: set = set()


def register(t: Transform) -> Transform:
    assert t.tid not in _SEEN, f"duplicate transform id {t.tid}"
    _SEEN.add(t.tid)
    TRANSFORMS.append(t)
    return t


def reg_many(rows: List[Transform]) -> None:
    for t in rows:
        register(t)
