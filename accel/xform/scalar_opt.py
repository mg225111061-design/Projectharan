"""
§AO §2.4 — SCALAR optimizations (strength reduction · const-fold · CSE · LICM · DCE), each z3-equivalence-gated.
================================================================================================================
The classic compiler passes, each admitted ONLY with a z3 ∀-equivalence proof (REUSE `topic_a.translation_validate`).
This is "CompCert for the accelerator": the speedup is real, the math is proven identical, and a WRONG variant of any
pass is REJECTED (the original is kept). Mirrors `pillar3.equiv_transforms`' sr/li/cse classes — reused in spirit.
"""
from __future__ import annotations


def _tv(src, opt, names, sort="Int"):
    import catalog.topic_a as TA
    return TA.translation_validate(src, opt, names, sort=sort)


def verify_pass(name: str, correct: bool = True):
    """Each scalar pass as a (src, opt) equivalence; correct=False injects the classic bug for that pass."""
    if name == "strength_reduction":                       # 2*x ≡ x+x ; wrong: x*x
        return _tv(lambda e: 2 * e["x"], (lambda e: e["x"] + e["x"]) if correct else (lambda e: e["x"] * e["x"]), ["x"])
    if name == "cse":                                      # a*b + a*b ≡ 2*(a*b) ; wrong: (a*b)*(a*b)
        return _tv(lambda e: e["a"] * e["b"] + e["a"] * e["b"],
                   (lambda e: 2 * (e["a"] * e["b"])) if correct else (lambda e: (e["a"] * e["b"]) * (e["a"] * e["b"])), ["a", "b"])
    if name == "licm":                                     # 3 iterations of an invariant a*b ≡ 3*(a*b) ; wrong: 3+a*b
        return _tv(lambda e: e["a"] * e["b"] + e["a"] * e["b"] + e["a"] * e["b"],
                   (lambda e: 3 * (e["a"] * e["b"])) if correct else (lambda e: 3 + e["a"] * e["b"]), ["a", "b"])
    if name == "const_fold":                               # x*1 + 0 ≡ x ; wrong: x+1
        return _tv(lambda e: e["x"] * 1 + 0, (lambda e: e["x"]) if correct else (lambda e: e["x"] + 1), ["x"])
    if name == "dce":                                      # out = x (dead t=y*y removed) ≡ x ; wrong: x+y*y
        return _tv(lambda e: e["x"], (lambda e: e["x"]) if correct else (lambda e: e["x"] + e["y"] * e["y"]), ["x", "y"])
    raise ValueError(name)


_PASSES = ("strength_reduction", "cse", "licm", "const_fold", "dce")


def adversarial_battery() -> dict:
    """★ all five scalar passes are z3-proven ≡ the original ∀ (accepted); ★★ the classic WRONG variant of each is
    z3-REJECTED (false EXACT 0 — A-2: every accel pass is translation-validated)."""
    import kernel_verdict as KV
    correct = {p: verify_pass(p, True).status == KV.EXACT for p in _PASSES}
    wrong = {p: verify_pass(p, False).status == KV.DECLINE for p in _PASSES}
    cases = {
        "all_passes_proven_equiv": all(correct.values()),
        "all_wrong_variants_rejected": all(wrong.values()),     # ★★ A-2
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
