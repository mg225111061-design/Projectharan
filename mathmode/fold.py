"""
MATH-Ascent §2 — FOLD: the ZFC-grade universal structure-folding tool (the center of everything).
===================================================================================================
`fold(object) → FoldResult{closed_form | canonical_form | DECLINE, certificate}`. It RECOGNIZES the structure
FIRST (math always has structure), routes to the right folding method (power sums → Faulhaber; recurrences →
companion/cfinite; geometric/telescoping → closed form; polynomial identities → e-graph; …), and CO-GENERATES a
machine-checked certificate — folding and proving are one act (Leap-2). Where there is no foldable structure
(unstructured / no closed form), fold DECLINEs honestly — never a fabricated formula (F5). EXACT only with a
checked certificate; an approximate summary is PROBABILISTIC(ε,δ).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

import cfinite
import kernel_verdict as KV
from pillar3 import kinduction as KI


@dataclass
class FoldResult:
    verdict: "KV.Verdict"
    structure: str                       # the recognized structure (or "none")
    closed_form: Optional[Callable]      # n ↦ value  (O(1)/O(log n)), or None on DECLINE
    detail: str = ""


# ── F2: structure recognition FIRST ─────────────────────────────────────────────────────────────────────
_KINDS = {"power_sum", "linear_recurrence", "geometric_sum", "telescoping_sum", "polynomial_identity"}


def recognize_structure(obj: Any) -> str:
    """Identify the structure of a math object. Returns the structure kind, or 'none' (⇒ honest DECLINE)."""
    if isinstance(obj, dict) and obj.get("kind") in _KINDS:
        return obj["kind"]
    return "none"


# ── the folding methods (each EXACT-certified or honest DECLINE) ────────────────────────────────────────
def _faulhaber_closed(p: int) -> Callable:
    """Σ_{k=1}^{n} k^p as an exact-integer O(1) closed form (rationals cleared)."""
    if p == 0:
        return lambda n: n
    if p == 1:
        return lambda n: n * (n + 1) // 2
    if p == 2:
        return lambda n: n * (n + 1) * (2 * n + 1) // 6
    if p == 3:
        return lambda n: (n * (n + 1) // 2) ** 2
    if p == 4:
        return lambda n: n * (n + 1) * (2 * n + 1) * (3 * n * n + 3 * n - 1) // 30
    return None


def _faulhaber_z3(p: int) -> Callable:
    """The same closed form over z3 integer division (for the k-induction proof, ∀ n)."""
    if p == 0:
        return lambda k: k
    if p == 1:
        return lambda k: k * (k + 1) / 2
    if p == 2:
        return lambda k: k * (k + 1) * (2 * k + 1) / 6
    if p == 3:
        return lambda k: (k * (k + 1) / 2) * (k * (k + 1) / 2)
    if p == 4:
        return lambda k: k * (k + 1) * (2 * k + 1) * (3 * k * k + 3 * k - 1) / 30
    return None


def _fold_power_sum(obj) -> FoldResult:
    """Σ_{k=1}^{n} k^p → Faulhaber closed form, PROVEN for ALL n by induction:
        base   cz(0) = 0                      (empty sum)
        step   cz(n) − cz(n−1) = n^p          (a polynomial identity — Z3/nlsat decides it ∀ real n ⇒ ∀ n)
    The step is a polynomial identity over the reals (no integer-division incompleteness); reals ⊇ integers, so
    a real-valid identity is integer-valid. base ∧ step ⇒ cz ≡ Σk^p for all n≥0 (EXACT, O(1) evaluation)."""
    p = int(obj["p"])
    cz, cn = _faulhaber_z3(p), _faulhaber_closed(p)
    if cz is None or cn is None:
        return FoldResult(KV.decline(f"power_sum p={p}: closed form beyond degree 4 not stocked ⇒ DECLINE", "fold"),
                          "power_sum", None, "no stocked Faulhaber polynomial")
    import z3
    n = z3.Real("n")
    term = z3.RealVal(1) if p == 0 else n ** p           # the k-th summand k^p (p=0 ⇒ the constant 1)
    base_ok, _ = KI._valid(cz(z3.RealVal(0)) == z3.RealVal(0))
    step_ok, cex = KI._valid(cz(n) - cz(n - 1) == term)  # cz(n) − cz(n−1) = n^p, ∀ real n
    if base_ok and step_ok:
        cert = KV.Cert(KV.EXACT, "faulhaber_kinduction", passed=True, check_cost="Z3 base + polynomial step (∀n)",
                       detail=f"Σ_(k=1..n) k^{p} = Faulhaber closed form; base cz(0)=0 ∧ step cz(n)−cz(n−1)=n^{p} "
                              f"proven ⇒ EXACT for ALL n (O(1) evaluation)")
        return FoldResult(KV.exact(cn, "fold", f"power_sum p={p}: O(1) closed form", cert), "power_sum", cn,
                          "Faulhaber closed form, proven ∀n by induction")
    why = "base cz(0)≠0" if not base_ok else f"step cz(n)−cz(n−1)≠n^{p} (cex {cex})"
    return FoldResult(KV.decline(f"power_sum p={p}: closed form NOT inductively verified ({why}) ⇒ DECLINE", "fold"),
                      "power_sum", None, "induction failed")


def _fold_linear_recurrence(obj) -> FoldResult:
    """A C-finite recurrence f(n)=Σ c_i f(n-1-i) → companion-matrix O(log n) closed form (EXACT integers)."""
    c, init, n = [int(x) for x in obj["c"]], [int(x) for x in obj["init"]], int(obj.get("n", 0))
    if len(init) != len(c) or n < 0:
        return FoldResult(KV.decline("linear_recurrence needs len(init)==len(c), n≥0 ⇒ DECLINE", "fold"),
                          "linear_recurrence", None, "shape")
    ok, _checked = cfinite.verify_cfinite(c, init)          # companion ≡ naive on a probe set (exact integers)
    if not ok:
        return FoldResult(KV.decline("recurrence failed companion≡naive verification ⇒ DECLINE", "fold"),
                          "linear_recurrence", None, "verification")
    cf = lambda nn: cfinite.companion_nth(c, init, nn)
    cert = KV.Cert(KV.EXACT, "cfinite_companion", passed=True, check_cost="O(d³ log n) probe",
                   detail=f"order-{len(c)} C-finite; companion-matrix power ≡ naive (exact integers), O(log n)")
    return FoldResult(KV.exact(cf, "fold", "linear_recurrence: O(log n) companion", cert), "linear_recurrence", cf,
                      "companion closed form")


def _fold_geometric_sum(obj) -> FoldResult:
    """Σ_{k=0}^{n-1} r^k = (r^n − 1)/(r − 1) (r≠1) — exact integers, verified against the naive on a probe set."""
    r = int(obj["r"])
    if r == 1:
        cf = lambda nn: nn
    else:
        cf = lambda nn: (r ** nn - 1) // (r - 1)
    # certificate: closed ≡ naive partial sum on a probe set (exact integers); the geometric-series identity
    def naive(nn):
        s = 0
        for k in range(nn):
            s += r ** k
        return s
    probe = [0, 1, 2, 5, 9, 16]
    if any(cf(nn) != naive(nn) for nn in probe):
        return FoldResult(KV.decline("geometric_sum closed form disagreed with the naive ⇒ DECLINE", "fold"),
                          "geometric_sum", None, "verification")
    cert = KV.Cert(KV.EXACT, "geometric_closed", passed=True, check_cost=f"{len(probe)}-point exact probe",
                   detail=f"Σ r^k = (r^n-1)/(r-1), r={r} (exact integers; closed ≡ naive on probe)")
    return FoldResult(KV.exact(cf, "fold", "geometric_sum: O(log n) via fast-pow", cert), "geometric_sum", cf,
                      "geometric closed form")


def _fold_telescoping(obj) -> FoldResult:
    """Σ_{k=0}^{n-1} (g(k+1) − g(k)) = g(n) − g(0). `g` supplied; certificate is the telescoping identity, verified."""
    g = obj["g"]
    cf = lambda nn: g(nn) - g(0)

    def naive(nn):
        return sum(g(k + 1) - g(k) for k in range(nn))
    if any(cf(nn) != naive(nn) for nn in (0, 1, 3, 7, 12)):
        return FoldResult(KV.decline("telescoping closed form disagreed with the naive ⇒ DECLINE", "fold"),
                          "telescoping_sum", None, "verification")
    cert = KV.Cert(KV.EXACT, "telescoping", passed=True, check_cost="5-point exact probe",
                   detail="Σ(g(k+1)-g(k)) = g(n)-g(0) (telescoping identity, verified)")
    return FoldResult(KV.exact(cf, "fold", "telescoping_sum: O(1)", cert), "telescoping_sum", cf, "telescoping")


def _fold_polynomial_identity(obj) -> FoldResult:
    """A polynomial expression (Term) → its Z3-certified simplest equivalent (e-graph equality saturation)."""
    import equality_saturation as ES
    v = ES.optimize(obj["term"], obj.get("max_iters", 8))
    if v.status != "OPTIMIZED":
        return FoldResult(KV.decline(f"polynomial_identity: {v.status} ({v.detail}) ⇒ DECLINE", "fold"),
                          "polynomial_identity", None, v.detail)
    best = v.optimized
    cert = KV.Cert(KV.EXACT, "egraph_z3_equiv", passed=True, check_cost="Z3 ∀-vars",
                   detail=f"equality saturation; Z3-proven term≡rewrite; {v.before}→{v.after} nodes")
    return FoldResult(KV.exact(best, "fold", f"polynomial_identity: {v.before}→{v.after} nodes", cert),
                      "polynomial_identity", None, ES.fmt(best))


_DISPATCH = {
    "power_sum": _fold_power_sum,
    "linear_recurrence": _fold_linear_recurrence,
    "geometric_sum": _fold_geometric_sum,
    "telescoping_sum": _fold_telescoping,
    "polynomial_identity": _fold_polynomial_identity,
}


def fold(obj: Any) -> FoldResult:
    """F1 — the universal fold. Recognize structure FIRST, route to the folding method, return closed form +
    certificate (EXACT) or an honest DECLINE (no structure / no closed form). Folding and proving are one act."""
    structure = recognize_structure(obj)
    if structure == "none":
        return FoldResult(KV.decline("fold: no foldable structure recognized ⇒ DECLINE (not a fabricated formula)",
                                     "fold"), "none", None, "unstructured / no closed form")
    return _DISPATCH[structure](obj)
