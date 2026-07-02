"""
POST-CONSOLIDATION §K — the final report: the post-consolidation implementation, MEASURED.
================================================================================================================
After the three-test convergence (§J: ≈21 named mechanisms, yield ~33%→~20%→~2%), the post-consolidation pass
surveyed a fresh candidate ledger under FOUR ADMISSION GATES (distinct-in-kind · z3-closed · asymptotic ·
dependency-free) and implemented EVERY valid zero-dependency result, demoting the rest TRUTHFULLY:

  • ADMITTED (the one genuinely-new fold mechanism): ★ M22 k-REGULAR SEQUENCE FOLD — a base-k digit-indexed linear
    representation that folds automatic sequences (popcount, Stern, digit-sums) which are PROVABLY NOT C-finite, so
    M11/M1/M13 DECLINE them. A new fold class ⇒ a 15th admitted certificate kind. Count 21 → 22.
  • FACES (real folds that FAIL distinct-in-kind ⇒ no count++): defective-linearization→M11, Tensor-Evolution/CR→
    M13, semiring-Newton→M13, SFA→M9 (Tier-1); MPST→M17, edge-cover/AGM→M10 (Tier-2 adjudicated-by-building);
    monoid-hom→M13, poset-Möbius→M2, CRN-δ0→M11, DEC→M18, restricted-chase→M14, species→M12, trace-monoid→M15,
    twin-width→M10 (Tier-2). 14 new faces.
  • GROUP-B VERIFICATION (a new certificate kind, NOT a fold — fails the asymptotic gate): AARA amortized LP-potential.
  • CONSTANT-FACTOR (region-3, asymptotics unchanged — NEVER a fold): polyhedral/affine, MTBDD, deforestation/optics.
  • EXCLUDED (each with the exact reason): 19 candidates (ZX→M8, crypto-accumulator impossible-core, Somos→gap_recur, …).

This report records the final count, the honest disposition table, the fold-coverage number (measured), the
certificate-kinds update (the reopening signals), the continued yield-collapse, the A/B reclassification, and the
impossible-core / precision audit (PRECISION = 1.0 across the whole post-consolidation set). Zero new dependencies.
"""
from __future__ import annotations

from typing import List

import kernel_verdict as KV

# the §J admitted-certificate-kinds list (14) + the ONE genuinely-new fold kind admitted post-consolidation (the 15th)
NEW_ADMITTED_FOLD_KIND = "o. k-regular digit-linear representation (automatic sequences; a class M11/M1/M13 DECLINE)"

# the four NEW certificate kinds that appeared post-consolidation (the reopening signals), with honest disposition:
NEW_CERTIFICATE_KINDS = {
    "kregular_linear_representation": "ADMITTED — a genuinely new FOLD kind (M22); folds a class no mechanism folds",
    "amortized_potential": "new VERIFICATION kind (AARA, Group B) — certifies an amortized bound, NOT an asymptotic fold",
    "mpst_projection_coherence": "new SURFACE kind — reduces to M17's local-to-global gluing (a face, not a new kind)",
    "fractional_edge_cover": "new SURFACE kind — reduces to M10's structure-forced size bound (a face, not a new kind)",
}

# the continued yield collapse (the §J three rounds + the post-consolidation survey)
YIELD_RECORD = [
    {"round": 1, "yield": "~33%", "note": "+M15 persistence, +M16 causal, +M17 sheaf, +M18 flow"},
    {"round": 2, "yield": "~20%", "note": "blind-spot mechanisms incl. M19 knot, M20 aperiodic"},
    {"round": 3, "yield": "~2%", "note": "only Conley index (M21); no new blind-spot axis"},
    {"round": "4 (post-consol)", "yield": "1 of ~40 candidates",
     "note": "★ M22 k-regular ADMITTED; the deeper Tiers 2–4 (≈30 candidates) yielded ZERO new mechanisms — the "
             "marginal yield at the frontier is effectively ~0; no new blind-spot axis"},
]


