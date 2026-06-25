"""
FRONT-END PHASE E — Topic A constant-factor VERIFIED speedups (for code that neither folds nor lifts).
=====================================================================================================
Make unfoldable/unliftable code fast anyway, each with a correctness certificate. ★ ASYMPTOTICS UNCHANGED — this is
constant-factor; the report says so (M7-honest, never "uniform 5×"). Orchestrates the existing in-repo modules:
  • E1 equality saturation (`equality_saturation`) — saturate sound rewrites, extract cheapest; the extracted form is
    Z3-equivalence-certified (also a translation validator: same-equivalence-class membership).
  • E2 Souper-style superoptimization (`superopt`) — synthesize a cheaper equivalent loop-free DAG, cert = refinement.
  • E3 translation validation (`equiv_check.prove_equiv_z3`) — prove an optimized fragment ≡ source per-instance.
  • E4 polyhedral / SIMD (`layout_simd`) and E5 proof-directed (`proof_directed_opt`) — dependence/aliasing/invariant
    certificates license the constant-factor transform.
Every speedup carries its certificate + tier; none claims an asymptotic improvement.
"""
from __future__ import annotations

from typing import Callable, List

import kernel_verdict as KV


def equality_saturation_speedup(term) -> KV.Verdict:
    """E1: saturate + extract the cheapest Z3-equivalent form; EXACT iff strictly smaller (constant-factor node count),
    Z3-certified equivalent. No smaller form ⇒ DECLINE (no fake speedup)."""
    import equality_saturation as ES
    v = ES.optimize(term)
    if v.status == "OPTIMIZED":
        cert = KV.Cert(KV.EXACT, "equivalence[egraph_z3]", passed=True, check_cost="Z3 ∀-equivalence of the extracted form",
                       detail=f"e-graph: {v.before}→{v.after} nodes ({ES.fmt(v.optimized)}); Z3-equivalent — CONSTANT-FACTOR "
                              "(node count), asymptotics UNCHANGED")
        return KV.exact({"before": v.before, "after": v.after, "optimized": ES.fmt(v.optimized), "asymptotics": "unchanged"},
                        "topic_a", "equality saturation (constant-factor)", cert)
    if v.status == "UNSOUND_BLOCKED":
        return KV.decline(f"topic_a.eqsat: extracted form not Z3-equivalent — rejected ({v.detail})", "topic_a")
    return KV.decline(f"topic_a.eqsat: no smaller equivalent form ({v.detail}) ⇒ DECLINE (no fake speedup)", "topic_a")


def translation_validate(build_src: Callable, build_opt: Callable, var_names: List[str], sort: str = "Int") -> KV.Verdict:
    """E3: prove an optimized fragment REFINES/equals the source per-instance (Alive2-style), via equiv_check. EXACT
    with the refinement certificate; a counterexample ⇒ DECLINE (the optimization is unsound on that input)."""
    from catalog import equiv_check as EC
    res = EC.prove_equiv_z3(build_src, build_opt, var_names, sort=sort)
    if res.proved:
        cert = KV.Cert(KV.EXACT, f"equivalence[{res.tier}]", passed=True, check_cost="z3 UNSAT of (src ≠ opt)",
                       detail=f"translation validation: optimized ≡ source ∀ {var_names} ({res.tier}); CONSTANT-FACTOR")
        return KV.exact({"validated": True, "tier": res.tier, "asymptotics": "unchanged"}, "topic_a",
                        "translation validation (refinement)", cert)
    return KV.decline(f"topic_a.translation_validate: NOT equivalent — {res.detail} ⇒ DECLINE", "topic_a")


def superopt_speedup(term) -> KV.Verdict:
    """E2: Souper-style — extract the certified-cheapest equivalent (reuses superopt's verified extraction)."""
    try:
        import superopt as SO
        ce = SO.certified_extract(term)
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"topic_a.superopt: {type(e).__name__}: {e}", "topic_a")
    before = getattr(ce, "before", None)
    after = getattr(ce, "after", None)
    verified = getattr(ce, "verified", getattr(ce, "certified", False))
    if verified and (after is None or before is None or after < before):
        cert = KV.Cert(KV.EXACT, "equivalence[superopt]", passed=True, check_cost="superopt verified extraction",
                       detail=f"Souper-style: {before}→{after} (verified equivalent); CONSTANT-FACTOR, asymptotics unchanged")
        return KV.exact({"before": before, "after": after, "asymptotics": "unchanged"}, "topic_a",
                        "superoptimization (constant-factor)", cert)
    return KV.decline("topic_a.superopt: no verified cheaper equivalent ⇒ DECLINE", "topic_a")


def topic_a_grade(x) -> KV.Verdict:
    """Route {"speedup": term} (equality saturation) | {"validate": [build_src, build_opt, vars]} (translation
    validation) | {"superopt": term}. All constant-factor, all certified."""
    if isinstance(x, dict) and "speedup" in x:
        return equality_saturation_speedup(x["speedup"])
    if isinstance(x, dict) and "validate" in x:
        b = x["validate"]
        return translation_validate(b[0], b[1], b[2], x.get("sort", "Int"))
    if isinstance(x, dict) and "superopt" in x:
        return superopt_speedup(x["superopt"])
    return KV.decline("topic_a: expected {speedup: term} | {validate:[src,opt,vars]} | {superopt: term}", "topic_a")
