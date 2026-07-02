"""
§BO NEW-3 — Boolean CSP complexity by Schaefer's dichotomy: polymorphism-closure classification (m09/m10, Axis B).
==================================================================================================================
Schaefer's theorem (1978): a Boolean constraint-satisfaction problem CSP(Γ) is in P if EVERY relation of Γ is one
of — 0-valid, 1-valid, Horn (closed under ∧), dual-Horn (closed under ∨), bijunctive (closed under majority), or
affine (closed under x⊕y⊕z) — and is NP-COMPLETE otherwise.  Each tractable class is a POLYMORPHISM closure that
is cheap to CHECK (Axis B): test the relation's tuples are closed under the operation.

  • P            ⇒ EXACT 'tractable', certified by the surviving polymorphism (the closure re-verified on Γ);
  • NP-complete  ⇒ EXACT 'NP-complete', certified by SIX witnesses — one violating each tractable class (missing
    all-0 / all-1, an ∧- / ∨- / majority- / minority-closure failure) — re-checked; failing all six ⟺ NPC.

★ HARD GUARDS (the directive's):
  • PROMISE CSP (PCSP) is ABSOLUTELY FORBIDDEN — its dichotomy is OPEN in general ⇒ DECLINE on any promise/pcsp
    spec, never a verdict.
  • non-Boolean (domain > 2) CSP: the Bulatov–Zhuk dichotomy holds, but the general polymorphism test is not
    implemented here ⇒ DECLINE (we classify only the complete Boolean Schaefer fragment).

★ certificate-or-DECLINE, false-EXACT 0; 0 new mechanism (complete-invariant m09 / structure-by-size m10 branch —
the polymorphism is the complete classifying invariant); 0 new disposer.  zero-dep (stdlib only).
"""
from __future__ import annotations

from typing import List, Sequence, Tuple

import kernel_verdict as KV

Tup = Tuple[int, ...]
Rel = List[Tup]


def _and(a: Tup, b: Tup) -> Tup:
    return tuple(x & y for x, y in zip(a, b))


def _or(a: Tup, b: Tup) -> Tup:
    return tuple(x | y for x, y in zip(a, b))


def _xor3(a: Tup, b: Tup, c: Tup) -> Tup:
    return tuple((x ^ y ^ z) for x, y, z in zip(a, b, c))


def _maj(a: Tup, b: Tup, c: Tup) -> Tup:
    return tuple(1 if (x + y + z) >= 2 else 0 for x, y, z in zip(a, b, c))


def _closed_binary(R: Rel, op) -> Tuple[bool, object]:
    S = set(R)
    for a in R:
        for b in R:
            if op(a, b) not in S:
                return False, (a, b, op(a, b))
    return True, None


def _closed_ternary(R: Rel, op) -> Tuple[bool, object]:
    S = set(R)
    for a in R:
        for b in R:
            for c in R:
                if op(a, b, c) not in S:
                    return False, (a, b, c, op(a, b, c))
    return True, None


def _all(rels: List[Rel], pred):
    """(holds_for_all, witness_of_first_failure_or_None)."""
    for R in rels:
        ok, w = pred(R)
        if not ok:
            return False, (R, w)
    return True, None


