"""
§BH ★ THE SPINE — recurrence→closed-form bridge: the loop axis-1 *folds* is the loop axis-2 *proves*.
======================================================================================================
The research's single strongest finding is that the two axes are ONE weapon. Take a linear-update loop

        x ← x0 ;  while x < N:  x ← a·x + b

• axis-1 (LLM-external execution acceleration) wants its CLOSED FORM, to *fold* away the loop:
  the affine map x↦a·x+b homogenizes to the order-2 C-finite recurrence  x_{k+1} = (1+a)·x_k − a·x_{k-1}
  (because x_{k+1}−x_k = a·(x_k−x_{k-1})), whose companion matrix is  C = [[1+a, −a], [1, 0]].
  Power-by-squaring C^n gives x_n in O(log n) instead of O(n)  →  reuse `cfinite.companion_nth`.

• axis-2 (thorough verification) wants to PROVE the loop TERMINATES: a ranking function r(x)=N−x that is
  bounded below and STRICTLY DECREASES under the guard. z3 discharges both obligations  →  reuse
  `pillar3.termination.proves_termination`.

★ THE BRIDGE (same math, build once both gain). The fold's per-step increment is
        Δ(x) = x_{k+1} − x_k = (a−1)·x + b
and the ranking function's change is  Δr(x) = r(x_{k+1}) − r(x) = −(x_{k+1}−x_k) = −Δ(x).
So **"the fold makes progress toward N" (Δ>0)  ⟺  "the ranking function strictly decreases" (Δr<0)** —
the *same expression* (a−1)·x+b, read once by axis-1 (closed-form growth) and once by axis-2 (termination).
The companion matrix C that axis-1 raises to the n-th power is the same linear map whose progress axis-2
certifies. Eigenvalues {a, 1}: the `1` is the constant offset b's mode, the `a` is the geometric mode —
together they decide BOTH the closed form AND whether the loop ever crosses N.

Honesty (false-EXACT 0, Rice-bounded): the fold is EXACT (lossless-by-theorem, re-checked vs naïve over a
window). Termination is EXACT only when z3 *proves* it (ranking bounded-below & strictly-decreasing under the
guard, possibly with the reachable start-invariant); otherwise DECLINE — we NEVER assume termination. The
degenerate a=1,b=0 loop folds to a CONSTANT (no progress) and is genuinely non-terminating: fold-to-constant
⟺ Δ≡0 ⟺ no ranking function ⟺ DECLINE. zero-dep: cfinite + z3 (via termination) + kernel_verdict.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import z3

import cfinite as CF
import kernel_verdict as KV
from pillar3 import termination as TERM


# ── the shared object: companion matrix C = [[1+a, −a],[1,0]]  and the homogenized C-finite recurrence ──
def companion_matrix(a: int) -> List[List[int]]:
    """The 2×2 companion matrix of the homogenized affine recurrence x_{k+1}=(1+a)x_k − a·x_{k-1}.
    ★ This ONE matrix is raised to the n-th power by axis-1 (fold) and is the linear map whose progress
    axis-2 (prove) certifies. Eigenvalues are {a, 1}."""
    return [[1 + a, -a], [1, 0]]


def _affine_to_cfinite(a: int, b: int, x0: int) -> Tuple[List[int], List[int]]:
    """Homogenize x_{k+1}=a·x_k+b into the order-2 homogeneous form cfinite consumes:
    c=[1+a, −a] (coeffs of x_{k-1}, x_{k-2}), init=[x0, x1]=[x0, a·x0+b]."""
    return [1 + a, -a], [x0, a * x0 + b]


def step_difference(a: int, b: int, x: int) -> int:
    """★ THE shared expression Δ(x)=(a−1)·x+b: axis-1's per-step closed-form increment AND −1× axis-2's
    ranking change. Δ>0 ⟺ progress toward N ⟺ ranking strictly decreases."""
    return (a - 1) * x + b


# ── axis-1: fold the loop to its closed form (O(log n)), EXACT, re-checked vs naïve ─────────────────────
def fold_linear_loop(a: int, b: int, x0: int, n: int) -> KV.Verdict:
    """axis-1: x_n via companion-matrix power in O(log n) (reuse cfinite). EXACT (lossless-by-theorem),
    re-verified companion≡naïve over a window so the certificate is machine-rechecked, not asserted."""
    c, init = _affine_to_cfinite(a, b, x0)
    ok, checked = CF.verify_cfinite(c, init, ns=(2, 5, 9, 14, 20))
    if not ok:
        return KV.decline(f"fold self-check failed (companion≢naïve) for a={a},b={b},x0={x0}", "bridge_fold")
    val = CF.companion_nth(c, init, n)
    if a == 1:
        form = f"x_n = x0 + n·b = {x0} + {b}·n"
    else:
        form = f"x_n = a^n·x0 + b·(a^n−1)/(a−1) = {a}^n·{x0} + {b}·({a}^n−1)/{a - 1}"
    cert = KV.Cert(KV.EXACT, "cfinite_companion", passed=True, check_cost="O(log n) ring ops",
                   detail=f"companion C={companion_matrix(a)} (eig {{{a},1}}); {form}; companion≡naïve on n∈{list(checked)}")
    return KV.exact(val, "bridge_fold", "O(log n)", cert)


# ── axis-2: prove the loop terminates via the ranking function r(x)=N−x (reuse pillar3.termination) ─────
def prove_terminates(a: int, b: int, N: int, start_invariant: Optional[int] = None) -> "TERM.TermResult":
    """axis-2: z3-prove `while x<N: x=a·x+b` terminates with rank r(x)=N−x. Optionally strengthen the guard
    with a reachable start-invariant x≥start_invariant (e.g. x≥x0 when the trajectory never decreases) — this
    is exactly the closed-form positivity that flips a conservative DECLINE into a PROVED EXACT.
    EXACT iff proven; DECLINE otherwise (never assume termination — sound, Rice-bounded)."""
    if start_invariant is None:
        cond = lambda x: x < N
    else:
        cond = lambda x: z3.And(x < N, x >= start_invariant)
    step = lambda x: a * x + b
    rank = lambda x: N - x
    name = f"loop(a={a},b={b},N={N}" + (f",x≥{start_invariant}" if start_invariant is not None else "") + ")"
    return TERM.termination_grade(name, cond, step, rank)


# ── the bridge: ONE object, both axes, and the consistency theorem checked numerically ──────────────────
@dataclass
class BridgeResult:
    a: int
    b: int
    N: int
    x0: int
    fold: KV.Verdict                 # axis-1 closed form (O(log n))
    terminates: "TERM.TermResult"    # axis-2 z3 ranking-function verdict
    companion: List[List[int]]
    progress_at_x0: int              # Δ(x0)=(a−1)x0+b — the shared expression
    bridge_consistent: bool          # ★ (fold makes progress along trajectory) ⟺ (z3 proved termination)


def bridge(a: int, b: int, N: int, x0: int, n_demo: int = 20,
           use_start_invariant: bool = True) -> BridgeResult:
    """★ Run BOTH axes on the SAME loop and assert the bridge: the fold's progress and the prover's termination
    are the same fact. We prove termination under the reachable invariant x≥x0 when the trajectory is
    non-decreasing (Δ≥0 at the start and a≥1 ⇒ Δ never decreases), mirroring the closed form's monotonicity."""
    comp = companion_matrix(a)
    fold = fold_linear_loop(a, b, x0, n_demo)
    d0 = step_difference(a, b, x0)
    # The reachable trajectory stays ≥ x0 exactly when it makes non-negative progress and does not turn around;
    # for a≥1 with Δ(x0)≥0 the increment Δ(x)=(a−1)x+b only grows as x grows ⇒ x≥x0 is invariant.
    inv = x0 if (use_start_invariant and a >= 1 and d0 >= 0) else None
    term = prove_terminates(a, b, N, start_invariant=inv)
    progresses = (d0 > 0)                                   # fold strictly advances toward N from x0
    proved = (term.verdict.status == KV.EXACT)
    bridge_consistent = (progresses == proved)             # ★ Δ>0 ⟺ z3 proves termination — same math
    return BridgeResult(a, b, N, x0, fold, term, comp, d0, bridge_consistent)


