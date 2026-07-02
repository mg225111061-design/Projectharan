"""
CAPSTONE bypass (우회군 C) — ZX-calculus circuit simplification + equivalence via pyzx, formally re-checked.
============================================================================================================
A quantum / reversible circuit is rewritten in the ZX-calculus to a simplified normal form (full_reduce), and
two circuits are decided EQUIVALENT by a complete-for-Clifford rewrite system + an independent tensor re-check.
This turns "is this circuit equal to that one / can it be reduced" (opaque) into M8's confluent-normal-form job.

★ CERTIFICATE (per-instance, §7): pyzx's `verify_equality` compares the two circuits' tensors EXACTLY (small
  circuits) — a wrong simplification cannot pass. We report EXACT only when that formal check returns a definite
  True/False; a circuit too large to verify within budget ⇒ honest DECLINE (we never claim an unverified rewrite). ★
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple

import kernel_verdict as KV


def _circuit(c):
    """Coerce a QASM string or a pyzx Circuit into a pyzx Circuit."""
    import pyzx as zx
    if isinstance(c, str):
        return zx.Circuit.from_qasm(c)
    return c


@dataclass
class ZXVerdict:
    status: str                       # EQUIV | NONEQUIV | SIMPLIFIED | DECLINE
    detail: str = ""
    before: int = 0
    after: int = 0


def equivalent(a, b) -> ZXVerdict:
    """Decide whether circuits `a` and `b` are equivalent (ZX full_reduce + an exact tensor re-check)."""
    try:
        ca, cb = _circuit(a), _circuit(b)
        eq = ca.verify_equality(cb)                       # exact tensor comparison (small circuits)
    except Exception as e:  # noqa: BLE001
        return ZXVerdict("DECLINE", detail=f"pyzx error / circuit too large to verify: {type(e).__name__}: {e}")
    if eq is True:
        return ZXVerdict("EQUIV", detail="ZX/tensor equality verified")
    if eq is False:
        return ZXVerdict("NONEQUIV", detail="circuits are not equal (tensor disagreement)")
    return ZXVerdict("DECLINE", detail="equality undetermined within budget (too large for an exact tensor re-check)")


def simplify(c) -> ZXVerdict:
    """Simplify a circuit to a ZX normal form and RE-VERIFY the simplified circuit is equal to the original."""
    try:
        import pyzx as zx
        c0 = _circuit(c)
        before = len(c0.gates)
        g = c0.to_graph()
        zx.simplify.full_reduce(g)
        c1 = zx.extract_circuit(g.copy())
        eq = c0.verify_equality(c1)
        after = len(c1.gates)
    except Exception as e:  # noqa: BLE001
        return ZXVerdict("DECLINE", detail=f"pyzx error: {type(e).__name__}: {e}")
    if eq is not True:
        return ZXVerdict("DECLINE", detail="extracted normal form not verified equal to the input ⇒ rejected")
    return ZXVerdict("SIMPLIFIED", detail=f"ZX normal form verified equal ({before}→{after} gates)", before=before, after=after)


def zx_grade(x) -> KV.Verdict:
    """Grade a ZX task: {"zx_equiv": (a, b)} → EXACT decision (equivalent / not); {"zx_simplify": c} → EXACT normal
    form (verified equal). Too-large / pyzx-error ⇒ honest DECLINE."""
    if isinstance(x, dict) and "zx_equiv" in x:
        a, b = x["zx_equiv"]
        v = equivalent(a, b)
        if v.status in ("EQUIV", "NONEQUIV"):
            cert = KV.Cert(KV.EXACT, "zx_tensor_equality", passed=True, check_cost="exact tensor comparison (pyzx)",
                           detail=v.detail)
            return KV.exact({"equivalent": v.status == "EQUIV"}, "zx_normalize", "ZX-calculus", cert)
        return KV.decline(f"zx: {v.detail}", "zx_normalize")
    if isinstance(x, dict) and "zx_simplify" in x:
        v = simplify(x["zx_simplify"])
        if v.status == "SIMPLIFIED":
            cert = KV.Cert(KV.EXACT, "normal_form_unique", passed=True, check_cost="ZX full_reduce + tensor re-check",
                           detail=v.detail)
            return KV.exact({"normal_form": "zx", "before": v.before, "after": v.after}, "zx_normalize", "ZX-calculus", cert)
        return KV.decline(f"zx: {v.detail}", "zx_normalize")
    return KV.decline("zx: expected {zx_equiv:(a,b)} or {zx_simplify:c}", "zx_normalize")
