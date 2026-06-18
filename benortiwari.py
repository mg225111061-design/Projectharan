"""
v32 STAGE B1 — Ben-Or–Tiwari sparse multivariate interpolation (black-box polynomial recovery) [Clock C].
=========================================================================================================
Target: loops that compute a sparse multivariate polynomial but whose symbolic form is invisible to the
static engine (deep nesting / control flow). We recover the polynomial from EVALUATIONS of the loop
(a black box), then collapse it to the closed polynomial — a Clock C win (and Clock B: the black box is
proved equal to a closed polynomial relation).

THE ALGORITHM (Ben-Or & Tiwari 1988), exact over ℤ (Python big ints — no flint/Sage needed):
  • Assign a distinct small prime pₖ to each variable. Evaluate the black box at the points
    (p₁^j, …, p_v^j) for j = 0,1,2,…  Each monomial x^e = ∏ xₖ^{eₖ} becomes (∏ pₖ^{eₖ})^j = mᵢ^j, so the
    evaluation sequence a_j = Σᵢ cᵢ mᵢ^j is a sum of t geometric sequences ⇒ a linear-recurrent sequence.
  • BERLEKAMP–MASSEY (over ℚ) on a_0…a_{2t-1} → the minimal recurrence; its characteristic polynomial
    has roots exactly the monomial evaluations mᵢ.   (EARLY TERMINATION: grow t until the order is stable.)
  • Factor each integer root mᵢ over {p₁,…,p_v} → the exponent vector eᵢ. A non-smooth / non-integer root
    ⇒ the black box is NOT a polynomial of this form ⇒ HONEST_DEFER.
  • Transposed Vandermonde solve Σᵢ cᵢ mᵢ^j = a_j → the coefficients cᵢ (exact rationals).

★ SOUND GATE (rule 1) ★: the recovered polynomial is verified against the black box by SCHWARTZ–ZIPPEL at
FRESH random points (not used in recovery). All agree ⇒ accept; the recovery is EXACT (bit-exact) but the
equality CHECK is probabilistic: error ≤ (deg/|S|) per round (stated). Any mismatch ⇒ HONEST_DEFER — a
non-polynomial black box (e.g. x//y, x mod 7) is caught here and never folded into false structure.

Certificate: exact (bit-exact recovered coefficients) with a probabilistic equality check (ε stated).
Clock: C (black-box loop → closed polynomial). Also Clock B (proves the loop ≡ a polynomial relation).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Callable, Dict, List, Optional, Tuple

# small primes assigned to variables (distinct ⇒ monomial evaluations are distinct by unique factorization)
_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29)


@dataclass
class BenOrTiwariResult:
    status: str                       # FOLDED | DEFER
    n_terms: int = 0
    monomials: List[Tuple[Tuple[int, ...], Fraction]] = field(default_factory=list)  # (exponent vector, coeff)
    poly_str: str = ""
    cert_type: str = "exact"          # exact recovery; equality check is probabilistic (ε below)
    error_prob: float = 0.0           # Schwartz-Zippel one-sided error of the equality CHECK
    verified: bool = False
    clock: str = "C"
    detail: str = ""

    def __str__(self):
        if self.status == "FOLDED":
            return f"FOLDED [Clock C] {self.poly_str}  (exact recovery, SZ-check ε≤{self.error_prob:.2e})"
        return f"DEFER — {self.detail}"


# ─────────────────────────────────────────────────────── Berlekamp–Massey over ℚ
def berlekamp_massey(seq: List[Fraction]) -> List[Fraction]:
    """Minimal connection polynomial C(z)=1+C₁z+…+C_Lz^L of a rational sequence (a_n = -Σ_{i≥1}Cᵢ a_{n-i}).
    Returned as [C₀=1, C₁, …, C_L]. The characteristic polynomial (roots = the mᵢ) is C read high→low."""
    C = [Fraction(1)]
    B = [Fraction(1)]
    L, m, b = 0, 1, Fraction(1)
    for n in range(len(seq)):
        d = seq[n] + sum(C[i] * seq[n - i] for i in range(1, L + 1))
        if d == 0:
            m += 1
        elif 2 * L <= n:
            T = C[:]
            coef = d / b
            C = C + [Fraction(0)] * (len(B) + m - len(C))
            for i in range(len(B)):
                C[i + m] -= coef * B[i]
            L, B, b, m = n + 1 - L, T, d, 1
        else:
            coef = d / b
            C = C + [Fraction(0)] * (len(B) + m - len(C))
            for i in range(len(B)):
                C[i + m] -= coef * B[i]
            m += 1
    return C[:L + 1]


def _integer_roots(char_coeffs_high_to_low: List[Fraction]) -> Optional[List[int]]:
    """Positive-integer roots of a rational polynomial (the monomial evaluations mᵢ). Uses sympy for
    robust root isolation; each candidate is EXACT-verified by substitution. None ⇒ a root is not a
    positive integer (⇒ black box is not a polynomial of the assumed form)."""
    import sympy as sp
    z = sp.Symbol("z")
    deg = len(char_coeffs_high_to_low) - 1
    poly = sum(sp.nsimplify(c) * z**(deg - i) for i, c in enumerate(char_coeffs_high_to_low))
    P = sp.Poly(poly, z)
    roots: List[int] = []
    try:
        approx = P.nroots(n=30)
    except Exception:  # noqa: BLE001
        return None
    for r in approx:
        if abs(sp.im(r)) > 1e-9:
            return None                                  # complex root ⇒ not a real monomial eval
        ri = int(sp.nsimplify(sp.re(r), rational=False).round())
        if ri <= 0 or P.eval(ri) != 0:                   # must be a positive integer AND an exact root
            return None
        roots.append(ri)
    return roots


def _factor_smooth(m: int, primes: Tuple[int, ...], nvars: int) -> Optional[Tuple[int, ...]]:
    """Factor m over the variable primes → exponent vector (e₁,…,e_v). None if m is not p-smooth."""
    e = [0] * nvars
    for k in range(nvars):
        p = primes[k]
        while m % p == 0:
            m //= p
            e[k] += 1
    return tuple(e) if m == 1 else None


def _vandermonde_solve(ms: List[int], a: List[Fraction]) -> Optional[List[Fraction]]:
    """Solve Σᵢ cᵢ mᵢ^j = a_j (j=0..t-1) for the coefficients cᵢ (exact rationals)."""
    import sympy as sp
    t = len(ms)
    M = sp.Matrix(t, t, lambda j, i: sp.Integer(ms[i])**j)
    rhs = sp.Matrix(t, 1, [sp.Rational(x.numerator, x.denominator) for x in a[:t]])
    try:
        sol = M.solve(rhs)
    except Exception:  # noqa: BLE001 — singular ⇒ recovery failed
        return None
    return [Fraction(int(sp.numer(v)), int(sp.denom(v))) for v in sol]


# ─────────────────────────────────────────────────────── the recovery + SOUND gate
def _eval_at_powers(blackbox: Callable, primes: Tuple[int, ...], nvars: int, j: int) -> Fraction:
    pt = [primes[k]**j for k in range(nvars)]
    return Fraction(blackbox(*pt))


def interpolate(blackbox: Callable, nvars: int, *, max_terms: int = 12) -> Optional[dict]:
    """Ben-Or–Tiwari recovery with EARLY TERMINATION. Returns {'mons': [(exp,coeff)], 'primes':…} or None
    if the black box is not a recoverable sparse polynomial (non-integer/non-smooth roots, singular solve)."""
    primes = _PRIMES[:nvars]
    seq: List[Fraction] = []
    prev_order = -1
    stable = 0
    for t in range(1, max_terms + 1):
        # ensure we have 2t samples
        while len(seq) < 2 * t:
            seq.append(_eval_at_powers(blackbox, primes, nvars, len(seq)))
        C = berlekamp_massey(seq[:2 * t])
        order = len(C) - 1
        if order == prev_order:                          # recurrence order stabilized ⇒ sparsity found
            stable += 1
            if stable >= 1:
                break
        else:
            stable = 0
        prev_order = order
    char = C                                             # coeffs high→low; roots = monomial evals
    if len(char) <= 1:                                   # constant sequence ⇒ degree-0 polynomial
        c0 = seq[0]
        return {"mons": [((0,) * nvars, c0)], "primes": primes}
    roots = _integer_roots(char)
    if roots is None or len(set(roots)) != len(roots):
        return None
    exps = []
    for m in roots:
        e = _factor_smooth(m, primes, nvars)
        if e is None:
            return None
        exps.append(e)
    coeffs = _vandermonde_solve(roots, seq)
    if coeffs is None:
        return None
    mons = [(exps[i], coeffs[i]) for i in range(len(roots)) if coeffs[i] != 0]
    return {"mons": mons, "primes": primes}


def _poly_str(mons: List[Tuple[Tuple[int, ...], Fraction]], nvars: int) -> str:
    names = [chr(ord("a") + i) if nvars > 3 else "xyz"[i] for i in range(nvars)] if nvars <= 3 \
        else [f"v{i}" for i in range(nvars)]
    names = (["x", "y", "z"] + [f"v{i}" for i in range(3, nvars)])[:nvars]
    terms = []
    for exp, c in sorted(mons, key=lambda t: (-sum(t[0]), t[0])):
        factors = [f"{names[k]}**{e}" if e > 1 else names[k] for k, e in enumerate(exp) if e > 0]
        body = "*".join(factors)
        cc = c.numerator if c.denominator == 1 else f"{c.numerator}/{c.denominator}"
        terms.append(f"{cc}*{body}" if body and c != 1 else (body if c == 1 and body else str(cc)))
    return " + ".join(terms) if terms else "0"


def verify_schwartz_zippel(blackbox: Callable, mons, nvars: int, *, rounds: int = 8,
                           field: int = (1 << 61) - 1, seed: int = 20260618) -> Tuple[bool, float, int]:
    """★ SOUND GATE ★ — compare the recovered polynomial to the black box at FRESH random points over a
    large prime field. Returns (ok, error_prob, degree). One-sided: a true polynomial identity always
    passes; a non-polynomial / wrong recovery fails (error ≤ deg/|S| per round)."""
    import random
    rng = random.Random(seed)
    deg = max((sum(e) for e, _ in mons), default=0)
    S = field
    for _ in range(rounds):
        pt = [rng.randrange(2, S) for _ in range(nvars)]
        # recovered poly value mod S
        val = 0
        for e, c in mons:
            term = c.numerator * pow(c.denominator, S - 2, S) % S
            for k in range(nvars):
                term = term * pow(pt[k], e[k], S) % S
            val = (val + term) % S
        try:
            bb = int(blackbox(*pt)) % S
        except Exception:  # noqa: BLE001 — black box can't take these inputs ⇒ treat as mismatch
            return False, 0.0, deg
        if val != bb:
            return False, 0.0, deg                       # a fresh point separated them — definitely not equal
    return True, (deg / S) ** rounds if S else 1.0, deg


def recover(blackbox: Callable, nvars: int, *, max_terms: int = 12) -> BenOrTiwariResult:
    """Full B1: interpolate the black box, then SOUND-VERIFY by Schwartz-Zippel before declaring FOLDED."""
    rec = interpolate(blackbox, nvars, max_terms=max_terms)
    if rec is None:
        return BenOrTiwariResult("DEFER", detail="not a recoverable sparse polynomial (non-integer/"
                                 "non-smooth roots or singular solve) — HONEST_DEFER")
    mons = rec["mons"]
    ok, eps, deg = verify_schwartz_zippel(blackbox, mons, nvars)
    if not ok:
        return BenOrTiwariResult("DEFER", n_terms=len(mons),
                                 detail="recovered candidate FAILED Schwartz-Zippel at a fresh random point "
                                        "(black box is not this polynomial) — HONEST_DEFER (no false structure)")
    return BenOrTiwariResult("FOLDED", n_terms=len(mons), monomials=mons,
                             poly_str=_poly_str(mons, nvars), cert_type="exact", error_prob=eps,
                             verified=True, clock="C",
                             detail=f"recovered {len(mons)} terms (deg {deg}); SZ-verified at {8} fresh points")


# ─────────────────────────────────────────────────────── B1.4 — corpus measurement
def measure_poly_corpus(split: Optional[str] = None) -> dict:
    """Run B1 over the defer corpus's `multivariate-poly` category. Reports hit rate AND Schwartz-Zippel
    verification rate, with ZERO false folds (negative controls must DEFER). Coverage MEASURED, not estimated."""
    import defer_corpus as DC
    cs = [c for c in DC.load() if c.category == "multivariate-poly" and (split is None or c.split == split)]
    folded = correct = verified = 0
    rows = []
    for c in cs:
        nvars = len(c.arg_spec)
        r = recover(c.naive, nvars)
        is_fold = (r.status == "FOLDED")
        ok = (is_fold == (c.expect == "foldable"))
        folded += int(is_fold)
        verified += int(r.verified)
        correct += int(ok)
        rows.append((c.cid, c.expect, r.status, ok, r.poly_str if is_fold else ""))
    n = len(cs)
    return {"n": n, "folded": folded, "correct": correct, "verified": verified,
            "hit_rate": round(folded / n, 3) if n else 0.0,
            "correctness": round(correct / n, 3) if n else 0.0,
            "rows": rows, "clock": "C"}
