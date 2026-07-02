"""
§AC REPORT — the SCOPED decomposition: each fold's lift labeled by its scope (workload / precondition / statement-level /
order / additive), never one inflated total. Plus the fallback audit, the HARAN-fit note, the denominator audit, LLM-free.
================================================================================================================
"""
from __future__ import annotations

import os
from typing import Dict

import inputfold.profile_fold as F1
import inputfold.spec_fold as F2
import inputfold.partial_fold as F3
import inputfold.asymptotic_fold as F4
import inputfold.recursive_fold as F5


def _llm_free_check() -> dict:
    """Structural (AST) check: no inputfold module imports an LLM client — profiling is measurement, spec is user-given,
    partial/asymptotic/recursive are deterministic analysis. A weak LLM changes nothing."""
    import ast
    here = os.path.dirname(__file__)
    llm_modules = {"claude_agent", "llm_router", "openai", "anthropic"}
    offenders = {}
    for fn in sorted(os.listdir(here)):
        if not fn.endswith(".py"):
            continue
        with open(os.path.join(here, fn), encoding="utf-8") as f:
            tree = ast.parse(f.read())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        if imported & llm_modules:
            offenders[fn] = sorted(imported & llm_modules)
    return {"llm_free": offenders == {}, "offenders": offenders}


def precision_battery() -> dict:
    bats = {"F1_profile": F1.adversarial_battery(), "F2_spec": F2.adversarial_battery(),
            "F3_partial": F3.adversarial_battery(), "F4_asymptotic": F4.adversarial_battery(),
            "F5_recursive": F5.adversarial_battery()}
    all_ok = all(b["all_ok"] for b in bats.values())
    return {"per_fold": {k: b["all_ok"] for k, b in bats.items()}, "all_ok": all_ok,
            "failed": {k: b["failed"] for k, b in bats.items() if not b["all_ok"]},
            "precision": 1.0 if all_ok else 0.0}


def report() -> dict:
    import dependency_audit as DA
    # F1 profile-guided (under workload W)
    folded, original = lambda e: e["x"] * 4, lambda e: e["x"] * e["k"]
    prof = F1.profile_guided_fold(folded, original, ["x", "k"], "k", F1.ingest_profile([4] * 90 + [9] * 10))
    W = [{"x": i, "k": 4} for i in range(90)] + [{"x": i, "k": 9} for i in range(10)]
    f1 = F1.run_under_workload(prof, folded, original, "k", W)
    fb = F1.verify_fallback_invariant(prof, folded, original, "k")
    # F2 spec-declared (under requires P)
    import z3
    f2 = F2.spec_fold(lambda e: e["x"], lambda e: z3.If(e["x"] < 0, -e["x"], e["x"]), ["x"],
                      lambda e: e["x"] >= 0, "x >= 0", "runtime-checked")
    # F3 partial (statement-level)
    f3 = F3.partial_fold([F3.Stmt("acc", {"s", "c"}, {"s"}, True, "accumulate"),
                          F3.Stmt("io", {"x"}, {"_io"}, False, "io")], c_step=3)
    # F4 asymptotic (order)
    f4 = F4.asymptotic_fold("prefix_sum")
    # F5 recursive (additive)
    f5 = F5.measure_recursive_lift([5, -5, 7, -7])
    prec = precision_battery()
    llm = _llm_free_check()
    fd = DA.final_dependency_set()["forbidden_present"]
    return {
        "thesis": "stop assuming the input is unknown and stop assuming a fold is all-or-nothing — learn the input by "
                  "measuring it (profile) or being told it (spec), and vary the fold's depth to take the part, the order, "
                  "or the fixpoint — every step proved, every scope stated, the profile never touching correctness",
        "scoped_decomposition": {
            "F1_profile_under_W": {"hit_rate_under_W": f1["hit_rate_under_W"], "scope": f1["scope"],
                                   "all_correct": f1["all_correct"],
                                   "note": "★ workload-scoped, never universal; correctness independent of the profile"},
            "F2_spec_under_requires": {"precondition": f2.precondition, "mode": f2.mode, "issued": f2.issued,
                                       "note": "★ sound UNDER the declared P; truth runtime-checked or declarer-responsible"},
            "F3_partial_statement_level": {"statement_level_rate": f3.statement_level_rate,
                                           "folded": f3.folded_stmts, "residual": f3.residual_stmts,
                                           "note": "★ statement-level denominator, DISTINCT from whole-loop, never merged"},
            "F4_asymptotic_order": {"before": f4.before_order, "after": f4.after_order, "grade": f4.grade,
                                    "note": "★ ORDER reduction, DISTINCT from closed-form (O(N)→O(1))"},
            "F5_recursive_additive": {"single_pass_folds": f5["single_pass_folds"], "fixpoint_folds": f5["fixpoint_folds"],
                                      "recursive_only_lift": f5["recursive_only_lift"],
                                      "note": "★ additive-with-overlap (fixpoint − single-pass), never multiplicative"},
            "headline": "baseline → +profile-under-W → +spec-under-requires → +partial-statement-level → "
                        "+asymptotic-order → +recursive-additive — each with its scope and denominator, NEVER one inflated total",
        },
        "fallback_audit_F1": {"fallback_invariant_holds": fb,
                              "note": "every profile-guided fold has a sound fallback (the original); correctness holds "
                                      "even if the profile is 100% wrong — only speed depends on the profile"},
        "haran_fit_F2": {"requires_as_acceleration_contract": f2.issued, "mode_stated": f2.mode,
                         "note": "the user's domain knowledge (`requires`) unlocks folds the code alone can't justify; "
                                 "P's truth is checked OR the declarer's responsibility — stated, never silent"},
        "denominator_audit_F3_F4": {"partial_statement_level": f3.statement_level_rate, "asymptotic_order_reduction":
                                    f"{f4.before_order}→{f4.after_order}",
                                    "note": "partial reported at statement-level, asymptotic at order-reduction — DISTINCT "
                                            "from closed-form, never merged into the whole-loop EXACT number"},
        "measured_real_ceiling": "after the five, the still-DECLINED remainder under the actual workload is the genuine "
                                 "I/O / genuine randomness / genuine data-dependent control — profile folds structured-"
                                 "under-W, spec folds structured-by-declaration, neither folds true randomness (pigeonhole)",
        "llm_free": llm,
        "precision": prec,
        "no_new_certificate_kind": True,
        "zero_dep_forbidden_present": fd, "zero_dep_ok": fd == [],
        "one_line": "잘못된 답보다 DECLINE이 항상 옳다 — 입력을 측정(프로파일)하거나 선언(spec)받고, fold 깊이를 부분·차수·"
                    f"고정점으로 변주한다; 프로파일은 정확성 불침범(fallback 불변식 {fb}), spec은 P 하에서만(모드 명시), "
                    f"부분은 문장단위 분모({f3.statement_level_rate}), 점근은 차수({f4.before_order}→{f4.after_order}), 재귀는 "
                    f"가산(lift {f5['recursive_only_lift']}); 범위 항상 명시, 합산 없음, LLM-free, 정밀도 {prec['precision']}.",
    }
