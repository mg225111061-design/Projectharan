"""
CATALOG ENGINE — PHASE D gated kernels (DECLINE backbone, mechanism 12/14).
===========================================================================
The MDL 2-part-code kernel (a MEASURED incompressibility test) — the recoverable side of the §6 DECLINE backbone:
data with hidden structure COMPRESSES (EXACT code-length, proceed); data with no model beating the literal
DECLINEs (per-instance, honest — NOT a Kolmogorov-randomness proof, which is uncomputable). The Rice / turbulence
guards + the 15-entry proven-boundary list (PHASE A) complete the backbone.
"""
from __future__ import annotations

import kernel_router as KR
import kernel_verdict as KV
from catalog.decline_boundary import mdl_grade
from catalog.kernels_phaseB import _verify_transform


def _mdl_detect(data) -> bool:
    if isinstance(data, (bytes, bytearray)):
        return True
    if isinstance(data, (list, tuple)) and data and all(isinstance(v, (int, float)) for v in data):
        return True
    return isinstance(data, dict) and data.get("mdl") is True


def _mdl_run(data, **kw) -> KV.Verdict:
    return mdl_grade(data.get("data") if isinstance(data, dict) else data)


KR.register(KR.Kernel(
    num=105, name="mdl_incompressibility", group="catalog",
    contract="requires data-like input (bytes / numeric sequence / {mdl,data}); ensures an EXACT MDL 2-part code "
            "length when a model beats the literal (zlib = sound Kolmogorov-complexity upper bound), else DECLINE "
            "(no model beats the literal — per-instance, NOT a Kolmogorov-randomness claim); grade EXACT | DECLINE",
    detect=_mdl_detect, run=_mdl_run, status="VERIFIED"))
_verify_transform("D1.kolmogorov_incompressible", "mdl_incompressibility")
