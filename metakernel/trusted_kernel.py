"""
§BQ NEW-1 — the unified witness-predicate contract + the one genuinely new, small, auditable kernel.
======================================================================================================
★ Research finding this module acts on: our existing CHC independent re-verification, fast_certificates
(Freivalds/Schwartz-Zippel), IC3 "never false SAFE", and Farkas/SOS are ALL already instances of the
Necula/Shankar "proof-carrying code" / kernel-of-truth pattern (certifying algorithms: propose cheaply,
verify a WITNESS independently and cheaply). None of that is re-proposed or rewritten here — see
METAUPGRADE_INDEX.md. What was missing: those checks are scattered, and the CHC case re-verifies using
z3 itself (a fresh z3.Solver()), so a z3 bug class could defeat both the synthesis AND the "independent"
re-check. This module is the missing piece: ONE small, textually-auditable witness contract that several
engines can present a certificate against, PLUS — for the fragment where it's actually possible — a
genuinely independent decision procedure that does not call z3 at all.

PART A (below) — thin re-exports. SOS (`sos_cert.py`) and Farkas/LP (`newengine/farkas.py`) are ALREADY
pure-algebraic, zero-z3, exact-rational checkers; this just lifts their output into the same `KV.Cert`
shape so callers can treat "matrix identity" / "Farkas certificate" / "SOS Gram" / "LP KKT" uniformly.
Zero lines of new math for those three — reuse, not reinvention (TCB minimization: importing one audited
checker beats writing a second, possibly-divergent one).

PART B — a brand-new, from-scratch independent matrix-power check for C-finite witnesses (the directive's
own example: "C-finite = matrix identity"). This does NOT import cfinite.py; it is a separate ~15-line
implementation, so an agreement between it and cfinite.py's own companion_nth is evidence from TWO
independently-written code paths, not one path checking itself twice.

PART C — the actual new decision procedure: a complete propositional DPLL (SAT/UNSAT, zero deps) and a
ground equality-with-uninterpreted-functions (EUF) congruence-closure consistency check (Union-Find +
congruence fixpoint, zero deps), combined into DPLL(EUF). This is the "checker simpler than solver"
deliverable: it decides exactly the fragment of first-order logic with no arithmetic (Booleans + ground
equality/uninterpreted functions) — a fragment where a textually tiny, fully-auditable program is a
COMPLETE decision procedure, so trusting it is strictly better (smaller TCB) than trusting z3 for that
fragment. Used by metakernel/chc_kernel_bridge.py to remove z3 from the TCB for CHC instances whose Horn
verification conditions fall in this fragment; everything outside the fragment is unaffected (DECLINE-to-
classify, not a guess) and falls back to the unchanged chc_solve.chc_grade().

★ Boundary discipline (per the directive): this kernel NEVER attempts non-stably-infinite theory
combination and NEVER runs an unbounded quantifier-instantiation loop — those are Stage 3 concerns (NEW-7/
NEW-8) with their own explicit hard guards. Here there is no MBQI, no quantifiers, no combination beyond
EUF+propositional — by construction, not by a runtime check, so there is nothing to diverge.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import kernel_verdict as KV

Term = Union[str, Tuple[str, Tuple["Term", ...]]]     # an atom name, or (func_name, (arg, ...)) recursively
Literal = int                                          # nonzero int; +v means var v TRUE, -v means FALSE
Clause = List[Literal]


def mkfun(name: str, *args: Term) -> Term:
    """Build a ground uninterpreted-function application term — the only term constructor callers need."""
    return (name, tuple(args))


# ============================================================================================================
# PART A — thin witness-contract wrappers around ALREADY-minimal-TCB engines. 0 new math; pure re-export.
# ============================================================================================================

def witness_sos(expr, Q, basis) -> KV.Cert:
    """Wrap sos_cert's already-exact (zero-z3, zero-float) Gram-PSD + polynomial-identity check."""
    import sos_cert
    ok = bool(sos_cert.verify_sos(expr, Q, basis))
    return KV.Cert(KV.EXACT if ok else KV.DECLINE, "sos_gram_witness", passed=ok,
                   check_cost="O(n^3) charpoly+Sturm (sos_cert.verify_sos, unmodified)",
                   detail="zᵀQz≡p (exact) ∧ Q⪰0 (exact Sturm root count)" if ok else "Gram identity or PSD check failed")


