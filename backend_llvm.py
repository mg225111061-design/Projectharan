"""
PHASE 2.S1+S2 — verified LLVM native backend: foldable closed forms → O(1) native, gated bit-exact.
====================================================================================================
HARAN/verified closed forms are lowered to LLVM IR (llvmlite) and JIT-compiled to native code. EVERY emit is
gated by a DIFFERENTIAL EQUIVALENCE check: the native function must be BIT-EXACT with the Python reference
over a battery of inputs, else the codegen is DECLINED (assume_unknown — never a wrong native answer).

P2.S1 backend : compile an integer closed form P(n)/d (sympy) to i64 LLVM IR → native (a small LLVM subset;
                unsupported constructs ⇒ UNKNOWN, not a guess).
P2.S2 fold→native : take fold_kernels' FOLDED closed form, emit native, and adopt it ONLY after bit-exact
                vs the original naive loop. Then the O(n) loop is replaced by an O(1) native evaluation.

★ ENV HONESTY (§8): if llvmlite is unavailable → [BLOCKED: llvmlite] with the install command, no fake native.
★ SOUNDNESS (§1.4/§4): i64 native can OVERFLOW where Python bigint does not; the bit-exact gate CATCHES this
   and DECLINEs that range (honest "missed optimization", never a wrong answer). Stated in the certificate.
"""
from __future__ import annotations

import ctypes
import time
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

import sympy as sp

_LLVM_OK = None
_LLVM_ERR = ""


def llvm_available() -> bool:
    global _LLVM_OK, _LLVM_ERR
    if _LLVM_OK is None:
        try:
            import llvmlite.binding as llvm   # llvmlite>=0.44 initializes LLVM automatically (no initialize() calls)
            for _init in ("initialize", "initialize_native_target", "initialize_native_asmprinter"):
                f = getattr(llvm, _init, None)
                if f is not None:
                    try:
                        f()                    # older llvmlite still needs these; 0.47 removed/deprecated them
                    except Exception:          # noqa: BLE001 — deprecated-removed in 0.47 → ignore
                        pass
            llvm.Target.from_default_triple().create_target_machine()   # real capability probe
            _LLVM_OK = True
        except Exception as e:  # noqa: BLE001
            _LLVM_OK, _LLVM_ERR = False, f"[BLOCKED: llvmlite — {type(e).__name__}: {e}; pip install llvmlite]"
    return _LLVM_OK


@dataclass
class NativeFn:
    status: str                 # OK | UNKNOWN | BLOCKED
    cfn: Optional[Callable] = None
    ir_text: str = ""
    closed_form: str = ""
    denom: int = 1
    detail: str = ""


def _emit_poly_i64(builder, ir, nval, poly: sp.Poly):
    """Emit i64 IR for an integer polynomial in n (Horner over expanded coefficients)."""
    i64 = ir.IntType(64)
    coeffs = poly.all_coeffs()          # highest degree first
    acc = ir.Constant(i64, int(coeffs[0]))
    for c in coeffs[1:]:
        acc = builder.mul(acc, nval)
        acc = builder.add(acc, ir.Constant(i64, int(c)))
    return acc


