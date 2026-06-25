"""
FRONT-END PHASE C — the certified equivalence/refinement substrate (z3-backed). Shared by lifting + Topic A.
============================================================================================================
The single most-reused gate: prove a candidate (lifted form, or optimized fragment) AGREES with the source. Three
strengths, each tagged with its certificate TIER (recorded honestly):
  • prove_equiv_z3  — ∀-equivalence of two z3-expressible computations: UNSAT of (lhs ≠ rhs) over all variable values.
                       TIER "z3_forall" (strong: trust z3 + the encoding). For peephole / closed-form equality.
  • inductive_sum_equiv — prove a closed form f(n) equals a loop's running accumulation by INDUCTION: f(base_n)=base
                       ∧ ∀n: f(n+1)−f(n) = body(n+1). z3 discharges both ⇒ agreement for ALL n. TIER "z3_induction".
                       This is the lifting verifier for recurrence/sum targets — a complete proof, not bounded.
  • bounded_equiv   — exhaustive concrete agreement over a finite domain (a sound proof over that domain only).
                       TIER "bounded" (can miss beyond the domain — labelled).
Refinement (asymmetric, for partiality/UB) is `prove_equiv_z3` with a domain assumption on the source.
A counterexample from z3 REJECTS the candidate (the central invariant: a wrong proposal cannot pass).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

import kernel_verdict as KV


@dataclass
class EquivResult:
    proved: bool
    tier: str                  # z3_forall | z3_induction | bounded | none
    counterexample: Optional[dict]
    detail: str


def prove_equiv_z3(build_lhs: Callable, build_rhs: Callable, var_names: List[str],
                   sort: str = "Int", assumptions: Optional[Callable] = None) -> EquivResult:
    """Prove ∀ vars: lhs == rhs by checking UNSAT of (lhs != rhs ∧ assumptions). build_* take a dict {name: z3 var}."""
    import z3
    mk = z3.Int if sort == "Int" else (z3.Real if sort == "Real" else z3.Int)
    env = {v: mk(v) for v in var_names}
    s = z3.Solver()
    if assumptions is not None:
        s.add(assumptions(env))
    try:
        s.add(build_lhs(env) != build_rhs(env))
    except Exception as e:  # noqa: BLE001
        return EquivResult(False, "none", None, f"encoding error: {type(e).__name__}: {e}")
    r = s.check()
    if r == z3.unsat:
        return EquivResult(True, "z3_forall", None, "∀ vars: lhs == rhs (UNSAT of inequality)")
    if r == z3.sat:
        m = s.model()
        cex = {v: (m[env[v]].as_long() if m[env[v]] is not None else None) for v in var_names}
        return EquivResult(False, "none", cex, f"counterexample {cex} — NOT equivalent")
    return EquivResult(False, "none", None, "z3 unknown")


def inductive_sum_equiv(closed_form: Callable, body: Callable, base_value, base_n: int = 0,
                        var: str = "n", sort: str = "Int") -> EquivResult:
    """Prove f(n) = Σ_{k≤n} body(k) by induction: f(base_n) == base_value ∧ ∀n≥base_n: f(n+1) − f(n) == body(n+1).
    A complete proof for ALL n (not bounded). Use sort="Real" when the closed form has rational coefficients
    (z3 integer division doesn't distribute — a polynomial identity proved over ℝ implies it over ℤ)."""
    import z3
    mk = z3.Real if sort == "Real" else z3.Int
    val = z3.RealVal if sort == "Real" else z3.IntVal
    n = mk(var)
    # base case
    sb = z3.Solver()
    sb.add(closed_form(val(base_n)) != val(base_value))
    if sb.check() != z3.unsat:
        return EquivResult(False, "none", None, f"base case f({base_n}) != {base_value}")
    # inductive step
    si = z3.Solver()
    si.add(n >= base_n)
    si.add(closed_form(n + 1) - closed_form(n) != body(n + 1))
    r = si.check()
    if r == z3.unsat:
        return EquivResult(True, "z3_induction", None, f"base f({base_n})={base_value} ∧ ∀n: f(n+1)−f(n)=body(n+1) ⇒ f=Σbody")
    if r == z3.sat:
        m = si.model()
        return EquivResult(False, "none", {"n": m[n].as_long() if m[n] is not None else None},
                           "inductive step fails — closed form does not match the accumulation")
    return EquivResult(False, "none", None, "z3 unknown on the inductive step")


def bounded_equiv(src_fn: Callable, cand_fn: Callable, domain) -> EquivResult:
    """Exhaustive concrete agreement on a finite `domain` (a sound proof over that domain only)."""
    for x in domain:
        try:
            a, b = src_fn(x), cand_fn(x)
        except Exception as e:  # noqa: BLE001
            return EquivResult(False, "none", {"input": x}, f"evaluation raised {type(e).__name__}")
        if a != b:
            return EquivResult(False, "none", {"input": x, "src": a, "cand": b}, f"disagree at {x}")
    return EquivResult(True, "bounded", None, f"agree on all {len(list(domain)) if hasattr(domain, '__len__') else '?'} domain points")


def equiv_grade(result: EquivResult, what: str = "candidate ≡ source") -> KV.Verdict:
    """Wrap an EquivResult as a graded verdict. z3_forall / z3_induction are EXACT (strong); bounded is EXACT over
    the domain (tier recorded); a refutation is DECLINE with the counterexample."""
    if not result.proved:
        return KV.decline(f"equiv_check: {what} NOT proved — {result.detail}", "equiv_check")
    cert = KV.Cert(KV.EXACT, f"equivalence[{result.tier}]", passed=True,
                   check_cost="z3 UNSAT of inequality" if result.tier.startswith("z3") else "exhaustive domain check",
                   detail=f"{what}: {result.detail} (tier={result.tier})")
    return KV.exact({"proved": True, "tier": result.tier}, "equiv_check", f"certified equivalence ({result.tier})", cert)
