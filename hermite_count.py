"""
§BA CAP-6 — HERMITE TRACE-FORM real-root count of a 0-dimensional ideal (exact, in ℚ).
======================================================================================
For a 0-dimensional ideal I = ⟨f₁,…,f_m⟩ ⊂ ℚ[x₁,…,xₙ], the quotient algebra A = ℚ[x]/I is a finite-dimensional
ℚ-vector space whose dimension equals the number of complex zeros counted with multiplicity. Hermite's theorem
(modern form: Pedersen–Roy–Szpirglas 1993) says that the symmetric **trace bilinear form**
        Q(p,q) = Trace( multiplication-by-(p·q) on A )
has, over ℚ:
        rank(Q)      = number of DISTINCT complex zeros of I,
        signature(Q) = number of DISTINCT real    zeros of I   (signature = n₊ − n₋).
So we count real solutions of a polynomial *system* with NO floating point and NO root finding — purely from the
multiplication structure of A and the **signature** of a rational symmetric matrix.

Repo-first reuse (no new mechanism, no new dependency):
  • `groebner`/sympy drive the Gröbner basis, the standard-monomial basis of A, and normal-form reduction;
  • `sos_cert.inertia(Q)` (the round-4 Sylvester-inertia primitive) supplies the exact signature (n₊,n₀,n₋).

The certificate is re-checkable: the trace-form Gram matrix Q is emitted, and its inertia is an exact congruence
invariant (Sylvester's law) recomputable by anyone. Honest DECLINE when the ideal is NOT 0-dimensional, when the
quotient dimension exceeds the budget, or when an eigenvalue sign of Q is undecidable.
"""
from __future__ import annotations

import itertools
from typing import List, Optional, Sequence, Tuple

import kernel_verdict as KV
import sos_cert

_DIM_CAP = 40                                    # extend-budget guard: |A| beyond this ⇒ honest DECLINE


def _leading_exps(Gpolys, gens, order) -> List[Tuple[int, ...]]:
    return [tuple(p.LM(order=order).exponents) for p in Gpolys]


def _divides(a: Tuple[int, ...], b: Tuple[int, ...]) -> bool:
    """monomial a | b  ⟺  a[i] ≤ b[i] for all i."""
    return all(ai <= bi for ai, bi in zip(a, b))


def _standard_monomials(lm_exps: List[Tuple[int, ...]], nvars: int) -> Optional[List[Tuple[int, ...]]]:
    """Standard monomials of A = ℚ[x]/I (exponent tuples not divisible by any leading monomial). Returns None if
    the ideal is NOT 0-dimensional (some variable has no pure-power leading term ⇒ infinitely many)."""
    if any(all(e == 0 for e in lm) for lm in lm_exps):       # a constant leading term ⇒ I=(1), trivial algebra
        return []
    box = []
    for v in range(nvars):
        powers = [lm[v] for lm in lm_exps if all(lm[w] == 0 for w in range(nvars) if w != v) and lm[v] > 0]
        if not powers:
            return None                                       # variable v unbounded ⇒ not 0-dimensional
        box.append(min(powers))                               # x_v^{d_v} is a leading term ⇒ e_v < d_v
    std = []
    for e in itertools.product(*[range(d) for d in box]):
        if not any(_divides(lm, e) for lm in lm_exps):
            std.append(e)
    return std


