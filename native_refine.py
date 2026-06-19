"""
PHASE 4.S3 — native translation validation: per-compilation REFINEMENT (Alive2-style).
=======================================================================================
The native code the backend emits is checked, PER COMPILATION, to REFINE the verified spec semantics: it must
produce the spec's result wherever the spec is defined (bit-exact on the validated domain). A codegen that does
not refine is DECLINED (the safe path is kept). This is the native analogue of P2.S5 (optimizer UNTRUSTED) —
the compiler is UNTRUSTED, the machine validates every emit.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

import backend_llvm as BE


@dataclass
class RefineResult:
    verdict: str                # REFINES | DECLINE | BLOCKED
    speedup: float = 0.0
    detail: str = ""


def native_refines_spec(closed_form: str, spec_naive: Callable, check_ns: Optional[List[int]] = None) -> RefineResult:
    """Per-compilation refinement: the native emit of `closed_form` must be BIT-EXACT with the spec's naive
    reference on the checked domain. FOLDED_NATIVE ⇒ REFINES; a mismatch (wrong codegen / overflow) ⇒ DECLINE."""
    r = BE.fold_to_native(closed_form, spec_naive, check_ns=check_ns)
    if r.status == "BLOCKED":
        return RefineResult("BLOCKED", detail=r.detail)
    if r.status == "FOLDED_NATIVE":
        return RefineResult("REFINES", r.speedup, "native refines the spec on the validated domain (bit-exact)")
    return RefineResult("DECLINE", 0.0, f"native does NOT refine the spec — codegen DECLINED: {r.detail}")
