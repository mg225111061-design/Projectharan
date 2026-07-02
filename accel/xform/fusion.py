"""
§AO §2.1 — OPERATOR/KERNEL FUSION, z3-equivalence-gated. Fuse matmul+bias+ReLU into one kernel (kill the intermediate
================================================================================================================
materializations) ONLY when z3 proves the fused dataflow ≡ the sequential one ∀ inputs. ★ REUSE
`topic_a.translation_validate` (z3 UNSAT-of-(src≠opt)) — a wrong fusion (e.g. ReLU applied before the bias) is REJECTED
and the original is kept. The speedup is memory-traffic (fewer passes), the math is identical — proven, not assumed.
"""
from __future__ import annotations


def verify_fusion(correct: bool = True):
    """Prove the fused matmul+bias+ReLU ≡ the sequential pipeline (correct) — or expose a wrong fusion (ReLU before
    bias) as NON-equivalent. Returns the z3 translation-validation verdict (EXACT iff equivalent ∀)."""
    import catalog.topic_a as TA
    import z3

    def relu(x):
        return z3.If(x >= 0, x, 0)
    # sequential: t = dot(a,b); t = t + bias; out = relu(t)
    src = lambda e: relu(e["a0"] * e["b0"] + e["a1"] * e["b1"] + e["bias"])
    if correct:
        opt = lambda e: relu((e["a0"] * e["b0"] + e["a1"] * e["b1"]) + e["bias"])     # fused — same math
    else:
        opt = lambda e: relu(e["a0"] * e["b0"] + e["a1"] * e["b1"]) + e["bias"]        # WRONG: relu before bias
    return TA.translation_validate(src, opt, ["a0", "a1", "b0", "b1", "bias"], sort="Int")


def adversarial_battery() -> dict:
    """★ the correct matmul+bias+ReLU fusion is z3-proven ≡ sequential (accepted); ★★ a wrong fusion (ReLU before the
    bias) is z3-REJECTED (not emitted — A-2: translation validation is the differentiator)."""
    import kernel_verdict as KV
    ok = verify_fusion(correct=True)
    bad = verify_fusion(correct=False)
    cases = {
        "correct_fusion_proven_equiv": ok.status == KV.EXACT,
        "wrong_fusion_rejected": bad.status == KV.DECLINE,      # ★★ A-2: not emitted
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