def real_root_count(gens: Sequence[str], variables: Sequence[str], order: str = "grevlex") -> KV.Verdict:
    """Count the DISTINCT real (and distinct complex) solutions of the system gens=0 via the Hermite trace form's
    signature. EXACT with the trace-form Gram matrix + Sylvester inertia as the re-checkable certificate."""
    import sympy as sp
    try:
        syms = list(sp.symbols(list(variables)))
        F = [sp.sympify(g) for g in gens]
        G = sp.groebner(F, *syms, order=order)
    except (sp.SympifyError, sp.PolynomialError, TypeError, ValueError, AttributeError) as e:
        return KV.decline(f"hermite_count: parse/Gröbner error {type(e).__name__}: {e} ⇒ DECLINE", "hermite_count")

    Gpolys = [g.as_poly(*syms, domain="QQ") for g in G.exprs]
    nvars = len(syms)
    lm_exps = _leading_exps(Gpolys, syms, order)
    std = _standard_monomials(lm_exps, nvars)
    if std is None:
        return KV.decline("hermite_count: ideal is NOT 0-dimensional (a variable has no pure-power leading term ⇒ "
                          "infinitely many / positive-dimensional solution set) ⇒ DECLINE", "hermite_count")
    if len(std) == 0:
        cert = KV.Cert(KV.EXACT, "hermite_trivial_ideal", passed=True, check_cost="leading-term scan",
                       detail="1 ∈ I (unit ideal) ⇒ empty variety ⇒ 0 real and 0 complex zeros.")
        return KV.exact({"n_real": 0, "n_distinct_complex": 0, "dim_quotient": 0}, "hermite_count",
                        "Hermite trace form (trivial)", cert)
    if len(std) > _DIM_CAP:
        return KV.decline(f"hermite_count: quotient dim {len(std)} exceeds budget {_DIM_CAP} ⇒ DECLINE "
                          f"(infeasible-within-budget, decision-procedure-correct).", "hermite_count")

    Gexprs = [g.as_expr() for g in G.exprs]
    basis = [sp.prod([syms[i] ** e[i] for i in range(nvars)]) for e in std]
    idx = {e: k for k, e in enumerate(std)}

    def nf_dict(expr):
        r = sp.reduced(sp.expand(expr), Gexprs, *syms, order=order)[1]
        rp = sp.Poly(r, *syms, domain="QQ")
        return rp.as_dict()

    def tau(h):
        """Trace of multiplication-by-h on A = Σ_k [coeff of b_k in NF(h·b_k)]."""
        total = sp.Integer(0)
        for k, bk in enumerate(basis):
            d = nf_dict(h * bk)
            total += d.get(std[k], sp.Integer(0))
        return total

    N = len(std)
    Q = sp.zeros(N, N)
    for i in range(N):
        for j in range(i, N):
            val = sp.nsimplify(tau(basis[i] * basis[j]))
            Q[i, j] = val
            Q[j, i] = val

    inr = sos_cert.inertia(Q)
    if inr is None:
        return KV.decline("hermite_count: trace-form signature undecidable (an eigenvalue sign was indeterminate) "
                          "⇒ DECLINE", "hermite_count")
    npos, nzero, nneg = inr
    n_real = npos - nneg
    n_complex = npos + nneg                              # rank = #distinct complex zeros
    if n_real < 0 or n_real > n_complex:
        return KV.decline(f"hermite_count: inconsistent signature {inr} ⇒ DECLINE (bug guard)", "hermite_count")
    cert = KV.Cert(KV.EXACT, "hermite_trace_signature", passed=True,
                   check_cost="Sylvester inertia of the rational trace-form Gram matrix (exact)",
                   detail=f"dim A = {N} (zeros with multiplicity); trace-form inertia (n₊,n₀,n₋)={inr} ⇒ "
                          f"#distinct real = n₊−n₋ = {n_real}, #distinct complex = rank = {n_complex} "
                          f"(Hermite / Pedersen–Roy–Szpirglas).")
    return KV.exact({"n_real": n_real, "n_distinct_complex": n_complex, "dim_quotient": N, "inertia": inr},
                    "hermite_count", "Hermite trace form (signature = #real)", cert)