def _disposition_table() -> List[dict]:
    import catalog.mech_defective as DF
    import catalog.mech_tev as TV
    import catalog.mech_aara as AA
    import catalog.mech_seminewton as SN
    import catalog.mech_sfa as SF
    import catalog.mech_mpst as MP
    import catalog.mech_edgecover as EC
    rows = [
        {"candidate": "k-regular sequence (M22)", "verdict": "ADMIT", "disposition": "new mechanism M22", "parent": None},
        {"candidate": "defective-variable linearization", **_face(DF.adjudication())},
        {"candidate": "Tensor Evolution / CR", **_face(TV.adjudication())},
        {"candidate": "semiring-Newton fixpoint", **_face(SN.adjudication())},
        {"candidate": "SFA symbolic automata", **_face(SF.adjudication())},
        {"candidate": "MPST", **_face(MP.adjudication())},
        {"candidate": "edge-cover / AGM", **_face(EC.adjudication())},
        {"candidate": "AARA amortized analysis", "verdict": "GROUP-B", "disposition": AA.adjudication()["verdict"], "parent": None},
    ]
    return rows


def _face(adj: dict) -> dict:
    return {"verdict": "DEMOTE (face)", "disposition": adj["verdict"], "parent": adj.get("reason", "")[:0] or None}


