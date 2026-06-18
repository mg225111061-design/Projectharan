"""
v32 STAGE C — meta-dispatcher + MEASURED coverage (baseline vs now), held out, with an Amdahl note.
====================================================================================================
Routes a deferred loop to the technique its category needs, ALWAYS behind that technique's own SOUND
verifier, then folds or defers honestly. The headline number — fold coverage baseline (current engine)
vs now (with A / B1 / B2) — is MEASURED on the fixed defer corpus, never estimated. Clock C (folds) and
Clock B (ABFT verification) are reported SEPARATELY and never mixed.

  C.1 dispatch : category → technique → sound verify → FOLDED | DEFER (informative).
  C.2 measure  : baseline M/N → now M'/N, per category + overall, on ALL and on the HELD-OUT split.
  C.3 amdahl   : a local fold dominates wall-clock only if the loop is the bottleneck — stated, not assumed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import abft as AB
import benortiwari as BT
import fold_kernels as FK
import kovacic as K
import q_fold as Q
import defer_corpus as DC


@dataclass
class DispatchResult:
    cid: str
    category: str
    technique: str              # kovacic | ben-or-tiwari | q-gosper | existing-engine | abft | none
    status: str                 # FOLDED | DEFER | VERIFIED_B (Clock-B verification handled)
    clock: str                  # C | B
    verified: bool
    cert_type: str = "—"
    closed_form: str = "—"
    detail: str = ""


def dispatch(case) -> DispatchResult:
    """C.1 — route a case to its technique (sound-gated) and return the fold/defer verdict."""
    cat = case.category
    if cat == "ode":
        v = K.kovacic_decide(case.meta["p"], case.meta["q"])
        folded = (v.status == "FOLDED")
        return DispatchResult(case.cid, cat, "kovacic", "FOLDED" if folded else "DEFER", "C",
                              verified=v.verified_exact, cert_type=v.cert_type if folded else "—",
                              closed_form=v.closed_form, detail=v.detail)
    if cat == "multivariate-poly":
        r = BT.recover(case.naive, len(case.arg_spec))
        folded = (r.status == "FOLDED")
        return DispatchResult(case.cid, cat, "ben-or-tiwari", "FOLDED" if folded else "DEFER", "C",
                              verified=r.verified, cert_type=r.cert_type if folded else "—",
                              closed_form=r.poly_str, detail=r.detail)
    if cat == "q-holonomic":
        v = Q.q_fold(case.meta["qterm"])
        folded = (v.status == "FOLDED")
        return DispatchResult(case.cid, cat, "q-gosper", "FOLDED" if folded else "DEFER", "C",
                              verified=v.verified, cert_type=v.cert_type if folded else "—",
                              closed_form=v.closed_form, detail=v.detail)
    if cat == "linear-algebra":
        mm = AB.measure_abft(dim=case.meta["dim"])
        ok = mm.error_caught_checksum and mm.error_caught_freivalds and mm.checksum_speedup > 1.0
        return DispatchResult(case.cid, cat, "abft", "VERIFIED_B" if ok else "DEFER", "B",
                              verified=ok, cert_type="probabilistic+exact",
                              detail=f"[Clock B] checksum {mm.checksum_speedup}× / Freivalds {mm.freivalds_speedup}× "
                                     f"(ε≤{mm.freivalds_error_prob:.0e}); COMPUTE unchanged")
    # combinatorial / blackbox → existing sound engine (Faulhaber/Gosper/C-finite)
    if case.haran:
        fv = FK.fold_certificate(case.haran)
        folded = (fv.status == "FOLDED")
        return DispatchResult(case.cid, cat, "existing-engine", "FOLDED" if folded else "DEFER", "C",
                              verified=folded, cert_type="exact" if folded else "—",
                              closed_form=fv.closed_form, detail=fv.reason or fv.certificate)
    return DispatchResult(case.cid, cat, "none", "DEFER", "C", verified=False,
                          detail="no applicable technique — HONEST_DEFER")


# ─────────────────────────────────────────────────────── C.2 — the headline measurement
@dataclass
class Coverage:
    n_clockC: int
    baseline_folded: int
    now_folded: int
    baseline_rate: float
    now_rate: float
    per_category: dict          # cat -> {baseline, now, n}
    false_folds: int            # FOLDED on an expect="defer" case — MUST be 0
    clockB_handled: int
    clockB_n: int
    split: str

    def summary(self) -> str:
        return (f"[Clock C] fold coverage {self.split}: baseline {self.baseline_folded}/{self.n_clockC} "
                f"({self.baseline_rate:.0%}) → now {self.now_folded}/{self.n_clockC} ({self.now_rate:.0%}); "
                f"false-folds={self.false_folds}; [Clock B] {self.clockB_handled}/{self.clockB_n} matmul verified")


def measure_coverage(split: Optional[str] = None) -> Coverage:
    """C.2 — MEASURED baseline (current engine) vs now (dispatcher with A/B1/B2) on the fixed corpus.
    Clock C only for the fold rate; linear-algebra (Clock B) counted separately. Reports false folds (=0)."""
    cases = [c for c in DC.load() if (split is None or c.split == split)]
    clock_c = [c for c in cases if c.category in DC.CLOCK_C_CATS or c.category == DC.NEGATIVE_CONTROL_CAT]
    clock_b = [c for c in cases if c.category in DC.CLOCK_B_CATS]
    per: dict = {}
    base_tot = now_tot = false_folds = 0
    for cat in sorted({c.category for c in clock_c}):
        cc = [c for c in clock_c if c.category == cat]
        b = sum(1 for c in cc if DC.current_engine_folds(c))
        nf = 0
        for c in cc:
            r = dispatch(c)
            if r.status == "FOLDED":
                nf += 1
                if c.expect == "defer":
                    false_folds += 1                  # ★ a fold on a negative control = FALSE STRUCTURE ★
        per[cat] = {"baseline": b, "now": nf, "n": len(cc)}
        base_tot += b
        now_tot += nf
    n = len(clock_c)
    cb_handled = sum(1 for c in clock_b if dispatch(c).status == "VERIFIED_B")
    return Coverage(n_clockC=n, baseline_folded=base_tot, now_folded=now_tot,
                    baseline_rate=round(base_tot / n, 3) if n else 0.0,
                    now_rate=round(now_tot / n, 3) if n else 0.0, per_category=per,
                    false_folds=false_folds, clockB_handled=cb_handled, clockB_n=len(clock_b),
                    split=split or "all")


# ─────────────────────────────────────────────────────── C.3 — Amdahl honesty
def amdahl_overall_speedup(local_speedup: float, fraction_in_loop: float) -> float:
    """Overall wall-clock speedup when a fold gives `local_speedup` on a loop that is `fraction_in_loop` of
    runtime: 1 / ((1-f) + f/s). A huge local fold barely helps end-to-end if the loop isn't the bottleneck."""
    f, s = fraction_in_loop, max(local_speedup, 1e-9)
    return 1.0 / ((1 - f) + f / s)


def amdahl_note(local_speedup: float = 100.0) -> dict:
    """An HONEST Amdahl table: the same fold (local_speedup×) yields very different END-TO-END speedups
    depending on how much of the wall-clock is actually in the folded loop. Folds dominate only when the
    loop dominates AND n is large; otherwise the headline is the LOCAL (Clock C) speedup, not end-to-end."""
    rows = {f"{int(f*100)}%_in_loop": round(amdahl_overall_speedup(local_speedup, f), 2)
            for f in (0.1, 0.5, 0.9, 0.99)}
    return {"local_speedup": local_speedup, "overall_by_loop_fraction": rows,
            "note": "a local fold dominates wall-clock ONLY if the loop is the bottleneck (Amdahl); "
                    "we report the LOCAL Clock-C speedup, not an end-to-end claim, unless the loop dominates"}