# ── CAP-5: real radical membership f ∈ ʳ√I for a 0-dim ideal (real Nullstellensatz, via two Hermite counts) ──────
def real_radical_member(gens: Sequence[str], f: str, variables: Sequence[str], order: str = "grevlex") -> KV.Verdict:
    """Decide f ∈ ʳ√I (the REAL radical: ʳ√I = I(V_ℝ(I))) for a 0-dimensional ideal I=⟨gens⟩. By the real
    Nullstellensatz, f ∈ ʳ√I ⟺ f vanishes on every real point of V(I) ⟺ V_ℝ(I) ⊆ {f=0} ⟺ the real-point count is
    UNCHANGED when f=0 is added: #real(I) = #real(I+⟨f⟩) (adding f=0 can only remove real points). Sound for 0-dim
    I; reuses CAP-6's Hermite real-count twice. EXACT decision; honest DECLINE if either count DECLINEs."""
    base = real_root_count(list(gens), variables, order)
    if base.status != KV.EXACT:
        return KV.decline(f"real_radical: base ideal not countable ({base.reason}) ⇒ DECLINE", "real_radical")
    ext = real_root_count(list(gens) + [f], variables, order)
    if ext.status != KV.EXACT:
        return KV.decline(f"real_radical: I+⟨f⟩ not countable ({ext.reason}) ⇒ DECLINE", "real_radical")
    nr0, nr1 = base.result["n_real"], ext.result["n_real"]
    member = (nr0 == nr1)
    cert = KV.Cert(KV.EXACT, "real_radical_via_real_count", passed=True,
                   check_cost="two Hermite real-counts (#real(I), #real(I+⟨f⟩))",
                   detail=f"#real(I)={nr0}, #real(I+⟨f⟩)={nr1} ⇒ "
                          + (f"equal ⇒ V_ℝ(I)⊆{{f=0}} ⇒ f ∈ ʳ√I (real Nullstellensatz)." if member
                             else f"f=0 removes {nr0 - nr1} real point(s) ⇒ f does NOT vanish on all of V_ℝ(I) ⇒ "
                                  f"f ∉ ʳ√I."))
    return KV.exact({"member": member, "n_real_I": nr0, "n_real_I_plus_f": nr1}, "real_radical",
                    "real radical membership (Hermite real-count ×2)", cert)


def solve(problem: dict) -> KV.Verdict:
    """problem = {"op":"real_root_count"|"real_radical_member", "gens":[...], "variables":[...], ...}."""
    op = problem.get("op")
    if op == "real_root_count":
        return real_root_count(problem["gens"], problem["variables"], problem.get("order", "grevlex"))
    if op == "real_radical_member":
        return real_radical_member(problem["gens"], problem["f"], problem["variables"], problem.get("order", "grevlex"))
    return KV.decline(f"hermite_count: unknown op {op!r} ⇒ DECLINE", "hermite_count")


def adversarial_battery() -> dict:
    """x²−1 ⇒ 2 real; x²+1 ⇒ 0 real (2 complex); x² ⇒ 1 distinct real (double); {x²−1,y²−1} ⇒ 4 real;
    {x²+1,y²−1} ⇒ 0 real / 4 complex; non-0-dim ⟨x⟩ in (x,y) ⇒ DECLINE."""
    out = {}
    v = real_root_count(["x**2 - 1"], ["x"]); out["x2m1_2real"] = v.status == KV.EXACT and v.result["n_real"] == 2
    v = real_root_count(["x**2 + 1"], ["x"]); out["x2p1_0real_2cplx"] = (
        v.status == KV.EXACT and v.result["n_real"] == 0 and v.result["n_distinct_complex"] == 2)
    v = real_root_count(["x**2"], ["x"]); out["x2_1distinct_real"] = (
        v.status == KV.EXACT and v.result["n_real"] == 1 and v.result["n_distinct_complex"] == 1)
    v = real_root_count(["x**2 - 1", "y**2 - 1"], ["x", "y"]); out["box_4real"] = (
        v.status == KV.EXACT and v.result["n_real"] == 4)
    v = real_root_count(["x**2 + 1", "y**2 - 1"], ["x", "y"]); out["mixed_0real_4cplx"] = (
        v.status == KV.EXACT and v.result["n_real"] == 0 and v.result["n_distinct_complex"] == 4)
    v = real_root_count(["x"], ["x", "y"]); out["non_zero_dim_decline"] = (
        v.status == KV.DECLINE and "0-dimensional" in v.reason)
    # CAP-5 real radical: x³−x ∈ ʳ√⟨x²−1⟩ (vanishes on {±1}); x−1 ∉ (misses −1); ⟨x²+1⟩ real radical = (1) ⇒ x ∈
    v = real_radical_member(["x**2 - 1"], "x**3 - x", ["x"]); out["rr_member"] = (
        v.status == KV.EXACT and v.result["member"] is True)
    v = real_radical_member(["x**2 - 1"], "x - 1", ["x"]); out["rr_nonmember"] = (
        v.status == KV.EXACT and v.result["member"] is False)
    v = real_radical_member(["x**2 + 1"], "x", ["x"]); out["rr_empty_realvariety_member"] = (
        v.status == KV.EXACT and v.result["member"] is True)
    v = real_radical_member(["x**2 - 1", "y**2 - 1"], "x - y", ["x", "y"]); out["rr_box_nonmember"] = (
        v.status == KV.EXACT and v.result["member"] is False)
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
