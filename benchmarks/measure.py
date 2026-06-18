#!/usr/bin/env python3
"""
STAGE 0 — REAL measurement. Every number the site shows is produced HERE by actually running the engines.
=========================================================================================================
No estimates, no memory, no placeholders. Each metric records its VALUE + UNIT + the METHOD (one line: how
it was measured) + the measurement timestamp. A metric that cannot be measured in this environment is
recorded under "blocked" with the reason — never faked. Re-running this regenerates benchmarks/stats.json
(the site reads that file; the frontend hardcodes no numbers) and appends to benchmarks/raw.log.

Run:  python3 benchmarks/measure.py    (from the repo root)
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
from contextlib import redirect_stdout
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

RAW = open(os.path.join(ROOT, "benchmarks", "raw.log"), "a")


def _log(line: str) -> None:
    RAW.write(line + "\n")
    RAW.flush()


def measure() -> dict:
    metrics: dict = {}
    blocked: list = []
    _log(f"\n===== measurement run {datetime.now(timezone.utc).isoformat()} =====")

    # 1. tests passing — run the whole suite, count real passes (no oracle bypass) -----------------
    import test_build as TB
    passed = failed = 0
    buf = io.StringIO()
    with redirect_stdout(buf):
        for t in TB.ALL:
            try:
                t(); passed += 1
            except Exception:  # noqa: BLE001
                failed += 1
    _log(f"tests: {passed} passed / {failed} failed of {len(TB.ALL)}")
    metrics["tests_passing"] = {
        "value": passed, "total": len(TB.ALL), "unit": "tests",
        "method": "run the full test_build.py suite in-process; count tests that pass (no oracle bypass)."}

    # 2. verifier soundness — Clover spec-gate on a real/vacuous corpus: false positives + vacuous caught
    import spec_gate as SG
    g = SG.measure_gate(TB.SPEC_GATE_CORPUS)
    _log(f"spec_gate: FP={g['false_pos']} caught={g['true_pos']}/6 unmodeled={g['unmodeled']}")
    metrics["verifier_false_positives"] = {
        "value": g["false_pos"], "unit": "false positives",
        "method": "run the Clover spec-gate over a corpus of REAL + vacuous specs; count real specs wrongly rejected."}
    metrics["vacuous_specs_caught"] = {
        "value": g["true_pos"], "total": 6, "unit": "specs",
        "method": "same gate run; count deliberately-vacuous/contradictory specs correctly flagged."}

    # 3. auto-fix loop — write→verify→fix over a seeded-bug corpus: solved, wrong, iteration spread ----
    import s11_live_measure as S11
    lm = S11.measure_loop_convergence("extended")
    _log(f"autofix: solved {lm.solved}/{len(lm.rows)} wrong={lm.wrong} iters={lm.histogram} {lm.total_ms:.1f}ms")
    metrics["autofix_solved"] = {
        "value": lm.solved, "total": len(lm.rows), "wrong": lm.wrong, "unit": "tasks",
        "method": "run the write→verify→fix loop on a seeded-bug corpus; count tasks reaching a verified fix; "
                  "`wrong` (claimed-fixed-but-not) must be 0."}

    # 4. proof reuse — round-2 re-verification is served from cache (cold vs warm wall-clock) ----------
    pr = S11.measure_proof_reuse()
    factor = (pr["cold_ms"] / pr["warm_ms"]) if pr["warm_ms"] > 0 else pr["reuse_speedup"]
    _log(f"proof_reuse: cold {pr['cold_ms']}ms warm {pr['warm_ms']}ms = {factor:.1f}x lossless={pr['lossless']}")
    metrics["proof_reuse_speedup"] = {
        "value": round(factor, 1), "unit": "x", "cold_ms": pr["cold_ms"], "warm_ms": pr["warm_ms"],
        "method": "prove a batch of obligations cold (SMT solver) then warm (structural cache); wall-clock ratio "
                  "(verdicts are identical — lossless)."}

    # 5. fold/replicate scale — prove a pattern once, certify N instances vs N independent proofs --------
    import fold_replicate as FR
    t = FR.Template("affine_monotone", ["A", "B"], {"A": "Int", "B": "Int"}, {"x1": "Int", "x2": "Int"},
                    precond=["A >= 0"], ensures="A*x1 + B <= A*x2 + B", input_hyp=["x1 <= x2"])
    big = FR.replicate(t, [{"A": (i % 40) + 1, "B": i} for i in range(150)])
    _log(f"fold_scale: N={big.n} fold {big.fold_ms:.1f}ms naive {big.naive_ms:.1f}ms = {big.speedup:.1f}x")
    metrics["fold_scale_speedup"] = {
        "value": round(big.speedup, 1), "unit": "x", "n": big.n,
        "method": f"prove a parametric template ONCE then certify N={big.n} instances by a cheap side-condition "
                  "check, vs N independent SMT proofs; wall-clock ratio (the gap widens with N)."}

    # 6. equality saturation — Z3-certified optimal extraction shrinks an expression -------------------
    import equality_saturation as ES
    v = ES.optimize(("+", ("*", ("var", "x"), ("const", 2)), ("*", ("var", "x"), ("const", 3))))
    reduction = round((v.before - v.after) / v.before * 100) if v.before else 0
    _log(f"eqsat: {v.before}->{v.after} nodes ({reduction}% smaller) status={v.status}")
    metrics["eqsat_node_reduction"] = {
        "value": reduction, "unit": "%", "before": v.before, "after": v.after,
        "method": "saturate an e-graph with sound ring rewrites, extract the lowest-cost equivalent term, "
                  "PROVE input==output with Z3; report node-count reduction (e.g. x*2+x*3 → 5*x)."}

    # 7. parallel reduction — measured speedup on this machine (honest: only if it's a real win) --------
    import parallel_algebra as PA
    pv = PA.parallelize_reduction("square", "+", 2_000_000, cores=4)
    _log(f"parallel: status={pv.status} speedup={pv.speedup:.2f}x cores={pv.cores}")
    if pv.status == "OPTIMIZED" and pv.speedup >= 1.1:
        metrics["parallel_speedup"] = {
            "value": round(pv.speedup, 2), "unit": "x", "cores": pv.cores, "workload": pv.workload,
            "method": "reduce(+, square(i) for i in 0..2,000,000) split across processes vs sequential; wall-clock "
                      "ratio, with the parallel result verified equal to the sequential one."}
    else:
        blocked.append({"metric": "parallel_speedup",
                        "reason": f"measured {pv.speedup:.2f}x ({pv.status}) on this sandbox's cores — below the "
                                  "1.1x win bar, so not shown (no fabricated speedup)."})

    # 8. fold coverage (v32) — MEASURED on the fixed defer corpus: current engine vs +A/B1/B2 ----------
    import fold_dispatcher as FD
    cov = FD.measure_coverage()
    covh = FD.measure_coverage(split="measure")
    _log(f"fold_coverage[Clock C]: baseline {cov.baseline_folded}/{cov.n_clockC} -> now {cov.now_folded}/"
         f"{cov.n_clockC}; false_folds={cov.false_folds}; held-out {covh.baseline_folded}->{covh.now_folded}"
         f"/{covh.n_clockC}; [Clock B] {cov.clockB_handled}/{cov.clockB_n}")
    assert cov.false_folds == 0 and covh.false_folds == 0    # never publish a number built on a false fold
    metrics["fold_coverage_now"] = {
        "value": round(cov.now_rate * 100), "unit": "%", "clock": "C",
        "baseline_pct": round(cov.baseline_rate * 100), "folded": cov.now_folded, "n": cov.n_clockC,
        "baseline_folded": cov.baseline_folded, "false_folds": cov.false_folds,
        "heldout_baseline_pct": round(covh.baseline_rate * 100), "heldout_now_pct": round(covh.now_rate * 100),
        "per_category": cov.per_category, "clockB_verified": f"{cov.clockB_handled}/{cov.clockB_n}",
        "method": "route each loop in the fixed defer corpus to its technique (Kovacic/Ben-Or-Tiwari/q-Gosper), "
                  "each behind its own SOUND verifier; count FOLDED. baseline = current engine. Clock C fold rate "
                  "only (ABFT is Clock B, counted separately). false_folds (a negative control folded) must be 0."}

    # 9. v33 fold soup — brewed verified lemma library + runtime no-regression (the first success condition)
    import final_measure as FM
    a1 = FM.axis1_speed_guard()
    a3 = FM.axis3_strength()
    au = FM.slow_path_leak_audit()
    _log(f"fold_soup: {a3['verified_instances']} verified instances / {a3['meta_families']} meta-families; "
         f"runtime regressed={a1['regressed']} fold {a1['fold_speedup']}× lookup {a1['lookup_us']}µs; "
         f"audit clean={au['clean']}")
    assert a1["regressed"] is False and au["clean"] is True       # never publish if runtime regressed or a leak
    metrics["fold_soup_lemmas"] = {
        "value": a3["verified_instances"], "unit": "verified instance-lemmas", "clock": "build-time",
        "meta_families": a3["meta_families"], "strength_distribution": a3["strength_distribution"],
        "epsilon0_via_lean": a3["epsilon0_via_lean"],
        "method": "brew genuinely-distinct fold families offline; each individually verified (induction-PIT / "
                  "companion≡naive), deduped by canonical signature. Counts MEASURED; meta-families vs instances "
                  "reported distinctly (no artificial splitting). ε₀-via-Lean BLOCKED (Lean unavailable)."}
    metrics["fold_runtime_no_regression"] = {
        "value": (not a1["regressed"]), "unit": "bool (true=no regression)", "clock": "C",
        "fold_speedup": a1["fold_speedup"], "lookup_us": a1["lookup_us"],
        "method": "[Clock C] median-of-k before(naive loop)/after(O(1) soup lookup + closed-form eval) at "
                  "n=1e5; the AFTER path must not be slower (first success condition). Lookup is O(1) in library size."}

    # live-LLM latency / accuracy needs a key + egress — explicitly BLOCKED, never faked ---------------
    blocked.append({"metric": "live_llm_latency",
                    "reason": "needs an API key + egress to a provider; not measurable in this sandbox "
                              "(no key, gateway hosts off the egress allowlist)."})

    return {
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "environment": "pure-Python sandbox (no numpy/native backend; egress-limited) — figures are local & "
                       "machine-dependent; re-run benchmarks/measure.py to refresh.",
        "metrics": metrics,
        "blocked": blocked,
    }


def main() -> int:
    stats = measure()
    out = os.path.join(ROOT, "benchmarks", "stats.json")
    with open(out, "w") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"wrote {out} — {len(stats['metrics'])} measured metrics, {len(stats['blocked'])} blocked")
    for k, m in stats["metrics"].items():
        print(f"  {k}: {m['value']} {m.get('unit','')}")
    for b in stats["blocked"]:
        print(f"  [BLOCKED] {b['metric']}: {b['reason'][:60]}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
