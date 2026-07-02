"""
CATALOG ENGINE — StructForm IR (Constitution §5, the connective tissue of composition).
=======================================================================================
The common representation that flows BETWEEN mechanisms so they CHAIN: one mechanism's output StructForm becomes
the next's input. This is what turns 14 isolated `apply`s into a composition BODY (몸통). The grade accumulates by
the WEAKEST-LINK law (`catalog.compose.combine_grade`): a chain is only as strong as its weakest stage, and the IR
makes a false upgrade — claiming EXACT while a PROBABILISTIC/DECLINE cert sits in the chain — a CONSTRUCTOR-TIME
exception (`assert_invariant`), never a silent label. "잘못된 답보다 DECLINE이 항상 옳다."

`StructForm`:
  kind        raw | spectral | closed_form | invariant | residual | decided | declined  (+ normal_form/…)
  data        the currently-structured object (what the next mechanism consumes)
  residual    the not-yet-structured remainder (the key to M7's structure⊕pseudorandom split)
  grade       EXACT | PROBABILISTIC | DECLINE — the ACCUMULATED weakest-link grade so far
  cert_chain  the KV.Certs accumulated (every one must be passed=True — the ADT enforces it)
  path        the mechanism_path as (m_num, grade, cert_kind) triples — full §7 traceability
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

import kernel_verdict as KV

# the grade lattice (weakest → strongest): DECLINE < PROBABILISTIC < EXACT. A composition's grade is the MIN.
_ORDER = {KV.DECLINE: 0, KV.PROBABILISTIC: 1, KV.EXACT: 2}

# kinds that count as "structured" (a mechanism produced a real object), vs the raw/declined poles.
STRUCTURED_KINDS = frozenset(
    {"spectral", "closed_form", "invariant", "decided", "normal_form", "latent_state", "code_length", "residual"})

_KEEP = object()   # sentinel: "leave this field unchanged" in accumulate()


def weaker(g1: str, g2: str) -> str:
    """The weakest-link of two grades (the ⊓ of the grade lattice)."""
    return g1 if _ORDER[g1] <= _ORDER[g2] else g2


@dataclass
class StructForm:
    kind: str
    data: Any = None
    residual: Any = None
    grade: str = KV.EXACT            # MIN-identity of the lattice (an empty chain composes as the top element)
    cert_chain: List[KV.Cert] = field(default_factory=list)
    path: List[Tuple[int, str, str]] = field(default_factory=list)

    # ── constructors ─────────────────────────────────────────────────────────────────────────────────
    @classmethod
    def raw(cls, x: Any) -> "StructForm":
        """Wrap a raw input as the start of a composition (everything is residual, nothing yet structured)."""
        return cls(kind="raw", data=x, residual=x, grade=KV.EXACT, cert_chain=[], path=[])

    # ── views ────────────────────────────────────────────────────────────────────────────────────────
    @property
    def mechanism_path(self) -> List[int]:
        """The bare mechanism-number path (backward-compatible with the §5 output tuple)."""
        return [m for (m, _g, _k) in self.path]

    @property
    def stopped(self) -> bool:
        return self.grade == KV.DECLINE

    def working(self) -> Any:
        """The object the next mechanism in a CHAIN consumes — the current structured data (raw payload if raw)."""
        return self.data

    # ── the weakest-link invariant (the honesty core; called on every to_verdict) ──────────────────────
    def assert_invariant(self) -> None:
        """No fake pass, no false upgrade. Every accumulated cert must be passed=True; and the composed grade can
        never be STRONGER than the weakest cert in the chain (claiming EXACT over a PROBABILISTIC cert ⇒ raise)."""
        for c in self.cert_chain:
            assert c.passed, f"WEAKEST-LINK: cert {c.kind!r} in the chain is not passed=True — would be a fake pass"
        if not self.cert_chain:
            return
        weakest = min((_ORDER[c.grade] for c in self.cert_chain), default=_ORDER[KV.EXACT])
        assert _ORDER[self.grade] <= weakest, (
            f"WEAKEST-LINK VIOLATION: composed grade {self.grade} is STRONGER than the weakest cert in the chain "
            f"({[c.grade for c in self.cert_chain]}) — a false upgrade (ADT exception, §5)")

    # ── the composition transition: fold a mechanism's Verdict into this form (uses compose.combine_grade) ──
    def accumulate(self, m_num: int, v: "KV.Verdict", *, new_kind: Optional[str] = None,
                   data: Any = _KEEP, residual: Any = _KEEP, cert_kind: Optional[str] = None) -> "StructForm":
        """Return a NEW StructForm = this one composed with mechanism `m_num`'s Verdict `v`, by the weakest-link
        law. A DECLINE `v` SHORT-CIRCUITS: the grade drops to DECLINE and `.stopped` is True (the executor halts
        the chain there, downstream not run), but the path still records (m_num, DECLINE, reason)."""
        from catalog.compose import combine_grade          # lazy import (breaks the compose↔ir cycle)
        grade, certs, _stop = combine_grade(self.grade, self.cert_chain, v)
        if v.status == KV.DECLINE:
            # record the FULL DECLINE reason (the obstruction / HONEST_DEFER proof) — never truncated, it IS the
            # certificate of a DECLINE-as-win; `cert_kind` (if given) is a short label prepended for the trace.
            rec = f"{cert_kind}: {v.reason}" if cert_kind else (v.reason or "DECLINE")
            new_kind = new_kind or "declined"
        else:
            rec = cert_kind or (v.certificate.kind if v.certificate else "-")
            new_kind = new_kind or self.kind
        return StructForm(
            kind=new_kind,
            data=self.data if data is _KEEP else data,
            residual=self.residual if residual is _KEEP else residual,
            grade=grade,
            cert_chain=certs,
            path=self.path + [(m_num, v.status, rec)])

    def note_step(self, m_num: int, grade: str, kind: str) -> "StructForm":
        """Append a TRACE-only step to the path WITHOUT adding a cert or changing the composed grade. For
        derived/read-off stages (e.g. M1 reading the spectrum off M7's certified split — one machine-check, two
        conceptual stages) and for branch-probe notes (an alternative leg that didn't fire must not poison the grade)."""
        return StructForm(self.kind, self.data, self.residual, self.grade, list(self.cert_chain),
                          self.path + [(m_num, grade, kind)])

    # ── exit: collapse the accumulated form back to a single graded KV.Verdict (the §5.6 output) ─────────
    def to_verdict(self, kernel: str = "catalog.compose", complexity: str = "composition") -> "KV.Verdict":
        """Collapse to one KV.Verdict, re-checking the weakest-link invariant first (false upgrade ⇒ raise)."""
        self.assert_invariant()
        if self.grade == KV.DECLINE or not self.cert_chain:
            decl = [p for p in self.path if p[1] == KV.DECLINE]
            detail = " ; ".join(f"M{m}: {why}" for (m, _g, why) in decl) if decl else "no mechanism structured the input"
            reason = f"composition DECLINE [path={self.mechanism_path}]: {detail}"   # surfaces every obstruction/HONEST_DEFER proof in the chain
            return KV.decline(reason, kernel)
        kinds = "∘".join(c.kind for c in self.cert_chain)
        bounds = [c.bound for c in self.cert_chain if c.bound is not None]
        bound = bounds[-1] if bounds else None
        epss = [c.epsilon for c in self.cert_chain if c.epsilon is not None]
        eps = sum(epss) if epss else None                  # ε propagated per-op (additive)
        if self.grade == KV.PROBABILISTIC:
            deltas = [c.delta for c in self.cert_chain if c.delta is not None]
            delta = sum(deltas) if deltas else None        # δ_total ≤ Σδ_i (union bound)
            cert = KV.Cert(KV.PROBABILISTIC, f"composition[{kinds}]", passed=True,
                           check_cost="re-verified per stage (weakest-link)", epsilon=eps, delta=delta, bound=bound,
                           detail=f"path={self.path}")
            return KV.probabilistic(self.data, kernel, complexity, cert)
        cert = KV.Cert(KV.EXACT, f"composition[{kinds}]", passed=True,
                       check_cost="re-verified per stage (weakest-link)", epsilon=eps, bound=bound,
                       detail=f"path={self.path}")
        return KV.exact(self.data, kernel, complexity, cert)
