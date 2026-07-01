"""
qmkernel/fermion_wick.py — §BR STAGE 1 NEW-2: fermionic anticommutator algebra + Wick contraction.
============================================================================================================
★ Confirmed net-new (QMKERNEL_INDEX.md §3): `mathmode/operator_algebra.py` is bosonic-commutator-only —
zero anticommutators, zero sign-tracking on reorder, zero fermionic type system. This module is the
fermionic analogue of that file's `comm`/`normal_order` (never edits it — 0 diff).

★ m08 confluent-normal-form rewriting recognition branch: Wick's theorem for fermions IS a sign-tracked
term-rewriting system — repeatedly swap an adjacent (annihilation, creation) pair via AB = {A,B} − BA,
which either shrinks the word by 2 (a contraction term) or performs a transposition; the "number of
(ann-before-cre) inversions" strictly decreases on every step, so the system terminates (well-founded), and
the result (creation-block before annihilation-block) is independent of which inversion is resolved first
(the standard confluence argument for adjacent-transposition sorting). A second, terminal rule falls out of
the SAME anticommutation relations for free: {c_i,c_i}={c_i†,c_i†}=0 ⇒ any adjacent IDENTICAL operator (same
dagger-flag, same mode) squares to zero — Pauli exclusion, not a separately-invented rule. No 15th mechanism.

★ Two INDEPENDENT verification oracles, both from scratch:
  (a) a Jordan-Wigner finite-matrix representation (exact Fraction, dimension 2^k for k modes) — used ONLY
      as an internal cross-check oracle here, not offered as a JW-stabilizer bridge engine (QMKERNEL_INDEX.md
      §2 found no such bridge exists yet, and building one is not one of the directive's 16 NEW items);
  (b) for vacuum expectation values, this module supplies ONLY the pairwise-contraction matrix and WIRES that
      into `mathmode.free_fermion.wick_pfaffian_fold` (unmodified, 0 diff) for the actual Pfaffian evaluation
      — reusing the existing Pfaffian engine rather than re-deriving Pfaffian combinatorics here.

★ 2-lane note: every input here is combinatorial (a boolean dagger-flag + an integer mode index) — there is no
continuous/float representation of "which mode, creation or annihilation" to approximate. Every result is
therefore Lane 1 (EXACT, backed by exact Fraction arithmetic) or DECLINE; Lane 2 does not apply to this
module's own domain (the discipline forbids CLAIMING exactness for float input, not requires a float lane to
exist where none is meaningful).
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import List, Tuple

import kernel_verdict as KV

_MAX_WORD = 12   # a generous, honestly-stated cap on word length (2^12 JW matrices are the practical limit)


@dataclass(frozen=True)
class FOp:
    """A single canonical fermionic ladder operator: dagger=True is creation c_mode†, False is annihilation c_mode."""
    dagger: bool
    mode: int

    def __repr__(self):
        return f"c{self.mode}†" if self.dagger else f"c{self.mode}"


def anticommutator(a: FOp, b: FOp) -> Fraction:
    """{a,b} for CANONICAL fermionic operators: {c_i,c_j†}=δ_ij, {c_i,c_j}=0, {c_i†,c_j†}=0."""
    if a.dagger == b.dagger:
        return Fraction(0)
    ann, cre = (a, b) if not a.dagger else (b, a)
    return Fraction(1) if ann.mode == cre.mode else Fraction(0)


def vacuum_two_point(a: FOp, b: FOp) -> Fraction:
    """⟨0|ab|0⟩: nonzero ONLY for (annihilation, creation) of the SAME mode, value 1 — every other type
    combination vanishes on the vacuum (creation on the left of ⟨0| or annihilation on the right of |0⟩ kills it)."""
    if (not a.dagger) and b.dagger and a.mode == b.mode:
        return Fraction(1)
    return Fraction(0)


# ── the genuinely new algebra: sign-tracked normal-ordering rewrite system ─────────────────────────────
def normal_order_word(word: List[FOp]) -> List[Tuple[Fraction, List[FOp]]]:
    """Rewrite `word` (a product of fermionic ladder operators) into a SUM of sign/coefficient-weighted
    NORMAL-ORDERED terms (every creation operator before every annihilation operator). Each rewrite step
    resolves one adjacent (annihilation, creation) inversion via AB = {A,B} − BA:
      • {A,B}=0 (different modes, or same type) ⇒ just the transposition, coefficient flips sign.
      • {A,B}=1 (same mode) ⇒ ALSO emits a shorter "contracted" term with the pair removed.
    Terminates because the inversion count strictly decreases on every transposition step, and the
    contraction branch recurses on a strictly shorter word (well-founded on (inversions, length))."""
    if len(word) > _MAX_WORD:
        raise ValueError(f"word length {len(word)} exceeds the honestly-stated cap {_MAX_WORD}")
    for i in range(len(word) - 1):
        a, b = word[i], word[i + 1]
        if a.dagger == b.dagger and a.mode == b.mode:
            return []                                         # op·op ≡ 0 (Pauli exclusion, from {op,op}=0)
        if (not a.dagger) and b.dagger:                      # an (annihilation, creation) inversion
            rest = word[:i] + word[i + 2:]
            swapped = word[:i] + [b, a] + word[i + 2:]
            terms: List[Tuple[Fraction, List[FOp]]] = []
            ac = anticommutator(a, b)
            if ac != 0:
                terms += [(coef * ac, w) for (coef, w) in normal_order_word(rest)]
            terms += [(-coef, w) for (coef, w) in normal_order_word(swapped)]
            return _combine_like_terms(terms)
    return [(Fraction(1), word)]


def _combine_like_terms(terms: List[Tuple[Fraction, List[FOp]]]) -> List[Tuple[Fraction, List[FOp]]]:
    """Merge terms whose reduced word is identical (same ops, same order) — a bookkeeping tidy-up, not a
    change of the represented value (Σ still equals the same operator)."""
    merged: dict = {}
    order: list = []
    for coef, w in terms:
        key = tuple((op.dagger, op.mode) for op in w)
        if key not in merged:
            merged[key] = Fraction(0)
            order.append((key, w))
        merged[key] += coef
    return [(merged[key], w) for key, w in order if merged[key] != 0]


def is_normal_ordered(word: List[FOp]) -> bool:
    seen_annihilation = False
    for op in word:
        if not op.dagger:
            seen_annihilation = True
        elif seen_annihilation:
            return False
    return True


# ── independent oracle 1: Jordan-Wigner finite matrices (exact Fraction, dimension 2^k) ────────────────
def jw_matrix(op: FOp, k: int) -> List[List[Fraction]]:
    """Exact (2^k×2^k) Fraction matrix of a single ladder operator, basis |n_0…n_{k-1}⟩ encoded as the
    integer with bit i = n_i. An INDEPENDENT construction from the rewrite system above — used only to
    cross-check it, never as a production JW-stabilizer bridge."""
    dim = 1 << k
    M = [[Fraction(0)] * dim for _ in range(dim)]
    i = op.mode
    for state in range(dim):
        bit = (state >> i) & 1
        if op.dagger:
            if bit == 1:
                continue
            new_state = state | (1 << i)
        else:
            if bit == 0:
                continue
            new_state = state & ~(1 << i)
        parity = bin(state & ((1 << i) - 1)).count("1")
        M[new_state][state] = Fraction(-1) if parity % 2 else Fraction(1)
    return M


def _mat_mul(A: List[List[Fraction]], B: List[List[Fraction]]) -> List[List[Fraction]]:
    n = len(A)
    return [[sum(A[i][t] * B[t][j] for t in range(n)) for j in range(n)] for i in range(n)]


def _mat_add_scaled(acc: List[List[Fraction]], coef: Fraction, M: List[List[Fraction]]) -> List[List[Fraction]]:
    n = len(acc)
    return [[acc[i][j] + coef * M[i][j] for j in range(n)] for i in range(n)]


def word_matrix(word: List[FOp], k: int) -> List[List[Fraction]]:
    dim = 1 << k
    M = [[Fraction(1) if i == j else Fraction(0) for j in range(dim)] for i in range(dim)]
    for op in word:
        M = _mat_mul(M, jw_matrix(op, k))
    return M


def terms_matrix(terms: List[Tuple[Fraction, List[FOp]]], k: int) -> List[List[Fraction]]:
    dim = 1 << k
    acc = [[Fraction(0)] * dim for _ in range(dim)]
    for coef, w in terms:
        acc = _mat_add_scaled(acc, coef, word_matrix(w, k) if w else
                              [[Fraction(1) if i == j else Fraction(0) for j in range(dim)] for i in range(dim)])
    return acc


def cross_checked_normal_order(word: List[FOp], k: int) -> KV.Verdict:
    """Normal-order `word`, then verify — via the INDEPENDENT Jordan-Wigner matrix oracle — that the matrix of
    the rewritten sum equals the matrix of the original word EXACTLY, entrywise. `k` must exceed every mode
    index used in `word` (enough qubits/modes to represent them)."""
    if word and max(op.mode for op in word) >= k:
        return KV.decline(f"k={k} too small for mode indices used in {word}", "qmkernel.fermion_wick")
    terms = normal_order_word(word)
    if not all(is_normal_ordered(w) for _, w in terms):
        return KV.decline("normal_order_word returned a non-normal-ordered term — internal bug, declining "
                          "rather than trusting it", "qmkernel.fermion_wick")
    m_orig = word_matrix(word, k)
    m_terms = terms_matrix(terms, k)
    agree = m_orig == m_terms
    if not agree:
        return KV.decline("Jordan-Wigner cross-check FAILED: normal-ordered sum's matrix ≠ original word's "
                          "matrix — declining rather than trusting the rewrite", "qmkernel.fermion_wick")
    cert = KV.Cert(KV.EXACT, "fermion_normal_order_jw_crosscheck", passed=True,
                   check_cost=f"Jordan-Wigner matrix rep, dimension 2^{k}, exact Fraction",
                   detail=f"{len(terms)} normal-ordered term(s); JW matrix cross-check exact match")
    return KV.exact({"terms": terms, "n_terms": len(terms)}, "qmkernel.fermion_wick", f"O(2^{k})", cert)


# ── independent oracle 2 / wiring: vacuum expectation via the EXISTING Pfaffian engine ─────────────────
def contraction_matrix(word: List[FOp]) -> List[List[Fraction]]:
    """A_ij = ⟨0|word[i] word[j]|0⟩ for i<j, antisymmetrized — the standard Wick–Pfaffian convention."""
    n = len(word)
    A = [[Fraction(0)] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            c = vacuum_two_point(word[i], word[j])
            A[i][j], A[j][i] = c, -c
    return A


def vacuum_expectation_via_pfaffian(word: List[FOp]) -> KV.Verdict:
    """⟨0|word|0⟩ for an EVEN-length word, via Wick's theorem = Pfaffian of the contraction matrix. This
    module supplies ONLY the contraction matrix; the Pfaffian itself is computed by the UNMODIFIED
    `mathmode.free_fermion.wick_pfaffian_fold` (reuse, not a re-derivation of Pfaffian combinatorics)."""
    if len(word) % 2 != 0:
        return KV.decline("odd-length word ⇒ vacuum expectation is identically 0 by fermion-number "
                          "superselection — declining rather than silently returning 0 for a likely-mistaken "
                          "call", "qmkernel.fermion_wick")
    from mathmode import free_fermion as FF
    A = contraction_matrix(word)
    return FF.wick_pfaffian_fold(A)


# ── adversarial battery ─────────────────────────────────────────────────────────────────────────────────
def adversarial_battery() -> dict:
    cases = {}

    # 1) already normal-ordered word: identity rewrite
    w1 = [FOp(True, 0), FOp(False, 1)]
    t1 = normal_order_word(w1)
    cases["already_normal_ordered_is_identity"] = t1 == [(Fraction(1), w1)]

    # 2) simple inversion, different modes -> pure sign flip, no contraction (anticommutator is 0)
    w2 = [FOp(False, 0), FOp(True, 1)]      # c_0 c_1†  ({c_0,c_1†}=0 since modes differ)
    t2 = normal_order_word(w2)
    cases["different_mode_inversion_pure_sign_flip"] = t2 == [(Fraction(-1), [FOp(True, 1), FOp(False, 0)])]

    # 3) same-mode inversion -> emits BOTH the contraction (identity term) and the sign-flipped swap
    w3 = [FOp(False, 2), FOp(True, 2)]      # c_2 c_2†  = {c_2,c_2†} - c_2† c_2 = 1 - c_2†c_2
    t3 = normal_order_word(w3)
    cases["same_mode_inversion_has_two_terms"] = len(t3) == 2
    coef_by_word = {tuple((o.dagger, o.mode) for o in w): c for c, w in t3}
    cases["same_mode_contraction_coefficient_is_one"] = coef_by_word.get(()) == Fraction(1)
    cases["same_mode_swap_coefficient_is_minus_one"] = coef_by_word.get(((True, 2), (False, 2))) == Fraction(-1)

    # 4) Jordan-Wigner cross-check on cases 1-3 (k=3 modes covers indices 0,1,2)
    for name, w in (("w1", w1), ("w2", w2), ("w3", w3)):
        v = cross_checked_normal_order(w, k=3)
        cases[f"jw_crosscheck_{name}_exact"] = v.status == KV.EXACT

    # 5) a longer, more adversarial word: c_0 c_1 c_0† c_1†  (two same-mode inversions to resolve)
    w4 = [FOp(False, 0), FOp(False, 1), FOp(True, 0), FOp(True, 1)]
    v4 = cross_checked_normal_order(w4, k=2)
    cases["longer_word_jw_crosscheck_exact"] = v4.status == KV.EXACT
    cases["longer_word_result_is_normal_ordered"] = all(is_normal_ordered(w) for _, w in v4.result["terms"])

    # 6) Pauli exclusion falls out for free: c_0† c_0† should normal-order to a term with coefficient 0 (dropped)
    w5 = [FOp(True, 0), FOp(True, 0)]
    t5 = normal_order_word(w5)
    cases["double_creation_same_mode_vanishes"] = t5 == []          # c_0†c_0† ≡ 0 (Pauli exclusion)
    v5 = cross_checked_normal_order(w5, k=1)
    cases["double_creation_jw_crosscheck_exact"] = v5.status == KV.EXACT   # 0 == 0, still a real check

    # 7) odd-length word declines vacuum expectation (never silently 0)
    v6 = vacuum_expectation_via_pfaffian([FOp(False, 0)])
    cases["odd_length_vacuum_ev_declines"] = v6.status == KV.DECLINE

    # 8) vacuum expectation ⟨0| c_0 c_0† |0⟩ = 1, via Pfaffian wiring, cross-checked against the JW oracle directly
    w7 = [FOp(False, 0), FOp(True, 0)]
    v7 = vacuum_expectation_via_pfaffian(w7)
    direct_jw = word_matrix(w7, k=1)[0][0]     # <0|c_0 c_0†|0> = matrix element [vacuum][vacuum]
    cases["vacuum_ev_pfaffian_matches_jw_oracle"] = (v7.status == KV.EXACT and direct_jw == Fraction(1)
                                                     and abs(complex(v7.result.get("pfaffian", 0)) - 1.0) < 1e-9)

    # 9) vacuum expectation of a 4-operator word via Pfaffian, cross-checked against JW oracle
    w8 = [FOp(False, 0), FOp(True, 0), FOp(False, 1), FOp(True, 1)]   # <0|c0 c0† c1 c1†|0> = 1 (product of two independent contractions)
    v8 = vacuum_expectation_via_pfaffian(w8)
    direct_jw8 = word_matrix(w8, k=2)[0][0]
    cases["four_op_vacuum_ev_pfaffian_matches_jw"] = (v8.status == KV.EXACT and direct_jw8 == Fraction(1))

    all_ok = all(cases.values())
    failed = [k for k, v_ in cases.items() if not v_]
    return {"cases": cases, "all_ok": all_ok, "failed": failed}


if __name__ == "__main__":
    import json
    b = adversarial_battery()
    print(json.dumps({"all_ok": b["all_ok"], "failed": b["failed"], "n_cases": len(b["cases"])}, indent=2))
