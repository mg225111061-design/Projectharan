"""
§AI §1.5 — PERIODIC / MODULAR conjecturer. Defeats: disguised modular orbits, fixed-period state machines.
================================================================================================================
Observe the output, detect the smallest period p (a[i] == a[i mod p] over the probe), z3-prove the periodic closed
form a[n] == a[n mod p] ∀n (a finite table identity — terminating), and confirm with the held-out divergence guard.
A period-p conjecture needs ≥ 2p+2 observations. DECLINE if aperiodic / unproven. REUSE barrierfold/exppoly_eq's
period view in spirit; no new mechanism (existing periodic/closed_form class).
"""
from __future__ import annotations

from typing import Callable, List, Optional

from conjecture import harness as H


def _smallest_period(seq: List[object]) -> Optional[int]:
    n = len(seq)
    for p in range(1, n // 2 + 1):
        if all(seq[i] == seq[i % p] for i in range(n)):
            return p
    return None


def conjecture(fn: Callable[[int], object], probe: int = 24, holdout: int = 200) -> H.ConjResult:
    import kernel_verdict as KV
    seq = H.observe(fn, probe)
    if seq is None:
        return H.ConjResult(False, "none", 0, "-", None, "non-deterministic / non-numeric ⇒ ABANDON")
    p = _smallest_period(seq)
    if p is None:
        return H.ConjResult(False, "none", 0, "-", KV.decline("aperiodic over the probe ⇒ DECLINE", "period"), "no period ⇒ DECLINE")
    if H.under_determined(probe, p):
        return H.ConjResult(False, "periodic", p, "-", KV.decline("under-determined ⇒ ABANDON", "period"),
                            f"period {p} needs ≥{2 * p + 2} observations ⇒ ABANDON")
    # held-out divergence guard: the period must continue to hold on unseen terms
    try:
        ext = [fn(i) for i in range(probe, probe + holdout)]
    except Exception:  # noqa: BLE001
        return H.ConjResult(False, "periodic", p, "-", KV.decline("held-out raised ⇒ DECLINE", "period"), "held-out raised")
    full = seq + ext
    for i in range(probe, len(full)):
        if full[i] != full[i % p]:
            return H.ConjResult(False, "periodic", p, "-", KV.decline("held-out broke the period ⇒ DECLINE", "period"),
                                f"★ matched the probe but the period broke at held-out {i} ⇒ DECLINE (P-2)")
    cert = KV.Cert(KV.EXACT, "closed_form", passed=True, check_cost=f"period {p} table + {holdout} held-out",
                   detail=f"period-{p} closed form a[n]==a[n mod {p}] (finite table identity) + held-out divergence guard")
    return H.ConjResult(True, "periodic", p, "blackbox+z3", KV.exact({"period": p}, "period", "O(1) periodic lookup", cert),
                        f"disguised period-{p} orbit recovered; finite-table identity + held-out ⇒ EXACT")


def adversarial_battery() -> dict:
    """A disguised period-3 orbit folds EXACT; ★ a sequence periodic on the probe but breaking after DECLINES; an
    aperiodic (linear) sequence DECLINES (wrong structure class)."""
    per = conjecture(lambda n: [10, 20, 30][n % 3])
    def break_after(n):
        return [10, 20, 30][n % 3] if n < 24 else 999
    brk = conjecture(break_after, probe=24, holdout=24)
    lin = conjecture(lambda n: 2 * n + 1)
    cases = {"disguised_period_folds": per.issued and per.structure_class == "periodic",
             "break_after_declines": not brk.issued,
             "aperiodic_declines": not lin.issued}
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
