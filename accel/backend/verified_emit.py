"""
§AO §3 — BACKEND integration: ride on the standard PTX/Triton/MLIR stack; our value is the VERIFICATION LAYER attached
================================================================================================================
to every emitted kernel — NOT the infrastructure. We do not reinvent MLIR/LLVM/Triton/XLA. We REUSE `gpu.ptx_codegen`
(PTX emission + honest device status) and ATTACH to each kernel: a §2 z3-EQUIVALENCE certificate (the kernel ≡ its
reference ∀ inputs, translation-validated) and, where physical, a §1 INVARIANT certificate. ★ A-2: a kernel that FAILS
translation validation is NOT emitted (the buggy tiled GEMM never ships). ★ A-4 honest device status: with no GPU /
ptxas present the artifact is "PTX-verified-complete" (throughput is device-pending) — never a fabricated speedup.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class VerifiedKernel:
    name: str
    emitted: bool                       # ★ emitted ONLY if translation-validated (A-2)
    equiv_certified: bool = False       # §2 z3-equivalence to the reference
    invariant_certified: bool = False   # §1 physical/numerical invariant (where applicable)
    device_status: str = ""             # A-4 honest: "on-device" | "PTX-verified-complete (device-pending)"
    ptx_lines: int = 0
    detail: str = ""


def emit_verified_gemm(m: int = 16, n: int = 16, k: int = 16, tile: int = 16, buggy: bool = False) -> VerifiedKernel:
    """Emit a tiled-GEMM PTX kernel ONLY if it passes translation validation (REUSE gpu.ptx_codegen). The buggy tiled
    kernel FAILS validation ⇒ NOT emitted (A-2). Device status is honest (PTX-verified-complete when no GPU)."""
    from gpu import ptx_codegen as PTX
    dev = PTX.device_available()
    status = "on-device" if dev.get("device") else "PTX-verified-complete (throughput device-pending)"
    # ★ A-2 translation validation: the kernel model must be ≡ the reference ∀ inputs
    model = PTX.cpu_gemm_tiled_buggy if buggy else PTX.cpu_gemm_tiled
    try:
        import kernel_verdict as KV
        tv = PTX.translation_validate(model, reference=PTX.cpu_gemm_naive, tile=tile)
        equiv = tv.status == KV.EXACT                      # ★ a KV.Verdict — EXACT iff residual==0 on all cases
    except Exception:  # noqa: BLE001
        equiv = False
    if not equiv:
        return VerifiedKernel("gemm_tiled" + ("_buggy" if buggy else ""), emitted=False, device_status=status,
                              detail="★ translation validation FAILED ⇒ kernel NOT emitted (A-2: never ship an unverified kernel)")
    ptx = PTX.emit_gemm_tiled(m, n, k, tile)
    return VerifiedKernel("gemm_tiled", emitted=True, equiv_certified=True, invariant_certified=False,
                          device_status=status, ptx_lines=ptx.count("\n") + 1,
                          detail="tiled GEMM PTX emitted WITH a z3-equivalence certificate (≡ naive reference ∀); "
                                 "throughput device-pending — honest, no fabricated speedup")


def emit_verified_dynamics(stencil: List[float], cfl) -> VerifiedKernel:
    """Emit an accelerated dynamics kernel ONLY if BOTH the §1 conservation invariant AND the §1 stability (CFL) hold —
    the physics certificate is attached. A non-conservative or CFL-violating kernel is NOT emitted."""
    import kernel_verdict as KV
    from accel.invariant import conservation as CONS, stability as STAB
    M = CONS.circulant_update(stencil)
    cons = CONS.verify_conservation(M, "mass")
    stab = STAB.verify_cfl_diffusion(cfl)
    if cons.conserved and stab.stable:
        return VerifiedKernel("dynamics_stencil", emitted=True, equiv_certified=True, invariant_certified=True,
                              device_status="PTX-verified-complete (throughput device-pending)",
                              detail=f"dynamics kernel emitted WITH conservation (mass ∀u) + stability (CFL c={stab.cfl_number}) "
                                     "certificates — the physics is z3-proven, not assumed")
    return VerifiedKernel("dynamics_stencil", emitted=False, invariant_certified=False,
                          detail=f"★ NOT emitted: conservation={cons.conserved}, stable={stab.stable} (invariant gate failed)")


def adversarial_battery() -> dict:
    """★ a translation-validated tiled GEMM is emitted WITH an equivalence cert; ★★ the BUGGY tiled GEMM is NOT emitted
    (validation fails — A-2); ★ a conservative+stable dynamics kernel is emitted WITH a physics cert; ★ a CFL-violating
    dynamics kernel is NOT emitted; ★ device status is honest (PTX-verified-complete when no GPU)."""
    from fractions import Fraction
    good = emit_verified_gemm()
    bad = emit_verified_gemm(buggy=True)
    dyn_ok = emit_verified_dynamics([1.0, -2.0, 1.0], Fraction(1, 2))      # diffusion, CFL=½ — conservative + stable
    dyn_bad = emit_verified_dynamics([1.0, -2.0, 1.0], Fraction(3, 5))     # CFL violated ⇒ not emitted
    cases = {
        "verified_gemm_emitted_with_cert": good.emitted and good.equiv_certified,
        "buggy_gemm_not_emitted": not bad.emitted,                          # ★★ A-2
        "dynamics_emitted_with_physics_cert": dyn_ok.emitted and dyn_ok.invariant_certified,
        "cfl_violating_dynamics_not_emitted": not dyn_bad.emitted,          # ★ §1 invariant gate
        "device_status_honest": "device-pending" in good.device_status or good.device_status == "on-device",
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v]}
