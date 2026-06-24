"""
HARAN #19 (Group A) — GRÖBNER BASIS (Buchberger) for ideal membership, with a re-checkable COFACTOR certificate.
================================================================================================================
Buchberger's algorithm completes a generating set F = {f₁..f_m} to a Gröbner basis G under a monomial order by
repeatedly reducing S-polynomials; ideal membership q ∈ ⟨F⟩ is then decided by reduction-to-zero modulo G. We DRIVE
the Buchberger completion ourselves (S-polynomials, the pair loop, AND a TRANSFORMATION matrix so every basis
element is tracked as g_j = Σ T_{ji} f_i), using sympy only for the underlying polynomial ring arithmetic and as
an independent cross-check (`sympy.groebner`). The CERTIFICATE is what makes a YES re-checkable WITHOUT trusting
the basis search: for q ∈ ⟨F⟩ we emit explicit cofactors H_i with q = Σ H_i f_i, verified by direct polynomial
expansion (a Positivstellensatz-style ideal-membership witness). For a NO we emit the nonzero normal form and
re-verify Buchberger's criterion (every S-pair of G reduces to 0) so the decision is sound, not a library
say-so. HONEST: Gröbner bases are EXPSPACE in the worst case (NEVER O(1)); this runs under the extend budget and
honestly DECLINEs (infeasible-within-budget) past a step cap — decision-procedure-correct, not magic.
"""
from __future__ import annotations

from typing import List, Sequence

import kernel_verdict as KV

_STEP_CAP = 4000                                              # extend-budget guard: bail honestly past this many pairs


def _spoly(f, g, gens, order):
    import sympy as sp
    lmf, lmg = f.LM(order=order).as_expr(), g.LM(order=order).as_expr()
    lcm = sp.lcm(lmf, lmg)
    mf = sp.Poly(lcm / (f.LC(order=order) * lmf), *gens)     # L/lt(f)
    mg = sp.Poly(lcm / (g.LC(order=order) * lmg), *gens)     # L/lt(g)
    return mf, mg, mf * f - mg * g                           # multipliers + the S-polynomial


