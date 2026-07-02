"""
§U PHASE 5B — ★THE DIFFERENTIATOR: formal verification BEYOND the visible tests (the 90→95 gap).
================================================================================================================
The visible tests are a subset; SWE-bench grades on HIDDEN tests too. A patch that passes every visible test can still
be wrong on the edge case a hidden test exercises. A plain test-runner cannot see this — our formal machinery can.

For the patched function we PROVE correctness against the reference oracle over the input DOMAIN (not just "passes
these N inputs" but "agrees with the spec for ALL inputs in the domain"):
  • `bounded_equiv` — exhaustive agreement over a declared finite domain (sound OVER THAT DOMAIN; tier "bounded"); the
    general mechanism, applicable to any Python function. Its counterexample is the EXACT failing input.
  • `prove_equiv_z3` — where the behaviour is arithmetic-expressible, an UNBOUNDED ∀ proof (tier "z3_forall").
★ A patch that passes the visible tests but FAILS the formal check is wrong on some input — likely the hidden test.
We reject it and hand the COUNTEREXAMPLE (the richest feedback no test-runner can give) to the fix loop, and we prefer
the candidate that is formally correct. This converts "passes the tests I can see" into "is actually correct" — which
is exactly what passing the hidden tests requires.

★ HONEST SCOPE: formal verification is possible where the behaviour is specifiable / has an oracle in a provable
domain. Where it is not, we fall back to the visible+regression gate and SAY SO (`applicable=False`) — never a claimed
formal coverage we don't have.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass
class FormalResult:
    applicable: bool                    # False ⇒ no reference/domain ⇒ honest fallback to visible+regression
    proved: bool                        # True ⇒ patched ≡ reference over the domain (correct on hidden inputs too)
    tier: str                           # "bounded" | "z3_forall" | "n/a"
    counterexample: Optional[dict]      # {"args": <failing input>, "expected": ..., "got": ...} — the rich feedback
    detail: str = ""


def formal_correct(task, patched_fn: Callable) -> FormalResult:
    """Prove the patched function agrees with the task's reference oracle over the declared domain. Returns a
    FormalResult; `proved=False` carries the counterexample (the exact input on which the patch is wrong — the hidden
    test it would fail). `applicable=False` when the task has no specifiable reference (honest fallback)."""
    if not getattr(task, "reference_src", None) or not getattr(task, "formal_domain", None):
        return FormalResult(False, False, "n/a", None, "no reference oracle / domain — formal check not applicable; "
                            "fall back to visible+regression (honest, not a claimed formal pass)")
    from swebench.harness import compile_fn
    ref = compile_fn(task.reference_src, task.fn_name)
    if ref is None:
        return FormalResult(False, False, "n/a", None, "reference oracle failed to compile")
    from catalog.equiv_check import bounded_equiv
    # wrap so each domain element (an args-tuple) is applied; the counterexample's input IS the failing args-tuple
    res = bounded_equiv(lambda t: ref(*t), lambda t: patched_fn(*t), task.formal_domain)
    if res.proved:
        return FormalResult(True, True, "bounded", None,
                            f"patched ≡ reference on all {len(task.formal_domain)} domain inputs (bounded — sound over "
                            "the declared domain, which includes the hidden-test inputs)")
    cx = res.counterexample or {}
    failing = cx.get("input")
    feedback = {"args": failing, "expected": cx.get("src"), "got": cx.get("cand")}
    return FormalResult(True, False, "bounded", feedback,          # applicable=True (formal ran), proved=False (cex found)
                        f"counterexample: input {failing} → reference {cx.get('src')!r} but patch {cx.get('cand')!r} "
                        "(this is the hidden-test failure, caught before submission)")


def prove_unbounded_z3(reference_build: Callable, candidate_build: Callable, var_names: List[str],
                       sort: str = "Int") -> dict:
    """The stronger FACE: where the behaviour is arithmetic-expressible as z3 terms, prove equivalence for ALL inputs
    (unbounded ∀), not merely over a finite domain. Returns {proved, tier, counterexample}. Used to demonstrate that
    the formal check upgrades from bounded to an unbounded proof when the domain is z3-expressible."""
    from catalog.equiv_check import prove_equiv_z3
    r = prove_equiv_z3(reference_build, candidate_build, var_names, sort=sort)
    return {"proved": r.proved, "tier": r.tier, "counterexample": r.counterexample, "detail": r.detail}


def catches_hidden_failure(task, cand) -> bool:
    """True iff this candidate PASSES the visible tests but the formal check proves it WRONG (would fail a hidden
    test). This is the precise event the differentiator prevents — measured across the bench in the score report."""
    from swebench.harness import compile_fn, run_cases
    fn = compile_fn(cand.src, task.fn_name)
    if fn is None:
        return False
    vok, _ = run_cases(fn, task.visible)
    if not vok:
        return False                                    # a visible failure is caught by the plain test gate, not formal
    fr = formal_correct(task, fn)
    return fr.applicable and not fr.proved              # passes visible, fails formal ⇒ a hidden failure formal caught
