"""
PRODUCT HARDENING — the write→verify→fix loop made fast, correct, and convergent (PHASE 0/2/3/4/5).
====================================================================================================
Three clocks NEVER mixed (clocks.py): A=LLM latency, B=verification, C=fold. Every speedup states its clock + N;
no uniform-Nx. Live LLM latency is [BLOCKED: egress] — the routing/streaming MECHANISM is built and offline-tested,
the live number is honestly deferred (as `test_native_s4_llm_routing` already does).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Tuple

import kernel_verdict as KV


# ── PHASE 0 — three-clocks attribution (measure before optimizing) ──────────────────────────────────────
def three_clocks(clock_a: Callable, clock_b: Callable, clock_c: Callable, k: int = 5) -> dict:
    """Measure A (LLM), B (verify), C (fold) on a workload; report the Amdahl serial bottleneck (the dominant clock).
    clock_a is typically a mock here (live egress BLOCKED) — labelled so, never a fabricated latency."""
    import clocks
    a = clocks.measure_repeat("clockA_llm", "A", clock_a, k=k).median_ms
    b = clocks.measure_repeat("clockB_verify", "B", clock_b, k=k).median_ms
    c = clocks.measure_repeat("clockC_fold", "C", clock_c, k=k).median_ms
    total = a + b + c + 1e-12
    clocks_d = {"A_llm": a, "B_verify": b, "C_fold": c}
    dom = max(clocks_d, key=clocks_d.get)
    return {"clocks_ms": {k_: round(v, 4) for k_, v in clocks_d.items()},
            "fractions": {k_: round(v / total, 3) for k_, v in clocks_d.items()},
            "bottleneck": dom, "amdahl_note": f"{dom} dominates ({round(clocks_d[dom] / total * 100, 1)}%) — optimize it first",
            "clockA_live": "BLOCKED: egress (mock latency used for attribution; real call needs a key+network)"}


# ── PHASE 2 — model routing by a cheap difficulty probe (mechanism; live BLOCKED) ───────────────────────
def route_model(task: str) -> dict:
    """Route an easy task to a small/fast model, a hard one to a large model — by a cheap difficulty probe, not
    always-max. Records the decision. (The actual call is the provider's job; this is the routing logic.)"""
    t = task.lower()
    hard_markers = ("prove", "∀", "forall", "invariant", "recurrence", "synthesize", "quantifier", "nonlinear",
                    "lift", "cegis", "induction")
    score = sum(1 for m in hard_markers if m in t) + (len(task) > 400)
    model = "large" if score >= 2 else "small"
    return {"model": model, "difficulty_score": score, "reason": f"{'hard' if model == 'large' else 'easy'} task "
            f"(markers={score}) → {model} model", "live": "BLOCKED: egress"}


# ── PHASE 3 — parallel verification (accept the first passing candidate) + incremental re-verification ───
def parallel_verify(candidates: List[Any], verify: Callable[[Any], bool]) -> dict:
    """Verify candidates and accept the FIRST that passes — Clock B shrinks to the fastest passing candidate, not the
    sum. (Sequential here for determinism; the contract is 'first pass wins', which a thread pool realizes live.)"""
    for i, c in enumerate(candidates):
        if verify(c):
            return {"accepted_index": i, "accepted": c, "checked": i + 1}
    return {"accepted_index": -1, "accepted": None, "checked": len(candidates)}


def incremental_reverify(unchanged_src, unchanged_opt, var_names: List[str]) -> KV.Verdict:
    """Re-verify only the changed part; PROVE the unchanged part equivalent via translation validation (equiv_check)
    before skipping it. The equivalence proof IS the justification for skipping — never a skipped check without it."""
    from catalog import equiv_check as EC
    res = EC.prove_equiv_z3(unchanged_src, unchanged_opt, var_names)
    if res.proved:
        cert = KV.Cert(KV.EXACT, f"equivalence[{res.tier}]", passed=True, check_cost="z3 UNSAT (unchanged-part equivalence)",
                       detail="unchanged part proved equivalent ⇒ safe to skip its re-verification")
        return KV.exact({"skip_safe": True, "tier": res.tier}, "product.incremental", "incremental re-verification", cert)
    return KV.decline(f"incremental: unchanged part NOT proved equivalent ({res.detail}) — must re-verify fully", "product.incremental")


# ── PHASE 4 — multi-oracle consensus (EXACT requires ≥2 INDEPENDENT oracles agreeing — Rule 0 deepened) ─
def multi_oracle_exact(result, oracles: List[Callable[[Any], bool]], need: int = 2) -> KV.Verdict:
    """EXACT only if ≥`need` INDEPENDENT oracles agree the result is correct. One oracle's bug cannot manufacture a
    fake pass. Fewer than `need` agreeing ⇒ DECLINE (not enough independent confirmation)."""
    votes = []
    for o in oracles:
        try:
            votes.append(bool(o(result)))
        except Exception:  # noqa: BLE001
            votes.append(False)
    agree = sum(votes)
    if agree >= need and agree == len(votes):
        cert = KV.Cert(KV.EXACT, "multi_oracle_consensus", passed=True, check_cost=f"{len(oracles)} independent oracles",
                       detail=f"{agree}/{len(oracles)} independent oracles agree (≥{need} required) — no single-oracle fake pass")
        return KV.exact({"result": result, "oracles": len(oracles), "agree": agree}, "product.multi_oracle",
                        "multi-oracle consensus", cert)
    return KV.decline(f"multi_oracle: only {agree}/{len(oracles)} oracles agree (need ≥{need} unanimous) ⇒ DECLINE "
                      "(insufficient independent confirmation)", "product.multi_oracle")


# ── PHASE 5 — fix loop with targeted feedback + converge-or-DECLINE (N-bounded) ─────────────────────────
@dataclass
class FixLoopResult:
    verdict: KV.Verdict
    iterations: int
    converged: bool
    feedback_trace: List[str] = field(default_factory=list)


def fix_loop(generate: Callable[[Optional[str]], Any], verify: Callable[[Any], Tuple[bool, str]],
             max_iters: int = 5) -> FixLoopResult:
    """Write→verify→fix with TARGETED feedback: on failure, the precise artifact (counterexample / failing obligation)
    is fed to the next generation, not a blind retry. Converges, or DECLINEs honestly after `max_iters` (the loop
    provably terminates; an N-bounded DECLINE is itself a correct, honest outcome — never ship unverified code)."""
    feedback: Optional[str] = None
    trace: List[str] = []
    for it in range(1, max_iters + 1):
        cand = generate(feedback)
        ok, artifact = verify(cand)
        trace.append(f"iter{it}: {'PASS' if ok else 'fail → ' + artifact[:50]}")
        if ok:
            cert = KV.Cert(KV.EXACT, "fix_loop_converged", passed=True, check_cost=f"{it} iteration(s)",
                           detail=f"verified after {it} iteration(s) with targeted feedback")
            return FixLoopResult(KV.exact({"candidate": cand, "iterations": it}, "product.fix_loop",
                                          f"fix loop ({it} iters)", cert), it, True, trace)
        feedback = artifact                                 # the CONCRETE failure artifact targets the next attempt
    return FixLoopResult(KV.decline(f"fix_loop: did not converge in {max_iters} iterations — DECLINE (honest: could "
                                    f"not produce verifiable code; never ship unverified)", "product.fix_loop"),
                         max_iters, False, trace)