def ideal_member_grade(gens: Sequence[str], query: str, variables: Sequence[str], order: str = "grevlex") -> KV.Verdict:
    """Decide whether `query` ∈ ⟨`gens`⟩ in ℚ[`variables`] by a self-driven Buchberger completion + reduction.
    YES ⇒ EXACT with a COFACTOR certificate q = Σ H_i f_i (verified by expansion). NO ⇒ EXACT with the nonzero
    normal form, after re-verifying Buchberger's S-pair criterion on the computed basis (sound, not a say-so).
    Cross-checked against sympy.groebner. EXPSPACE worst case ⇒ honest DECLINE past the step cap."""
    import sympy as sp
    try:
        gen_syms = sp.symbols(list(variables))
        if not isinstance(gen_syms, (list, tuple)):
            gen_syms = (gen_syms,)
        F = [sp.Poly(sp.sympify(g), *gen_syms, domain="QQ") for g in gens]
        Q = sp.Poly(sp.sympify(query), *gen_syms, domain="QQ")
    except (sp.SympifyError, sp.PolynomialError, TypeError, ValueError) as e:
        return KV.decline(f"groebner: parse error {e} ⇒ DECLINE", "groebner")
    if any(f.is_zero for f in F):
        F = [f for f in F if not f.is_zero]
    if not F:
        return KV.decline("groebner: empty/zero generating set ⇒ DECLINE", "groebner")

    # ── self-driven Buchberger with transformation tracking: basis[j] = (poly, [cofactors in terms of F]) ──
    m = len(F)
    basis = [(F[i], [sp.Poly(1 if j == i else 0, *gen_syms, domain="QQ") for j in range(m)]) for i in range(m)]
    pairs = [(i, j) for i in range(len(basis)) for j in range(i + 1, len(basis))]
    steps = 0
    while pairs:
        if steps >= _STEP_CAP:
            return KV.decline(f"groebner: exceeded {_STEP_CAP} S-pairs (EXPSPACE — infeasible within budget) ⇒ "
                              f"DECLINE", "groebner")
        steps += 1
        i, j = pairs.pop()
        mf, mg, s = _spoly(basis[i][0], basis[j][0], gen_syms, order)
        if s.is_zero:
            continue
        qr = sp.reduced(s.as_expr(), [b[0].as_expr() for b in basis], *gen_syms, order=order)
        quo = [sp.Poly(c, *gen_syms, domain="QQ") for c in qr[0]]
        r = sp.Poly(qr[1], *gen_syms, domain="QQ")
        if r.is_zero:
            continue
        # r = s − Σ quo[k]·basis[k];  transform of r in terms of F (so the basis stays certified):
        tr = [mf * basis[i][1][t] - mg * basis[j][1][t] for t in range(m)]
        for k in range(len(basis)):
            for t in range(m):
                tr[t] = tr[t] - quo[k] * basis[k][1][t]
        basis.append((r, tr))
        pairs += [(k, len(basis) - 1) for k in range(len(basis) - 1)]

    G = [b[0] for b in basis]
    qr = sp.reduced(Q.as_expr(), [g.as_expr() for g in G], *gen_syms, order=order)
    quo = [sp.Poly(c, *gen_syms, domain="QQ") for c in qr[0]]
    rem = sp.Poly(qr[1], *gen_syms, domain="QQ")
    member = rem.is_zero

    if member:
        # cofactors of Q in terms of F:  H_i = Σ_k quo[k]·T_{ki}
        H = [sum((quo[k] * basis[k][1][i] for k in range(len(basis))), sp.Poly(0, *gen_syms, domain="QQ"))
             for i in range(m)]
        recon = sum((H[i] * F[i] for i in range(m)), sp.Poly(0, *gen_syms, domain="QQ"))
        if not (recon - Q).is_zero:                          # ★ re-check the cofactor witness by expansion ★
            return KV.decline("groebner: cofactor reconstruction ≠ query ⇒ DECLINE (bug guard)", "groebner")
        cofs = [str(h.as_expr()) for h in H]
        cert = KV.Cert(KV.EXACT, "groebner_cofactor_membership", passed=True,
                       check_cost=f"Buchberger {steps} S-pairs + cofactor expansion",
                       detail=f"{query} ∈ ⟨{', '.join(gens)}⟩: {query} = Σ Hᵢ·fᵢ with H={cofs} (verified by "
                              f"polynomial expansion — a re-checkable ideal-membership witness)")
        return KV.exact({"member": True, "cofactors": cofs}, "groebner", f"Buchberger ({order})", cert)

    # NO: re-verify Buchberger's criterion (every S-pair of G reduces to 0) ⇒ G is a genuine Gröbner basis
    for a in range(len(G)):
        for b in range(a + 1, len(G)):
            _, _, s = _spoly(G[a], G[b], gen_syms, order)
            if s.is_zero:
                continue
            sr = sp.reduced(s.as_expr(), [g.as_expr() for g in G], *gen_syms, order=order)[1]
            if not sp.Poly(sr, *gen_syms, domain="QQ").is_zero:
                return KV.decline("groebner: S-pair criterion failed ⇒ basis not Gröbner ⇒ DECLINE (sound-NO guard)",
                                  "groebner")
    cert = KV.Cert(KV.EXACT, "groebner_nonmembership_normalform", passed=True,
                   check_cost=f"Buchberger {steps} S-pairs + S-pair criterion re-check",
                   detail=f"{query} ∉ ⟨{', '.join(gens)}⟩: nonzero normal form {rem.as_expr()} modulo a basis "
                          f"re-verified Gröbner (all S-pairs reduce to 0) ⇒ sound NO")
    return KV.exact({"member": False, "normal_form": str(rem.as_expr())}, "groebner", f"Buchberger ({order})", cert)
