"""
v29 §4 — the prompt-understanding FRONT-END: S26→S31 wired into one fail-safe pipeline.
=========================================================================================
                          prompt
                            │
              [S26] requirement-structure parse  (cached on the prefix)
                            │
      ┌──────── parallel cascade (cheap; runs beside the first token) ────────┐
      │  [S27] missing-info   [S28] danger/contradiction   [S29] ambiguity    │
      │                       [S31] cross-representation consistency           │
      └───────────────────────────────┬───────────────────────────────────────┘
                            │  [policy engine]
   • danger/contradiction/divergence  → FLAG + safe alternative (proceed, never silently comply)
   • genuine high-stakes fork / critical-missing → [S30] VoI: ASK_ONE (rare) else PROCEED
   • minor ambiguity / minor missing  → PROCEED + STATED ASSUMPTIONS  (does NOT ask)
   • all clear                        → PROCEED
                            │
        structured · grounded · clarified requirements → write→verify→fix (v26–v28)

★ This breaks garbage-in-garbage-out: a bad prompt is detected and completed/flagged, never silently
propagated. ★ FAIL-SAFE everywhere: the default is PROCEED with stated assumptions; we ask only on a
VoI-cleared high-stakes fork and we flag danger — never a silent wrong action, never a hard block.
★ ZERO-WRONG-ANSWER (§1.12): the front-end only ADDS structure/assumptions/flags; the original prompt is
preserved and the downstream verifier's correctness is unchanged. ★ Latency: the cascade is deterministic
(regex + a couple of Z3 calls), measured here; the live model first-token is [BLOCKED: key/egress].
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional

import ambiguity_detector as S29
import clarification_policy as S30
import dangerous_instruction_detector as S28
import missing_info_detector as S27
import prompt_consistency as S31
import requirement_parser as S26


@dataclass
class FrontendDecision:
    action: str                 # PROCEED | ASK_ONE | FLAG
    proceed: bool               # True unless we must get the answer first (ASK_ONE)
    assumptions: List[str] = field(default_factory=list)   # reasonable completions, stated for the user
    flags: List[str] = field(default_factory=list)         # danger/contradiction/divergence + alternatives
    question: Optional[str] = None
    requirements: object = None
    latency_ms: float = 0.0
    detail: str = ""

    def __str__(self):
        if self.action == "ASK_ONE":
            return f"ASK_ONE: {self.question}"
        if self.action == "FLAG":
            return f"FLAG (proceeds with safe reading): {self.flags}"
        return f"PROCEED" + (f" with assumptions {self.assumptions}" if self.assumptions else " (all clear)")


def analyze(prompt: str, symbols: Optional[List[str]] = None, mode: str = "normal",
            monitor: Optional[S30.AskRateMonitor] = None) -> FrontendDecision:
    """Run the full understanding cascade + policy engine. Default PROCEED (+stated assumptions); ASK only a
    VoI-cleared high-stakes fork; FLAG danger/contradiction. Never silent, never hard-block (fail-safe)."""
    t0 = time.perf_counter()
    req = S26.parse_requirements(prompt, mode)
    missing = S27.detect_missing(req)
    danger = S28.detect(prompt)
    ambiguity = S29.detect_ambiguity(prompt)
    consistency = S31.gate(prompt, symbols)
    latency = (time.perf_counter() - t0) * 1000

    assumptions: List[str] = []
    assumptions += missing.assumptions()
    assumptions += ambiguity.assumptions()
    flags: List[str] = []
    if danger.status == "FLAGGED":
        flags += [f"{f.kind}({f.cwe or '-'}): {f.evidence} → {f.alternative}" for f in danger.flags]
    if consistency.status == "DIVERGENT":
        flags += [f"inconsistent prompt: {d}" for d in consistency.divergences]

    # policy engine (priority): danger/divergence FLAG → high-stakes fork S30 → minor PROCEED+assume → clear
    if flags:
        return FrontendDecision("FLAG", True, assumptions, flags, None, req, latency,
                                "flagged a danger/contradiction/divergence + safe alternative; proceeds, "
                                "never silently complies, never hard-blocks")
    high_stakes = (ambiguity.status == "HIGH_STAKES_FORK") or missing.escalate_to_s30
    if high_stakes:
        fork = ambiguity if ambiguity.status == "HIGH_STAKES_FORK" else \
            S29.AmbiguityReport("HIGH_STAKES_FORK", fork="critical missing requirement")
        decision = S30.decide(prompt, fork, req=req, monitor=monitor)
        if decision.status == "ASK_ONE":
            return FrontendDecision("ASK_ONE", False, assumptions, [], decision.question, req, latency,
                                    "genuine high-stakes fork, VoI over threshold → exactly one question")
        return FrontendDecision("PROCEED", True, assumptions, [], None, req, latency,
                                "high-stakes fork but VoI/detailed → reasonable completion (no question)")
    if monitor is not None:
        monitor.record(S30.is_detailed(req), False)
    return FrontendDecision("PROCEED", True, assumptions, [], None, req, latency,
                            "reasonable completion with stated assumptions" if assumptions else "all clear")
