"""
v34 STAGE 4 — ε₀ ordinal-descent kernel (CNF ordinals < ε₀), dependency-0. INSURANCE for general recursion.
=============================================================================================================
★ This does NOT extend fold coverage. ★ STAGE 1 already proves fold's ∀n at PRA (ω^ω) strength — ε₀ never
arises for C-finite/holonomic/polynomial folds. This kernel is insurance for ARBITRARY user recursion whose
termination needs transfinite induction up to ε₀ (Goodstein / Hydra / Ackermann-style nested recursion).

Cantor Normal Form below ε₀:  α = ω^{e₁}·c₁ + … + ω^{eₖ}·cₖ  with e₁ > e₂ > … ≥ 0 (each eᵢ itself a CNF
ordinal) and cᵢ ≥ 1. Zero = empty sum. Every FINITE CNF expression is < ε₀ (ε₀ needs an infinite ω-tower).

The kernel (the whole TCB for the ε₀ claim) is just: CNF well-formedness + comparison + strict-descent check.
A strictly decreasing sequence of ordinals is finite (well-foundedness) ⇒ the annotated derivation terminates.
The expensive part (FINDING the ordinal annotation via size-change / RPO) is OFFLINE; the runtime kernel only
CHECKS a supplied witness (cheap).

★ TCB honesty (rule 7): even this "small kernel" trusts the Python runtime, the integer arithmetic, and the
hardware. Gödel's 2nd incompleteness theorem: this kernel cannot prove ITS OWN consistency (a system can
prove Con of weaker systems, never of itself). Stated, not hidden.
★ We label a recursion ε₀ ONLY when this kernel accepts its descent witness — never otherwise (rule 5/10). ★
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class Ord:
    """CNF ordinal < ε₀: terms = tuple of (exponent: Ord, coeff: int), exponents strictly DECREASING."""
    terms: Tuple[Tuple["Ord", int], ...] = ()

    def is_zero(self) -> bool:
        return len(self.terms) == 0


def zero() -> Ord:
    return Ord(())


def nat(n: int) -> Ord:
    """finite ordinal n = ω^0 · n."""
    return Ord(((zero(), n),)) if n > 0 else zero()


def omega() -> Ord:
    """ω = ω^1 · 1  (exponent is the ordinal 1 = ω^0·1)."""
    return Ord(((nat(1), 1),))


def omega_power(exp: Ord, coeff: int = 1) -> Ord:
    return Ord(((exp, coeff),)) if coeff > 0 else zero()


def compare(a: Ord, b: Ord) -> int:
    """-1 if a<b, 0 if a==b, 1 if a>b. Lexicographic on (exponent, coeff) terms; longer tail ⇒ larger."""
    for (ea, ca), (eb, cb) in zip(a.terms, b.terms):
        c = compare(ea, eb)
        if c != 0:
            return c
        if ca != cb:
            return -1 if ca < cb else 1
    if len(a.terms) != len(b.terms):
        return -1 if len(a.terms) < len(b.terms) else 1
    return 0


def validate(a: Ord) -> bool:
    """Well-formed CNF < ε₀: exponents strictly decreasing, coeffs ≥ 1, each exponent itself valid (finite
    depth ⇒ < ε₀)."""
    prev = None
    for (e, c) in a.terms:
        if c < 1 or not validate(e):
            return False
        if prev is not None and compare(e, prev) >= 0:    # exponents must strictly decrease
            return False
        prev = e
    return True


def add(a: Ord, b: Ord) -> Ord:
    """Natural ordinal sum in CNF (a + b): drop a-terms with exponent < b's leading exponent, then append b."""
    if b.is_zero():
        return a
    if a.is_zero():
        return b
    lead_b = b.terms[0][0]
    kept = [(e, c) for (e, c) in a.terms if compare(e, lead_b) > 0]
    # if a's last kept exponent equals b's lead, merge coeffs
    if kept and compare(kept[-1][0], lead_b) == 0:
        kept[-1] = (lead_b, kept[-1][1] + b.terms[0][1])
        return Ord(tuple(kept) + b.terms[1:])
    return Ord(tuple(kept) + b.terms)


# ─────────────────────────────────────────────────────── the kernel: descent check (the whole TCB)
def check_descent(witness: List[Ord]) -> bool:
    """THE KERNEL: accept iff every ordinal is a valid CNF < ε₀ AND the sequence strictly DECREASES. A strict
    descent in a well-founded order is finite ⇒ the annotated computation terminates. (TCB = this + compare +
    validate.)"""
    if not all(validate(o) for o in witness):
        return False
    return all(compare(witness[i + 1], witness[i]) < 0 for i in range(len(witness) - 1))


def lex_measure_to_ordinal(measure: Tuple[int, ...]) -> Ord:
    """Map a lexicographic termination measure (m₀,…,m_{k-1}) to the ordinal ω^{k-1}·m₀ + … + ω^0·m_{k-1}.
    A lexicographically-DECREASING measure ⇒ a strictly DECREASING ordinal (the size-change → ordinal bridge)."""
    k = len(measure)
    terms = [(nat(k - 1 - i), m) for i, m in enumerate(measure) if m > 0]
    return Ord(tuple(terms))


def size_change_witness(measures: List[Tuple[int, ...]]) -> List[Ord]:
    """OFFLINE (potentially expensive size-change/RPO analysis, abstracted here): turn a sequence of
    termination measures into ordinal annotations. The runtime kernel then only CHECKS descent (cheap)."""
    return [lex_measure_to_ordinal(m) for m in measures]


def tcb_line_count() -> int:
    """Honest TCB size: lines of the kernel (validate + compare + check_descent + Ord) in THIS file."""
    import inspect
    src = "".join(inspect.getsource(f) for f in (Ord, compare, validate, check_descent))
    return sum(1 for ln in src.splitlines() if ln.strip() and not ln.strip().startswith("#"))


GODEL_NOTE = ("Gödel 2nd incompleteness: this kernel cannot prove its OWN consistency (only that of weaker "
              "systems). It also trusts the Python runtime + integer arithmetic + hardware (TCB).")
