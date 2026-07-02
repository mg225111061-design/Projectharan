"""
§BN NEW-6 — Hasse–Minkowski / Legendre: rational solvability of a ternary quadratic form (guess-and-certify m03).
==================================================================================================================
Decide whether  a·x² + b·y² + c·z² = 0  has a NONTRIVIAL rational (⟺ integer) solution.  This is the local-global
principle made effective by Legendre's theorem (1785) — a finite, decidable check, certified three sound ways:

  • SOLVABLE  : an EXPLICIT nontrivial integer (x,y,z) found by a bounded (Holzer-bounded) search, substituted
                back to 0 — the gold-standard re-checked certificate.  (Trivial axis solution if a coeff is 0.)
  • SOLVABLE  : when the form is squarefree + pairwise-coprime + mixed-sign and the three Legendre congruences
                hold (−bc ≡□ mod|a|, −ca ≡□ mod|b|, −ab ≡□ mod|c|, each re-checked by exhaustive t) ⇒ Legendre's
                theorem proves a solution exists — the congruence certificate.
  • UNSOLVABLE: the REAL obstruction (a,b,c all same sign ⇒ no nontrivial real solution) — cert = the signs; OR a
                FAILING Legendre congruence (−bc a non-residue mod|a|, …) re-checked exhaustively — the p-adic
                obstruction.

★ DECIDABLE-BOUNDARY GUARD: outside the small-solution / squarefree-pairwise-coprime fragment (and beyond the cost
  cap on |a|,|b|,|c|), we DECLINE — never a guessed verdict.  certificate-or-DECLINE, false-EXACT 0.  Exact ℤ.
0 new mechanism (guess-and-certify m03 for solvable, relax/obstruction m04 for unsolvable); 0 new disposer. zero-dep.
"""
from __future__ import annotations

from math import gcd, isqrt
from typing import Optional, Tuple

import kernel_verdict as KV

_MAX_COEF = 100000          # |a|,|b|,|c| cap (exhaustive QR mod the coefficient) — beyond ⇒ DECLINE on cost
_MAX_BOX = 400              # explicit-search box cap — beyond ⇒ fall back to Legendre cert or DECLINE


def _squarefree(n: int) -> bool:
    n = abs(n)
    d = 2
    while d * d <= n:
        if n % (d * d) == 0:
            return False
        d += 1
    return True


def _is_residue(a: int, m: int) -> Tuple[bool, Optional[int]]:
    """∃ t∈[0,m): t² ≡ a (mod m)?  Returns (yes, a witness t) — exhaustive, re-checkable (m small)."""
    m = abs(m)
    if m <= 1:
        return True, 0
    a %= m
    for t in range(m):
        if (t * t) % m == a:
            return True, t
    return False, None


def _bounded_solution(a: int, b: int, c: int, box: int) -> Optional[Tuple[int, int, int]]:
    """Search |x|,|y|,|z| ≤ box for a nontrivial integer zero of a x²+b y²+c z² (z normalized ≥0)."""
    for z in range(0, box + 1):
        cz = c * z * z
        for x in range(-box, box + 1):
            axcz = a * x * x + cz
            # solve b y² = −axcz
            rem = -axcz
            if b != 0:
                if rem % b != 0:
                    continue
                q = rem // b
                if q < 0:
                    continue
                y = isqrt(q)
                if y * y == q and not (x == 0 and y == 0 and z == 0):
                    return (x, y, z)
            else:
                if axcz == 0 and not (x == 0 and z == 0):
                    return (x, 1, z)        # b=0 ⇒ y free
    return None


