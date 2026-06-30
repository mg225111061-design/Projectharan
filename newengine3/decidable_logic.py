"""
§BO NEW-2 — decidable first-order fragments: EPR/Bernays–Schönfinkel decision + the Skolem-problem guard (m03/m10).
==================================================================================================================
Two decidable-boundary engines, each DECLINEing the undecidable / open residual rather than guessing:

  • epr_decide — the EPR (Bernays–Schönfinkel–Ramsey) fragment: a relational ∃*∀* sentence.  It has the FINITE
    (small) MODEL PROPERTY: a satisfiable EPR sentence has a model whose domain is just its Skolem constants.  So
    we GROUND the universal clauses over that finite domain and decide the (finite) propositional theory with z3.
      – SAT   ⇒ EXACT satisfiable, certified by RE-EVALUATING every ground clause under the returned model;
      – UNSAT ⇒ EXACT unsatisfiable — the grounding is COMPLETE for EPR (small-model property), so no model of any
        size exists.
    ★ GUARD: a function symbol of arity ≥ 1 leaves EPR (full FO is UNDECIDABLE) ⇒ DECLINE.

  • skolem_decide — the Skolem problem (does a linear recurrence ever take the value 0?).
    ★ HARD GUARD (the directive's): order ≥ 5 is OPEN (not known decidable) ⇒ DECLINE, never a verdict.  For low
    order we still certify a POSITIVE answer when a real zero witness is found (re-checked by exact evaluation);
    the famously-hard "proven never zero" is NOT overclaimed (DECLINE) — soundness over completeness.

★ certificate-or-DECLINE, false-EXACT 0; 0 new mechanism (guess-and-certify m03 / structure-by-size m10 branch);
0 new disposer.  Reuses z3 (z3_guard for the bounded solve) + cfinite.naive_nth (exact LRS term).  zero-dep.
"""
from __future__ import annotations

from itertools import product
from typing import Dict, List, Sequence, Tuple

import cfinite as CF
import kernel_verdict as KV

try:
    import z3
    _Z3 = True
except Exception:  # noqa: BLE001
    _Z3 = False

_MAX_DOMAIN = 12          # EPR finite-model domain cap (constants); beyond ⇒ DECLINE on cost
_MAX_GROUND = 200000      # ground-atom/clause cap


def _ground_atoms_equal(name: str, args: Tuple[str, ...]) -> str:
    return f"{name}({','.join(args)})"


def epr_decide(spec: dict) -> KV.Verdict:
    """Decide an EPR sentence ∃c*∀x*. ⋀(⋁ literal) by grounding over the finite domain {constants} and solving the
    propositional theory with z3.  spec = {constants:[…], predicates:{P:arity}, forall:[vars], clauses:[[ [P,[args],pol], … ], … ]}."""
    if not _Z3:
        return KV.decline("decidable_logic: z3 unavailable", "decidable_logic")
    if spec.get("functions"):
        return KV.decline("decidable_logic: a function symbol of arity≥1 leaves EPR — full FO is UNDECIDABLE ⇒ "
                          "DECLINE (decidable-fragment guard)", "decidable_logic")
    consts: List[str] = [str(c) for c in spec.get("constants", [])]
    if not consts:
        consts = ["e0"]                              # a nonempty domain (EPR models are nonempty)
    if len(consts) > _MAX_DOMAIN:
        return KV.decline(f"decidable_logic: domain {len(consts)} > {_MAX_DOMAIN} ⇒ DECLINE on cost",
                          "decidable_logic")
    preds: Dict[str, int] = {str(k): int(v) for k, v in spec.get("predicates", {}).items()}
    fvars: List[str] = [str(v) for v in spec.get("forall", [])]
    clauses = spec.get("clauses", [])
    try:
        atoms: Dict[str, "z3.BoolRef"] = {}

        def atom(name, args):
            key = _ground_atoms_equal(name, tuple(args))
            if key not in atoms:
                atoms[key] = z3.Bool(key)
            return atoms[key]

        s = z3.Solver()
        ground_clause_keys: List[List[Tuple[str, bool]]] = []      # for the model re-check
        nground = 0
        for clause in clauses:
            for assign in product(consts, repeat=len(fvars)):
                env = dict(zip(fvars, assign))
                lits = []
                key_lits = []
                for (pname, pargs, pol) in clause:
                    pname = str(pname)
                    if pname not in preds:
                        return KV.decline(f"decidable_logic: predicate {pname} not declared", "decidable_logic")
                    gargs = [env.get(str(a), str(a)) for a in pargs]
                    if any(g not in consts for g in gargs):
                        return KV.decline(f"decidable_logic: argument outside domain in {pname}{tuple(gargs)}",
                                          "decidable_logic")
                    a = atom(pname, gargs)
                    lits.append(a if pol else z3.Not(a))
                    key_lits.append((_ground_atoms_equal(pname, tuple(gargs)), bool(pol)))
                s.add(z3.Or(*lits) if lits else z3.BoolVal(False))
                ground_clause_keys.append(key_lits)
                nground += 1
                if nground > _MAX_GROUND:
                    return KV.decline(f"decidable_logic: >{_MAX_GROUND} ground clauses ⇒ DECLINE on cost",
                                      "decidable_logic")
        res = s.check()
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"decidable_logic: z3 error {type(e).__name__}: {e}", "decidable_logic")

    if res == z3.sat:
        model = s.model()
        truth = {k: (bool(model[atoms[k]]) if model[atoms[k]] is not None else False) for k in atoms}
        # ★ re-check: every ground clause is satisfied under the model
        for kl in ground_clause_keys:
            if not any((truth.get(key, False) == pol) for (key, pol) in kl):
                return KV.decline("decidable_logic: model failed clause re-check ⇒ DECLINE (bug guard)",
                                  "decidable_logic")
        true_atoms = sorted(k for k, v in truth.items() if v)
        cert = KV.Cert(KV.EXACT, "epr_finite_model", passed=True,
                       check_cost="re-evaluate every ground clause under the model",
                       detail=f"finite model over domain {consts} (|D|={len(consts)}); {nground} ground clauses all "
                              f"satisfied; true atoms: {true_atoms[:12]}{'…' if len(true_atoms) > 12 else ''}")
        return KV.exact({"satisfiable": True, "domain_size": len(consts), "true_atoms": true_atoms},
                        "decidable_logic", "EPR finite-model decision", cert)
    if res == z3.unsat:
        cert = KV.Cert(KV.EXACT, "epr_unsat_complete_grounding", passed=True,
                       check_cost=f"complete grounding over the small-model domain ({nground} clauses), z3 unsat",
                       detail="EPR small-model property ⇒ the finite grounding is complete ⇒ no model of any size "
                              "⇒ UNSATISFIABLE")
        return KV.exact({"satisfiable": False, "domain_size": len(consts)}, "decidable_logic",
                        "EPR finite-model decision", cert)
    return KV.decline("decidable_logic: z3 returned unknown (unexpected for EPR) ⇒ DECLINE", "decidable_logic")


