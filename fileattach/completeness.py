"""
§BI FL-4 — ★ 100% EXTRACTION (verifiable, EXACT) vs understanding (best-effort, NEVER certified).
===================================================================================================
Correction 2 made structural. Two claims that must never be conflated:

  • **Extraction completeness** — did we pull EVERY declared unit (page / sheet / slide / archive entry / row)?
    This is decidable: compare the container's DECLARED count to the count we actually extracted. Equal ⇒ the
    extraction is provably complete ⇒ graded **EXACT** (via `kernel_verdict`, the same soundness ADT as every
    fold). A gap ⇒ honest **DECLINE** with the exact shortfall — never "probably fine".

  • **Understanding** — did the LLM grasp the meaning? This is probabilistic and **cannot be certified**. This
    module makes that structural: `certify_understanding()` ALWAYS raises (a false-EXACT guard, like §BF's
    GradeViolation), and every verdict carries `understanding_certified == False`. You can ask whether extraction
    is complete; you can NEVER get a certificate that the content was understood.

zero-dep (stdlib + kernel_verdict). This module verifies counts; it does not itself parse files (the extractors
in `mathmode/ingest.py` / `file_ingest.py` do that, then hand their declared/extracted tallies here).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import kernel_verdict as KV


class UnderstandingCertificationError(AssertionError):
    """Raised by any attempt to CERTIFY understanding. ★ Correction 2: extraction is verifiable, understanding is
    not — certifying it would be a false-EXACT. Subclasses AssertionError so existing handlers still catch it, but
    it is raised EXPLICITLY (never via `assert`) so `python -O` cannot strip the guard."""


# ★ the structural fact: understanding is never certifiable through this system
UNDERSTANDING_CERTIFIABLE = False


def certify_understanding(*_args, **_kwargs):
    """There is no honest path to a certified-understanding verdict. This function exists ONLY to refuse — any
    caller that reaches for it gets a hard error, so 'we 100% understood the file' cannot be produced in code."""
    raise UnderstandingCertificationError(
        "understanding is best-effort and is NEVER certified (false-EXACT 0) — use check_completeness for the "
        "verifiable EXTRACTION claim; LLM comprehension carries no certificate")


@dataclass
class ExtractionVerdict:
    complete: bool
    declared: Dict[str, int]
    extracted: Dict[str, int]
    gaps: List[Tuple[str, int, int]] = field(default_factory=list)   # (unit, declared, extracted)
    verdict: "KV.Verdict" = None                                     # EXACT iff complete, else DECLINE
    understanding_certified: bool = False                            # ★ ALWAYS False (Correction 2)


def check_completeness(declared: Dict[str, int], extracted: Dict[str, int]) -> ExtractionVerdict:
    """Compare declared vs extracted unit counts (pages/sheets/slides/entries/rows). All equal ⇒ extraction is
    provably complete ⇒ EXACT; any shortfall ⇒ DECLINE with the gap. ★ Extraction is verified; understanding is
    not even attempted here (it carries no certificate)."""
    gaps: List[Tuple[str, int, int]] = []
    for unit, dcount in declared.items():
        ecount = int(extracted.get(unit, 0))
        if ecount != int(dcount):
            gaps.append((unit, int(dcount), ecount))
    complete = not gaps
    if complete:
        cert = KV.Cert(KV.EXACT, "extraction_completeness", passed=True, check_cost="O(#units)",
                       detail=f"every declared unit extracted: {dict(declared)} (counts match exactly)")
        verdict = KV.exact(dict(extracted), "fileattach_extract", "O(#units)", cert)
    else:
        verdict = KV.decline(f"extraction INCOMPLETE — gaps (unit, declared, extracted): {gaps}; honest partial, "
                             f"never reported as complete", "fileattach_extract")
    return ExtractionVerdict(complete=complete, declared=dict(declared), extracted=dict(extracted), gaps=gaps,
                             verdict=verdict, understanding_certified=False)


def adversarial_battery() -> dict:
    """★ complete extraction ⇒ EXACT (verifiable); ★ a missing page ⇒ DECLINE with the exact gap (never 'probably
    complete'); ★ understanding is NEVER certified — certify_understanding() raises, every verdict says so."""
    full = check_completeness({"pages": 10, "sheets": 3}, {"pages": 10, "sheets": 3})
    short = check_completeness({"pages": 10}, {"pages": 7})
    refused = False
    try:
        certify_understanding("the document", "means X")
    except UnderstandingCertificationError:
        refused = True
    cases = {
        "complete_is_EXACT": full.complete and full.verdict.status == KV.EXACT,
        "gap_is_DECLINE": (not short.complete) and short.verdict.status == KV.DECLINE and short.gaps == [("pages", 10, 7)],
        "understanding_never_certified": full.understanding_certified is False and short.understanding_certified is False,
        "certify_understanding_refused": refused and UNDERSTANDING_CERTIFIABLE is False,
        "extraction_exact_carries_cert": full.verdict.certificate is not None and full.verdict.certificate.passed,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
