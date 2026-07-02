"""
MATH-Ascent §B4 (arsenal) — LOGIC / VERIFICATION: propositional tautology / SAT / equivalence, decided by Z3.
=============================================================================================================
Boolean reasoning with machine-checked certificates (Z3 is the sanctioned prover):
  • TAUTOLOGY φ — valid iff ¬φ is UNSAT (a Z3 proof). If ¬φ is SAT, that satisfying assignment is a concrete
    COUNTEREXAMPLE (EXACT "not a tautology", witness exhibited). For a small variable count we ALSO cross-check
    exhaustively over the truth table (an independent, bounded-domain proof).
  • SATISFIABILITY φ — SAT ⇒ a model, which we VERIFY independently by substituting it back into the formula
    (it must evaluate to True); UNSAT ⇒ a Z3 proof of unsatisfiability.
  • EQUIVALENCE f ≡ g — the tautology of (f ↔ g); a difference is shown by a witness assignment.
The grade is EXACT either way (the decision is exact); we never report "valid" without the UNSAT proof, nor
"satisfiable" without a verified model. sympy parses the formula (&, |, ~, >>, Eq via Implies/Equivalent); the
decision + the certificate are Z3's (and, for small n, an exhaustive truth-table cross-check).
"""
from __future__ import annotations

import itertools

import sympy as sp
from sympy.logic.boolalg import BooleanFunction, BooleanTrue, BooleanFalse

import kernel_verdict as KV

_EXHAUSTIVE_BOUND = 18           # ≤ 2^18 truth-table rows for the independent cross-check


def _parse(formula):
    return sp.sympify(formula) if isinstance(formula, str) else formula


def _to_z3(expr, env, z3):
    if expr is sp.true or isinstance(expr, BooleanTrue):
        return z3.BoolVal(True)
    if expr is sp.false or isinstance(expr, BooleanFalse):
        return z3.BoolVal(False)
    if expr.is_Symbol:
        return env.setdefault(expr.name, z3.Bool(expr.name))
    if isinstance(expr, sp.Not):
        return z3.Not(_to_z3(expr.args[0], env, z3))
    if isinstance(expr, sp.And):
        return z3.And(*[_to_z3(a, env, z3) for a in expr.args])
    if isinstance(expr, sp.Or):
        return z3.Or(*[_to_z3(a, env, z3) for a in expr.args])
    if isinstance(expr, sp.Implies):
        return z3.Implies(_to_z3(expr.args[0], env, z3), _to_z3(expr.args[1], env, z3))
    if isinstance(expr, sp.Equivalent):
        a = [_to_z3(x, env, z3) for x in expr.args]
        return z3.And(*[a[0] == ai for ai in a[1:]]) if len(a) > 1 else z3.BoolVal(True)
    raise ValueError(f"unsupported boolean node: {sp.srepr(expr)}")


def _exhaustive_taut(expr) -> bool:
    """Independent bounded-domain check: φ is True on EVERY assignment (only for small variable counts)."""
    syms = sorted(expr.free_symbols, key=str)
    if len(syms) > _EXHAUSTIVE_BOUND:
        return True                                          # skip (Z3 already decided); bound honestly stated
    for bits in itertools.product([False, True], repeat=len(syms)):
        if expr.subs(dict(zip(syms, bits))) != sp.true:
            return False
    return True


def tautology_grade(formula) -> KV.Verdict:
    """φ valid? EXACT: ¬φ UNSAT ⇒ tautology (Z3 proof + small-n exhaustive cross-check); else a witness."""
    import z3
    expr = _parse(formula)
    env = {}
    try:
        z3f = _to_z3(expr, env, z3)
    except Exception as e:                                   # noqa: BLE001
        return KV.decline(f"tautology: cannot translate ({e}) ⇒ DECLINE", "logic.tautology")
    s = z3.Solver()
    s.add(z3.Not(z3f))
    r = s.check()
    if r == z3.unsat:
        if not _exhaustive_taut(expr):
            return KV.decline("tautology: Z3 UNSAT but exhaustive cross-check disagrees ⇒ DECLINE (sound)",
                              "logic.tautology")
        cert = KV.Cert(KV.EXACT, "z3_unsat_negation", passed=True, check_cost="Z3 UNSAT(¬φ) + small-n truth table",
                       detail=f"¬φ is UNSAT ⇒ φ is a TAUTOLOGY (valid); {len(expr.free_symbols)} vars")
        return KV.exact(True, "logic.tautology", "exact (Z3)", cert)
    if r == z3.sat:
        m = s.model()
        witness = {str(d): bool(m[d]) for d in m.decls()}
        cert = KV.Cert(KV.EXACT, "z3_counterexample", passed=True, check_cost="one satisfying assignment of ¬φ",
                       detail=f"φ is NOT a tautology — counterexample {witness} falsifies it")
        return KV.exact({"tautology": False, "counterexample": witness}, "logic.tautology", "exact (Z3)", cert)
    return KV.decline("tautology: Z3 returned unknown ⇒ DECLINE", "logic.tautology")


