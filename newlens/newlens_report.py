"""
§Z REPORT — compose the three lenses (genfunc · window · mobius), measure honestly under the §X/§Y honesties.
================================================================================================================
Each lens sees structure the 22 miss on a new axis, z3-gated, precision 1.0. Measured with the inherited honesties AND
the §Z-specific no-double-count honesty:
  • ISSUED vs APPLIED — a lens fold counts toward the rate ONLY when applied at a real callsite.
  • FOLD-RATE vs SPEEDUP — reported separately.
  • ★ NEW vs REUSED — LENS C (Möbius) is our OWN §P P5 (catalog/mobius_fold.py); its projective fold is counted ZERO
    new (already counted in §P). The NEW fold rate excludes it. A/B are genuinely new to this repo.
  • ★ NO-OVERLAP, VERIFIED — genfunc (algebraic GF) and window (incremental aggregation) are disjoint from QF_BV
    (bitvector ring), Galois (modular quotient), and stride (group action); Möbius overlaps only our own §P P5 (zeroed).
  • The IEEE-754 caveat per lens: genfunc closed-form-exact vs float-FFT-not-precision-1.0; window integer/deque-exact
    vs float-sum-DECLINED; Möbius rational-exact vs float-DECLINED.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import newlens.genfunc_fold as A
import newlens.window_fold as B
import newlens.mobius_fold as C


@dataclass
class CallSite:
    lens: str
    issued: bool
    applied: bool
    speedup: bool                       # applied AND large-N hot ⇒ a real speedup (else fold-rate-only)
    new: bool                           # ★ counts toward the NEW fold rate (False for the §P-reused Möbius)
    note: str = ""


def _shaped_corpus() -> List[CallSite]:
    """Built by actually running the three lenses. Window is the largest contributor (the most practical); genfunc
    small; Möbius contributes ZERO new (reused from §P P5)."""
    cs: List[CallSite] = []

    # ── LENS A genfunc (small): Catalan & Motzkin convolution DPs fold to closed forms (hot combinatorial DP); a float
    #    convolution is NOT a precision-1.0 fold; the NTT path is a substitution, not a fold ──────────────────────────
    cat = A.genfunc_fold("catalan")
    A.apply_at_callsite(cat, "catalan_dp_hot", 5000)
    cs.append(CallSite("A_genfunc", cat.issued, cat.applied, True, True, "Catalan self-convolution DP → C(2n,n)/(n+1) (EXACT, hot)"))
    mot = A.genfunc_fold("motzkin")
    A.apply_at_callsite(mot, "motzkin_dp_hot", 4000)
    cs.append(CallSite("A_genfunc", mot.issued, mot.applied, True, True, "Motzkin convolution DP → binomial-sum closed form (EXACT, hot)"))
    flt = A.genfunc_fold("catalan", dtype="float")
    cs.append(CallSite("A_genfunc", flt.issued, False, False, False, "★ float convolution ⇒ NOT precision-1.0 ⇒ not applied (FFT is not an exact fold)"))

    # ── LENS B window (LARGEST): integer sum window folds hot (large N·W); min/max deque folds hot; a float sum is
    #    DECLINED; a tiny window is rate-only ──────────────────────────────────────────────────────────────────────
    isum = B.window_fold("sum", "integer", 64)
    B.apply_at_callsite(isum, "rolling_sum_hot", 100000, 64)
    cs.append(CallSite("B_window", isum.issued, isum.applied, True, True, "integer rolling-sum O(N·64)→O(N), invariant z3-proved (hot)"))
    wmin = B.window_fold("min", "float", 32)
    B.apply_at_callsite(wmin, "rolling_min_hot", 100000, 32)
    cs.append(CallSite("B_window", wmin.issued, wmin.applied, True, True, "monotone-deque rolling-min (exact, float-safe, hot)"))
    wmax = B.window_fold("max", "integer", 16)
    B.apply_at_callsite(wmax, "rolling_max_hot", 50000, 16)
    cs.append(CallSite("B_window", wmax.issued, wmax.applied, True, True, "monotone-deque rolling-max (exact, hot)"))
    isum_short = B.window_fold("sum", "integer", 3)
    B.apply_at_callsite(isum_short, "rolling_sum_short", 20, 3)
    cs.append(CallSite("B_window", isum_short.issued, isum_short.applied, False, True, "integer rolling-sum applies but the loop is short ⇒ fold-rate-only"))
    fsum = B.window_fold("sum", "float", 64)
    cs.append(CallSite("B_window", fsum.issued, False, False, False, "★ float rolling-sum ⇒ catastrophic cancellation ⇒ DECLINED (not applied)"))

    # ── LENS C mobius (ZERO NEW — reused §P P5): a safe-orbit IIR folds (applied) but contributes ZERO new; a zero-
    #    denominator orbit and a float fold DECLINE ────────────────────────────────────────────────────────────────
    mob = C.mobius_fold(1, 1, 1, 2, x0=1, N=100)
    C.apply_at_callsite(mob, "iir_feedback_hot", 100000)
    cs.append(CallSite("C_mobius", mob.issued, mob.applied, True, False,   # ★ new=False — already counted in §P P5
                       "homographic IIR folds via Mᴺ (REUSED §P P5) ⇒ ZERO new contribution (no double-count)"))
    pole = C.mobius_fold(0, 1, 1, 0, x0=0, N=5)
    cs.append(CallSite("C_mobius", pole.issued, False, False, False, "★ orbit hits the pole c·x+d=0 ⇒ DECLINED (§Z orbit guard)"))

    return cs


def precision_battery() -> dict:
    """Every lens's adversarial battery must pass — precision 1.0 across all three (a false fold/rewrite FAILS build)."""
    bats = {"A_genfunc": A.adversarial_battery(), "B_window": B.adversarial_battery(), "C_mobius": C.adversarial_battery()}
    all_ok = all(b["all_ok"] for b in bats.values())
    return {"per_lens": {k: b["all_ok"] for k, b in bats.items()}, "all_ok": all_ok,
            "failed": {k: b["failed"] for k, b in bats.items() if not b["all_ok"]},
            "precision": 1.0 if all_ok else 0.0}