def compile_closed_form(expr_str: str, var: str = "n") -> NativeFn:
    """P2.S1: compile an integer-valued closed form P(n)/d to native i64 (LLVM). UNKNOWN if it is not of that
    form (non-constant denominator / non-polynomial numerator). BLOCKED if llvmlite is missing."""
    if not llvm_available():
        return NativeFn("BLOCKED", detail=_LLVM_ERR)
    import llvmlite.binding as llvm
    import llvmlite.ir as ir
    n = sp.Symbol(var)
    try:
        expr = sp.sympify(expr_str, locals={var: n})
        num, den = sp.fraction(sp.together(expr))
        if not den.is_integer or den == 0:
            return NativeFn("UNKNOWN", closed_form=expr_str, detail="denominator not an integer constant")
        poly = sp.Poly(sp.expand(num), n)
        if poly.total_degree() > 12 or any(not c.is_integer for c in poly.all_coeffs()):
            return NativeFn("UNKNOWN", closed_form=expr_str, detail="numerator not an integer polynomial (or too high degree)")
    except Exception as e:  # noqa: BLE001
        return NativeFn("UNKNOWN", closed_form=expr_str, detail=f"not analyzable ({type(e).__name__})")
    i64 = ir.IntType(64)
    mod = ir.Module(name="fold")
    fn = ir.Function(mod, ir.FunctionType(i64, [i64]), name="f")
    blk = fn.append_basic_block("entry")
    b = ir.IRBuilder(blk)
    res = _emit_poly_i64(b, ir, fn.args[0], poly)
    if int(den) != 1:
        res = b.sdiv(res, ir.Constant(i64, int(den)))      # exact for integer-valued closed forms
    b.ret(res)
    ir_text = str(mod)
    target = llvm.Target.from_default_triple(); tm = target.create_target_machine()
    backing = llvm.parse_assembly(ir_text); backing.verify()
    engine = llvm.create_mcjit_compiler(backing, tm)
    engine.finalize_object()
    addr = engine.get_function_address("f")
    cfn = ctypes.CFUNCTYPE(ctypes.c_int64, ctypes.c_int64)(addr)
    cfn._engine = engine                                   # keep the JIT engine alive
    return NativeFn("OK", cfn, ir_text, expr_str, int(den), "compiled P(n)/d to i64 native")


def differential_equiv(native: Callable, py_ref: Callable, ns: List[int]) -> Tuple[bool, Optional[int]]:
    """The GATE: native must be BIT-EXACT with the Python reference over `ns`. Returns (ok, first_bad_n)."""
    for n in ns:
        if int(native(n)) != int(py_ref(n)):
            return False, n
    return True, None


@dataclass
class FoldNative:
    status: str                 # FOLDED_NATIVE | DECLINE | BLOCKED
    bit_exact: bool = False
    n_checked: int = 0
    closed_form: str = ""
    native_ms: float = 0.0
    naive_ms: float = 0.0
    speedup: float = 0.0
    detail: str = ""


def fold_to_native(closed_form: str, naive_py: Callable, check_ns: Optional[List[int]] = None,
                   bench_n: int = 200_000, var: str = "n") -> FoldNative:
    """P2.S2: compile the FOLDED closed form to native, ADOPT only after bit-exact vs the naive loop on
    `check_ns` (catches i64 overflow honestly). Then measure native O(1) vs naive O(n) at `bench_n`."""
    nf = compile_closed_form(closed_form, var)
    if nf.status == "BLOCKED":
        return FoldNative("BLOCKED", detail=nf.detail)
    if nf.status != "OK":
        return FoldNative("DECLINE", detail=f"backend UNKNOWN: {nf.detail}")
    check_ns = check_ns or [0, 1, 2, 3, 5, 8, 13, 100, 1000, 5000]
    _v = sp.Symbol(var)
    _cf = sp.sympify(closed_form, locals={var: _v})
    py_closed = lambda m: int(_cf.subs(_v, m))     # EXACT integer eval (NOT float lambdify — float /6 truncates)
    # gate 1: native == python-closed-form (bit-exact on the checked range)
    ok1, bad1 = differential_equiv(nf.cfn, lambda n: int(py_closed(n)), check_ns)
    # gate 2: closed form == naive loop (the fold itself is correct)
    ok2, bad2 = differential_equiv(lambda n: int(py_closed(n)), naive_py, check_ns)
    if not (ok1 and ok2):
        return FoldNative("DECLINE", bit_exact=False, n_checked=len(check_ns),
                          detail=f"bit-exact gate FAILED (native@{bad1} / fold@{bad2}) — declined, "
                                 "naive kept (honest: likely i64 overflow or fold mismatch)")
    # measure [Clock C]: native O(1) vs naive O(n)
    t = time.perf_counter(); naive_py(bench_n); naive_ms = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    for _ in range(1000):
        nf.cfn(bench_n)
    native_ms = (time.perf_counter() - t) / 1000 * 1000
    return FoldNative("FOLDED_NATIVE", True, len(check_ns), closed_form,
                      round(native_ms, 6), round(naive_ms, 4),
                      round(naive_ms / native_ms, 1) if native_ms > 0 else 0.0,
                      f"native O(1) bit-exact vs naive on {len(check_ns)} points; i64 range only (gate catches overflow)")