def satisfiable_grade(formula) -> KV.Verdict:
    """φ SAT? EXACT: a model (VERIFIED by substitution) or a Z3 UNSAT proof."""
    import z3
    expr = _parse(formula)
    env = {}
    try:
        z3f = _to_z3(expr, env, z3)
    except Exception as e:                                   # noqa: BLE001
        return KV.decline(f"satisfiable: cannot translate ({e}) ⇒ DECLINE", "logic.sat")
    s = z3.Solver()
    s.add(z3f)
    r = s.check()
    if r == z3.sat:
        m = s.model()
        model = {d.name(): bool(m[d]) for d in m.decls()}
        syms = {sym.name: sym for sym in expr.free_symbols}
        assign = {syms[k]: sp.true if v else sp.false for k, v in model.items() if k in syms}
        for sym in expr.free_symbols:                        # unconstrained vars: default False
            assign.setdefault(sym, sp.false)
        if expr.subs(assign) != sp.true:                     # ★ verify the model independently ★
            return KV.decline("satisfiable: Z3 model failed independent substitution ⇒ DECLINE (sound)", "logic.sat")
        cert = KV.Cert(KV.EXACT, "verified_model", passed=True, check_cost="substitute the model into φ",
                       detail=f"SATISFIABLE — model {model} makes φ True (verified)")
        return KV.exact({"satisfiable": True, "model": model}, "logic.sat", "exact (Z3 + verified model)", cert)
    if r == z3.unsat:
        cert = KV.Cert(KV.EXACT, "z3_unsat", passed=True, check_cost="Z3 UNSAT",
                       detail="UNSATISFIABLE — no assignment satisfies φ (Z3 proof)")
        return KV.exact({"satisfiable": False}, "logic.sat", "exact (Z3)", cert)
    return KV.decline("satisfiable: Z3 returned unknown ⇒ DECLINE", "logic.sat")


def equivalent_grade(f, g) -> KV.Verdict:
    """f ≡ g? The tautology of (f ↔ g); a difference is shown by a witness assignment."""
    expr = sp.Equivalent(_parse(f), _parse(g))
    v = tautology_grade(expr)
    if v.status == KV.EXACT and v.result is True:
        cert = KV.Cert(KV.EXACT, "equivalence_tautology", passed=True, check_cost="Z3 UNSAT(¬(f↔g))",
                       detail="f ↔ g is a tautology ⇒ f and g are logically EQUIVALENT")
        return KV.exact({"equivalent": True}, "logic.equiv", "exact (Z3)", cert)
    if v.status == KV.EXACT:                                 # not a tautology ⇒ has a distinguishing witness
        return KV.exact({"equivalent": False, "counterexample": v.result["counterexample"]}, "logic.equiv",
                        "exact (Z3)", KV.Cert(KV.EXACT, "z3_counterexample", True, "distinguishing assignment",
                                              detail=f"f and g DIFFER at {v.result['counterexample']}"))
    return v


def solve(problem: dict) -> KV.Verdict:
    op = problem.get("op")
    if op == "tautology":
        return tautology_grade(problem["formula"])
    if op == "satisfiable":
        return satisfiable_grade(problem["formula"])
    if op == "equivalent":
        return equivalent_grade(problem["f"], problem["g"])
    return KV.decline(f"logic: unknown op {op!r} ⇒ DECLINE", "logic")
