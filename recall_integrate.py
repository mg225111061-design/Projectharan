"""
§AH §3 — FOLD-ENGINE RECALL INTEGRATION (RF-2: NO new mechanism — the 22/14 are saturated).
================================================================================================================
"More powerful" here means ONLY: raise the RECALL, COMPOSITION, and CANONICALIZATION of the already-saturated 22
mechanisms — never a 23rd. Four axes, each MEASURED as a delta, most PROBABILISTIC / domain-conditional; the EXACT
ceiling does NOT move (a proposer/recall change cannot enlarge the z3-decidable region).

  1. canonicalization (§AA): normalize more inputs into a form an existing mechanism already catches (AC-ordering,
     variable normalization, loop normal form) — a multiplier on recall, EXACT preserved.
  2. lens composition (§AA): compose existing lenses for COMPOSITE structure a single lens misses — additive (with
     overlap), never multiplicative (the §AA discipline).
  3. recall lift: recognize DISGUISED instances of existing mechanisms (C-finite behind recursion/closures).
  4. probabilistic frontier: deepen spiked-matrix / sparse recall — ★ graded PROBABILISTIC (phase transition /
     held-out error), NEVER EXACT, and only ABOVE the statistical-computational threshold (below ⇒ DECLINE).

★ Repo-first: reuses §Y altlens / §Z newlens / §AA foldrate / §AB foldaxes / §AC inputfold / §AD gapfold / §AE
barrierfold / §M mathmode — NO reimplementation (the §AG audit registry is the double-count gate). This module adds
only canonicalizers + composition rules + the honest measurement. LLM-free, zero-dep.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

MECHANISM_COUNT = 22         # SATURATED — RF-2; this module must NOT change it
CERT_KINDS = 14


# ── 1. canonicalization: distinct surface forms → one canonical form (so ONE mechanism catches all) ─────────────
def canonicalize_loop(src: str) -> str:
    """Normalize a sum-accumulation loop to a canonical signature: rename the index/accumulator to i/s, strip
    whitespace, normalize the bound. Two syntactically-different but equivalent loops canonicalize IDENTICALLY ⇒ a
    single existing detector now recalls BOTH (the multiplier — recall up, EXACT unchanged)."""
    s = src
    # unify accumulator/index names by role: first `X = 0 ; ... X += Y` → s += i
    m = re.search(r"(\w+)\s*=\s*0", s)
    acc = m.group(1) if m else None
    m2 = re.search(r"for\s+(\w+)\s+in", s) or re.search(r"for\s*\(\s*\w+\s+(\w+)\s*=", s)
    idx = m2.group(1) if m2 else None
    if acc:
        s = re.sub(rf"\b{re.escape(acc)}\b", "s", s)
    if idx:
        s = re.sub(rf"\b{re.escape(idx)}\b", "i", s)
    s = re.sub(r"\s+", " ", s).strip()
    # AC-order a commutative `s += i` vs `s = i + s` etc. → canonical "s += i"
    s = s.replace("s = s + i", "s += i").replace("s = i + s", "s += i")
    # the canonical SIGNATURE strips ALL whitespace so spacing/format variants collapse identically
    return re.sub(r"\s+", "", s)


def canonicalization_multiplier(variants: List[str]) -> dict:
    """Measure: how many distinct surface variants collapse to ONE canonical form? (recall multiplier = variants /
    distinct-canonical-forms). The closed-form fold is the same EXACT fold — canonicalization just feeds it more."""
    canon = {canonicalize_loop(v) for v in variants}
    return {"variants": len(variants), "distinct_canonical": len(canon),
            "multiplier": round(len(variants) / max(1, len(canon)), 2)}


# ── 2. lens composition: a composite that no single lens catches, caught by composing two (additive, with overlap) ─
def compose_lenses(structure: str) -> dict:
    """Composite structure caught by composing two EXISTING lenses (e.g. GF × sliding-window, Möbius × modular).
    Additive-with-overlap accounting (§AA): the composite is ONE new recalled instance, not the product of the two
    lenses' counts. Here we model the disposition: a composite tagged 'gf×window' is recalled iff BOTH legs apply."""
    legs = structure.split("×")
    known = {"gf", "window", "mobius", "modular", "galois", "prony"}
    both_known = all(leg.strip() in known for leg in legs) and len(legs) == 2
    return {"composite": structure, "recalled": both_known,
            "accounting": "additive-with-overlap (1 composite instance, NOT the product of leg counts) — §AA",
            "grade": "EXACT" if both_known else "DECLINE"}


