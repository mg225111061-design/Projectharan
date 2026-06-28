"""
§AH §6 (graph ②) — REENTRANCY / CFG security verifier (RF-3). ★ DeFi smart-contract audit (the monetization angle).
================================================================================================================
Reentrancy bug = an EXTERNAL CALL happens BEFORE a state change that the call's re-entry could exploit (the
checks-effects-interactions (CEI) pattern violated). Given the function's ordered effect list over the modelled CFG,
prove CEI holds (all state writes precede external calls) ⇒ reentrancy ABSENT (theorem under the model); a call
before a later write ⇒ FLAG (the offending order named). ★ Never "exploit-free" in general — only "no CEI violation
in the modelled CFG". LLM-free, zero-dep.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class ReentrancyVerdict:
    disposition: str        # "PROVEN-CEI" | "FLAG" | "DECLINE"
    violation: Tuple[int, int]  # (call_index, later_write_index) or (-1,-1)
    detail: str


def verify_cei(effects: List[str]) -> ReentrancyVerdict:
    """`effects` = the ordered effect sequence over the modelled CFG, each one of {"check","write","ext_call"}.
    CEI is satisfied iff NO ext_call is followed by a later write (the re-entrant window). Returns PROVEN-CEI /
    FLAG (the (call, later-write) pair) / DECLINE (unmodelled effect)."""
    if any(e not in ("check", "write", "ext_call") for e in effects):
        return ReentrancyVerdict("DECLINE", (-1, -1), "unmodelled effect in the sequence ⇒ DECLINE (never a false 'safe')")
    for i, e in enumerate(effects):
        if e == "ext_call":
            for j in range(i + 1, len(effects)):
                if effects[j] == "write":
                    return ReentrancyVerdict("FLAG", (i, j),
                                             f"external call at step {i} precedes a state write at step {j} ⇒ REENTRANCY "
                                             "WINDOW FLAGGED (checks-effects-interactions violated)")
    return ReentrancyVerdict("PROVEN-CEI", (-1, -1),
                             "every state write precedes all external calls (CEI) ⇒ reentrancy ABSENT over the modelled CFG (theorem)")


def adversarial_battery() -> dict:
    """The classic vulnerable withdraw (ext_call BEFORE the balance write) is FLAGGED with the offending order; the
    CEI-fixed version (write BEFORE call) is PROVEN-CEI; ★ an unmodelled effect DECLINES; precision 1.0 = no false
    'safe' (a real CEI violation is never passed)."""
    vuln = verify_cei(["check", "ext_call", "write"])          # call before write ⇒ reentrancy
    fixed = verify_cei(["check", "write", "ext_call"])         # CEI ⇒ safe-under-model
    unk = verify_cei(["check", "delegatecall", "write"])       # unmodelled ⇒ DECLINE
    cases = {
        "vulnerable_flagged": vuln.disposition == "FLAG" and vuln.violation == (1, 2),
        "cei_proven": fixed.disposition == "PROVEN-CEI",
        "unmodelled_declined": unk.disposition == "DECLINE",
        "no_false_safe": vuln.disposition != "PROVEN-CEI",      # ★ a real violation is never passed as safe
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
