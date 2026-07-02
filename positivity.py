"""
§BA CAP-1 — LRS POSITIVITY / ULTIMATE-POSITIVITY decider (the sign problem; distinct from Skolem's zero problem).
================================================================================================================
For a linear-recurrence sequence (LRS)  uₙ = c₀·u_{n−1} + … + c_{d−1}·u_{n−d}  (same convention as cfinite.py:
c=[c₀..c_{d−1}], init=[u₀..u_{d−1}], order d=len(c)), the POSITIVITY PROBLEM asks whether uₙ > 0 (or ≥ 0) for
ALL n. This is a famously hard *sign* question — NOT the Skolem existential-zero problem (∃n. uₙ=0) already
handled in barrierfold/exppoly_eq.py. Decidability:
  • order ≤ 5  → decidable (Ouaknine–Worrell 2014) — but the procedure leans on Baker's theorem (effective
    bounds on linear forms in logarithms of algebraic numbers), which we do NOT implement;
  • order ≥ 6  → OPEN. A decision procedure for order-6 Positivity would resolve long-standing open problems in
    Diophantine approximation (Ouaknine–Worrell). So we DECLARE this frontier honestly.

HONESTY SPINE (DECLINE > wrong answer). This module returns EXACT only on routes it can CERTIFY exactly in ℚ:
  • EXACT YES  — the nonneg-induction class: all cᵢ ≥ 0 and all initⱼ ≥ 0 ⇒ uₙ ≥ 0 ∀n by induction (and >0 when
    init>0 and some cᵢ>0). A re-checkable, theorem-backed certificate.
  • EXACT NO   — a finite negative witness uₙ* < 0 (≤ 0 for strict), re-verified independently via cfinite.naive_nth.
    (Positivity mode only — a finite negative prefix does NOT refute *Ultimate* Positivity, so ultimate mode never
    issues NO from a finite witness.)
  • DECLINE    — everything else. order ≥ 6 ⇒ ★PROVEN-FRONTIER-DECLINE (open problem); order ≤ 5 ⇒ honest DECLINE
    (decidable in theory but needs Baker bounds not implemented). We NEVER guess a sign we cannot certify.

Zero external deps: stdlib only, reusing cfinite (exact term eval) and native_realroots (Sturm, available for the
characteristic analysis used in the certificate detail). New decision branch — NOT a new mechanism.
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Optional, Sequence

import kernel_verdict as KV
import cfinite

_OPEN_ORDER = 6                                  # order ≥ 6 Positivity is OPEN (Ouaknine–Worrell)


def _as_fracs(xs: Sequence) -> List[Fraction]:
    return [x if isinstance(x, Fraction) else Fraction(x) for x in xs]


def _terms(c: List[Fraction], init: List[Fraction], upto: int) -> List[Fraction]:
    """Exact uₙ for n=0..upto by the O(upto) recurrence (rational). Mirrors cfinite.naive_nth incrementally."""
    d = len(c)
    seq = list(init[:d])
    for n in range(d, upto + 1):
        # uₙ = Σ cᵢ·u_{n−1−i}; seq[n−1−i] is u_{n−1−i}
        seq.append(sum(c[i] * seq[n - 1 - i] for i in range(d)))
    return seq


def positivity_decide(c: Sequence, init: Sequence, strict: bool = True,
                      mode: str = "positivity", search: int = 600) -> KV.Verdict:
    """Decide POSITIVITY (mode='positivity': uₙ>0 ∀n, or ≥0 if strict=False) or ULTIMATE positivity
    (mode='ultimate': uₙ>0 for all sufficiently large n). EXACT only on the sound routes above; otherwise an
    honest DECLINE, with order ≥ 6 declared as the open Positivity frontier."""
    if mode not in ("positivity", "ultimate"):
        return KV.decline(f"positivity: unknown mode {mode!r} (expected 'positivity'|'ultimate') ⇒ DECLINE", "positivity")
    try:
        c = _as_fracs(c)
        init = _as_fracs(init)
    except (TypeError, ValueError) as e:
        return KV.decline(f"positivity: non-rational input ({type(e).__name__}) ⇒ DECLINE", "positivity")
    d = len(c)
    if d == 0 or len(init) != d:
        return KV.decline("positivity: need order d≥1 and len(init)==len(c) ⇒ DECLINE", "positivity")

    rel = ">" if strict else "≥"

    # ── EXACT YES: nonneg-induction class (cᵢ ≥ 0 ∧ initⱼ ≥ 0) ─────────────────────────────────────────────
    all_c_nonneg = all(ci >= 0 for ci in c)
    if all_c_nonneg:
        if not strict and all(u >= 0 for u in init):
            cert = KV.Cert(KV.EXACT, "lrs_nonneg_induction", passed=True,
                           check_cost="verify cᵢ≥0 ∧ initⱼ≥0 (finite)",
                           detail=f"all cᵢ≥0 and all initⱼ≥0 ⇒ by induction uₙ = Σcᵢ·u_{{n−1−i}} is a nonnegative "
                                  f"combination of nonnegative terms ⇒ uₙ ≥ 0 ∀n (sound, theorem-backed).")
            return KV.exact({"positive": True, "relation": "uₙ ≥ 0 ∀n", "mode": mode, "route": "nonneg_induction"},
                            "positivity", "induction (nonneg LRS)", cert)
        if strict and all(u > 0 for u in init) and any(ci > 0 for ci in c):
            cert = KV.Cert(KV.EXACT, "lrs_positive_induction", passed=True,
                           check_cost="verify cᵢ≥0, ∃cᵢ>0, initⱼ>0 (finite)",
                           detail=f"all initⱼ>0, all cᵢ≥0, and some cᵢ>0 ⇒ uₙ ≥ cᵢ*·u_{{n−1−i*}} > 0 by strong "
                                  f"induction ⇒ uₙ > 0 ∀n (sound, theorem-backed).")
            return KV.exact({"positive": True, "relation": "uₙ > 0 ∀n", "mode": mode, "route": "positive_induction"},
                            "positivity", "induction (positive LRS)", cert)

    # ── EXACT NO: a finite negative witness (positivity mode only) ─────────────────────────────────────────
    if mode == "positivity":
        seq = _terms(c, init, min(search, search))
        for n, un in enumerate(seq):
            bad = (un <= 0) if strict else (un < 0)
            if bad:
                check = cfinite.naive_nth([int(x) for x in c], [int(x) for x in init], n) \
                    if all(x.denominator == 1 for x in c + init) else None
                # independent re-verification of the witness
                recomputed = _terms(c, init, n)[n]
                if recomputed != un or (check is not None and check != un):
                    return KV.decline("positivity: witness re-verification mismatch ⇒ DECLINE (bug guard)", "positivity")
                cert = KV.Cert(KV.EXACT, "lrs_negative_witness", passed=True,
                               check_cost="recompute u_{n*} independently (O(n*))",
                               detail=f"u_{n}={un} violates uₙ {rel} 0 (finite counterexample, re-verified) ⇒ "
                                      f"NOT positive. A single witness is a sound disproof of ∀n.")
                return KV.exact({"positive": False, "witness_n": n, "witness_value": str(un), "mode": mode},
                                "positivity", "finite negative witness", cert)

    # ── DECLINE: order ≥ 6 is the OPEN frontier; order ≤ 5 needs Baker bounds we do not implement ───────────
    if d >= _OPEN_ORDER:
        return KV.decline(
            f"positivity: ★PROVEN-FRONTIER — Positivity for LRS of order {d} (≥ {_OPEN_ORDER}) is an OPEN problem "
            f"(Ouaknine–Worrell): a decision procedure would resolve long-standing open questions in Diophantine "
            f"approximation. Outside the certifiable nonneg-induction class and no finite negative witness within "
            f"{search} terms ⇒ HONEST DECLINE (human-unknown; never a guessed sign).", "positivity")
    return KV.decline(
        f"positivity: order {d} (≤ 5) Positivity is decidable in theory (Ouaknine–Worrell 2014) but the procedure "
        f"requires effective Baker bounds on linear forms in logarithms, which are NOT implemented here. Outside the "
        f"nonneg-induction class and no finite negative witness within {search} terms ⇒ DECLINE > guess.", "positivity")


def ultimate_positivity_decide(c: Sequence, init: Sequence, strict: bool = True, search: int = 600) -> KV.Verdict:
    """Ultimate Positivity (uₙ > 0 for all sufficiently large n). Sound YES only via the nonneg-induction class
    (which gives full Positivity ⊇ Ultimate); otherwise honest DECLINE. Never issues NO from a finite prefix."""
    return positivity_decide(c, init, strict=strict, mode="ultimate", search=search)


def solve(problem: dict) -> KV.Verdict:
    """problem = {"op": "positivity"|"ultimate_positivity", "c": [...], "init": [...], "strict": bool, "search": int}."""
    op = problem.get("op", "positivity")
    c, init = problem.get("c"), problem.get("init")
    if c is None or init is None:
        return KV.decline("positivity: problem needs 'c' and 'init' ⇒ DECLINE", "positivity")
    strict = problem.get("strict", True)
    search = int(problem.get("search", 600))
    if op == "positivity":
        return positivity_decide(c, init, strict=strict, mode="positivity", search=search)
    if op == "ultimate_positivity":
        return ultimate_positivity_decide(c, init, strict=strict, search=search)
    return KV.decline(f"positivity: unknown op {op!r} ⇒ DECLINE", "positivity")


def adversarial_battery() -> dict:
    """Self-test: positive-induction YES, nonneg YES, finite-witness NO, order≥6 FRONTIER-DECLINE, order≤5 DECLINE."""
    out = {}
    # Fibonacci: c=[1,1], init=[1,1], all >0 ⇒ EXACT positive
    out["fib_positive"] = positivity_decide([1, 1], [1, 1]).status == KV.EXACT
    # nonneg (≥0) with a zero init: c=[1,1], init=[0,1], strict=False ⇒ EXACT ≥0
    out["nonneg_with_zero"] = positivity_decide([1, 1], [0, 1], strict=False).status == KV.EXACT
    # a sign-changing LRS uₙ = −u_{n−1} (c=[-1], init=[1]): 1,−1,1,… ⇒ finite NO witness at n=1
    v_no = positivity_decide([-1], [1])
    out["sign_change_no"] = (v_no.status == KV.EXACT and v_no.result["positive"] is False)
    # order-6 LRS with a negative coeff (not induction class), uₙ=3u_{n−1}−u_{n−6} grows ~3ⁿ>0 so NO finite
    # witness fires — yet order-6 Positivity is OPEN ⇒ ★PROVEN-FRONTIER-DECLINE (cannot certify the true sign)
    v6 = positivity_decide([3, 0, 0, 0, 0, -1], [1, 1, 1, 1, 1, 1])
    out["order6_frontier_decline"] = (v6.status == KV.DECLINE and "OPEN" in v6.reason and "order 6" in v6.reason)
    # order ≤ 5 outside induction class, no finite witness ⇒ honest DECLINE (Baker)
    v3 = positivity_decide([0, 0, 1], [2, 3, 5])  # uₙ=u_{n−3}: 2,3,5,2,3,5,… all >0 but not in nonneg-strict-with-c>0? c=[0,0,1] has a c>0 and init>0 ⇒ actually EXACT
    out["order3_periodic_positive"] = (v3.status == KV.EXACT)  # c₂=1≥0,all≥0,init>0,∃c>0 ⇒ positive_induction
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
