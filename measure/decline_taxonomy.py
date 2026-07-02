"""
§AK §3 — DECLINE REASON TAXONOMY: a MAP of "what we can't fold and why" (the real output of the measurement).
================================================================================================================
★ M-2: the fold rate matters less than the DISTRIBUTION of what does NOT fold. Each DECLINE is tagged with a
PROVEN_BOUNDARIES class. If classes A–E/H dominate, the floor is REAL (the mathematics, not a bug — those will never
fold). If ★R dominates, that is RECALL HEADROOM — foldable code the engine didn't see (the §4 near-miss hunter proves
R by actually folding it; the taxonomy here assigns A–I or UNCLASSIFIED from the engine's own decline signals).

Classes (PART-1 characterization, mapped from the signals the adapter already captured — no engine change):
  A undecidable          — halting/Rice, Hilbert-10 (nonlinear integer), Galois impossibility
  B non-computable       — Kolmogorov-random (no model beats the literal)
  C information floor Ω(N)— true randomness / CSPRNG / one-way hash (the §AJ precheck's random-oracle signature)
  D computationally hard  — statistical-computational gap, PPAD, meta-barriers
  E no closed form        — turbulence / chaos / volume-law (iterated nonlinear dynamics)
  F z3 wall               — transcendental (exp/sin/log), IEEE-754 reassociation, NIA/Skolem, non-holonomic
  G asymptotic/avg/dist   — random-matrix / ergodic / statistical-mechanics laws (never EXACT)
  H physical floor        — I/O, encoding/serialization, RTT, kernel crossings
  I data-dependent flow   — the input decides the branch (control flow, not arithmetic)
  R recall gap (★)        — DEMONSTRABLY foldable but the engine missed it (assigned by §4 near-miss, NOT here)
  UNCLASSIFIED            — declined but no proven boundary applies and no fold demonstrated (honest — never forced)

★ Honesty: we do NOT force a class. When the signals are ambiguous the verdict is UNCLASSIFIED, and §4 decides whether
it is actually R. Assigning A–E to something that secretly folds would HIDE recall headroom — the opposite of the goal.
"""
from __future__ import annotations

from typing import Tuple

CLASS_NAMES = {
    "A": "undecidable", "B": "non-computable", "C": "information-floor", "D": "computationally-hard",
    "E": "no-closed-form", "F": "z3-wall", "G": "asymptotic-avg-dist", "H": "physical-floor",
    "I": "data-dependent-control-flow", "R": "recall-gap", "UNCLASSIFIED": "unclassified",
}


def classify_decline(reason_signals: dict) -> Tuple[str, str, str]:
    """Map the adapter's captured DECLINE signals to a PROVEN_BOUNDARIES class. Priority = most decisive first. Returns
    (class_letter, class_name, why). Never returns R (that is §4's job) — ambiguous ⇒ UNCLASSIFIED (honest)."""
    s = reason_signals or {}
    lift_reason = (s.get("lift_reason") or "").lower()
    boundary = (s.get("boundary") or "").lower()
    dispatch = (s.get("dispatch_detail") or "").lower()

    # ── B/C: the proven-boundary guard fired, or the §AJ precheck saw the random-oracle signature ──
    if "incompressible" in boundary or "kolmogorov" in boundary or "no model beats the literal" in boundary:
        return "B", CLASS_NAMES["B"], "MDL/incompressibility guard fired — no model beats the literal"
    if "undecidable" in boundary or "rice" in boundary or "halting" in boundary:
        return "A", CLASS_NAMES["A"], "Rice/halting boundary guard fired — undecidable semantic property"
    if s.get("precheck_skip") == "random-oracle" or s.get("has_hash_or_random"):
        return "C", CLASS_NAMES["C"], "random / CSPRNG / one-way hash — information floor Ω(N) (no recurrence to recover)"

    # ── F: the z3 wall — transcendental functions / floating-point iteration ──
    if s.get("has_transcendental"):
        return "F", CLASS_NAMES["F"], "transcendental (exp/sin/log/sqrt) — outside the decidable z3 fragments"

    # ── E: iterated nonlinear (float) dynamics — chaos / no closed form ──
    if s.get("has_float") and s.get("has_loop"):
        return "E", CLASS_NAMES["E"], "iterated nonlinear/float dynamics — no exact closed form (chaos/round-off)"

    # ── H: physical floor — I/O and serialization ──
    if s.get("has_io"):
        return "H", CLASS_NAMES["H"], "I/O / serialization (json/os/socket/open) — a physical boundary, not arithmetic"

    # ── I: data-dependent control flow — the input decides the branch ──
    if s.get("has_data_branch"):
        return "I", CLASS_NAMES["I"], "data-dependent control flow — the input chooses the branch (not a recurrence)"

    # ── honest fallback: declined, but no proven boundary applies and no fold demonstrated ──
    return "UNCLASSIFIED", CLASS_NAMES["UNCLASSIFIED"], \
        f"declined with no decisive boundary signal (lift: {lift_reason[:40]} / dispatch: {dispatch[:40]}) — §4 decides R"


def tally(results) -> dict:
    """Tally DECLINE classes over a list of AdapterResults (only the DECLINE ones). Returns {class: count} + percents."""
    from measure import engine_adapter as EA
    counts = {k: 0 for k in CLASS_NAMES}
    declines = [r for r in results if r.classification == EA.DECLINE]
    for r in declines:
        cls, _, _ = classify_decline(r.reason_signals)
        counts[cls] += 1
    total = len(declines) or 1
    pct = {k: round(100 * v / total, 1) for k, v in counts.items() if v}
    return {"total_declines": len(declines), "counts": {k: v for k, v in counts.items() if v}, "percent": pct}


def adversarial_battery() -> dict:
    """★ each signal maps to its boundary class: hash⇒C, transcendental⇒F, I/O⇒H, data-branch⇒I, float-loop⇒E; ★ an
    ambiguous decline ⇒ UNCLASSIFIED (never force a class — that would hide recall headroom)."""
    c = classify_decline({"has_hash_or_random": True})[0]
    f = classify_decline({"has_transcendental": True})[0]
    h = classify_decline({"has_io": True})[0]
    i = classify_decline({"has_data_branch": True})[0]
    e = classify_decline({"has_float": True, "has_loop": True})[0]
    b = classify_decline({"boundary": "incompressible in the MDL/zlib class"})[0]
    unc = classify_decline({"has_loop": True})[0]          # data loop, no decisive signal ⇒ UNCLASSIFIED
    cases = {
        "hash_is_C": c == "C", "transcendental_is_F": f == "F", "io_is_H": h == "H",
        "data_branch_is_I": i == "I", "float_loop_is_E": e == "E", "incompressible_is_B": b == "B",
        "ambiguous_is_unclassified": unc == "UNCLASSIFIED",     # ★ never force a class
        "never_returns_R_here": all(x != "R" for x in (c, f, h, i, e, b, unc)),  # ★ R is §4's job only
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