# ── battery: the flagship demonstration (terminating ⟺ folds-with-progress; non-term ⟺ folds-to-constant) ──
def bridge_battery() -> dict:
    """★ increasing-affine loops: fold EXACT + z3 PROVES termination + bridge consistent (Δ>0).
    ★ degenerate a=1,b=0: folds to a CONSTANT + z3 DECLINEs (genuinely non-terminating) + bridge consistent (Δ=0).
    ★ geometric a=2: folds EXACT unconditionally; termination is start-dependent — z3 PROVES it under the
      reachable invariant x≥x0≥0 (the closed-form positivity), demonstrating the bridge end-to-end."""
    R = {}
    # 1) increasing affine: while x<100: x+=7    folds linear, terminates (Δ=7>0)
    R["incr_b7"] = bridge(a=1, b=7, N=100, x0=0)
    # 2) increasing affine: while x<1000: x+=1   folds linear, terminates (Δ=1>0)
    R["incr_b1"] = bridge(a=1, b=1, N=1000, x0=0)
    # 3) degenerate: while x<100: x=x            folds to CONSTANT x0, non-terminating (Δ=0)
    R["degenerate"] = bridge(a=1, b=0, N=100, x0=0)
    # 4) geometric: while x<1_000_000: x=2x+1    folds 2^n closed form; terminates under x≥x0=1 (Δ=2>0)
    R["geom_a2"] = bridge(a=2, b=1, N=1_000_000, x0=1)

    cases = {
        "incr_b7_folds_EXACT": R["incr_b7"].fold.status == KV.EXACT,
        "incr_b7_PROVES_term": R["incr_b7"].terminates.verdict.status == KV.EXACT,
        "incr_b7_bridge_consistent": R["incr_b7"].bridge_consistent,
        "incr_b1_folds_EXACT": R["incr_b1"].fold.status == KV.EXACT,
        "incr_b1_PROVES_term": R["incr_b1"].terminates.verdict.status == KV.EXACT,
        "degenerate_folds_to_constant": R["degenerate"].fold.status == KV.EXACT and R["degenerate"].fold.result == 0,
        "degenerate_DECLINEs_term": R["degenerate"].terminates.verdict.status == KV.DECLINE,
        "degenerate_bridge_consistent": R["degenerate"].bridge_consistent,      # Δ=0 ⟺ no progress ⟺ DECLINE
        "geom_folds_EXACT": R["geom_a2"].fold.status == KV.EXACT,
        "geom_PROVES_term_under_invariant": R["geom_a2"].terminates.verdict.status == KV.EXACT,
        "geom_bridge_consistent": R["geom_a2"].bridge_consistent,
        # ★ the shared expression: fold's per-step Δ equals −1× the ranking change, checked numerically
        "shared_expression_holds": all(
            step_difference(a, b, x) == (a * x + b) - x                          # Δ(x) = x_{k+1} − x_k
            for (a, b) in [(1, 7), (1, 0), (2, 1), (3, -4)] for x in (-5, 0, 11, 100)
        ),
    }
    return {"cases": cases, "all_ok": all(cases.values()),
            "failed": [k for k, v in cases.items() if not v]}


if __name__ == "__main__":
    import json
    out = bridge_battery()
    print(json.dumps(out["cases"], indent=2))
    print("ALL_OK:", out["all_ok"], "FAILED:", out["failed"])
    # show one bridge in full
    r = bridge(a=1, b=7, N=100, x0=0)
    print(f"\nbridge(while x<100: x+=7): companion={r.companion}  Δ(x0)={r.progress_at_x0}")
    print(f"  axis-1 fold     : {r.fold.status}  x_20={r.fold.result}  [{r.fold.complexity}]")
    print(f"  axis-2 terminates: {r.terminates.verdict.status}  ({r.terminates.verdict.reason or r.fold.certificate.detail[:60]})")
    print(f"  ★ bridge_consistent (Δ>0 ⟺ proves-termination): {r.bridge_consistent}")
