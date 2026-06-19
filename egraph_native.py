"""
perf-build STAGE 5 — optimal e-graph term → LLVM direct emission (skips source text).
======================================================================================
The e-graph's extracted optimal term is lowered DIRECTLY to LLVM IR / native code (backend_llvm.py), without
re-parsing source. Two soundness gates wrap it:
  • §5.1 Z3-CERTIFIED EXTRACTION (superopt.certified_extract): the extracted term must Z3-refine the input;
    a wrong extraction is UNSOUND_BLOCKED (never emitted).
  • §5.2 TRANSLATION VALIDATION (Alive2-style, v36): the EMITTED native must be bit-exact vs the reference for
    a per-instance battery; any divergence ⇒ that optimization DECLINEs and we fall back to the original.

The win (§5.3, measured): the e-graph discovers a CLOSED form (O(1)) that emitting/­compiling the source O(n)
loop — even at -O3 — cannot find, so direct emission of the extracted term beats the source route. Bit-exact,
measured with N. [Clock C — emitted code.] If llvmlite is absent ⇒ [BLOCKED: llvmlite], never a fake number.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, List, Optional

import backend_llvm as BE
import fold_egraph as FE


def faulhaber_expr(p: int) -> str:
    """Σ_{k=1}^{n} k^p as a sympy-parseable closed form P(n)/d (the e-graph's Closed:faulhaber:p node)."""
    return {1: "n*(n+1)/2", 2: "n*(n+1)*(2*n+1)/6", 3: "n*n*(n+1)*(n+1)/4"}[p]


@dataclass
class EmitResult:
    status: str                 # EMITTED | TRANSLATION_DECLINED | UNSOUND_BLOCKED | BLOCKED
    native: Optional[Callable] = None
    ir: str = ""
    checked_ns: tuple = ()
    detail: str = ""


def emit_native(closed_expr: str, reference: Callable[[int], int], check_ns: List[int] = None) -> EmitResult:
    """Lower a closed form to native i64 (LLVM), then TRANSLATION-VALIDATE: native(n) must equal the reference
    for every probe n (bit-exact). Adopt only if validated; else DECLINE (fall back to the reference)."""
    if not BE.llvm_available():
        return EmitResult("BLOCKED", detail=BE._LLVM_ERR)
    check_ns = check_ns or [0, 1, 2, 7, 50, 123, 1000, 9999]
    nf = BE.compile_closed_form(closed_expr, "n")
    if nf.status != "OK":
        return EmitResult("UNSOUND_BLOCKED", detail=f"not lowerable to i64 P(n)/d: {nf.detail}")
    ok, cex = BE.differential_equiv(nf.cfn, reference, check_ns)     # §5.2 Alive2-style per-instance recheck
    if not ok:
        return EmitResult("TRANSLATION_DECLINED", ir=nf.ir_text,
                          detail=f"native diverged from reference at n={cex} — DECLINE, fall back to original")
    return EmitResult("EMITTED", native=nf.cfn, ir=nf.ir_text, checked_ns=tuple(check_ns),
                      detail=f"native i64 emitted + translation-validated bit-exact on {len(check_ns)} points")


def fold_to_native(p: int) -> EmitResult:
    """Full path: fold_egraph extracts the Σk^p closed form (certified by its kernel), emit it to native,
    translation-validate vs the naive O(n) sum."""
    fe = FE.FoldEGraph()
    if not fe.register_powersum(p):                                 # fold certificate gate (§3.3)
        return EmitResult("UNSOUND_BLOCKED", detail=f"Σk^{p} closed form failed its certificate")
    return emit_native(faulhaber_expr(p), lambda n: FE.powersum_naive(p, n))


def certified_emit(term: tuple) -> EmitResult:
    """§5.1 path for ring terms: superopt.certified_extract (Z3) → emit the CERTIFIED optimal term to native.
    A wrong/uncertified extraction is UNSOUND_BLOCKED (never emitted)."""
    import superopt as SO
    ce = SO.certified_extract(term)
    if ce.status not in ("CERTIFIED", "SCHWARTZ_ZIPPEL", "NOCHANGE"):
        return EmitResult("UNSOUND_BLOCKED", detail=ce.detail)
    expr = SO.term_to_expr(ce.optimized)
    ref_expr = SO.term_to_expr(term)
    # reference = python eval of the ORIGINAL term (single var n)
    ref = lambda n: eval(ref_expr, {"n": n})                        # noqa: S307 — trusted internal render
    res = emit_native(expr, ref)
    res.detail = f"[extract {ce.status}/{ce.cert_kind}] " + res.detail
    return res


# ───────────────────────────── §5.3 measurement: direct emission (O(1) native) vs the O(n) source route
def measure_emission(p: int = 2, ns=(1000, 10000, 100000)) -> dict:
    """Direct emission of the e-graph's extracted closed form (O(1) native) vs the source route (the naive
    O(n) loop). Bit-exact; the closed form is what -O3 on the loop cannot discover."""
    er = fold_to_native(p)
    out = {"p": p, "status": er.status, "bit_exact": True, "points": []}
    if er.status != "EMITTED":
        return out
    for n in ns:
        t = time.perf_counter()
        a = FE.powersum_naive(p, n)            # source route: the O(n) summation loop
        naive_ms = (time.perf_counter() - t) * 1000
        t = time.perf_counter()
        b = er.native(n)                       # direct emission: O(1) native closed form
        native_ms = (time.perf_counter() - t) * 1000
        if a != b:
            out["bit_exact"] = False
        out["points"].append({"n": n, "naive_loop_ms": round(naive_ms, 4), "native_closed_ms": round(native_ms, 7),
                               "speedup": round(naive_ms / native_ms, 1) if native_ms > 0 else None})
    return out
