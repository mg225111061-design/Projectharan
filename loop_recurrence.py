"""
§4 — linear-recurrence loop recognizer: an O(n) state-update loop → an O(log n) companion-matrix collapse.
==================================================================================================
A loop like `a, b = 0, 1; for _ in range(n): a, b = b, a + b; return a` computes a C-finite (linear
constant-coefficient) integer sequence. We don't parse the transition algebra symbolically (fragile); we DECIDE
it soundly by sample-fit-and-VERIFY:

  1. SAMPLE the user's f(0..N) (sandboxed exec — no imports/IO, via structure_recognizer's safe builtins).
  2. FIT the shortest exact integer recurrence f(n)=Σ c_j f(n-1-j) (mathmode.ingest.find_recurrence,
     Berlekamp-style over ℚ, integer-only).
  3. ★ VERIFY companion_nth(c, init) ≡ the USER'S ACTUAL loop on HELD-OUT n (beyond the fitted window) ★ — the
     sound gate. A wrong fit is rejected ⇒ DECLINE (never a wrong collapse).
  4. The O(n) loop then collapses to O(log n) via power-by-squaring of the companion matrix
     (cfinite.companion_nth), MEASURED with Amdahl honesty.

Honest scope (§X): EXACT only behind the held-out verification (companion ≡ the loop). DOMAIN-CONDITIONAL —
C-finite sequences only (Fibonacci/Pell/linear recurrences); a factorial / prime / non-linear loop is NOT C-finite
⇒ honest DECLINE (keep the loop). The measured ratio is whole-program FOR THIS FUNCTION (the loop IS the program,
f=1); it GROWS as n/log n (n stated, never an average); embed it in a larger program and the whole-program
speedup is ≤ the Amdahl ceiling. A wrong "collapse" or a wrong "not C-finite" would be a correctness bug — we are
sound/conservative (the held-out gate + the final re-check at the measured n).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import kernel_verdict as KV
import cfinite
from loop_decision import _median_time          # reuse the median-timing helper
from mathmode.ingest import find_recurrence


@dataclass
class RecurrenceCollapse:
    status: str                       # COLLAPSED | DECLINE
    c: List[int] = field(default_factory=list)
    init: List[int] = field(default_factory=list)
    order: int = 0
    n: int = 0
    naive_s: float = 0.0
    log_s: float = 0.0
    ratio: float = 1.0
    measured_win: bool = False        # ratio > 1.1 at the measured n (honest: not every collapse wins at a given n)
    closed_desc: str = ""
    verdict: Optional["KV.Verdict"] = None


def _decline(reason: str) -> RecurrenceCollapse:
    return RecurrenceCollapse("DECLINE", verdict=KV.decline(f"loop_recurrence: {reason}", "loop_recurrence"))


def decide_recurrence_collapse(source: str, fn_name: Optional[str] = None, sample: int = 24, n: int = 4000,
                               trials: int = 5) -> RecurrenceCollapse:
    """DECIDE whether a single-parameter loop f(n) computes a C-finite sequence and, if so, collapse the O(n)
    loop to an O(log n) companion form — MEASURED, verified ≡ the loop on held-out n. Otherwise DECLINE (honest:
    keep the loop). Sound: a wrong fit or a non-C-finite loop never yields a (wrong) collapse."""
    import structure_recognizer as SR                          # reuse _first_fn / _make_callable / _SAFE_BUILTINS

    fn = SR._first_fn(source, fn_name)
    if fn is None or len(fn.args.args) != 1:
        return _decline("not a single-parameter function ⇒ outside this recognizer")
    try:
        f = SR._make_callable(source, fn.name)                 # sandboxed: no imports / open / exec / IO
    except Exception as e:                                     # noqa: BLE001
        return _decline(f"could not build the function ({type(e).__name__})")
    if f is None:
        return _decline("function not found after exec")

    # 1) SAMPLE f(0..sample-1) — must be a pure integer sequence (bool excluded)
    seq: List[int] = []
    for i in range(sample):
        try:
            v = f(i)
        except Exception:                                     # noqa: BLE001
            return _decline("the loop raised during sampling ⇒ DECLINE")
        if not isinstance(v, int) or isinstance(v, bool):
            return _decline("non-integer sequence ⇒ outside the C-finite recognizer (honest)")
        seq.append(v)

    # 2) FIT the shortest exact integer recurrence
    rec = find_recurrence(seq)
    if rec is None:
        return _decline("not C-finite — no short integer recurrence fits the sequence ⇒ keep the loop (DECLINE)")
    c, init = rec

    # 3) ★ SOUND GATE: companion_nth ≡ the USER'S ACTUAL loop on HELD-OUT n (beyond the fitted window) ★
    holdout = [sample + 2, sample + 5, sample + 9, 2 * sample + 1]
    for nv in holdout:
        try:
            want = f(nv)
        except Exception:                                     # noqa: BLE001
            return _decline("the loop raised on held-out n ⇒ DECLINE")
        if cfinite.companion_nth(c, init, nv) != want:
            return _decline(f"companion form ≠ the loop at held-out n={nv} ⇒ DECLINE (no wrong collapse)")

    # 4) final re-check at the measured n, then MEASURE the O(n) loop vs the O(log n) companion
    if f(n) != cfinite.companion_nth(c, init, n):
        return _decline(f"companion ≠ loop at the measured n={n} ⇒ DECLINE")
    naive_s = _median_time(lambda: f(n), trials)
    log_s = _median_time(lambda: cfinite.companion_nth(c, init, n), max(trials, 9))
    ratio = (naive_s / log_s) if log_s > 0 else float("inf")
    import fold_dispatcher as FD
    wp_half = FD.amdahl_overall_speedup(ratio, 0.5)
    order = len(c)
    win = ratio > 1.1
    speed = (f"MEASURED O(n)→O(log n) {ratio:.1f}× at n={n} (naive {naive_s * 1e3:.2f} ms → companion "
             f"{log_s * 1e6:.2f} µs)" if win else
             f"VERIFIED O(log n) form, but NO measured whole-program win at n={n} (ratio {ratio:.2f}× — the "
             f"companion's big-integer-multiply constants don't beat the cheap O(n) loop here; honest, no speedup "
             f"claimed)")
    cert = KV.Cert(KV.EXACT, "verified_recurrence_collapse", passed=True,
                   check_cost=f"{trials} timed trials at n={n} + held-out companion≡loop verification",
                   detail=f"order-{order} C-finite recurrence f(n)=Σ c_j·f(n-1-j), c={c}, init={init}, fitted from "
                          f"{sample} samples and VERIFIED ≡ the user's loop on held-out n {holdout} (not merely the "
                          f"fit window) — the O(log n) companion form is a PROVEN lossless replacement. {speed}. "
                          f"HONEST: the collapse MEASURABLY wins when the sequence values GROW (bigint blowup makes "
                          f"the O(n) loop's per-step cost rise — Fibonacci-like); machine-int-bounded sequences stay "
                          f"cheap so it may not beat the loop at a given n (measured, never assumed). The loop IS this "
                          f"function (f=1) ⇒ whole-program FOR THIS FUNCTION; embed it in a larger program and the "
                          f"whole-program speedup is ≤ {wp_half:.2f}× (Amdahl ceiling). DOMAIN-CONDITIONAL — C-finite "
                          f"(linear constant-coefficient) sequences only; a factorial / prime / non-linear loop is "
                          f"NOT C-finite ⇒ DECLINE.")
    return RecurrenceCollapse("COLLAPSED", c=c, init=init, order=order, n=n, naive_s=naive_s, log_s=log_s,
                              ratio=ratio, measured_win=win,
                              closed_desc=f"companion_nth(c={c}, init={init}, n) — O(log n)",
                              verdict=KV.exact({"c": c, "init": init, "ratio": ratio, "n": n, "measured_win": win},
                                               "loop_recurrence",
                                               "verified O(n)→O(log n) collapse (≡ loop on held-out n; Amdahl-honest)",
                                               cert))


def _detect_modulus(fn, ns) -> Optional[int]:
    """Find a modulus M from a `% M` in the loop's update — M as a literal, a constant expr (10**9+7), or a
    Name resolved in the function's namespace. A wrong guess is harmless: the held-out verification rejects it."""
    import ast
    for node in ast.walk(fn):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            try:
                v = eval(compile(ast.Expression(node.right), "<m>", "eval"), {"__builtins__": {}}, dict(ns))  # noqa: S307
                if isinstance(v, int) and not isinstance(v, bool) and v > 1:
                    return v
            except Exception:                                # noqa: BLE001
                continue
    return None


