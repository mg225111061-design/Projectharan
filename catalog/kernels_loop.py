"""
CATALOG ENGINE — §9 research→judge→build loop recoveries.
=========================================================
Each cycle JUDGEs where the engine declines, narrowly RESEARCHes a more precise instance of an EXISTING mechanism
(never a new one — the framework is closed), BUILDs a §7-gated kernel, and recovers a deferred transform.

Cycle 1 — mechanism 1 (diagonalize): Sylvester INERTIA (n₊,n₀,n₋), a complete invariant of a symmetric rational
matrix's congruence class, EXACT via exact eigenvalue signs. Recovers 16.spectral_svd_pca (was deferred).
"""
from __future__ import annotations

import kernel_router as KR
import kernel_verdict as KV
import sos_cert
from catalog.kernels_phaseB import _verify_transform

try:
    import sympy as _sp
    _MatrixType = _sp.MatrixBase
except Exception:  # noqa: BLE001
    _MatrixType = ()


def _inertia_detect(data) -> bool:
    if isinstance(data, _MatrixType):
        return True
    if isinstance(data, dict) and data.get("inertia") is True and "matrix" in data:
        return True
    return False


def _inertia_run(data, **kw) -> KV.Verdict:
    M = data["matrix"] if isinstance(data, dict) else data
    return sos_cert.inertia_grade(M)


KR.register(KR.Kernel(
    num=108, name="spectral_inertia", group="catalog",
    contract="requires a symmetric rational matrix; ensures its EXACT Sylvester inertia (n₊,n₀,n₋) — a complete "
            "congruence invariant (definiteness falls out) — via exact eigenvalue signs; non-symmetric → DECLINE; "
            "grade EXACT | DECLINE",
    detect=_inertia_detect, run=_inertia_run, status="VERIFIED"))
_verify_transform("16.spectral_svd_pca", "spectral_inertia")
