"""
§P — THE AUGMENTED DETECTOR + per-priority RE-MEASUREMENT harness (detector RECALL, precision unchanged).
================================================================================================================
`detect(src)` is the detector with its eyes opened: it tries the white-box lifter FIRST (the existing path), then
each recall fallback in priority order. Every fallback carries its own EXACT proof — so widening what is ATTEMPTED
never widens what is wrongly ACCEPTED. The fallbacks route ONLY to EXISTING certificate kinds (linear_recurrence,
gosper_antidifference, …); no 23rd mechanism is introduced.

`measure_corpus(corpus)` runs the SAME deterministic classification as fold_coverage_production but through `detect`,
so the production fold fraction can be re-measured after each priority — the gain (or its honest absence) is measured.
The fixed PRODUCTION_BACKEND_CORPUS_v1 (the 5.7%→8.6% baseline) is reused unchanged; a separate disguise/structure
corpus (in recall_report) demonstrates the recall on the shapes the research identified as common-but-missed.
"""
from __future__ import annotations

import ast
from typing import Callable, Dict, List, Optional

import kernel_verdict as KV


def _defname(src: str) -> Optional[str]:
    try:
        tree = ast.parse(src.strip())
    except SyntaxError:
        return None
    fn = next((n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))), None)
    return fn.name if fn else None


def _arity(src: str, name: str) -> int:
    try:
        tree = ast.parse(src.strip())
    except SyntaxError:
        return -1
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name:
            a = n.args
            return len(a.args) + len(a.kwonlyargs)
    return -1


def detect(src: str) -> KV.Verdict:
    """The augmented detector: white-box lifter → structure recognizer → lazy-decline (telescoping + periodic/mod-k)
    → black-box (representational disguise). Returns the FIRST exact fold, else an honest DECLINE. Each step is
    proof-gated (precision 1.0); the fallbacks fire only when the prior steps DECLINE."""
    # 1) existing white-box verified lifter
    try:
        import catalog.lift as LIFT
        v = LIFT.lift_grade({"lift_code": src, "hot": True, "reused": True})
        if v.status == KV.EXACT:
            return v
    except Exception:  # noqa: BLE001
        pass
    # 2) existing structure recognizer (closed-form loop / relational, etc.)
    try:
        import structure_recognizer as SR
        d = SR.dispatch(src)
        if getattr(d, "status", "") == "OFFLOADED" and getattr(d, "closed_form", ""):
            cert = KV.Cert(KV.EXACT, "structure_recognizer", passed=True, check_cost="differential-gated dispatch",
                           detail=f"structure_recognizer fold: {getattr(d, 'closed_form', '')}")
            return KV.exact({"via": "structure_recognizer"}, "recall_detect", "structure_recognizer", cert)
    except Exception:  # noqa: BLE001
        pass
    # 2.5) P4 bitvector-ring: affine Z_2^w state-advance loops (LCG / checksum) — QF_BV matrix-power
    try:
        import catalog.bitvector_ring as BVR
        if ("% (2" in src or "%(2" in src or "&" in src) and "*" in src:
            v = BVR.bitvector_ring_grade(src, label="recall_detect")
            if v.status == KV.EXACT:
                return v
    except Exception:  # noqa: BLE001
        pass
    # 3) P2 lazy-decline: telescoping (Gosper ⑫) + periodic/mod-k partial sums (C-finite via black-box ⑪)
    try:
        import catalog.lazy_decline as LD
        v = LD.lazy_decline_grade(src, label="recall_detect")
        if v.status == KV.EXACT:
            return v
    except Exception:  # noqa: BLE001
        pass
    # 3.5) P3 holonomic-sum face of ⑬: nested 2-variable definite sums Σ_k F(n,k) (binomial / DP-fill)
    try:
        import catalog.holonomic_sum as HS
        v = HS.holonomic_sum_grade(src, label="recall_detect")
        if v.status == KV.EXACT:
            return v
    except Exception:  # noqa: BLE001
        pass
    # 4) P1 black-box on the whole function (representational disguise: recursion/closure/CPS/…)
    try:
        import catalog.blackbox_fallback as BB
        name = _defname(src)
        if name and _arity(src, name) == 1:
            v = BB.blackbox_grade({name: src}, name, label="recall_detect")
            if v.status == KV.EXACT:
                return v
    except Exception:  # noqa: BLE001
        pass
    return KV.decline("recall_detect: no white-box, structure, telescoping, periodic/mod-k, or black-box fold ⇒ DECLINE",
                      "recall_detect")


def measure_corpus(corpus: List[Dict]) -> dict:
    """Run `detect` over a corpus of {name, category, cost, src}; report the asymptotic-fold fraction (raw + cost-
    weighted) and the folded function names. Same partitioning convention as fold_coverage_production (so the numbers
    are comparable to the 5.7%/8.6% baseline) — this is the augmented measurement."""
    folded, fold_cost, total_cost, by_kind = [], 0, 0, {}
    for it in corpus:
        cost = it.get("cost", 1)
        total_cost += cost
        v = detect(it["src"])
        if v.status == KV.EXACT:
            folded.append(it["name"])
            fold_cost += cost
            kind = v.certificate.kind if v.certificate else "?"
            by_kind[kind] = by_kind.get(kind, 0) + 1
    n = len(corpus)
    return {
        "size": n, "folded_count": len(folded), "folded": folded,
        "fold_raw": round(len(folded) / n, 4) if n else 0.0,
        "fold_cost_weighted": round(fold_cost / total_cost, 4) if total_cost else 0.0,
        "by_certificate_kind": by_kind,
    }


def measure_production() -> dict:
    """The fixed PRODUCTION_BACKEND_CORPUS_v1 (the 5.7%→8.6% baseline) re-measured through the augmented detector."""
    import catalog.fold_coverage_production as FP
    return measure_corpus(FP._corpus())
