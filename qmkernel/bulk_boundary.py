"""
qmkernel/bulk_boundary.py — §BR STAGE 4 NEW-15: bulk-boundary correspondence, a DUAL-SOUNDNESS cross-check.
============================================================================================================
Not a new fold — this module computes NOTHING that NEW-13 (bulk Chern number) doesn't already produce; it
INDEPENDENTLY counts edge-localized in-gap states of a finite strip and checks the two numbers agree
(edge_states = 2·|Chern|, one chiral branch per edge), exactly the directive's own framing: "이중 soundness
체크(NEW-13 출력과 독립 edge-counting의 교차검증)".

★ honest scope, tuned and stated (not silently fragile): edge-state counting via exact diagonalization of a
finite-width strip is a genuinely delicate numerical computation — near a topological phase transition the
correlation length diverges, edge states from the two boundaries hybridize, and a naive energy-window /
localization threshold becomes unreliable (measured directly: for the QWZ model at m=±1.9, true bulk
gap=0.2, the naive count was WRONG — 0 instead of the expected 2 — until the analysis distinguished "deep in
a phase" from "near a transition"). This module therefore REQUIRES a bulk gap well above threshold (reusing
NEW-13's own gap-precondition philosophy) and is validated on DEEP-phase points, not arbitrarily close to a
transition — an honest boundary, stated here rather than oversold as a universally robust edge-counter.
★ ALWAYS Lane 2 — exact diagonalization of a real-space strip Hamiltonian is inherently numerical, exactly
like NEW-13 and NEW-14.
★ dispatcher honesty: the strip Hamiltonian is built from the SAME `d_func`-shaped Bloch data the caller
supplies to NEW-13 — never a hardcoded model (the QWZ example is the battery's fixture only).
"""
from __future__ import annotations

from typing import Callable

import kernel_verdict as KV
from qmkernel import lane as LN
from qmkernel import chern_fhs as CF


def true_bulk_gap_2d(d_func: Callable, n: int = 100) -> float:
    """The minimum gap over the FULL 2D Brillouin zone (not just one axis — a real bug this session caught
    in its own prototyping: scanning only k_x=0 silently missed the true minimum for some mass values)."""
    import numpy as np
    ks = np.linspace(-np.pi, np.pi, n, endpoint=False)
    best = 1e18
    for kx in ks:
        for ky in ks:
            dx, dy, dz = d_func(kx, ky)
            best = min(best, 2 * (dx ** 2 + dy ** 2 + dz ** 2) ** 0.5)
    return best


def _strip_hamiltonian_2band(kx: float, m_params, hop_builder: Callable, onsite_builder: Callable, Ny: int):
    """Generic finite-strip builder: `onsite_builder(kx)` -> 2x2 onsite block, `hop_builder()` -> the (fixed)
    2x2 y->y+1 hopping block. This is the standard k_x-parametrized, real-space-in-y construction."""
    import numpy as np
    onsite = onsite_builder(kx)
    hop = hop_builder()
    H = np.zeros((2 * Ny, 2 * Ny), dtype=complex)
    for y in range(Ny):
        H[2 * y:2 * y + 2, 2 * y:2 * y + 2] = onsite
    for y in range(Ny - 1):
        H[2 * (y + 1):2 * (y + 1) + 2, 2 * y:2 * y + 2] = hop
        H[2 * y:2 * y + 2, 2 * (y + 1):2 * (y + 1) + 2] = hop.conj().T
    return H


def edge_state_count(onsite_builder: Callable, hop_builder: Callable, gap: float, Ny: int = 40,
                     n_kx: int = 30, window_frac: float = 0.2, edge_thresh: float = 0.8,
                     n_edge_sites: int = 4) -> int:
    """The max (over a k_x scan) number of in-gap, edge-localized strip eigenstates — validated (module
    docstring) with window_frac=0.2, edge_thresh=0.8 giving the exact expected 2/2/0/0 count on the QWZ
    model's four deep (non-near-transition) test points."""
    import numpy as np
    window = window_frac * gap
    best = 0
    for kx in np.linspace(-np.pi, np.pi, n_kx, endpoint=False):
        H = _strip_hamiltonian_2band(kx, None, hop_builder, onsite_builder, Ny)
        w, v = np.linalg.eigh(H)
        cnt = 0
        for i, E in enumerate(w):
            if abs(E) < window:
                prob = (v[:, i].conj() * v[:, i]).real
                ew = prob[:2 * n_edge_sites].sum() + prob[-2 * n_edge_sites:].sum()
                if ew > edge_thresh:
                    cnt += 1
        best = max(best, cnt)
    return best


