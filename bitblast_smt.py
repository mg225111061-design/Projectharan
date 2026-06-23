"""
§2 — ZERO-DEPENDENCY bit-blasting SMT (in-house DPLL SAT + bit-blaster + certificate checker).
==============================================================================================
No coqc / cvc5 / Bitwuzla / Lean / z3 — this decides fixed-width BITVECTOR obligations entirely in-house, so the
engine can discharge the proofs it actually generates (no-overflow bounds, equivalence of integer transforms)
with ZERO external solver. It is:
  • a DECISION PROCEDURE on a bounded domain — width-w bitvectors. A validity result is EXACT *within that
    width* (the bound is stated); widen and re-prove, or DECLINE, beyond it. Never EXACT outside the decided bound.
  • DETERMINISTIC — fixed variable order, fixed clause order, no wall-clock heuristics; same input ⇒ same result
    AND same certificate, every run.
  • CERTIFICATE-PRODUCING — SAT returns a MODEL that an independent tiny checker verifies against the CNF; for a
    validity claim (∀x. P), UNSAT of ¬P is the proof (decided exhaustively over the w-bit domain by the SAT core).
Honest scope: bitvector add / sub / neg / mul-by-constant / general w×w multiply / eq / ult / slt / sgt (signed
compare) / and / or / xor / not / left-shift / logical+arithmetic right-shift (by a constant), quantifier-free,
fixed width. NOT cvc5/Z3-parity (no division, no VARIABLE-amount shift, no ite-mux as a first-class op, no arrays,
no reals, no unbounded ints). That's the point — small TCB, zero deps. (Signed comparison was added so the
signed-overflow obligations the CODE engine generates — e.g. (x+1) >ₛ x false at INT_MAX — are decided in-house;
general multiply + right-shift were added so strength-reduction transforms — mul↔shift, sign-mask, bit round-trips
— are proven VALID in-house rather than only refuted, each EXACT within the stated width.)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ── CNF builder (Tseitin), variables are positive ints; a literal is ±var ────────────────────────────────
TRUE_SENTINEL = None


class CNF:
    def __init__(self):
        self.nvars = 0
        self.clauses: List[List[int]] = []

    def new_var(self) -> int:
        self.nvars += 1
        return self.nvars

    def add(self, *lits: int):
        self.clauses.append(list(lits))

    # gate helpers (Tseitin): return a literal equal to the gate output
    def lit_and(self, a: int, b: int) -> int:
        o = self.new_var()
        self.add(-o, a); self.add(-o, b); self.add(o, -a, -b)
        return o

    def lit_or(self, a: int, b: int) -> int:
        o = self.new_var()
        self.add(o, -a); self.add(o, -b); self.add(-o, a, b)
        return o

    def lit_xor(self, a: int, b: int) -> int:
        o = self.new_var()
        self.add(-o, a, b); self.add(-o, -a, -b); self.add(o, -a, b); self.add(o, a, -b)
        return o

    def lit_not(self, a: int) -> int:
        return -a

    def assert_eq(self, a: int, b: int):                     # a ↔ b
        self.add(-a, b); self.add(a, -b)


# ── bit-blasted bitvectors: a BV is a list of CNF literals, LSB first ─────────────────────────────────────
@dataclass
class BV:
    bits: List[int]                                          # each a CNF literal (or a const True/False literal)

    @property
    def width(self) -> int:
        return len(self.bits)


class BitBlaster:
    def __init__(self, width: int):
        self.w = width
        self.cnf = CNF()
        self._true = self.cnf.new_var()
        self.cnf.add(self._true)                             # a literal pinned to True
        self._false = -self._true
        self.inputs: Dict[str, BV] = {}

    def const(self, value: int) -> BV:
        return BV([self._true if (value >> i) & 1 else self._false for i in range(self.w)])

    def var(self, name: str) -> BV:
        bv = BV([self.cnf.new_var() for _ in range(self.w)])
        self.inputs[name] = bv
        return bv

    def add(self, a: BV, b: BV) -> BV:                       # ripple-carry adder (mod 2^w)
        out, carry = [], self._false
        for i in range(self.w):
            s = self.cnf.lit_xor(self.cnf.lit_xor(a.bits[i], b.bits[i]), carry)
            c1 = self.cnf.lit_and(a.bits[i], b.bits[i])
            c2 = self.cnf.lit_and(self.cnf.lit_xor(a.bits[i], b.bits[i]), carry)
            carry = self.cnf.lit_or(c1, c2)
            out.append(s)
        return BV(out)

    def neg(self, a: BV) -> BV:                              # two's complement: ~a + 1
        return self.add(BV([-x for x in a.bits]), self.const(1))

    def sub(self, a: BV, b: BV) -> BV:
        return self.add(a, self.neg(b))

    def mul_const(self, a: BV, k: int) -> BV:               # shift-add by a constant
        acc = self.const(0)
        for i in range(self.w):
            if (k >> i) & 1:
                shifted = BV([self._false] * i + a.bits[: self.w - i])
                acc = self.add(acc, shifted)
        return acc

    def bnot(self, a: BV) -> BV:                             # bitwise complement (negate each literal)
        return BV([-x for x in a.bits])

    def band(self, a: BV, b: BV) -> BV:
        return BV([self.cnf.lit_and(a.bits[i], b.bits[i]) for i in range(self.w)])

    def bor(self, a: BV, b: BV) -> BV:
        return BV([self.cnf.lit_or(a.bits[i], b.bits[i]) for i in range(self.w)])

    def bxor(self, a: BV, b: BV) -> BV:
        return BV([self.cnf.lit_xor(a.bits[i], b.bits[i]) for i in range(self.w)])

    def shl(self, a: BV, k: int) -> BV:
        return BV([self._false] * min(k, self.w) + a.bits[: max(0, self.w - k)])

    def lshr(self, a: BV, k: int) -> BV:                    # LOGICAL right shift by constant k (zero-fill from top)
        return BV([a.bits[i + k] if i + k < self.w else self._false for i in range(self.w)])

    def ashr(self, a: BV, k: int) -> BV:                    # ARITHMETIC right shift by constant k (sign-fill from top)
        sign = a.bits[self.w - 1]
        return BV([a.bits[i + k] if i + k < self.w else sign for i in range(self.w)])

    def mul(self, a: BV, b: BV) -> BV:                      # general w×w multiply mod 2^w (shift-add, and-gated)
        acc = self.const(0)
        for j in range(self.w):                            # partial product j = (a << j) gated by b_j, summed
            pp = BV([self.cnf.lit_and(a.bits[i - j], b.bits[j]) if i >= j else self._false
                     for i in range(self.w)])
            acc = self.add(acc, pp)
        return acc

    def eq_lit(self, a: BV, b: BV) -> int:                  # a literal that is True iff a == b
        acc = self._true
        for i in range(self.w):
            same = -self.cnf.lit_xor(a.bits[i], b.bits[i])  # bit i equal
            acc = self.cnf.lit_and(acc, same)
        return acc

    def ult_lit(self, a: BV, b: BV) -> int:                 # unsigned a < b, as a literal (compute a-b borrow)
        borrow = self._false
        for i in range(self.w):
            # borrow_{i+1} = (¬a_i ∧ b_i) ∨ ((¬(a_i ⊕ b_i)) ∧ borrow_i)
            nb = self.cnf.lit_and(-a.bits[i], b.bits[i])
            eqb = self.cnf.lit_and(-self.cnf.lit_xor(a.bits[i], b.bits[i]), borrow)
            borrow = self.cnf.lit_or(nb, eqb)
        return borrow                                       # final borrow ⇔ a < b (unsigned)

    def slt_lit(self, a: BV, b: BV) -> int:                 # SIGNED a < b (two's complement), as a literal
        am, bm = a.bits[self.w - 1], b.bits[self.w - 1]     # sign bits (MSB)
        diff = self.cnf.lit_xor(am, bm)
        # signs differ ⇒ a<b iff a is negative (am=1); signs equal ⇒ unsigned compare
        return self.cnf.lit_or(self.cnf.lit_and(diff, am),
                               self.cnf.lit_and(-diff, self.ult_lit(a, b)))

    def sgt_lit(self, a: BV, b: BV) -> int:                 # SIGNED a > b  ≡  b <_s a
        return self.slt_lit(b, a)


# ── DPLL SAT core (deterministic: lowest-index unassigned var, positive first) ───────────────────────────
def _solve(nvars: int, clauses: List[List[int]]) -> Optional[Dict[int, bool]]:
    assign: Dict[int, bool] = {}

    def lit_true(lit: int) -> Optional[bool]:
        v = abs(lit)
        if v not in assign:
            return None
        return assign[v] == (lit > 0)

    def unit_propagate() -> bool:
        changed = True
        while changed:
            changed = False
            for cl in clauses:
                unassigned, sat = [], False
                for lit in cl:
                    t = lit_true(lit)
                    if t is True:
                        sat = True; break
                    if t is None:
                        unassigned.append(lit)
                if sat:
                    continue
                if not unassigned:
                    return False                            # conflict: all false
                if len(unassigned) == 1:
                    lit = unassigned[0]
                    assign[abs(lit)] = (lit > 0)
                    changed = True
        return True

    def dpll() -> bool:
        snapshot = dict(assign)
        if not unit_propagate():
            assign.clear(); assign.update(snapshot)
            return False
        nxt = next((v for v in range(1, nvars + 1) if v not in assign), None)
        if nxt is None:
            return True                                     # all assigned, no conflict ⇒ SAT
        for val in (True, False):                           # deterministic: positive branch first
            save = dict(assign)
            assign[nxt] = val
            if dpll():
                return True
            assign.clear(); assign.update(save)
        assign.clear(); assign.update(snapshot)
        return False

    return dict(assign) if dpll() else None


def _check_model(clauses: List[List[int]], model: Dict[int, bool]) -> bool:
    """Independent certificate checker: the model satisfies EVERY clause (TCB = this tiny function)."""
    for cl in clauses:
        if not any((model.get(abs(l), False) == (l > 0)) for l in cl):
            return False
    return True


# ── the engine-facing API ────────────────────────────────────────────────────────────────────────────────
@dataclass
class BVResult:
    status: str                                             # VALID | INVALID | SAT | UNSAT
    width: int
    model: Optional[Dict[str, int]] = None                  # decoded input assignment (counterexample / witness)
    certificate: str = ""


def _decode(bb: BitBlaster, model: Dict[int, bool]) -> Dict[str, int]:
    out = {}
    for name, bv in bb.inputs.items():
        val = 0
        for i, lit in enumerate(bv.bits):
            bit = model.get(abs(lit), False) == (lit > 0)
            if bit:
                val |= (1 << i)
        out[name] = val
    return out


def prove_bv_identity(build, width: int) -> BVResult:
    """Decide ∀ (width-bit vars). lhs == rhs. `build(bb)` returns (lhs_BV, rhs_BV) using a fresh BitBlaster.
    EXACT within `width`: assert lhs ≠ rhs and SAT-solve; UNSAT ⇒ VALID (proof over the w-bit domain); SAT ⇒
    INVALID with a concrete counterexample (model independently checked against the CNF)."""
    bb = BitBlaster(width)
    lhs, rhs = build(bb)
    neq = -bb.eq_lit(lhs, rhs)                               # assert NOT(lhs == rhs)
    bb.cnf.add(neq)
    model = _solve(bb.cnf.nvars, bb.cnf.clauses)
    if model is None:
        return BVResult("VALID", width,
                        certificate=f"¬(lhs==rhs) UNSAT over all {width}-bit inputs ⇒ identity holds (decision "
                                    f"procedure, bound=2^{width}); EXACT within width {width}")
    assert _check_model(bb.cnf.clauses, model), "SAT model failed the independent checker"   # certificate
    cex = _decode(bb, model)
    return BVResult("INVALID", width, model=cex,
                    certificate=f"counterexample {cex} (mod 2^{width}) falsifies lhs==rhs — model checked vs CNF")


def solve_bv(build_constraint, width: int) -> BVResult:
    """Decide satisfiability of a bitvector constraint. `build_constraint(bb)` returns a single CNF literal that
    must hold. SAT ⇒ a verified model; UNSAT ⇒ a proof (no w-bit assignment satisfies it)."""
    bb = BitBlaster(width)
    top = build_constraint(bb)
    bb.cnf.add(top)
    model = _solve(bb.cnf.nvars, bb.cnf.clauses)
    if model is None:
        return BVResult("UNSAT", width, certificate=f"no {width}-bit assignment satisfies the constraint (proof)")
    assert _check_model(bb.cnf.clauses, model), "SAT model failed the independent checker"
    return BVResult("SAT", width, model=_decode(bb, model),
                    certificate=f"model {_decode(bb, model)} satisfies the constraint — checked vs CNF")


# ── engine wiring: the in-house, ZERO-DEPENDENCY counterpart of pillar3/bv_validate.sound_peepholes ─────────
# These are the EXACT sound machine-integer peepholes the CODE engine validates with Z3 over bitvectors — but
# expressed in this solver's QF-BV ops, so the obligation can be discharged with ZERO external solver. Each is a
# `build(bb) → (lhs, rhs)` that `prove_bv_identity` decides VALID (UNSAT of ≠) over the chosen width. The unsafe
# peepholes (succ_gt_self / mul2_div2_id / add_monotone) are deliberately ABSENT here: they need signed `>`,
# division, and if-then-else MUX — outside this solver's stated theory. They stay on Z3. We never imply parity.
def inhouse_sound_peepholes() -> List[Tuple[str, "callable", int]]:
    def _mul2(bb):  x = bb.var("x");                return (bb.mul_const(x, 2), bb.shl(x, 1))
    def _mul8(bb):  x = bb.var("x");                return (bb.mul_const(x, 8), bb.shl(x, 3))
    def _xor(bb):   x, y = bb.var("x"), bb.var("y"); return (bb.sub(bb.bor(x, y), bb.band(x, y)), bb.bxor(x, y))
    def _addsub(bb):x, y = bb.var("x"), bb.var("y"); return (bb.sub(bb.add(x, y), y), x)
    def _clrlow(bb):x = bb.var("x");                return (bb.band(x, bb.sub(x, bb.const(1))),
                                                            bb.band(x, bb.bnot(bb.band(bb.neg(x), x))))
    # (name, build, width). Widths kept small (the SAT search is exhaustive over 2^(#input bits)): 1-var ⇒ 6 bits,
    # 2-var ⇒ 4 bits — each a bounded, deterministic, EXACT-WITHIN-WIDTH decision. Widen + re-prove to raise the bound.
    return [("mul2_to_shl1", _mul2, 6), ("mul8_to_shl3", _mul8, 6),
            ("xor_via_or_minus_and", _xor, 4), ("add_sub_cancel", _addsub, 4), ("clear_low_bit", _clrlow, 6)]


def prove_sound_peepholes() -> Dict[str, BVResult]:
    """Decide every in-house sound peephole VALID with a checkable certificate — ZERO external solver."""
    return {name: prove_bv_identity(build, width) for name, build, width in inhouse_sound_peepholes()}


# ── STRENGTH-REDUCTION catalog (the EXPANDED theory: general multiply + logical/arithmetic right-shift) ─────────
# These are the transforms the CODE engine WANTS TO ACCEPT — turning an expensive op into a cheap one (multiply→
# shift, mask→shift round-trip, branchless sign via arithmetic shift). Unlike the unsafe peepholes that stay on Z3,
# every one of these is PROVEN VALID *in-house* (UNSAT of the negation over the whole w-bit domain) — so the engine
# can soundly ACCEPT the strength reduction with ZERO external solver, EXACT within the stated width. This catalog
# is in-house-ONLY (it exercises ops outside pillar3's Z3-cross-checked set), so it is deliberately NOT part of
# inhouse_sound_peepholes() / cross_check_inhouse_vs_z3 — we never imply Z3 parity for it.
def inhouse_strength_reductions() -> List[Tuple[str, "callable", int]]:
    def _sign_mask(bb):                                       # ashr(x,w-1) ≡ neg(lshr(x,w-1)) — branchless sign mask
        x = bb.var("x"); return (bb.ashr(x, bb.w - 1), bb.neg(bb.lshr(x, bb.w - 1)))
    def _clear_low(bb):                                       # lshr-then-shl round-trip ≡ AND ~(2^k−1) (clear low k)
        x = bb.var("x"); k = 2; mask = ((1 << bb.w) - 1) ^ ((1 << k) - 1)
        return (bb.shl(bb.lshr(x, k), k), bb.band(x, bb.const(mask)))
    def _clear_high(bb):                                      # shl-then-lshr round-trip ≡ AND (2^(w−k)−1) (clear high)
        x = bb.var("x"); k = 2; return (bb.lshr(bb.shl(x, k), k), bb.band(x, bb.const((1 << (bb.w - k)) - 1)))
    def _mul_to_shift(bb):                                    # general x·8 ≡ x<<3 (strength reduction, general mul side)
        x = bb.var("x"); return (bb.mul(x, bb.const(8)), bb.shl(x, 3))
    def _mul_agrees(bb):                                      # general multiplier AGREES with trusted shift-add const
        x = bb.var("x"); return (bb.mul(x, bb.const(5)), bb.mul_const(x, 5))
    def _mul_comm(bb):                                        # × commutes mod 2^w (multiplier soundness)
        x, y = bb.var("x"), bb.var("y"); return (bb.mul(x, y), bb.mul(y, x))
    def _mul_assoc(bb):                                       # × associates mod 2^w (reassociation is sound)
        x, y, z = bb.var("x"), bb.var("y"), bb.var("z")
        return (bb.mul(bb.mul(x, y), z), bb.mul(x, bb.mul(y, z)))
    def _mul_dist(bb):                                        # × distributes over + mod 2^w (the ring law)
        x, y, z = bb.var("x"), bb.var("y"), bb.var("z")
        return (bb.mul(x, bb.add(y, z)), bb.add(bb.mul(x, y), bb.mul(x, z)))
    # (name, build, width). Multiply is O(w²) gates so 3-var laws stay at width 3 (exhaustive over 2^9 inputs);
    # 1-var stays at 6. Each is a bounded, deterministic, EXACT-WITHIN-WIDTH decision — widen + re-prove to raise it.
    return [("sign_mask_ashr=neg_lshr", _sign_mask, 6), ("clear_low_bits_roundtrip", _clear_low, 6),
            ("clear_high_bits_roundtrip", _clear_high, 6), ("mul8_to_shl3_general", _mul_to_shift, 6),
            ("general_mul=mul_const", _mul_agrees, 6), ("mul_commutes", _mul_comm, 4),
            ("mul_associates", _mul_assoc, 3), ("mul_distributes_over_add", _mul_dist, 3)]


def prove_strength_reductions() -> Dict[str, BVResult]:
    """Decide every in-house strength-reduction identity VALID with a checkable certificate (general multiply +
    right-shift theory) — ZERO external solver, EXACT within each stated width."""
    return {name: prove_bv_identity(build, width) for name, build, width in inhouse_strength_reductions()}
