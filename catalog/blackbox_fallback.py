"""
§P P1 — BLACK-BOX FALLBACK: recover known structure from the OUTPUT SEQUENCE when white-box lifting is blinded by
REPRESENTATIONAL disguise. (Detector RECALL — NOT a new mechanism; routes to the existing `linear_recurrence` kind.)
================================================================================================================
Kimi proved by code execution that the SAME C-finite structure under 13 disguises (recursion, closure, object-state,
CPS, dead-code, mutual-recursion, conditional, call-chain, data-structure, dynamic-dispatch, …) ALL emit the identical
output sequence — the disguise changes the code's FORM, never its OUTPUT. So when the white-box lifter DECLINEs (it
reads syntax, which the disguise scrambles), we execute the function as a PURE ORACLE on n = 0,1,2,…, read the output
sequence, and recover the minimal linear recurrence with Berlekamp–Massey (reusing native_sequence). Hankel rank
corroborates the finite-dimensional state.

★ PRECISION IS UNCHANGED — the proposer widens, the certifier does not:
  • PURITY GUARD: probing is only valid if the function is a deterministic, side-effect-free function of its index.
    We prove this transitively (handles self-/mutual-recursion). A side-effecting / non-deterministic function (the
    distributed/async-state disguise) DECLINEs here and falls through — black-box cannot probe it (that needs P6).
  • DISPOSER (the exact gate): the recovered recurrence must predict a block of HELD-OUT terms — freshly computed by
    the oracle BEYOND the recovery window — EXACTLY. This catches the fit-valid-only-on-the-window adversary
    (Fibonacci-then-diverge), exactly the failure the repo's loop-collapse gate already guards. A recurrence that
    fits the probe but misses a held-out term ⇒ DECLINE. A recovered-but-unconfirmed candidate never folds.
  • The certificate kind is `linear_recurrence` (an EXISTING kind, ⑪/① class) — no 23rd kind is introduced.
"""
from __future__ import annotations

import inspect
from fractions import Fraction
from typing import Callable, Dict, Optional

import kernel_verdict as KV
from native_sequence import berlekamp_massey_Q, _verify_recurrence

_PROBE_N = 24          # terms the recovery sees
_HOLDOUT = 24          # terms it must predict but never saw (the disposer / divergence guard)
_MAX_ORDER = 50        # honest BM order cap (beyond this the probe cannot reach — DECLINE, never claim)


def blackbox_recover(fn: Callable[[int], object], probe_n: int = _PROBE_N, holdout: int = _HOLDOUT,
                     label: str = "blackbox", assume_pure: bool = False) -> KV.Verdict:
    """Core engine: probe a UNARY PURE oracle fn(0..probe_n−1), recover its minimal linear recurrence (BM over ℚ), and
    DISPOSE it by exact prediction of `holdout` terms the recovery never saw. EXACT(linear_recurrence) or DECLINE.
    `assume_pure` must be True — the caller is responsible for the purity proof (use blackbox_grade for the guarded
    entry); probing a side-effecting/non-deterministic function is unsound."""
    if not assume_pure:
        return KV.decline("blackbox: purity not established ⇒ cannot probe (side-effects defeat black-box recovery)", label)
    try:
        seq = [fn(i) for i in range(probe_n)]
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"blackbox: probe raised {type(e).__name__} ⇒ DECLINE", label)
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in seq):
        return KV.decline("blackbox: output is not a real-numeric sequence ⇒ not BM-recoverable here", label)
    if probe_n < 6:
        return KV.decline("blackbox: probe too short (<6) to estimate linear complexity", label)
    C, L = berlekamp_massey_Q(seq)
    if L > _MAX_ORDER:
        return KV.decline(f"blackbox: recovered order L={L} exceeds the honest probe cap {_MAX_ORDER} ⇒ DECLINE", label)
    if 2 * L > probe_n - 2:                                   # L ≈ n/2 — no compression ⇒ random / non-C-finite signature
        return KV.decline(f"blackbox: linear complexity L={L} ≈ n/2 (probe={probe_n}) — random/non-C-finite ⇒ DECLINE", label)
    if not _verify_recurrence(seq, C, L):
        return KV.decline(f"blackbox: recurrence (L={L}) fails run-forward on the probe ⇒ DECLINE", label)
    # ── DISPOSER: exact prediction of HELD-OUT terms the recovery never saw (the divergence / window-fit guard) ──
    try:
        extra = [fn(i) for i in range(probe_n, probe_n + holdout)]
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"blackbox: held-out probe raised {type(e).__name__} ⇒ DECLINE", label)
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in extra):
        return KV.decline("blackbox: held-out output not real-numeric ⇒ DECLINE", label)
    s = [Fraction(v) for v in (seq + extra)]
    for i in range(probe_n, len(s)):
        pred = -sum(C[j] * s[i - j] for j in range(1, L + 1))
        if pred != s[i]:
            return KV.decline(f"blackbox: recurrence predicts term {i} as {pred} but oracle gives {s[i]} — fit valid "
                              "only on the recovery window (diverge-after adversary) ⇒ DECLINE", label)
    coeffs = [str(-C[j]) for j in range(1, L + 1)]
    cert = KV.Cert(KV.EXACT, "linear_recurrence", passed=True,
                   check_cost=f"run-forward over {probe_n - L} probe terms + EXACT prediction of {holdout} held-out terms",
                   detail=f"black-box recovery: representational disguise defeated by output-sequence analysis; minimal "
                          f"order-L={L} linear recurrence s[i]=Σcⱼ·s[i−j], c={coeffs}; cross-validated on {holdout} "
                          "terms the recovery never saw (window-fit/divergence adversary excluded)")
    return KV.exact({"order": L, "coeffs": coeffs, "via": "blackbox"}, label,
                    f"black-box BM recovery (L={L}, probe={probe_n} + holdout={holdout})", cert)


