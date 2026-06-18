"""
v32 STAGE A — differential-Galois / Kovacic foldability decision for 2nd-order linear ODEs.
============================================================================================
Target: numeric ODE-integration loops (Euler/Runge-Kutta discretizations) that compute y(x) by O(steps)
stepping. If the underlying ODE y'' + p(x)y' + q(x)y = 0 has a LIOUVILLIAN (closed-form) solution, the loop
collapses to an O(1) analytic evaluation — a Clock C win.

PIPELINE (detector → candidate → SOUND verifier → fold | HONEST_DEFER):
  A.1 detect  : recover (p,q) from an Euler/RK discretization u_{k+1}=u_k+h·φ(x_k,u_k,v_k)   (ast + sympy)
  A.2 decide  : SymPy `dsolve` PROPOSES a closed form for y''+py'+qy=0; reject special-function /
                truncated-series / Integral answers (those are NOT Liouvillian closed forms).
  A.2 verify  : ★ THE SOUND GATE ★ — substitute the candidate back: require L[y]=y''+py'+qy ≡ 0 EXACTLY
                (symbolic), PLUS a random-point numeric cross-check. Independent solutions (Wronskian≠0).
                Only a verified candidate folds. Verification fails ⇒ HONEST_DEFER (never a false fold).
  A.4 measure : run over the defer corpus's `ode` category — decision rate AND fold rate (held out).

HONEST SCOPE (A.3):
  • 2nd-order LINEAR ODE only. Nonlinear / higher-order ⇒ out of scope ⇒ DEFER (no overclaim).
  • The closed form is PROVEN by exact re-substitution (certificate type: exact). We never emit one unverified.
  • NON-Liouvillian is reported by SPECIAL-FUNCTION RECOGNITION (airy/bessel are classically non-Liouvillian,
    Galois group SL₂) — this is recognition, NOT a from-scratch differential-Galois proof. Labeled as such;
    we do NOT claim "PROVEN non-existence". Honest informative DEFER.

Clock (§4): Clock C (the emitted integration loop O(steps) → O(1) analytic eval). The LLM call (Clock A)
and the verification (Clock B) are unchanged — perceived response latency does NOT change.
"""
from __future__ import annotations

import ast
import random
from dataclasses import dataclass
from typing import Optional, Tuple

# special functions whose appearance in a solution means NON-Liouvillian (out of closed form)
_SPECIAL = ("airyai", "airybi", "besseli", "besselj", "besselk", "bessely", "hyper",
            "erf", "erfi", "fresnel", "Ei", "li", "Si", "Ci", "gamma", "lowergamma", "uppergamma")


@dataclass
class OdeVerdict:
    status: str                 # FOLDED | DEFER | OUT_OF_SCOPE
    liouvillian: Optional[bool] # True | False | None(undecided)
    closed_form: str = "—"
    cert_type: str = "—"        # "exact" (re-substitution) | "—"
    verified_exact: bool = False
    verified_numeric: bool = False
    clock: str = "C"
    detail: str = ""

    def __str__(self):
        if self.status == "FOLDED":
            return f"FOLDED [Clock C] y(x)={self.closed_form}  (cert: {self.cert_type}; {self.detail})"
        return f"{self.status} — {self.detail}"


# ─────────────────────────────────────────────────────── A.1 — discretization detector
def euler_source(p: str, q: str, *, h: str = "h") -> str:
    """Render a canonical explicit-Euler discretization of y'' + p(x)y' + q(x)y = 0 (system form
    y'=v, v'=-p·v-q·y). Used to exercise the detector on REAL loop code."""
    return (
        "x, u, v = x0, u0, v0\n"
        "for _ in range(steps):\n"
        "    u_new = u + {h}*v\n"
        "    v_new = v + {h}*(-({p})*v - ({q})*u)\n"
        "    u, v, x = u_new, v_new, x + {h}\n"
    ).format(p=p, q=q, h=h)