def witness_farkas(A, b, y) -> KV.Cert:
    """Wrap newengine.farkas's already-exact-rational Farkas-infeasibility check."""
    from newengine import farkas
    v = farkas.verify_farkas_infeasible(A, b, y)
    if v.certificate is not None:
        return v.certificate
    return KV.Cert(KV.DECLINE, "farkas_witness", passed=False, detail=v.reason)


def witness_lp_kkt(c, A, b, x, y) -> KV.Cert:
    """Wrap newengine.farkas's already-exact-rational primal-dual KKT/complementary-slackness check."""
    from newengine import farkas
    v = farkas.verify_lp_optimal(c, A, b, x, y)
    if v.certificate is not None:
        return v.certificate
    return KV.Cert(KV.DECLINE, "lp_kkt_witness", passed=False, detail=v.reason)


# ============================================================================================================
# PART B — a SEPARATE, from-scratch independent matrix-power check for C-finite claims (does NOT import
# cfinite.py — two independently-written implementations agreeing is the actual evidence).
# ============================================================================================================

def _kernel_companion_nth(c: Sequence[int], init: Sequence[int], n: int) -> int:
    """Minimal, self-contained companion-matrix power-by-squaring over exact Python ints. Deliberately NOT
    shared code with cfinite.py — this is the independent half of the witness check."""
    d = len(c)
    if n < d:
        return init[n]
    C = [[c[j] for j in range(d)]] + [[1 if k == i - 1 else 0 for k in range(d)] for i in range(1, d)]

    def matmul(X, Y):
        return [[sum(X[i][k] * Y[k][j] for k in range(d)) for j in range(d)] for i in range(d)]

    p = n - (d - 1)
    R = [[1 if i == j else 0 for j in range(d)] for i in range(d)]
    base = [row[:] for row in C]
    while p > 0:
        if p & 1:
            R = matmul(R, base)
        base = matmul(base, base)
        p >>= 1
    v = [init[d - 1 - i] for i in range(d)]
    return sum(R[0][k] * v[k] for k in range(d))


def witness_matrix_identity(c: Sequence[int], init: Sequence[int], n: int, claimed: int) -> KV.Cert:
    """C-finite witness: does the kernel's OWN (separately-written) companion-power recomputation match the
    claimed value, exactly? This is the smallest possible independent check for a linear-recurrence claim —
    no shared code with whatever engine produced `claimed`."""
    try:
        recomputed = _kernel_companion_nth(list(c), list(init), n)
    except Exception as e:  # noqa: BLE001
        return KV.Cert(KV.DECLINE, "matrix_identity_witness", passed=False,
                       detail=f"kernel recomputation error: {type(e).__name__}: {e}")
    ok = (recomputed == claimed)
    return KV.Cert(KV.EXACT if ok else KV.DECLINE, "matrix_identity_witness", passed=ok,
                   check_cost="O(log n) independent companion-power recomputation (separate code path)",
                   detail=f"kernel recomputed {recomputed}, claim was {claimed}" if not ok
                          else f"kernel-independent recomputation confirms {claimed}")


# ============================================================================================================
# PART C — the genuinely new decision procedure: propositional DPLL + ground-EUF congruence closure.
# Deliberately the SIMPLEST correct construction (full enumeration, no unit-propagation-on-EUF-atoms,
# no incremental theory propagation) — this is a CHECKER, and auditable correctness outranks performance.
# ============================================================================================================

def _clause_status(clause: Clause, assign: Dict[int, bool]) -> Optional[bool]:
    """True=satisfied, False=falsified (every literal assigned, none true), None=undetermined."""
    any_unassigned = False
    for lit in clause:
        v = abs(lit)
        if v in assign:
            if (lit > 0) == assign[v]:
                return True
        else:
            any_unassigned = True
    return None if any_unassigned else False


def _vars_in(clauses: List[Clause]) -> List[int]:
    s = set()
    for clause in clauses:
        for lit in clause:
            s.add(abs(lit))
    return sorted(s)