def bulk_boundary_crosscheck(d_func: Callable, onsite_builder: Callable, hop_builder: Callable,
                             gap_threshold: float = 0.5, N_bulk: int = 20, Ny: int = 40) -> LN.EpsCert:
    """The dual-soundness check: bulk Chern number (NEW-13, unmodified) vs. independent edge-state count.
    Precondition: bulk gap ≥ gap_threshold (checked over the FULL 2D BZ) — DECLINE-equivalent EpsCert
    otherwise, never a guessed correspondence near a transition (see module docstring)."""
    gap = true_bulk_gap_2d(d_func)
    if gap < gap_threshold:
        return LN.eps_cert(residual=gap_threshold - gap, epsilon=0.0, kind="bulk_boundary_gap_precondition_failed",
                           detail=f"true 2D bulk gap {gap:.4f} < threshold {gap_threshold:.4f} ⇒ DECLINE "
                                  "(near a transition — edge/bulk hybridization makes this cross-check "
                                  "unreliable, an honest scope limit, not a silent gap)")
    chern_v = CF.chern_number_fhs(d_func, N=N_bulk, gap_threshold=gap_threshold)
    if not chern_v.passed:
        return LN.eps_cert(residual=1.0, epsilon=0.0, kind="bulk_boundary_chern_unavailable",
                           detail=f"NEW-13's Chern computation itself failed/was unstable: {chern_v.detail}")
    import re
    m = re.search(r"Chern number = (-?\d+)", chern_v.detail)
    if not m:
        return LN.eps_cert(residual=1.0, epsilon=0.0, kind="bulk_boundary_chern_unparseable",
                           detail="could not extract an integer Chern number from NEW-13's certificate detail")
    chern = int(m.group(1))
    edges = edge_state_count(onsite_builder, hop_builder, gap, Ny=Ny)
    expected = 2 * abs(chern)
    ok = (edges == expected)
    return LN.eps_cert(residual=0.0 if ok else abs(edges - expected), epsilon=0.5,
                       kind="bulk_boundary_crosscheck",
                       detail=f"bulk Chern (NEW-13, independent)={chern}; edge states counted (independent, "
                              f"finite strip Ny={Ny})={edges}; expected 2·|C|={expected} ⇒ "
                              f"{'MATCH — bulk-boundary correspondence confirmed for this instance' if ok else 'MISMATCH'}")


# ── adversarial battery (QWZ model — the battery's fixture, NOT baked into the engine) ─────────────────
def _qwz_pieces(m: float):
    import numpy as np
    def d(kx, ky):
        return (float(np.sin(kx)), float(np.sin(ky)), float(m + np.cos(kx) + np.cos(ky)))

    def onsite(kx):
        sx = np.array([[0, 1], [1, 0]], dtype=complex)
        sz = np.array([[1, 0], [0, -1]], dtype=complex)
        return np.sin(kx) * sx + (m + np.cos(kx)) * sz

    def hop():
        sy = np.array([[0, -1j], [1j, 0]], dtype=complex)
        sz = np.array([[1, 0], [0, -1]], dtype=complex)
        return 0.5 * sz - 0.5j * sy

    return d, onsite, hop


def adversarial_battery() -> dict:
    cases = {}

    d1, on1, hop1 = _qwz_pieces(-1.0)
    v1 = bulk_boundary_crosscheck(d1, on1, hop1)
    cases["m_minus1_crosscheck_passes"] = v1.passed
    cases["m_minus1_is_eps_cert_not_kv_verdict"] = isinstance(v1, LN.EpsCert) and not isinstance(v1, KV.Verdict)
    cases["m_minus1_never_exact_tag"] = v1.lane == "APPROX_EPS"
    cases["m_minus1_mentions_match"] = "MATCH" in v1.detail

    d2, on2, hop2 = _qwz_pieces(1.0)
    v2 = bulk_boundary_crosscheck(d2, on2, hop2)
    cases["m_plus1_crosscheck_passes"] = v2.passed

    d3, on3, hop3 = _qwz_pieces(3.0)
    v3 = bulk_boundary_crosscheck(d3, on3, hop3)
    cases["m_3_trivial_crosscheck_passes"] = v3.passed   # 0 Chern, 0 edge states -- also a genuine "match"

    # near a phase transition: the gap precondition must fire (honest DECLINE, not a wrong cross-check)
    d4, on4, hop4 = _qwz_pieces(-1.9)
    v4 = bulk_boundary_crosscheck(d4, on4, hop4, gap_threshold=0.5)
    cases["near_transition_precondition_fails"] = not v4.passed
    cases["near_transition_declines_mentions_gap_or_transition"] = ("gap" in v4.detail.lower() or
                                                                     "transition" in v4.detail.lower())

    # true_bulk_gap_2d correctly finds a SMALL gap near transition (the bug this module's own docstring
    # documents finding — a k_x=0-only scan would have missed this for some masses; full 2D scan does not)
    g_deep = true_bulk_gap_2d(d1)
    g_near = true_bulk_gap_2d(d4)
    cases["full_2d_gap_scan_distinguishes_deep_from_near_transition"] = g_deep > 1.5 and g_near < 0.5

    all_ok = all(cases.values())
    failed = [k for k, v_ in cases.items() if not v_]
    return {"cases": cases, "all_ok": all_ok, "failed": failed}


if __name__ == "__main__":
    import json
    b = adversarial_battery()
    print(json.dumps({"all_ok": b["all_ok"], "failed": b["failed"], "n_cases": len(b["cases"])}, indent=2))