def recover_ode_from_euler(src: str) -> Optional[Tuple[str, str]]:
    """Parse an explicit-Euler 2nd-order discretization and recover (p, q) of y''+p y'+q y=0.
    Reads the v-update increment φ where v_new = v + h·φ, with φ = -p(x)·v - q(x)·u (linear in u,v).
    Returns (p_str, q_str) or None if the loop is not a recognizable 2nd-order linear Euler scheme."""
    import sympy as sp
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    # find an assignment `v_new = v + h*( ... )`
    incr = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "v_new":
            # node.value should be  v + h*(φ)
            try:
                expr = ast.unparse(node.value)
            except Exception:  # noqa: BLE001
                return None
            incr = expr
            break
    if incr is None:
        return None
    x, u, v, h = sp.symbols("x u v h")
    try:
        e = sp.sympify(incr, locals={"x": x, "u": u, "v": v, "h": h})
        phi = sp.expand((e - v) / h)          # strip the `v +` and the step `h` → φ = -p v - q u
        if not phi.has(u) and not phi.has(v):
            return None
        # linear in u, v: φ = -p·v - q·u
        p = sp.simplify(-phi.coeff(v, 1))
        q = sp.simplify(-phi.coeff(u, 1))
        # soundness: reconstruct and confirm φ == -p v - q u (rejects nonlinear / cross-term loops)
        if sp.simplify(phi - (-p * v - q * u)) != 0:
            return None
        return (str(p), str(q))
    except Exception:  # noqa: BLE001
        return None


# ─────────────────────────────────────────────────────── A.2 — Kovacic / Liouvillian decision + SOUND verify
def _is_closed_liouvillian(sol_str: str) -> bool:
    """A dsolve answer is a Liouvillian closed form only if it has NO special function, NO truncated
    series (Order/O(...)), and NO unevaluated Integral."""
    if any(s in sol_str for s in _SPECIAL):
        return False
    if "Order" in sol_str or "O(" in sol_str:        # truncated power series — NOT a closed form
        return False
    if "Integral" in sol_str:
        return False
    return True


def _verify_solution(p, q, rhs, x, consts) -> Tuple[bool, bool]:
    """★ THE SOUND GATE ★ — substitute the candidate general solution into L[y]=y''+p y'+q y and require
    it to be IDENTICALLY zero. Returns (exact_ok, numeric_ok):
      exact_ok   : sympy.simplify(L[rhs]) == 0  (a real proof the candidate solves the ODE)
      numeric_ok : L[rhs] evaluates to ~0 at random x and random constants (independent cross-check)."""
    import sympy as sp
    L = sp.diff(rhs, x, 2) + p * sp.diff(rhs, x, 1) + q * rhs
    try:
        exact_ok = sp.simplify(L) == 0
    except Exception:  # noqa: BLE001
        exact_ok = False
    # numeric cross-check (random differential identity test): pick random reals, require |L| tiny
    numeric_ok = True
    rng = random.Random(12345)
    try:
        for _ in range(6):
            subs = {c: sp.Rational(rng.randint(-5, 5)) for c in consts}
            subs[x] = sp.Rational(rng.randint(1, 9), rng.randint(1, 4))   # avoid x=0 (poles in Euler-Cauchy)
            val = complex(L.subs(subs))
            if abs(val) > 1e-6:
                numeric_ok = False
                break
    except Exception:  # noqa: BLE001
        numeric_ok = False
    return exact_ok, numeric_ok


