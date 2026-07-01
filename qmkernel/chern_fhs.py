"""
qmkernel/chern_fhs.py — §BR STAGE 4 NEW-13 (★ flagship of this stage): Fukui-Hatsugai-Suzuki Chern number.
============================================================================================================
The Chern number of a 2-band Bloch Hamiltonian's lower band, via the FHS lattice link-variable method:
discretize the Brillouin-zone torus into an N×N grid, build U(1) link variables from the lower eigenvector's
overlaps, sum the plaquette curvatures, divide by 2πi — the result is a topological integer.

★ precondition FIRST, no exceptions (§4 of the directive): the band gap is checked over the ENTIRE sampled
grid before anything else. A small gap makes lattice discretization risk a SPURIOUS non-quantized result near
a gap-closing (Dirac) point — verified directly: the QWZ model's gap goes to EXACTLY 0 at its phase-transition
masses (m=0, m=±2) and shrinks linearly nearby, confirmed by direct computation before this module was
written. Gap below the caller's threshold ⇒ DECLINE, never a guessed integer.

★ ALWAYS Lane 2 (qmkernel.lane.EpsCert), NEVER EXACT — stated explicitly, not a lane-detection accident: even
when the Bloch Hamiltonian's FORM is exact/symbolic (sin/cos of rational multiples of π, say), the FHS
procedure itself computes floating-point eigenvectors and a floating-point curvature sum at every grid point.
The Chern number's TRUE value is a topological integer, but THIS COMPUTATION reaching it is numerical — the
same discipline as everywhere else in §1: don't launder a numerically-obtained (even if conceptually exact)
integer into EXACT.
★ certificate — TWO parts, both required: (a) the raw curvature sum is within `int_tol` of its nearest
integer; (b) STABILITY: recomputing at DOUBLE the lattice resolution gives the SAME integer — a genuine
re-verification against lattice artifacts, not a rubber stamp on a single grid size.
★ m09 complete-invariant-classification recognition branch — the directive's own research already identifies
Chern number as a complete invariant instance; this is that recognition branch, not a new mechanism.
★ dispatcher honesty (§2 principle 3): the Hamiltonian is built from the CALLER-SUPPLIED `d_func`, never a
hardcoded model — the QWZ example below is the BATTERY's test fixture, not baked into the engine.
"""
from __future__ import annotations

from typing import Callable, Tuple

import kernel_verdict as KV
from qmkernel import lane as LN

DFunc = Callable[[float, float], Tuple[float, float, float]]


def _bloch_h(d_func: DFunc, kx: float, ky: float):
    import numpy as np
    dx, dy, dz = d_func(kx, ky)
    return np.array([[dz, dx - 1j * dy], [dx + 1j * dy, -dz]], dtype=complex)


def _lower_eigvec(Hk):
    import numpy as np
    w, v = np.linalg.eigh(Hk)
    return v[:, 0]


def _gap(Hk):
    import numpy as np
    w = np.linalg.eigvalsh(Hk)
    return float(w[1] - w[0])


def min_gap_over_grid(d_func: DFunc, N: int) -> float:
    """The precondition quantity: the smallest band gap sampled over the N×N BZ grid."""
    import numpy as np
    ks = np.linspace(-np.pi, np.pi, N, endpoint=False)
    return min(_gap(_bloch_h(d_func, kx, ky)) for kx in ks for ky in ks)


def _chern_raw(d_func: DFunc, N: int) -> float:
    """The FHS lattice sum, un-rounded (a float close to, but not asserted to equal, an integer)."""
    import numpy as np
    ks = np.linspace(-np.pi, np.pi, N, endpoint=False)
    u = [[None] * N for _ in range(N)]
    for i, kx in enumerate(ks):
        for j, ky in enumerate(ks):
            u[i][j] = _lower_eigvec(_bloch_h(d_func, kx, ky))
    total = 0.0
    for i in range(N):
        for j in range(N):
            ip, jp = (i + 1) % N, (j + 1) % N
            ux1 = np.vdot(u[i][j], u[ip][j]); ux1 /= abs(ux1)
            uy1 = np.vdot(u[ip][j], u[ip][jp]); uy1 /= abs(uy1)
            ux2 = np.vdot(u[i][jp], u[ip][jp]); ux2 /= abs(ux2)
            uy2 = np.vdot(u[i][j], u[i][jp]); uy2 /= abs(uy2)
            total += float(np.log(ux1 * uy1 / (ux2 * uy2)).imag)
    return total / (2 * np.pi)


