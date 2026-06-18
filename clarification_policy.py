"""
v29 STAGE 30 — VoI-gated clarification policy (ask RARELY, ask SMART, max one).  ★the user philosophy★
======================================================================================================
We almost never ask. A clarifying question is justified ONLY when (a) the input is a genuine high-stakes
fork (from S29), (b) the prompt is NOT already detailed, and (c) the value of information clears a
CONSERVATIVE threshold. Then exactly ONE maximally-informative question is asked; otherwise we PROCEED with
a reasonable completion. (ClarifyGPT's 2.85 questions/problem is a CEILING to stay well under, not a goal.)

  VoI = uncertainty_reduction × cost_of_wrong_assumption / cost_of_asking
  ASK_ONE iff  (HIGH_STAKES_FORK)  ∧  (not detailed)  ∧  (VoI > threshold)        — else PROCEED.

★ ABSOLUTE RULES (§1.13) ★: a DETAILED prompt is NEVER asked (hard gate, before VoI). No trivial/obvious
questions. At most ONE question per request (zero preferred). An `AskRateMonitor` watches the ask-rate on
detailed prompts and raises the threshold if it ever drifts above ~0.

★ HONEST (§1.4, §5.4) ★: ask/don't-ask classification is hard (ClariQ F1 ~0.37) → the threshold is
deliberately conservative (toward NOT asking). Live UX/utility measurement needs a key → [BLOCKED]; the
policy logic and ask-rate accounting are deterministic and measured.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# cost of a WRONG assumption, by the stakes of the fork dimension (higher = more worth asking about)
_IRREVERSIBLE = {"delete", "remove", "drop", "overwrite", "truncate", "wipe", "destroy", "purge", "format"}
_FINANCIAL = {"payment", "charge", "refund", "bill", "money"}
_OPS = {"production", "migrate", "migration", "deploy"}
_DEFAULT_THRESHOLD = 3.0
_UNCERTAINTY = 0.6              # a binary fork resolves ~0.6 of the uncertainty (single-pass estimate)


def cost_of_wrong(prompt: str) -> float:
    t = prompt.lower()
    if any(k in t for k in _IRREVERSIBLE):
        return 10.0
    if any(k in t for k in _FINANCIAL):
        return 8.0
    if any(k in t for k in _OPS):
        return 6.0
    return 2.0


def voi(uncertainty_reduction: float, wrong_cost: float, ask_cost: float) -> float:
    return uncertainty_reduction * wrong_cost / max(ask_cost, 1e-9)


def is_detailed(req) -> bool:
    """A prompt is 'detailed' (→ NEVER ask, §1.13) when its requirement schema is rich: ≥4 confident slots,
    OR ≥3 slots WITH a stated constraint or substantial length. (Cue parsing under-binds, so we don't demand
    all six slots — the goal is 'specific enough that asking would annoy'.)"""
    if not req:
        return False
    slots = len(req.bound_slots())
    words = len(getattr(req, "raw", "").split())
    if slots >= 4 and getattr(req, "confidence", 0.0) >= 0.7:
        return True
    return slots >= 3 and (bool(getattr(req, "constraints", None)) or words >= 22)


@dataclass
class AskRateMonitor:
    detailed_total: int = 0
    detailed_asked: int = 0
    total: int = 0
    asked: int = 0

    def record(self, detailed: bool, asked: bool) -> None:
        self.total += 1
        self.asked += int(asked)
        if detailed:
            self.detailed_total += 1
            self.detailed_asked += int(asked)

    def rate_on_detailed(self) -> float:
        return self.detailed_asked / self.detailed_total if self.detailed_total else 0.0

    def overall_rate(self) -> float:
        return self.asked / self.total if self.total else 0.0

    def suggest_threshold(self, current: float, cap: float = 0.0) -> float:
        """If we EVER asked on a detailed prompt (should be impossible), raise the threshold to clamp down."""
        return current * 2 if self.rate_on_detailed() > cap else current


@dataclass
class ClarifyDecision:
    status: str                 # PROCEED | ASK_ONE
    question: Optional[str] = None
    voi: float = 0.0
    reason: str = ""

    def __str__(self):
        if self.status == "ASK_ONE":
            return f"ASK_ONE (VoI={self.voi:.1f}): {self.question}"
        return f"PROCEED — {self.reason}"


def _make_question(prompt: str) -> str:
    """One focused, non-trivial question about the core fork dimension."""
    t = prompt.lower()
    if any(k in t for k in _IRREVERSIBLE):
        return "This is irreversible — should it permanently destroy data, or do a recoverable/soft variant?"
    if any(k in t for k in _FINANCIAL):
        return "This moves money — should it execute the real transaction now, or stage it for confirmation?"
    if any(k in t for k in _OPS):
        return "This targets production — apply directly, or produce a dry-run/plan for review first?"
    return "There's one genuine fork here that changes everything — which branch did you intend?"


def decide(prompt: str, fork_report, req=None, monitor: Optional[AskRateMonitor] = None,
           threshold: float = _DEFAULT_THRESHOLD) -> ClarifyDecision:
    """Decide whether to ask (rare) or proceed (default). Only HIGH_STAKES_FORK input can ever ASK; a
    detailed prompt is never asked; VoI must clear a conservative threshold; at most ONE question."""
    detailed = is_detailed(req)
    status = getattr(fork_report, "status", "CLEAR")
    decision: ClarifyDecision
    if status != "HIGH_STAKES_FORK":
        decision = ClarifyDecision("PROCEED", reason="not a high-stakes fork → reasonable completion")
    elif detailed:
        decision = ClarifyDecision("PROCEED", reason="prompt is already detailed → NEVER ask (§1.13)")
    else:
        v = voi(_UNCERTAINTY, cost_of_wrong(prompt), ask_cost=1.0)
        if v > threshold:
            decision = ClarifyDecision("ASK_ONE", _make_question(prompt), v,
                                       "genuine high-stakes fork, VoI over the conservative threshold")
        else:
            decision = ClarifyDecision("PROCEED", voi=v,
                                       reason=f"VoI {v:.1f} ≤ threshold {threshold} → reasonable completion")
    if monitor is not None:
        monitor.record(detailed, decision.status == "ASK_ONE")
    return decision