def solve(a: int, b: int, c: int) -> KV.Verdict:
    """EXACT solvable (explicit witness or Legendre congruence cert) | EXACT unsolvable (real / congruence
    obstruction) | DECLINE (outside the decidable/cost fragment)."""
    try:
        a, b, c = int(a), int(b), int(c)
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"hasse_minkowski: {type(e).__name__}: {e}", "hasse_minkowski")
    if max(abs(a), abs(b), abs(c)) > _MAX_COEF:
        return KV.decline(f"hasse_minkowski: |coef| > {_MAX_COEF} ⇒ DECLINE on cost", "hasse_minkowski")
    # zero coefficient ⇒ a coordinate axis is a trivial nontrivial solution
    if a == 0 or b == 0 or c == 0:
        sol = (1, 0, 0) if a == 0 else (0, 1, 0) if b == 0 else (0, 0, 1)
        return _exact_solvable(a, b, c, sol, "a zero coefficient ⇒ axis solution")
    # (1) REAL obstruction — all the same sign ⇒ no nontrivial real solution
    if (a > 0 and b > 0 and c > 0) or (a < 0 and b < 0 and c < 0):
        cert = KV.Cert(KV.EXACT, "real_obstruction", passed=True, check_cost="O(1) sign check",
                       detail=f"sign(a,b,c)=({a},{b},{c}) all same ⇒ a x²+b y²+c z² has no nontrivial real zero")
        return KV.exact({"solvable": False, "obstruction": "real"}, "hasse_minkowski", "Hasse–Minkowski", cert)
    # (2) explicit bounded search (Holzer-bounded) — the strongest certificate
    holzer = isqrt(abs(b * c)) + isqrt(abs(a * c)) + isqrt(abs(a * b)) + 1
    box = min(holzer, _MAX_BOX)
    sol = _bounded_solution(a, b, c, box)
    if sol is not None:
        return _exact_solvable(a, b, c, sol, f"explicit solution within box {box}")
    # (3) Legendre congruence decision — requires squarefree + pairwise coprime form
    sqfree = _squarefree(a) and _squarefree(b) and _squarefree(c)
    coprime = gcd(a, b) == 1 and gcd(b, c) == 1 and gcd(a, c) == 1
    if sqfree and coprime:
        r1, t1 = _is_residue(-b * c, a)
        r2, t2 = _is_residue(-a * c, b)
        r3, t3 = _is_residue(-a * b, c)
        if not (r1 and r2 and r3):
            which = "−bc mod|a|" if not r1 else "−ca mod|b|" if not r2 else "−ab mod|c|"
            cert = KV.Cert(KV.EXACT, "legendre_congruence_obstruction", passed=True,
                           check_cost="exhaustive t mod the coefficient",
                           detail=f"Legendre condition fails: {which} is a non-residue ⇒ no p-adic solution ⇒ "
                                  "the form is anisotropic ⇒ UNSOLVABLE")
            return KV.exact({"solvable": False, "obstruction": "legendre_congruence"}, "hasse_minkowski",
                            "Hasse–Minkowski", cert)
        # all three hold + mixed sign ⇒ Legendre's theorem proves solvable (congruence certificate)
        if holzer > _MAX_BOX:
            cert = KV.Cert(KV.EXACT, "legendre_theorem", passed=True,
                           check_cost="squarefree + pairwise-coprime + mixed-sign + 3 QR congruences (exhaustive t)",
                           detail=f"Legendre 1785: residues t²≡−bc({t1}),−ca({t2}),−ab({t3}) all exist + mixed sign "
                                  "⇒ a nontrivial rational solution exists (Holzer bound exceeds the search cap)")
            return KV.exact({"solvable": True, "by": "legendre_theorem"}, "hasse_minkowski", "Hasse–Minkowski", cert)
        return KV.decline("hasse_minkowski: Legendre says solvable but the bounded search missed the witness within "
                          "the cap ⇒ DECLINE (bug guard — never claim solvable without a re-checked certificate)",
                          "hasse_minkowski")
    return KV.decline("hasse_minkowski: no small solution and the form is not squarefree+pairwise-coprime (outside "
                      "the decidable fragment handled here) ⇒ DECLINE", "hasse_minkowski")


def _exact_solvable(a, b, c, sol, why) -> KV.Verdict:
    x, y, z = sol
    val = a * x * x + b * y * y + c * z * z
    if val != 0 or (x == 0 and y == 0 and z == 0):
        return KV.decline("hasse_minkowski: candidate fails substitution ⇒ DECLINE (bug guard)", "hasse_minkowski")
    cert = KV.Cert(KV.EXACT, "explicit_zero", passed=True, check_cost="substitute (x,y,z) → 0",
                   detail=f"({x},{y},{z}): {a}·{x}²+{b}·{y}²+{c}·{z}²=0 ✓ ({why})")
    return KV.exact({"solvable": True, "solution": [x, y, z]}, "hasse_minkowski", "Hasse–Minkowski (explicit)", cert)


def adversarial_battery() -> dict:
    """★ x²+y²−z²=0 ⇒ solvable (3,4,5); ★ x²+y²+z²=0 ⇒ unsolvable (real obstruction); ★ x²+y²−3z²=0 ⇒ unsolvable
    (Legendre: 3≡3 mod4 non-residue route) ; ★ explicit solution re-checked by substitution; ★ huge coef ⇒ DECLINE."""
    pyth = solve(1, 1, -1)                      # 3²+4²=5² ⇒ solvable
    real = solve(1, 1, 1)                       # positive-definite ⇒ unsolvable (real)
    leg = solve(1, 1, -3)                       # x²+y²=3z² has no nontrivial solution ⇒ unsolvable (congruence)
    big = solve(10 ** 6, 1, -1)                 # |coef| over cap ⇒ DECLINE
    cases = {
        "pythagorean_solvable_EXACT": pyth.status == "EXACT" and pyth.result["solvable"] is True,
        "definite_unsolvable_real": real.status == "EXACT" and real.result["solvable"] is False
                                    and real.result["obstruction"] == "real",
        "x2y2_3z2_unsolvable": leg.status == "EXACT" and leg.result["solvable"] is False,
        "solution_substitutes_to_0": pyth.status == "EXACT" and (lambda s: 1 * s[0]**2 + 1 * s[1]**2 - 1 * s[2]**2 == 0)
                                     (pyth.result["solution"]),
        "huge_coef_DECLINE": big.status == "DECLINE",
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
