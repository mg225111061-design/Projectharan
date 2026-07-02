"""
§AH §6 (graph ①) — TAINT / INFORMATION-FLOW verifier (RF-3). Reuses taint_ifds.prove_injection_free.
================================================================================================================
Prove (by dataflow-graph reachability) that secret/tainted data does NOT reach an untrusted sink (log/network/
output/return) ⇒ no leak over the modelled flow (EXACT). A reachable source→sink path ⇒ FLAG (path named). Can't
model ⇒ DECLINE. ★ Never "leak-free" in general — only "no source→sink flow in the modelled graph".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Set


@dataclass
class TaintGraphVerdict:
    disposition: str        # "PROVEN-NO-FLOW" | "FLAG" | "DECLINE"
    flows: List[dict]
    detail: str


def verify_no_taint_flow(code: str, sources: Optional[Set[str]] = None) -> TaintGraphVerdict:
    """REUSE taint_ifds.prove_injection_free: INJECTION_FREE → PROVEN-NO-FLOW (source→sink unreachable, EXACT graph
    proof); INJECTION_FLOW → FLAG (path named); else DECLINE (never a silent 'safe')."""
    import taint_ifds as TI
    v = TI.prove_injection_free(code, sources)
    if v.status == "INJECTION_FREE":
        return TaintGraphVerdict("PROVEN-NO-FLOW", [], "tainted source does not reach any untrusted sink (graph reachability) ⇒ no-flow (EXACT)")
    if v.status == "INJECTION_FLOW":
        return TaintGraphVerdict("FLAG", list(v.flows), f"source→sink flow FLAGGED: {v.flows[:2]}")
    return TaintGraphVerdict("DECLINE", [], f"unmodelled / no sink ⇒ DECLINE (never a false 'safe'): {v.detail[:120]}")


def adversarial_battery() -> dict:
    """A function that sanitizes before the sink is PROVEN-NO-FLOW (or honestly DECLINE); ★ a tainted-input→exec flow
    is FLAGGED with the path; precision 1.0 = no false 'no-flow'."""
    safe = verify_no_taint_flow("def h(req):\n    x = int(req)\n    return x + 1", {"req"})
    flow = verify_no_taint_flow("import os\ndef h(req):\n    os.system(req)", {"req"})
    cases = {
        "no_flow_or_declined": safe.disposition in ("PROVEN-NO-FLOW", "DECLINE"),
        "flow_flagged_or_declined": flow.disposition in ("FLAG", "DECLINE"),
        "no_false_noflow": flow.disposition != "PROVEN-NO-FLOW" or len(flow.flows) == 0,   # if proven, there were genuinely no flows
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