def _all_defs(sources: Dict[str, str]) -> Dict[str, str]:
    """Expand to EVERY function definition, including NESTED ones (CPS / closure helpers), so the transitive purity
    proof can resolve a call to a locally-defined helper instead of treating it as an unknown external effect. Used
    ONLY for the purity proof; execution still runs the original (nested) sources, so closure context is preserved."""
    import ast
    out: Dict[str, str] = {}
    for src in sources.values():
        try:
            tree = ast.parse(src.strip())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                try:
                    out[node.name] = ast.unparse(node)
                except Exception:  # noqa: BLE001 — ast.unparse missing/failed; skip (purity stays conservative)
                    pass
    return out


def _prove_pure_transitive_ok(sources: Dict[str, str], target: str) -> tuple:
    """Purity guard for probing — transitive so self-/mutual-recursion AND nested CPS/closure helpers are allowed,
    while a clock/RNG/IO/global-mutation function (which black-box CANNOT validly probe) is excluded. accel.maximal."""
    from accel.maximal import prove_pure_transitive
    verdict = prove_pure_transitive(_all_defs(sources) or sources)
    if target not in verdict:
        return False, f"target {target} not analyzable"
    return verdict[target]


def blackbox_grade(sources: Dict[str, str], target: str, probe_n: int = _PROBE_N, holdout: int = _HOLDOUT,
                   label: str = "blackbox") -> KV.Verdict:
    """Guarded source-level entry. `sources` = {fn_name: source} (include every function the target calls, for
    self-/mutual-recursion); `target` = the unary function to probe. (1) PROVE the target transitively pure
    (side-effecting/non-deterministic ⇒ DECLINE — black-box invalid). (2) compile + probe + recover + dispose."""
    ok, why = _prove_pure_transitive_ok(sources, target)
    if not ok:
        return KV.decline(f"blackbox: target NOT proved pure ({why}) — side-effecting/non-deterministic functions "
                          "defeat black-box probing (the distributed/async disguise — see P6) ⇒ DECLINE", label)
    ns: Dict[str, object] = {}
    try:
        for src in sources.values():
            exec(compile(src.strip(), "<blackbox>", "exec"), ns, ns)   # shared ns ⇒ recursion/mutual-recursion resolves
    except Exception as e:  # noqa: BLE001
        return KV.decline(f"blackbox: cannot compile sources ({type(e).__name__}) ⇒ DECLINE", label)
    fn = ns.get(target)
    if not callable(fn):
        return KV.decline(f"blackbox: target {target} is not a callable after compilation ⇒ DECLINE", label)
    try:
        arity = len(inspect.signature(fn).parameters)
    except (ValueError, TypeError):
        arity = 1
    if arity != 1:
        return KV.decline(f"blackbox: target arity {arity} ≠ 1 — black-box probe is over a single index n ⇒ DECLINE", label)
    return blackbox_recover(fn, probe_n, holdout, label=label, assume_pure=True)


def hankel_state_dim(seq, max_rows: Optional[int] = None) -> int:
    """Corroborating finite-state-dimension estimate: the rank of the Hankel matrix of the sequence (exact over ℚ) =
    the dimension of the minimal linear state space. Used as a cross-check on the BM order (they must agree)."""
    s = [Fraction(v) for v in seq]
    n = len(s)
    r = (n // 2) if max_rows is None else min(max_rows, n // 2)
    if r < 1:
        return 0
    H = [[s[i + j] for j in range(n - r + 1)] for i in range(r)]   # r × (n−r+1) Hankel
    # exact ℚ Gaussian rank
    rows = [row[:] for row in H]
    rank = 0
    ncols = len(rows[0]) if rows else 0
    for c in range(ncols):
        piv = next((k for k in range(rank, len(rows)) if rows[k][c] != 0), None)
        if piv is None:
            continue
        rows[rank], rows[piv] = rows[piv], rows[rank]
        inv = rows[rank][c]
        rows[rank] = [v / inv for v in rows[rank]]
        for k in range(len(rows)):
            if k != rank and rows[k][c] != 0:
                f = rows[k][c]
                rows[k] = [a - f * b for a, b in zip(rows[k], rows[rank])]
        rank += 1
    return rank
