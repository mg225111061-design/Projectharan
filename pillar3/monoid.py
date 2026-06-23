"""
Pillar 3 · ROUND 2 #39 — map-reduce / monoid recognition (Z3, SOUND) → parallel/tree-reduction is EXACT.
========================================================================================================
A reduction  fold(⊕, xs)  may be re-associated into a parallel/tree reduction ONLY if ⊕ is ASSOCIATIVE
((a⊕b)⊕c = a⊕(b⊕c)); if it also has an identity it is a MONOID (the clean map-reduce shape). We prove
associativity with Z3 over the operator's symbolic semantics; proven ⇒ the tree/parallel reduction yields the
SAME result as the sequential fold regardless of split ⇒ EXACT (data-parallel-safe). A NON-associative operator
(subtraction, average) is Z3-refuted with a counterexample ⇒ DECLINE (re-associating it changes the result —
a correctness bug). This is the structural license behind data-parallel / map-reduce; the speedup itself is a
separate measured concern (and is mode-gated).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

import z3

import kernel_verdict as KV


@dataclass
class MonoidResult:
    verdict: "KV.Verdict"
    associative: bool
    has_identity: bool
    counterexample: Optional[str]


def _valid(claim) -> Tuple[bool, Optional[str]]:
    s = z3.Solver()
    s.add(z3.Not(claim))
    r = s.check()
    if r == z3.unsat:
        return True, None
    if r == z3.sat:
        return False, str(s.model())
    return False, "z3 unknown"


def analyze_reduction(name: str, op: Callable, identity=None) -> MonoidResult:
    """Z3: is `op` associative (∀ a,b,c: (a⊕b)⊕c = a⊕(b⊕c))? and is `identity` a unit? Associative ⇒ EXACT
    (parallel/tree reduction ≡ sequential fold); non-associative ⇒ DECLINE with a counterexample."""
    a, b, c = z3.Ints("a b c")
    assoc, cex = _valid(op(op(a, b), c) == op(a, op(b, c)))
    has_id = False
    if identity is not None:
        idok, _ = _valid(z3.And(op(a, z3.IntVal(identity)) == a, op(z3.IntVal(identity), a) == a))
        has_id = idok
    if not assoc:
        v = KV.decline(f"{name}: ⊕ is NOT associative (counterexample {cex}) ⇒ re-association changes the result "
                       f"⇒ DECLINE (cannot parallelize/tree-reduce)", f"monoid:{name}")
        return MonoidResult(v, False, has_id, cex)
    shape = "monoid (associative + identity)" if has_id else "semigroup (associative)"
    cert = KV.Cert(KV.EXACT, "associativity_proof", passed=True, check_cost="Z3 ∀ a,b,c",
                   detail=f"{name}: ⊕ is associative ⇒ tree/parallel reduction ≡ sequential fold (EXACT); {shape}")
    return MonoidResult(KV.exact(name, f"reduce:{name}", "data-parallel-safe", cert), True, has_id, None)


# ── batteries: associative monoids (parallel-safe) and non-associative operators (must stay sequential) ──
def associative_ops():
    return [
        ("add", lambda x, y: x + y, 0),
        ("mul", lambda x, y: x * y, 1),
        ("max", lambda x, y: z3.If(x > y, x, y), None),
        ("min", lambda x, y: z3.If(x < y, x, y), None),
        ("bit_or_via_arith", lambda x, y: z3.If(z3.Or(x != 0, y != 0), z3.IntVal(1), z3.IntVal(0)), 0),  # boolean OR monoid
    ]


def nonassociative_ops():
    return [
        ("subtract", lambda x, y: x - y, 0),
        ("average", lambda x, y: (x + y) / 2, None),
        ("first_minus_double", lambda x, y: x - 2 * y, 0),
    ]
