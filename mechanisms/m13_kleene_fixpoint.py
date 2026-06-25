"""Mechanism 13 — KLEENE FIXPOINT (★ the abstract form of fold itself). Chain-of-recurrences, C-finite folds,
coupled-cluster e^T amplitudes, Bellman/HJB value iteration, separation-logic frame inference, abstract
interpretation. Output: the least/greatest fixpoint = the closed form / value function the loop computes.
This is what the existing fold engine already does; M13 is its catalog-level name."""
from mechanisms.base import Mechanism, feats, honest_defer


def _probe(x):
    f = feats(x)
    s = 0.0
    if "recurrence" in f.tags:
        s += 0.5
    if "fixpoint" in f.tags:
        s += 0.4
    if "sum" in f.tags or "loop" in f.tags:
        s += 0.3
    return min(1.0, s)


def _apply(x, **kw):
    """M13 Kleene/least-fixpoint. Code-source strings route to the existing fold engine (in compose). NEW: structured
    transition-system / dataflow inputs reach a real fixpoint procedure —
      • {"ic3": True, "varnames", "init", "trans", "prop"} → k-induction (ic3_pdr): SAFE ⇒ EXACT inductive invariant;
        UNSAFE ⇒ EXACT decision + counterexample trace; not-k-inductive ⇒ honest DECLINE.
      • {"taint": code} → intraprocedural taint IFDS fixpoint (taint_ifds): INJECTION-FREE ⇒ EXACT safety invariant;
        a flow ⇒ EXACT decision + flow witness; unmodeled/parse-error ⇒ DECLINE."""
    import kernel_verdict as KV
    if isinstance(x, dict) and x.get("ic3") and "trans" in x:
        import ic3_pdr
        sv = ic3_pdr.prove_safety(x["varnames"], x["init"], x["trans"], x["prop"],
                                  max_k=x.get("max_k", 8), invariant_str=x.get("invariant", "prop"))
        if sv.status == "SAFE":
            cert = KV.Cert(KV.EXACT, "fixpoint_inductive", passed=True, check_cost=f"SMT k-induction (k={sv.k})",
                           detail=f"property is {sv.k}-inductive — an inductive invariant (least-fixpoint over-approx): {sv.invariant}")
            return KV.exact({"safe": True, "k": sv.k, "invariant": sv.invariant}, "m13_ic3", "k-induction", cert)
        if sv.status == "UNSAFE":
            cert = KV.Cert(KV.EXACT, "reachability_counterexample", passed=True, check_cost="SMT BMC base case",
                           detail=f"reachable property violation — counterexample trace {sv.trace}")
            return KV.exact({"safe": False, "trace": sv.trace}, "m13_ic3", "k-induction", cert)
        return KV.decline(f"M13.ic3: {sv.detail} (not k-inductive within k≤{sv.k} — needs a stronger invariant, honest)", "m13_ic3")
    if isinstance(x, dict) and x.get("chc") and "trans" in x:        # CHC/Spacer: synthesize + independently re-verify the invariant
        import chc_solve
        return chc_solve.chc_grade(x["varnames"], x["init"], x["trans"], x["prop"])
    if isinstance(x, dict) and "taint" in x:
        import taint_ifds
        tv = taint_ifds.prove_injection_free(x["taint"], x.get("sources"))
        if tv.status == "INJECTION_FREE":
            cert = KV.Cert(KV.EXACT, "fixpoint_inductive", passed=True, check_cost="IFDS taint fixpoint",
                           detail=tv.certificate())
            return KV.exact({"injection_free": True, "sources": tv.sources}, "m13_taint", "IFDS dataflow fixpoint", cert)
        if tv.status == "INJECTION_FLOW":
            cert = KV.Cert(KV.EXACT, "dataflow_witness", passed=True, check_cost="IFDS taint fixpoint",
                           detail=tv.certificate())
            return KV.exact({"injection_free": False, "flows": tv.flows}, "m13_taint", "IFDS dataflow fixpoint", cert)
        return KV.decline(f"M13.taint: {tv.status} — {tv.detail} (cannot model soundly ⇒ honest DECLINE)", "m13_taint")
    return honest_defer("M13.kleene_fixpoint",
                        "code-source strings route to the existing fold engine (handled in compose); structured "
                        "{ic3|taint} transition systems are wired above")


MECHANISM = Mechanism(
    num=13, name="kleene_fixpoint", probe=_probe, apply=_apply,
    cert_kinds=("fold_closed_form", "value_function", "frame_inference"),
    contract="requires a monotone iteration / recurrence / DP; ensures the fixpoint (closed form / value function), "
            "differential-equivalence-gated against the real loop; grade EXACT; Clock C only (not perceived speed)",
    composable_with=(1, 2, 6, 8),
    ur_form="fold = least-fixpoint of the loop functional; the catalog's most-instantiated mechanism",
)