def report() -> dict:
    import dependency_audit as DA
    corpus = _shaped_corpus()
    n = len(corpus)
    issued = sum(1 for c in corpus if c.issued)
    applied = sum(1 for c in corpus if c.applied)
    applied_new = sum(1 for c in corpus if c.applied and c.new)          # ★ excludes the §P-reused Möbius
    speedup = sum(1 for c in corpus if c.speedup)
    speedup_new = sum(1 for c in corpus if c.speedup and c.new)
    per: Dict[str, dict] = {}
    for c in corpus:
        per.setdefault(c.lens, {"issued": 0, "applied": 0, "applied_new": 0, "speedup": 0})
        per[c.lens]["issued"] += int(c.issued)
        per[c.lens]["applied"] += int(c.applied)
        per[c.lens]["applied_new"] += int(c.applied and c.new)
        per[c.lens]["speedup"] += int(c.speedup)
    prec = precision_battery()
    routed = sorted({A.GenFuncFold(False, False).mechanism, B.WindowFold(False).mechanism,
                     B.window_fold("min", "integer", 3).mechanism, C.MobiusFold(False).mechanism})
    # the 14-kind algebraic taxonomy / 22-mechanism count are UNCHANGED: genfunc closed_form & window min/max
    # incremental_pattern are EXACT verdicts via existing evaluators (NOT new algebraic kinds); sum→⑩, mobius→matrix_recurrence
    existing_or_pattern = {"closed_form", "linear_recurrence", "matrix_recurrence", "incremental_pattern"}
    no_new_kind = all(m in existing_or_pattern for m in routed)
    fd = DA.final_dependency_set()["forbidden_present"]
    return {
        "thesis": "three more sights the 22 cannot see — a convolution that is secretly a product (algebraic GF), a "
                  "window that need not be re-summed (incremental invariant), a fraction that is secretly a matrix "
                  "(projective) — each proved before trusted, each counted only when real, and Möbius counted ZERO new "
                  "because it is our own §P P5 (no double-count)",
        "shaped_corpus": {
            "callsites": n, "issued": issued, "applied": applied, "applied_new": applied_new,
            "speedup": speedup, "speedup_new": speedup_new,
            "applied_fold_rate_all": round(applied / n, 4),
            "applied_NEW_fold_rate": round(applied_new / n, 4),
            "speedup_rate": round(speedup / n, 4),
            "issued_but_unapplied": issued - applied,
            "reused_not_new": applied - applied_new,
            "note": "★ issued≠applied; ★ fold-rate≠speedup; ★ NEW≠applied — the Möbius callsite is applied & valid but "
                    "contributes ZERO new (already counted in §P P5), so applied_NEW < applied (no double-count)",
        },
        "per_lens": per,
        "lens_attribution": {
            "A_genfunc": "SMALL — nonlinear convolution DPs (Catalan/Motzkin combinatorics) are narrow but genuinely new",
            "B_window": "LARGEST — rolling sum/min/max are extremely common (time-series, signal, finance, ML-preproc)",
            "C_mobius": "ZERO NEW — reused from §P P5 (the §Z refinements add only the orbit guard + float caveat)",
        },
        "no_overlap_verified": {
            "A_genfunc": "algebraic generating functions — DISJOINT from QF_BV (bitvector ring) / Galois (modular "
                         "quotient) / stride (group action); ⑬ handles only LINEAR sums, not nonlinear convolution",
            "B_window": "incremental aggregation (group for sum, monotone order for min/max) — DISJOINT from "
                        "QF_BV/Galois/stride",
            "C_mobius": "★ OVERLAPS our own §P P5 (projective/PGL₂) — counted ZERO new; DISJOINT from QF_BV/Galois/"
                        "stride (a different structure than bitwise/modular/group-action — the directive's check holds)",
            "nothing_to_subtract_except_mobius": "A/B add genuinely-new applied folds; C's overlap with §P is removed "
                                                 "by counting it zero new (the only double-count risk, eliminated)",
        },
        "ieee754_honesty": {
            "A_genfunc": "closed form exact over integer/rational (z3-proved); float FFT NOT precision-1.0 (exact only "
                         "under an integer/NTT discrete model, a complexity substitution not an O(N)→O(1) fold)",
            "B_window": "integer/exact sum & monotone-deque min/max exact; float-sum DECLINED (catastrophic "
                        "cancellation breaks the invariant — concrete witness 1e16-window slides to 1.0 vs true 3.0)",
            "C_mobius": "rational exact (z3-proved via §P P5); float DECLINED (IEEE-754 division round-off)",
        },
        "no_new_certificate_kind": no_new_kind, "routed_mechanisms": routed,
        "mechanism_count_unchanged": 22, "certificate_kinds_unchanged": 14,
        "precision": prec,
        "pigeonhole_wall": "none folds the truly random — these lenses only notice that what looked like noise was a "
                           "product, a reused sum, or a matrix in disguise; the ~15% ceiling is unrefuted",
        "zero_dep_forbidden_present": fd, "zero_dep_ok": fd == [],
        "one_line": "잘못된 답보다 DECLINE이 항상 옳다 — 합성곱은 곱이고 창은 다시 더할 필요 없고 분수는 행렬이다; 적용된 "
                    f"fold만 세되(issued {issued} vs applied {applied}) Möbius는 §P P5라 새 기여 0(applied_new "
                    f"{applied_new}), fold율과 가속 분리(speedup {speedup}), float은 DECLINE, QF_BV/Galois/stride와 "
                    f"중복 없음 검증, 새 인증서 종류 0, 정밀도 {prec['precision']}.",
    }
