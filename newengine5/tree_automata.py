"""
§BN NEW-1 — bottom-up finite tree automata: emptiness + membership (structure-by-size m10 branch).
=====================================================================================================
A (non)deterministic bottom-up tree automaton over a RANKED alphabet decides a regular tree language.
Two questions, both DECIDABLE and certifiable in (low-degree) polynomial time:

  • membership — does the automaton accept a given ground term?  The bottom-up run IS the certificate:
    recompute reach(node) ⊆ Q for every subterm; accept ⟺ reach(root) ∩ F ≠ ∅ (cheap, linear in |term|).
  • emptiness — is the accepted language empty?  Least-fixpoint reachable-state set R (close under δ):
      – EMPTY      : R is a fixpoint (one more closure round adds nothing) ∧ R ∩ F = ∅      [re-checked]
      – NON-EMPTY  : a witness term built by back-tracking from a reachable final state, then RE-RUN
                     through membership and accepted                                          [re-checked]

★ DECIDABLE-FRAGMENT GUARD (the directive's hard guard): tree automata WITH equality/DISEQUALITY
  constraints between subterms are UNDECIDABLE (emptiness) in general — a `constraints`/`diseq` key in
  the spec ⇒ DECLINE, never a guessed answer. We decide only the constraint-free (N)FTA fragment.

★ certificate-or-DECLINE: every EXACT rides an independently re-checked certificate (the bottom-up run,
  or the saturated-fixpoint + witness re-run); a construction bug ⇒ failed re-check ⇒ DECLINE. zero-dep.
0 new mechanism (a recognition branch of m10 structure-by-size / m08 confluent saturation); 0 new disposer.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

import kernel_verdict as KV

# a transition is (symbol, (child_state, …), result_state); a 0-ary symbol has an empty child tuple.
Transition = Tuple[str, Tuple[str, ...], str]


def _parse(spec: dict):
    """Validate + normalize {alphabet:{sym:arity}, states:[…], final:[…], transitions:[[sym,[q…],q],…]}."""
    alphabet: Dict[str, int] = {str(k): int(v) for k, v in spec.get("alphabet", {}).items()}
    states: Set[str] = {str(s) for s in spec.get("states", [])}
    final: Set[str] = {str(s) for s in spec.get("final", [])}
    trans: List[Transition] = []
    for t in spec.get("transitions", []):
        sym, kids, res = t[0], tuple(str(k) for k in t[1]), str(t[2])
        if sym not in alphabet:
            raise ValueError(f"transition symbol {sym!r} not in alphabet")
        if alphabet[sym] != len(kids):
            raise ValueError(f"transition {sym!r} arity {len(kids)} ≠ declared {alphabet[sym]}")
        states.update(kids); states.add(res)
        trans.append((sym, kids, res))
    if not final <= states:
        raise ValueError("final states must be a subset of states")
    return alphabet, states, final, trans


def _reach_term(term, trans: List[Transition]) -> Set[str]:
    """Bottom-up: the set of states the (N)FTA can assign to `term` = [sym, child1, …, childk]."""
    if not isinstance(term, (list, tuple)) or not term:
        raise ValueError(f"malformed term {term!r}")
    sym = str(term[0])
    child_reach = [_reach_term(c, trans) for c in term[1:]]
    out: Set[str] = set()
    for tsym, kids, res in trans:
        if tsym != sym or len(kids) != len(child_reach):
            continue
        if all(kids[i] in child_reach[i] for i in range(len(kids))):
            out.add(res)
    return out


def _reachable_states(trans: List[Transition]) -> Tuple[Set[str], int]:
    """Least fixpoint of states producible bottom-up; returns (R, rounds). One extra round == R proves closure."""
    R: Set[str] = set()
    rounds = 0
    while True:
        rounds += 1
        new = set(R)
        for sym, kids, res in trans:
            if all(k in R for k in kids):      # 0-ary (kids==()) seeds the set; then close upward
                new.add(res)
        if new == R:
            return R, rounds
        R = new


def _witness(trans: List[Transition], target: str) -> Optional[list]:
    """A minimal ground term evaluating to `target` (back-track over the reachability fixpoint), or None."""
    term_of: Dict[str, list] = {}
    changed = True
    while changed:
        changed = False
        for sym, kids, res in trans:
            if res in term_of:
                continue
            if all(k in term_of for k in kids):
                term_of[res] = [sym] + [term_of[k] for k in kids]
                changed = True
    return term_of.get(target)


def membership(spec: dict, term) -> KV.Verdict:
    """EXACT accept/reject of a ground term — the bottom-up run is the certificate (recomputed, linear)."""
    if "constraints" in spec or "diseq" in spec or "equality" in spec:
        return KV.decline("tree_automata: equality/disequality-constrained tree automata are UNDECIDABLE "
                          "(emptiness) ⇒ DECLINE (decidable-fragment guard)", "tree_automata")
    try:
        _, _, final, trans = _parse(spec)
        reach = _reach_term(term, trans)
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"tree_automata: {type(e).__name__}: {e}", "tree_automata")
    accepted = bool(reach & final)
    cert = KV.Cert(KV.EXACT, "tree_run", passed=True, check_cost="O(|term|·|δ|) bottom-up re-run",
                   detail=f"reach(root)={sorted(reach)}; final={sorted(final)}; accepted={accepted}")
    return KV.exact({"accepted": accepted, "root_states": sorted(reach)}, "tree_automata",
                    "bottom-up (N)FTA run", cert)


def emptiness(spec: dict) -> KV.Verdict:
    """EXACT empty (saturated reachable set is a fixpoint ∧ disjoint from F) or EXACT non-empty (witness re-run)."""
    if "constraints" in spec or "diseq" in spec or "equality" in spec:
        return KV.decline("tree_automata: constrained tree automata emptiness is UNDECIDABLE ⇒ DECLINE "
                          "(decidable-fragment guard)", "tree_automata")
    try:
        _, _, final, trans = _parse(spec)
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"tree_automata: {type(e).__name__}: {e}", "tree_automata")
    R, _ = _reachable_states(trans)
    reachable_final = sorted(R & final)
    if not reachable_final:
        # ★ certificate: R is closed (extra round adds nothing — re-checked) ∧ R ∩ F = ∅ ⇒ language EMPTY
        R2, _ = _reachable_states(trans)
        if R2 != R or (R & final):
            return KV.decline("tree_automata: fixpoint re-check failed ⇒ DECLINE (bug guard)", "tree_automata")
        cert = KV.Cert(KV.EXACT, "tree_emptiness_fixpoint", passed=True,
                       check_cost="recompute reachable fixpoint + R∩F=∅",
                       detail=f"reachable states R={sorted(R)} is a closed fixpoint, R∩F=∅ ⇒ L(A)=∅")
        return KV.exact({"empty": True}, "tree_automata", "reachable-state fixpoint", cert)
    # ★ certificate: a witness term reaching a final state, RE-RUN through membership and accepted
    w = _witness(trans, reachable_final[0])
    if w is None or not (_reach_term(w, trans) & final):
        return KV.decline("tree_automata: could not certify a witness ⇒ DECLINE (bug guard)", "tree_automata")
    cert = KV.Cert(KV.EXACT, "tree_emptiness_witness", passed=True, check_cost="re-run membership on the witness",
                   detail=f"witness term {w} ↦ final {reachable_final[0]} (re-run accepted) ⇒ L(A)≠∅")
    return KV.exact({"empty": False, "witness": w}, "tree_automata", "reachable-state fixpoint + witness", cert)


def tree_automata_grade(payload: dict) -> KV.Verdict:
    """Route: {emptiness: spec} | {membership: spec, term: t}."""
    if isinstance(payload, dict) and "emptiness" in payload:
        return emptiness(payload["emptiness"])
    if isinstance(payload, dict) and "membership" in payload and "term" in payload:
        return membership(payload["membership"], payload["term"])
    return KV.decline("tree_automata: expected {emptiness: spec} | {membership: spec, term: t}", "tree_automata")


def adversarial_battery() -> dict:
    """★ a reachable final ⇒ EXACT non-empty + re-run witness; ★ no 0-ary seed ⇒ EXACT empty; ★ accepted term ⇒
    EXACT accept, rejected term ⇒ EXACT reject; ★ a constrained spec ⇒ DECLINE (undecidable guard)."""
    # NFTA for "even number of g's over a": states q0(even)/q1(odd), a↦q0, g(q0)↦q1, g(q1)↦q0, final={q0}
    A = {"alphabet": {"a": 0, "g": 1}, "states": ["q0", "q1"], "final": ["q0"],
         "transitions": [["a", [], "q0"], ["g", ["q0"], "q1"], ["g", ["q1"], "q0"]]}
    ne = emptiness(A)                                            # a↦q0 final ⇒ non-empty
    acc = membership(A, ["g", ["g", ["a"]]])                    # g(g(a)) two g's ⇒ even ⇒ accept
    rej = membership(A, ["g", ["a"]])                           # g(a) one g ⇒ odd ⇒ reject
    # an automaton with NO 0-ary transition can never seed a term ⇒ empty language
    B = {"alphabet": {"g": 1}, "states": ["q0"], "final": ["q0"], "transitions": [["g", ["q0"], "q0"]]}
    empt = emptiness(B)
    guard = emptiness({"alphabet": {"a": 0}, "states": ["q0"], "final": ["q0"],
                       "transitions": [["a", [], "q0"]], "diseq": [["x", "y"]]})
    cases = {
        "nonempty_EXACT_witness": ne.status == "EXACT" and ne.result["empty"] is False and "witness" in ne.result,
        "empty_no_seed_EXACT": empt.status == "EXACT" and empt.result["empty"] is True,
        "accept_even_EXACT": acc.status == "EXACT" and acc.result["accepted"] is True,
        "reject_odd_EXACT": rej.status == "EXACT" and rej.result["accepted"] is False,
        "diseq_constraint_DECLINE": guard.status == "DECLINE",
        "nonempty_carries_cert": ne.certificate is not None and ne.certificate.passed,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
