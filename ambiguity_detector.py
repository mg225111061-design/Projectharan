"""
v29 STAGE 29 — ambiguity detector + reasonable completion (the DEFAULT policy: almost never asks).
====================================================================================================
When a prompt admits several readings we do NOT silently pick one and we do NOT reflexively ask. The
default is to COMPLETE reasonably and STATE the assumption. Only a genuine high-stakes fork (a choice that
is irreversible/costly AND left open) is escalated to S30 — and even there S30 usually proceeds.

  • CLEAR              — no vague markers → proceed.
  • MINOR_AMBIGUITY    — vague terms but a concrete goal → reasonable completion + "assumed X" (does NOT ask).
  • HIGH_STAKES_FORK   — a costly/irreversible dimension left genuinely open → hand to S30 (VoI-gated).

★ HONEST (§0.4, §1.4, §1.13, §5.2) ★: ambiguity detection is imperfect (precision 34-97%, ClariQ
ask-need F1 ~0.37), so this is CONSERVATIVE toward CLEAR/MINOR (not asking). The cheap path is a
deterministic LEXICON; the semantic-entropy probe and ClarifyGPT-style multi-sample code-consistency need
an LLM and are [BLOCKED: key/egress]. Fail-safe: uncertain → reasonable completion + stated assumption.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# vague / open-ended terms → a sensible default to assume (and state)
_VAGUE_DEFAULT: Dict[str, str] = {
    "fast": "target the standard optimal complexity for the task (e.g. O(n log n) sort)",
    "efficient": "target the standard optimal complexity; avoid quadratic blowups",
    "large": "design for inputs up to ~1e6 elements; stream/iterate, don't hold needless copies",
    "small": "assume inputs fit comfortably in memory",
    "robust": "validate inputs and raise clear typed errors",
    "scalable": "keep per-item work near-linear; no global quadratic structures",
    "user-friendly": "clear error messages + sensible defaults",
    "appropriate": "a sensible default consistent with the stated goal",
    "reasonable": "a sensible default consistent with the stated goal",
    "some": "a small representative set",
    "several": "about 3-5",
    "etc": "the remaining cases follow the same pattern",
    "and so on": "the remaining cases follow the same pattern",
    "as needed": "only when the stated condition holds",
    "handle it": "validate and handle the error path explicitly",
}
_OPEN_RANGE = ("up to", "around", "approximately", "roughly", "or so", "ish")
# dimensions where the WRONG choice is costly/irreversible
_HIGH_STAKES = ("delete", "remove", "drop", "overwrite", "truncate", "wipe", "destroy", "purge",
                "payment", "charge", "refund", "production", "migrate", "irreversible", "format")
# markers that a choice is left genuinely OPEN
_FORK = ("either", " or ", "your call", "you decide", "whichever", "up to you", "if you want",
         "one of", "some way", "a or b")


@dataclass
class AmbiguityReport:
    status: str                 # CLEAR | MINOR_AMBIGUITY | HIGH_STAKES_FORK
    score: float = 0.0
    vague_terms: List[str] = field(default_factory=list)
    completions: Dict[str, str] = field(default_factory=dict)   # vague term -> assumed default
    fork: Optional[str] = None
    detail: str = ""

    @property
    def asks(self) -> bool:
        return False             # ★ S29 itself NEVER asks — only S30 may, and only on HIGH_STAKES_FORK ★

    def assumptions(self) -> List[str]:
        return [f"assumed '{t}' = {d}" for t, d in self.completions.items()]

    def __str__(self):
        if self.status == "CLEAR":
            return "CLEAR — no vague markers (proceed, no question)"
        if self.status == "MINOR_AMBIGUITY":
            return f"MINOR_AMBIGUITY {self.vague_terms} → reasonable completion (no question): {self.assumptions()}"
        return f"HIGH_STAKES_FORK ({self.fork}) → S30 (VoI-gated)"


def _high_stakes_fork(text: str) -> Optional[str]:
    """A fork is high-stakes only when a costly/irreversible dimension is ALSO left genuinely open."""
    t = " " + text.lower() + " "
    stake = next((k for k in _HIGH_STAKES if k in t), None)
    forked = next((k for k in _FORK if k in t), None)
    if stake and forked:
        return f"'{stake}' with an open choice ('{forked.strip()}') — wrong pick is costly/irreversible"
    return None


def detect_ambiguity(prompt: str, goal_present: Optional[bool] = None) -> AmbiguityReport:
    """Classify ambiguity. DEFAULT = reasonable completion (no ask); only a genuine high-stakes fork → S30."""
    text = prompt.lower()
    words = re.findall(r"[a-zA-Z]+", text)
    n = max(len(words), 1)
    vague = [t for t in _VAGUE_DEFAULT if re.search(rf"\b{re.escape(t)}\b", text)]
    vague += [t for t in _OPEN_RANGE if t in text]
    score = len(vague) / n
    fork = _high_stakes_fork(prompt)
    if fork:
        return AmbiguityReport("HIGH_STAKES_FORK", score, vague, fork=fork,
                               detail="costly/irreversible choice left open → escalate to S30 (VoI-gated)")
    if not vague:
        return AmbiguityReport("CLEAR", score, detail="no vague markers — proceed")
    completions = {t: _VAGUE_DEFAULT[t] for t in vague if t in _VAGUE_DEFAULT}
    return AmbiguityReport("MINOR_AMBIGUITY", score, vague, completions,
                           detail="vague but intent clear → reasonable completion + stated assumption (no ask)")
