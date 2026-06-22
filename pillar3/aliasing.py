"""
Pillar 3 · ROUND 3 #69 — alias / loop-carried dependence analysis (Z3, SOUND) → safe reorder/parallelize.
=========================================================================================================
Reordering or parallelizing a loop  for i: a[w(i)] = g(a[r(i)])  is valid ONLY if distinct iterations do not
interfere: no iteration reads a cell another writes (flow/anti dependence) and no two iterations write the same
cell (output dependence). We prove independence with Z3 over the AFFINE index functions, for ALL i≠j (unbounded):
        ∀ i,j ≥ 0, i≠j:  w(i) ≠ r(j)   ∧   w(i) ≠ w(j).
Proven ⇒ the iterations are independent ⇒ parallel/reordered ≡ sequential ⇒ EXACT. If Z3 finds a colliding
(i,j) ⇒ a real dependence ⇒ DECLINE (keep the sequential order — a wrong "independent" is a correctness bug).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Tuple

import z3

import kernel_verdict as KV


@dataclass
class DependenceResult:
    verdict: "KV.Verdict"
    independent: bool
    counterexample: Optional[str]


def analyze_dependence(name: str, w: Callable, r: Callable) -> DependenceResult:
    """w, r : (z3 index i) -> z3 affine index. Prove ∀ i≠j≥0: w(i)≠r(j) ∧ w(i)≠w(j) (no cross-iteration dep)."""
    i, j = z3.Int("i"), z3.Int("j")
    dom = z3.And(i >= 0, j >= 0, i != j)
    # flow/anti dependence: iteration j reads a cell iteration i wrote
    s_flow = z3.Solver()
    s_flow.add(z3.And(dom, w(i) == r(j)))
    # output dependence: two iterations write the same cell
    s_out = z3.Solver()
    s_out.add(z3.And(dom, w(i) == w(j)))
    rf, ro = s_flow.check(), s_out.check()
    if rf == z3.sat:
        m = s_flow.model()
        return DependenceResult(KV.decline(f"{name}: loop-carried FLOW dependence (i={m[i]} writes what j={m[j]} "
                                           f"reads) ⇒ DECLINE (keep sequential)", f"dep:{name}"), False, str(m))
    if ro == z3.sat:
        m = s_out.model()
        return DependenceResult(KV.decline(f"{name}: OUTPUT dependence (i={m[i]}, j={m[j]} write the same cell) "
                                           f"⇒ DECLINE", f"dep:{name}"), False, str(m))
    if rf == z3.unknown or ro == z3.unknown:
        return DependenceResult(KV.decline(f"{name}: Z3 unknown ⇒ conservatively DECLINE", f"dep:{name}"), False, "unknown")
    cert = KV.Cert(KV.EXACT, "no_loop_carried_dependence", passed=True, check_cost="Z3 (2 ∀ i≠j goals)",
                   detail=f"{name}: ∀ i≠j: w(i)≠r(j) ∧ w(i)≠w(j) ⇒ iterations independent ⇒ parallel ≡ sequential")
    return DependenceResult(KV.exact(name, f"parallel:{name}", "reorder/parallel-safe", cert), True, None)


# ── batteries: independent loops (parallel-safe) and dependent ones (must keep sequential) ──────────────
def independent_loops():
    return [
        # a[2i] = g(a[2i+1])      write even, read odd — never collide (even≠odd), for ALL i,j
        ("even_write_odd_read", lambda i: 2 * i, lambda i: 2 * i + 1),
        # a[2i] = g(a[2i])        each iteration touches only its own (distinct) even cell — independent
        ("self_even_cell", lambda i: 2 * i, lambda i: 2 * i),
        # a[3i] = g(a[3i+2])      stride 3, read offset 2 — w(i)=3i, r(j)=3j+2 never equal (mod 3)
        ("stride3_off2", lambda i: 3 * i, lambda i: 3 * i + 2),
    ]


def dependent_loops():
    return [
        # a[i] = g(a[i+1])        consecutive — iteration i writes i, iteration i-1 reads i ⇒ flow dependence
        ("consecutive", lambda i: i, lambda i: i + 1),
        # a[i//2] = ...           collisions: i=0,1 both write 0 ⇒ output dependence
        ("halving_write", lambda i: i / 2, lambda i: i + 1000000),
    ]