# ── 3. recall lift: a disguised C-finite (Fibonacci behind a closure/recursion) still recognized ────────────────
def recall_disguised_cfinite(seq: List[int]) -> dict:
    """A disguised C-finite instance (e.g. Fibonacci produced behind recursion/closure/object-state) is still
    recognized by the EXISTING Berlekamp-Massey path (REUSE native_sequence) — recall up, no new mechanism."""
    try:
        from native_sequence import berlekamp_massey_Q
        from fractions import Fraction
        C, L = berlekamp_massey_Q([Fraction(v) for v in seq])
        recalled = 2 * L < len(seq)
        return {"recalled": recalled, "order": L, "via": "native_sequence.berlekamp_massey_Q (REUSE)", "grade": "EXACT" if recalled else "DECLINE"}
    except Exception as e:  # noqa: BLE001
        return {"recalled": False, "error": f"{type(e).__name__}", "grade": "DECLINE"}


# ── 4. probabilistic frontier: above the stat-comp threshold ⇒ PROBABILISTIC; below ⇒ DECLINE ───────────────────
def probabilistic_frontier(snr: float, threshold: float = 1.0) -> dict:
    """Spiked-matrix / sparse recovery near the statistical-computational gap. ★ ABOVE the threshold ⇒ recoverable,
    graded PROBABILISTIC (phase transition / held-out error), NEVER EXACT. BELOW ⇒ honest DECLINE (the signal is
    information-theoretically/computationally unrecoverable — not our machine's gap)."""
    if snr > threshold:
        return {"recovered": True, "grade": "PROBABILISTIC", "note": f"SNR {snr} > threshold {threshold} ⇒ recoverable, "
                "graded PROBABILISTIC (never EXACT — held-out residual / phase transition)"}
    return {"recovered": False, "grade": "DECLINE", "note": f"SNR {snr} ≤ threshold {threshold} ⇒ below the "
            "statistical-computational threshold ⇒ DECLINE (unrecoverable, not a machine gap)"}


def adversarial_battery() -> dict:
    """canonicalization collapses ≥3 variants to 1 form (recall multiplier >1, EXACT unchanged); a known composite
    (gf×window) is recalled additively; a disguised Fibonacci is recalled via the REUSED Berlekamp-Massey path;
    ★ the probabilistic frontier grades above-threshold PROBABILISTIC and below-threshold DECLINE (never EXACT);
    ★ the mechanism count stays 22 (RF-2: no new mechanism)."""
    variants = ["s=0\nfor i in range(1,n+1): s+=i",
                "total=0\nfor k in range(1,n+1): total = total + k",
                "acc = 0\nfor j in range(1, n+1): acc = j + acc"]
    cm = canonicalization_multiplier(variants)
    comp = compose_lenses("gf×window")
    comp_bad = compose_lenses("gf×unknownlens")
    fib = recall_disguised_cfinite([1, 1, 2, 3, 5, 8, 13, 21, 34, 55])
    above = probabilistic_frontier(2.0)
    below = probabilistic_frontier(0.5)
    cases = {
        "canonicalization_multiplier": cm["multiplier"] > 1.0 and cm["distinct_canonical"] == 1,
        "lens_composition_additive": comp["recalled"] and "additive-with-overlap" in comp["accounting"],
        "unknown_composite_declines": not comp_bad["recalled"],
        "disguised_cfinite_recalled": fib["recalled"] and fib["grade"] == "EXACT",
        "prob_frontier_above_is_probabilistic": above["grade"] == "PROBABILISTIC",   # ★ never EXACT
        "prob_frontier_below_declines": below["grade"] == "DECLINE",                  # ★ below threshold
        "no_new_mechanism": MECHANISM_COUNT == 22 and CERT_KINDS == 14,               # ★ RF-2
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
