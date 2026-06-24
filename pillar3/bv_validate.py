"""
Pillar 3 · ROUND 3 #67 — translation validation under REAL machine semantics (bitvector / overflow-aware).
============================================================================================================
A peephole rewrite that is correct over idealized integers ℤ can be WRONG on a real machine because of
fixed-width wraparound:  (x+1) > x  is a theorem over ℤ but FALSE at INT_MAX;  (x*2)/2 == x  fails on signed
overflow. An optimizer that trusts the ℤ-identity miscompiles. This validator proves equivalence over Z3
BITVECTORS (the machine's actual two's-complement semantics), so a transform is accepted EXACT only if it is
sound under overflow — and an overflow-unsafe rewrite is REFUTED with a concrete counterexample ⇒ DECLINE
(keep the original; a wrong 'safe' is a correctness bug). This is the Clock-B VERIFICATION half (machine-
faithful refinement), not a speedup claim: EXACT here means "proven equivalent on the real machine".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Tuple

import z3

import kernel_verdict as KV


@dataclass
class BVResult:
    verdict: KV.Verdict
    proved: bool
    counterexample: Optional[dict]


def bv_equiv(orig: Callable, opt: Callable, bits: int = 32, nvars: int = 2) -> Tuple[str, Optional[dict]]:
    """Z3 over BITVECTORS: is orig(v…) == opt(v…) for EVERY machine-integer assignment? PROVEN (unsat of ≠) /
    REFUTED (a wraparound counterexample) / UNKNOWN. orig/opt take z3 BitVec args and return a z3 BitVec expr."""
    xs = [z3.BitVec(f"v{i}", bits) for i in range(nvars)]
    s = z3.Solver()
    s.add(orig(*xs) != opt(*xs))
    r = s.check()
    if r == z3.unsat:
        return "PROVEN", None
    if r == z3.sat:
        m = s.model()
        return "REFUTED", {str(v): (m[v].as_long() if m[v] is not None else None) for v in xs}
    return "UNKNOWN", None


def bv_equiv_inhouse(build: Callable, bits: int = 8) -> Tuple[str, Optional[dict]]:
    """ZERO-DEPENDENCY counterpart of bv_equiv: decide ∀(bits-bit vars). lhs == rhs with the in-house bit-blasting
    SMT (no Z3). `build(bb)` returns (lhs_BV, rhs_BV) over a `bitblast_smt.BitBlaster`. Same contract as bv_equiv —
    PROVEN (UNSAT of ≠) / REFUTED (a checked counterexample) — but EXACT only WITHIN `bits` (the bound is stated by
    the certificate) and only for this solver's QF-BV theory. Used to discharge in-scope obligations with no
    external solver, and to cross-check Z3 where both apply. NOT Z3 parity (no SIGNED division (sdiv) or
    variable-shift; signed compare, general multiply, right-shift, ite-mux, and UNSIGNED division ARE in-house)."""
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root → bitblast_smt
    import bitblast_smt as BB
    r = BB.prove_bv_identity(build, bits)
    if r.status == "VALID":
        return "PROVEN", None
    if r.status == "INVALID":
        return "REFUTED", r.model
    return "UNKNOWN", None


def cross_check_inhouse_vs_z3() -> dict:
    """Demonstrate the in-house solver is a FAITHFUL zero-dependency replacement for Z3 on its decidable subset:
    prove every sound peephole BOTH ways at the SAME small width and assert agreement. The unsafe peepholes are
    NOT cross-checked here — they are unsound (and mul2_div2_id needs SIGNED division (sdiv), still Z3-only);
    the in-house solver can refute the conditional ones via ite-mux, but they are not SOUND peepholes, so they
    stay out of this cross-check."""
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import bitblast_smt as BB
    z3_by_name = {name: (o, p) for name, o, p in sound_peepholes()}
    rows = []
    for name, build, width in BB.inhouse_sound_peepholes():
        inhouse, _ = bv_equiv_inhouse(build, width)
        orig, opt = z3_by_name[name]
        z3v, _ = bv_equiv(orig, opt, bits=width, nvars=2)          # Z3 at the SAME width for a fair comparison
        rows.append({"name": name, "width": width, "inhouse": inhouse, "z3": z3v, "agree": inhouse == z3v == "PROVEN"})
    return {"rows": rows, "all_agree": all(r["agree"] for r in rows),
            "covered": [r["name"] for r in rows],
            "out_of_scope_for_inhouse": [n for n, *_ in unsafe_peepholes()]}  # honest: these stay on Z3


def bv_grade(name: str, orig: Callable, opt: Callable, *, bits: int = 32, nvars: int = 2) -> BVResult:
    """EXACT iff the rewrite is PROVEN equivalent under machine (bitvector) semantics; REFUTED/UNKNOWN ⇒ DECLINE
    (keep the original — never an unsound 'safe'). A Clock-B verification verdict (machine-faithful refinement)."""
    verdict, cex = bv_equiv(orig, opt, bits, nvars)
    if verdict == "PROVEN":
        cert = KV.Cert(KV.EXACT, "bitvector_refinement", passed=True, check_cost=f"Z3 ∀ bv{bits}",
                       detail=f"{name}: opt ≡ orig proven over {bits}-bit two's-complement (overflow-faithful)")
        return BVResult(KV.exact(opt, f"bv:{name}", f"Clock-B refinement (bv{bits})", cert), True, None)
    if verdict == "REFUTED":
        return BVResult(KV.decline(f"{name}: overflow-unsafe — opt ≠ orig at {cex} ⇒ DECLINE (keep original)",
                                   f"bv:{name}"), False, cex)
    return BVResult(KV.decline(f"{name}: Z3 UNKNOWN ⇒ conservatively DECLINE", f"bv:{name}"), False, None)


def _i1(b):
    return (z3.BitVecVal(1, b), z3.BitVecVal(0, b))


# ── SOUND peepholes — equivalent under machine wraparound (each EXACT) ──────────────────────────────────
def sound_peepholes(bits: int = 32):
    return [
        ("mul2_to_shl1", lambda x, y: x * 2, lambda x, y: x << 1),
        ("mul8_to_shl3", lambda x, y: x * 8, lambda x, y: x << 3),
        ("xor_via_or_minus_and", lambda x, y: (x | y) - (x & y), lambda x, y: x ^ y),
        ("add_sub_cancel", lambda x, y: (x + y) - y, lambda x, y: x),        # wraps identically ⇒ sound
        ("clear_low_bit", lambda x, y: x & (x - 1), lambda x, y: x & ~(-x & x)),
    ]


# ── UNSAFE over machine ints — true over ℤ, FALSE under overflow (each must be REFUTED ⇒ DECLINE) ───────
def unsafe_peepholes(bits: int = 32):
    one, zero = z3.BitVecVal(1, bits), z3.BitVecVal(0, bits)
    return [
        # (x+1) > x : a ℤ-theorem, false at INT_MAX (signed gt)
        ("succ_gt_self", lambda x, y: z3.If(x + 1 > x, one, zero), lambda x, y: one),
        # (x*2)/2 == x : signed, fails on overflow
        ("mul2_div2_id", lambda x, y: (x * 2) / 2, lambda x, y: x),
        # x+y >= x  (assuming y>=0 is NOT encoded) : false on overflow
        ("add_monotone", lambda x, y: z3.If(x + y >= x, one, zero), lambda x, y: one),
    ]


def idealized_vs_machine_contrast() -> dict:
    """The headline: (x+1) > x is PROVABLE over idealized ℤ but REFUTED over bitvectors. An optimizer that
    trusts the ℤ-identity miscompiles; the machine-faithful validator catches it. Returns both verdicts."""
    xi = z3.Int("x")
    si = z3.Solver()
    si.add(z3.Not(xi + 1 > xi))                              # ℤ: ∀x x+1>x ⇒ negation unsat ⇒ "provable"
    idealized = "PROVEN" if si.check() == z3.unsat else "REFUTED"
    machine, cex = bv_equiv(lambda x, y: z3.If(x + 1 > x, z3.BitVecVal(1, 32), z3.BitVecVal(0, 32)),
                            lambda x, y: z3.BitVecVal(1, 32))
    return {"claim": "(x+1) > x", "idealized_Z": idealized, "machine_bv32": machine, "machine_counterexample": cex}
