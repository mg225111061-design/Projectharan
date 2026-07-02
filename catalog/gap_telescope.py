"""
GAP 13 (certification) — full Zeilberger creative telescoping with an EXACT WZ rational certificate.
======================================================================================================
Gosper (native_telescope) certifies only HYPERGEOMETRIC summation; this certifies HOLONOMIC sums S(n)=Σ_k F(n,k)
by finding the P-recursive recurrence Σ_j a_j(n)·S(n+j)=0 and PROVING it with the WZ certificate:

  PROPOSER : guess the recurrence — solve, EXACTLY over ℚ, for polynomial coefficients a_j(n) from computed values
             of S(n) (the holonomic guesser; a nullspace of [n^d·S(n+j)]).
  ★DISPOSER (mandatory, EXACT): build t(n,k)=Σ_j a_j(n)·F(n+j,k) = F(n,k)·Σ_j a_j(n)·(F(n+j,k)/F(n,k)) (the ratio is
             rational in k ⇒ t is hypergeometric in k); run Gosper to get the antidifference G with t=G(k+1)−G(k),
             then VERIFY the exact polynomial identity t − (G(k+1)−G(k)) ≡ 0 (a skeptic re-checks; guessing is NOT
             proof). The certificate is R(n,k)=G/F. Finite support ⇒ boundary terms vanish ⇒ Σ_j a_j(n)S(n+j)=0.

A sum with no such recurrence (the guesser finds none, or Gosper fails to certify) ⇒ DECLINE. zero-dep (sympy).
"""
from __future__ import annotations

from typing import Optional

import kernel_verdict as KV


def zeilberger_grade(summand_str: str, max_order: int = 2, max_deg: int = 2, n_hi: int = 16) -> KV.Verdict:
    """Gap 13 — certify a holonomic sum S(n)=Σ_{k=0}^{n} F(n,k) by an exact WZ creative-telescoping certificate.
    `summand_str` is a sympy expression in n,k (e.g. 'binomial(n,k)**2'). EXACT iff the WZ identity verifies in
    exact polynomial arithmetic; otherwise DECLINE (no guessed recurrence is trusted without its certificate)."""
    import sympy as sp
    from sympy.concrete.gosper import gosper_term
    n, k = sp.symbols("n k", integer=True)
    try:
        F = sp.sympify(summand_str, locals={"n": n, "k": k, "binomial": sp.binomial, "factorial": sp.factorial})
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"zeilberger: cannot parse summand ({type(e).__name__})", "gap_telescope")
    # exact S(n) values by summation over k=0..n
    try:
        Sv = {}
        for nv in range(0, n_hi + 1):
            Sv[nv] = sp.Integer(sum(sp.Integer(F.subs({n: nv, k: kk})) for kk in range(0, nv + 1)))
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"zeilberger: summand not integer-valued / unevaluable ({type(e).__name__})", "gap_telescope")

    for J in range(1, max_order + 1):
        for D in range(0, max_deg + 1):
            ncoef = (J + 1) * (D + 1)
            n_eqs = n_hi - J                                    # usable n = 0 .. n_hi-J
            if n_eqs < ncoef + 2:                              # need held-out equations to validate the nullspace
                continue
            rows = []
            for nv in range(0, n_hi - J + 1):
                row = []
                for j in range(J + 1):
                    for d in range(D + 1):
                        row.append(sp.Rational(nv) ** d * Sv[nv + j])
                rows.append(row)
            A = sp.Matrix(rows)
            ns = A.nullspace()
            if not ns:
                continue
            cvec = ns[0]
            if all(c == 0 for c in cvec):
                continue
            # reconstruct a_j(n) = Σ_d c[j][d] n^d
            a = []
            idx = 0
            for j in range(J + 1):
                poly = sp.Integer(0)
                for d in range(D + 1):
                    poly += cvec[idx] * n ** d
                    idx += 1
                a.append(sp.expand(poly))
            if a[J] == 0:                                       # leading coefficient must be nonzero (true order J)
                continue
            # ★ build t(n,k) and demand the Gosper/WZ certificate (the mandatory proof) ★
            try:
                ratios = [sp.simplify(F.subs(n, n + j) / F) for j in range(J + 1)]   # rational in k
                bracket = sp.simplify(sum(a[j] * ratios[j] for j in range(J + 1)))
                t = sp.simplify(F * bracket)
                R = gosper_term(t, k)
                if R is None:
                    continue
                G = sp.simplify(R * t)
                if sp.simplify(t - (G.subs(k, k + 1) - G)) != 0:
                    continue                                    # WZ identity failed ⇒ not certified ⇒ try next
                cert_R = sp.simplify(G / F)
            except Exception:  # noqa: BLE001
                continue
            rec = " + ".join(f"({sp.srepr(a[j])[:0]}{a[j]})·S(n+{j})" for j in range(J + 1)) + " = 0"
            cert = KV.Cert(KV.EXACT, "zeilberger_telescoping", passed=True,
                           check_cost="exact polynomial identity t(n,k) ≡ G(k+1)−G(k) (WZ certificate re-checked)",
                           detail=f"holonomic recurrence order {J}: {rec}; WZ certificate R(n,k)={cert_R}")
            return KV.exact({"order": J, "coeffs": [str(a[j]) for j in range(J + 1)], "recurrence": rec,
                             "wz_certificate": str(cert_R)}, "gap_telescope.zeilberger",
                            f"Zeilberger creative telescoping (order {J})", cert)
    return KV.decline("zeilberger: no holonomic recurrence with a verified WZ certificate ⇒ DECLINE "
                      "(non-holonomic / outside the bounded order·degree island)", "gap_telescope")