def classify(relations: Sequence[Sequence[Sequence[int]]]) -> KV.Verdict:
    """EXACT 'tractable' (P) with the surviving Schaefer polymorphism, or EXACT 'NP-complete' with six refuting
    witnesses; DECLINE on malformed / non-Boolean input."""
    rels: List[Rel] = []
    for R in relations:
        rr = [tuple(int(x) for x in t) for t in R]
        if rr and any(len(t) != len(rr[0]) for t in rr):
            return KV.decline("csp: relation has tuples of differing arity", "csp_dichotomy")
        if any(x not in (0, 1) for t in rr for x in t):
            return KV.decline("csp: non-Boolean value — domain>2 CSP dichotomy holds but is not classified here ⇒ "
                              "DECLINE (Boolean Schaefer fragment only)", "csp_dichotomy")
        rels.append(rr)
    if not rels:
        return KV.decline("csp: empty constraint language", "csp_dichotomy")

    zero_valid, w0 = _all(rels, lambda R: (tuple(0 for _ in R[0]) in set(R), tuple(0 for _ in R[0])))
    one_valid, w1 = _all(rels, lambda R: (tuple(1 for _ in R[0]) in set(R), tuple(1 for _ in R[0])))
    horn, wh = _all(rels, lambda R: _closed_binary(R, _and))
    dual_horn, wd = _all(rels, lambda R: _closed_binary(R, _or))
    affine, wa = _all(rels, lambda R: _closed_ternary(R, _xor3))
    bijunctive, wb = _all(rels, lambda R: _closed_ternary(R, _maj))

    classes = {"0-valid": zero_valid, "1-valid": one_valid, "Horn(∧)": horn, "dual-Horn(∨)": dual_horn,
               "affine(⊕)": affine, "bijunctive(maj)": bijunctive}
    surviving = [k for k, v in classes.items() if v]
    if surviving:
        cert = KV.Cert(KV.EXACT, "schaefer_polymorphism", passed=True,
                       check_cost="re-verify the closure of every relation under the surviving polymorphism",
                       detail=f"CSP(Γ) ∈ P: every relation is {surviving[0]}"
                              f"{' (also '+', '.join(surviving[1:])+')' if len(surviving) > 1 else ''} ⇒ tractable")
        return KV.exact({"tractable": True, "in_P": True, "classes": surviving}, "csp_dichotomy",
                        "Schaefer dichotomy", cert)
    # NP-complete: all six fail — record one witness each (re-checkable)
    witnesses = {"not_0valid": str(w0), "not_1valid": str(w1), "not_Horn": str(wh), "not_dualHorn": str(wd),
                 "not_affine": str(wa), "not_bijunctive": str(wb)}
    cert = KV.Cert(KV.EXACT, "schaefer_npc_witnesses", passed=True,
                   check_cost="six closure-failure witnesses, each re-checked",
                   detail=f"every Schaefer tractable class fails (witnesses: {witnesses}) ⇒ CSP(Γ) is NP-COMPLETE")
    return KV.exact({"tractable": False, "in_P": False, "np_complete": True, "witnesses": witnesses},
                    "csp_dichotomy", "Schaefer dichotomy", cert)


def csp_grade(payload) -> KV.Verdict:
    """Route + the hard guards.  {relations:[…]} ⇒ classify; a promise/pcsp spec ⇒ DECLINE (forbidden)."""
    if isinstance(payload, dict):
        if "pcsp" in payload or "promise" in payload or ("templateA" in payload and "templateB" in payload):
            return KV.decline("csp: PROMISE CSP (PCSP) is forbidden — its dichotomy is OPEN in general ⇒ DECLINE",
                              "csp_dichotomy")
        if "relations" in payload:
            return classify(payload["relations"])
        return KV.decline("csp: expected {relations:[…]}", "csp_dichotomy")
    return classify(payload)


def adversarial_battery() -> dict:
    """★ 2-SAT relations (bijunctive) ⇒ tractable; ★ affine (XOR) relation ⇒ tractable; ★ 1-in-3 / NAE-style
    relation ⇒ NP-complete (six witnesses); ★ a PCSP spec ⇒ DECLINE (forbidden); ★ non-Boolean ⇒ DECLINE."""
    # implication x→y as a binary relation {(0,0),(0,1),(1,1)} — bijunctive (2-SAT)
    impl = [(0, 0), (0, 1), (1, 1)]
    twosat = classify([impl])
    # XOR relation {(0,1),(1,0)} — affine
    xor = classify([[(0, 1), (1, 0)]])
    # 1-in-3 (R(x,y,z): exactly one true) {(1,0,0),(0,1,0),(0,0,1)} — NP-complete (positive 1-in-3 SAT)
    one_in_three = classify([[(1, 0, 0), (0, 1, 0), (0, 0, 1)]])
    pcsp = csp_grade({"pcsp": True, "relations": [impl]})
    nonbool = classify([[(0, 2), (1, 0)]])
    cases = {
        "twosat_tractable_EXACT": twosat.status == "EXACT" and twosat.result["in_P"] is True
                                  and "bijunctive(maj)" in twosat.result["classes"],
        "xor_affine_tractable_EXACT": xor.status == "EXACT" and "affine(⊕)" in xor.result["classes"],
        "one_in_three_NPC_EXACT": one_in_three.status == "EXACT" and one_in_three.result.get("np_complete") is True,
        "pcsp_DECLINE": pcsp.status == "DECLINE",
        "nonboolean_DECLINE": nonbool.status == "DECLINE",
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