def dpll_sat(clauses: List[Clause], assign: Optional[Dict[int, bool]] = None) -> Optional[Dict[int, bool]]:
    """Complete propositional SAT decision procedure: unit propagation to a fixpoint, then branch on an
    unassigned variable from an undetermined clause, recursing both ways. Returns a satisfying assignment
    or None (UNSAT, proven by exhaustive search — sound AND complete for propositional logic)."""
    base = dict(assign) if assign else {}

    def unit_propagate(a: Dict[int, bool]) -> Optional[Dict[int, bool]]:
        a = dict(a)
        changed = True
        while changed:
            changed = False
            for clause in clauses:
                st = _clause_status(clause, a)
                if st is False:
                    return None                                    # conflict
                if st is None:
                    unassigned = [lit for lit in clause if abs(lit) not in a]
                    if len(unassigned) == 1:
                        lit = unassigned[0]
                        a[abs(lit)] = (lit > 0)
                        changed = True
        return a

    def recurse(a: Dict[int, bool]) -> Optional[Dict[int, bool]]:
        a2 = unit_propagate(a)
        if a2 is None:
            return None
        statuses = [_clause_status(c, a2) for c in clauses]
        if any(st is False for st in statuses):
            return None
        if all(st is True for st in statuses):
            return a2
        var = None
        for clause, st in zip(clauses, statuses):
            if st is None:
                for lit in clause:
                    if abs(lit) not in a2:
                        var = abs(lit)
                        break
                if var is not None:
                    break
        for val in (True, False):
            a3 = dict(a2); a3[var] = val
            r = recurse(a3)
            if r is not None:
                return r
        return None

    return recurse(base)


def propositional_unsat(clauses: List[Clause]) -> bool:
    """UNSAT iff no satisfying assignment exists — decided exactly, not approximated."""
    return dpll_sat(clauses) is None


def _subterms(t: Term, acc: set) -> None:
    acc.add(t)
    if isinstance(t, tuple):
        _, args = t
        for a in args:
            _subterms(a, acc)


