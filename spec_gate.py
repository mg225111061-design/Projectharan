"""
STAGE 1.3 — Clover-style spec consistency gate (ACCURACY · SOUND).
==================================================================
"PROVEN" only means something if the SPEC means something. A vacuous spec — `ensures true`,
`ensures result = result`, a self-tautology, or a contradictory `requires` — is satisfied (or
vacuously satisfied) by *any* implementation, so proving code against it is worthless. This gate
catches that BEFORE the fix loop / proof, so HARAN never hands out a "PROVEN" that rests on a spec
that constrains nothing (the §1.7 honesty bar; the §6 anti-"spec-gaming" rule).

The decision is a real Z3 decision procedure, not a keyword guess. Treating `result` and the params
as free variables over the spec's arithmetic domain:

  VACUOUS_TRUE     ¬(ensures) is UNSAT  → the spec is valid (always true) → constrains nothing.
  CONTRADICTORY    (ensures) is UNSAT   → no implementation can ever satisfy it.
  VACUOUS_PRECOND  (requires) is UNSAT  → precondition false → every obligation is vacuously true.
  OK               ensures is satisfiable AND falsifiable → it genuinely constrains `result`.
  UNMODELED        spec uses lists / opaque calls Z3 can't model here → we DON'T judge it (no false
                   reject); the downstream verifier handles it. SOUND: we only reject demonstrable vacuity.

★ No false positives by construction: a spec is rejected only when Z3 *proves* it vacuous/contradictory
  (an unsat result). Anything Z3 can't settle passes through. Measured FP rate on real specs = 0.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import haran_ast as A
import z3_adapter as Z


@dataclass
class GateVerdict:
    kind: str        # OK | VACUOUS_TRUE | CONTRADICTORY | VACUOUS_PRECOND | UNMODELED | NO_SPEC
    reason: str

    def vacuous(self) -> bool:
        """True iff the spec was PROVEN meaningless and a 'PROVEN' against it must be rejected."""
        return self.kind in ("VACUOUS_TRUE", "CONTRADICTORY", "VACUOUS_PRECOND")

    def __str__(self):
        return f"{self.kind} — {self.reason}"


def _result_type(fn) -> str:
    ret = getattr(fn, "ret", None)
    if isinstance(ret, A.TyName) and ret.name in ("Float", "Real", "rat"):
        return "Real"
    return "Int"   # Nat/Int/Bool-ish → Int domain (Bool specs encode fine over Int-typed result too)


def _var_types(fn) -> Dict[str, str]:
    vt: Dict[str, str] = {}
    for p in fn.params:
        if isinstance(p.ty, A.TyName) and p.ty.name in ("Float", "Real", "rat"):
            vt[p.name] = "Real"
        elif isinstance(p.ty, A.TyName) and p.ty.name in ("Int", "Nat"):
            vt[p.name] = "Int"
        # list/own/other params are simply left unmodeled (their absence forces UNMODELED if referenced)
    vt["result"] = _result_type(fn)
    return vt


def gate_spec(fn) -> GateVerdict:
    """Classify fn's spec. Pure decision procedure (Z3) — see module docstring for the categories."""
    if not Z.z3_available():
        return GateVerdict("UNMODELED", "Z3 unavailable")
    if fn.ensures is None:
        return GateVerdict("NO_SPEC", "no ensures clause")
    import z3
    vt = _var_types(fn)
    real = all(t == "Real" for t in vt.values()) or not vt
    env = {n: (z3.Real(n) if t == "Real" else z3.Int(n)) for n, t in vt.items()}

    # Encode ensures (and requires, if present). Anything Z3 can't model → UNMODELED (no judgment).
    try:
        P = Z._to_z3(fn.ensures, env, real)
        R = Z._to_z3(fn.requires, env, real) if fn.requires is not None else None
    except Z._Unsupported as e:
        return GateVerdict("UNMODELED", f"spec not Z3-modelable ({e}) — passed through, not judged")

    def _check(*constraints):
        s = z3.Solver()
        s.set("timeout", 5000)
        for c in constraints:
            s.add(c)
        return s.check()

    # 1. contradictory precondition → every obligation vacuously holds
    if R is not None and _check(R) == z3.unsat:
        return GateVerdict("VACUOUS_PRECOND", "requires is UNSAT (precondition false → vacuous proof)")

    asm = [R] if R is not None else []
    # 2. vacuous-true: ¬ensures unsat (under requires) → spec is valid → constrains nothing
    if _check(*asm, z3.Not(P)) == z3.unsat:
        return GateVerdict("VACUOUS_TRUE", "¬(ensures) is UNSAT → spec always true → constrains nothing")
    # 3. contradictory: ensures unsat (under requires) → unsatisfiable spec
    if _check(*asm, P) == z3.unsat:
        return GateVerdict("CONTRADICTORY", "ensures is UNSAT → no implementation can satisfy it")
    return GateVerdict("OK", "spec is satisfiable and falsifiable — it genuinely constrains result")


def is_vacuous(fn) -> bool:
    return gate_spec(fn).vacuous()


# --------------------------------------------------------- measurement
def measure_gate(corpus) -> dict:
    """corpus: list of (label, haran_src, expect_vacuous: bool). Returns measured TP/FP/etc.
    FP = a REAL spec wrongly flagged vacuous (must be 0). TP = a vacuous spec correctly caught."""
    from haran_parser import parse
    tp = fp = tn = fn_ = unmodeled = 0
    rows = []
    for label, src, expect_vac in corpus:
        prog = parse(src)
        fns = [it for it in prog.items if isinstance(it, A.FnDecl)]
        if not fns:
            rows.append((label, "PARSE_ERROR", expect_vac)); continue
        v = gate_spec(fns[0])
        flagged = v.vacuous()
        rows.append((label, v.kind, expect_vac))
        if v.kind == "UNMODELED":
            unmodeled += 1
        if expect_vac and flagged:
            tp += 1
        elif expect_vac and not flagged:
            fn_ += 1
        elif (not expect_vac) and flagged:
            fp += 1
        else:
            tn += 1
    n = len(corpus)
    return {"n": n, "true_pos": tp, "false_pos": fp, "true_neg": tn, "false_neg": fn_,
            "unmodeled": unmodeled, "rows": rows,
            "fp_rate": round(fp / n, 3) if n else 0.0,
            "catch_rate": round(tp / (tp + fn_), 3) if (tp + fn_) else 0.0}


if __name__ == "__main__":
    from test_build import SPEC_GATE_CORPUS
    m = measure_gate(SPEC_GATE_CORPUS)
    for label, kind, exp in m["rows"]:
        tag = "vac" if exp else "real"
        print(f"  [{tag:4s}] {label:28s} → {kind}")
    print(f"\n  n={m['n']}  caught {m['true_pos']}/{m['true_pos']+m['false_neg']} vacuous "
          f"(catch_rate={m['catch_rate']}), false_pos={m['false_pos']} (rate={m['fp_rate']}), "
          f"unmodeled={m['unmodeled']}")
