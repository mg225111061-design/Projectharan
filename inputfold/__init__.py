"""
§AC — INPUT-AWARE & DEPTH-VARYING FOLDS: learn the input (profile/spec) or vary the fold's depth (partial/order/fixpoint).
================================================================================================================
Every prior directive folded blind to the input. §AC breaks that two ways — we MEASURE the input distribution (profile)
or the user DECLARES it (HARAN `requires`) — and varies the fold's DEPTH three ways (fold part of a loop; fold the
asymptotic order; fold recursively to a fixpoint). All five are z3-verified where they claim soundness, all LLM-free
(deterministic), all honest about scope.

★ THE FOUR HONESTIES (binding):
  • PROFILE-GUIDED is sound only under the MEASURED WORKLOAD — a fact about a deployment, not a theorem about all inputs.
    So it is ALWAYS dual-path with the original as fallback; ★ correctness NEVER depends on the profile (only speed does);
    the fold rate is reported "under workload W," never universal.
  • SPEC-DECLARED is sound under the DECLARED PRECONDITION — `requires is_sorted(arr)` ⇒ proved sound UNDER P (zero
    synthesis cost, 100% hit where P holds). P's truth is runtime-checked OR the declarer's responsibility (mode stated).
  • PARTIAL and ASYMPTOTIC redefine what a fold IS, so they redefine the NUMBER — partial reports a statement-level/
    fraction denominator; asymptotic reports an ORDER reduction (O(N²)→O(N)) — both DISTINCT from whole-loop closed-form.
  • RECURSIVE is composition to a FIXPOINT — additive-with-overlap (per §AA-W2), never multiplicative, and must TERMINATE
    (a measured cap + a well-founded progress measure).

  F1 profile_fold · F2 spec_fold · F3 partial_fold · F4 asymptotic_fold · F5 recursive_fold · inputfold_report.
★ Fold rate = APPLIED not issued; fold-rate ≠ speedup; scope always stated; the fallback invariant for profiles; LLM-free;
the pigeonhole wall stands (profile folds structured-under-W, spec folds structured-by-declaration; neither folds random).
Zero-dep (`forbidden_present == []`); never imported by test_build.
"""
