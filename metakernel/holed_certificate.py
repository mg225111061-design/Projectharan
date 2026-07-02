"""
§BQ NEW-2 — Why3-style "holed" certificates for fold-IR transform chains.
=============================================================================
A `catalog.ir.StructForm` chain (via `.accumulate`) already enforces the weakest-link law and refuses a
false upgrade — but it requires a COMPLETE `KV.Verdict` at every step before that step can be recorded at
all. `HoledChain` is a PARALLEL, optional representation for the time BEFORE that: a planned proof
SKELETON — which stages exist, what each one is supposed to certify, and (if known) HOW to check it — with
explicit `is_hole=True` markers for anything not yet checked. Nothing here duplicates the weakest-link law
or StructForm itself: `to_struct_form()` only ever converts a FULLY-filled chain by calling the EXISTING
`StructForm.raw(...).accumulate(...)` machinery, unmodified.

★ Why this matters beyond bookkeeping: it is the natural HANDLE for §BQ Stage 2 (Adapton DCG) — a small
edit to one stage's input means only THAT stage's hole needs re-filling (`fill(stage)`), not the whole
chain re-derived from scratch. `HoledChain` makes "which holes are open / which one needs re-filling"
an explicit, queryable state instead of an implicit re-run-everything assumption.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

import kernel_verdict as KV


@dataclass
class HoledCert:
    stage: str                                          # the transform/mechanism name this slot belongs to
    cert: Optional[KV.Cert] = None                      # None = an open hole (not yet checked)
    checker: Optional[Callable[[], KV.Cert]] = None     # how to fill it, if known (lazy — not run until fill())

    @property
    def is_hole(self) -> bool:
        return self.cert is None


@dataclass
class HoledChain:
    """A sequence of holed certificates describing a planned fold-IR transform pipeline. Stages may be
    added with a known checker (fillable on demand) or as a bare, EXPLICIT hole (no checker registered yet
    — a documented gap, never a silent one)."""
    holes: List[HoledCert] = field(default_factory=list)
    _fill_counts: dict = field(default_factory=dict)     # stage -> number of times its checker has actually run

    def add_hole(self, stage: str, checker: Optional[Callable[[], KV.Cert]] = None) -> "HoledChain":
        self.holes.append(HoledCert(stage, cert=None, checker=checker))
        return self

    def add_filled(self, stage: str, cert: KV.Cert) -> "HoledChain":
        self.holes.append(HoledCert(stage, cert=cert))
        return self

    def replace_checker(self, stage: str, checker: Callable[[], KV.Cert]) -> bool:
        """Mark a previously-filled (or holed) stage's checker as STALE — reopen it as a hole with the new
        checker. This is the 'one stage's input changed' operation: callers re-open exactly the stages whose
        inputs actually changed, leaving every other stage's existing cert untouched."""
        for h in self.holes:
            if h.stage == stage:
                h.cert = None
                h.checker = checker
                return True
        return False

    @property
    def open_holes(self) -> List[str]:
        return [h.stage for h in self.holes if h.is_hole]

    def fill(self, stage: str) -> bool:
        """Run the named hole's checker (if registered) and replace the hole with its result. Returns True
        iff the hole is now filled (checked — not necessarily PASSED; a failed check fills the hole with a
        DECLINE-grade Cert, which is itself a complete, honest result, not an unfilled gap)."""
        for h in self.holes:
            if h.stage == stage and h.is_hole:
                if h.checker is None:
                    return False                          # no checker registered — stays an explicit, documented hole
                h.cert = h.checker()
                self._fill_counts[stage] = self._fill_counts.get(stage, 0) + 1
                return True
        return False

    def fill_all(self) -> List[str]:
        """Fill every hole that has a registered checker. Returns the stages that remain open afterward (no
        checker available) — those are NEVER silently treated as passed."""
        for h in self.holes:
            if h.is_hole and h.checker is not None:
                self.fill(h.stage)
        return self.open_holes

    def fill_count(self, stage: str) -> int:
        """How many times this stage's checker has actually executed — the Clock-B evidence that filling
        one stage does not re-run the others (used by the §BQ Stage-2 incremental-consistency tests)."""
        return self._fill_counts.get(stage, 0)

    def to_struct_form(self, raw_data: Any):
        """Convert a FULLY-filled chain (zero open holes) into a real `catalog.ir.StructForm` via the
        EXISTING, unmodified accumulate/weakest-link machinery. Returns None if any hole remains — an honest
        refusal, never a partial/silent upgrade."""
        if self.open_holes:
            return None
        from catalog.ir import StructForm
        sf = StructForm.raw(raw_data)
        for i, h in enumerate(self.holes):
            c = h.cert
            if c.grade == KV.EXACT:
                v = KV.exact(raw_data, h.stage, "holed-chain", c)
            elif c.grade == KV.PROBABILISTIC:
                v = KV.probabilistic(raw_data, h.stage, "holed-chain", c)
            else:
                v = KV.decline(c.detail or f"{h.stage}: certificate did not pass", h.stage)
            sf = sf.accumulate(i, v, cert_kind=c.kind)
        return sf


