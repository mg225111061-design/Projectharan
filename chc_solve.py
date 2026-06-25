"""
CAPSTONE bypass (우회군 B) — CHC / IC3-PDR via z3 Spacer, with INDEPENDENT invariant re-verification.
====================================================================================================
Where k-induction needs the property to already be k-inductive, Spacer SYNTHESIZES a strengthening — an inductive
invariant Inv with: init ⇒ Inv,  Inv ∧ trans ⇒ Inv',  Inv ⇒ prop. That recovers reachability structure (M13
least-fixpoint) for safety problems k-induction returns UNKNOWN on.

★ CERTIFICATE (per-instance, §7): we do NOT trust Spacer's search — we EXTRACT the synthesized invariant and
  RE-VERIFY all three Horn conditions with a FRESH z3 Solver (independent of the fixedpoint engine). EXACT only if
  the three re-checks pass; if extraction/re-check fails ⇒ honest DECLINE (never an unverified SAFE). ★

Interface mirrors ic3_pdr: init/trans/prop are builders over a state dict {varname: z3.Int}.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

import kernel_verdict as KV


@dataclass
class CHCVerdict:
    status: str                       # SAFE | UNSAFE | UNKNOWN
    invariant: str = ""
    detail: str = ""


def prove_safety_chc(varnames: List[str], init: Callable, trans: Callable, prop: Callable) -> CHCVerdict:
    """Solve a safety CHC with Spacer and re-verify the synthesized invariant independently."""
    import z3
    n = len(varnames)
    fp = z3.Fixedpoint()
    fp.set(engine="spacer")
    Inv = z3.Function("Inv", *([z3.IntSort()] * n + [z3.BoolSort()]))
    fp.register_relation(Inv)
    xs = [z3.Int(v) for v in varnames]
    xps = [z3.Int(v + "!p") for v in varnames]
    for v in xs + xps:
        fp.declare_var(v)
    s = {varnames[i]: xs[i] for i in range(n)}
    sp = {varnames[i]: xps[i] for i in range(n)}
    fp.add_rule(Inv(*xs), init(s))
    fp.add_rule(Inv(*xps), z3.And(Inv(*xs), trans(s, sp)))
    res = fp.query(z3.And(Inv(*xs), z3.Not(prop(s))))
    if res == z3.sat:
        return CHCVerdict("UNSAFE", detail="Spacer found the property reachable (counterexample exists)")
    if res != z3.unsat:
        return CHCVerdict("UNKNOWN", detail="Spacer returned unknown")
    # ── extract the invariant and RE-VERIFY the three Horn conditions with a fresh solver ──
    try:
        ans = fp.get_answer()
        body = ans.body() if z3.is_quantifier(ans) else ans     # ForAll([..], Inv(vars) == formula)
        if not (z3.is_app(body) and body.num_args() == 2):
            return CHCVerdict("UNKNOWN", detail="could not parse Spacer's invariant for re-verification")
        inv_formula = body.arg(1)                               # RHS of Inv(Var0..Var_{n-1}) == formula
        # de-Bruijn index order is ambiguous a priori (ForAll([A,B]) → A=Var(1),B=Var(0)); try both positional
        # orderings and accept the one for which init ⇒ Inv actually holds (a SOUND disambiguation).
        for perm in (list(range(n)), list(reversed(range(n)))):
            sub_x = [xs[perm[i]] for i in range(n)]
            sub_xp = [xps[perm[i]] for i in range(n)]
            I_x = z3.substitute_vars(inv_formula, *sub_x)
            I_xp = z3.substitute_vars(inv_formula, *sub_xp)
            c0 = z3.Solver(); c0.add(z3.And(init(s), z3.Not(I_x)))
            if c0.check() != z3.unsat:                          # wrong ordering (or invariant fails init) — try the other
                continue
            c1 = z3.Solver(); c1.add(z3.And(I_x, trans(s, sp), z3.Not(I_xp)))   # Inv ∧ trans ⇒ Inv'
            c2 = z3.Solver(); c2.add(z3.And(I_x, z3.Not(prop(s))))             # Inv ⇒ prop
            if c1.check() == z3.unsat and c2.check() == z3.unsat:
                return CHCVerdict("SAFE", invariant=str(inv_formula),
                                  detail="invariant re-verified: init⇒Inv, Inv∧trans⇒Inv', Inv⇒prop (fresh solver)")
        return CHCVerdict("UNKNOWN", detail="invariant extracted but independent re-verification did not pass")
    except Exception as e:  # noqa: BLE001
        return CHCVerdict("UNKNOWN", detail=f"invariant re-verification error: {type(e).__name__}: {e}")


def chc_grade(varnames, init, trans, prop) -> KV.Verdict:
    """Grade a CHC safety query: SAFE (invariant independently re-verified) ⇒ EXACT; UNSAFE ⇒ EXACT decision;
    UNKNOWN / unverifiable ⇒ honest DECLINE."""
    v = prove_safety_chc(varnames, init, trans, prop)
    if v.status == "SAFE":
        cert = KV.Cert(KV.EXACT, "fixpoint_inductive", passed=True,
                       check_cost="fresh-solver re-check of init⇒Inv, Inv∧trans⇒Inv', Inv⇒prop",
                       detail=f"Spacer-synthesized inductive invariant, independently re-verified: {v.invariant}")
        return KV.exact({"safe": True, "invariant": v.invariant}, "chc_spacer", "CHC/Spacer", cert)
    if v.status == "UNSAFE":
        cert = KV.Cert(KV.EXACT, "reachability_counterexample", passed=True, check_cost="Spacer reachability",
                       detail=v.detail)
        return KV.exact({"safe": False}, "chc_spacer", "CHC/Spacer", cert)
    return KV.decline(f"chc_spacer: {v.detail} ⇒ honest DECLINE", "chc_spacer")
