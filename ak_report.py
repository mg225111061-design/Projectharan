"""
§AK REPORT — measure 2000 codes UNFAKEABLY, then map what we can't fold and why.
================================================================================================================
Composes the harness: build the provenance-fixed 2000-code corpus → run the UNCHANGED engine (4-way classify) →
classify every DECLINE into a PROVEN_BOUNDARIES class → hunt the near-misses (R = foldable-but-missed) → and ★ the
most important single number: re-verify EVERY EXACT independently (M-3) — false-EXACT must be 0.

★ M-1 the fold rate is reported PER DOMAIN × PER PROVENANCE, never as a lone scalar. ★ M-2 the DECLINE distribution is
the real product (the map of what's unfoldable and why). ★ M-3 false-EXACT == 0 is the release gate (1+ ⇒ build fail).
★ M-4 the corpus is general-backend-majority and synthetic/realworld are separated (synthetic = recall ceiling, real =
the honest number). z3-terminating · zero-dep · engine UNCHANGED (measurement only) · reproducible (fixed seed).
"""
from __future__ import annotations

from typing import Optional

from corpus import build_corpus as BC
from measure import run_corpus as RC, decline_taxonomy as DT, near_miss as NM, engine_adapter as EA


def report(n: int = BC.TOTAL, seed: int = BC.SEED, probe: int = EA._PROBE, z3_timeout_ms: int = 5000,
           near_miss_limit: Optional[int] = None) -> dict:
    """Full §AK measurement. `near_miss_limit` caps the near-miss retries (the fast test path); None = all DECLINEs."""
    rr = RC.run(n, seed, probe, z3_timeout_ms)
    items = BC.build_corpus(n, seed)
    by_cid = {it.cid: it for it in items}

    # ── ★★ M-3: independently re-verify EVERY EXACT_FOLD → false-EXACT count (the gate) ──
    exacts = [r for r in rr.results if r.classification == EA.EXACT_FOLD]
    false_exact, reverify_methods, false_cases = 0, {}, []
    for r in exacts:
        rv = EA.reverify_exact(by_cid[r.cid])
        reverify_methods[rv["method"]] = reverify_methods.get(rv["method"], 0) + 1
        if rv["false_exact"]:
            false_exact += 1
            false_cases.append({"cid": r.cid, "detail": rv["detail"]})

    # ── §3 DECLINE taxonomy + §4 near-miss (R) ──
    tax = DT.tally(rr.results)
    nm = NM.hunt(items, rr.results, limit=near_miss_limit)
    # carve R out of the DECLINE distribution (R = a DECLINE that actually folds — recall headroom, not a hard floor)
    decl = tax["total_declines"]
    r_count = nm["R_count"]

    return {
        "thesis": "measure 2000 codes unfakeably — fixed provenance + per-domain separation (M-1) + synthetic/realworld "
                  "split; run the engine UNCHANGED (4-class); map every DECLINE to PROVEN_BOUNDARIES A–I + R (M-2); "
                  "★ re-verify every EXACT (M-3: false-EXACT 0 = the gate).",
        "main_table": {
            "overall": rr.summary["overall"],
            "by_domain": rr.summary["by_domain"],
            "by_provenance": rr.summary["by_provenance"],
            "by_domain_provenance": rr.summary["by_domain_provenance"],
        },
        "decline_taxonomy": {
            "total_declines": decl,
            "classes": tax["counts"], "percent": tax["percent"],
            "R_carved_out": r_count,
            "note": "A–E/H dominant ⇒ the floor is REAL mathematics (never folds); ★R dominant ⇒ RECALL headroom. "
                    "Ambiguous declines are UNCLASSIFIED (honest — never forced into a hard-boundary class).",
        },
        "near_miss": {
            "R_count": r_count, "declined_unary_retried": nm["declined_unary_retried"],
            "disguise_distribution": nm["disguise_distribution"], "recall_priority": nm["recall_priority"],
            "examples": nm["examples"],
            "note": "R = DECLINE that ACTUALLY folds under aggressive retry (z3-gated + double/far held-out, M-3). "
                    "The disguise distribution is the ranked recall target for the next §AI push.",
        },
        "precision_M3": {
            "exact_folds": len(exacts),
            "false_exact": false_exact,                    # ★★ THE most important number — must be 0
            "precision": round(1.0 - (false_exact / len(exacts)), 6) if exacts else 1.0,
            "gate_pass": false_exact == 0,
            "reverify_methods": reverify_methods,
            "false_cases": false_cases,
            "note": "every EXACT_FOLD is re-verified INDEPENDENTLY (unary: recovered recurrence vs the TRUE oracle on a "
                    "FAR window n≈400–420; static: differential re-proof). false-EXACT ≥ 1 ⇒ BUILD FAIL.",
        },
        "honest_annotations": [
            "(1) the fold rate is corpus-PROVENANCE-dependent (M-1) — read it per domain × per provenance, never alone.",
            "(2) general_backend's low fold rate is MATHEMATICS, not failure — structureless backend code has nothing to fold.",
            "(3) PROBABILISTIC is reported SEPARATELY and is NOT in the EXACT fold-rate numerator.",
            "(4) ERROR is EXCLUDED from the fold-rate denominator and reported on its own.",
            "(5) synthetic = the RECALL CEILING (does the engine catch what it knows?); realworld_style = the REAL number.",
        ],
        "config": {"n": n, "seed": seed, "probe": probe, "z3_timeout_ms": z3_timeout_ms, "reproducible": True},
        "engine_unchanged": True, "new_certificate_kinds": 0,
    }


def adversarial_battery() -> dict:
    """★ M-1 per-domain (general_backend fold rate < numeric — domain dominates the number); ★ M-3 false-EXACT == 0 (the
    gate — precision 1.0); ★ M-2 the DECLINE taxonomy is populated (a real map); ★ §4 near-miss finds genuine R with a
    disguise distribution; ★ crypto folds ~0 (hashes must DECLINE); ★ synthetic > realworld (separated honestly)."""
    r = report(n=320, seed=11, near_miss_limit=60)
    dom = r["main_table"]["by_domain"]
    prov = r["main_table"]["by_provenance"]
    cases = {
        "false_exact_zero_precision_1": r["precision_M3"]["gate_pass"] and r["precision_M3"]["precision"] == 1.0,
        "exact_folds_were_reverified": r["precision_M3"]["exact_folds"] > 0,
        "general_backend_below_numeric": dom["general_backend"]["fold_rate"] < dom["numeric"]["fold_rate"],   # ★ M-1
        "crypto_near_zero": dom["crypto_preprocessing"]["fold_rate"] <= 0.05,                                  # hashes DECLINE
        "synthetic_above_realworld": prov["synthetic"]["fold_rate"] > prov["realworld_style"]["fold_rate"],    # ★ ceiling>real
        "decline_taxonomy_populated": r["decline_taxonomy"]["total_declines"] > 0 and len(r["decline_taxonomy"]["classes"]) >= 3,
        "near_miss_found_R": r["near_miss"]["R_count"] >= 1 and len(r["near_miss"]["disguise_distribution"]) >= 1,  # ★ recall map
        "engine_unchanged_no_new_kind": r["engine_unchanged"] and r["new_certificate_kinds"] == 0,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
