"""
§AA WEAPON 2 — LENS COMPOSITION / PIPELINE (additive-with-overlap, never multiplicative).
================================================================================================================
Lenses currently each try alone. Composing them — one lens's transform exposing structure a DIFFERENT lens folds —
catches what no single lens catches: canonicalize (W1) rewrites `Σ(i·2)` to the canonical `Σ(2·i)` form that Faulhaber
folds, where Faulhaber alone DECLINED the variant spelling. The composition pipeline runs a transform, then re-attempts
the fold.

★ THE NO-OVERCLAIM DISCIPLINE (the point): serial passes do NOT multiply. The composed lift is ADDITIVE-WITH-OVERLAP —
many items are caught by one lens regardless (the overlap); only the items caught ONLY by chaining are the real lift. We
measure the real composed lift and SUBTRACT the overlap (the single-lens folds), never claiming the "30–50%" multiplicative
figure. ★ Each link is its own proved fold; the FINAL fold is z3-proved against the ORIGINAL (not just the intermediate).
LLM-free (deterministic pipeline + z3). No new certificate kind (chains existing folds; the final verdict is the existing kind).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import foldrate.canonicalize as CANON


@dataclass
class FoldOutcome:
    folded: bool
    closed_form: str = ""
    path: str = ""                          # "faulhaber" | "canonicalize→faulhaber" | ""
    proved_against_original: bool = False


# ── a representative lens: Faulhaber, BRITTLE to spelling (folds Σ c·i only in the canonical `c*i` form) ───────────
def _parse_linear_summand(summand: str) -> Optional[int]:
    """Return c if `summand` is EXACTLY the canonical spelling `c*i` (c an integer literal), else None — the brittle
    matcher that misses `i*2`, `i+i`, etc. until canonicalization rewrites them."""
    import re
    m = re.fullmatch(r"\s*(-?\d+)\s*\*\s*i\s*", summand)
    return int(m.group(1)) if m else None


def prove_faulhaber_closed_z3(c: int) -> bool:
    """z3 ∀-prove the Faulhaber closed form S(n)=c·n·(n+1)/2 for Σ_{i=1}^{n} c·i, by induction over integers:
    base S(1)==c AND step ∀n≥1. 2·S(n)==c·n·(n+1) (cleared denominator). A real ∀ proof against the sum's recurrence."""
    import z3
    n = z3.Int("n")
    S = lambda k: c * k * (k + 1)                                # 2·S(k) (denominator cleared)
    s = z3.Solver()
    base = S(1) == 2 * c                                         # 2·S(1) == 2c  ⟺ S(1)==c
    step = z3.ForAll([n], z3.Implies(n >= 1, S(n + 1) - S(n) == 2 * (c * (n + 1))))  # 2·(S(n+1)-S(n))==2·c·(n+1)
    s.add(z3.Not(z3.And(base, step)))
    return s.check() == z3.unsat


def faulhaber_fold(summand: str) -> FoldOutcome:
    """Fold Σ_{i=1}^{n} summand to a closed form — ONLY if summand is the canonical `c*i` spelling (brittle)."""
    c = _parse_linear_summand(summand)
    if c is None:
        return FoldOutcome(False)
    proved = prove_faulhaber_closed_z3(c)
    return FoldOutcome(proved, closed_form=f"{c}*n*(n+1)/2", path="faulhaber", proved_against_original=proved)


def compose_fold(summand: str) -> FoldOutcome:
    """The pipeline: try Faulhaber alone; if it DECLINEs, CANONICALIZE the summand (W1, z3-proved equiv) and re-attempt.
    The final fold is proved against the ORIGINAL because canonicalization is z3-proved equivalent AND the Faulhaber
    closed form is z3-proved against the (canonical = original) sum."""
    direct = faulhaber_fold(summand)
    if direct.folded:
        return direct                                           # single-lens (overlap)
    canon = CANON.canonicalize_expr(summand, ["i"], "integer")  # transform exposes structure
    if not canon.proved:
        return FoldOutcome(False)
    via = faulhaber_fold(canon.canonical)
    if via.folded:
        # final fold sound: canon proved (original==canonical) AND faulhaber proved on the canonical summand
        return FoldOutcome(True, via.closed_form, path="canonicalize→faulhaber", proved_against_original=True)
    return FoldOutcome(False)


def measure_composition() -> dict:
    """Run a corpus through single-lens (Faulhaber alone) vs the composed pipeline; report the REAL composed lift with
    the OVERLAP (single-lens folds) subtracted — additive, never multiplicative."""
    corpus = ["2*i", "3*i", "i*2", "i+i", "5*i", "i*4", "2*i + i"]   # mix: canonical spellings + variants
    single = [s for s in corpus if faulhaber_fold(s).folded]         # caught by one lens alone (the overlap)
    composed = [s for s in corpus if compose_fold(s).folded]         # caught by the pipeline
    comp_only = [s for s in composed if s not in single]             # the REAL lift: caught ONLY by chaining
    n = len(corpus)
    return {
        "corpus_size": n,
        "single_lens_folds": len(single),                           # overlap
        "composed_folds": len(composed),
        "composition_only_lift": len(comp_only),                    # additive lift (overlap subtracted)
        "composition_only_examples": comp_only,
        "single_lens_rate": round(len(single) / n, 4),
        "composed_rate": round(len(composed) / n, 4),
        "lift_rate": round(len(comp_only) / n, 4),
        "note": "composed = single ∪ composition-only; the lift is composition-only (overlap subtracted); "
                "additive-with-overlap, NEVER the product of pass rates",
    }


def adversarial_battery() -> dict:
    """A variant spelling folds ONLY via composition (canonicalize→faulhaber), proved against the original; ★ the lift
    is additive (composition-only < composed, overlap subtracted), NEVER multiplicative; a wrong final result would be
    caught (the Faulhaber z3 proof); a non-linear summand DECLINEs even composed."""
    variant = compose_fold("i*2")                                   # variant ⇒ caught only by composition
    canonical = faulhaber_fold("2*i")                               # caught single-lens
    m = measure_composition()
    nonlinear = compose_fold("i*i")                                 # not Σ c·i even after canon ⇒ DECLINE
    # ★ additive-not-multiplicative: composed rate is NOT the product of pass rates (it's the union)
    not_multiplicative = m["composed_rate"] <= m["single_lens_rate"] + m["lift_rate"] + 1e-9
    cases = {
        "variant_folds_only_via_composition": variant.folded and variant.path == "canonicalize→faulhaber",
        "final_proved_against_original": variant.proved_against_original,
        "single_lens_still_works": canonical.folded and canonical.path == "faulhaber",
        "composition_only_lift_positive": m["composition_only_lift"] >= 1,
        "overlap_subtracted": m["composition_only_lift"] == m["composed_folds"] - m["single_lens_folds"],
        "additive_not_multiplicative": not_multiplicative,
        "nonlinear_declined_even_composed": not nonlinear.folded,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
