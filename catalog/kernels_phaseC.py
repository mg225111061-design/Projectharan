"""
CATALOG ENGINE — PHASE C gated kernels (fold-core self-improvement).
====================================================================
Ordinal-bounded termination (the fold/loop decreases-clause backbone) registered as a §7-gated kernel, flipping
its catalog transforms to VERIFIED. The arithmetic-hierarchy routing probe (mechanism 9) is wired into
`catalog.compose` as the §5-first signal. NbE / cut-elimination as the evaluation core is HONEST_DEFERred
(`haran_eval.Interp` exists, but a gated `normalize()` fold-core entry is beyond this PHASE's budget — §1.6).
"""
from __future__ import annotations

import kernel_router as KR
import kernel_verdict as KV
import ordinal_cert
from catalog.kernels_phaseB import _verify_transform


# ── ordinal-bounded termination (mechanism 14 / ordinal) — the fold decreases-clause ─────────────────
def _ord_detect(data) -> bool:
    return isinstance(data, dict) and data.get("ordinal_termination") is True and (
        "measures" in data or ("before" in data and "after" in data))


def _ord_run(data, **kw) -> KV.Verdict:
    if "measures" in data:
        return ordinal_cert.descent_witness(data["measures"])
    return ordinal_cert.step_cert(tuple(data["before"]), tuple(data["after"]))


KR.register(KR.Kernel(
    num=104, name="ordinal_termination", group="catalog",
    contract="requires a lexicographic measure (tuple of naturals) per loop/recursion step; ensures EXACT "
            "termination when the measures map to a strictly DESCENDING ordinal sequence (CNF, well-founded ⇒ "
            "finite), machine-rechecked by ordinal.check_descent; else DECLINE (no false termination claim); "
            "grade EXACT | DECLINE",
    detect=_ord_detect, run=_ord_run, status="VERIFIED"))
_verify_transform("D1.ordinal_termination", "ordinal_termination")
_verify_transform("B2.ranking_termination", "ordinal_termination")
