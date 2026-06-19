"""
PHASE 2.S3 — proof-directed optimization: inject HARAN-proven FACTS that -O3 cannot derive, then re-validate.
=============================================================================================================
The frontier (§5): in the NON-foldable (variable) region we cannot change the asymptotics, but we can still
beat ordinary -O3 — but ONLY when a HARAN proof gives the native compiler a FACT it could not derive itself
(§1.6). The canonical fact is NON-ALIASING: -O3 must conservatively assume two pointers may alias and so it
refuses to vectorize; a HARAN non-aliasing proof injects `noalias`, unlocking vectorization.

★ HONEST MEASUREMENT (§1.6, §6) ★: we compile the SAME kernel WITH the proof-fact (noalias) and WITHOUT, run
BOTH through the real LLVM -O3 (loop+SLP vectorization) pipeline, and report the MEASURED speedup. If the fact
does not actually unlock a faster kernel here, the number is ~1× and we SAY SO — never "native 초월" without
the proof paying off. Every optimized kernel is re-validated bit-exact (P2.S5) — the optimizer is UNTRUSTED.

The proof→optimization RULE TABLE (declarative; each rule fires only when the proof supplies the fact):
  non-aliasing proof → `noalias`         → vectorization unlocked
  range proof        → drop bounds-check → branch removed
  independence proof → loop reorder      → fusion/interchange (P2.S6)
"""
from __future__ import annotations

import ctypes
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import backend_llvm as BE   # for llvm_available() (registers the native target)

# the declarative proof→optimization table (HARAN-expressible; dogfood self-verifies the table)
RULE_TABLE: Dict[str, str] = {
    "non-aliasing": "noalias attribute → vectorization",
    "range":        "bounds-check elimination → branch removal",
    "independence": "loop reorder (fusion/interchange/tiling)",
}


def _dot_module(noalias: bool):
    import llvmlite.ir as ir
    i64 = ir.IntType(64)
    i64p = i64.as_pointer()
    mod = ir.Module(name="pdo")
    fn = ir.Function(mod, ir.FunctionType(i64, [i64p, i64p, i64]), name="dot")
    a, b, n = fn.args
    a.name, b.name, n.name = "a", "b", "n"
    if noalias:                                   # ★ the proof-injected FACT: a, b do not alias ★
        a.add_attribute("noalias")
        b.add_attribute("noalias")
    entry = fn.append_basic_block("entry")
    loop = fn.append_basic_block("loop")
    exit_ = fn.append_basic_block("exit")
    bld = ir.IRBuilder(entry)
    is_empty = bld.icmp_signed("<=", n, ir.Constant(i64, 0))
    bld.cbranch(is_empty, exit_, loop)
    bld = ir.IRBuilder(loop)
    i_phi = bld.phi(i64, "i")
    acc_phi = bld.phi(i64, "acc")
    i_phi.add_incoming(ir.Constant(i64, 0), entry)
    acc_phi.add_incoming(ir.Constant(i64, 0), entry)
    ai = bld.load(bld.gep(a, [i_phi], inbounds=True))
    bi = bld.load(bld.gep(b, [i_phi], inbounds=True))
    acc_next = bld.add(acc_phi, bld.mul(ai, bi))
    i_next = bld.add(i_phi, ir.Constant(i64, 1))
    cond = bld.icmp_signed("<", i_next, n)
    bld.cbranch(cond, loop, exit_)
    i_phi.add_incoming(i_next, loop)
    acc_phi.add_incoming(acc_next, loop)
    bld = ir.IRBuilder(exit_)
    ret = bld.phi(i64)
    ret.add_incoming(ir.Constant(i64, 0), entry)
    ret.add_incoming(acc_next, loop)
    bld.ret(ret)
    return str(mod)