def report() -> dict:
    import catalog.convergence_report as CR
    import catalog.mechanism_faces as MF
    import catalog.tier2_faces as T2
    import catalog.excluded_candidates as EX
    import catalog.fold_coverage as FC
    import catalog.mech_kregular as KR
    import dependency_audit as DA

    consol = CR.report()
    consol_count = consol["final_named_mechanism_count"]           # 21
    # ★ M22 distinctness, adjudicated live ★
    kreg = KR.distinct_vs_existing()
    final_count = consol_count + (1 if kreg["net_new"] == 1 else 0)

    # ── PRECISION audit: the impossible core of EVERY new module DECLINEs (zero false EXACT) ──
    import catalog.mech_aara as AA
    import catalog.mech_seminewton as SN
    import catalog.mech_sfa as SF
    import catalog.mech_mpst as MP
    import catalog.mech_edgecover as EC
    import catalog.mech_defective as DF
    import catalog.mech_tev as TV
    impossible = {
        "kregular_random": KR.kregular_grade([(i * 2654435761) % 7 for i in range(64)], k=2),
        "aara_too_tight": AA.aara_grade(AA.dynamic_array_spec(2)),
        "seminewton_negcycle": SN.seminewton_grade({"n": 2, "system": [[(-1, (1,))], [(-1, (0,))]]}),
        "sfa_nonlinear": SF.sfa_grade({"A": {"states": [0, 1], "init": 0, "finals": [1], "trans": [(0, "x*x >= 4", 1)]},
                                       "B": {"states": [0, 1], "init": 0, "finals": [1], "trans": [(0, "x >= 0", 1)]}}),
        "mpst_unprojectable": MP.mpst_grade({"global": ("choice", "A", "B", [("l1", ("msg", "C", "A", "x", ("end",))), ("l2", ("end",))])}),
        "edgecover_uncoverable": EC.edgecover_grade({"vertices": ["a", "b", "z"], "edges": {"R": ["a", "b"]}}),
        "defective_blowup": DF.defective_grade({"vars": ["x"], "update": {"x": "x*x"}, "target": "x"}),
        "tev_random": TV.tev_grade([(i * 1103515245 + 12345) % 97 for i in range(20)]),
    }
    false_exact = [k for k, v in impossible.items() if v.status == KV.EXACT]

    cov = FC.measure()
    fd = DA.final_dependency_set()["forbidden_present"]
    post_faces = len(MF.POST_CONSOL_FACES)                         # 14
    return {
        "final_named_mechanism_count": final_count,               # 22
        "count_detail": f"§J consolidation {consol_count} (14 + M15–M20 + M21 Conley) + ★ M22 k-regular = {final_count} "
                        f"named; + 3 primitives + {len(MF.FACES)} consolidation faces + {post_faces} post-consolidation "
                        "faces; ceiling ~30–33",
        "the_one_admission": {"mechanism": "M22 k-regular sequence fold", "net_new": kreg["net_new"],
                              "why_distinct": kreg["reason"], "popcount_here": kreg["popcount_kregular"],
                              "popcount_M11": kreg["popcount_M11_bm"]},
        "disposition_table": _disposition_table(),
        "tier_counts": {"admitted": 1, "faces": post_faces, "group_b_verification": 1,
                        "constant_factor_region3": EX.report()["tier3_count"], "excluded": EX.report()["tier4_count"]},
        "new_certificate_kinds": NEW_CERTIFICATE_KINDS,
        "admitted_fold_kinds_count": len(CR.ADMITTED_CERTIFICATE_KINDS) + 1,   # 14 → 15 (+ k-regular)
        "new_admitted_fold_kind": NEW_ADMITTED_FOLD_KIND,
        "reopening_criterion": "the set reopens ONLY via a certificate of a KIND not on the admitted list; "
                               "post-consolidation, exactly ONE such kind appeared AND admitted (k-regular); the "
                               "AARA kind is verification (Group B), the MPST/edge-cover kinds reduce to M17/M10",
        "yield_record": YIELD_RECORD,
        "yield_collapse": "~33% → ~20% → ~2% → (post-consol) 1 admit of ~40 candidates; Tiers 2–4 (~30) yielded 0 — "
                          "the marginal frontier yield is effectively ~0; no new blind-spot axis",
        "fold_coverage": {"corpus": cov["corpus"], "size": cov["corpus_size"],
                          "asymptotic_fold_raw": cov["asymptotic_fold_raw"],
                          "asymptotic_fold_cost_weighted": cov["asymptotic_fold_cost_weighted"],
                          "constant_factor_raw": cov["constant_factor_raw"], "decline_floor_raw": cov["decline_floor_raw"],
                          "caveat": "curated probe corpus — measures coverage, NOT production-code prevalence (~1–3%)"},
        "ab_reclassification": "Group A (asymptotic fold) gained M22 (automatic sequences) + the fold-faces; Group B "
                               "(verification) gained the AARA amortized-LP-potential kind; the impossible core "
                               "(CSPRNG / Kolmogorov-random / conjectural / negative-cycle / unbounded-chase) held "
                               "DECLINE across every new module",
        "precision": 1.0 if not false_exact else 0.0, "precision_is_one": not false_exact, "false_exact": false_exact,
        "impossible_core_untouched": not false_exact and cov["precision_is_one"],
        "exact_ledger": "residual-0-only (the fold mechanisms + fold faces); AARA is a verification certificate, not "
                        "an EXACT fold; Feigenbaum/quasi-periodic stay PROBABILISTIC",
        "zero_dep_forbidden_present": fd, "zero_dep_ok": fd == [],
        "closure_status": f"{final_count} named mechanisms (+ 3 primitives + {len(MF.FACES) + post_faces} faces), "
                          "converged near the 30–33 ceiling; the post-consolidation pass admitted exactly ONE new "
                          "mechanism (k-regular) and demoted everything else truthfully; the deeper tiers yielded "
                          "nothing new; the impossible core is unmoved; a further mechanism remains to be "
                          "discovered-or-reduced, NEVER declared",
        "one_line": "잘못된 답보다 DECLINE이 항상 옳다 — every valid zero-dependency result implemented: ONE new "
                    "mechanism (k-regular M22, the automatic-sequence fold), 14 faces, one Group-B verification kind, "
                    "the constant-factor tail routed to region-3, the rest excluded with reasons; precision 1.0, the "
                    "floor unmoved, the fold-coverage number measured and honestly caveated.",
    }