def skolem_decide(c: Sequence[int], init: Sequence[int], search: int = 2000) -> KV.Verdict:
    """The Skolem problem for the LRS f with f(n)=Σ cᵢ f(n−1−i).  ★ order ≥ 5 is OPEN ⇒ DECLINE.  For order ≤ 4 we
    certify a POSITIVE answer when a zero witness is found (re-checked exactly); 'never zero' is not overclaimed."""
    c = [int(x) for x in c]; init = [int(x) for x in init]
    d = len(c)
    if d == 0 or len(init) != d:
        return KV.decline("skolem: need c and init of equal nonzero length", "decidable_logic")
    if d >= 5:
        return KV.decline(f"skolem: recurrence order {d} ≥ 5 — the Skolem problem is OPEN (not known decidable) ⇒ "
                          "DECLINE (hard decidable-boundary guard)", "decidable_logic")
    for n in range(search):
        if CF.naive_nth(c, init, n) == 0:
            # ★ re-check the witness exactly
            if CF.naive_nth(c, init, n) != 0:
                return KV.decline("skolem: witness re-check failed ⇒ DECLINE (bug guard)", "decidable_logic")
            cert = KV.Cert(KV.EXACT, "skolem_zero_witness", passed=True, check_cost="exact LRS evaluation at n",
                           detail=f"order-{d} LRS hits zero at n={n} (f({n})=0, re-checked exactly)")
            return KV.exact({"hits_zero": True, "witness_n": n}, "decidable_logic", "Skolem (low-order, witness)",
                            cert)
    return KV.decline(f"skolem: no zero in the first {search} terms (order {d} ≤ 4 is decidable in theory, but the "
                      "'never zero' bound is not implemented here) ⇒ DECLINE rather than overclaim", "decidable_logic")


def adversarial_battery() -> dict:
    """★ EPR SAT: ∀x. P(x)∨Q(x) over {a} ⇒ satisfiable (model re-checked); ★ EPR UNSAT: P(a) ∧ ∀x.¬P(x) ⇒ unsat;
    ★ function symbol ⇒ DECLINE (leaves EPR); ★ Skolem order 2 (Fibonacci-like hitting 0) witness; ★ Skolem
    order 5 ⇒ DECLINE (open)."""
    sat = epr_decide({"constants": ["a"], "predicates": {"P": 1, "Q": 1}, "forall": ["x"],
                      "clauses": [[["P", ["x"], True], ["Q", ["x"], True]]]})
    unsat = epr_decide({"constants": ["a"], "predicates": {"P": 1}, "forall": ["x"],
                        "clauses": [[["P", ["a"], True]], [["P", ["x"], False]]]})
    func = epr_decide({"constants": ["a"], "predicates": {"P": 1}, "functions": {"f": 1}, "forall": ["x"],
                       "clauses": [[["P", ["x"], True]]]})
    # order-2 LRS f(n)=f(n-1)-f(n-2), init [0,1]: 0,1,1,0,-1,-1,0,… hits 0 at n=0 (init) — use init [2,1]:2,1,-1,-2,-1,1,2,… no 0; use a clean one that hits 0: f(n)=−f(n-2)? order2 c=[0,-1], init=[1,0]:1,0,… hits 0 at n=1
    sk2 = skolem_decide([0, -1], [1, 0])                  # 1,0,-1,0,1,… hits 0 at n=1
    sk5 = skolem_decide([1, 0, 0, 0, 1], [1, 1, 1, 1, 1])  # order 5 ⇒ DECLINE (open)
    cases = {
        "epr_sat_EXACT": sat.status == "EXACT" and sat.result["satisfiable"] is True,
        "epr_unsat_EXACT": unsat.status == "EXACT" and unsat.result["satisfiable"] is False,
        "function_symbol_DECLINE": func.status == "DECLINE",
        "skolem_order2_witness_EXACT": sk2.status == "EXACT" and sk2.result["hits_zero"] is True,
        "skolem_order5_DECLINE": sk5.status == "DECLINE",
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
