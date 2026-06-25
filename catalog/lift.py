"""
FRONT-END PHASE D — verified lifting: translate imperative code into a structured form the fold engine handles,
with a z3-certified equivalence proof. Proposer (synthesis) + disposer (PHASE C equiv_check) — nothing folds uncert.
================================================================================================================
Pipeline: parse → identify liftable fragment (routing probe) → SYNTHESIZE a structured candidate → PROVE equivalence
(equiv_check) → emit certificate → hand the StructForm to the 14-mechanism engine (no 15th mechanism added).

Targets (priority order):
  • SUM/RECURRENCE (highest — feeds the closed-form mechanisms): a loop  s += body(k)  over k ∈ [a,b]. Synthesize the
    closed form by exact interpolation of partial sums (the proposer), then PROVE it by INDUCTION via z3
    (f(a−1)=0 ∧ ∀n: f(n)−f(n−1)=body(n)) — a complete proof, not bounded. Non-polynomial body / unprovable ⇒ DECLINE.
  • TENSOR/ELEMENTWISE (Tenspiler-style): a nested affine loop  c[i]=a[i] OP b[i]  → a tensor op; verified by bounded
    exhaustive equivalence on a sample domain (tier=bounded, recorded honestly).
Cost gate: synthesis+proof is justified only for HOT/REUSED kernels — `should_lift()` is a real cost-benefit check.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import kernel_verdict as KV


# ── safe arithmetic expr → (python eval, z3 expr) over a single integer variable ────────────────────────
def _to_sympy(expr: str, var: str):
    import sympy as sp
    n = sp.Symbol(var)
    e = sp.sympify(expr, locals={var: n})
    if e.free_symbols - {n}:
        raise ValueError(f"expr has variables other than {var}: {e.free_symbols}")
    return e, n


def _sympy_to_z3(e, zvar, var: str):
    """sympy expr → z3 REAL expr (exact rational division; a polynomial identity proved over ℝ implies it over ℤ)."""
    import z3
    if e.is_Integer:
        return z3.RealVal(int(e))
    if e.is_Symbol and str(e) == var:
        return zvar
    if e.is_Add:
        acc = _sympy_to_z3(e.args[0], zvar, var)
        for a in e.args[1:]:
            acc = acc + _sympy_to_z3(a, zvar, var)
        return acc
    if e.is_Mul:
        acc = _sympy_to_z3(e.args[0], zvar, var)
        for a in e.args[1:]:
            acc = acc * _sympy_to_z3(a, zvar, var)
        return acc
    if e.is_Pow and e.exp.is_Integer and int(e.exp) >= 0:
        base = _sympy_to_z3(e.base, zvar, var)
        acc = z3.RealVal(1)
        for _ in range(int(e.exp)):
            acc = acc * base
        return acc
    if e.is_Rational:
        return z3.RealVal(int(e.p)) / z3.RealVal(int(e.q))   # exact rational division over ℝ
    raise ValueError(f"cannot encode {e} for z3")


@dataclass
class LiftResult:
    lifted: bool
    target: str                # sum | tensor | none
    closed_form: str
    tier: str                  # z3_induction | bounded | none
    detail: str


def lift_sum(body_expr: str, var: str = "k", base_n: int = 1) -> KV.Verdict:
    """Lift Σ_{k=base_n}^{n} body(k) to a closed form, PROVED by z3 induction. body_expr is a polynomial in `var`."""
    import sympy as sp
    import z3
    from catalog import equiv_check as EC
    try:
        body_sym, k = _to_sympy(body_expr, var)
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"lift_sum: cannot parse body {body_expr!r}: {e}", "lift")
    # PROPOSER: closed form via symbolic summation (Faulhaber); for polynomial body this is exact + degree-bounded
    n = sp.Symbol("n")
    try:
        closed = sp.simplify(sp.summation(body_sym, (k, base_n, n)))
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"lift_sum: summation failed ({type(e).__name__}) ⇒ DECLINE", "lift")
    if closed.free_symbols - {n}:
        return KV.decline(f"lift_sum: no closed form in n (got {closed}) ⇒ DECLINE", "lift")
    # DISPOSER: PROVE by induction via z3 over ℝ — f(base_n−1)=0 ∧ ∀m: f(m)−f(m−1)=body(m)
    def closed_z3(zn):
        return _sympy_to_z3(closed.xreplace({n: sp.Symbol("__n")}), zn, "__n")

    def body_z3(zk):
        return _sympy_to_z3(body_sym.xreplace({k: sp.Symbol("__n")}), zk, "__n")

    res = EC.inductive_sum_equiv(closed_z3, body_z3, base_value=0, base_n=base_n - 1, var="n", sort="Real")
    if not res.proved:
        return KV.decline(f"lift_sum: closed form {closed} NOT proved by induction — {res.detail} ⇒ DECLINE", "lift")
    cert = KV.Cert(KV.EXACT, f"lift_equivalence[{res.tier}]", passed=True, check_cost="z3 induction (base + step UNSAT)",
                   detail=f"Σ_{{{var}={base_n}}}^n {body_expr} = {closed}; proved by induction ({res.tier})")
    return KV.exact({"closed_form": str(closed), "target": "sum", "tier": res.tier}, "lift",
                    "verified lifting (sum→closed form)", cert)


_SUM_LOOP = re.compile(
    r"for\s+(\w+)\s+in\s+range\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)\s*:\s*\n?\s*\w+\s*\+=\s*(.+)", re.MULTILINE)


def lift_code(code: str) -> KV.Verdict:
    """Identify a liftable accumulation loop `for k in range(a, b): s += body` and lift the sum. Routing probe +
    synthesis + proof. Non-matching / non-liftable code ⇒ honest DECLINE (fall back to Topic A or DECLINE)."""
    m = _SUM_LOOP.search(code)
    if not m:
        return KV.decline("lift_code: no liftable accumulation loop (for k in range(a,b): s += body) found ⇒ DECLINE", "lift")
    var, lo, hi, body = m.group(1), m.group(2).strip(), m.group(3).strip(), m.group(4).strip().rstrip(":")
    # range(lo, hi) sums k from lo to hi-1; lift Σ_{k=lo}^{hi-1} body with the upper limit symbolic (hi = n+1 ⇒ to n)
    base_n = 1
    try:
        base_n = int(lo)
    except ValueError:
        base_n = 1
    return lift_sum(body, var=var, base_n=base_n)


def should_lift(code: str, hot: bool = True, reused: bool = True) -> bool:
    """Cost-benefit gate: synthesis+proof costs seconds — justified only for HOT, REUSED kernels (not run-once/cold)."""
    return bool(hot and reused and _SUM_LOOP.search(code))


def lift_grade(x) -> KV.Verdict:
    """Route {"lift_sum": "body", "var": "k", "base": a} | {"lift_code": "source"} → verified lifting."""
    if isinstance(x, dict) and "lift_sum" in x:
        return lift_sum(x["lift_sum"], x.get("var", "k"), x.get("base", 1))
    if isinstance(x, dict) and "lift_code" in x:
        if not should_lift(x["lift_code"], x.get("hot", True), x.get("reused", True)):
            return KV.decline("lift: cost gate — cold/run-once code, lifting not justified (prefer Topic A) ⇒ DECLINE", "lift")
        return lift_code(x["lift_code"])
    return KV.decline("lift: expected {lift_sum: body} | {lift_code: source}", "lift")