class _UnionFind:
    """Union-Find with path compression. Terms (strings or nested tuples) ARE the keys directly — no
    separate id-registry needed since ground terms are already hashable/comparable structures."""
    __slots__ = ("parent",)

    def __init__(self) -> None:
        self.parent: Dict[Term, Term] = {}

    def find(self, x: Term) -> Term:
        self.parent.setdefault(x, x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:                              # path compression
            nxt = self.parent[x]
            self.parent[x] = root
            x = nxt
        return root

    def union(self, x: Term, y: Term) -> bool:
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return False
        self.parent[rx] = ry
        return True


def _congruence_close(uf: _UnionFind, all_terms: List[Term], true_eqs: List[Tuple[Term, Term]]) -> None:
    """Union the asserted-true equalities, then close under function congruence to a fixpoint:
    f(a1..an) ≡ f(b1..bn) whenever ai≡bi for every i. O(n²) per round on the (small) term set — fine for a
    checker, not meant to scale to industrial SMT instances."""
    for a, b in true_eqs:
        uf.union(a, b)
    changed = True
    while changed:
        changed = False
        for i, t1 in enumerate(all_terms):
            if not isinstance(t1, tuple):
                continue
            f1, args1 = t1
            for t2 in all_terms[i + 1:]:
                if not isinstance(t2, tuple):
                    continue
                f2, args2 = t2
                if f1 != f2 or len(args1) != len(args2):
                    continue
                if uf.find(t1) == uf.find(t2):
                    continue
                if all(uf.find(a1) == uf.find(a2) for a1, a2 in zip(args1, args2)):
                    if uf.union(t1, t2):
                        changed = True


def euf_consistent(true_eqs: List[Tuple[Term, Term]], false_eqs: List[Tuple[Term, Term]]) -> bool:
    """Sound+complete ground-EUF consistency: is there NO contradiction between the asserted equalities and
    disequalities once congruence is taken into account? False iff congruence-closing `true_eqs` FORCES some
    pair in `false_eqs` to be equal anyway (a genuine EUF contradiction)."""
    all_terms: set = set()
    for a, b in true_eqs + false_eqs:
        _subterms(a, all_terms)
        _subterms(b, all_terms)
    uf = _UnionFind()
    terms_list = list(all_terms)
    for t in terms_list:
        uf.find(t)                                                  # register every term as its own root
    _congruence_close(uf, terms_list, true_eqs)
    for a, b in false_eqs:
        if uf.find(a) == uf.find(b):
            return False
    return True


def sat_modulo_euf(clauses: List[Clause], eq_atoms: Dict[int, Tuple[Term, Term]],
                    all_vars: Optional[List[int]] = None) -> Optional[Dict[int, bool]]:
    """clauses: propositional CNF where some variables (keyed in `eq_atoms`) denote ground equalities
    `term_a == term_b`; the rest are plain Booleans. Returns a satisfying assignment consistent with BOTH the
    propositional structure AND EUF congruence semantics, or None (UNSAT in the combination). Deliberately
    full enumeration + a post-hoc congruence-closure check at each propositionally-complete leaf: simplest
    correct construction, not the fastest one — see module docstring."""
    if all_vars is None:
        all_vars = _vars_in(clauses)

    def recurse(a: Dict[int, bool]) -> Optional[Dict[int, bool]]:
        for c in clauses:
            if _clause_status(c, a) is False:
                return None
        unassigned = [v for v in all_vars if v not in a]
        if not unassigned:
            true_eqs = [eq_atoms[v] for v, val in a.items() if val and v in eq_atoms]
            false_eqs = [eq_atoms[v] for v, val in a.items() if (not val) and v in eq_atoms]
            if not euf_consistent(true_eqs, false_eqs):
                return None                                         # theory conflict ⇒ dead branch
            return dict(a)
        v = unassigned[0]
        for val in (True, False):
            a2 = dict(a); a2[v] = val
            r = recurse(a2)
            if r is not None:
                return r
        return None

    return recurse({})


def is_unsat_modulo_euf(clauses: List[Clause], eq_atoms: Dict[int, Tuple[Term, Term]],
                         all_vars: Optional[List[int]] = None) -> bool:
    """UNSAT iff no model exists in the propositional+ground-EUF combination — decided exactly."""
    return sat_modulo_euf(clauses, eq_atoms, all_vars) is None


def verify_witness(kind: str, **kw) -> KV.Cert:
    """Single dispatch point for every witness kind this kernel knows. Unknown kind ⇒ honest DECLINE,
    never a guess — this is the one function callers outside metakernel/ should use."""
    table = {
        "sos_gram": witness_sos,
        "farkas": witness_farkas,
        "lp_kkt": witness_lp_kkt,
        "matrix_identity": witness_matrix_identity,
    }
    fn = table.get(kind)
    if fn is None:
        return KV.Cert(KV.DECLINE, "unknown_witness_kind", passed=False, detail=f"no checker registered for {kind!r}")
    try:
        return fn(**kw)
    except Exception as e:  # noqa: BLE001
        return KV.Cert(KV.DECLINE, f"{kind}_witness", passed=False, detail=f"witness check raised {type(e).__name__}: {e}")


def tcb_loc() -> int:
    """Non-blank, non-comment-only line count of THIS file — the measured TCB size for everything Part B/C
    cover (the propositional+ground-EUF decision procedure that replaces z3 for that fragment)."""
    import inspect
    src = inspect.getsource(__import__(__name__, fromlist=["_"]))
    n = 0
    for line in src.splitlines():
        s = line.strip()
        if s and not s.startswith("#") and not (s.startswith('"""') and s.endswith('"""') and len(s) > 3):
            n += 1
    return n


def adversarial_battery() -> dict:
    """★ propositional: a satisfiable CNF is SAT; the same plus its negation is UNSAT (classic conflict).
    ★ EUF: a==b ∧ b==c ⇒ a==c (congruence forces it) so asserting a==b, b==c, a!=c is UNSAT; without the
    third constraint it's SAT. ★ congruence over a function: f(a)=f(b) forced when a=b is asserted.
    ★ a genuinely satisfiable EUF instance (no forced equality) stays SAT. ★ matrix_identity / sos / farkas /
    lp_kkt witnesses round-trip through verify_witness with correct EXACT/DECLINE grading."""
    # -- propositional --
    sat1 = dpll_sat([[1, 2], [-1, 2]])                                   # (x1∨x2)∧(¬x1∨x2) — SAT (x2=True)
    unsat1 = propositional_unsat([[1], [-1]])                            # x1 ∧ ¬x1 — UNSAT
    unsat2 = propositional_unsat([[1, 2], [-1, 2], [1, -2], [-1, -2]])   # all 4 clauses over 2 vars — UNSAT
    # -- ground EUF (a,b,c plain atoms; x=mkfun term to exercise congruence) --
    a, b, c = "a", "b", "c"
    cong_forced = not euf_consistent([(a, b), (b, c)], [(a, c)])         # a=b,b=c ⊢ a=c ⇒ asserting a≠c is a contradiction
    cong_free = euf_consistent([(a, b)], [])                             # a=b alone, no disequality claimed ⇒ consistent
    fa, fb = mkfun("f", a), mkfun("f", b)
    func_cong_forced = not euf_consistent([(a, b)], [(fa, fb)])          # a=b ⇒ f(a)=f(b) (congruence) ⇒ f(a)≠f(b) is a contradiction
    func_cong_free = euf_consistent([], [(fa, fb)])                     # no equality asserted ⇒ f(a)≠f(b) is consistent
    # -- combined propositional+EUF: var 1 means (a==b), var 2 means (b==c), var 3 means (a==c) --
    eqs = {1: (a, b), 2: (b, c), 3: (a, c)}
    combo_unsat = is_unsat_modulo_euf([[1], [2], [-3]], eqs)             # a=b ∧ b=c ∧ a≠c ⇒ UNSAT (forced congruence contradiction)
    combo_sat = is_unsat_modulo_euf([[1], [2], [3]], eqs) is False       # a=b ∧ b=c ∧ a=c ⇒ consistent ⇒ SAT
    # -- witness wrappers --
    import sympy as sp
    x = sp.Symbol("x")
    wit_sos = verify_witness("sos_gram", expr=x ** 2, Q=sp.Matrix([[1]]), basis=[x])
    wit_farkas = verify_witness("farkas", A=[[1], [-1]], b=[-1, -1], y=[1, 1])
    wit_lp = verify_witness("lp_kkt", c=[1], A=[[1]], b=[3], x=[3], y=[1])
    wit_mat = verify_witness("matrix_identity", c=[1, 1], init=[0, 1], n=20, claimed=6765)        # Fibonacci(20)
    wit_mat_wrong = verify_witness("matrix_identity", c=[1, 1], init=[0, 1], n=20, claimed=9999)  # wrong claim
    wit_unknown = verify_witness("nonsense_kind")
    cases = {
        "propositional_sat_found": sat1 is not None and (sat1.get(2) is True),
        "propositional_unsat_trivial": unsat1 is True,
        "propositional_unsat_4clauses": unsat2 is True,
        "euf_congruence_forces_transitivity": cong_forced,
        "euf_no_false_contradiction": cong_free,
        "euf_function_congruence_forced": func_cong_forced,
        "euf_function_congruence_free_when_unasserted": func_cong_free,
        "combo_dpll_euf_unsat": combo_unsat,
        "combo_dpll_euf_sat": combo_sat,
        "witness_sos_exact": wit_sos.grade == KV.EXACT and wit_sos.passed,
        "witness_farkas_exact": wit_farkas.grade == KV.EXACT and wit_farkas.passed,
        "witness_lp_kkt_exact": wit_lp.grade == KV.EXACT and wit_lp.passed,
        "witness_matrix_identity_exact": wit_mat.grade == KV.EXACT and wit_mat.passed,
        "witness_matrix_identity_declines_on_wrong_claim": wit_mat_wrong.grade == KV.DECLINE,
        "witness_unknown_kind_declines": wit_unknown.grade == KV.DECLINE,
    }
    return {"cases": cases, "all_ok": all(cases.values()), "failed": [k for k, v in cases.items() if not v],
            "tcb_loc": tcb_loc()}


if __name__ == "__main__":
    import json
    print(json.dumps(adversarial_battery(), indent=2, default=str))
