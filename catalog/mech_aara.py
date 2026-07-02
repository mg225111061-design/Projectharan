"""
POST-CONSOLIDATION PHASE 1c — AARA: AUTOMATIC AMORTIZED RESOURCE ANALYSIS (the potential method, ∀n-SOUND).
================================================================================================================
Given the OPERATION TYPES of a data structure (each a parametric transition: guard, actual cost, next state) and
its invariant, find a POTENTIAL Φ:state→ℝ≥0 (linear) such that for EVERY op type and EVERY symbolic state in the
invariant region, the AMORTIZED cost  a = cost + Φ(next) − Φ(state) ≤ B. The telescoping sum then proves
Σtᵢ ≤ n·B + Φ(s₀) for ALL n. ★ SOUNDNESS: the proof is over the SYMBOLIC state (z3 ∃Φ ∀state, LRA), NOT a finite
trace — a finite trace would let z3 "front-load" potential and falsely certify any B (the classic AARA trap); the
∀-quantified proof is valid for every n. The certificate is the potential's coefficients + the z3 ∀ proof.

★ THE HONEST ADJUDICATION (four gates):
  gate 1 (distinct in kind): ✓ — "amortized LP-potential" is a NEW certificate KIND (a reopening signal).
  gate 2 (z3-closed): ✓ — ∃Φ ∀state feasibility in LINEAR REAL ARITHMETIC (z3), the model re-verified by a ground
      negation check (a fresh z3 UNSAT — the independent disposer).
  gate 4 (dependency-free): ✓ — z3 (heavy, lazy); no external LP/AARA tool.
  gate 3 (ASYMPTOTIC FOLD O(N)→O(polylog)): ✗ — AARA CERTIFIES a complexity BOUND; it does not fold or accelerate
      code. ⇒ a Group-B VERIFICATION capability, NOT a Group-A fold mechanism (no count++). The new certificate
      kind is recorded as a reopening signal.

A bound with no linear potential valid for all n (genuinely too expensive, e.g. amortized 2 for the doubling array
whose true amortized is 3) ⇒ DECLINE (never a false amortized bound). Precision 1.0.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Dict, List, Optional

import kernel_verdict as KV

GROUP = "B"   # a VERIFICATION capability (certifies a bound for all n), NOT a Group-A fold mechanism


def _ev(expr, env: Dict):
    """Evaluate a restricted arithmetic/relational expression string in `env` (z3 Reals). No builtins."""
    return eval(expr, {"__builtins__": {}}, dict(env))   # noqa: S307 — author-provided in-repo specs only


def _solve(spec: dict):
    """∃ linear Φ-coeffs · ∀ symbolic state in the invariant region: Φ≥0 and every op's amortized ≤ B.
    Returns (coeffs[φ₀,φ₁,…], z3, env_builders) or None (infeasible / z3 absent / unknown)."""
    try:
        import z3
    except Exception:  # noqa: BLE001
        return None
    svars = list(spec["state_vars"])
    B = z3.RealVal(Fraction(spec["bound"]).numerator) / z3.RealVal(Fraction(spec["bound"]).denominator)
    phi = [z3.Real(f"_phi{k}") for k in range(len(svars) + 1)]      # φ₀ + Σ φ_k·var_k

    def state_env(names):
        return {v: z3.Real(v) for v in names}

    def PHI(env, vals):                                            # Φ at a point given by exprs `vals` over env
        return phi[0] + z3.Sum([phi[k + 1] * vals[k] for k in range(len(svars))])

    s = z3.Solver()
    base = state_env(svars)
    inv = [_ev(c, base) for c in spec.get("invariant", [])]
    # (1) Φ ≥ 0 on the invariant region
    s.add(z3.ForAll([base[v] for v in svars], z3.Implies(z3.And(*inv) if inv else z3.BoolVal(True),
                                                         PHI(base, [base[v] for v in svars]) >= 0)))
    # (2) every op type: amortized ≤ B for all states (+aux) in the region satisfying the guard
    for op in spec["ops"]:
        aux = list(op.get("aux", []))
        env = state_env(svars + aux)
        hyp = [_ev(c, env) for c in spec.get("invariant", [])] + [_ev(c, env) for c in op.get("guard", [])] \
            + [_ev(c, env) for c in op.get("aux_constraints", [])]
        cost = _ev(op["cost"], env)
        cur = PHI(env, [env[v] for v in svars])
        nxt = PHI(env, [_ev(op["next"][v], env) for v in svars])
        amort = cost + nxt - cur
        qv = [env[v] for v in svars + aux]
        s.add(z3.ForAll(qv, z3.Implies(z3.And(*hyp) if hyp else z3.BoolVal(True), amort <= B)))
    if s.check() != z3.sat:
        return None
    m = s.model()
    coeffs = []
    for k in range(len(svars) + 1):
        v = m[phi[k]]
        coeffs.append(Fraction(int(v.numerator_as_long()), int(v.denominator_as_long())) if v is not None else Fraction(0))
    return coeffs, svars


def _reverify(spec: dict, coeffs: List[Fraction]) -> bool:
    """The independent DISPOSER: plug the found φ back in and ask a FRESH z3 to refute the ∀-claim (negation UNSAT).
    A second, ground confirmation that the potential is valid for all n — not a finite-trace spot check."""
    try:
        import z3
    except Exception:  # noqa: BLE001
        return False
    svars = list(spec["state_vars"])
    B = z3.RealVal(Fraction(spec["bound"]).numerator) / z3.RealVal(Fraction(spec["bound"]).denominator)

    def cR(fr):
        return z3.RealVal(fr.numerator) / z3.RealVal(fr.denominator)

    def PHI(vals):
        return cR(coeffs[0]) + z3.Sum([cR(coeffs[k + 1]) * vals[k] for k in range(len(svars))])

    for check in ["phi_nonneg"] + [op["name"] for op in spec["ops"]]:
        s = z3.Solver()
        if check == "phi_nonneg":
            env = {v: z3.Real(v) for v in svars}
            hyp = [_ev(c, env) for c in spec.get("invariant", [])]
            s.add(z3.And(*hyp) if hyp else z3.BoolVal(True))
            s.add(z3.Not(PHI([env[v] for v in svars]) >= 0))      # seek a violation
        else:
            op = next(o for o in spec["ops"] if o["name"] == check)
            env = {v: z3.Real(v) for v in svars + list(op.get("aux", []))}
            hyp = [_ev(c, env) for c in spec.get("invariant", [])] + [_ev(c, env) for c in op.get("guard", [])] \
                + [_ev(c, env) for c in op.get("aux_constraints", [])]
            amort = _ev(op["cost"], env) + PHI([_ev(op["next"][v], env) for v in svars]) - PHI([env[v] for v in svars])
            s.add(z3.And(*hyp) if hyp else z3.BoolVal(True))
            s.add(z3.Not(amort <= B))
        if s.check() != z3.unsat:                                 # a violation exists (or unknown) ⇒ NOT certified
            return False
    return True


def aara_grade(spec: dict) -> KV.Verdict:
    """Certify an amortized bound for ALL n by the potential method. spec = {state_vars, invariant, ops:[{name, aux?,
    guard?, aux_constraints?, cost, next}], bound}. EXACT (a Group-B VERIFICATION cert) iff a linear Φ≥0 makes every
    op's amortized ≤ B over the whole symbolic state region (z3 ∃Φ∀state), re-verified by a ground negation check;
    no such potential ⇒ DECLINE (never a false amortized bound)."""
    if not (isinstance(spec, dict) and "state_vars" in spec and "ops" in spec and "bound" in spec):
        return KV.decline("aara: need {state_vars, invariant, ops:[{name,cost,next,…}], bound}", "mech_aara")
    try:
        sol = _solve(spec)
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"aara: z3 formulation error ({type(e).__name__}: {e}) ⇒ DECLINE", "mech_aara")
    if sol is None:
        return KV.decline(f"aara: NO linear potential Φ≥0 certifies amortized ≤ {spec['bound']} for ALL n (genuinely "
                          "too expensive, or z3 unavailable) ⇒ DECLINE (never a false amortized bound)", "mech_aara")
    coeffs, svars = sol
    if not _reverify(spec, coeffs):                               # ★ independent ground disposer ★
        return KV.decline("aara: the found potential failed independent ground re-verification ⇒ DECLINE", "mech_aara")
    phi_str = " + ".join((f"{coeffs[0]}" if k == 0 else f"{coeffs[k]}·{svars[k - 1]}") for k in range(len(svars) + 1)
                         if k == 0 or coeffs[k] != 0)
    cert = KV.Cert(KV.EXACT, "amortized_potential", passed=True,
                   check_cost=f"z3 ∃Φ∀state LRA feasibility + a fresh ground negation re-check ({len(spec['ops'])} "
                              "op types + Φ≥0)",
                   detail=f"potential Φ(s) = {phi_str} ≥ 0; every op's amortized ≤ {spec['bound']} for ALL n "
                          f"(∀-quantified, not a finite trace); Σtᵢ ≤ n·{spec['bound']} + Φ(s₀) — a VERIFICATION "
                          "certificate (Group B, NOT an asymptotic fold; amortized-LP-potential is a NEW cert kind)")
    return KV.exact({"group": GROUP, "kind": "amortized_potential", "potential": phi_str,
                     "potential_coeffs": [str(c) for c in coeffs], "amortized_bound": str(Fraction(spec["bound"])),
                     "n_op_types": len(spec["ops"]), "sound_for_all_n": True},
                    "mech_aara", "AARA amortized bound (potential method, ∀n-sound)", cert)


# ── canonical examples (parametric op types — sound for all n) ───────────────────────────────────────────
def dynamic_array_spec(bound=3) -> dict:
    """Dynamic array with doubling. State (size, cap), invariant cap/2 ≤ size ≤ cap. Normal push cost 1; resize push
    (size==cap) cost size+1, cap→2cap. True amortized = 3 (Φ = 2·size − cap); bound 2 is DECLINEd."""
    return {"state_vars": ["size", "cap"], "bound": bound,
            "invariant": ["2*size >= cap", "size <= cap", "cap >= 1", "size >= 0"],
            "ops": [
                {"name": "normal", "guard": ["size < cap"], "cost": "1", "next": {"size": "size+1", "cap": "cap"}},
                {"name": "resize", "guard": ["size == cap"], "cost": "size+1", "next": {"size": "size+1", "cap": "2*cap"}},
            ]}


def binary_counter_spec(bound=2) -> dict:
    """Binary counter increment. State (ones)=popcount; increment flips k trailing 1s to 0 and one 0 to 1: cost k+1,
    ones→ones−k+1. True amortized = 2 (Φ = ones)."""
    return {"state_vars": ["ones"], "bound": bound, "invariant": ["ones >= 0"],
            "ops": [{"name": "incr", "aux": ["k"], "aux_constraints": ["k >= 0", "k <= ones"],
                     "cost": "k+1", "next": {"ones": "ones-k+1"}}]}


def adjudication() -> dict:
    """Honest gate-by-gate: distinct cert kind ✓, z3-closed ✓, dependency-free ✓, but NOT an asymptotic fold
    (verification, not collapse) ⇒ admitted as a Group-B verification CERTIFICATE KIND, not a fold mechanism."""
    return {"candidate": "AARA (amortized resource analysis)", "distinct_in_kind": True, "z3_closed": True,
            "dependency_free": True, "asymptotic_fold": False, "group": "B",
            "verdict": "ADMIT as a Group-B verification cert kind (amortized_potential) — NOT a Group-A fold mechanism",
            "reason": "AARA certifies an amortized complexity BOUND for all n (a ∀-sound potential-method witness); it "
                      "does not fold or accelerate code, so it is not an O(N)→O(polylog) fold mechanism. The "
                      "amortized-LP-potential is a NEW certificate kind (a reopening signal), in the Group-B ledger"}