def adversarial_battery() -> dict:
    """★ a fully-filled, all-EXACT chain converts to a StructForm whose to_verdict() is EXACT. ★ an open
    hole (no checker) refuses conversion (None), never a silent upgrade. ★ a checker that legitimately
    DECLINEs still COUNTS as filled, and the resulting StructForm's grade is DECLINE (weakest-link, reused
    not reimplemented). ★ replacing one stage's checker and re-filling touches ONLY that stage (fill_count
    proves the others are untouched) — the incremental-re-verification property NEW-2 exists to enable."""
    import sos_cert
    import sympy as sp

    calls = {"a": 0, "b": 0}

    def checker_a():
        calls["a"] += 1
        return KV.Cert(KV.EXACT, "stage_a", passed=True, detail="a ok")

    def checker_b():
        calls["b"] += 1
        return KV.Cert(KV.EXACT, "stage_b", passed=True, detail="b ok")

    chain = HoledChain().add_hole("a", checker_a).add_hole("b", checker_b)
    remaining = chain.fill_all()
    sf = chain.to_struct_form(raw_data=42)
    full_chain_exact = (not remaining and sf is not None and sf.to_verdict().status == KV.EXACT
                        and chain.fill_count("a") == 1 and chain.fill_count("b") == 1)

    open_chain = HoledChain().add_hole("documented_but_unchecked")          # explicit hole, no checker
    open_refuses = open_chain.to_struct_form(raw_data=1) is None and open_chain.open_holes == ["documented_but_unchecked"]

    def checker_fail():
        return KV.Cert(KV.DECLINE, "stage_fail", passed=False, detail="legitimately could not verify")

    decl_chain = HoledChain().add_hole("ok_stage", checker_a).add_hole("fail_stage", checker_fail)
    decl_chain.fill_all()
    sf_decl = decl_chain.to_struct_form(raw_data=1)
    decline_propagates = (sf_decl is not None and sf_decl.to_verdict().status == KV.DECLINE
                          and not decl_chain.open_holes)                     # filled (checked), even though it failed

    # incremental re-verification: refill only "a" after "replacing" its checker — "b" must NOT re-run
    incr_chain = HoledChain().add_hole("a", checker_a).add_hole("b", checker_b)
    incr_chain.fill_all()
    before_b = incr_chain.fill_count("b")
    incr_chain.replace_checker("a", checker_a)                              # simulate "a"'s input changed
    incr_chain.fill("a")
    only_a_refilled = (incr_chain.fill_count("a") == 2 and incr_chain.fill_count("b") == before_b == 1)

    # a real SOS witness as one stage of a 2-stage chain, demonstrating this isn't toy data
    x = sp.Symbol("x")

    def sos_checker():
        g = sos_cert.sos_gram(x ** 2)
        Q, basis = g
        ok = sos_cert.verify_sos(x ** 2, Q, basis)
        return KV.Cert(KV.EXACT if ok else KV.DECLINE, "sos_gram", passed=ok, detail="x^2 SOS witness")

    real_chain = HoledChain().add_hole("sos_stage", sos_checker)
    real_chain.fill_all()
    real_sf = real_chain.to_struct_form(raw_data=x ** 2)
    real_witness_chain_exact = real_sf is not None and real_sf.to_verdict().status == KV.EXACT

    cases = {
        "full_chain_converts_to_exact_structform": full_chain_exact,
        "open_hole_refuses_conversion": open_refuses,
        "declined_stage_fills_and_propagates_decline": decline_propagates,
        "replace_and_refill_touches_only_that_stage": only_a_refilled,
        "real_sos_witness_chain_is_exact": real_witness_chain_exact,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2, default=str))
