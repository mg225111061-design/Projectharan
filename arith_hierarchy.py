"""
ARITHMETIC-HIERARCHY routing probe (Constitution §4.8/§5, mechanism 9). The cheapest §5 router signal: place a
request in the arithmetic hierarchy — Δ⁰₀ (decidable, bounded quantifiers) / Σ⁰₁ (r.e., "∃ a halting run") / Π⁰₁
(co-r.e., "∀ inputs …") / Σ⁰₂+ — and route accordingly:
  • Δ⁰₀ / decidable                          → PROCEED to the mechanisms;
  • Σ⁰₁- or Π⁰₁-COMPLETE semantic-program-property (Rice) → DECLINE (an obstruction, mechanism 14);
  • otherwise                                → PROCEED (let the mechanisms try; honest about being a heuristic).
This is a CHEAP, HONEST heuristic placement (not a decision of the hierarchy itself, which is undecidable). It feeds
`catalog.compose` BEFORE the mechanism probe vector (§5 ordering).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from mechanisms.base import feats

# Σ⁰₁ / Π⁰₁-complete semantic properties of PROGRAMS (Rice) — undecidable ⇒ route DECLINE
_UNDECIDABLE = re.compile(
    r"\b(halt|halting|terminate[s]?|diverge|for (all|every) (input|program)s?|on all inputs|"
    r"semantically equivalent|always (return|output|halt|terminate)|computes the same|is total|"
    r"reachab(le|ility)|never (crashes|errors))\b", re.IGNORECASE)
# Δ⁰₀ / decidable markers: bounded / finite / quantifier-free / explicit decision procedures
_DECIDABLE = re.compile(
    r"\b(bounded|finite|presburger|real[- ]closed|polynomial (in|ideal|inequality)|quantifier[- ]free|"
    r"linear (arithmetic|program)|sos|sum of squares|primality|gcd|matrix|eigen|closed[- ]form|modular)\b",
    re.IGNORECASE)


@dataclass
class Placement:
    level: str          # "Δ⁰₀" | "Σ⁰₁" | "Π⁰₁" | "Σ⁰₂+" | "unknown"
    route: str          # "PROCEED" | "DECLINE"
    reason: str
    decidable: bool


def classify(x) -> Placement:
    """Heuristic arithmetic-hierarchy placement of a request (cheap, µs). Honest: a placement, not a decision."""
    t = feats(x).text
    if _UNDECIDABLE.search(t):
        # a non-trivial semantic property of programs sits at Σ⁰₁/Π⁰₁ and is Rice-undecidable
        lvl = "Π⁰₁" if re.search(r"for (all|every)|on all|always|is total", t, re.IGNORECASE) else "Σ⁰₁"
        return Placement(lvl, "DECLINE", "non-trivial semantic property of programs (Rice; undecidable)", False)
    if _DECIDABLE.search(t):
        return Placement("Δ⁰₀", "PROCEED", "bounded / quantifier-free / explicit decision procedure (decidable)", True)
    return Placement("unknown", "PROCEED", "no hierarchy marker — proceed to the mechanism probe (heuristic)", False)
