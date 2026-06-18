"""
v26 STAGE 3 — incorrectness-logic bug-existence checker (UX, zero false positives by construction).
====================================================================================================
The dual of verification: instead of proving a bug ABSENT (over-approximate, OX), prove a bug PRESENT
(under-approximate, UX — O'Hearn POPL 2020). Here: reachable division/modulo-by-zero. For each `/`/`%`,
ask Z3 whether some input satisfying `requires` AND the path condition to that operation makes the
denominator 0. If SAT, the Z3 model is a concrete WITNESS → BUG_REACHABLE. Because the witness is a real
model of (requires ∧ path ∧ denom=0), there are **zero false positives by construction**.

Verdicts:  BUG_REACHABLE (class + witness) | NO_BUG_FOUND | UNMODELED (e.g. requires not encodable).

★ HONEST LABELS (§1.8) ★:
  • This is UX (under-approximation). `NO_BUG_FOUND` is **NOT** a proof of absence — it means this
    under-approximate search found none (other bug classes, or regions it doesn't analyze, may hide bugs).
  • Path-sensitive & sound: a division guarded by a branch (e.g. `match b {0 => .. _ => a/b}`) is NOT
    reported (its path condition `b≠0` makes `denom=0` unsat). Divisions inside list/ADT-pattern arms or
    fold bodies are NOT analyzed (skipped, never falsely reported) to keep FP=0.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import haran_ast as A
import z3_adapter as Z
from haran_parser import parse


@dataclass
class BugVerdict:
    status: str                         # BUG_REACHABLE | NO_BUG_FOUND | UNMODELED | PARSE_ERROR | NONE
    bugs: List[dict] = field(default_factory=list)   # [{cls, line, witness}]
    detail: str = ""

    def __str__(self):
        if self.status == "BUG_REACHABLE":
            b = self.bugs[0]
            return f"BUG_REACHABLE ({len(self.bugs)}): {b['cls']} at line {b['line']} — witness {b['witness']} (UX)"
        if self.status == "NO_BUG_FOUND":
            return "NO_BUG_FOUND — under-approximate search found no modeled bug. NOT a proof of absence."
        return f"{self.status} — {self.detail}"


def _var_types(fn):
    vt = {}
    for p in fn.params:
        if isinstance(p.ty, A.TyName) and p.ty.name in ("Float", "Real", "rat"):
            vt[p.name] = "Real"
        elif isinstance(p.ty, A.TyName) and p.ty.name in ("Int", "Nat"):
            vt[p.name] = "Int"
    return vt


def check_reachable_bugs(code: str) -> BugVerdict:
    """Find reachable division/modulo-by-zero with a concrete witness (UX). See module docstring."""
    if not Z.z3_available():
        return BugVerdict("UNMODELED", detail="Z3 unavailable")
    prog = parse(code)
    if prog.errors:
        return BugVerdict("PARSE_ERROR", detail=str(prog.errors[0]))
    fns = prog.fns()
    if not fns:
        return BugVerdict("NONE", detail="no function found")
    fn = fns[0]
    import z3
    vt = _var_types(fn)
    real = any(t == "Real" for t in vt.values())
    zenv = {n: (z3.Real(n) if t == "Real" else z3.Int(n)) for n, t in vt.items()}

    # base assumption = requires (must be encodable, else we cannot soundly witness → UNMODELED)
    base = []
    if fn.requires is not None:
        try:
            base = [Z._to_z3(fn.requires, zenv, real)]
        except Z._Unsupported:
            return BugVerdict("UNMODELED", detail="`requires` not Z3-encodable — cannot soundly witness "
                              "a bug under it (avoiding a false positive)")

    bugs: List[dict] = []

    def query_zero(denom, line, path):
        try:
            dz = Z._to_z3(denom, zenv, real)
        except Z._Unsupported:
            return                       # can't encode this denominator → skip (no false positive)
        s = z3.Solver(); s.set("timeout", 5000)
        for c in base + path:
            s.add(c)
        s.add(dz == 0)
        if s.check() == z3.sat:
            m = s.model()
            witness = {n: str(m.eval(zenv[n], model_completion=True)) for n in vt}
            bugs.append({"cls": "div_by_zero" , "line": line, "witness": witness})

    def scan(n, path, analyzable):
        if n is None:
            return
        if isinstance(n, A.Bin):
            if n.op in ("/", "%") and analyzable:
                query_zero(n.rhs, getattr(getattr(n, "span", None), "line", 0), path)
            scan(n.lhs, path, analyzable); scan(n.rhs, path, analyzable)
        elif isinstance(n, A.Un):
            scan(n.operand, path, analyzable)
        elif isinstance(n, A.Call):
            for a in n.args:
                scan(a, path, analyzable)
        elif isinstance(n, A.Block):
            for st in n.stmts:
                scan(st, path, analyzable)
        elif isinstance(n, (A.ExprStmt, A.Let)):
            scan(n.value, path, analyzable)
        elif isinstance(n, A.Match):
            # encode the scrutinee; build each arm's path guard from PNum/PBool patterns + wildcard
            try:
                scz = Z._to_z3(n.scrut, zenv, real)
                scrut_ok = True
            except Z._Unsupported:
                scrut_ok = False
            prior = []
            import z3
            for arm in n.arms:
                guard, arm_ok = [], scrut_ok and analyzable
                p = arm.pattern
                if isinstance(p, A.PNum) and arm_ok:
                    guard = [scz == int(p.value)]; prior.append(int(p.value))
                elif isinstance(p, A.PBool) and arm_ok:
                    guard = [scz == (1 if p.value else 0)]
                elif isinstance(p, (A.PWild, A.PVar)) and arm_ok:
                    guard = [scz != k for k in prior]            # the catch-all: none of the prior nums
                else:
                    arm_ok = False                                # list/ADT pattern → don't analyze interior
                scan(arm.body, path + guard, arm_ok)
        elif isinstance(n, A.Fold):
            scan(n.body, path, False)                             # binder semantics → not analyzed (sound)
        # other nodes: nothing to scan for div/mod

    scan(fn.body, [], True)
    if bugs:
        return BugVerdict("BUG_REACHABLE", bugs=bugs)
    return BugVerdict("NO_BUG_FOUND")


def bug_feedback(v: BugVerdict) -> str:
    """Witness → concrete fix instruction for the write→verify→fix loop."""
    if v.status != "BUG_REACHABLE" or not v.bugs:
        return ""
    b = v.bugs[0]
    return (f"REACHABLE BUG ({b['cls']}) at line {b['line']} on input {b['witness']}: the denominator "
            f"can be 0. Fix: guard the division (e.g. `requires` the divisor ≠ 0, or branch on it) so the "
            f"divide-by-zero state is unreachable. Return the corrected HARAN function only.")
