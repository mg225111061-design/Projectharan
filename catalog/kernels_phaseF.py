"""
CATALOG ENGINE — PHASE F gated kernels (domain transforms reusing mature [이미 있음] modules).
=============================================================================================
Thin §7-gated kernels delegating to existing, already-gical modules (reinforce + register, never reimplement,
§1.2): Buckingham-Π (mechanism 9, `mathmode.buckingham`) and Noether energy conservation (mechanism 5,
`mathmode.lagrangian`). Both return a graded KV.Verdict directly.
"""
from __future__ import annotations

import kernel_router as KR
import kernel_verdict as KV
from catalog.kernels_phaseB import _verify_transform


# ── Buckingham-Π (mechanism 9 / symmetry primitive) — dimensionless-group normal form ────────────────
def _bpi_detect(data) -> bool:
    # a quantities dict: name → {dimension-symbol: integer exponent}
    return (isinstance(data, dict) and bool(data)
            and all(isinstance(v, dict) and all(isinstance(e, int) for e in v.values()) for v in data.values()))


def _bpi_run(data, **kw) -> KV.Verdict:
    import mathmode.buckingham as B
    return B.buckingham_pi(data)


KR.register(KR.Kernel(
    num=106, name="buckingham_pi", group="catalog",
    contract="requires physical quantities with dimension exponents; ensures the dimensionless Π-group basis "
            "(null space of the dimension matrix), machine-checkable; grade EXACT",
    detect=_bpi_detect, run=_bpi_run, status="VERIFIED"))
_verify_transform("16.buckingham_pi", "buckingham_pi")


# ── Noether / energy conservation (mechanism 5) — conserved quantity with dI/dt≡0 ────────────────────
def _noether_detect(data) -> bool:
    return isinstance(data, dict) and data.get("noether") is True and "L" in data and "q" in data and "t" in data


def _noether_run(data, **kw) -> KV.Verdict:
    import mathmode.lagrangian as L
    return L.energy_conservation(data["L"], data["q"], data["t"])


KR.register(KR.Kernel(
    num=107, name="noether_energy", group="catalog",
    contract="requires a time-translation-invariant Lagrangian L(q,q̇,t); ensures the conserved energy/Hamiltonian "
            "with a machine-checked dH/dt≡0 (Euler–Lagrange on shell); grade EXACT",
    detect=_noether_detect, run=_noether_run, status="VERIFIED"))
_verify_transform("16.noether", "noether_energy")
