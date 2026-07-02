"""
Pillar 3 · Stage 3 — cross-cutting GLOBAL transforms (the flat-profile killer; extend mode).
=============================================================================================
When no single hotspot dominates ("death by a thousand cuts"), local fixes fail — a global transform that
multiplies across EVERY frame is the only lever. Each transform is differential-verified and whole-program
measured (Rules 1/4). Honest UNVERIFIED tagging where a dependency is absent in the sandbox (Rule 6).

  • async/batch all independent I/O  — sequential blocking I/O → concurrent (ThreadPool, stdlib). VERIFIED.
  • pervasive serialization swap     — json → a faster serializer everywhere, round-trip-value-equivalent.
        orjson/msgpack are ABSENT here ⇒ the production target is tagged UNVERIFIED; we DEMONSTRATE the swap
        with stdlib `marshal` (measurable) and verify round-trip value identity.
  • interpreter → compiled hot region — a hot pure-numeric op compiled via llvmlite (backend_llvm), applied
        across every frame. Differential-verified; tagged UNVERIFIED if llvmlite is unavailable.
"""
from __future__ import annotations

import concurrent.futures as _cf
import json
import marshal
from typing import Any, Callable, List

import kernel_verdict as KV


# ── async / batch all independent I/O ─────────────────────────────────────────────────────────────────
def make_concurrent(io_fn: Callable[[Any], Any], max_workers: int = 16) -> Callable[[List[Any]], List[Any]]:
    """Turn a sequential map over independent blocking I/O into a concurrent one (order-preserving)."""
    def run(items: List[Any]) -> List[Any]:
        with _cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
            return list(ex.map(io_fn, items))
    return run


def sequential(io_fn: Callable[[Any], Any]) -> Callable[[List[Any]], List[Any]]:
    return lambda items: [io_fn(x) for x in items]


# ── pervasive serialization swap (json → marshal here; orjson is the UNVERIFIED production target) ─────
def json_roundtrip(obj: Any) -> Any:
    return json.loads(json.dumps(obj))


def marshal_roundtrip(obj: Any) -> Any:
    return marshal.loads(marshal.dumps(obj))


def serialization_swap_grade(workload: List[Any]) -> "tuple[KV.Verdict, dict]":
    """Verify round-trip VALUE equivalence (json vs marshal) and report which is faster. Output bytes differ
    (different formats) — equivalence is on the deserialized value, which is what callers depend on."""
    import time
    equiv = all(marshal_roundtrip(x) == json_roundtrip(x) == x for x in workload)
    if not equiv:
        return KV.decline("marshal/json round-trip values differ on this workload", "serialize_swap"), {}
    def med(fn):
        ts = []
        for _ in range(7):
            t = time.perf_counter()
            for x in workload:
                fn(x)
            ts.append(time.perf_counter() - t)
        return min(ts)
    tj, tm = med(json_roundtrip), med(marshal_roundtrip)
    info = {"json_s": tj, "marshal_s": tm, "ratio": tj / tm if tm else 0.0,
            "orjson": "UNVERIFIED (ABSENT in sandbox; production target)"}
    cert = KV.Cert(KV.EXACT, "roundtrip_value_equiv", passed=True, check_cost=f"O(n)={len(workload)}",
                   detail="json↔marshal round-trip yields identical deserialized values (bytes differ by format)")
    return KV.exact(marshal_roundtrip, "serialize_swap", f"{info['ratio']:.2f}× per-op (stdlib marshal)", cert), info


# ── interpreter → compiled hot numeric region (llvmlite via backend_llvm) ──────────────────────────────
def compile_numeric_poly(expr: str):
    """Compile an integer polynomial P(n) to native i64 (llvmlite). Returns (callable_or_None, status)."""
    import backend_llvm as BE
    if not BE.llvm_available():
        return None, "UNVERIFIED [BLOCKED: llvmlite absent]"
    nf = BE.compile_closed_form(expr, "n")
    if nf.status != "OK":
        return None, f"UNVERIFIED (not lowerable: {nf.detail})"
    return nf.cfn, "EXACT (native i64; translation-validatable)"
