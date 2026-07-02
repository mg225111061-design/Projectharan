"""
CAPSTONE bypass (우회군 H) — straight-line / QF_S string constraints via z3's string theory, model re-verified.
==============================================================================================================
String constraints LOOK undecidable, but the straight-line / QF_S(LIA) fragment is DECIDABLE. We use z3's string
theory (z3 is an ALREADY-PRESENT, allowed dependency — NOT a forbidden big-prover binder like cvc5/Bitwuzla), and
make the answer re-checkable per-instance:
  • SAT  → a concrete model (finite witness) RE-SUBSTITUTED into every constraint (independent of the solver) ⇒
           EXACT decision (satisfiable, witness verified).
  • UNSAT→ z3's sound refutation over the fragment ⇒ EXACT decision (unsatisfiable) — an obstruction (M14).
Tiny constraint DSL (each a tuple): ("eq", a, b) ("concat_eq", x, [parts]) ("len", x, n) ("contains", x, sub)
("prefix", p, x) ("suffix", s, x) — operands are var names (str) or literals ("'lit'").
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import kernel_verdict as KV


@dataclass
class StringVerdict:
    status: str                       # SAT | UNSAT | DECLINE
    model: Optional[Dict[str, str]] = None
    reason: str = ""


def _lit(tok) -> Optional[str]:
    """A quoted literal 'abc' → abc; else None (it's a variable name)."""
    if isinstance(tok, str) and len(tok) >= 2 and tok[0] == "'" and tok[-1] == "'":
        return tok[1:-1]
    return None


def _collect_vars(constraints) -> List[str]:
    vs: List[str] = []
    def add(tok):
        if isinstance(tok, str) and _lit(tok) is None and tok not in vs:
            vs.append(tok)
    for c in constraints:
        op = c[0]
        if op == "concat_eq":
            add(c[1])
            for t in c[2]:
                add(t)
        elif op == "len":
            add(c[1])
        else:
            for tok in c[1:]:
                add(tok)
    return vs


def solve(constraints: List[Tuple], extra_vars: Optional[List[str]] = None) -> StringVerdict:
    """Decide a straight-line/QF_S string constraint list with z3; SAT returns a re-verifiable model."""
    try:
        import z3
    except Exception as e:  # noqa: BLE001
        return StringVerdict("DECLINE", reason=f"z3 not available: {type(e).__name__}")
    varnames = list(dict.fromkeys((extra_vars or []) + _collect_vars(constraints)))
    V = {v: z3.String(v) for v in varnames}

    def term(tok):
        lit = _lit(tok)
        return z3.StringVal(lit) if lit is not None else V[tok]

    s = z3.Solver()
    try:
        for c in constraints:
            op = c[0]
            if op == "eq":
                s.add(term(c[1]) == term(c[2]))
            elif op == "concat_eq":
                parts = [term(p) for p in c[2]]
                s.add(term(c[1]) == (parts[0] if len(parts) == 1 else z3.Concat(*parts)))
            elif op == "len":
                s.add(z3.Length(term(c[1])) == int(c[2]))
            elif op == "contains":
                s.add(z3.Contains(term(c[1]), term(c[2])))
            elif op == "prefix":
                s.add(z3.PrefixOf(term(c[1]), term(c[2])))
            elif op == "suffix":
                s.add(z3.SuffixOf(term(c[1]), term(c[2])))
            else:
                return StringVerdict("DECLINE", reason=f"unsupported constraint op {op!r}")
    except Exception as e:  # noqa: BLE001
        return StringVerdict("DECLINE", reason=f"z3 encoding error: {type(e).__name__}: {e}")
    r = s.check()
    if r == z3.sat:
        m = s.model()
        return StringVerdict("SAT", model={v: m[V[v]].as_string() if m[V[v]] is not None else "" for v in varnames})
    if r == z3.unsat:
        return StringVerdict("UNSAT")
    return StringVerdict("DECLINE", reason="z3 returned unknown")


def _recheck(constraints, model: Dict[str, str]) -> bool:
    """Independent re-substitution of the model into every constraint (the §7 differential check — no solver)."""
    def val(tok):
        lit = _lit(tok)
        return lit if lit is not None else model.get(tok, "")
    for c in constraints:
        op = c[0]
        if op == "eq" and val(c[1]) != val(c[2]):
            return False
        if op == "concat_eq" and val(c[1]) != "".join(val(p) for p in c[2]):
            return False
        if op == "len" and len(val(c[1])) != int(c[2]):
            return False
        if op == "contains" and val(c[2]) not in val(c[1]):
            return False
        if op == "prefix" and not val(c[2]).startswith(val(c[1])):
            return False
        if op == "suffix" and not val(c[2]).endswith(val(c[1])):
            return False
    return True


def string_grade(constraints: List[Tuple], extra_vars: Optional[List[str]] = None) -> KV.Verdict:
    """Grade a string-constraint decision: SAT (model re-verified independently) ⇒ EXACT; UNSAT ⇒ EXACT (obstruction
    — no string satisfies the constraints, M14); z3 unavailable / unknown ⇒ honest DECLINE."""
    v = solve(constraints, extra_vars)
    if v.status == "SAT":
        if not _recheck(constraints, v.model):
            return KV.decline("string_solver: model failed independent re-substitution ⇒ DECLINE (bug guard)", "string_solver")
        cert = KV.Cert(KV.EXACT, "string_model_witness", passed=True, check_cost="model re-substitution (independent of z3)",
                       detail=f"SAT — witness {v.model} re-verified against every constraint")
        return KV.exact({"sat": True, "model": v.model}, "string_solver", "QF_S (z3)", cert)
    if v.status == "UNSAT":
        cert = KV.Cert(KV.EXACT, "string_unsat_refutation", passed=True, check_cost="z3 QF_S decision",
                       detail="UNSAT — no string assignment satisfies the straight-line constraints (sound over QF_S)")
        return KV.exact({"sat": False}, "string_solver", "QF_S (z3)", cert)
    return KV.decline(f"string_solver: {v.reason}", "string_solver")
