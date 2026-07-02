"""
§AY QFT-1 — transfer-matrix path sum tr(Tᴺ).
================================================================================================================
A weighted path sum Z_N = Σ_paths ∏ W(s_i,s_{i+1}) = tr(Tᴺ) with T_{ab}=W(a,b) (1D Ising, HMM forward, DP-on-paths).
The scalar sequence Z_N = tr(Tᴺ) = Σ λ_iᴺ is C-finite (it satisfies T's characteristic recurrence) and tr(Tᴺ)
evaluates in O(q³·log N) by power-by-squaring (REUSE cfinite._matpow) versus O(N·q²) forward DP. The fold of the
Z-sequence REUSES QLA-1 (krylov.fold_moment_sequence — BM + companion held-out replay).

★ ∀-N = the transfer-matrix theorem (tr(Tᴺ)≡path sum, by construction) + companion held-out replay (§0-b). A
position-DEPENDENT kernel (W=W_i ⇒ no single T, only ∏T_i) ⇒ B-axis DECLINE. Float weights ⇒ DECLINE.
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Sequence

import cfinite
import kernel_verdict as KV

from . import _la, krylov


def _trace_pow(T, N):
    P = cfinite._matpow(T, N)
    return sum((P[i][i] for i in range(len(T))), Fraction(0))


def transfer_matrix_fold(T: Sequence[Sequence]) -> KV.Verdict:
    """Fold a path-sum / forward-DP governed by a single transfer matrix T: Z_N=tr(Tᴺ) is C-finite and evaluates in
    O(q³·log N). EXACT (integer/rational T) gated by held-out replay; float ⇒ DECLINE."""
    try:
        Tf = _la.fmat(T)
    except _la.NonExact as e:
        return KV.decline(f"transfer_matrix: {e} ⇒ DECLINE (no float-EXACT)", "transfer_matrix")
    q = len(Tf)
    if q == 0 or any(len(r) != q for r in Tf):
        return KV.decline("transfer_matrix: need a square transfer matrix", "transfer_matrix")
    seq = [_trace_pow(Tf, N) for N in range(2 * q + 12)]       # Z_N = tr(Tᴺ)
    v = krylov.fold_moment_sequence(seq)                       # REUSE QLA-1: BM + companion held-out replay
    if v.status != KV.EXACT:
        return KV.decline("transfer_matrix: tr(Tᴺ) sequence has no short recurrence / fails replay ⇒ DECLINE",
                          "transfer_matrix")
    cert = KV.Cert(KV.EXACT, "transfer_matrix_trace", passed=True, check_cost="C-finite BM + companion held-out replay",
                   detail=f"Z_N=tr(Tᴺ) is C-finite order {v.result['order']} (=Σλ_iᴺ); tr(Tᴺ) by power-by-squaring "
                          f"O(q³·log N); held-out replay ✓ (∀-N by the transfer-matrix theorem)")
    return KV.exact({"order": v.result["order"], "q": q, "closed_form": "tr(T^N) via O(q³·log N) matpow"},
                    "transfer_matrix", f"O(q³·log N) (q={q})", cert,
                    reason="Axis-A: path-sum/forward-DP recognized as tr(Tᴺ); Axis-B O(N·q²)→O(q³·log N), crossover "
                           "when log N < N/q")


def position_dependent_decline(T_list: Sequence[Sequence[Sequence]]) -> KV.Verdict:
    """A position-dependent kernel W=W_i has no single transfer matrix — only the ordered product ∏T_i (O(N·q²),
    no speedup). Honest DECLINE on the B-axis (the structure is recognized but offers no fold)."""
    return KV.decline(f"transfer_matrix: position-dependent kernel ({len(T_list)} distinct T_i) ⇒ no single T ⇒ "
                      f"only ∏T_i (O(N·q²), gain 0) ⇒ B-axis DECLINE", "transfer_matrix")


def adversarial_battery() -> dict:
    """★ EXACT: a 2-state and a 3-state transfer matrix fold (Z_N=tr(Tᴺ) C-finite, held-out replay ✓). ★★ DECLINE:
    a position-dependent kernel (no single T) and a float matrix DECLINE."""
    t2 = transfer_matrix_fold([[1, 1], [1, 0]])               # Fibonacci-type: tr(Tᴺ)=Lucas numbers
    t2_ok = t2.status == KV.EXACT
    t3 = transfer_matrix_fold([[2, 1, 0], [1, 1, 1], [0, 1, 2]])
    t3_ok = t3.status == KV.EXACT
    posdep = position_dependent_decline([[[1, 1], [0, 1]], [[1, 0], [1, 1]]])
    posdep_declines = posdep.status == KV.DECLINE
    flt = transfer_matrix_fold([[1.0, 0.5], [0.5, 1.0]])
    flt_declines = flt.status == KV.DECLINE
    cases = {"transfer2_exact": t2_ok, "transfer3_exact": t3_ok, "position_dependent_declines": posdep_declines,
             "float_declines": flt_declines}
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, x in cases.items() if not x]}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2))
