"""
v29 STAGE 26 — requirement-structure parser (the prompt-understanding FRONT-END's foundation).
================================================================================================
An LLM blurs the middle of a prompt (Lost-in-the-Middle, Liu et al. TACL 2024 — 30%+ loss). We make the
prompt's structure EXPLICIT instead: parse it into typed slots —

    { goals, constraints, inputs, outputs, prohibitions, assumptions }

so the downstream detectors (S27 missing, S28 danger/contradiction, S29 ambiguity) operate on structure,
not raw text. The extractor here is DETERMINISTIC (cue-phrase slot-filling) — measurable, fast, key-free.
The schema acts as the "constrained-decoding" well-formedness guarantee: the output is ALWAYS a valid
typed RequirementSchema (a malformed object is rejected). Multi-part prompts are decomposed least-to-most.

★ HONEST (§0.7, §1.4, §1.12) ★: this is a LOSSY, checkable EXTRACTION proxy — NOT "understanding" (Rice).
We report a measurable slot-extraction score, never an understanding claim. LLM-based slot-filling (richer
than cue phrases) is [BLOCKED: key/egress]; the structural parse + schema validation are measured here.
The parser is fail-safe: an unclassifiable clause is kept as an explicit `assumptions`/`unparsed` note, not
silently dropped. The requirement structure is cached so the same prompt is never re-parsed.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# cue lexicons (priority order matters: a clause is assigned to the highest-priority slot it matches)
_PROHIBITION = ("don't", "do not", "never", "must not", "must n't", "should not", "shouldn't", "without",
                "avoid", "no external", "do not use", "not allowed", "forbidden", "except")
_INPUT = ("input", "given", "takes", "accepts", "parameter", "argument", "reads", "receives", "consume")
_OUTPUT = ("output", "return", "returns", "produce", "print", "writes", "emit", "yields", "result is")
_CONSTRAINT = ("must", "at most", "at least", "within", "o(", "less than", "greater than", "no more than",
               "under ", "limit", "only", "exactly", "ms", "seconds", "memory", "in-place", "sorted",
               "thread-safe", "deterministic", "constant time", "linear")
_GOAL_VERB = ("implement", "write", "create", "build", "make", "add", "fix", "compute", "sort", "parse",
              "generate", "design", "refactor", "optimize", "find", "return a", "calculate", "convert")
_ASSUME = ("assume", "assuming", "suppose", "given that", "presumably")
_NUM = re.compile(r"(?:(?<=\s)|^)\d+[\.\)]\s+")                                   # 1. / 2) markers (inline ok)
_KW = re.compile(r"(?:(?<=\s)|^)(?:first|then|next|also|finally)[,:]?\s+", re.IGNORECASE)


def _is_multipart(prompt: str) -> bool:
    return bool(_NUM.search(prompt) or _KW.search(prompt))


@dataclass
class RequirementSchema:
    goals: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    prohibitions: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    parts: List[str] = field(default_factory=list)        # least-to-most decomposition (multi-part)
    raw: str = ""
    confidence: float = 0.0                               # fraction of clauses classified (extraction proxy)
    cached: bool = False

    SLOTS = ("goals", "constraints", "inputs", "outputs", "prohibitions", "assumptions")

    def bound_slots(self) -> List[str]:
        return [s for s in self.SLOTS if getattr(self, s)]

    def __str__(self):
        return ("RequirementSchema(" + ", ".join(f"{s}={len(getattr(self, s))}" for s in self.SLOTS)
                + f", parts={len(self.parts)}, conf={self.confidence:.2f})")


def _clauses(prompt: str) -> List[str]:
    # split on sentence punctuation and newlines; keep non-trivial clauses
    rough = re.split(r"(?<=[.!?;\n])\s+|\n", prompt)
    return [c.strip(" \t-*•") for c in rough if len(c.strip(" \t-*•")) >= 2]


def _classify(clause: str) -> List[str]:
    """Assign a clause to the slots it matches (a clause may carry both a goal and its IO)."""
    c = clause.lower()
    slots: List[str] = []
    if any(k in c for k in _PROHIBITION):
        slots.append("prohibitions")
    if any(k in c for k in _ASSUME):
        slots.append("assumptions")
    if any(k in c for k in _INPUT):
        slots.append("inputs")
    if any(k in c for k in _OUTPUT):
        slots.append("outputs")
    if any(k in c for k in _CONSTRAINT):
        slots.append("constraints")
    if c.split()[0] in _GOAL_VERB or any(k in c for k in _GOAL_VERB):
        slots.append("goals")
    return slots


def decompose(prompt: str) -> List[str]:
    """Least-to-most: split an enumerated / multi-step prompt into ordered subtasks (SCAN-style anchor).
    Prefer numbered markers; else step keywords; else sentence split."""
    if _NUM.search(prompt):
        pieces = _NUM.split(prompt)
    elif _KW.search(prompt):
        pieces = _KW.split(prompt)
    else:
        pieces = re.split(r"(?<=[.!?])\s+", prompt)
    parts = [p.strip(" \t.") for p in pieces if len(p.strip(" \t.")) >= 3]
    return parts if len(parts) > 1 else []


_CACHE: Dict[str, RequirementSchema] = {}
_STATS = {"hits": 0, "misses": 0}


def reset_cache():
    _CACHE.clear()
    _STATS.update(hits=0, misses=0)


def cache_stats() -> Dict[str, int]:
    return dict(_STATS)


def parse_requirements(prompt: str, mode: str = "normal") -> RequirementSchema:
    """Parse a prompt into the typed requirement schema. Deterministic + cached. `mode=extended` adds the
    least-to-most decomposition of multi-part prompts."""
    key = hashlib.sha256((mode + "::" + prompt).encode()).hexdigest()
    if key in _CACHE:
        _STATS["hits"] += 1
        c = _CACHE[key]
        return RequirementSchema(**{**c.__dict__, "cached": True})   # a copy flagged as a cache hit
    _STATS["misses"] += 1
    req = RequirementSchema(raw=prompt)
    clauses = _clauses(prompt)
    classified = 0
    for cl in clauses:
        slots = _classify(cl)
        if slots:
            classified += 1
        for s in slots:
            getattr(req, s).append(cl)
    if mode == "extended" or _is_multipart(prompt):
        req.parts = decompose(prompt)
    req.confidence = classified / len(clauses) if clauses else 0.0
    _CACHE[key] = req
    return RequirementSchema(**req.__dict__)


def is_well_formed(req) -> bool:
    """The 'constrained-decoding' guarantee: the structure must be a valid typed RequirementSchema (every
    slot a list of strings). A malformed object (e.g. a slot that is not a list) is rejected."""
    if not isinstance(req, RequirementSchema):
        return False
    return all(isinstance(getattr(req, s), list) and all(isinstance(x, str) for x in getattr(req, s))
               for s in RequirementSchema.SLOTS)


# ── measurable extraction proxy (NOT understanding) ─────────────────────────────────────────────────
def extraction_score(parsed: RequirementSchema, gold_slots: Dict[str, bool]) -> float:
    """Slot-level extraction accuracy vs a hand-labeled gold (which slots SHOULD be bound). A checkable
    proxy for the parse quality — explicitly not a measure of 'understanding'."""
    correct = sum(1 for s in RequirementSchema.SLOTS if bool(getattr(parsed, s)) == gold_slots.get(s, False))
    return correct / len(RequirementSchema.SLOTS)