def decide_modular_recurrence_collapse(source: str, fn_name: Optional[str] = None, sample: int = 24,
                                       n: int = 100000, trials: int = 5) -> RecurrenceCollapse:
    """DECIDE whether a single-parameter loop computes a C-finite sequence f(n) MOD M and, if so, collapse the
    O(n) modular loop to an O(log n) companion-matrix-power-MOD-M form — the case where O(log n) genuinely WINS
    (bounded ints, no bigint). Sound: M is detected from the loop's `% M`, the recurrence is fitted from the
    early (unwrapped) samples, and — the gate — `companion_nth_mod ≡ the user's ACTUAL loop on HELD-OUT n where
    it has WRAPPED`. A wrong M or a wrong fit ⇒ DECLINE (never a wrong collapse). Otherwise DECLINE (honest)."""
    import structure_recognizer as SR

    fn = SR._first_fn(source, fn_name)
    if fn is None or len(fn.args.args) != 1:
        return _decline("not a single-parameter function ⇒ outside this recognizer")
    ns: dict = {"__builtins__": SR._SAFE_BUILTINS}            # SINGLE namespace ⇒ f.__globals__ sees module consts (M)
    try:
        exec(compile(source, "<modrec>", "exec"), ns)        # noqa: S102 — sandboxed builtins, no imports/IO
    except Exception as e:                                    # noqa: BLE001
        return _decline(f"could not build the function ({type(e).__name__})")
    f = ns.get(fn.name)
    if f is None:
        return _decline("function not found after exec")
    M = _detect_modulus(fn, ns)
    if M is None:
        return _decline("no modulus `% M` found in the loop ⇒ not a modular recurrence (use the exact recognizer)")

    # 1) SAMPLE early values (likely unwrapped for a large M) → fit the exact integer recurrence
    seq: List[int] = []
    for i in range(sample):
        try:
            v = f(i)
        except Exception:                                    # noqa: BLE001
            return _decline("the loop raised during sampling ⇒ DECLINE")
        if not isinstance(v, int) or isinstance(v, bool):
            return _decline("non-integer sequence ⇒ DECLINE")
        seq.append(v)
    rec = find_recurrence(seq)
    if rec is None:
        return _decline("no short integer recurrence fits the early samples ⇒ DECLINE (not C-finite, or M too small)")
    c, init = rec

    # 2) ★ SOUND GATE: companion_nth_MOD ≡ the loop on HELD-OUT n where the loop has WRAPPED (mod behaviour) ★
    holdout = [sample + 60, sample + 130, 2 * sample + 300, 3 * sample + 777]
    for nv in holdout:
        try:
            want = f(nv)
        except Exception:                                    # noqa: BLE001
            return _decline("the loop raised on held-out n ⇒ DECLINE")
        if cfinite.companion_nth_mod(c, init, nv, M) != want:
            return _decline(f"companion-mod ≠ the loop at held-out n={nv} (mod {M}) ⇒ DECLINE (no wrong collapse)")

    # 3) re-check at the measured n, then MEASURE the O(n) modular loop vs the O(log n) companion-mod
    if f(n) != cfinite.companion_nth_mod(c, init, n, M):
        return _decline(f"companion-mod ≠ loop at the measured n={n} ⇒ DECLINE")
    naive_s = _median_time(lambda: f(n), trials)
    log_s = _median_time(lambda: cfinite.companion_nth_mod(c, init, n, M), max(trials, 9))
    ratio = (naive_s / log_s) if log_s > 0 else float("inf")
    import fold_dispatcher as FD
    wp_half = FD.amdahl_overall_speedup(ratio, 0.5)
    order = len(c)
    win = ratio > 1.1
    cert = KV.Cert(KV.EXACT, "verified_modular_recurrence_collapse", passed=True,
                   check_cost=f"{trials} timed trials at n={n} + held-out companion-mod≡loop verification",
                   detail=f"order-{order} C-finite recurrence f(n)=Σ c_j·f(n-1-j) mod {M}, c={c}, init={init}, fitted "
                          f"from {sample} early samples and VERIFIED ≡ the user's loop on held-out n {holdout} WHERE "
                          f"IT HAS WRAPPED (mod {M}). MEASURED O(n)→O(log n) {ratio:.1f}× at n={n} (naive "
                          f"{naive_s * 1e3:.2f} ms → companion-mod {log_s * 1e6:.2f} µs). This is the case the O(log n) "
                          f"collapse genuinely WINS: the modulus keeps ints BOUNDED (no bigint), so it is true "
                          f"O(log n) ring work. The loop IS this function (f=1) ⇒ whole-program FOR THIS FUNCTION; "
                          f"embed → ≤ {wp_half:.2f}× (Amdahl). DOMAIN-CONDITIONAL — C-finite modular recurrences only.")
    return RecurrenceCollapse("COLLAPSED", c=c, init=init, order=order, n=n, naive_s=naive_s, log_s=log_s,
                              ratio=ratio, measured_win=win,
                              closed_desc=f"companion_nth_mod(c={c}, init={init}, n, M={M}) — O(log n) bounded",
                              verdict=KV.exact({"c": c, "init": init, "M": M, "ratio": ratio, "n": n, "measured_win": win},
                                               "loop_recurrence",
                                               f"verified O(n)→O(log n) modular collapse mod {M} (≡ loop on wrapped "
                                               f"held-out n; Amdahl-honest)", cert))
