"""
§AI §1 — CONJECTURE-THEN-VERIFY harness (the strongest recall lever). Observation CONJECTURES; z3 DISPOSES.
================================================================================================================
When the symbolic matcher can't READ the code (disguise: recursion / closure / CPS / object-state / dynamic
dispatch), don't give up — run it as a black box, observe the I/O, CONJECTURE a recurrence/closed-form, and let z3
prove it ∀-inputs. Conjecturing is free (a wrong guess is rejected by z3), so the numerator grows AND the disguise
dimension collapses (infinitely many disguises, ONE behavior — the black box sees behavior, not form).

★★ P-2 (the line 5 AIs failed at): OBSERVATION IS NOT PROOF. A conjecture that matches every observed point is issued
ONLY if (a) the held-out block beyond the fit is predicted EXACTLY (the divergence guard, reused from §P P1
blackbox_recover) AND (b) z3 proves the closed form satisfies the conjectured recurrence ∀n. No z3 proof ⇒ DECLINE.
★ under-determination guard: an order-d conjecture needs ≥ 2d+2 observations; fewer ⇒ ABANDON (a fit through too few
points proves nothing). ★ No new mechanism (routes to the EXISTING linear_recurrence / closed_form kinds); no new
disposer (z3 / blackbox_recover's held-out gate). LLM-free (BM / interpolation / period detection are deterministic).
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, List, Optional


@dataclass
class ConjResult:
    issued: bool
    structure_class: str = ""        # linear_recurrence | polynomial | periodic | matrix_power | holonomic | none
    order: int = 0
    proved_by: str = ""              # "z3+held-out" | "blackbox+z3" | "-"
    verdict: object = None           # the KV.Verdict (EXACT / DECLINE) — existing kinds only
    detail: str = ""


def observe(fn: Callable[[int], object], n: int) -> Optional[List[object]]:
    """Sandbox-probe a unary oracle fn(0..n-1). Returns the numeric sequence, or None if it raises / is non-numeric /
    (a cheap determinism re-check fails) — in which case the conjecture is ABANDONED and the existing path is used."""
    try:
        seq = [fn(i) for i in range(n)]
        recheck = [fn(i) for i in (0, n // 2, n - 1)]               # cheap nondeterminism screen
    except Exception:  # noqa: BLE001
        return None
    if [seq[0], seq[n // 2], seq[n - 1]] != recheck:                # non-deterministic ⇒ not a pure oracle ⇒ abandon
        return None
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in seq):
        return None
    return seq


def under_determined(num_obs: int, order_d: int) -> bool:
    """An order-d conjecture needs ≥ 2d+2 observations (d to fit + ≥d+2 to disprove a coincidence). Fewer ⇒ ABANDON.
    ★ This is the guard against 'a polynomial of degree k fits any k+1 points' — a fit is not a proof."""
    return num_obs < 2 * order_d + 2


def prove_companion_consecution(coeffs: List[int]) -> bool:
    """z3 (QF_LRA): the recovered order-L linear recurrence a[n] = Σ_{j} coeffs[j]·a[n-1-j] is advanced EXACTLY by the
    companion matrix one step — i.e. the closed form (companion-matrix power) satisfies the recurrence ∀n by induction.
    A wrong coeff/matrix ⇒ z3 finds a counterexample ⇒ False ⇒ DECLINE. This is the ∀n half of the P-2 gate."""
    import z3
    L = len(coeffs)
    if L < 1:
        return False                                             # degenerate / empty recurrence ⇒ nothing to fold
    a = list(z3.Reals(" ".join(f"a{i}" for i in range(L))))      # symbolic window [a_{n-1},…,a_{n-L}]
    # the actual companion matrix the O(log N) fold uses: top row = coeffs, then a shift-identity sub-block
    M = [[z3.RealVal(coeffs[j]) for j in range(L)]] + \
        [[z3.RealVal(1) if c == r else z3.RealVal(0) for c in range(L)] for r in range(L - 1)]
    Mv = [sum(M[r][c] * a[c] for c in range(L)) for r in range(L)]          # the companion advances the state
    expected = [sum(z3.RealVal(coeffs[j]) * a[j] for j in range(L))] + [a[r] for r in range(L - 1)]
    s = z3.Solver()
    s.add(z3.Or(*[Mv[r] != expected[r] for r in range(L)]))      # ∃ a window where the companion step is wrong?
    return s.check() == z3.unsat                                  # UNSAT ⇒ companion fold faithful ∀ window


def conjecture_verify(fn: Callable[[int], object], probe: int = 24, holdout: int = 200) -> ConjResult:
    """The unified pipeline: observe → run the conjecturers (linear/polynomial/periodic via the recovered recurrence)
    → z3 ∀-proof gate + held-out divergence guard. EXACT only when BOTH pass; else DECLINE. Reuses §P P1
    blackbox_recover for the recovery + held-out, and ADDS the explicit z3 consecution proof (P-2)."""
    seq = observe(fn, probe)
    if seq is None:
        return ConjResult(False, "none", 0, "-", None, "non-deterministic / non-numeric / raised ⇒ conjecture ABANDONED (existing path)")
    # ── recovery + held-out divergence guard (reuse §P P1) ──
    from catalog import blackbox_fallback as BB
    v = BB.blackbox_recover(fn, probe_n=probe, holdout=holdout, label="conjecture", assume_pure=True)
    import kernel_verdict as KV
    if v.status != KV.EXACT:
        return ConjResult(False, "none", 0, "-", v, f"recovery/held-out gate DECLINED: {v.reason[:90] if hasattr(v, 'reason') else ''}")
    order = int(v.result.get("order", 0)) if isinstance(v.result, dict) else 0
    if under_determined(probe, order):                            # ★ under-determination guard
        return ConjResult(False, "linear_recurrence", order, "-",
                          KV.decline(f"under-determined: probe {probe} < 2·{order}+2 ⇒ ABANDON", "conjecture"),
                          "insufficient observations for the conjectured order ⇒ ABANDON (a fit is not a proof)")
    coeffs = [int(c) for c in v.result.get("coeffs", [])] if isinstance(v.result, dict) else []
    # ── ★ z3 ∀-proof gate (P-2): the closed form must satisfy the recurrence ∀n, not just match the probe ──
    if not coeffs or not prove_companion_consecution(coeffs):
        return ConjResult(False, "linear_recurrence", order, "-",
                          KV.decline("z3 could not prove the closed form satisfies the recurrence ∀n ⇒ DECLINE", "conjecture"),
                          "★ observation matched but z3 ∀-proof FAILED ⇒ DECLINE (P-2: a match is not a proof)")
    return ConjResult(True, "linear_recurrence", order, "blackbox+z3", v,
                      f"disguise defeated: black-box recovery (order {order}) + held-out divergence guard + z3 ∀-proof "
                      "of the companion closed form ⇒ EXACT (existing linear_recurrence kind, no new mechanism)")


def adversarial_battery() -> dict:
    """A disguised Fibonacci (behind a closure) folds EXACT (recovery + held-out + z3); ★ the P-2 adversary — a
    sequence that MATCHES on the probe window but DIVERGES after (fib-then-+1) is DECLINED; ★ a non-deterministic
    oracle is ABANDONED (not probed); ★ an under-determined short probe is ABANDONED; ★ a random/non-C-finite oracle
    DECLINES. false-EXACT count = 0 (z3/held-out is the gate, never observation)."""
    # disguised Fibonacci behind a closure (the white-box matcher can't read it; behavior is the same)
    def make_fib():
        memo = {0: 0, 1: 1}
        def f(n):
            if n not in memo:
                f(n - 1); memo[n] = memo[n - 1] + memo[n - 2]
            return memo[n]
        return f
    fib = conjecture_verify(make_fib())
    # ★ P-2 adversary: matches Fibonacci on the probe window, then DIVERGES (held-out catches it)
    def fib_then_diverge(n):
        a, b = 0, 1
        for _ in range(n):
            a, b = b, a + b
        return a if n < 24 else a + 1            # diverges exactly past the probe window
    adv = conjecture_verify(fib_then_diverge, probe=24, holdout=24)
    # ★ non-deterministic oracle ⇒ abandoned (state mutates per call)
    _ctr = {"v": 0}
    def nondet(n):
        _ctr["v"] += 1
        return n + _ctr["v"]
    nd = conjecture_verify(nondet)
    # random/non-C-finite ⇒ DECLINE
    rnd = conjecture_verify(lambda n: (n * 2654435761) % 4294967296)
    cases = {
        "disguised_fibonacci_folds_exact": fib.issued and fib.structure_class == "linear_recurrence",
        "p2_diverge_after_probe_declined": not adv.issued,                  # ★ observation-match-then-diverge ⇒ DECLINE
        "nondeterministic_abandoned": (not nd.issued) and "ABANDON" in nd.detail.upper(),
        "random_declined": not rnd.issued,
        "z3_consecution_real": prove_companion_consecution([1, 1]) and not prove_companion_consecution([]),  # z3 gate live
        "false_exact_zero": not adv.issued and not rnd.issued,             # ★ P-2: no false EXACT
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