def _compile_o3(ir_text: str):
    """Run the REAL LLVM -O3 pipeline (loop + SLP vectorization) on the module, then JIT."""
    import llvmlite.binding as llvm
    tm = llvm.Target.from_default_triple().create_target_machine()
    mod = llvm.parse_assembly(ir_text)
    mod.verify()
    pto = llvm.create_pipeline_tuning_options(speed_level=3, size_level=0)
    pto.loop_vectorization = True
    pto.slp_vectorization = True
    pb = llvm.create_pass_builder(tm, pto)
    mpm = pb.getModulePassManager()
    try:
        mpm.run(mod, pb)
    except TypeError:
        mpm.run(mod)
    engine = llvm.create_mcjit_compiler(llvm.parse_assembly(str(mod)), tm)
    engine.finalize_object()
    addr = engine.get_function_address("dot")
    cfn = ctypes.CFUNCTYPE(ctypes.c_int64, ctypes.POINTER(ctypes.c_int64),
                           ctypes.POINTER(ctypes.c_int64), ctypes.c_int64)(addr)
    cfn._engine = engine
    return cfn, str(mod)


@dataclass
class ProofOptResult:
    status: str                 # MEASURED | DECLINE | BLOCKED
    fact: str = ""
    bit_exact: bool = False
    noalias_ms: float = 0.0
    mayalias_ms: float = 0.0
    speedup: float = 0.0
    vectorized: bool = False
    honest_note: str = ""
    detail: str = ""


def measure_noalias_vectorization(n: int = 200_000, reps: int = 50) -> ProofOptResult:
    """[Clock C] the proof-directed headline, measured HONESTLY: same dot-product kernel through -O3, with the
    non-aliasing proof (noalias) vs without. Reports the REAL speedup (and whether vectorization appears in the
    IR). Both validated bit-exact vs a numpy reference. §1.6: if the fact doesn't pay off, the number is ~1×."""
    if not BE.llvm_available():
        return ProofOptResult("BLOCKED", detail=BE._LLVM_ERR)
    try:
        import numpy as np
    except Exception as e:  # noqa: BLE001
        return ProofOptResult("BLOCKED", detail=f"[BLOCKED: numpy — {e}]")
    try:
        cfn_na, ir_na = _compile_o3(_dot_module(noalias=True))
        cfn_ma, ir_ma = _compile_o3(_dot_module(noalias=False))
    except Exception as e:  # noqa: BLE001
        return ProofOptResult("BLOCKED", detail=f"[BLOCKED: pass pipeline — {type(e).__name__}: {e}]")
    rng = np.random.default_rng(7)
    a = rng.integers(0, 100, size=n, dtype=np.int64)
    b = rng.integers(0, 100, size=n, dtype=np.int64)
    ap = a.ctypes.data_as(ctypes.POINTER(ctypes.c_int64))
    bp = b.ctypes.data_as(ctypes.POINTER(ctypes.c_int64))
    ref = int((a * b).sum())                                   # numpy reference (ground truth)
    na_val, ma_val = int(cfn_na(ap, bp, n)), int(cfn_ma(ap, bp, n))
    bit_exact = (na_val == ref == ma_val)                     # ★ S5 gate: both must match the reference ★
    if not bit_exact:
        return ProofOptResult("DECLINE", "non-aliasing", False,
                              detail=f"bit-exact gate failed (noalias={na_val}, mayalias={ma_val}, ref={ref})")
    def bench(cfn):
        cfn(ap, bp, n)                                        # warm
        return min(_t(lambda: cfn(ap, bp, n)) for _ in range(reps))
    na_ms, ma_ms = bench(cfn_na), bench(cfn_ma)
    vectorized = ("<" in ir_na and "x i64>" in ir_na)         # vector types present in the optimized IR
    speedup = round(ma_ms / na_ms, 2) if na_ms > 0 else 1.0
    note = (f"non-aliasing proof unlocked vectorization → {speedup}× over may-alias -O3"
            if speedup > 1.15 else
            f"[MEASURED {speedup}×]: the noalias fact did NOT measurably unlock a faster kernel here (§1.6 — "
            "we report ~1×, NOT 'native 초월'); both are bit-exact")
    return ProofOptResult("MEASURED", "non-aliasing", True, round(na_ms, 5), round(ma_ms, 5),
                          speedup, vectorized, note, f"n={n}, reps={reps}; both -O3, validated bit-exact vs numpy")


def _t(fn) -> float:
    t = time.perf_counter(); fn(); return (time.perf_counter() - t) * 1000
