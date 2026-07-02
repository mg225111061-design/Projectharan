"""
PRESBURGER / linear-integer-arithmetic validity — a mature decision procedure (Constitution §4.8/§8, mechanism
2+3). Decides ∀ (x∈ℤⁿ). φ(x) over (ℤ, +, <, =) via Z3 (the trusted oracle, §2 TCB): φ is valid iff ¬φ is UNSAT;
a counterexample model is the witness when it is not. EXACT True/False, or DECLINE if Z3 returns unknown / the
goal isn't encodable as linear integer arithmetic. (Direct z3 API — bypasses the finicky z3_adapter string parser.)
"""
from __future__ import annotations

from typing import Dict, List, Optional

import kernel_verdict as KV

try:
    import z3
    _Z3 = True
except Exception:  # noqa: BLE001
    _Z3 = False


_SAFE = {  # only arithmetic/relational names reach eval; z3 overloads the operators
    "min": min, "max": max, "abs": abs,
}


def _to_z3(goal: str, ints: Dict[str, "z3.ArithRef"]):
    """Parse `goal` into a z3 expression by evaluating it with the z3 Int vars in scope (operators are z3-overloaded).
    Restricted builtins; raises on anything unparseable."""
    return eval(goal.replace("^", "**"), {"__builtins__": {}, **_SAFE}, dict(ints))  # noqa: S307


def presburger_decide(goal: str, int_vars: List[str], assumptions: Optional[List[str]] = None) -> KV.Verdict:
    """∀ (int_vars ∈ ℤ). (assumptions ⇒ goal). EXACT True (UNSAT negation) / EXACT False (+ counterexample) / DECLINE."""
    if not _Z3:
        return KV.decline("presburger: z3 unavailable", "presburger_qe")
    try:
        ints = {v: z3.Int(v) for v in int_vars}
        g = _to_z3(goal, ints)
        hyp = [_to_z3(a, ints) for a in (assumptions or [])]
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"presburger: could not encode as linear integer arithmetic ({type(e).__name__})", "presburger_qe")
    s = z3.Solver()
    s.set("timeout", 5000)
    # validity of (∧hyp ⇒ g)  ⟺  UNSAT of (∧hyp ∧ ¬g)
    for h in hyp:
        s.add(h)
    s.add(z3.Not(g))
    r = s.check()
    if r == z3.unsat:
        cert = KV.Cert(KV.EXACT, "presburger_unsat", passed=True, check_cost="z3 UNSAT proof (trusted oracle)",
                       detail=f"∀{int_vars}. {goal} is VALID (¬goal UNSAT)")
        return KV.exact(True, "presburger_qe", "Presburger QE (Z3, EXACT)", cert)
    if r == z3.sat:
        m = s.model()
        cex = {v: m[ints[v]].as_long() if m[ints[v]] is not None else None for v in int_vars}
        cert = KV.Cert(KV.EXACT, "presburger_counterexample", passed=True, check_cost="z3 model (re-checkable)",
                       detail=f"NOT valid; counterexample {cex}")
        return KV.exact(False, "presburger_qe", "Presburger QE (Z3, EXACT)", cert)
    return KV.decline(f"presburger: z3 returned {r} (timeout/unknown) — honest DECLINE", "presburger_qe")
