"""
POST-CONSOLIDATION PHASE 1e — SFA: SYMBOLIC FINITE AUTOMATA (predicate-guarded, infinite-alphabet decisions).
================================================================================================================
A Symbolic Finite Automaton labels transitions by PREDICATES over an (infinite) alphabet — here ℤ with LINEAR-
INTEGER-ARITHMETIC guards — instead of concrete symbols. Emptiness, equivalence, and minimization stay DECIDABLE
exactly when the guard theory is decidable. Equivalence is decided by SYMBOLIC BISIMULATION: explore product pairs,
partition the alphabet by the two states' guards, and recurse on each SATISFIABLE region (z3 over LIA); a reachable
pair where one side accepts and the other rejects is a distinguishing witness.

★ THE HONEST ADJUDICATION (four gates — this candidate DEMOTES):
  gate 2 (z3-closed): ✓ — every guard-region satisfiability check is z3 over LIA; the decision is exact.
  gate 3 (asymptotic): ✓ — the symbolic product is |A|·|B| pairs regardless of the (infinite) alphabet size — an
      O(N)→O(1)-in-alphabet collapse (one symbolic region replaces unboundedly-many concrete symbols).
  gate 4 (dependency-free): ✓ — z3 (heavy, lazy); the bisimulation is in-repo.
  gate 1 (DISTINCT IN KIND): ✗ — the minimal SFA / the equivalence decision is a CANONICAL automaton — a COMPLETE
      INVARIANT of the (symbolic) language, exactly M9's kind (Myhill–Nerode / the minimal DFA via L*). SFA widens
      the ALPHABET (predicates vs concrete symbols) but emits the same KIND of certificate. ⇒ DEMOTE: a FACE of M9
      (parent mechanism 9).

Decidable island: LIA (Presburger) guards. The UNDECIDABLE boundary — nonlinear-integer (x·x) guards (Hilbert-10th)
— ⇒ DECLINE (never a guessed decision). Precision 1.0: non-equivalent SFAs are correctly DISTINGUISHED (never
falsely merged), with a concrete distinguishing witness.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import kernel_verdict as KV

PARENT_MECHANISM = 9   # the minimal SFA / equivalence decision is a complete invariant — M9's kind
DEAD = -1              # the implicit reject sink (any symbol with no matching guard)


def _guard_expr(guard: str, x):
    """Parse a LIA guard string over the symbol variable x into a z3 BoolRef. Boolean combinators: & | ~."""
    return eval(guard, {"__builtins__": {}}, {"x": x})   # noqa: S307 — author-provided in-repo specs only


def _is_nonlinear(guard: str) -> bool:
    g = guard.replace(" ", "")
    return bool(re.search(r"x\*x", g) or "x**" in g or re.search(r"\*x\*", g))


def _theory_decidable(*sfas) -> bool:
    for sfa in sfas:
        for (_, g, _) in sfa.get("trans", []):
            if _is_nonlinear(g):
                return False
    return True


def _successors(sfa, q) -> List[Tuple[str, int]]:
    if q == DEAD:
        return []
    return [(g, d) for (s, g, d) in sfa["trans"] if s == q]


def sfa_equivalent(A: dict, B: dict) -> Tuple[Optional[bool], Optional[Tuple[int, int]]]:
    """Decide L(A)=L(B) by symbolic bisimulation over LIA guards. Returns (True, None) if equivalent, (False, pair)
    with a distinguishing reachable pair, or (None, None) if z3 is unavailable. Assumes deterministic guards out of
    each state (a guard implies the negation of its siblings); the implicit DEAD sink handles uncovered symbols."""
    try:
        import z3
    except Exception:  # noqa: BLE001
        return None, None
    x = z3.Int("x")
    fA, fB = set(A["finals"]), set(B["finals"])

    def sat(pos: List[str], neg: List[str]) -> bool:
        s = z3.Solver()
        for g in pos:
            s.add(_guard_expr(g, x))
        for g in neg:
            s.add(z3.Not(_guard_expr(g, x)))
        return s.check() == z3.sat

    seen = set()
    stack = [(A["init"], B["init"])]
    while stack:
        qa, qb = stack.pop()
        if (qa, qb) in seen:
            continue
        seen.add((qa, qb))
        if ((qa in fA) if qa != DEAD else False) != ((qb in fB) if qb != DEAD else False):
            return False, (qa, qb)                              # a reachable pair disagreeing on acceptance
        sa, sb = _successors(A, qa), _successors(B, qb)
        for (ga, da) in sa + [(None, DEAD)]:
            for (gb, db) in sb + [(None, DEAD)]:
                pos, neg = [], []
                if ga is None:
                    neg += [g for g, _ in sa]                   # region: A makes no move (→ DEAD)
                else:
                    pos.append(ga)
                if gb is None:
                    neg += [g for g, _ in sb]
                else:
                    pos.append(gb)
                if (pos or neg) and sat(pos, neg):
                    stack.append((da, db))
    return True, None


def sfa_grade(spec: dict) -> KV.Verdict:
    """Decide SFA language equivalence (a complete-invariant decision, M9's kind). spec = {A: sfa, B: sfa}. EXACT
    (equivalent OR not — a complete decision) with the symbolic-bisimulation certificate; nonlinear-integer guards
    (undecidable theory) ⇒ DECLINE. DEMOTES to a FACE of M9."""
    if not (isinstance(spec, dict) and "A" in spec and "B" in spec):
        return KV.decline("sfa: need {A: sfa, B: sfa} with sfa = {states, init, finals, trans:[(src, guard, dst)]}", "mech_sfa")
    A, B = spec["A"], spec["B"]
    if not _theory_decidable(A, B):
        return KV.decline("sfa: nonlinear-integer (x·x) guards — the guard theory is UNDECIDABLE (Hilbert-10th) ⇒ "
                          "DECLINE (the LIA island IS decided; this boundary is not)", "mech_sfa")
    equiv, witness = sfa_equivalent(A, B)
    if equiv is None:
        return KV.decline("sfa: z3 unavailable — cannot decide guard-region satisfiability ⇒ DECLINE", "mech_sfa")
    cert = KV.Cert(KV.EXACT, "sfa_bisimulation", passed=True,
                   check_cost="symbolic bisimulation over the product (z3 LIA guard-region satisfiability); "
                              f"{'equivalent' if equiv else 'distinguished at pair %s' % (witness,)}",
                   detail=f"L(A) {'=' if equiv else '≠'} L(B) decided by symbolic bisimulation over LIA guards — a "
                          "canonical / complete-invariant decision over an infinite alphabet (FACE of M9; SFA widens "
                          "the alphabet to predicates but emits M9's kind of certificate)")
    return KV.exact({"parent_mechanism": PARENT_MECHANISM, "face": "symbolic_finite_automata", "equivalent": equiv,
                     "distinguishing_pair": witness}, "mech_sfa",
                    "SFA equivalence (symbolic bisimulation, LIA) → M9 face", cert)


def adjudication() -> dict:
    """Honest gate-by-gate: passes z3-closed/asymptotic/dependency-free; FAILS distinct-in-kind (the minimal SFA /
    equivalence decision is a complete invariant — M9's kind) ⇒ DEMOTE to a FACE of M9."""
    return {"candidate": "SFA (symbolic finite automata)", "z3_closed": True, "asymptotic": True,
            "dependency_free": True, "distinct_in_kind": False, "verdict": "DEMOTE → FACE of M9",
            "reason": "the minimal SFA / the equivalence decision is a canonical automaton — a COMPLETE INVARIANT of "
                      "the language (Myhill–Nerode / minimal DFA via L*), exactly M9's kind; SFA widens the alphabet "
                      "to predicates but emits the same certificate kind"}