def chern_number_fhs(d_func: DFunc, N: int = 20, gap_threshold: float = 0.05,
                     int_tol: float = 0.05) -> LN.EpsCert:
    """The top-level entry point. Returns a `LN.EpsCert` (never a KV.Verdict — this computation is ALWAYS
    numerical, see module docstring) whose `.passed` reflects BOTH the near-integer check and the
    2×-resolution stability check, and whose `.detail` states the resulting integer or the failure reason."""
    gap = min_gap_over_grid(d_func, N)
    if gap < gap_threshold:
        return LN.eps_cert(residual=gap_threshold - gap, epsilon=0.0, kind="chern_fhs_gap_precondition_failed",
                           detail=f"min gap over the N={N} grid is {gap:.4f} < threshold {gap_threshold:.4f} "
                                  "⇒ DECLINE-equivalent (a small gap risks spurious lattice-discretization "
                                  "non-quantization near a Dirac point) — reported as a FAILED EpsCert, not "
                                  "a guessed integer")
    raw = _chern_raw(d_func, N)
    nearest = round(raw)
    near_int_ok = abs(raw - nearest) <= int_tol

    gap2 = min_gap_over_grid(d_func, 2 * N)
    if gap2 < gap_threshold:
        return LN.eps_cert(residual=1.0, epsilon=int_tol, kind="chern_fhs_refined_grid_gap_failed",
                           detail=f"the 2×-resolution grid (N={2*N}) sampled a smaller gap ({gap2:.4f}) than "
                                  "the threshold — the original grid may have missed a near-degeneracy; DECLINE")
    raw2 = _chern_raw(d_func, 2 * N)
    nearest2 = round(raw2)
    stable = (nearest == nearest2)

    passed = near_int_ok and stable
    residual = abs(raw - nearest) if near_int_ok else abs(raw - nearest)
    detail = (f"N={N}: raw={raw:.5f}→{nearest} (|raw-int|={abs(raw-nearest):.2e} "
              f"{'≤' if near_int_ok else '>'} tol={int_tol:.2e}); N={2*N}: raw={raw2:.5f}→{nearest2} "
              f"({'STABLE — same integer' if stable else 'UNSTABLE — different integer, DECLINE-equivalent'}); "
              f"min_gap={gap:.4f} (≥ threshold {gap_threshold:.4f})")
    return LN.eps_cert(residual=residual if passed else max(residual, int_tol + 1), epsilon=int_tol,
                       kind="chern_fhs", detail=detail + (f"; Chern number = {nearest}" if passed else ""))


# ── adversarial battery (QWZ model — the battery's fixture, NOT baked into the engine) ─────────────────
def _qwz(m: float) -> DFunc:
    import numpy as np
    def d(kx, ky):
        return (float(np.sin(kx)), float(np.sin(ky)), float(m + np.cos(kx) + np.cos(ky)))
    return d


def adversarial_battery() -> dict:
    cases = {}

    # topological phase, m=-1: gap open (=2), Chern number nonzero integer, stable under refinement
    v1 = chern_number_fhs(_qwz(-1.0), N=16)
    cases["m_minus1_passes"] = v1.passed
    cases["m_minus1_is_eps_cert_not_kv_verdict"] = isinstance(v1, LN.EpsCert) and not isinstance(v1, KV.Verdict)
    cases["m_minus1_never_exact_tag"] = v1.lane == "APPROX_EPS"
    cases["m_minus1_nonzero_chern"] = "Chern number = 0" not in v1.detail and "Chern number" in v1.detail

    # topological phase, m=+1: opposite sign from m=-1 (both nonzero, different integers)
    v2 = chern_number_fhs(_qwz(1.0), N=16)
    cases["m_plus1_passes"] = v2.passed
    import re
    c1 = int(re.search(r"Chern number = (-?\d+)", v1.detail).group(1))
    c2 = int(re.search(r"Chern number = (-?\d+)", v2.detail).group(1))
    cases["m_minus1_and_m_plus1_have_opposite_sign"] = (c1 == -c2 and c1 != 0)

    # trivial phase, m=3 (|m|>2): gap open, Chern number exactly 0
    v3 = chern_number_fhs(_qwz(3.0), N=16)
    cases["m_3_trivial_passes"] = v3.passed
    cases["m_3_trivial_chern_is_zero"] = "Chern number = 0" in v3.detail

    # gap-CLOSING point m=0 exactly -> the precondition must fire (failed EpsCert, no guessed integer)
    v4 = chern_number_fhs(_qwz(0.0), N=16, gap_threshold=0.05)
    cases["m_0_gap_closing_precondition_fails"] = not v4.passed
    cases["m_0_declines_mentions_gap"] = "gap" in v4.detail.lower()

    # gap-CLOSING point m=2 exactly -> same precondition guard, different transition
    v5 = chern_number_fhs(_qwz(2.0), N=16, gap_threshold=0.05)
    cases["m_2_gap_closing_precondition_fails"] = not v5.passed

    # a SMALL-but-nonzero gap case just off the transition still passes (precondition correctly permissive
    # when the gap genuinely IS large enough, not overly conservative)
    v6 = chern_number_fhs(_qwz(-1.5), N=16, gap_threshold=0.05)
    cases["near_transition_but_open_gap_passes"] = v6.passed

    all_ok = all(cases.values())
    failed = [k for k, v_ in cases.items() if not v_]
    return {"cases": cases, "all_ok": all_ok, "failed": failed}


if __name__ == "__main__":
    import json
    b = adversarial_battery()
    print(json.dumps({"all_ok": b["all_ok"], "failed": b["failed"], "n_cases": len(b["cases"])}, indent=2))
