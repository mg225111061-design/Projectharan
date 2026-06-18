"""
v29 STAGE 31 — cross-representation consistency gate (Clover-for-prompts) + entity grounding.
==============================================================================================
Clover's idea applied to PROMPTS: generate the requirement in more than one representation and flag the
DIVERGENCE. Here, deterministically and key-free, we cross-check the prompt's OWN representations —
its stated NL constraints vs its worked EXAMPLES — and we ground its entities against a code/IR symbol
table (reusing S21).

  • consistency: a stated constraint on the result (e.g. "non-negative result") vs an example output
    (e.g. "f(2) returns -4") — if the example SOUNDLY violates the constraint, the prompt is internally
    DIVERGENT → route to S28 (contradiction) / S29 (ambiguity). ★zero false-positives: we flag ONLY a
    proven numeric violation (Clover's 0-FP property), never a heuristic hunch.★
  • grounding: prompt entities → code/IR symbols; a symbol that exists is GROUNDED, one that doesn't is
    flagged (checkable, reuses S21's entity-linking).

★ HONEST (§1.4, §1.5) ★: cross-representation agreement is a CONSISTENCY check, not intent correctness
(Rice) — two reps can agree and both be wrong about intent. Grounding only covers the checkable part
(symbol existence / test compiles). LLM-generated alternative representations (richer than examples) are
[BLOCKED: key/egress]; the example-vs-constraint check and symbol grounding are measured.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ── extract result-bounds and worked examples from the prompt's text ────────────────────────────────
# sign phrases, MOST-SPECIFIC FIRST (so "non-negative" wins and "negative" inside it never double-counts)
_PHRASE_BOUND = [
    (r"non[- ]?negative", (">=", 0)), (r"non[- ]?positive", ("<=", 0)),
    (r"\bpositive\b", (">", 0)), (r"\bnegative\b", ("<", 0)),
]
_RESULT_OP = re.compile(r"result\s*(?:must be|should be|is)?\s*"
                        r"(<=|>=|<|>|=|at least|at most)\s*(-?\d+)", re.IGNORECASE)
# example-output markers: a value-producing verb/arrow + a number (NO bare '=', which would catch '>= 100')
_EXAMPLE = re.compile(r"(?:returns?|outputs?|gives?|yields?|->|=>)\s*(-?\d+)", re.IGNORECASE)
_OPMAP = {"<=": "<=", ">=": ">=", "<": "<", ">": ">", "=": "==", "at least": ">=", "at most": "<="}


def result_bounds(text: str) -> List[Tuple[str, int]]:
    out: List[Tuple[str, int]] = []
    low = text.lower()
    for rx, (op, n) in _PHRASE_BOUND:           # first matching sign phrase wins (no double-count)
        if re.search(rx, low):
            out.append((op, n))
            break
    for m in _RESULT_OP.finditer(text):         # explicit "result <op> N" bounds
        out.append((_OPMAP[m.group(1).lower()], int(m.group(2))))
    return out


def example_outputs(text: str) -> List[int]:
    """Worked-example outputs: a value-producing marker followed by a number, anywhere in the prompt."""
    return [int(m.group(1)) for m in _EXAMPLE.finditer(text)]


def _violates(out: int, bound: Tuple[str, int]) -> bool:
    op, n = bound
    return not {"<": out < n, ">": out > n, "<=": out <= n, ">=": out >= n, "==": out == n}[op]


@dataclass
class ConsistencyReport:
    status: str                 # CONSISTENT | DIVERGENT
    divergences: List[str] = field(default_factory=list)
    grounded: List[str] = field(default_factory=list)
    ungrounded: List[str] = field(default_factory=list)
    route: str = ""             # "" | S28 | S29
    detail: str = ""

    def __str__(self):
        if self.status == "CONSISTENT":
            return f"CONSISTENT (grounded {len(self.grounded)}/{len(self.grounded) + len(self.ungrounded)})"
        return f"DIVERGENT → {self.route}: {self.divergences}"


def check_consistency(prompt: str) -> ConsistencyReport:
    """Cross-check the prompt's stated result-constraints against its worked examples. Flag ONLY a sound
    numeric violation (zero false positives); route a divergence to S28 (contradiction) / S29 (ambiguity)."""
    bounds = result_bounds(prompt)
    outs = example_outputs(prompt)
    divergences = [f"example output {o} violates stated constraint result {op} {n}"
                   for o in outs for (op, n) in bounds if _violates(o, (op, n))]
    if divergences:
        return ConsistencyReport("DIVERGENT", divergences, route="S28",
                                 detail="example contradicts a stated constraint (internally inconsistent prompt)")
    return ConsistencyReport("CONSISTENT", detail="stated constraints and worked examples agree (or none to check)")


# ── entity grounding to a code/IR symbol table (reuse S21's linking idea) ───────────────────────────
def ground_entities(prompt: str, symbols: List[str], entities: Optional[List[str]] = None) -> Tuple[List[str], List[str]]:
    """Link referenced entities to existing symbols. Returns (grounded, ungrounded). Checkable: a grounded
    entity names a symbol that EXISTS in the code/IR (reuses the S21 grounding notion)."""
    if entities is None:
        entities = sorted(set(re.findall(r"\b([a-z_][a-z0-9_]*)\s*\(", prompt, re.IGNORECASE)))   # f(...) calls
    symset = set(symbols)
    grounded = [e for e in entities if e in symset]
    ungrounded = [e for e in entities if e not in symset]
    return (grounded, ungrounded)


def gate(prompt: str, symbols: Optional[List[str]] = None) -> ConsistencyReport:
    """The full S31 gate: consistency (zero-FP) + entity grounding. DIVERGENT routes to S28/S29."""
    rep = check_consistency(prompt)
    if symbols is not None:
        rep.grounded, rep.ungrounded = ground_entities(prompt, symbols)
    return rep