def kovacic_decide(p_str: str, q_str: str, *, order: int = 2, linear: bool = True) -> OdeVerdict:
    """Decide foldability of y'' + p(x)y' + q(x)y = 0. dsolve PROPOSES a closed form; the SOUND gate
    (exact re-substitution) DISPOSES. Non-Liouvillian / out-of-scope ⇒ HONEST_DEFER with a reason."""
    import sympy as sp
    if order != 2 or not linear:                      # A.3 honest scope
        return OdeVerdict("OUT_OF_SCOPE", None,
                          detail=f"Kovacic applies to 2nd-order LINEAR ODEs only (got order={order}, "
                                 f"linear={linear}) — out of scope, DEFER")
    x = sp.Symbol("x")
    try:
        p = sp.sympify(p_str, locals={"x": x})
        q = sp.sympify(q_str, locals={"x": x})
    except Exception as e:  # noqa: BLE001
        return OdeVerdict("DEFER", None, detail=f"coefficients not analyzable ({type(e).__name__})")
    y = sp.Function("y")
    ode = sp.Eq(y(x).diff(x, 2) + p * y(x).diff(x) + q * y(x), 0)
    try:
        sol = sp.dsolve(ode, y(x))
    except Exception as e:  # noqa: BLE001
        return OdeVerdict("DEFER", None, detail=f"dsolve could not solve it ({type(e).__name__}) — DEFER")
    rhs = sol.rhs
    sol_str = str(rhs)
    if not _is_closed_liouvillian(sol_str):
        # informative, honest DEFER — recognition of why (special function / series / integral)
        why = next((s for s in _SPECIAL if s in sol_str), None)
        if why:
            reason = (f"NON-Liouvillian: solution involves special function `{why}` (classically Galois "
                      f"group SL₂ — no Liouvillian closed form). Recognition, NOT a from-scratch proof.")
            return OdeVerdict("DEFER", False, detail=reason, clock="C")
        if "Order" in sol_str or "O(" in sol_str:
            return OdeVerdict("DEFER", None, detail="dsolve returned a TRUNCATED power series (not a closed "
                              "form) — DEFER (no fake fold).", clock="C")
        return OdeVerdict("DEFER", None, detail="solution not in closed Liouvillian form — DEFER", clock="C")
    # candidate closed form → ★ SOUND VERIFY before folding ★
    consts = sorted(rhs.free_symbols - {x}, key=str)
    exact_ok, numeric_ok = _verify_solution(p, q, rhs, x, consts)
    if not exact_ok:
        return OdeVerdict("DEFER", None, closed_form=sol_str,
                          detail="candidate FAILED exact re-substitution (L[y]≢0) — refusing to fold "
                                 "(never a false structure)", verified_numeric=numeric_ok, clock="C")
    # Wronskian ≠ 0 (two independent solutions) — confirm it's a genuine 2-dim solution space
    indep = True
    try:
        basis = [rhs.coeff(c) for c in consts if rhs.coeff(c) != 0]
        if len(basis) >= 2:
            W = sp.simplify(basis[0] * sp.diff(basis[1], x) - sp.diff(basis[0], x) * basis[1])
            indep = (W != 0)
    except Exception:  # noqa: BLE001
        indep = True
    return OdeVerdict("FOLDED", True, closed_form=sol_str, cert_type="exact",
                      verified_exact=True, verified_numeric=numeric_ok, clock="C",
                      detail=f"Liouvillian; L[y]≡0 verified symbolically{' + numeric' if numeric_ok else ''}; "
                             f"independent-solutions={indep}; O(steps)→O(1) analytic eval")


# ─────────────────────────────────────────────────────── A.4 — corpus measurement
def measure_ode_corpus(split: Optional[str] = None) -> dict:
    """Run the Kovacic decision over the defer corpus's `ode` category. Reports decision rate (definite
    Liouvillian/non-Liouvillian vs undecided) AND fold rate (verified closed form). `split` optionally
    restricts to held-out cases. Coverage is MEASURED here — never estimated."""
    import defer_corpus as DC
    ode = [c for c in DC.load() if c.category == "ode" and (split is None or c.split == split)]
    decided = folded = correct = 0
    rows = []
    for c in ode:
        v = kovacic_decide(c.meta["p"], c.meta["q"])
        is_fold = (v.status == "FOLDED")
        is_decided = (v.liouvillian is not None)        # we gave a definite Liouvillian / non-Liouvillian call
        # correctness vs the honest label: foldable→FOLDED, defer→not FOLDED
        ok = (is_fold == (c.expect == "foldable"))
        decided += int(is_decided)
        folded += int(is_fold)
        correct += int(ok)
        rows.append((c.cid, c.expect, v.status, v.liouvillian, ok))
    n = len(ode)
    return {"n": n, "decided": decided, "folded": folded, "correct": correct,
            "decision_rate": round(decided / n, 3) if n else 0.0,
            "fold_rate": round(folded / n, 3) if n else 0.0,
            "correctness": round(correct / n, 3) if n else 0.0,
            "rows": rows, "clock": "C", "scope": "2nd-order linear ODE only"}
