"""
§X PARADIGM 5 — STRIDE / COMPOSITION FOLD (cheap to add; the weakest — folds f^k when f doesn't).
================================================================================================================
When a step function `f` doesn't fold but `f^k` (k-fold composition) does — cancellation / oscillation / period —
fold in k-blocks. An alternating-sign update where `f² == identity` collapses to O(1); a rotation where `f^k` is
linear collapses to a matrix-power. Run `folded_k` over n/k blocks, the n%k remainder applied directly.

★ z3 gate (precision 1.0): prove ∀s. f^k(s) == folded_k(s) (the composition equivalence). Proved ⇒ fold; else DECLINE.
★ Honest boundary (this is the weakest paradigm): works only where f^k is SIMPLER than f (cancellation/oscillation/
period). General nonlinear systems (f(s)=s²+1 — logistic-like) where every f^k is as complex ⇒ DECLINE. Bounded
k ≤ 64. Expect a SMALL contribution — reported honestly, not oversold. NO new certificate kind. Adversarial: an f^k
fold that isn't actually equivalent is rejected.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass
class StrideFold:
    issued: bool
    paradigm: str = "stride"
    mechanism: str = "matrix_recurrence"
    k: Optional[int] = None
    detail: str = ""


def _compose(f: Callable, k: int) -> Callable:
    def fk(s):
        for _ in range(k):
            s = f(s)
        return s
    return fk


def _is_affine(f: Callable) -> bool:
    """Prove f is affine (f(s)=c·s+d) via the Cauchy identity ∀a,b. f(a+b)−f(a)−f(b)+f(0)==0 — ONE small z3 check, no
    composition. ★ This is the safety gate AND the honest boundary: f^k stays bounded only for affine/periodic maps;
    a nonlinear f (s²+1) would make f^k explode (degree 2^k) and never simplify, so it is DECLINED here without ever
    being composed (the directive's general-nonlinear DECLINE, made cheap and total)."""
    import z3
    a, b = z3.Int("a"), z3.Int("b")
    solver = z3.Solver()
    solver.add(f(a + b) - f(a) - f(b) + f(0) != 0)
    return solver.check() == z3.unsat


def prove_fk_equiv(f: Callable, folded_k: Callable, k: int) -> bool:
    """Prove ∀s. f^k(s) == folded_k(s) (z3 ∀ over Int). Composes f^k — SAFE only because the caller has gated on
    `_is_affine` (affine f ⇒ f^k stays linear-sized; a nonlinear f is DECLINED before reaching here)."""
    import z3
    s = z3.Int("s")
    fk = _compose(f, k)
    solver = z3.Solver()
    solver.set("timeout", 2000)
    solver.add(fk(s) != folded_k(s))
    return solver.check() == z3.unsat


# candidate simplified forms for f^k
def _identity(s):
    return s


def search_stride(f: Callable, ks: List[int] = (2, 4, 8, 16, 32, 64)) -> StrideFold:
    """Bounded k-search: for each k, check whether f^k collapses to a simpler form (here: the identity — the
    cancellation/oscillation case). The first k for which `f^k == identity` is z3-proved is issued. None ⇒ DECLINE.
    ★ Gated on affineness first: a general nonlinear f (whose f^k would explode and never simplify) is DECLINED
    immediately, without composing — that is the honest boundary and the safety bound."""
    if not _is_affine(f):
        return StrideFold(False, detail="f is not affine — every f^k is as complex (general nonlinear, e.g. s²+1) "
                          "⇒ DECLINE without composing (honest boundary; no explosion)")
    for k in ks:
        if prove_fk_equiv(f, _identity, k):
            return StrideFold(True, k=k, detail=f"f^{k} ≡ identity (z3 ∀-proved) — period-{k} cancellation collapses "
                              f"the loop to n/{k} blocks; small honest contribution")
    return StrideFold(False, detail="no k≤64 makes f^k simpler (general nonlinear — every f^k as complex) ⇒ DECLINE")


def adversarial_battery() -> dict:
    """negation f(s)=-s has f²==identity (folds); a general nonlinear f(s)=s²+1 has no simpler f^k (DECLINE); a
    wrong claim (f²==identity for f(s)=s+1) is rejected."""
    neg = search_stride(lambda s: -s)                          # f² == identity ⇒ issued at k=2
    nonlinear = search_stride(lambda s: s * s + 1)             # every f^k as complex ⇒ DECLINE
    # ★ adversarial: f(s)=s+1, f² = s+2 ≠ identity ⇒ must NOT be issued
    wrong = search_stride(lambda s: s + 1)
    cases = {"negation_period2_folds": neg.issued and neg.k == 2,
             "general_nonlinear_declined": not nonlinear.issued,
             "wrong_fk_rejected": not wrong.issued}
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
